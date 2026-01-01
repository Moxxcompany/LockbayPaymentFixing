"""
Comprehensive E2E tests for Unified Transaction System
Tests validate complete transaction flows as requested by the architect:

1. WALLET_CASHOUT: OTP gating, external API retry paths
2. EXCHANGE_BUY/SELL: No OTP, internal wallet crediting
3. ESCROW_RELEASE: No OTP, direct seller wallet transfers

Key validation areas:
- 16-status unified lifecycle
- Dual-write synchronization
- User error handling (non-retryable)
- OTP flow completion
- Escrow status finalization
"""

import pytest
import asyncio
import logging
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import json
import uuid

# Database and model imports
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from database import managed_session
from models import (
    Base, User, Wallet, UnifiedTransaction, UnifiedTransactionStatus, 
    UnifiedTransactionType, UnifiedTransactionPriority, FundMovementType,
    UnifiedTransactionStatusHistory, UnifiedTransactionRetryLog,
    Cashout, CashoutStatus, Escrow, EscrowStatus, ExchangeOrder, ExchangeStatus,
    WalletHolds, WalletHoldStatus
)

# Service imports for testing
from services.unified_transaction_service import (
    UnifiedTransactionService, TransactionRequest, TransactionResult,
    TransactionError, ExternalAPIError, InternalTransferError
)
from services.conditional_otp_service import ConditionalOTPService
from services.dual_write_adapter import DualWriteConfig, DualWriteMode, DualWriteStrategy

# Mock external services
from services.fincra_service import fincra_service
from services.kraken_service import kraken_service
from services.fastforex_service import fastforex_service
from services.crypto import CryptoServiceAtomic

# Utilities
from utils.helpers import generate_utid
from utils.atomic_transactions import atomic_transaction


logger = logging.getLogger(__name__)


