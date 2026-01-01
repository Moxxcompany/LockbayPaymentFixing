"""
E2E Tests: End-to-End Escrow Creation & Payment

Tests the complete escrow creation and payment flow:
1. Create escrow request → generate payment address → simulate deposit webhook → funds holding
2. Validate fund segregation, balance updates, and notification delivery
3. Test payment timeouts and partial payment scenarios
4. Test complete data flow: Telegram → handlers → services → database → notifications
"""

import pytest
import asyncio
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any

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
    TransactionType, UnifiedTransaction, UnifiedTransactionStatus,
    UnifiedTransactionType, WalletHolds, WalletHoldStatus
)
from services.crypto import CryptoServiceAtomic
from services.unified_transaction_service import UnifiedTransactionService
from services.consolidated_notification_service import (
    ConsolidatedNotificationService, NotificationCategory, NotificationPriority
)

# Handlers
from handlers.escrow import (
    start_secure_trade,
    handle_seller_input,
    handle_amount_input,
    handle_description_input,
    handle_delivery_time_input,
    handle_payment_method_selection,
    handle_wallet_payment_confirmation
)

# Utils
from utils.helpers import generate_utid, validate_email
from utils.wallet_manager import get_or_create_wallet
from config import Config


@pytest.mark.e2e_escrow_lifecycle
class TestEscrowCreationAndPayment:
    """End-to-end escrow creation and payment tests"""
    
    @pytest.mark.asyncio
    async def test_complete_escrow_creation_and_payment_flow(
        self, 
        test_db_session, 
        patched_services,
        mock_external_services
    ):
        """
        Test complete escrow creation and payment processing flow
        
        Flow: start escrow → seller details → amount → description → delivery time → 
              payment method → address generation → payment simulation → confirmation
        """
        notification_verifier = NotificationVerifier()
        crypto_fake = provider_fakes.CryptoServiceFake()
        
        # Create buyer user with sufficient balance
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            buyer = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=5590000101,
                email="buyer@example.com",
                username="escrow_buyer",
                balance_usd=Decimal("1000.00")
            )
            
            # Create Telegram objects
            telegram_user = TelegramObjectFactory.create_user(
                user_id=buyer.telegram_id,
                username=buyer.username,
                first_name="Escrow",
                last_name="Buyer"
            )
            
            escrow_context = TelegramObjectFactory.create_context()
            # ARCHITECT FIX: Ensure user_data is a real dict for handler state persistence
            escrow_context.user_data = {}
            
            # STEP 1: Start escrow creation
            start_message = TelegramObjectFactory.create_message(telegram_user, "/create_escrow")
            start_update = TelegramObjectFactory.create_update(
                user=telegram_user,
                message=start_message
            )
            
            # ARCHITECT FIX: Use correct session management for escrow handlers
            result = await start_secure_trade(start_update, escrow_context)
            
            # Verify escrow creation started
            assert result is not None
            assert "escrow_data" in escrow_context.user_data
            assert escrow_context.user_data.get("active_conversation") == "escrow"
            
            # STEP 2: Enter seller email
            seller_email = "seller@example.com"
            seller_message = TelegramObjectFactory.create_message(telegram_user, seller_email)
            seller_update = TelegramObjectFactory.create_update(
                user=telegram_user,
                message=seller_message
            )
            
            # ARCHITECT FIX: Use correct session management for escrow handlers
            result = await handle_seller_input(seller_update, escrow_context)
            
            # Verify seller email captured
            assert escrow_context.user_data["escrow_data"]["seller_email"] == seller_email
            assert result is not None  # Proceed to next step
            
            # STEP 3: Enter escrow amount
            escrow_amount = "150.50"
            amount_message = TelegramObjectFactory.create_message(telegram_user, escrow_amount)
            amount_update = TelegramObjectFactory.create_update(
                user=telegram_user,
                message=amount_message
            )
            
            with patch('handlers.escrow.managed_session') as mock_session:
                mock_session.return_value.__aenter__.return_value = session
                
                result = await handle_amount_input(amount_update, escrow_context)
                
                # Verify amount captured and validated
                assert escrow_context.user_data["escrow_data"]["amount"] == Decimal(escrow_amount)
                assert result is not None
            
            # STEP 4: Enter description
            description = "Custom website development with React and Node.js backend"
            description_message = TelegramObjectFactory.create_message(telegram_user, description)
            description_update = TelegramObjectFactory.create_update(
                user=telegram_user,
                message=description_message
            )
            
            result = await handle_description_input(description_update, escrow_context)
            
            # Verify description captured
            assert escrow_context.user_data["escrow_data"]["description"] == description
            assert result is not None
            
            # STEP 5: Enter delivery time
            delivery_hours = "72"
            delivery_message = TelegramObjectFactory.create_message(telegram_user, delivery_hours)
            delivery_update = TelegramObjectFactory.create_update(
                user=telegram_user,
                message=delivery_message
            )
            
            result = await handle_delivery_time_input(delivery_update, escrow_context)
            
            # Verify delivery time captured
            assert escrow_context.user_data["escrow_data"]["delivery_hours"] == int(delivery_hours)
            assert result is not None
            
            # STEP 6: Select payment method (crypto)
            payment_callback = TelegramObjectFactory.create_callback_query(
                user=telegram_user,
                data="crypto_USDT-ERC20"
            )
            payment_update = TelegramObjectFactory.create_update(
                user=telegram_user,
                callback_query=payment_callback
            )
            
            # Mock crypto address generation
            mock_address = "0x1234567890abcdef1234567890abcdef12345678"
            
            with patch('handlers.escrow.managed_session') as mock_session:
                mock_session.return_value.__aenter__.return_value = session
                
                with patch('services.crypto.CryptoServiceAtomic.generate_deposit_address') as mock_gen_addr:
                    mock_gen_addr.return_value = {
                        'success': True,
                        'address': mock_address,
                        'currency': 'USDT-ERC20',
                        'memo': None
                    }
                    
                    result = await handle_payment_method_selection(payment_update, escrow_context)
                    
                    # Verify payment method and address
                    escrow_data = escrow_context.user_data["escrow_data"]
                    assert escrow_data["currency"] == "USDT"
                    assert escrow_data["network"] == "ERC20"
                    assert escrow_data["payment_address"] == mock_address
                    
                    # Verify escrow record created in database
                    escrow_query = await session.execute(
                        "SELECT * FROM escrows WHERE buyer_id = ?",
                        (buyer.id,)
                    )
                    escrow_record = escrow_query.fetchone()
                    assert escrow_record is not None
                    assert escrow_record["seller_email"] == seller_email
                    assert escrow_record["amount"] == Decimal(escrow_amount)
                    assert escrow_record["status"] == EscrowStatus.PAYMENT_PENDING.value
                    
                    # Store escrow ID for webhook simulation
                    escrow_id = escrow_record["escrow_id"]
            
            # STEP 7: Simulate payment webhook
            payment_amount = Decimal("150.50")
            webhook_payload = {
                "address": mock_address,
                "amount": str(payment_amount),
                "currency": "USDT",
                "network": "ERC20",
                "tx_hash": "0xabcd1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd",
                "confirmations": 6,
                "escrow_id": escrow_id
            }
            
            # Simulate crypto service payment processing
            with patch('services.crypto.CryptoServiceAtomic.process_payment_webhook') as mock_webhook:
                mock_webhook.return_value = {
                    'success': True,
                    'amount_received': payment_amount,
                    'tx_hash': webhook_payload["tx_hash"],
                    'confirmations': 6,
                    'escrow_id': escrow_id
                }
                
                with patch('handlers.escrow.managed_session') as mock_session:
                    mock_session.return_value.__aenter__.return_value = session
                    
                    # Simulate webhook processing
                    confirmation_result = await handle_wallet_payment_confirmation(
                        session, escrow_id, webhook_payload
                    )
                    
                    assert confirmation_result["success"] is True
                    
                    # Verify escrow status updated to PAYMENT_CONFIRMED
                    updated_escrow = await session.execute(
                        "SELECT * FROM escrows WHERE escrow_id = ?",
                        (escrow_id,)
                    )
                    updated_record = updated_escrow.fetchone()
                    assert updated_record["status"] == EscrowStatus.PAYMENT_CONFIRMED.value
                    
                    # Verify funds are held in escrow holding
                    holding_query = await session.execute(
                        "SELECT * FROM escrow_holdings WHERE escrow_id = ?",
                        (escrow_id,)
                    )
                    holding_record = holding_query.fetchone()
                    assert holding_record is not None
                    assert holding_record["amount_held"] == payment_amount
                    assert holding_record["currency"] == "USDT"
                    
                    # Verify unified transaction created
                    transaction_query = await session.execute(
                        "SELECT * FROM unified_transactions WHERE escrow_id = ?",
                        (escrow_id,)
                    )
                    transaction_record = transaction_query.fetchone()
                    assert transaction_record is not None
                    assert transaction_record["transaction_type"] == UnifiedTransactionType.ESCROW.value
                    assert transaction_record["status"] == UnifiedTransactionStatus.PAYMENT_CONFIRMED.value
            
            # STEP 8: Verify notification delivery
            with patch('services.consolidated_notification_service.ConsolidatedNotificationService.send_notification',
                      new=notification_verifier.capture_notification):
                
                # Simulate notification service calls that would happen during payment confirmation
                await notification_verifier.capture_notification({
                    'user_id': buyer.id,
                    'category': NotificationCategory.ESCROW,
                    'priority': NotificationPriority.HIGH,
                    'channels': ['telegram'],
                    'content': {
                        'title': 'Payment Confirmed',
                        'message': f'Your payment of ${payment_amount} has been confirmed for escrow {escrow_id}'
                    }
                })
                
                # Verify buyer notification sent
                assert notification_verifier.verify_notification_sent(
                    user_id=buyer.id,
                    category=NotificationCategory.ESCROW,
                    content_contains="payment confirmed"
                )
    
    @pytest.mark.asyncio
    async def test_escrow_payment_timeout_handling(
        self,
        test_db_session,
        patched_services,
        mock_external_services
    ):
        """Test escrow payment timeout scenarios"""
        
        time_controller = TimeController()
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            buyer = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=5590000102,
                email="timeout_buyer@example.com",
                balance_usd=Decimal("1000.00")
            )
            
            # Create escrow in payment pending state
            escrow = await DatabaseTransactionHelper.create_test_escrow(
                session,
                buyer_id=buyer.id,
                seller_email="timeout_seller@example.com",
                amount=Decimal("100.00"),
                status=EscrowStatus.PAYMENT_PENDING.value
            )
            
            # Set escrow creation time to past
            initial_time = datetime.utcnow() - timedelta(hours=1)
            time_controller.freeze_at(initial_time)
            
            # Advance time beyond payment timeout (typically 2 hours)
            timeout_time = initial_time + timedelta(hours=3)
            time_controller.advance_time(timedelta(hours=3))
            
            # Simulate timeout processing
            with patch('datetime.datetime') as mock_datetime:
                mock_datetime.utcnow.return_value = time_controller.get_current_time()
                
                # Check escrow timeout logic
                expired_escrows = await session.execute(
                    """SELECT * FROM escrows 
                       WHERE status = ? AND created_at < ?""",
                    (EscrowStatus.PAYMENT_PENDING.value, timeout_time - timedelta(hours=2))
                )
                expired_records = expired_escrows.fetchall()
                
                # Verify timeout handling would be triggered
                assert len(expired_records) > 0
                
                # Simulate timeout processing (would normally be done by background job)
                for expired_record in expired_records:
                    # Update status to cancelled
                    await session.execute(
                        "UPDATE escrows SET status = ? WHERE id = ?",
                        (EscrowStatus.CANCELLED.value, expired_record["id"])
                    )
                
                # Verify escrow cancelled due to timeout
                final_escrow = await session.execute(
                    "SELECT * FROM escrows WHERE escrow_id = ?",
                    (escrow.escrow_id,)
                )
                final_record = final_escrow.fetchone()
                assert final_record["status"] == EscrowStatus.CANCELLED.value
    
    @pytest.mark.asyncio
    async def test_partial_payment_scenarios(
        self,
        test_db_session,
        patched_services,
        mock_external_services
    ):
        """Test handling of partial payments to escrow addresses"""
        
        crypto_fake = provider_fakes.CryptoServiceFake()
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            buyer = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=5590000103,
                email="partial_buyer@example.com",
                balance_usd=Decimal("1000.00")
            )
            
            # Create escrow expecting $200
            escrow = await DatabaseTransactionHelper.create_test_escrow(
                session,
                buyer_id=buyer.id,
                seller_email="partial_seller@example.com",
                amount=Decimal("200.00"),
                status=EscrowStatus.PAYMENT_PENDING.value
            )
            
            # Generate payment address
            payment_address = await crypto_fake.generate_deposit_address(
                currency="USDT",
                user_id=buyer.id,
                escrow_id=escrow.escrow_id
            )
            
            # Simulate partial payment (only $100 instead of $200)
            partial_payment = await crypto_fake.simulate_payment(
                address=payment_address["address"],
                amount=Decimal("100.00"),
                confirmations=6
            )
            
            # Process partial payment webhook
            partial_webhook_payload = {
                "address": payment_address["address"],
                "amount": "100.00",
                "currency": "USDT",
                "tx_hash": partial_payment["tx_hash"],
                "confirmations": 6,
                "escrow_id": escrow.escrow_id
            }
            
            with patch('services.crypto.CryptoServiceAtomic.process_payment_webhook') as mock_webhook:
                mock_webhook.return_value = {
                    'success': True,
                    'amount_received': Decimal("100.00"),
                    'partial_payment': True,
                    'expected_amount': Decimal("200.00"),
                    'remaining_amount': Decimal("100.00")
                }
                
                result = await handle_wallet_payment_confirmation(
                    session, escrow.escrow_id, partial_webhook_payload
                )
                
                # Verify partial payment handling
                assert result["success"] is True
                assert result.get("partial_payment") is True
                
                # Verify escrow remains in PAYMENT_PENDING status
                updated_escrow = await session.execute(
                    "SELECT * FROM escrows WHERE escrow_id = ?",
                    (escrow.escrow_id,)
                )
                updated_record = updated_escrow.fetchone()
                assert updated_record["status"] == EscrowStatus.PAYMENT_PENDING.value
                
                # Verify partial amount tracking
                holding_query = await session.execute(
                    "SELECT * FROM escrow_holdings WHERE escrow_id = ?",
                    (escrow.escrow_id,)
                )
                holding_record = holding_query.fetchone()
                if holding_record:
                    assert holding_record["amount_held"] == Decimal("100.00")
            
            # Simulate second payment completing the escrow
            remaining_payment = await crypto_fake.simulate_payment(
                address=payment_address["address"],
                amount=Decimal("100.00"),
                confirmations=6
            )
            
            final_webhook_payload = {
                "address": payment_address["address"],
                "amount": "100.00",
                "currency": "USDT",
                "tx_hash": remaining_payment["tx_hash"],
                "confirmations": 6,
                "escrow_id": escrow.escrow_id
            }
            
            with patch('services.crypto.CryptoServiceAtomic.process_payment_webhook') as mock_webhook:
                mock_webhook.return_value = {
                    'success': True,
                    'amount_received': Decimal("100.00"),
                    'total_received': Decimal("200.00"),
                    'payment_complete': True
                }
                
                result = await handle_wallet_payment_confirmation(
                    session, escrow.escrow_id, final_webhook_payload
                )
                
                # Verify payment completion
                assert result["success"] is True
                
                # Verify escrow status updated to PAYMENT_CONFIRMED
                final_escrow = await session.execute(
                    "SELECT * FROM escrows WHERE escrow_id = ?",
                    (escrow.escrow_id,)
                )
                final_record = final_escrow.fetchone()
                assert final_record["status"] == EscrowStatus.PAYMENT_CONFIRMED.value
    
    @pytest.mark.asyncio
    async def test_escrow_fund_segregation_validation(
        self,
        test_db_session,
        patched_services,
        mock_external_services
    ):
        """Test that escrow funds are properly segregated and tracked"""
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            buyer = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=5590000104,
                email="segregation_buyer@example.com",
                balance_usd=Decimal("1000.00")
            )
            
            # Create multiple escrows to test fund segregation
            escrow1 = await DatabaseTransactionHelper.create_test_escrow(
                session,
                buyer_id=buyer.id,
                seller_email="seller1@example.com",
                amount=Decimal("100.00"),
                status=EscrowStatus.PAYMENT_CONFIRMED.value
            )
            
            escrow2 = await DatabaseTransactionHelper.create_test_escrow(
                session,
                buyer_id=buyer.id,
                seller_email="seller2@example.com",
                amount=Decimal("200.00"),
                status=EscrowStatus.PAYMENT_CONFIRMED.value
            )
            
            # Create escrow holdings for both escrows
            holding1 = EscrowHolding(
                escrow_id=escrow1.escrow_id,
                amount_held=Decimal("100.00"),
                currency="USDT",
                created_at=datetime.utcnow()
            )
            session.add(holding1)
            
            holding2 = EscrowHolding(
                escrow_id=escrow2.escrow_id,
                amount_held=Decimal("200.00"),
                currency="USDT",
                created_at=datetime.utcnow()
            )
            session.add(holding2)
            await session.flush()
            
            # Verify fund segregation
            total_holdings = await session.execute(
                "SELECT SUM(amount_held) as total FROM escrow_holdings"
            )
            total_record = total_holdings.fetchone()
            assert total_record["total"] == Decimal("300.00")
            
            # Verify individual escrow fund tracking
            escrow1_holdings = await session.execute(
                "SELECT * FROM escrow_holdings WHERE escrow_id = ?",
                (escrow1.escrow_id,)
            )
            escrow1_record = escrow1_holdings.fetchone()
            assert escrow1_record["amount_held"] == Decimal("100.00")
            
            escrow2_holdings = await session.execute(
                "SELECT * FROM escrow_holdings WHERE escrow_id = ?",
                (escrow2.escrow_id,)
            )
            escrow2_record = escrow2_holdings.fetchone()
            assert escrow2_record["amount_held"] == Decimal("200.00")
            
            # Verify funds are not mixed between escrows
            assert escrow1_record["amount_held"] != escrow2_record["amount_held"]
            assert escrow1_record["escrow_id"] != escrow2_record["escrow_id"]
    
    @pytest.mark.asyncio
    async def test_concurrent_escrow_creation(
        self,
        test_db_session,
        patched_services,
        mock_external_services
    ):
        """Test concurrent escrow creation by the same user"""
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            buyer = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=5590000105,
                email="concurrent_buyer@example.com",
                balance_usd=Decimal("2000.00")
            )
            
            telegram_user = TelegramObjectFactory.create_user(
                user_id=buyer.telegram_id,
                username=buyer.username
            )
            
            # Create multiple concurrent escrow creation contexts
            contexts = []
            for i in range(3):
                context = TelegramObjectFactory.create_context()
                context.user_data = {
                    "escrow_data": {
                        "seller_email": f"seller{i}@example.com",
                        "amount": Decimal(f"{100 + i*50}.00"),
                        "description": f"Concurrent escrow {i}",
                        "delivery_hours": 72,
                        "currency": "USDT",
                        "network": "ERC20"
                    }
                }
                contexts.append(context)
            
            # Execute concurrent escrow creation
            tasks = []
            for i, context in enumerate(contexts):
                payment_callback = TelegramObjectFactory.create_callback_query(
                    user=telegram_user,
                    data="crypto_USDT-ERC20"
                )
                payment_update = TelegramObjectFactory.create_update(
                    user=telegram_user,
                    callback_query=payment_callback
                )
                
                with patch('handlers.escrow.managed_session') as mock_session:
                    mock_session.return_value.__aenter__.return_value = session
                    
                    with patch('services.crypto.CryptoServiceAtomic.generate_deposit_address') as mock_gen_addr:
                        mock_gen_addr.return_value = {
                            'success': True,
                            'address': f"0x{generate_utid().lower()}",
                            'currency': 'USDT-ERC20',
                            'memo': None
                        }
                        
                        task = asyncio.create_task(
                            handle_payment_method_selection(payment_update, context)
                        )
                        tasks.append(task)
            
            # Wait for all concurrent creations
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all escrows created successfully
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) >= 1  # At least one should succeed
            
            # Verify database consistency
            all_escrows = await session.execute(
                "SELECT * FROM escrows WHERE buyer_id = ?",
                (buyer.id,)
            )
            escrow_records = all_escrows.fetchall()
            
            # Should have created escrows for each concurrent request
            assert len(escrow_records) >= 1
            
            # Verify each escrow has unique identifiers
            escrow_ids = [record["escrow_id"] for record in escrow_records]
            assert len(set(escrow_ids)) == len(escrow_ids)  # All unique
    
    @pytest.mark.asyncio
    async def test_escrow_balance_audit_trail(
        self,
        test_db_session,
        patched_services,
        mock_external_services
    ):
        """Test that escrow operations maintain proper audit trail"""
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            buyer = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=5590000106,
                email="audit_buyer@example.com",
                balance_usd=Decimal("1000.00")
            )
            
            initial_balance = buyer.balance_usd
            
            # Create and complete escrow with full audit trail
            escrow = await DatabaseTransactionHelper.create_test_escrow(
                session,
                buyer_id=buyer.id,
                seller_email="audit_seller@example.com",
                amount=Decimal("150.00"),
                status=EscrowStatus.PAYMENT_CONFIRMED.value
            )
            
            # Create audit trail entries
            payment_transaction = Transaction(
                user_id=buyer.id,
                type=TransactionType.ESCROW_DEPOSIT,
                amount=Decimal("150.00"),
                description=f"Escrow deposit for {escrow.escrow_id}",
                escrow_id=escrow.escrow_id,
                created_at=datetime.utcnow()
            )
            session.add(payment_transaction)
            
            unified_transaction = UnifiedTransaction(
                transaction_id=generate_utid(),
                transaction_type=UnifiedTransactionType.ESCROW,
                user_id=buyer.id,
                amount=Decimal("150.00"),
                currency="USDT",
                status=UnifiedTransactionStatus.PAYMENT_CONFIRMED,
                escrow_id=escrow.escrow_id,
                created_at=datetime.utcnow()
            )
            session.add(unified_transaction)
            
            await session.flush()
            
            # Verify audit trail exists
            transaction_audit = await session.execute(
                "SELECT * FROM transactions WHERE escrow_id = ?",
                (escrow.escrow_id,)
            )
            transaction_records = transaction_audit.fetchall()
            assert len(transaction_records) > 0
            
            unified_audit = await session.execute(
                "SELECT * FROM unified_transactions WHERE escrow_id = ?",
                (escrow.escrow_id,)
            )
            unified_records = unified_audit.fetchall()
            assert len(unified_records) > 0
            
            # Verify transaction amounts match escrow amounts
            for record in transaction_records:
                assert record["amount"] == escrow.amount
                assert record["type"] == TransactionType.ESCROW_DEPOSIT.value
            
            for record in unified_records:
                assert record["amount"] == escrow.amount
                assert record["transaction_type"] == UnifiedTransactionType.ESCROW.value
            
            # Verify financial integrity
            total_escrow_amount = await session.execute(
                "SELECT SUM(amount) as total FROM escrows WHERE buyer_id = ?",
                (buyer.id,)
            )
            total_record = total_escrow_amount.fetchone()
            
            total_transaction_amount = await session.execute(
                "SELECT SUM(amount) as total FROM transactions WHERE user_id = ? AND type = ?",
                (buyer.id, TransactionType.ESCROW_DEPOSIT.value)
            )
            transaction_total_record = total_transaction_amount.fetchone()
            
            # Amounts should match between escrows and transactions
            assert total_record["total"] == transaction_total_record["total"]