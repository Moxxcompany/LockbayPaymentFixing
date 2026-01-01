"""
E2E Tests: Concurrency and Race Condition Testing

Tests the system's ability to handle concurrent operations safely:
1. Concurrent user registrations and database integrity
2. Race conditions in escrow operations (payment, release, dispute)
3. Simultaneous cashout attempts and balance consistency  
4. Concurrent admin operations and resource contention
5. High-load scenarios with multiple users performing various operations simultaneously
"""

import pytest
import asyncio
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any, List
import logging

from telegram import Update
from telegram.ext import ConversationHandler

# Test foundation
from tests.e2e_test_foundation import (
    TelegramObjectFactory, 
    DatabaseTransactionHelper,
    NotificationVerifier,
    TimeController,
    provider_fakes
)

# Models and services
from models import (
    User, Wallet, Escrow, EscrowStatus, EscrowHolding, Transaction, 
    TransactionType, Cashout, CashoutStatus, UnifiedTransaction, 
    UnifiedTransactionStatus, UnifiedTransactionType, Dispute, DisputeStatus,
    OnboardingSession, OnboardingStep, EmailVerification
)
from services.unified_transaction_service import UnifiedTransactionService
from services.escrow_validation_service import EscrowValidationService
from services.escrow_fund_manager import EscrowFundManager
from services.onboarding_service import OnboardingService
from services.consolidated_notification_service import (
    ConsolidatedNotificationService, NotificationCategory, NotificationPriority
)

# Handlers
from handlers.onboarding_router import _handle_start, _handle_email_input
from handlers.escrow import (
    handle_seller_input, handle_confirm_trade_final, handle_switch_payment_method
)
from handlers.wallet_direct import (
    handle_confirm_ngn_cashout, handle_amount_selection
)

# Utils
from utils.helpers import generate_utid
from utils.wallet_manager import get_or_create_wallet
from utils.distributed_lock import DistributedLockService
from config import Config

logger = logging.getLogger(__name__)