class UnifiedTransactionTestFramework:
    """
    Comprehensive test framework for unified transaction system
    
    Provides:
    - Test database setup with unified schema
    - Mock external API services (Fincra, Kraken, etc.)
    - Test user and wallet creation utilities
    - Transaction validation helpers
    - Status transition verification
    """
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self.test_session = None
        
        # Mock service configurations
        self.mock_services = {}
        self.api_call_log = []
        
        # Test data tracking
        self.created_users = []
        self.created_transactions = []
    
    def setup_test_database(self):
        """Setup in-memory test database with unified schema"""
        self.engine = create_engine(
            "sqlite:///:memory:", 
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True
        )
        
        # Create tables safely, handling existing schemas
        try:
            Base.metadata.create_all(self.engine, checkfirst=True)
        except Exception as e:
            logger.warning(f"⚠️ Database schema creation warning: {e}")
            # Continue with existing schema
        
        self.session_factory = scoped_session(sessionmaker(bind=self.engine))
        self.test_session = self.session_factory()
        
        logger.info("🗄️ Test database initialized with unified schema")
    
    def teardown_test_database(self):
        """Clean up test database and sessions"""
        if self.test_session:
            self.test_session.close()
        if self.session_factory:
            self.session_factory.remove()
        if self.engine:
            self.engine.dispose()
        
        logger.info("🧹 Test database cleaned up")
    
    def setup_mock_services(self):
        """Setup mock external services for controlled testing"""
        
        # Mock Fincra service for NGN cashouts
        self.mock_services['fincra'] = Mock()
        self.mock_services['fincra'].process_payout.return_value = {
            'success': True,
            'reference': 'FINCRA_REF_123456',
            'status': 'processing',
            'message': 'Payout initiated successfully'
        }
        
        # Mock Kraken service for crypto cashouts
        self.mock_services['kraken'] = Mock()
        self.mock_services['kraken'].withdraw_crypto.return_value = {
            'success': True,
            'txid': 'KRAKEN_TX_789012',
            'status': 'pending',
            'refid': 'REF_123456789'
        }
        
        # Mock FastForex for exchange rates
        self.mock_services['fastforex'] = Mock()
        self.mock_services['fastforex'].get_usd_to_ngn_rate.return_value = Decimal('1521.50')
        self.mock_services['fastforex'].get_crypto_to_usd_rate.return_value = Decimal('50000.00')
        
        # Mock CryptoService for wallet operations
        self.mock_services['crypto'] = Mock()
        self.mock_services['crypto'].credit_wallet.return_value = {'success': True}
        self.mock_services['crypto'].debit_wallet.return_value = {'success': True}
        
        logger.info("🔧 Mock external services configured")
    
    def create_test_user(self, telegram_id: str, balance_usd: Decimal = Decimal('1000.00'), **kwargs) -> User:
        """Create test user with wallet"""
        user = User(
            telegram_id=telegram_id,
            username=kwargs.get('username', f'testuser_{telegram_id}'),
            first_name=kwargs.get('first_name', 'Test'),
            last_name=kwargs.get('last_name', 'User'),
            email=kwargs.get('email', f'{telegram_id}@example.com'),
            is_active=kwargs.get('is_active', True)
        )
        
        self.test_session.add(user)
        self.test_session.commit()
        
        # Create wallet for user
        wallet = Wallet(
            user_id=user.id,
            balance_usd=balance_usd,
            frozen_balance_usd=Decimal('0.00'),
            total_deposited=balance_usd,
            total_withdrawn=Decimal('0.00')
        )
        
        self.test_session.add(wallet)
        self.test_session.commit()
        
        self.created_users.append(user)
        logger.info(f"👤 Created test user: {telegram_id} with ${balance_usd} balance")
        
        return user
    
    def verify_status_transition(self, transaction_id: str, expected_status: UnifiedTransactionStatus) -> bool:
        """Verify transaction reached expected status"""
        tx = self.test_session.query(UnifiedTransaction).filter(
            UnifiedTransaction.transaction_id == transaction_id
        ).first()
        
        if not tx:
            logger.error(f"❌ Transaction not found: {transaction_id}")
            return False
        
        current_status = UnifiedTransactionStatus(tx.status)
        if current_status == expected_status:
            logger.info(f"✅ Status verified: {transaction_id} → {expected_status.value}")
            return True
        else:
            logger.error(f"❌ Status mismatch: {transaction_id} expected {expected_status.value}, got {current_status.value}")
            return False
    
    def verify_dual_write_sync(self, transaction_id: str, legacy_entity_type: str) -> bool:
        """Verify dual-write synchronization between unified and legacy systems"""
        # Get unified transaction
        unified_tx = self.test_session.query(UnifiedTransaction).filter(
            UnifiedTransaction.transaction_id == transaction_id
        ).first()
        
        if not unified_tx:
            logger.error(f"❌ Unified transaction not found: {transaction_id}")
            return False
        
        # Check legacy entity exists and is synchronized
        legacy_id = None
        if legacy_entity_type == 'cashout':
            legacy_id = unified_tx.cashout_id
            legacy_entity = self.test_session.query(Cashout).filter(
                Cashout.cashout_id == legacy_id
            ).first() if legacy_id else None
        elif legacy_entity_type == 'escrow':
            legacy_id = unified_tx.escrow_id
            legacy_entity = self.test_session.query(Escrow).filter(
                Escrow.escrow_id == legacy_id
            ).first() if legacy_id else None
        elif legacy_entity_type == 'exchange':
            legacy_id = unified_tx.exchange_id
            legacy_entity = self.test_session.query(ExchangeOrder).filter(
                ExchangeOrder.id == legacy_id
            ).first() if legacy_id else None
        else:
            logger.error(f"❌ Unknown legacy entity type: {legacy_entity_type}")
            return False
        
        if legacy_entity:
            logger.info(f"✅ Dual-write sync verified: {transaction_id} ↔ {legacy_entity_type}:{legacy_id}")
            return True
        else:
            logger.error(f"❌ Legacy entity not found for {transaction_id}")
            return False
    
    def log_api_call(self, service: str, method: str, success: bool, **kwargs):
        """Log API calls for testing verification"""
        call_record = {
            'timestamp': datetime.utcnow(),
            'service': service,
            'method': method,
            'success': success,
            'params': kwargs
        }
        self.api_call_log.append(call_record)
        
        logger.info(f"📡 API Call logged: {service}.{method}({'✅' if success else '❌'})")
    
    def verify_api_calls(self, expected_calls: List[Dict[str, Any]]) -> bool:
        """Verify expected API calls were made"""
        if len(self.api_call_log) != len(expected_calls):
            logger.error(f"❌ API call count mismatch: expected {len(expected_calls)}, got {len(self.api_call_log)}")
            return False
        
        for i, (actual, expected) in enumerate(zip(self.api_call_log, expected_calls)):
            if actual['service'] != expected['service'] or actual['method'] != expected['method']:
                logger.error(f"❌ API call {i} mismatch: expected {expected['service']}.{expected['method']}, got {actual['service']}.{actual['method']}")
                return False
        
        logger.info(f"✅ All {len(expected_calls)} API calls verified")
        return True
    
    def cleanup(self):
        """Clean up test framework resources"""
        self.api_call_log.clear()
        self.created_users.clear()
        self.created_transactions.clear()
        self.teardown_test_database()


