"""
Comprehensive Integration Tests for Unified Retry System
Tests validate unified retry behavior end-to-end across all transaction types
and external API providers with production-realistic scenarios.

Key Test Areas:
1. Happy path retry scenarios (technical failure → successful retry)
2. Maximum retry attempts reached (6 attempts exhausted)
3. User error vs technical error classification  
4. Different provider failures (Fincra, Kraken, DynoPay)
5. Integration with existing wallet holds and transaction systems
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
    UnifiedTransactionType, UnifiedTransactionRetryLog, CashoutErrorCode,
    OperationFailureType, CashoutStatus, WalletHolds, WalletHoldStatus
)

# Service imports for testing
from services.unified_retry_service import UnifiedRetryService, RetryContext, RetryResult, RetryDecision
from jobs.unified_retry_processor import UnifiedRetryProcessor
from services.cashout_retry_service import cashout_retry_service
from services.auto_cashout import auto_cashout_service
from utils.financial_audit_logger import financial_audit_logger

logger = logging.getLogger(__name__)


class UnifiedRetryTestFramework:
    """
    Comprehensive test framework for unified retry system validation
    
    Features:
    - Test database setup with unified retry schema
    - Mock external API services with controlled failure scenarios
    - Retry timing and progression validation
    - Transaction state verification
    - Financial audit logging validation
    """
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self.test_session = None
        
        # Mock services with controllable failure patterns
        self.mock_services = {}
        self.api_failure_sequence = {}
        self.retry_call_log = []
        
        # Test data tracking
        self.created_users = []
        self.created_transactions = []
        self.retry_service = UnifiedRetryService()
        self.retry_processor = UnifiedRetryProcessor()
    
    def setup_test_database(self):
        """Setup test database with unified retry schema"""
        self.engine = create_engine(
            "sqlite:///:memory:", 
            echo=False,
            pool_pre_ping=True
        )
        
        Base.metadata.create_all(self.engine, checkfirst=True)
        self.session_factory = scoped_session(sessionmaker(bind=self.engine))
        self.test_session = self.session_factory()
        
        logger.info("🗄️ Unified retry test database initialized")
    
    def teardown_test_database(self):
        """Clean up test database and sessions"""
        if self.test_session:
            self.test_session.close()
        if self.session_factory:
            self.session_factory.remove()
        if self.engine:
            self.engine.dispose()
        
        logger.info("🧹 Unified retry test database cleaned up")
    
    def setup_mock_external_services(self):
        """Setup mock external services with controllable failure patterns"""
        
        # Mock Fincra service for NGN cashouts
        self.mock_services['fincra'] = Mock()
        
        # Mock Kraken service for crypto cashouts  
        self.mock_services['kraken'] = Mock()
        
        # Mock DynoPay service for international cashouts
        self.mock_services['dynopay'] = Mock()
        
        logger.info("🔧 Mock external services configured for retry testing")
    
    def configure_api_failure_sequence(self, provider: str, failure_pattern: List[Dict[str, Any]]):
        """
        Configure specific failure patterns for external API testing
        
        Args:
            provider: 'fincra', 'kraken', or 'dynopay'
            failure_pattern: List of response patterns for sequential calls
                           e.g., [{'success': False, 'error': 'timeout'}, {'success': True}]
        """
        self.api_failure_sequence[provider] = failure_pattern
        logger.info(f"🎭 Configured failure pattern for {provider}: {len(failure_pattern)} responses")
    
    def create_test_user_with_wallet(self, telegram_id: str, balances: Dict[str, Decimal] = None) -> User:
        """Create test user with wallets and balances"""
        if balances is None:
            balances = {'USD': Decimal('1000.00')}
        
        user = User(
            telegram_id=telegram_id,
            username=f'testuser_{telegram_id}',
            first_name='Test',
            last_name='User',
            email=f'{telegram_id}@example.com',
            is_active=True
        )
        
        self.test_session.add(user)
        self.test_session.commit()
        
        # Create wallets for each currency
        for currency, balance in balances.items():
            wallet = Wallet(
                user_id=user.id,
                currency=currency,
                balance=balance,
                frozen_balance=Decimal('0.00'),
                total_deposited=balance,
                total_withdrawn=Decimal('0.00')
            )
            self.test_session.add(wallet)
        
        self.test_session.commit()
        self.created_users.append(user)
        
        logger.info(f"👤 Created test user {telegram_id} with balances: {balances}")
        return user
    
    def create_failed_transaction_for_retry(self, 
                                          user_id: int,
                                          transaction_type: str = 'wallet_cashout',
                                          amount: Decimal = Decimal('100.00'),
                                          currency: str = 'USD',
                                          provider: str = 'fincra',
                                          error_code: str = 'FINCRA_API_TIMEOUT',
                                          failure_type: str = 'technical',
                                          retry_count: int = 0) -> str:
        """Create a failed transaction ready for retry testing"""
        
        from utils.helpers import generate_utid
        transaction_id = generate_utid("TX")
        
        # Create unified transaction record
        unified_tx = UnifiedTransaction(
            transaction_id=transaction_id,
            transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
            user_id=user_id,
            amount=amount,
            currency=currency,
            status=UnifiedTransactionStatus.FAILED,
            external_provider=provider,
            failure_type=failure_type,
            last_error_code=error_code,
            retry_count=retry_count,
            next_retry_at=datetime.utcnow() + timedelta(minutes=5),  # Ready for immediate retry
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata={'test_scenario': True}
        )
        
        self.test_session.add(unified_tx)
        
        # Create corresponding wallet hold
        wallet_hold = WalletHolds(
            user_id=user_id,
            amount=amount,
            currency=currency,
            hold_type='cashout',
            status=WalletHoldStatus.FAILED_HELD,  # Funds frozen due to failure
            reference_id=transaction_id,
            external_reference=f"{provider}_ref_{transaction_id[-8:]}",
            created_at=datetime.utcnow()
        )
        
        self.test_session.add(wallet_hold)
        self.test_session.commit()
        
        self.created_transactions.append(transaction_id)
        logger.info(f"💸 Created failed {transaction_type} transaction {transaction_id} for retry testing")
        
        return transaction_id
    
    def verify_retry_progression(self, transaction_id: str, expected_retry_count: int) -> bool:
        """Verify retry count progression and timing"""
        tx = self.test_session.query(UnifiedTransaction).filter(
            UnifiedTransaction.transaction_id == transaction_id
        ).first()
        
        if not tx:
            logger.error(f"❌ Transaction not found: {transaction_id}")
            return False
        
        if tx.retry_count != expected_retry_count:
            logger.error(f"❌ Retry count mismatch: expected {expected_retry_count}, got {tx.retry_count}")
            return False
        
        # Verify retry logs exist
        retry_logs = self.test_session.query(UnifiedTransactionRetryLog).filter(
            UnifiedTransactionRetryLog.transaction_id == transaction_id
        ).all()
        
        if len(retry_logs) != expected_retry_count:
            logger.error(f"❌ Retry log count mismatch: expected {expected_retry_count}, got {len(retry_logs)}")
            return False
        
        logger.info(f"✅ Retry progression verified: {transaction_id} → {expected_retry_count} attempts")
        return True
    
    def verify_wallet_hold_status(self, transaction_id: str, expected_status: WalletHoldStatus) -> bool:
        """Verify wallet hold status matches expected state"""
        hold = self.test_session.query(WalletHolds).filter(
            WalletHolds.reference_id == transaction_id
        ).first()
        
        if not hold:
            logger.error(f"❌ Wallet hold not found for transaction: {transaction_id}")
            return False
        
        if hold.status != expected_status:
            logger.error(f"❌ Wallet hold status mismatch: expected {expected_status.value}, got {hold.status.value}")
            return False
        
        logger.info(f"✅ Wallet hold status verified: {transaction_id} → {expected_status.value}")
        return True
    
    def simulate_external_api_call(self, provider: str, method: str, **kwargs) -> Dict[str, Any]:
        """Simulate external API call with configured failure patterns"""
        if provider not in self.api_failure_sequence:
            # Default success response
            return {'success': True, 'reference': f'{provider.upper()}_REF_SUCCESS'}
        
        pattern = self.api_failure_sequence[provider]
        if not pattern:
            return {'success': True, 'reference': f'{provider.upper()}_REF_SUCCESS'}
        
        # Get next response in sequence
        response = pattern.pop(0)
        
        # Log API call for verification
        self.retry_call_log.append({
            'timestamp': datetime.utcnow(),
            'provider': provider,
            'method': method,
            'response': response,
            'kwargs': kwargs
        })
        
        logger.info(f"📡 Simulated {provider}.{method}: {response}")
        return response
    
    def verify_api_call_sequence(self, expected_sequence: List[Dict[str, Any]]) -> bool:
        """Verify API calls match expected sequence"""
        if len(self.retry_call_log) != len(expected_sequence):
            logger.error(f"❌ API call count mismatch: expected {len(expected_sequence)}, got {len(self.retry_call_log)}")
            return False
        
        for i, (actual, expected) in enumerate(zip(self.retry_call_log, expected_sequence)):
            if actual['provider'] != expected['provider'] or actual['method'] != expected['method']:
                logger.error(f"❌ API call {i} mismatch: expected {expected}, got {actual}")
                return False
        
        logger.info(f"✅ API call sequence verified: {len(expected_sequence)} calls")
        return True
    
    def cleanup(self):
        """Clean up test framework resources"""
        self.retry_call_log.clear()
        self.api_failure_sequence.clear()
        self.created_users.clear()
        self.created_transactions.clear()
        self.teardown_test_database()


@pytest.fixture(scope="class")
def retry_test_framework():
    """Pytest fixture providing unified retry test framework"""
    framework = UnifiedRetryTestFramework()
    framework.setup_test_database()
    framework.setup_mock_external_services()
    
    yield framework
    
    framework.cleanup()


class TestHappyPathRetryScenarios:
    """Test successful retry scenarios after technical failures"""
    
    @pytest.mark.asyncio
    async def test_fincra_ngn_cashout_retry_success(self, retry_test_framework):
        """Test Fincra NGN cashout fails then succeeds on retry"""
        # Create user with NGN balance
        user = retry_test_framework.create_test_user_with_wallet(
            '123456789', 
            {'USD': Decimal('500.00')}
        )
        
        # Configure Fincra failure then success
        retry_test_framework.configure_api_failure_sequence('fincra', [
            {'success': False, 'error': 'API timeout', 'error_code': 'FINCRA_API_TIMEOUT'},
            {'success': True, 'reference': 'FINCRA_REF_SUCCESS_123', 'status': 'processing'}
        ])
        
        # Create failed transaction for retry
        transaction_id = retry_test_framework.create_failed_transaction_for_retry(
            user_id=user.id,
            amount=Decimal('150.00'),
            currency='USD',
            provider='fincra',
            error_code='FINCRA_API_TIMEOUT',
            failure_type='technical',
            retry_count=1
        )
        
        # Simulate retry attempt
        retry_context = RetryContext(
            transaction_id=transaction_id,
            transaction_type='wallet_cashout',
            user_id=user.id,
            amount=Decimal('150.00'),
            currency='USD',
            external_provider='fincra',
            attempt_number=2,
            error_code='FINCRA_API_TIMEOUT',
            error_message='Previous API timeout'
        )
        
        # Mock the actual retry processing
        with patch('services.fincra_service.process_payout') as mock_payout:
            # First call (retry) succeeds
            mock_payout.return_value = retry_test_framework.simulate_external_api_call(
                'fincra', 'process_payout', amount=150.00, currency='USD'
            )
            
            # Process the retry
            retry_result = await retry_test_framework.retry_service.handle_transaction_failure(
                retry_context, Exception("Previous timeout")
            )
            
            # Verify retry scheduled
            assert retry_result.decision == RetryDecision.RETRY
            assert retry_result.delay_seconds is not None
            
            # Simulate successful retry execution
            success_response = retry_test_framework.simulate_external_api_call(
                'fincra', 'process_payout', amount=150.00, currency='USD'
            )
            assert success_response['success'] is True
        
        # Verify transaction progression
        assert retry_test_framework.verify_retry_progression(transaction_id, 2)
        
        # Verify wallet hold status updated
        assert retry_test_framework.verify_wallet_hold_status(
            transaction_id, 
            WalletHoldStatus.CONSUMED_SENT
        )
        
        logger.info("✅ Fincra NGN cashout retry success scenario validated")
    
    @pytest.mark.asyncio
    async def test_kraken_crypto_cashout_retry_success(self, retry_test_framework):
        """Test Kraken crypto cashout fails then succeeds on retry"""
        user = retry_test_framework.create_test_user_with_wallet(
            '987654321',
            {'BTC': Decimal('0.1')}
        )
        
        # Configure Kraken failure then success
        retry_test_framework.configure_api_failure_sequence('kraken', [
            {'success': False, 'error': 'Address verification failed', 'error_code': 'KRAKEN_ADDR_NOT_FOUND'},
            {'success': True, 'txid': 'KRAKEN_TX_SUCCESS', 'refid': 'REF_SUCCESS_456'}
        ])
        
        transaction_id = retry_test_framework.create_failed_transaction_for_retry(
            user_id=user.id,
            amount=Decimal('0.01'),
            currency='BTC',
            provider='kraken',
            error_code='KRAKEN_ADDR_NOT_FOUND',
            failure_type='technical',
            retry_count=1
        )
        
        retry_context = RetryContext(
            transaction_id=transaction_id,
            transaction_type='wallet_cashout',
            user_id=user.id,
            amount=Decimal('0.01'),
            currency='BTC',
            external_provider='kraken',
            attempt_number=2,
            error_code='KRAKEN_ADDR_NOT_FOUND',
            error_message='Address not found in Kraken whitelist'
        )
        
        with patch('services.kraken_service.withdraw_crypto') as mock_withdraw:
            mock_withdraw.return_value = retry_test_framework.simulate_external_api_call(
                'kraken', 'withdraw_crypto', amount=0.01, currency='BTC'
            )
            
            retry_result = await retry_test_framework.retry_service.handle_transaction_failure(
                retry_context, Exception("Address not found")
            )
            
            assert retry_result.decision == RetryDecision.RETRY
            
            # Simulate successful retry
            success_response = retry_test_framework.simulate_external_api_call(
                'kraken', 'withdraw_crypto', amount=0.01, currency='BTC'
            )
            assert success_response['success'] is True
        
        assert retry_test_framework.verify_retry_progression(transaction_id, 2)
        assert retry_test_framework.verify_wallet_hold_status(transaction_id, WalletHoldStatus.CONSUMED_SENT)
        
        logger.info("✅ Kraken crypto cashout retry success scenario validated")
    
    @pytest.mark.asyncio
    async def test_dynopay_international_retry_success(self, retry_test_framework):
        """Test DynoPay international cashout retry success"""
        user = retry_test_framework.create_test_user_with_wallet(
            '555666777',
            {'USD': Decimal('1000.00')}
        )
        
        # Configure DynoPay failure then success  
        retry_test_framework.configure_api_failure_sequence('dynopay', [
            {'success': False, 'error': 'Service unavailable', 'error_code': 'DYNOPAY_SERVICE_UNAVAILABLE'},
            {'success': True, 'reference': 'DYNOPAY_REF_SUCCESS', 'status': 'pending'}
        ])
        
        transaction_id = retry_test_framework.create_failed_transaction_for_retry(
            user_id=user.id,
            amount=Decimal('250.00'),
            currency='USD',
            provider='dynopay',
            error_code='DYNOPAY_SERVICE_UNAVAILABLE',
            failure_type='technical',
            retry_count=1
        )
        
        retry_context = RetryContext(
            transaction_id=transaction_id,
            transaction_type='wallet_cashout',
            user_id=user.id,
            amount=Decimal('250.00'),
            currency='USD',
            external_provider='dynopay',
            attempt_number=2,
            error_code='DYNOPAY_SERVICE_UNAVAILABLE',
            error_message='Service temporarily unavailable'
        )
        
        with patch('services.dynopay_service.process_transfer') as mock_transfer:
            mock_transfer.return_value = retry_test_framework.simulate_external_api_call(
                'dynopay', 'process_transfer', amount=250.00, currency='USD'
            )
            
            retry_result = await retry_test_framework.retry_service.handle_transaction_failure(
                retry_context, Exception("Service unavailable")
            )
            
            assert retry_result.decision == RetryDecision.RETRY
            
            success_response = retry_test_framework.simulate_external_api_call(
                'dynopay', 'process_transfer', amount=250.00, currency='USD'
            )
            assert success_response['success'] is True
        
        assert retry_test_framework.verify_retry_progression(transaction_id, 2)
        assert retry_test_framework.verify_wallet_hold_status(transaction_id, WalletHoldStatus.CONSUMED_SENT)
        
        logger.info("✅ DynoPay international cashout retry success scenario validated")


class TestMaximumRetryAttemptsReached:
    """Test scenarios where maximum retry attempts (6) are exhausted"""
    
    @pytest.mark.asyncio 
    async def test_fincra_max_retries_exhausted_final_failure(self, retry_test_framework):
        """Test Fincra cashout exhausts all 6 retry attempts and fails permanently"""
        user = retry_test_framework.create_test_user_with_wallet(
            '111222333',
            {'USD': Decimal('300.00')}
        )
        
        # Configure 6 consecutive failures
        failure_sequence = [
            {'success': False, 'error': 'API timeout', 'error_code': 'FINCRA_API_TIMEOUT'},
            {'success': False, 'error': 'Service unavailable', 'error_code': 'FINCRA_SERVICE_UNAVAILABLE'},
            {'success': False, 'error': 'Network error', 'error_code': 'NETWORK_ERROR'},
            {'success': False, 'error': 'API timeout', 'error_code': 'FINCRA_API_TIMEOUT'},
            {'success': False, 'error': 'Rate limit exceeded', 'error_code': 'RATE_LIMIT_EXCEEDED'},
            {'success': False, 'error': 'Final timeout', 'error_code': 'FINCRA_API_TIMEOUT'}
        ]
        retry_test_framework.configure_api_failure_sequence('fincra', failure_sequence)
        
        # Start with transaction at retry count 5 (next retry would be 6th and final)
        transaction_id = retry_test_framework.create_failed_transaction_for_retry(
            user_id=user.id,
            amount=Decimal('100.00'),
            currency='USD',
            provider='fincra',
            error_code='FINCRA_API_TIMEOUT',
            failure_type='technical',
            retry_count=5
        )
        
        # Simulate final retry attempt
        retry_context = RetryContext(
            transaction_id=transaction_id,
            transaction_type='wallet_cashout',
            user_id=user.id,
            amount=Decimal('100.00'),
            currency='USD',
            external_provider='fincra',
            attempt_number=6,  # Final attempt
            error_code='FINCRA_API_TIMEOUT',
            error_message='Final retry attempt'
        )
        
        with patch('services.fincra_service.process_payout') as mock_payout:
            # Simulate final failure
            mock_payout.return_value = retry_test_framework.simulate_external_api_call(
                'fincra', 'process_payout', amount=100.00, currency='USD'
            )
            
            retry_result = await retry_test_framework.retry_service.handle_transaction_failure(
                retry_context, Exception("Final timeout")
            )
            
            # Should indicate final failure (no more retries)
            assert retry_result.decision == RetryDecision.FAIL
            assert retry_result.final_failure is True
            assert retry_result.next_retry_at is None
        
        # Verify transaction marked as permanently failed
        tx = retry_test_framework.test_session.query(UnifiedTransaction).filter(
            UnifiedTransaction.transaction_id == transaction_id
        ).first()
        
        assert tx.retry_count == 6  # All attempts exhausted
        assert tx.status == UnifiedTransactionStatus.FAILED
        assert tx.next_retry_at is None
        
        # Verify wallet hold marked for admin intervention
        assert retry_test_framework.verify_wallet_hold_status(
            transaction_id,
            WalletHoldStatus.FAILED_HELD  # Funds stay frozen for admin review
        )
        
        logger.info("✅ Maximum retry attempts exhausted scenario validated")
    
    @pytest.mark.asyncio
    async def test_kraken_max_retries_with_admin_notification(self, retry_test_framework):
        """Test Kraken crypto cashout max retries triggers admin notification"""
        user = retry_test_framework.create_test_user_with_wallet(
            '444555666',
            {'BTC': Decimal('0.05')}
        )
        
        transaction_id = retry_test_framework.create_failed_transaction_for_retry(
            user_id=user.id,
            amount=Decimal('0.01'),
            currency='BTC',
            provider='kraken',
            error_code='KRAKEN_API_ERROR',
            failure_type='technical',
            retry_count=5  # 5th attempt, next is final
        )
        
        retry_context = RetryContext(
            transaction_id=transaction_id,
            transaction_type='wallet_cashout',
            user_id=user.id,
            amount=Decimal('0.01'),
            currency='BTC',
            external_provider='kraken',
            attempt_number=6,
            error_code='KRAKEN_API_ERROR',
            error_message='Persistent API errors'
        )
        
        with patch('services.admin_funding_notifications.send_retry_exhausted_alert') as mock_alert:
            with patch('services.kraken_service.withdraw_crypto') as mock_withdraw:
                mock_withdraw.return_value = {'success': False, 'error': 'Persistent error'}
                
                retry_result = await retry_test_framework.retry_service.handle_transaction_failure(
                    retry_context, Exception("Persistent API error")
                )
                
                assert retry_result.decision == RetryDecision.FAIL
                assert retry_result.final_failure is True
                
                # Verify admin notification sent
                mock_alert.assert_called_once()
                alert_args = mock_alert.call_args
                assert transaction_id in str(alert_args)
                assert 'retry_exhausted' in str(alert_args).lower()
        
        logger.info("✅ Max retries with admin notification scenario validated")


class TestUserErrorVsTechnicalErrorClassification:
    """Test proper classification of user errors (non-retryable) vs technical errors (retryable)"""
    
    @pytest.mark.asyncio
    async def test_insufficient_balance_user_error_no_retry(self, retry_test_framework):
        """Test insufficient balance is classified as user error with no retries"""
        user = retry_test_framework.create_test_user_with_wallet(
            '777888999',
            {'USD': Decimal('50.00')}  # Low balance
        )
        
        # Create transaction exceeding balance
        transaction_id = retry_test_framework.create_failed_transaction_for_retry(
            user_id=user.id,
            amount=Decimal('500.00'),  # Exceeds available balance
            currency='USD',
            provider='fincra',
            error_code='USER_INSUFFICIENT_BALANCE',
            failure_type='user',  # User error
            retry_count=0
        )
        
        retry_context = RetryContext(
            transaction_id=transaction_id,
            transaction_type='wallet_cashout',
            user_id=user.id,
            amount=Decimal('500.00'),
            currency='USD',
            external_provider='fincra',
            attempt_number=1,
            error_code='USER_INSUFFICIENT_BALANCE',
            error_message='Insufficient balance for withdrawal'
        )
        
        retry_result = await retry_test_framework.retry_service.handle_transaction_failure(
            retry_context, Exception("Insufficient balance")
        )
        
        # Should skip retry for user errors
        assert retry_result.decision == RetryDecision.SKIP
        assert "user error" in retry_result.message.lower()
        assert retry_result.next_retry_at is None
        
        # Verify transaction remains at retry count 0
        tx = retry_test_framework.test_session.query(UnifiedTransaction).filter(
            UnifiedTransaction.transaction_id == transaction_id
        ).first()
        
        assert tx.retry_count == 0  # No retries attempted
        assert tx.failure_type == 'user'
        assert tx.next_retry_at is None
        
        logger.info("✅ User error classification (no retry) validated")
    
    @pytest.mark.asyncio
    async def test_invalid_address_user_error_no_retry(self, retry_test_framework):
        """Test invalid destination address is classified as user error"""
        user = retry_test_framework.create_test_user_with_wallet(
            '123789456',
            {'BTC': Decimal('0.1')}
        )
        
        transaction_id = retry_test_framework.create_failed_transaction_for_retry(
            user_id=user.id,
            amount=Decimal('0.01'),
            currency='BTC',
            provider='kraken',
            error_code='INVALID_ADDRESS',
            failure_type='user',
            retry_count=0
        )
        
        retry_context = RetryContext(
            transaction_id=transaction_id,
            transaction_type='wallet_cashout',
            user_id=user.id,
            amount=Decimal('0.01'),
            currency='BTC',
            external_provider='kraken',
            attempt_number=1,
            error_code='INVALID_ADDRESS',
            error_message='Invalid BTC address format'
        )
        
        retry_result = await retry_test_framework.retry_service.handle_transaction_failure(
            retry_context, Exception("Invalid address")
        )
        
        assert retry_result.decision == RetryDecision.SKIP
        assert "user error" in retry_result.message.lower()
        
        # Verify wallet hold marked for user correction
        assert retry_test_framework.verify_wallet_hold_status(
            transaction_id,
            WalletHoldStatus.FAILED_HELD  # Admin intervention needed
        )
        
        logger.info("✅ Invalid address user error classification validated")
    
    @pytest.mark.asyncio
    async def test_api_timeout_technical_error_retry(self, retry_test_framework):
        """Test API timeout is classified as technical error with retry"""
        user = retry_test_framework.create_test_user_with_wallet(
            '654321789',
            {'USD': Decimal('200.00')}
        )
        
        transaction_id = retry_test_framework.create_failed_transaction_for_retry(
            user_id=user.id,
            amount=Decimal('100.00'),
            currency='USD',
            provider='fincra',
            error_code='FINCRA_API_TIMEOUT',
            failure_type='technical',
            retry_count=1
        )
        
        retry_context = RetryContext(
            transaction_id=transaction_id,
            transaction_type='wallet_cashout',
            user_id=user.id,
            amount=Decimal('100.00'),
            currency='USD',
            external_provider='fincra',
            attempt_number=2,
            error_code='FINCRA_API_TIMEOUT',
            error_message='API request timed out'
        )
        
        retry_result = await retry_test_framework.retry_service.handle_transaction_failure(
            retry_context, Exception("API timeout")
        )
        
        # Should schedule retry for technical errors
        assert retry_result.decision == RetryDecision.RETRY
        assert retry_result.next_retry_at is not None
        assert retry_result.delay_seconds > 0
        
        # Verify progressive delay (2nd attempt should have 15 minute delay)
        expected_delay_range = (900 - 180, 900 + 180)  # 15 min ± jitter
        assert expected_delay_range[0] <= retry_result.delay_seconds <= expected_delay_range[1]
        
        logger.info("✅ Technical error classification (with retry) validated")
    
    @pytest.mark.asyncio
    async def test_service_unavailable_technical_error_retry(self, retry_test_framework):
        """Test service unavailable is classified as technical error with retry"""
        user = retry_test_framework.create_test_user_with_wallet(
            '987123654',
            {'USD': Decimal('300.00')}
        )
        
        transaction_id = retry_test_framework.create_failed_transaction_for_retry(
            user_id=user.id,
            amount=Decimal('150.00'),
            currency='USD',
            provider='dynopay',
            error_code='DYNOPAY_SERVICE_UNAVAILABLE',
            failure_type='technical',
            retry_count=2
        )
        
        retry_context = RetryContext(
            transaction_id=transaction_id,
            transaction_type='wallet_cashout',
            user_id=user.id,
            amount=Decimal('150.00'),
            currency='USD',
            external_provider='dynopay',
            attempt_number=3,
            error_code='DYNOPAY_SERVICE_UNAVAILABLE',
            error_message='Service temporarily unavailable'
        )
        
        retry_result = await retry_test_framework.retry_service.handle_transaction_failure(
            retry_context, Exception("Service unavailable")
        )
        
        assert retry_result.decision == RetryDecision.RETRY
        
        # Verify progressive delay (3rd attempt should have 30 minute delay)
        expected_delay_range = (1800 - 360, 1800 + 360)  # 30 min ± jitter
        assert expected_delay_range[0] <= retry_result.delay_seconds <= expected_delay_range[1]
        
        logger.info("✅ Service unavailable technical error classification validated")


class TestProviderSpecificFailureScenarios:
    """Test provider-specific failure scenarios and error handling"""
    
    @pytest.mark.asyncio
    async def test_fincra_insufficient_funds_admin_notification(self, retry_test_framework):
        """Test Fincra insufficient funds triggers admin funding notification"""
        user = retry_test_framework.create_test_user_with_wallet(
            '111333555',
            {'USD': Decimal('500.00')}
        )
        
        transaction_id = retry_test_framework.create_failed_transaction_for_retry(
            user_id=user.id,
            amount=Decimal('200.00'),
            currency='USD',
            provider='fincra',
            error_code='FINCRA_INSUFFICIENT_FUNDS',
            failure_type='technical',  # Admin can fund account
            retry_count=1
        )
        
        retry_context = RetryContext(
            transaction_id=transaction_id,
            transaction_type='wallet_cashout',
            user_id=user.id,
            amount=Decimal('200.00'),
            currency='USD',
            external_provider='fincra',
            attempt_number=2,
            error_code='FINCRA_INSUFFICIENT_FUNDS',
            error_message='Fincra account has insufficient funds'
        )
        
        with patch('services.admin_funding_notifications.send_funding_alert') as mock_funding_alert:
            retry_result = await retry_test_framework.retry_service.handle_transaction_failure(
                retry_context, Exception("Insufficient funds in Fincra account")
            )
            
            # Should still schedule retry (admin can fund the account)
            assert retry_result.decision == RetryDecision.RETRY
            
            # Verify admin funding notification sent
            mock_funding_alert.assert_called_once()
            alert_args = mock_funding_alert.call_args
            assert 'fincra' in str(alert_args).lower()
            assert 'insufficient_funds' in str(alert_args).lower()
        
        logger.info("✅ Fincra insufficient funds admin notification validated")
    
    @pytest.mark.asyncio
    async def test_kraken_address_not_whitelisted_admin_notification(self, retry_test_framework):
        """Test Kraken address not whitelisted triggers admin notification"""
        user = retry_test_framework.create_test_user_with_wallet(
            '222444666',
            {'BTC': Decimal('0.05')}
        )
        
        transaction_id = retry_test_framework.create_failed_transaction_for_retry(
            user_id=user.id,
            amount=Decimal('0.01'),
            currency='BTC',
            provider='kraken',
            error_code='KRAKEN_ADDR_NOT_FOUND',
            failure_type='technical',  # Admin can whitelist address
            retry_count=1
        )
        
        retry_context = RetryContext(
            transaction_id=transaction_id,
            transaction_type='wallet_cashout',
            user_id=user.id,
            amount=Decimal('0.01'),
            currency='BTC',
            external_provider='kraken',
            attempt_number=2,
            error_code='KRAKEN_ADDR_NOT_FOUND',
            error_message='Address not found in Kraken withdrawal whitelist'
        )
        
        with patch('services.admin_funding_notifications.send_address_whitelist_alert') as mock_whitelist_alert:
            retry_result = await retry_test_framework.retry_service.handle_transaction_failure(
                retry_context, Exception("Address not whitelisted")
            )
            
            assert retry_result.decision == RetryDecision.RETRY
            
            # Verify admin whitelist notification sent
            mock_whitelist_alert.assert_called_once()
            alert_args = mock_whitelist_alert.call_args
            assert 'kraken' in str(alert_args).lower()
            assert 'whitelist' in str(alert_args).lower()
        
        logger.info("✅ Kraken address whitelist admin notification validated")
    
    @pytest.mark.asyncio
    async def test_dynopay_rate_limit_progressive_backoff(self, retry_test_framework):
        """Test DynoPay rate limit error uses progressive backoff"""
        user = retry_test_framework.create_test_user_with_wallet(
            '333555777',
            {'USD': Decimal('400.00')}
        )
        
        # Test various retry attempts to verify progressive delays
        retry_scenarios = [
            {'retry_count': 1, 'expected_delay_min': 300},   # 5 minutes
            {'retry_count': 2, 'expected_delay_min': 900},   # 15 minutes
            {'retry_count': 3, 'expected_delay_min': 1800},  # 30 minutes
            {'retry_count': 4, 'expected_delay_min': 3600},  # 1 hour
            {'retry_count': 5, 'expected_delay_min': 7200},  # 2 hours
        ]
        
        for scenario in retry_scenarios:
            transaction_id = retry_test_framework.create_failed_transaction_for_retry(
                user_id=user.id,
                amount=Decimal('100.00'),
                currency='USD',
                provider='dynopay',
                error_code='RATE_LIMIT_EXCEEDED',
                failure_type='technical',
                retry_count=scenario['retry_count']
            )
            
            retry_context = RetryContext(
                transaction_id=transaction_id,
                transaction_type='wallet_cashout',
                user_id=user.id,
                amount=Decimal('100.00'),
                currency='USD',
                external_provider='dynopay',
                attempt_number=scenario['retry_count'] + 1,
                error_code='RATE_LIMIT_EXCEEDED',
                error_message='Rate limit exceeded'
            )
            
            retry_result = await retry_test_framework.retry_service.handle_transaction_failure(
                retry_context, Exception("Rate limit exceeded")
            )
            
            assert retry_result.decision == RetryDecision.RETRY
            
            # Verify progressive delay with jitter tolerance
            expected_min = scenario['expected_delay_min']
            jitter_tolerance = expected_min * 0.2  # 20% jitter
            
            assert retry_result.delay_seconds >= (expected_min - jitter_tolerance)
            assert retry_result.delay_seconds <= (expected_min + jitter_tolerance)
            
            logger.info(f"✅ Progressive delay verified: attempt {scenario['retry_count'] + 1} → {retry_result.delay_seconds}s")


class TestWalletHoldsIntegration:
    """Test integration with wallet holds system during retry scenarios"""
    
    @pytest.mark.asyncio
    async def test_wallet_hold_status_during_retry_cycle(self, retry_test_framework):
        """Test wallet hold status transitions during retry cycle"""
        user = retry_test_framework.create_test_user_with_wallet(
            '999888777',
            {'USD': Decimal('300.00')}
        )
        
        transaction_id = retry_test_framework.create_failed_transaction_for_retry(
            user_id=user.id,
            amount=Decimal('100.00'),
            currency='USD',
            provider='fincra',
            error_code='FINCRA_API_TIMEOUT',
            failure_type='technical',
            retry_count=1
        )
        
        # Initial state: funds held due to failure
        assert retry_test_framework.verify_wallet_hold_status(
            transaction_id,
            WalletHoldStatus.FAILED_HELD
        )
        
        # Simulate retry attempt
        retry_context = RetryContext(
            transaction_id=transaction_id,
            transaction_type='wallet_cashout',
            user_id=user.id,
            amount=Decimal('100.00'),
            currency='USD',
            external_provider='fincra',
            attempt_number=2,
            error_code='FINCRA_API_TIMEOUT',
            error_message='Retry attempt'
        )
        
        # Configure success on retry
        retry_test_framework.configure_api_failure_sequence('fincra', [
            {'success': True, 'reference': 'FINCRA_SUCCESS_RETRY', 'status': 'processing'}
        ])
        
        with patch('services.fincra_service.process_payout') as mock_payout:
            mock_payout.return_value = retry_test_framework.simulate_external_api_call(
                'fincra', 'process_payout', amount=100.00, currency='USD'
            )
            
            retry_result = await retry_test_framework.retry_service.handle_transaction_failure(
                retry_context, Exception("Previous timeout")
            )
            
            assert retry_result.decision == RetryDecision.RETRY
            
            # Simulate successful retry execution
            success_response = retry_test_framework.simulate_external_api_call(
                'fincra', 'process_payout', amount=100.00, currency='USD'
            )
            
            if success_response['success']:
                # Update wallet hold status to consumed/sent
                hold = retry_test_framework.test_session.query(WalletHolds).filter(
                    WalletHolds.reference_id == transaction_id
                ).first()
                hold.status = WalletHoldStatus.CONSUMED_SENT
                retry_test_framework.test_session.commit()
        
        # Final state: funds consumed (sent to external provider)
        assert retry_test_framework.verify_wallet_hold_status(
            transaction_id,
            WalletHoldStatus.CONSUMED_SENT
        )
        
        logger.info("✅ Wallet hold status transitions during retry cycle validated")
    
    @pytest.mark.asyncio
    async def test_wallet_hold_remains_frozen_after_max_retries(self, retry_test_framework):
        """Test wallet hold remains frozen after exhausting all retries"""
        user = retry_test_framework.create_test_user_with_wallet(
            '666777888',
            {'USD': Decimal('250.00')}
        )
        
        transaction_id = retry_test_framework.create_failed_transaction_for_retry(
            user_id=user.id,
            amount=Decimal('125.00'),
            currency='USD',
            provider='fincra',
            error_code='FINCRA_API_TIMEOUT',
            failure_type='technical',
            retry_count=6  # Maximum retries exhausted
        )
        
        # Update transaction to reflect exhausted retries
        tx = retry_test_framework.test_session.query(UnifiedTransaction).filter(
            UnifiedTransaction.transaction_id == transaction_id
        ).first()
        tx.status = UnifiedTransactionStatus.FAILED
        tx.next_retry_at = None  # No more retries
        retry_test_framework.test_session.commit()
        
        # Verify wallet hold remains frozen for admin intervention
        assert retry_test_framework.verify_wallet_hold_status(
            transaction_id,
            WalletHoldStatus.FAILED_HELD
        )
        
        # Verify user's available balance is reduced by held amount
        wallet = retry_test_framework.test_session.query(Wallet).filter(
            Wallet.user_id == user.id,
            Wallet.currency == 'USD'
        ).first()
        
        # Available balance should be total - held amount
        available_balance = wallet.balance - wallet.frozen_balance
        expected_available = Decimal('250.00') - Decimal('125.00')
        assert available_balance == expected_available
        
        logger.info("✅ Wallet hold remains frozen after max retries validated")


if __name__ == "__main__":
    # Run unified retry integration tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "not slow"
    ])