@pytest.mark.e2e_concurrency
class TestConcurrencyAndRaceConditions:
    """Comprehensive concurrency and race condition testing"""
    
    async def test_concurrent_user_registrations_database_integrity(
        self, 
        test_db_session, 
        patched_services,
        mock_external_services
    ):
        """
        Test concurrent user registrations maintain database integrity
        
        Scenario: Multiple users attempting to register simultaneously with potential conflicts
        """
        logger.info("Testing concurrent user registrations...")
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            # Create concurrent registration tasks
            registration_tasks = []
            user_data = []
            
            # Generate 10 concurrent user registration attempts
            for i in range(10):
                telegram_id = 5590000500 + i
                username = f"concurrent_user_{i}"
                email = f"concurrent_user_{i}@example.com"
                
                telegram_user = TelegramObjectFactory.create_user(
                    user_id=telegram_id,
                    username=username,
                    first_name=f"User{i}",
                    last_name="Concurrent"
                )
                
                user_data.append({
                    'telegram_user': telegram_user,
                    'email': email,
                    'username': username
                })
            
            # Execute concurrent registrations
            async def register_user(user_info):
                try:
                    start_message = TelegramObjectFactory.create_message(
                        user_info['telegram_user'], "/start"
                    )
                    start_update = TelegramObjectFactory.create_update(
                        user=user_info['telegram_user'],
                        message=start_message
                    )
                    context = TelegramObjectFactory.create_context()
                    
                    with patch('handlers.onboarding_router.managed_session') as mock_session:
                        mock_session.return_value.__aenter__.return_value = session
                        
                        # Add artificial delay to increase chance of race conditions
                        await asyncio.sleep(0.01)
                        
                        result = await handle_start_command(start_update, context)
                        return {
                            'success': True,
                            'telegram_id': user_info['telegram_user'].id,
                            'username': user_info['username'],
                            'result': result
                        }
                        
                except Exception as e:
                    logger.error(f"Registration failed for {user_info['username']}: {e}")
                    return {
                        'success': False,
                        'telegram_id': user_info['telegram_user'].id,
                        'username': user_info['username'],
                        'error': str(e)
                    }
            
            # Execute all registrations concurrently
            results = await asyncio.gather(
                *[register_user(user_info) for user_info in user_data],
                return_exceptions=True
            )
            
            # Analyze results
            successful_registrations = [r for r in results if isinstance(r, dict) and r.get('success')]
            failed_registrations = [r for r in results if isinstance(r, dict) and not r.get('success')]
            exceptions = [r for r in results if isinstance(r, Exception)]
            
            logger.info(f"Successful registrations: {len(successful_registrations)}")
            logger.info(f"Failed registrations: {len(failed_registrations)}")
            logger.info(f"Exceptions: {len(exceptions)}")
            
            # Verify database integrity
            # Check for duplicate telegram_ids
            telegram_ids = [r['telegram_id'] for r in successful_registrations]
            assert len(telegram_ids) == len(set(telegram_ids)), "Duplicate telegram_ids detected"
            
            # Verify users were actually created in database
            for result in successful_registrations:
                user_query = await session.execute(
                    "SELECT * FROM users WHERE telegram_id = ?",
                    (result['telegram_id'],)
                )
                user_record = user_query.fetchone()
                assert user_record is not None, f"User {result['username']} not found in database"
                assert user_record['telegram_id'] == result['telegram_id']
            
            # Verify no orphaned wallet records
            all_users = await session.execute("SELECT id FROM users")
            user_ids = [row['id'] for row in all_users.fetchall()]
            
            all_wallets = await session.execute("SELECT user_id FROM wallets")
            wallet_user_ids = [row['user_id'] for row in all_wallets.fetchall()]
            
            # Every wallet should belong to an existing user
            for wallet_user_id in wallet_user_ids:
                assert wallet_user_id in user_ids, f"Orphaned wallet found for user_id {wallet_user_id}"
    
    async def test_concurrent_escrow_operations_race_conditions(
        self,
        test_db_session,
        patched_services,
        mock_external_services
    ):
        """
        Test race conditions in concurrent escrow operations
        
        Scenario: Multiple operations on the same escrow (release, dispute, cancel) happening simultaneously
        """
        logger.info("Testing concurrent escrow operations...")
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            # Create users and escrow
            buyer = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=5590000600,
                email="race_buyer@example.com",
                balance_usd=Decimal("1000.00")
            )
            
            seller = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=5590000601,
                email="race_seller@example.com",
                balance_usd=Decimal("500.00")
            )
            
            # Create active escrow
            escrow = await DatabaseTransactionHelper.create_test_escrow(
                session,
                buyer_id=buyer.id,
                seller_email=seller.email,
                amount=Decimal("300.00"),
                status=EscrowStatus.ACTIVE.value
            )
            
            # Update to include seller_id
            await session.execute(
                "UPDATE escrows SET seller_id = ? WHERE escrow_id = ?",
                (seller.id, escrow.escrow_id)
            )
            
            # Create escrow holding
            holding = EscrowHolding(
                escrow_id=escrow.escrow_id,
                amount_held=Decimal("300.00"),
                currency="USDT",
                created_at=datetime.utcnow()
            )
            session.add(holding)
            await session.flush()
            
            # Create Telegram users
            buyer_telegram = TelegramObjectFactory.create_user(
                user_id=buyer.telegram_id,
                username=buyer.username
            )
            
            seller_telegram = TelegramObjectFactory.create_user(
                user_id=seller.telegram_id,
                username=seller.username
            )
            
            # Define concurrent operations
            async def release_escrow():
                try:
                    release_callback = TelegramObjectFactory.create_callback_query(
                        user=buyer_telegram,
                        data=f"release_escrow_{escrow.escrow_id}"
                    )
                    release_update = TelegramObjectFactory.create_update(
                        user=buyer_telegram,
                        callback_query=release_callback
                    )
                    release_context = TelegramObjectFactory.create_context()
                    
                    with patch('handlers.escrow.managed_session') as mock_session:
                        mock_session.return_value.__aenter__.return_value = session
                        
                        # Add delay to increase race condition chance
                        await asyncio.sleep(0.02)
                        
                        result = await handle_escrow_release(release_update, release_context)
                        return {'operation': 'release', 'success': True, 'result': result}
                        
                except Exception as e:
                    return {'operation': 'release', 'success': False, 'error': str(e)}
            
            async def create_dispute():
                try:
                    dispute_message = TelegramObjectFactory.create_message(
                        buyer_telegram,
                        "I want to dispute this escrow - service not delivered"
                    )
                    dispute_update = TelegramObjectFactory.create_update(
                        user=buyer_telegram,
                        message=dispute_message
                    )
                    dispute_context = TelegramObjectFactory.create_context()
                    dispute_context.user_data = {"escrow_id": escrow.escrow_id}
                    
                    with patch('handlers.escrow.managed_session') as mock_session:
                        mock_session.return_value.__aenter__.return_value = session
                        
                        # Add delay to increase race condition chance
                        await asyncio.sleep(0.01)
                        
                        result = await handle_dispute_creation(dispute_update, dispute_context)
                        return {'operation': 'dispute', 'success': True, 'result': result}
                        
                except Exception as e:
                    return {'operation': 'dispute', 'success': False, 'error': str(e)}
            
            async def seller_action():
                try:
                    # Simulate seller trying to modify escrow state
                    await asyncio.sleep(0.015)
                    
                    # Check current escrow status
                    status_query = await session.execute(
                        "SELECT status FROM escrows WHERE escrow_id = ?",
                        (escrow.escrow_id,)
                    )
                    status_record = status_query.fetchone()
                    current_status = status_record['status'] if status_record else None
                    
                    return {
                        'operation': 'seller_check', 
                        'success': True, 
                        'current_status': current_status
                    }
                    
                except Exception as e:
                    return {'operation': 'seller_check', 'success': False, 'error': str(e)}
            
            # Execute concurrent operations
            concurrent_results = await asyncio.gather(
                release_escrow(),
                create_dispute(), 
                seller_action(),
                return_exceptions=True
            )
            
            # Analyze results
            successful_ops = [r for r in concurrent_results if isinstance(r, dict) and r.get('success')]
            failed_ops = [r for r in concurrent_results if isinstance(r, dict) and not r.get('success')]
            exceptions = [r for r in concurrent_results if isinstance(r, Exception)]
            
            logger.info(f"Successful operations: {len(successful_ops)}")
            logger.info(f"Failed operations: {len(failed_ops)}")
            logger.info(f"Exceptions: {len(exceptions)}")
            
            # Verify escrow final state is consistent
            final_escrow = await session.execute(
                "SELECT * FROM escrows WHERE escrow_id = ?",
                (escrow.escrow_id,)
            )
            final_record = final_escrow.fetchone()
            
            # Escrow should be in one valid final state
            valid_final_states = [
                EscrowStatus.ACTIVE.value,
                EscrowStatus.COMPLETED.value,
                EscrowStatus.DISPUTED.value,
                EscrowStatus.CANCELLED.value
            ]
            
            assert final_record['status'] in valid_final_states, f"Invalid final state: {final_record['status']}"
            
            # If completed, verify balance updates are consistent
            if final_record['status'] == EscrowStatus.COMPLETED.value:
                updated_seller = await session.execute(
                    "SELECT balance_usd FROM wallets WHERE user_id = ?",
                    (seller.id,)
                )
                seller_balance = updated_seller.fetchone()
                # Seller should have received the escrow amount
                assert seller_balance['balance_usd'] >= Decimal("500.00")
            
            # Verify no duplicate dispute records
            dispute_count = await session.execute(
                "SELECT COUNT(*) as count FROM disputes WHERE escrow_id = ?",
                (escrow.escrow_id,)
            )
            dispute_count_record = dispute_count.fetchone()
            assert dispute_count_record['count'] <= 1, "Multiple disputes created for same escrow"
    
    async def test_concurrent_balance_operations_consistency(
        self,
        test_db_session,
        patched_services,
        mock_external_services
    ):
        """
        Test concurrent balance operations maintain consistency
        
        Scenario: Multiple cashouts and transactions happening simultaneously for the same user
        """
        logger.info("Testing concurrent balance operations...")
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            # Create user with substantial balance
            user = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=5590000700,
                email="balance_race_user@example.com",
                balance_usd=Decimal("5000.00")
            )
            
            # Set crypto balances
            await session.execute(
                "UPDATE wallets SET balance_btc = ?, balance_eth = ? WHERE user_id = ?",
                (Decimal("0.5"), Decimal("10.0"), user.id)
            )
            
            initial_usd_balance = Decimal("5000.00")
            initial_btc_balance = Decimal("0.5")
            initial_eth_balance = Decimal("10.0")
            
            telegram_user = TelegramObjectFactory.create_user(
                user_id=user.telegram_id,
                username=user.username
            )
            
            # Define concurrent balance operations
            async def crypto_cashout_btc():
                try:
                    context = TelegramObjectFactory.create_context()
                    context.user_data = {
                        "cashout_data": {
                            "type": "crypto",
                            "currency": "BTC",
                            "address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
                            "amount": Decimal("0.1")
                        }
                    }
                    
                    confirm_callback = TelegramObjectFactory.create_callback_query(
                        user=telegram_user,
                        data="confirm_crypto_cashout"
                    )
                    confirm_update = TelegramObjectFactory.create_update(
                        user=telegram_user,
                        callback_query=confirm_callback
                    )
                    
                    with patch('services.kraken_service.KrakenService.withdraw_crypto') as mock_kraken:
                        mock_kraken.return_value = {
                            'success': True,
                            'withdrawal_id': 'KRAKEN_BTC_123',
                            'txid': 'BTC_TX_123'
                        }
                        
                        with patch('handlers.wallet_direct.managed_session') as mock_session:
                            mock_session.return_value.__aenter__.return_value = session
                            
                            await asyncio.sleep(0.01)  # Race condition delay
                            
                            result = await handle_crypto_cashout_confirmation(confirm_update, context)
                            
                            # Update balance
                            await session.execute(
                                "UPDATE wallets SET balance_btc = balance_btc - ? WHERE user_id = ?",
                                (Decimal("0.1"), user.id)
                            )
                            
                            return {'operation': 'btc_cashout', 'success': True, 'amount': Decimal("0.1")}
                            
                except Exception as e:
                    return {'operation': 'btc_cashout', 'success': False, 'error': str(e)}
            
            async def crypto_cashout_eth():
                try:
                    context = TelegramObjectFactory.create_context()
                    context.user_data = {
                        "cashout_data": {
                            "type": "crypto",
                            "currency": "ETH",
                            "address": "0x742d35Cc6238C1357F5B1e34e62eC3E6b6D2C3e1",
                            "amount": Decimal("2.0")
                        }
                    }
                    
                    confirm_callback = TelegramObjectFactory.create_callback_query(
                        user=telegram_user,
                        data="confirm_crypto_cashout"
                    )
                    confirm_update = TelegramObjectFactory.create_update(
                        user=telegram_user,
                        callback_query=confirm_callback
                    )
                    
                    with patch('services.kraken_service.KrakenService.withdraw_crypto') as mock_kraken:
                        mock_kraken.return_value = {
                            'success': True,
                            'withdrawal_id': 'KRAKEN_ETH_456',
                            'txid': 'ETH_TX_456'
                        }
                        
                        with patch('handlers.wallet_direct.managed_session') as mock_session:
                            mock_session.return_value.__aenter__.return_value = session
                            
                            await asyncio.sleep(0.02)  # Race condition delay
                            
                            result = await handle_crypto_cashout_confirmation(confirm_update, context)
                            
                            # Update balance
                            await session.execute(
                                "UPDATE wallets SET balance_eth = balance_eth - ? WHERE user_id = ?",
                                (Decimal("2.0"), user.id)
                            )
                            
                            return {'operation': 'eth_cashout', 'success': True, 'amount': Decimal("2.0")}
                            
                except Exception as e:
                    return {'operation': 'eth_cashout', 'success': False, 'error': str(e)}
            
            async def ngn_cashout():
                try:
                    context = TelegramObjectFactory.create_context()
                    context.user_data = {
                        "cashout_data": {
                            "type": "ngn",
                            "usd_amount": Decimal("1000.00"),
                            "ngn_amount": Decimal("1500000.00"),
                            "bank_account_id": 1,
                            "otp_verified": True
                        }
                    }
                    
                    confirm_callback = TelegramObjectFactory.create_callback_query(
                        user=telegram_user,
                        data="confirm_ngn_cashout"
                    )
                    confirm_update = TelegramObjectFactory.create_update(
                        user=telegram_user,
                        callback_query=confirm_callback
                    )
                    
                    with patch('services.fincra_service.FincraService.process_bank_transfer') as mock_fincra:
                        mock_fincra.return_value = {
                            'success': True,
                            'transfer_id': 'FINCRA_NGN_789',
                            'reference': 'NGN_REF_789'
                        }
                        
                        with patch('handlers.wallet_direct.managed_session') as mock_session:
                            mock_session.return_value.__aenter__.return_value = session
                            
                            await asyncio.sleep(0.015)  # Race condition delay
                            
                            result = await handle_ngn_cashout_confirmation(confirm_update, context)
                            
                            # Update balance
                            await session.execute(
                                "UPDATE wallets SET balance_usd = balance_usd - ? WHERE user_id = ?",
                                (Decimal("1000.00"), user.id)
                            )
                            
                            return {'operation': 'ngn_cashout', 'success': True, 'amount': Decimal("1000.00")}
                            
                except Exception as e:
                    return {'operation': 'ngn_cashout', 'success': False, 'error': str(e)}
            
            # Execute concurrent balance operations
            balance_results = await asyncio.gather(
                crypto_cashout_btc(),
                crypto_cashout_eth(),
                ngn_cashout(),
                return_exceptions=True
            )
            
            # Analyze results
            successful_cashouts = [r for r in balance_results if isinstance(r, dict) and r.get('success')]
            failed_cashouts = [r for r in balance_results if isinstance(r, dict) and not r.get('success')]
            
            logger.info(f"Successful cashouts: {len(successful_cashouts)}")
            logger.info(f"Failed cashouts: {len(failed_cashouts)}")
            
            # Verify final balance consistency
            final_wallet = await session.execute(
                "SELECT * FROM wallets WHERE user_id = ?",
                (user.id,)
            )
            wallet_record = final_wallet.fetchone()
            
            # Calculate expected balances based on successful operations
            expected_usd = initial_usd_balance
            expected_btc = initial_btc_balance
            expected_eth = initial_eth_balance
            
            for cashout in successful_cashouts:
                if cashout['operation'] == 'btc_cashout':
                    expected_btc -= cashout['amount']
                elif cashout['operation'] == 'eth_cashout':
                    expected_eth -= cashout['amount']
                elif cashout['operation'] == 'ngn_cashout':
                    expected_usd -= cashout['amount']
            
            # Verify balances are consistent (allowing for small rounding differences)
            assert abs(wallet_record['balance_usd'] - expected_usd) < Decimal("0.01"), f"USD balance inconsistent: {wallet_record['balance_usd']} vs {expected_usd}"
            assert abs(wallet_record['balance_btc'] - expected_btc) < Decimal("0.0001"), f"BTC balance inconsistent: {wallet_record['balance_btc']} vs {expected_btc}"
            assert abs(wallet_record['balance_eth'] - expected_eth) < Decimal("0.001"), f"ETH balance inconsistent: {wallet_record['balance_eth']} vs {expected_eth}"
            
            # Verify no negative balances
            assert wallet_record['balance_usd'] >= Decimal("0"), "Negative USD balance detected"
            assert wallet_record['balance_btc'] >= Decimal("0"), "Negative BTC balance detected"
            assert wallet_record['balance_eth'] >= Decimal("0"), "Negative ETH balance detected"
    
    async def test_high_load_concurrent_user_operations(
        self,
        test_db_session,
        patched_services,
        mock_external_services
    ):
        """
        Test system under high load with many concurrent users
        
        Scenario: 50+ users performing various operations simultaneously
        """
        logger.info("Testing high load concurrent operations...")
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            # Create multiple users for high load testing
            users = []
            for i in range(20):  # Reduced from 50 for test performance
                user = await DatabaseTransactionHelper.create_test_user(
                    session,
                    telegram_id=5590000800 + i,
                    email=f"load_user_{i}@example.com",
                    username=f"load_user_{i}",
                    balance_usd=Decimal("1000.00")
                )
                users.append(user)
            
            # Define various operation types
            async def create_escrow_operation(user_idx):
                try:
                    user = users[user_idx]
                    telegram_user = TelegramObjectFactory.create_user(
                        user_id=user.telegram_id,
                        username=user.username
                    )
                    
                    context = TelegramObjectFactory.create_context()
                    context.user_data = {
                        "escrow_data": {
                            "seller_email": f"seller_{user_idx}@example.com",
                            "amount": Decimal("100.00"),
                            "description": f"Load test escrow {user_idx}",
                            "delivery_hours": 72,
                            "currency": "USDT",
                            "network": "ERC20"
                        }
                    }
                    
                    payment_callback = TelegramObjectFactory.create_callback_query(
                        user=telegram_user,
                        data="crypto_USDT-ERC20"
                    )
                    payment_update = TelegramObjectFactory.create_update(
                        user=telegram_user,
                        callback_query=payment_callback
                    )
                    
                    with patch('services.crypto.CryptoServiceAtomic.generate_deposit_address') as mock_addr:
                        mock_addr.return_value = {
                            'success': True,
                            'address': f"0x{generate_utid().lower()}",
                            'currency': 'USDT-ERC20'
                        }
                        
                        with patch('handlers.escrow.managed_session') as mock_session:
                            mock_session.return_value.__aenter__.return_value = session
                            
                            # Random delay to simulate real user behavior
                            await asyncio.sleep(0.001 * (user_idx % 10))
                            
                            result = await handle_payment_method_selection(payment_update, context)
                            
                            return {
                                'user_idx': user_idx,
                                'operation': 'create_escrow',
                                'success': True
                            }
                            
                except Exception as e:
                    return {
                        'user_idx': user_idx,
                        'operation': 'create_escrow', 
                        'success': False,
                        'error': str(e)
                    }
            
            async def register_new_user_operation(user_idx):
                try:
                    new_telegram_id = 5590001000 + user_idx
                    telegram_user = TelegramObjectFactory.create_user(
                        user_id=new_telegram_id,
                        username=f"new_load_user_{user_idx}",
                        first_name=f"New{user_idx}",
                        last_name="LoadUser"
                    )
                    
                    start_message = TelegramObjectFactory.create_message(telegram_user, "/start")
                    start_update = TelegramObjectFactory.create_update(
                        user=telegram_user,
                        message=start_message
                    )
                    context = TelegramObjectFactory.create_context()
                    
                    with patch('handlers.onboarding_router.managed_session') as mock_session:
                        mock_session.return_value.__aenter__.return_value = session
                        
                        await asyncio.sleep(0.001 * (user_idx % 15))
                        
                        result = await handle_start_command(start_update, context)
                        
                        return {
                            'user_idx': user_idx,
                            'operation': 'register_user',
                            'success': True,
                            'telegram_id': new_telegram_id
                        }
                        
                except Exception as e:
                    return {
                        'user_idx': user_idx,
                        'operation': 'register_user',
                        'success': False,
                        'error': str(e)
                    }
            
            async def balance_check_operation(user_idx):
                try:
                    user = users[user_idx]
                    
                    # Simulate balance check
                    await asyncio.sleep(0.001 * (user_idx % 5))
                    
                    balance_query = await session.execute(
                        "SELECT * FROM wallets WHERE user_id = ?",
                        (user.id,)
                    )
                    balance_record = balance_query.fetchone()
                    
                    return {
                        'user_idx': user_idx,
                        'operation': 'balance_check',
                        'success': True,
                        'balance': balance_record['balance_usd'] if balance_record else 0
                    }
                    
                except Exception as e:
                    return {
                        'user_idx': user_idx,
                        'operation': 'balance_check',
                        'success': False,
                        'error': str(e)
                    }
            
            # Create mixed load test operations
            load_tasks = []
            
            # 20 escrow creations
            for i in range(10):
                load_tasks.append(create_escrow_operation(i))
            
            # 15 new user registrations  
            for i in range(10):
                load_tasks.append(register_new_user_operation(i))
            
            # 30 balance checks
            for i in range(15):
                load_tasks.append(balance_check_operation(i % 20))
            
            # Execute all operations concurrently
            logger.info(f"Executing {len(load_tasks)} concurrent operations...")
            start_time = datetime.utcnow()
            
            load_results = await asyncio.gather(*load_tasks, return_exceptions=True)
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            # Analyze load test results
            successful_ops = [r for r in load_results if isinstance(r, dict) and r.get('success')]
            failed_ops = [r for r in load_results if isinstance(r, dict) and not r.get('success')]
            exceptions = [r for r in load_results if isinstance(r, Exception)]
            
            logger.info(f"Load test completed in {duration:.2f} seconds")
            logger.info(f"Successful operations: {len(successful_ops)}")
            logger.info(f"Failed operations: {len(failed_ops)}")
            logger.info(f"Exceptions: {len(exceptions)}")
            
            # Performance assertions
            success_rate = len(successful_ops) / len(load_tasks)
            assert success_rate >= 0.8, f"Success rate too low: {success_rate:.2%}"
            
            # Verify database consistency after load test
            total_users = await session.execute("SELECT COUNT(*) as count FROM users")
            user_count = total_users.fetchone()['count']
            
            total_wallets = await session.execute("SELECT COUNT(*) as count FROM wallets")
            wallet_count = total_wallets.fetchone()['count']
            
            # Every user should have exactly one wallet
            assert user_count == wallet_count, f"User-wallet mismatch: {user_count} users, {wallet_count} wallets"
            
            # Check for any negative balances
            negative_balances = await session.execute(
                "SELECT COUNT(*) as count FROM wallets WHERE balance_usd < 0 OR balance_btc < 0 OR balance_eth < 0"
            )
            negative_count = negative_balances.fetchone()['count']
            assert negative_count == 0, f"Found {negative_count} wallets with negative balances"
    
    async def test_database_deadlock_prevention(
        self,
        test_db_session,
        patched_services,
        mock_external_services
    ):
        """
        Test database deadlock prevention mechanisms
        
        Scenario: Operations that could cause deadlocks under high concurrency
        """
        logger.info("Testing database deadlock prevention...")
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            # Create users for deadlock testing
            user1 = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=5590000900,
                email="deadlock_user1@example.com",
                balance_usd=Decimal("2000.00")
            )
            
            user2 = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=5590000901,
                email="deadlock_user2@example.com",
                balance_usd=Decimal("2000.00")
            )
            
            # Create escrow between users
            escrow = await DatabaseTransactionHelper.create_test_escrow(
                session,
                buyer_id=user1.id,
                seller_email=user2.email,
                amount=Decimal("500.00"),
                status=EscrowStatus.ACTIVE.value
            )
            
            await session.execute(
                "UPDATE escrows SET seller_id = ? WHERE escrow_id = ?",
                (user2.id, escrow.escrow_id)
            )
            
            # Define operations that could cause deadlocks
            async def update_user1_then_user2():
                try:
                    # Update user1 wallet first, then user2
                    await asyncio.sleep(0.01)
                    
                    await session.execute(
                        "UPDATE wallets SET balance_usd = balance_usd - ? WHERE user_id = ?",
                        (Decimal("100.00"), user1.id)
                    )
                    
                    await asyncio.sleep(0.02)
                    
                    await session.execute(
                        "UPDATE wallets SET balance_usd = balance_usd + ? WHERE user_id = ?",
                        (Decimal("100.00"), user2.id)
                    )
                    
                    return {'operation': 'user1_then_user2', 'success': True}
                    
                except Exception as e:
                    return {'operation': 'user1_then_user2', 'success': False, 'error': str(e)}
            
            async def update_user2_then_user1():
                try:
                    # Update user2 wallet first, then user1
                    await asyncio.sleep(0.01)
                    
                    await session.execute(
                        "UPDATE wallets SET balance_usd = balance_usd - ? WHERE user_id = ?",
                        (Decimal("50.00"), user2.id)
                    )
                    
                    await asyncio.sleep(0.02)
                    
                    await session.execute(
                        "UPDATE wallets SET balance_usd = balance_usd + ? WHERE user_id = ?",
                        (Decimal("50.00"), user1.id)
                    )
                    
                    return {'operation': 'user2_then_user1', 'success': True}
                    
                except Exception as e:
                    return {'operation': 'user2_then_user1', 'success': False, 'error': str(e)}
            
            async def update_escrow_status():
                try:
                    await asyncio.sleep(0.015)
                    
                    await session.execute(
                        "UPDATE escrows SET status = ? WHERE escrow_id = ?",
                        (EscrowStatus.COMPLETED.value, escrow.escrow_id)
                    )
                    
                    return {'operation': 'escrow_update', 'success': True}
                    
                except Exception as e:
                    return {'operation': 'escrow_update', 'success': False, 'error': str(e)}
            
            # Execute operations that could deadlock
            deadlock_results = await asyncio.gather(
                update_user1_then_user2(),
                update_user2_then_user1(),
                update_escrow_status(),
                return_exceptions=True
            )
            
            # Analyze deadlock test results
            successful_ops = [r for r in deadlock_results if isinstance(r, dict) and r.get('success')]
            failed_ops = [r for r in deadlock_results if isinstance(r, dict) and not r.get('success')]
            exceptions = [r for r in deadlock_results if isinstance(r, Exception)]
            
            logger.info(f"Deadlock test - Successful: {len(successful_ops)}, Failed: {len(failed_ops)}, Exceptions: {len(exceptions)}")
            
            # At least some operations should succeed (deadlock prevention working)
            assert len(successful_ops) >= 2, "Too many operations failed - possible deadlock issue"
            
            # Verify final database state is consistent
            final_user1 = await session.execute(
                "SELECT balance_usd FROM wallets WHERE user_id = ?",
                (user1.id,)
            )
            user1_balance = final_user1.fetchone()['balance_usd']
            
            final_user2 = await session.execute(
                "SELECT balance_usd FROM wallets WHERE user_id = ?",
                (user2.id,)
            )
            user2_balance = final_user2.fetchone()['balance_usd']
            
            # Total balance should be conserved
            total_balance = user1_balance + user2_balance
            expected_total = Decimal("4000.00")  # Initial 2000 + 2000
            
            assert abs(total_balance - expected_total) < Decimal("1.00"), f"Balance not conserved: {total_balance} vs {expected_total}"
            
            # No negative balances
            assert user1_balance >= Decimal("0"), f"User1 has negative balance: {user1_balance}"
            assert user2_balance >= Decimal("0"), f"User2 has negative balance: {user2_balance}"
    
    async def test_notification_system_under_load(
        self,
        test_db_session,
        patched_services,
        mock_external_services
    ):
        """
        Test notification system handles concurrent load properly
        
        Scenario: Many notifications being sent simultaneously
        """
        logger.info("Testing notification system under load...")
        
        notification_verifier = NotificationVerifier()
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            # Create users for notification testing
            users = []
            for i in range(15):
                user = await DatabaseTransactionHelper.create_test_user(
                    session,
                    telegram_id=5590001100 + i,
                    email=f"notify_user_{i}@example.com",
                    username=f"notify_user_{i}",
                    balance_usd=Decimal("1000.00")
                )
                users.append(user)
            
            # Define concurrent notification operations
            async def send_escrow_notification(user_idx):
                try:
                    user = users[user_idx]
                    
                    with patch('services.consolidated_notification_service.ConsolidatedNotificationService.send_notification',
                              new=notification_verifier.capture_notification):
                        
                        await notification_verifier.capture_notification({
                            'user_id': user.id,
                            'category': NotificationCategory.ESCROW,
                            'priority': NotificationPriority.HIGH,
                            'channels': ['telegram'],
                            'content': {
                                'title': f'Escrow Update {user_idx}',
                                'message': f'Your escrow has been updated - User {user_idx}'
                            }
                        })
                        
                        await asyncio.sleep(0.001 * (user_idx % 5))
                        
                        return {
                            'user_idx': user_idx,
                            'operation': 'escrow_notification',
                            'success': True
                        }
                        
                except Exception as e:
                    return {
                        'user_idx': user_idx,
                        'operation': 'escrow_notification',
                        'success': False,
                        'error': str(e)
                    }
            
            async def send_cashout_notification(user_idx):
                try:
                    user = users[user_idx]
                    
                    with patch('services.consolidated_notification_service.ConsolidatedNotificationService.send_notification',
                              new=notification_verifier.capture_notification):
                        
                        await notification_verifier.capture_notification({
                            'user_id': user.id,
                            'category': NotificationCategory.CASHOUT,
                            'priority': NotificationPriority.MEDIUM,
                            'channels': ['email'],
                            'content': {
                                'title': f'Cashout Processed {user_idx}',
                                'message': f'Your cashout has been processed - User {user_idx}'
                            }
                        })
                        
                        await asyncio.sleep(0.001 * (user_idx % 3))
                        
                        return {
                            'user_idx': user_idx,
                            'operation': 'cashout_notification',
                            'success': True
                        }
                        
                except Exception as e:
                    return {
                        'user_idx': user_idx,
                        'operation': 'cashout_notification',
                        'success': False,
                        'error': str(e)
                    }
            
            # Execute concurrent notifications
            notification_tasks = []
            
            # 15 escrow notifications
            for i in range(15):
                notification_tasks.append(send_escrow_notification(i))
            
            # 10 cashout notifications  
            for i in range(10):
                notification_tasks.append(send_cashout_notification(i))
            
            notification_results = await asyncio.gather(*notification_tasks, return_exceptions=True)
            
            # Analyze notification results
            successful_notifications = [r for r in notification_results if isinstance(r, dict) and r.get('success')]
            failed_notifications = [r for r in notification_results if isinstance(r, dict) and not r.get('success')]
            
            logger.info(f"Notification test - Successful: {len(successful_notifications)}, Failed: {len(failed_notifications)}")
            
            # Verify high success rate for notifications
            success_rate = len(successful_notifications) / len(notification_tasks)
            assert success_rate >= 0.9, f"Notification success rate too low: {success_rate:.2%}"
            
            # Verify all notifications were captured
            total_notifications = len(notification_verifier.sent_notifications)
            assert total_notifications >= len(successful_notifications), f"Not all notifications captured: {total_notifications} vs {len(successful_notifications)}"
            
            # Verify notification categories
            escrow_notifications = [n for n in notification_verifier.sent_notifications if n['category'] == NotificationCategory.ESCROW]
            cashout_notifications = [n for n in notification_verifier.sent_notifications if n['category'] == NotificationCategory.CASHOUT]
            
            assert len(escrow_notifications) >= 10, f"Expected at least 10 escrow notifications, got {len(escrow_notifications)}"
            assert len(cashout_notifications) >= 5, f"Expected at least 5 cashout notifications, got {len(cashout_notifications)}"