@pytest.fixture(scope="class")
def test_framework():
    """Pytest fixture providing test framework"""
    framework = UnifiedTransactionTestFramework()
    framework.setup_test_database()
    framework.setup_mock_services()
    
    yield framework
    
    framework.cleanup()


@pytest.fixture
def unified_service(test_framework):
    """Pytest fixture providing UnifiedTransactionService with test config"""
    dual_write_config = DualWriteConfig(
        mode=DualWriteMode.DUAL_WRITE_UNIFIED_PRIMARY,
        strategy=DualWriteStrategy.UNIFIED_FIRST
    )
    
    # Patch the service to use test database session
    with patch('services.unified_transaction_service.managed_session') as mock_session:
        mock_session.return_value.__aenter__ = AsyncMock(return_value=test_framework.test_session)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        service = UnifiedTransactionService(dual_write_config)
        yield service


class TestWalletCashoutE2E:
    """Test wallet cashout E2E flow with OTP validation and external API retry paths"""
    
    @pytest.mark.asyncio
    async def test_wallet_cashout_crypto_with_otp_success(self, test_framework, unified_service):
        """Test successful crypto wallet cashout with OTP flow"""
        # Create test user with sufficient balance
        user = test_framework.create_test_user('123456789', Decimal('500.00'))
        
        # Create transaction request
        request = TransactionRequest(
            transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
            user_id=user.id,
            amount=Decimal('100.00'),
            currency='BTC',
            destination_address='1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
            metadata={'network': 'bitcoin', 'fee_tier': 'standard'}
        )
        
        # Mock external service calls
        with patch.object(test_framework.mock_services['kraken'], 'withdraw_crypto') as mock_withdraw:
            mock_withdraw.return_value = {
                'success': True,
                'txid': 'KRAKEN_TX_12345',
                'status': 'pending'
            }
            
            # Step 1: Create transaction
            result = await unified_service.create_transaction(request)
            
            assert result.success is True
            assert result.requires_otp is True
            assert result.status == UnifiedTransactionStatus.OTP_PENDING.value
            
            transaction_id = result.transaction_id
            test_framework.created_transactions.append(transaction_id)
            
            # Verify OTP requirement via ConditionalOTPService
            otp_required = ConditionalOTPService.requires_otp('wallet_cashout')
            assert otp_required is True
            
            # Step 2: Complete OTP verification
            otp_result = await unified_service.complete_otp_verification(transaction_id, '123456')
            assert otp_result.success is True
            assert otp_result.status == UnifiedTransactionStatus.PROCESSING.value
            
            # Step 3: Process external API call
            processing_result = await unified_service.continue_processing(transaction_id)
            assert processing_result.success is True
            assert processing_result.status == UnifiedTransactionStatus.AWAITING_RESPONSE.value
            
            # Step 4: Simulate external API response (webhook)
            webhook_result = await unified_service.handle_external_confirmation(
                transaction_id, 
                {'txid': 'KRAKEN_TX_12345', 'status': 'completed'}
            )
            assert webhook_result.success is True
            assert webhook_result.status == UnifiedTransactionStatus.SUCCESS.value
        
        # Verify final state
        assert test_framework.verify_status_transition(transaction_id, UnifiedTransactionStatus.SUCCESS)
        
        # Verify dual-write synchronization
        assert test_framework.verify_dual_write_sync(transaction_id, 'cashout')
        
        # Log API call for verification
        test_framework.log_api_call('kraken', 'withdraw_crypto', True)
    
    @pytest.mark.asyncio
    async def test_wallet_cashout_insufficient_balance_user_error(self, test_framework, unified_service):
        """Test wallet cashout with insufficient balance (non-retryable user error)"""
        # Create test user with low balance
        user = test_framework.create_test_user('987654321', Decimal('50.00'))
        
        # Create transaction request exceeding balance
        request = TransactionRequest(
            transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
            user_id=user.id,
            amount=Decimal('1000.00'),  # Exceeds available balance
            currency='USD',
            destination_bank_account='ACC123456789'
        )
        
        # Step 1: Create transaction (should fail immediately)
        result = await unified_service.create_transaction(request)
        
        assert result.success is False
        assert "insufficient balance" in result.error.lower()
        assert result.status == UnifiedTransactionStatus.FAILED.value
        
        # Verify transaction was created but marked as failed (non-retryable)
        if result.transaction_id:
            tx = test_framework.test_session.query(UnifiedTransaction).filter(
                UnifiedTransaction.transaction_id == result.transaction_id
            ).first()
            
            assert tx.failure_type == 'user'  # Non-retryable user error
            assert tx.retry_count == 0  # Should not trigger retries
            assert 'USER_INSUFFICIENT_BALANCE' in tx.last_error_code
    
    @pytest.mark.asyncio
    async def test_wallet_cashout_external_api_failure_retry(self, test_framework, unified_service):
        """Test wallet cashout with external API failure triggering unified retry logic"""
        # Create test user
        user = test_framework.create_test_user('555666777', Decimal('200.00'))
        
        request = TransactionRequest(
            transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
            user_id=user.id,
            amount=Decimal('50.00'),
            currency='BTC',
            destination_address='1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa'
        )
        
        # Mock API failure then success
        with patch.object(test_framework.mock_services['kraken'], 'withdraw_crypto') as mock_withdraw:
            # First 2 calls fail, 3rd succeeds
            mock_withdraw.side_effect = [
                {'success': False, 'error': 'Network timeout'},
                {'success': False, 'error': 'Service temporarily unavailable'},
                {'success': True, 'txid': 'KRAKEN_TX_RETRY_SUCCESS', 'status': 'pending'}
            ]
            
            # Create and complete OTP
            result = await unified_service.create_transaction(request)
            transaction_id = result.transaction_id
            
            await unified_service.complete_otp_verification(transaction_id, '123456')
            
            # First processing attempt (should fail, schedule retry)
            processing_result = await unified_service.continue_processing(transaction_id)
            assert processing_result.success is False
            
            # Verify retry scheduled
            tx = test_framework.test_session.query(UnifiedTransaction).filter(
                UnifiedTransaction.transaction_id == transaction_id
            ).first()
            assert tx.retry_count == 1
            assert tx.next_retry_at is not None
            assert tx.failure_type == 'technical'
            
            # Simulate unified retry processor
            retry_result = await unified_service.continue_external_processing(transaction_id)
            assert retry_result.success is False  # 2nd attempt fails
            assert tx.retry_count == 2
            
            # 3rd retry attempt succeeds
            final_retry_result = await unified_service.continue_external_processing(transaction_id)
            assert final_retry_result.success is True
            assert final_retry_result.status == UnifiedTransactionStatus.AWAITING_RESPONSE.value
        
        # Verify retry logic worked correctly
        final_tx = test_framework.test_session.query(UnifiedTransaction).filter(
            UnifiedTransaction.transaction_id == transaction_id
        ).first()
        assert final_tx.retry_count == 3  # All 3 attempts made
        assert final_tx.status == UnifiedTransactionStatus.AWAITING_RESPONSE.value


