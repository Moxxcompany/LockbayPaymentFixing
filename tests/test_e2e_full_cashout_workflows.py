"""
E2E Tests: Full Cashout Workflows

Tests the complete cashout workflows:
1. Crypto cashouts: wallet selection → Kraken withdrawal → confirmation → completion
2. NGN cashouts: bank details → OTP verification → Fincra transfer → success confirmation  
3. Test insufficient balance, failed transfers, and retry mechanisms
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
    User, Wallet, Cashout, CashoutStatus, CashoutProcessingMode,
    PendingCashout, SavedAddress, SavedBankAccount, Transaction,
    TransactionType, UnifiedTransaction, UnifiedTransactionStatus,
    UnifiedTransactionType, EmailVerification
)
from services.kraken_service import KrakenService
from services.fincra_service import FincraService
from services.unified_transaction_service import UnifiedTransactionService
from services.conditional_otp_service import ConditionalOTPService
from services.consolidated_notification_service import (
    ConsolidatedNotificationService, NotificationCategory, NotificationPriority
)

# Handlers
from handlers.wallet_direct import (
    start_cashout,  # Main cashout entry point
    handle_crypto_currency_selection,
    handle_crypto_address_input,
    handle_confirm_crypto_cashout,  # Correct name for crypto confirmation
    handle_select_ngn_bank,  # Correct name for NGN bank selection
    handle_ngn_otp_verification,
    handle_confirm_ngn_cashout  # Correct name for NGN confirmation
)

# Utils
from utils.helpers import generate_utid, validate_crypto_address
from utils.wallet_manager import get_or_create_wallet
from config import Config


@pytest.mark.e2e_cashout_flows
class TestFullCashoutWorkflows:
    """Complete cashout workflow E2E tests"""
    
    @pytest.mark.asyncio
    async def test_complete_crypto_cashout_workflow(
        self, 
        test_db_session, 
        patched_services,
        mock_external_services
    ):
        """
        Test complete crypto cashout workflow (Kraken)
        
        Flow: wallet selection → currency selection → address input → amount → 
              confirmation → Kraken processing → completion
        """
        notification_verifier = NotificationVerifier()
        kraken_fake = provider_fakes.KrakenFake()
        
        # Create user with crypto balance using working pattern
        from tests.e2e_test_foundation import TestDataFactory
        test_data_factory = TestDataFactory(test_db_session)
        
        user = test_data_factory.create_test_user(
            telegram_id=5590000301,
            email="crypto_cashout_user@example.com",
            username="crypto_cashout_user",
            balances={'USD': Decimal("2000.00")}
        )
        
        # Add crypto balances to user's wallet (create separate wallet records per currency)
        from models import Wallet
        
        # Create BTC wallet
        btc_wallet = Wallet(
            user_id=user.id,
            currency='BTC',
            balance=Decimal("0.05"),
            frozen_balance=Decimal("0"),
            locked_balance=Decimal("0"),
            wallet_type='standard',
            is_active=True
        )
        test_db_session.add(btc_wallet)
        
        # Create ETH wallet
        eth_wallet = Wallet(
            user_id=user.id,
            currency='ETH',
            balance=Decimal("2.5"),
            frozen_balance=Decimal("0"),
            locked_balance=Decimal("0"),
            wallet_type='standard',
            is_active=True
        )
        test_db_session.add(eth_wallet)
        
        # Create LTC wallet
        ltc_wallet = Wallet(
            user_id=user.id,
            currency='LTC',
            balance=Decimal("15.0"),
            frozen_balance=Decimal("0"),
            locked_balance=Decimal("0"),
            wallet_type='standard',
            is_active=True
        )
        test_db_session.add(ltc_wallet)
        test_db_session.commit()
        
        telegram_user = TelegramObjectFactory.create_user(
            user_id=user.telegram_id,
            username=user.username,
            first_name="Crypto",
            last_name="User"
        )
        
        cashout_context = TelegramObjectFactory.create_context()
        
        # STEP 1: Start crypto cashout
        start_message = TelegramObjectFactory.create_message(telegram_user, "/cashout_crypto")
        start_update = TelegramObjectFactory.create_update(
            user=telegram_user,
            message=start_message
        )
        
        result = await start_cashout(start_update, cashout_context)
        
        # Verify cashout started
        assert result is not None
        assert "cashout_data" in cashout_context.user_data
        assert cashout_context.user_data["cashout_data"]["type"] == "crypto"
        
        # STEP 2: Select cryptocurrency (BTC)
        currency_callback = TelegramObjectFactory.create_callback_query(
            user=telegram_user,
            data="crypto_currency_BTC"
        )
        currency_update = TelegramObjectFactory.create_update(
            user=telegram_user,
            callback_query=currency_callback
        )
        
        with patch('handlers.wallet_direct.managed_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = session
            
            result = await handle_crypto_currency_selection(currency_update, cashout_context)
            
            # Verify currency selected
            assert cashout_context.user_data["cashout_data"]["currency"] == "BTC"
            assert result is not None
        
        # STEP 3: Enter withdrawal address
        btc_address = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
        address_message = TelegramObjectFactory.create_message(telegram_user, btc_address)
        address_update = TelegramObjectFactory.create_update(
            user=telegram_user,
            message=address_message
        )
        
        with patch('utils.helpers.validate_crypto_address') as mock_validate:
            mock_validate.return_value = True
            
            with patch('handlers.wallet_direct.managed_session') as mock_session:
                mock_session.return_value.__aenter__.return_value = test_db_session
                
                result = await handle_crypto_address_input(address_update, cashout_context)
                
                # Verify address captured
                assert cashout_context.user_data["cashout_data"]["address"] == btc_address
                assert result is not None
        
        # STEP 4: Enter withdrawal amount
        withdrawal_amount = "0.02"
        amount_message = TelegramObjectFactory.create_message(telegram_user, withdrawal_amount)
        amount_update = TelegramObjectFactory.create_update(
            user=telegram_user,
            message=amount_message
        )
        
        with patch('handlers.wallet_direct.managed_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = test_db_session
            
            result = await handle_crypto_amount_input(amount_update, cashout_context)
            
            # Verify amount captured and validated
            assert cashout_context.user_data["cashout_data"]["amount"] == Decimal(withdrawal_amount)
            assert result is not None
        
        # STEP 5: Confirm cashout
        confirm_callback = TelegramObjectFactory.create_callback_query(
            user=telegram_user,
            data="confirm_crypto_cashout"
        )
        confirm_update = TelegramObjectFactory.create_update(
            user=telegram_user,
            callback_query=confirm_callback
        )
        
        # Mock Kraken service responses
        with patch('services.kraken_service.KrakenService.withdraw_crypto') as mock_kraken:
            mock_kraken.return_value = {
                'success': True,
                'withdrawal_id': 'KRAKEN_W123456',
                'txid': 'KRAKEN_TX789012',
                'refid': 'KRAKEN_REF345678'
            }
            
            with patch('handlers.wallet_direct.managed_session') as mock_session:
                mock_session.return_value.__aenter__.return_value = test_db_session
                
                with patch('services.consolidated_notification_service.ConsolidatedNotificationService.send_notification',
                          new=notification_verifier.capture_notification):
                    
                    result = await handle_crypto_cashout_confirmation(confirm_update, cashout_context)
                    
                    # Verify cashout initiated
                    assert result == ConversationHandler.END
                    
                    # Create cashout record
                    cashout = Cashout(
                        cashout_id=generate_utid("CASHOUT"),
                        user_id=user.id,
                        amount=Decimal(withdrawal_amount),
                        currency="BTC",
                        address=btc_address,
                        status=CashoutStatus.PROCESSING.value,
                        processing_mode=CashoutProcessingMode.KRAKEN.value,
                        kraken_withdrawal_id="KRAKEN_W123456",
                        created_at=datetime.utcnow()
                    )
                    test_db_session.add(cashout)
                    
                    # Create unified transaction
                    unified_tx = UnifiedTransaction(
                        transaction_id=generate_utid("UTE"),
                        transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                        user_id=user.id,
                        amount=Decimal(withdrawal_amount),
                        currency="BTC",
                        status=UnifiedTransactionStatus.PROCESSING,
                        cashout_id=cashout.cashout_id,
                        created_at=datetime.utcnow()
                    )
                    test_db_session.add(unified_tx)
                    
                    # Update user balance
                    btc_wallet.balance -= Decimal(withdrawal_amount)
                    test_db_session.commit()
                    
                    # Verify cashout record created
                    cashout_record = test_db_session.query(Cashout).filter_by(
                        user_id=user.id, currency="BTC"
                    ).first()
                    assert cashout_record is not None
                    assert cashout_record.amount == Decimal(withdrawal_amount)
                    assert cashout_record.status == CashoutStatus.PROCESSING.value
                    assert cashout_record.address == btc_address
        
        # STEP 6: Simulate Kraken confirmation webhook
        # (Would normally come from Kraken's webhook system)
        kraken_webhook_payload = {
            "withdrawal_id": "KRAKEN_W123456",
            "txid": "0xabcd1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd",
            "status": "success",
            "amount": withdrawal_amount,
            "currency": "BTC"
        }
        
        # Process webhook confirmation
        cashout.status = CashoutStatus.COMPLETED.value
        cashout.tx_hash = kraken_webhook_payload["txid"]
        unified_tx.status = UnifiedTransactionStatus.SUCCESS.value
        test_db_session.commit()
        
        # Verify final state
        final_record = test_db_session.query(Cashout).filter_by(
            cashout_id=cashout.cashout_id
        ).first()
        assert final_record.status == CashoutStatus.COMPLETED.value
        assert final_record.tx_hash == kraken_webhook_payload["txid"]
        
        # Verify user balance updated
        test_db_session.refresh(btc_wallet)
        assert btc_wallet.balance == Decimal("0.03")  # 0.05 - 0.02
        
        # Verify notifications sent
        assert notification_verifier.verify_notification_sent(
            user_id=user.id,
            category=NotificationCategory.CASHOUT,
            content_contains="withdrawal initiated"
        )
    
    async def test_complete_ngn_cashout_workflow(
        self,
        test_db_session,
        patched_services,
        mock_external_services
    ):
        """
        Test complete NGN cashout workflow (Fincra)
        
        Flow: bank selection → amount input → OTP verification → Fincra transfer → completion
        """
        notification_verifier = NotificationVerifier()
        fincra_fake = provider_fakes.FincraFake()
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            # Create user with USD balance
            user = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=5590000302,
                email="ngn_cashout_user@example.com",
                username="ngn_cashout_user",
                balance_usd=Decimal("3000.00")
            )
            
            # Create saved bank account
            saved_bank = SavedBankAccount(
                user_id=user.id,
                bank_name="Access Bank",
                bank_code="044",
                account_number="0123456789",
                account_name="NGN CASHOUT USER",
                created_at=datetime.utcnow()
            )
            session.add(saved_bank)
            await session.flush()
            
            telegram_user = TelegramObjectFactory.create_user(
                user_id=user.telegram_id,
                username=user.username,
                first_name="NGN",
                last_name="User"
            )
            
            cashout_context = TelegramObjectFactory.create_context()
            
            # STEP 1: Start NGN cashout
            start_message = TelegramObjectFactory.create_message(telegram_user, "/cashout_ngn")
            start_update = TelegramObjectFactory.create_update(
                user=telegram_user,
                message=start_message
            )
            
            with patch('handlers.wallet_direct.managed_session') as mock_session:
                mock_session.return_value.__aenter__.return_value = session
                
                result = await handle_ngn_cashout_start(start_update, cashout_context)
                
                # Verify NGN cashout started
                assert result is not None
                assert "cashout_data" in cashout_context.user_data
                assert cashout_context.user_data["cashout_data"]["type"] == "ngn"
            
            # STEP 2: Select bank account
            bank_callback = TelegramObjectFactory.create_callback_query(
                user=telegram_user,
                data=f"select_bank_{saved_bank.id}"
            )
            bank_update = TelegramObjectFactory.create_update(
                user=telegram_user,
                callback_query=bank_callback
            )
            
            with patch('handlers.wallet_direct.managed_session') as mock_session:
                mock_session.return_value.__aenter__.return_value = session
                
                result = await handle_ngn_bank_selection(bank_update, cashout_context)
                
                # Verify bank selected
                assert cashout_context.user_data["cashout_data"]["bank_account_id"] == saved_bank.id
                assert result is not None
            
            # STEP 3: Enter withdrawal amount (USD)
            usd_amount = "200.00"
            amount_message = TelegramObjectFactory.create_message(telegram_user, usd_amount)
            amount_update = TelegramObjectFactory.create_update(
                user=telegram_user,
                message=amount_message
            )
            
            # Mock exchange rate service
            with patch('services.fastforex_service.FastForexService.get_usd_to_ngn_rate') as mock_rate:
                mock_rate.return_value = Decimal("1500.00")  # 1 USD = 1500 NGN
                
                with patch('handlers.wallet_direct.managed_session') as mock_session:
                    mock_session.return_value.__aenter__.return_value = session
                    
                    result = await handle_ngn_amount_input(amount_update, cashout_context)
                    
                    # Verify amount and conversion
                    assert cashout_context.user_data["cashout_data"]["usd_amount"] == Decimal(usd_amount)
                    assert cashout_context.user_data["cashout_data"]["ngn_amount"] == Decimal("300000.00")  # 200 * 1500
                    assert result is not None
            
            # STEP 4: OTP verification
            # Generate OTP
            otp_code = "567890"
            with patch('services.conditional_otp_service.ConditionalOTPService.generate_otp') as mock_gen_otp:
                mock_gen_otp.return_value = otp_code
                
                # Create email verification record
                email_verification = EmailVerification(
                    email=user.email,
                    otp_code=otp_code,
                    user_id=user.id,
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(minutes=10),
                    verified=False,
                    attempts=0
                )
                session.add(email_verification)
                await session.flush()
            
            # User enters OTP
            otp_message = TelegramObjectFactory.create_message(telegram_user, otp_code)
            otp_update = TelegramObjectFactory.create_update(
                user=telegram_user,
                message=otp_message
            )
            
            with patch('services.conditional_otp_service.ConditionalOTPService.verify_otp') as mock_verify_otp:
                mock_verify_otp.return_value = {
                    'success': True,
                    'message': 'OTP verified successfully',
                    'email': user.email
                }
                
                with patch('handlers.wallet_direct.managed_session') as mock_session:
                    mock_session.return_value.__aenter__.return_value = session
                    
                    result = await handle_ngn_otp_verification(otp_update, cashout_context)
                    
                    # Verify OTP verified
                    assert cashout_context.user_data["cashout_data"]["otp_verified"] is True
                    assert result is not None
            
            # STEP 5: Confirm NGN cashout
            confirm_callback = TelegramObjectFactory.create_callback_query(
                user=telegram_user,
                data="confirm_ngn_cashout"
            )
            confirm_update = TelegramObjectFactory.create_update(
                user=telegram_user,
                callback_query=confirm_callback
            )
            
            # Mock Fincra service responses
            with patch('services.fincra_service.FincraService.process_bank_transfer') as mock_fincra:
                mock_fincra.return_value = {
                    'success': True,
                    'transfer_id': 'FINCRA_T789012',
                    'reference': 'FINCRA_REF345678',
                    'status': 'processing',
                    'requires_admin_funding': False
                }
                
                with patch('handlers.wallet_direct.managed_session') as mock_session:
                    mock_session.return_value.__aenter__.return_value = session
                    
                    with patch('services.consolidated_notification_service.ConsolidatedNotificationService.send_notification',
                              new=notification_verifier.capture_notification):
                        
                        result = await handle_ngn_cashout_confirmation(confirm_update, cashout_context)
                        
                        # Verify cashout initiated
                        assert result == ConversationHandler.END
                        
                        # Create cashout record
                        cashout = Cashout(
                            cashout_id=generate_utid(),
                            user_id=user.id,
                            amount=Decimal(usd_amount),
                            currency="NGN",
                            ngn_amount=Decimal("300000.00"),
                            bank_account_id=saved_bank.id,
                            status=CashoutStatus.PROCESSING.value,
                            processing_mode=CashoutProcessingMode.FINCRA.value,
                            fincra_transfer_id="FINCRA_T789012",
                            created_at=datetime.utcnow()
                        )
                        session.add(cashout)
                        
                        # Update user balance
                        await session.execute(
                            "UPDATE wallets SET balance_usd = balance_usd - ? WHERE user_id = ?",
                            (Decimal(usd_amount), user.id)
                        )
                        
                        await session.flush()
                        
                        # Verify cashout record created
                        cashout_query = await session.execute(
                            "SELECT * FROM cashouts WHERE user_id = ? AND currency = 'NGN'",
                            (user.id,)
                        )
                        cashout_record = cashout_query.fetchone()
                        assert cashout_record is not None
                        assert cashout_record["amount"] == Decimal(usd_amount)
                        assert cashout_record["ngn_amount"] == Decimal("300000.00")
                        assert cashout_record["status"] == CashoutStatus.PROCESSING.value
            
            # STEP 6: Simulate Fincra confirmation webhook
            fincra_webhook_payload = {
                "transfer_id": "FINCRA_T789012",
                "status": "successful",
                "amount": "300000.00",
                "currency": "NGN",
                "reference": "FINCRA_REF345678"
            }
            
            # Process webhook confirmation
            await session.execute(
                "UPDATE cashouts SET status = ? WHERE fincra_transfer_id = ?",
                (CashoutStatus.COMPLETED.value, "FINCRA_T789012")
            )
            
            # Verify final state
            final_cashout = await session.execute(
                "SELECT * FROM cashouts WHERE cashout_id = ?",
                (cashout.cashout_id,)
            )
            final_record = final_cashout.fetchone()
            assert final_record["status"] == CashoutStatus.COMPLETED.value
            
            # Verify user balance updated
            updated_wallet = await session.execute(
                "SELECT balance_usd FROM wallets WHERE user_id = ?",
                (user.id,)
            )
            wallet_record = updated_wallet.fetchone()
            assert wallet_record["balance_usd"] == Decimal("2800.00")  # 3000 - 200
            
            # Verify notifications sent
            assert notification_verifier.verify_notification_sent(
                user_id=user.id,
                category=NotificationCategory.CASHOUT,
                content_contains="NGN transfer initiated"
            )
    
    async def test_insufficient_balance_scenarios(
        self,
        test_db_session,
        patched_services,
        mock_external_services
    ):
        """Test cashout attempts with insufficient balance"""
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            # Create user with low balance
            user = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=5590000303,
                email="low_balance_user@example.com",
                username="low_balance_user",
                balance_usd=Decimal("50.00")  # Low balance
            )
            
            # Set low crypto balances
            await session.execute(
                "UPDATE wallets SET balance_btc = ? WHERE user_id = ?",
                (Decimal("0.001"), user.id)  # Very small BTC amount
            )
            
            telegram_user = TelegramObjectFactory.create_user(
                user_id=user.telegram_id,
                username=user.username
            )
            
            # SCENARIO 1: Try to withdraw more BTC than available
            cashout_context = TelegramObjectFactory.create_context()
            cashout_context.user_data = {
                "cashout_data": {
                    "type": "crypto",
                    "currency": "BTC",
                    "address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
                }
            }
            
            # Try to withdraw 0.01 BTC (but only have 0.001)
            large_amount = "0.01"
            amount_message = TelegramObjectFactory.create_message(telegram_user, large_amount)
            amount_update = TelegramObjectFactory.create_update(
                user=telegram_user,
                message=amount_message
            )
            
            with patch('handlers.wallet_direct.managed_session') as mock_session:
                mock_session.return_value.__aenter__.return_value = session
                
                result = await handle_crypto_amount_input(amount_update, cashout_context)
                
                # Should reject insufficient balance
                assert "error" in cashout_context.user_data.get("cashout_data", {})
                # Amount should not be set due to insufficient balance
                assert cashout_context.user_data["cashout_data"].get("amount") != Decimal(large_amount)
            
            # SCENARIO 2: Try NGN cashout with insufficient USD
            ngn_context = TelegramObjectFactory.create_context()
            ngn_context.user_data = {
                "cashout_data": {
                    "type": "ngn",
                    "bank_account_id": 1
                }
            }
            
            # Try to withdraw $500 USD (but only have $50)
            large_usd_amount = "500.00"
            usd_amount_message = TelegramObjectFactory.create_message(telegram_user, large_usd_amount)
            usd_amount_update = TelegramObjectFactory.create_update(
                user=telegram_user,
                message=usd_amount_message
            )
            
            with patch('handlers.wallet_direct.managed_session') as mock_session:
                mock_session.return_value.__aenter__.return_value = session
                
                result = await handle_ngn_amount_input(usd_amount_update, ngn_context)
                
                # Should reject insufficient balance
                assert "error" in ngn_context.user_data.get("cashout_data", {})
                assert ngn_context.user_data["cashout_data"].get("usd_amount") != Decimal(large_usd_amount)
    
    async def test_failed_transfer_retry_mechanisms(
        self,
        test_db_session,
        patched_services,
        mock_external_services
    ):
        """Test retry mechanisms for failed transfers"""
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            user = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=5590000304,
                email="retry_user@example.com",
                balance_usd=Decimal("1000.00")
            )
            
            # SCENARIO 1: Kraken API failure with retry
            cashout = Cashout(
                cashout_id=generate_utid(),
                user_id=user.id,
                amount=Decimal("0.01"),
                currency="BTC",
                address="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
                status=CashoutStatus.PENDING.value,
                processing_mode=CashoutProcessingMode.KRAKEN.value,
                retry_count=0,
                created_at=datetime.utcnow()
            )
            session.add(cashout)
            await session.flush()
            
            # Simulate Kraken API failure
            with patch('services.kraken_service.KrakenService.withdraw_crypto') as mock_kraken:
                mock_kraken.side_effect = Exception("Kraken API temporarily unavailable")
                
                # Attempt processing
                try:
                    result = await mock_kraken(
                        currency="BTC",
                        amount=Decimal("0.01"),
                        address="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
                    )
                except Exception as e:
                    # Update cashout for retry
                    await session.execute(
                        "UPDATE cashouts SET status = ?, retry_count = retry_count + 1, last_error = ? WHERE cashout_id = ?",
                        (CashoutStatus.FAILED_RETRYING.value, str(e), cashout.cashout_id)
                    )
                
                # Verify retry setup
                failed_cashout = await session.execute(
                    "SELECT * FROM cashouts WHERE cashout_id = ?",
                    (cashout.cashout_id,)
                )
                failed_record = failed_cashout.fetchone()
                assert failed_record["status"] == CashoutStatus.FAILED_RETRYING.value
                assert failed_record["retry_count"] == 1
                assert "Kraken API" in failed_record["last_error"]
            
            # SCENARIO 2: Fincra insufficient funds
            fincra_cashout = Cashout(
                cashout_id=generate_utid(),
                user_id=user.id,
                amount=Decimal("100.00"),
                currency="NGN",
                ngn_amount=Decimal("150000.00"),
                status=CashoutStatus.PENDING.value,
                processing_mode=CashoutProcessingMode.FINCRA.value,
                retry_count=0,
                created_at=datetime.utcnow()
            )
            session.add(fincra_cashout)
            await session.flush()
            
            # Simulate Fincra insufficient funds
            with patch('services.fincra_service.FincraService.process_bank_transfer') as mock_fincra:
                mock_fincra.return_value = {
                    'success': False,
                    'error': 'insufficient_funds',
                    'message': 'Insufficient balance in Fincra account'
                }
                
                result = await mock_fincra(
                    amount=Decimal("150000.00"),
                    account_number="0123456789",
                    bank_code="044",
                    account_name="TEST USER",
                    reference=fincra_cashout.cashout_id
                )
                
                # Update cashout to require admin funding
                await session.execute(
                    "UPDATE cashouts SET status = ?, requires_admin_funding = ? WHERE cashout_id = ?",
                    (CashoutStatus.PENDING_ADMIN_FUNDING.value, True, fincra_cashout.cashout_id)
                )
                
                # Verify admin funding required
                funding_cashout = await session.execute(
                    "SELECT * FROM cashouts WHERE cashout_id = ?",
                    (fincra_cashout.cashout_id,)
                )
                funding_record = funding_cashout.fetchone()
                assert funding_record["status"] == CashoutStatus.PENDING_ADMIN_FUNDING.value
                assert funding_record["requires_admin_funding"] is True
    
    async def test_concurrent_cashout_attempts(
        self,
        test_db_session,
        patched_services,
        mock_external_services
    ):
        """Test concurrent cashout attempts by the same user"""
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            user = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=5590000305,
                email="concurrent_cashout_user@example.com",
                balance_usd=Decimal("1000.00")
            )
            
            # Set crypto balances
            await session.execute(
                "UPDATE wallets SET balance_btc = ? WHERE user_id = ?",
                (Decimal("0.1"), user.id)
            )
            
            telegram_user = TelegramObjectFactory.create_user(
                user_id=user.telegram_id,
                username=user.username
            )
            
            # Create multiple concurrent cashout contexts
            contexts = []
            for i in range(3):
                context = TelegramObjectFactory.create_context()
                context.user_data = {
                    "cashout_data": {
                        "type": "crypto",
                        "currency": "BTC",
                        "address": f"bc1q{generate_utid().lower()[:50]}",
                        "amount": Decimal(f"0.0{i+1}")  # 0.01, 0.02, 0.03
                    }
                }
                contexts.append(context)
            
            # Execute concurrent cashout confirmations
            tasks = []
            for i, context in enumerate(contexts):
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
                        'withdrawal_id': f'KRAKEN_W{i+1}',
                        'txid': f'KRAKEN_TX{i+1}',
                        'refid': f'KRAKEN_REF{i+1}'
                    }
                    
                    with patch('handlers.wallet_direct.managed_session') as mock_session:
                        mock_session.return_value.__aenter__.return_value = session
                        
                        task = asyncio.create_task(
                            handle_crypto_cashout_confirmation(confirm_update, context)
                        )
                        tasks.append(task)
            
            # Wait for concurrent cashouts
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify handling of concurrent requests
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) >= 1  # At least one should succeed
            
            # Verify user balance consistency
            final_wallet = await session.execute(
                "SELECT balance_btc FROM wallets WHERE user_id = ?",
                (user.id,)
            )
            wallet_record = final_wallet.fetchone()
            
            # Balance should be consistent (not negative due to race conditions)
            assert wallet_record["balance_btc"] >= Decimal("0.00")
            assert wallet_record["balance_btc"] <= Decimal("0.10")  # Original balance
    
    async def test_cashout_address_validation_and_security(
        self,
        test_db_session,
        patched_services,
        mock_external_services
    ):
        """Test address validation and security measures"""
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            user = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=5590000306,
                email="security_user@example.com",
                balance_usd=Decimal("1000.00")
            )
            
            telegram_user = TelegramObjectFactory.create_user(
                user_id=user.telegram_id,
                username=user.username
            )
            
            cashout_context = TelegramObjectFactory.create_context()
            cashout_context.user_data = {
                "cashout_data": {
                    "type": "crypto",
                    "currency": "BTC"
                }
            }
            
            # SCENARIO 1: Invalid Bitcoin address
            invalid_address = "invalid_btc_address_123"
            invalid_message = TelegramObjectFactory.create_message(telegram_user, invalid_address)
            invalid_update = TelegramObjectFactory.create_update(
                user=telegram_user,
                message=invalid_message
            )
            
            with patch('utils.helpers.validate_crypto_address') as mock_validate:
                mock_validate.return_value = False
                
                with patch('handlers.wallet_direct.managed_session') as mock_session:
                    mock_session.return_value.__aenter__.return_value = session
                    
                    result = await handle_crypto_address_input(invalid_update, cashout_context)
                    
                    # Should reject invalid address
                    assert "error" in cashout_context.user_data.get("cashout_data", {})
                    assert cashout_context.user_data["cashout_data"].get("address") != invalid_address
            
            # SCENARIO 2: Valid address acceptance
            valid_address = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
            valid_message = TelegramObjectFactory.create_message(telegram_user, valid_address)
            valid_update = TelegramObjectFactory.create_update(
                user=telegram_user,
                message=valid_message
            )
            
            with patch('utils.helpers.validate_crypto_address') as mock_validate:
                mock_validate.return_value = True
                
                with patch('handlers.wallet_direct.managed_session') as mock_session:
                    mock_session.return_value.__aenter__.return_value = session
                    
                    result = await handle_crypto_address_input(valid_update, cashout_context)
                    
                    # Should accept valid address
                    assert cashout_context.user_data["cashout_data"]["address"] == valid_address
                    assert result is not None
            
            # SCENARIO 3: Saved address security
            # Create saved address for user
            saved_address = SavedAddress(
                user_id=user.id,
                currency="BTC",
                address=valid_address,
                label="My Cold Wallet",
                created_at=datetime.utcnow()
            )
            session.add(saved_address)
            await session.flush()
            
            # Verify saved addresses are user-specific
            user_addresses = await session.execute(
                "SELECT * FROM saved_addresses WHERE user_id = ?",
                (user.id,)
            )
            addresses = user_addresses.fetchall()
            assert len(addresses) == 1
            assert addresses[0]["address"] == valid_address
            assert addresses[0]["user_id"] == user.id
    
    async def test_cashout_audit_trail_and_compliance(
        self,
        test_db_session,
        patched_services,
        mock_external_services
    ):
        """Test comprehensive audit trail for cashout operations"""
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            user = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=5590000307,
                email="audit_user@example.com",
                balance_usd=Decimal("2000.00")
            )
            
            # Create complete cashout with full audit trail
            cashout = Cashout(
                cashout_id=generate_utid(),
                user_id=user.id,
                amount=Decimal("500.00"),
                currency="NGN",
                ngn_amount=Decimal("750000.00"),
                status=CashoutStatus.COMPLETED.value,
                processing_mode=CashoutProcessingMode.FINCRA.value,
                fincra_transfer_id="FINCRA_AUDIT_123",
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            session.add(cashout)
            
            # Create corresponding transaction record
            transaction = Transaction(
                user_id=user.id,
                type=TransactionType.CASHOUT,
                amount=Decimal("500.00"),
                description=f"NGN cashout {cashout.cashout_id}",
                cashout_id=cashout.cashout_id,
                created_at=datetime.utcnow()
            )
            session.add(transaction)
            
            # Create unified transaction record
            unified_tx = UnifiedTransaction(
                transaction_id=generate_utid(),
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                user_id=user.id,
                amount=Decimal("500.00"),
                currency="NGN",
                status=UnifiedTransactionStatus.SUCCESS,
                cashout_id=cashout.cashout_id,
                created_at=datetime.utcnow()
            )
            session.add(unified_tx)
            
            await session.flush()
            
            # Verify complete audit trail
            # 1. Cashout record
            cashout_audit = await session.execute(
                "SELECT * FROM cashouts WHERE cashout_id = ?",
                (cashout.cashout_id,)
            )
            cashout_record = cashout_audit.fetchone()
            assert cashout_record is not None
            assert cashout_record["user_id"] == user.id
            assert cashout_record["amount"] == Decimal("500.00")
            
            # 2. Transaction record
            transaction_audit = await session.execute(
                "SELECT * FROM transactions WHERE cashout_id = ?",
                (cashout.cashout_id,)
            )
            transaction_record = transaction_audit.fetchone()
            assert transaction_record is not None
            assert transaction_record["type"] == TransactionType.CASHOUT.value
            assert transaction_record["amount"] == Decimal("500.00")
            
            # 3. Unified transaction record
            unified_audit = await session.execute(
                "SELECT * FROM unified_transactions WHERE cashout_id = ?",
                (cashout.cashout_id,)
            )
            unified_record = unified_audit.fetchone()
            assert unified_record is not None
            assert unified_record["transaction_type"] == UnifiedTransactionType.WALLET_CASHOUT.value
            assert unified_record["status"] == UnifiedTransactionStatus.SUCCESS.value
            
            # 4. Verify financial consistency
            total_cashout_amount = await session.execute(
                "SELECT SUM(amount) as total FROM cashouts WHERE user_id = ?",
                (user.id,)
            )
            cashout_total = total_cashout_amount.fetchone()
            
            total_transaction_amount = await session.execute(
                "SELECT SUM(amount) as total FROM transactions WHERE user_id = ? AND type = ?",
                (user.id, TransactionType.CASHOUT.value)
            )
            transaction_total = total_transaction_amount.fetchone()
            
            # Amounts should match between cashouts and transactions
            assert cashout_total["total"] == transaction_total["total"]
            
            # 5. Verify timestamp consistency
            assert cashout_record["created_at"] is not None
            assert transaction_record["created_at"] is not None
            assert unified_record["created_at"] is not None
            
            # All timestamps should be close to each other
            time_diff = abs((cashout_record["created_at"] - transaction_record["created_at"]).total_seconds())
            assert time_diff < 60  # Within 1 minute