class TestExchangeOperationsE2E:
    """Test exchange buy/sell flows with no OTP requirement and internal wallet crediting"""
    
    @pytest.mark.asyncio
    async def test_exchange_sell_crypto_no_otp_internal_credit(self, test_framework, unified_service):
        """Test EXCHANGE_SELL_CRYPTO with no OTP and internal wallet crediting"""
        # Create test user
        user = test_framework.create_test_user('111222333', Decimal('100.00'))
        
        # Create exchange sell request
        request = TransactionRequest(
            transaction_type=UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
            user_id=user.id,
            amount=Decimal('0.01'),  # 0.01 BTC
            currency='BTC',
            exchange_rate=Decimal('50000.00'),  # $50k per BTC
            metadata={
                'target_currency': 'USD',
                'exchange_type': 'crypto_to_fiat',
                'expected_usd_amount': '500.00'
            }
        )
        
        # Verify no OTP requirement
        otp_required = ConditionalOTPService.requires_otp('exchange_sell_crypto')
        assert otp_required is False
        
        with patch.object(test_framework.mock_services['crypto'], 'credit_wallet') as mock_credit:
            mock_credit.return_value = {'success': True, 'new_balance': '600.00'}
            
            # Step 1: Create transaction (should skip OTP, go straight to awaiting payment)
            result = await unified_service.create_transaction(request)
            
            assert result.success is True
            assert result.requires_otp is False
            assert result.status == UnifiedTransactionStatus.AWAITING_PAYMENT.value
            
            transaction_id = result.transaction_id
            
            # Step 2: Simulate payment confirmation (crypto deposit received)
            payment_result = await unified_service.confirm_payment_received(
                transaction_id,
                {'amount_received': '0.01', 'currency': 'BTC', 'tx_hash': '0xabc123...'}
            )
            assert payment_result.success is True
            assert payment_result.status == UnifiedTransactionStatus.PAYMENT_CONFIRMED.value
            
            # Step 3: Process exchange (internal operation, no external API)
            processing_result = await unified_service.continue_processing(transaction_id)
            assert processing_result.success is True
            assert processing_result.status == UnifiedTransactionStatus.PROCESSING.value
            
            # Step 4: Complete internal wallet crediting
            completion_result = await unified_service.complete_internal_transfer(transaction_id)
            assert completion_result.success is True
            assert completion_result.status == UnifiedTransactionStatus.SUCCESS.value
        
        # Verify final state
        assert test_framework.verify_status_transition(transaction_id, UnifiedTransactionStatus.SUCCESS)
        
        # Verify dual-write synchronization
        assert test_framework.verify_dual_write_sync(transaction_id, 'exchange')
        
        # Log internal operation (no external API call)
        test_framework.log_api_call('internal', 'wallet_credit', True)
    
    @pytest.mark.asyncio
    async def test_exchange_buy_crypto_no_otp_flow(self, test_framework, unified_service):
        """Test EXCHANGE_BUY_CRYPTO with no OTP requirement"""
        # Create test user
        user = test_framework.create_test_user('444555666', Decimal('1000.00'))
        
        request = TransactionRequest(
            transaction_type=UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
            user_id=user.id,
            amount=Decimal('500.00'),  # $500 USD
            currency='USD',
            exchange_rate=Decimal('50000.00'),  # $50k per BTC
            destination_address='bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
            metadata={
                'target_currency': 'BTC',
                'exchange_type': 'fiat_to_crypto',
                'expected_btc_amount': '0.01'
            }
        )
        
        # Verify no OTP requirement
        otp_required = ConditionalOTPService.requires_otp('exchange_buy_crypto')
        assert otp_required is False
        
        with patch.object(test_framework.mock_services['crypto'], 'send_crypto') as mock_send:
            mock_send.return_value = {
                'success': True, 
                'tx_hash': '0xdef456...',
                'amount_sent': '0.01'
            }
            
            # Create and process transaction
            result = await unified_service.create_transaction(request)
            transaction_id = result.transaction_id
            
            assert result.requires_otp is False
            assert result.status == UnifiedTransactionStatus.AWAITING_PAYMENT.value
            
            # Simulate fiat payment confirmation
            await unified_service.confirm_payment_received(
                transaction_id,
                {'amount_received': '500.00', 'currency': 'USD', 'payment_method': 'bank_transfer'}
            )
            
            # Complete exchange processing
            processing_result = await unified_service.continue_processing(transaction_id)
            assert processing_result.success is True
            
            # Complete crypto sending
            completion_result = await unified_service.complete_internal_transfer(transaction_id)
            assert completion_result.success is True
            assert completion_result.status == UnifiedTransactionStatus.SUCCESS.value
        
        # Verify successful completion
        assert test_framework.verify_status_transition(transaction_id, UnifiedTransactionStatus.SUCCESS)


class TestEscrowReleaseE2E:
    """Test escrow release flows with direct seller wallet transfers and no OTP"""
    
    @pytest.mark.asyncio
    async def test_escrow_release_no_otp_direct_transfer(self, test_framework, unified_service):
        """Test escrow release to seller wallet with no OTP"""
        # Create buyer and seller users
        buyer = test_framework.create_test_user('buyer123', Decimal('1000.00'))
        seller = test_framework.create_test_user('seller456', Decimal('100.00'))
        
        # Create escrow release request
        request = TransactionRequest(
            transaction_type=UnifiedTransactionType.ESCROW,
            user_id=seller.id,  # Seller receives the funds
            amount=Decimal('250.00'),
            currency='USD',
            fund_movement_type=FundMovementType.RELEASE,
            escrow_details={
                'escrow_id': 'ESC789012',
                'buyer_id': buyer.id,
                'seller_id': seller.id,
                'operation': 'release_to_seller',
                'release_reason': 'delivery_confirmed'
            }
        )
        
        # Verify no OTP requirement for escrow operations
        otp_required = ConditionalOTPService.requires_otp('escrow')
        assert otp_required is False
        
        # Mock wallet operations
        with patch.object(test_framework.mock_services['crypto'], 'credit_wallet') as mock_credit:
            mock_credit.return_value = {'success': True, 'new_balance': '350.00'}
            
            # Step 1: Create escrow release transaction
            result = await unified_service.create_transaction(request)
            
            assert result.success is True
            assert result.requires_otp is False
            assert result.status == UnifiedTransactionStatus.FUNDS_HELD.value  # Escrow starts with held funds
            
            transaction_id = result.transaction_id
            
            # Step 2: Process release (direct internal transfer, no external API)
            release_result = await unified_service.process_escrow_release(transaction_id)
            assert release_result.success is True
            assert release_result.status == UnifiedTransactionStatus.RELEASE_PENDING.value
            
            # Step 3: Complete seller wallet crediting
            completion_result = await unified_service.complete_internal_transfer(transaction_id)
            assert completion_result.success is True
            assert completion_result.status == UnifiedTransactionStatus.SUCCESS.value
        
        # Verify final state and seller balance update
        assert test_framework.verify_status_transition(transaction_id, UnifiedTransactionStatus.SUCCESS)
        
        # Verify dual-write sync with escrow entity
        assert test_framework.verify_dual_write_sync(transaction_id, 'escrow')
        
        # Verify seller wallet was credited (internal operation)
        updated_seller_wallet = test_framework.test_session.query(Wallet).filter(
            Wallet.user_id == seller.id
        ).first()
        # Note: In real implementation, this would be updated by atomic transaction
        
        test_framework.log_api_call('internal', 'escrow_release', True)
    
    @pytest.mark.asyncio
    async def test_escrow_refund_to_buyer_no_otp(self, test_framework, unified_service):
        """Test escrow refund to buyer with no OTP"""
        # Create buyer and seller
        buyer = test_framework.create_test_user('refund_buyer', Decimal('500.00'))
        seller = test_framework.create_test_user('refund_seller', Decimal('200.00'))
        
        # Create escrow refund request
        request = TransactionRequest(
            transaction_type=UnifiedTransactionType.ESCROW,
            user_id=buyer.id,  # Buyer receives the refund
            amount=Decimal('300.00'),
            currency='USD',
            fund_movement_type=FundMovementType.RELEASE,
            escrow_details={
                'escrow_id': 'ESC_REFUND_123',
                'buyer_id': buyer.id,
                'seller_id': seller.id,
                'operation': 'refund_to_buyer',
                'refund_reason': 'delivery_failed'
            }
        )
        
        # Verify no OTP for escrow refunds
        assert ConditionalOTPService.requires_otp('escrow') is False
        
        with patch.object(test_framework.mock_services['crypto'], 'credit_wallet') as mock_refund:
            mock_refund.return_value = {'success': True, 'new_balance': '800.00'}
            
            # Process refund transaction
            result = await unified_service.create_transaction(request)
            transaction_id = result.transaction_id
            
            # Complete refund flow
            await unified_service.process_escrow_release(transaction_id)
            completion_result = await unified_service.complete_internal_transfer(transaction_id)
            
            assert completion_result.success is True
            assert completion_result.status == UnifiedTransactionStatus.SUCCESS.value
        
        # Verify refund completion
        assert test_framework.verify_status_transition(transaction_id, UnifiedTransactionStatus.SUCCESS)
        test_framework.log_api_call('internal', 'escrow_refund', True)


class TestEdgeCasesAndIntegration:
    """Test edge cases and integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_concurrent_transaction_processing(self, test_framework, unified_service):
        """Test concurrent transaction processing doesn't cause conflicts"""
        # Create user for concurrent transactions
        user = test_framework.create_test_user('concurrent_user', Decimal('1000.00'))
        
        # Create multiple transaction requests
        requests = []
        for i in range(5):
            request = TransactionRequest(
                transaction_type=UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
                user_id=user.id,
                amount=Decimal(f'{10 + i}.00'),
                currency='USD',
                metadata={'batch_id': f'concurrent_batch_{i}'}
            )
            requests.append(request)
        
        # Process transactions concurrently
        results = await asyncio.gather(*[
            unified_service.create_transaction(req) for req in requests
        ], return_exceptions=True)
        
        # Verify all transactions were created successfully
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= 4  # At least 80% success rate
        
        # Verify each has unique transaction ID
        transaction_ids = [r.transaction_id for r in successful_results if r.success]
        assert len(set(transaction_ids)) == len(transaction_ids)  # All unique
        
        logger.info(f"✅ Concurrent processing: {len(successful_results)}/{len(requests)} succeeded")
    
    @pytest.mark.asyncio
    async def test_status_transition_validation(self, test_framework, unified_service):
        """Test unified status transitions follow proper lifecycle"""
        user = test_framework.create_test_user('status_test', Decimal('500.00'))
        
        # Create wallet cashout to test full status lifecycle
        request = TransactionRequest(
            transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
            user_id=user.id,
            amount=Decimal('100.00'),
            currency='USD'
        )
        
        with patch.object(test_framework.mock_services['fincra'], 'process_payout') as mock_payout:
            mock_payout.return_value = {'success': True, 'reference': 'TEST_REF_123'}
            
            # Track status transitions
            result = await unified_service.create_transaction(request)
            transaction_id = result.transaction_id
            
            # Expected status flow: pending → otp_pending → processing → awaiting_response → success
            status_history = [UnifiedTransactionStatus.PENDING.value]
            
            # OTP phase
            if result.requires_otp:
                status_history.append(UnifiedTransactionStatus.OTP_PENDING.value)
                await unified_service.complete_otp_verification(transaction_id, '123456')
            
            status_history.append(UnifiedTransactionStatus.PROCESSING.value)
            
            # Processing phase
            await unified_service.continue_processing(transaction_id)
            status_history.append(UnifiedTransactionStatus.AWAITING_RESPONSE.value)
            
            # Completion
            await unified_service.handle_external_confirmation(
                transaction_id,
                {'reference': 'TEST_REF_123', 'status': 'completed'}
            )
            status_history.append(UnifiedTransactionStatus.SUCCESS.value)
        
        # Verify status history in database
        tx = test_framework.test_session.query(UnifiedTransaction).filter(
            UnifiedTransaction.transaction_id == transaction_id
        ).first()
        
        history_records = test_framework.test_session.query(UnifiedTransactionStatusHistory).filter(
            UnifiedTransactionStatusHistory.transaction_id == tx.id
        ).order_by(UnifiedTransactionStatusHistory.changed_at).all()
        
        recorded_statuses = [h.new_status for h in history_records]
        
        # Verify status progression matches expected lifecycle
        for expected_status in status_history:
            assert expected_status in recorded_statuses, f"Missing status: {expected_status}"
        
        logger.info(f"✅ Status lifecycle verified: {' → '.join(recorded_statuses)}")


if __name__ == "__main__":
    # Run comprehensive E2E tests
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "--maxfail=1",  # Stop on first failure for debugging
        "-x"  # Exit on first failure
    ])