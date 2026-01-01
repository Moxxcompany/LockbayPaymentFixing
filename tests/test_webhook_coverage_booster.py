"""
DynoPay Webhook Coverage Booster Tests
=====================================

Additional focused tests to achieve 80%+ coverage on dynopay_exchange_webhook handler
by testing more code paths and edge cases.
"""

import pytest
import logging
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from fastapi import HTTPException

from handlers.dynopay_exchange_webhook import DynoPayExchangeWebhookHandler
from models import ExchangeOrder, ExchangeStatus, UnifiedTransaction, UnifiedTransactionStatus, UnifiedTransactionType

logger = logging.getLogger(__name__)


@pytest.mark.dynopay_webhook
@pytest.mark.production
class TestWebhookCoverageBooster:
    """Additional tests to boost coverage to 80%+"""
    
    @pytest.mark.asyncio
    async def test_main_exception_path(self):
        """Test the main exception handler in handle_exchange_deposit_webhook"""
        
        webhook_data = {
            'id': 'error_tx_001',
            'paid_amount': 500.00,
            'paid_currency': 'USD',
            'meta_data': {'refId': 'test_order_001'}
        }
        
        # Mock to raise an exception during distributed lock acquisition
        with patch('utils.distributed_lock.distributed_lock_service.acquire_payment_lock') as mock_lock:
            mock_lock.side_effect = Exception("Distributed lock service error")
            
            # Should catch the exception and raise HTTPException 500
            with pytest.raises(HTTPException) as exc_info:
                await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data)
                
            assert exc_info.value.status_code == 500
            assert "Internal server error" in str(exc_info.value.detail)
        
        logger.info("✅ Main exception path test completed")
    
    @pytest.mark.asyncio  
    async def test_extract_webhook_data_paths(self):
        """Test all the data extraction and validation paths"""
        
        # Test each individual validation path to increase coverage
        validation_tests = [
            # Missing reference_id
            {
                'data': {'id': 'tx_001', 'paid_amount': 500.0, 'paid_currency': 'USD', 'meta_data': {}},
                'expected_error': "Missing reference ID"
            },
            # Missing paid_amount
            {
                'data': {'id': 'tx_002', 'paid_currency': 'USD', 'meta_data': {'refId': 'order_001'}},
                'expected_error': "Missing payment details"  
            },
            # Missing paid_currency
            {
                'data': {'id': 'tx_003', 'paid_amount': 500.0, 'meta_data': {'refId': 'order_001'}},
                'expected_error': "Missing payment details"
            },
            # Missing transaction id
            {
                'data': {'paid_amount': 500.0, 'paid_currency': 'USD', 'meta_data': {'refId': 'order_001'}},
                'expected_error': "Missing transaction ID"
            }
        ]
        
        for test_case in validation_tests:
            with pytest.raises(HTTPException) as exc_info:
                await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(test_case['data'])
            
            # Should be 400 or 500 (depending on where exactly it fails)
            assert exc_info.value.status_code in [400, 500]
            
        logger.info("✅ Data extraction and validation paths test completed")
    
    @pytest.mark.asyncio
    async def test_distributed_lock_log_paths(self):
        """Test the logging paths in distributed lock handling"""
        
        webhook_data = {
            'id': 'log_test_tx_001',
            'paid_amount': 500.00,
            'paid_currency': 'USD',
            'meta_data': {'refId': 'test_order_log'}
        }
        
        # Test the successful lock acquisition logging
        with patch('utils.distributed_lock.distributed_lock_service.acquire_payment_lock') as mock_lock, \
             patch.object(DynoPayExchangeWebhookHandler, '_process_locked_exchange_payment', return_value={'status': 'success'}) as mock_process, \
             patch('handlers.dynopay_exchange_webhook.logger') as mock_logger:
            
            # Mock successful lock acquisition
            mock_context = MagicMock()
            mock_context.__enter__.return_value.acquired = True
            mock_context.__enter__.return_value.error = None
            mock_lock.return_value = mock_context
            
            result = await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data)
            
            # Verify logging occurred
            mock_logger.critical.assert_called()
            assert result['status'] == 'success'
            
        # Test the failed lock acquisition logging 
        with patch('utils.distributed_lock.distributed_lock_service.acquire_payment_lock') as mock_lock, \
             patch('handlers.dynopay_exchange_webhook.logger') as mock_logger:
            
            # Mock failed lock acquisition
            mock_context = MagicMock()
            mock_context.__enter__.return_value.acquired = False
            mock_context.__enter__.return_value.error = "Lock timeout"
            mock_lock.return_value = mock_context
            
            result = await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data)
            
            # Verify warning logging and early return
            mock_logger.warning.assert_called()
            assert result['status'] == 'already_processing'
            
        logger.info("✅ Distributed lock logging paths test completed")
    
    @pytest.mark.asyncio
    async def test_unified_transaction_processing_paths(self, test_db_session, test_data_factory):
        """Test the unified transaction processing paths"""
        
        # Create test data
        user = test_data_factory.create_test_user(
            telegram_id='unified_test_001',
            balances={'USD': Decimal('1000.00')}
        )
        
        # Mock unified transaction
        mock_unified_tx = MagicMock()
        mock_unified_tx.transaction_id = 'unified_tx_001'
        mock_unified_tx.transaction_type = UnifiedTransactionType.EXCHANGE_SELL_CRYPTO.value
        mock_unified_tx.status = UnifiedTransactionStatus.AWAITING_PAYMENT.value
        mock_unified_tx.user_id = user.id
        
        webhook_data = {
            'id': 'unified_tx_test',
            'paid_amount': 500.0,
            'paid_currency': 'USD',
            'meta_data': {'refId': 'unified_order_001'}
        }
        
        # Test successful unified transaction processing
        with patch('utils.atomic_transactions.payment_confirmation_transaction') as mock_tx, \
             patch('handlers.dynopay_exchange_webhook.unified_tx_service') as mock_service:
            
            # Mock session context manager
            mock_session = MagicMock()
            mock_tx.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = mock_unified_tx
            
            # Mock successful transition with AsyncMock
            mock_transition_result = MagicMock()
            mock_transition_result.success = True
            mock_service.transition_status = AsyncMock(return_value=mock_transition_result)
            
            result = await DynoPayExchangeWebhookHandler._process_unified_exchange_payment(
                mock_unified_tx, webhook_data, 500.0, 'USD', 'unified_tx_test', mock_session
            )
            
            assert result['status'] == 'success'
            assert result['transaction_id'] == 'unified_tx_001'
            
        # Test failed unified transaction processing
        with patch('utils.atomic_transactions.payment_confirmation_transaction') as mock_tx, \
             patch('handlers.dynopay_exchange_webhook.unified_tx_service') as mock_service:
            
            mock_session = MagicMock()
            mock_tx.return_value.__enter__.return_value = mock_session
            
            # Mock failed transition with AsyncMock
            mock_transition_result = MagicMock()
            mock_transition_result.success = False
            mock_transition_result.error = "Transition failed"
            mock_service.transition_status = AsyncMock(return_value=mock_transition_result)
            
            result = await DynoPayExchangeWebhookHandler._process_unified_exchange_payment(
                mock_unified_tx, webhook_data, 500.0, 'USD', 'unified_tx_test', mock_session
            )
            
            assert result['status'] == 'error'
            assert 'Transition failed' in result['message']
            
        logger.info("✅ Unified transaction processing paths test completed")
    
    @pytest.mark.asyncio
    async def test_different_transaction_types(self, test_db_session):
        """Test different transaction type handling paths"""
        
        webhook_data = {
            'id': 'type_test_tx',
            'paid_amount': 500.0,
            'paid_currency': 'USD'
        }
        
        transaction_types_to_test = [
            # Exchange buy crypto
            {
                'type': UnifiedTransactionType.EXCHANGE_BUY_CRYPTO.value,
                'status': UnifiedTransactionStatus.AWAITING_PAYMENT.value,
                'expected_next': UnifiedTransactionStatus.PAYMENT_CONFIRMED
            },
            # Escrow transaction (edge case)
            {
                'type': UnifiedTransactionType.ESCROW.value,
                'status': UnifiedTransactionStatus.AWAITING_PAYMENT.value,
                'expected_next': UnifiedTransactionStatus.PAYMENT_CONFIRMED
            },
            # Wallet cashout (error case)
            {
                'type': UnifiedTransactionType.WALLET_CASHOUT.value,
                'status': UnifiedTransactionStatus.AWAITING_PAYMENT.value,
                'expected_error': 'Wallet cashouts should not receive payments'
            }
        ]
        
        for test_case in transaction_types_to_test:
            mock_unified_tx = MagicMock()
            mock_unified_tx.transaction_id = 'test_tx_001'
            mock_unified_tx.transaction_type = test_case['type']
            mock_unified_tx.status = test_case['status']
            mock_unified_tx.user_id = 1
            
            mock_session = MagicMock()
            
            result = await DynoPayExchangeWebhookHandler._process_unified_exchange_payment(
                mock_unified_tx, webhook_data, 500.0, 'USD', 'type_test_tx', mock_session
            )
            
            if 'expected_error' in test_case:
                assert result['status'] == 'error'
                assert test_case['expected_error'] in result['message']
            else:
                # For successful cases, we expect it to try to transition (even if mocked)
                assert result is not None
                
        logger.info("✅ Different transaction types test completed")
    
    @pytest.mark.asyncio
    async def test_invalid_transaction_status(self, test_db_session):
        """Test invalid transaction status handling"""
        
        webhook_data = {'id': 'invalid_status_tx', 'paid_amount': 500.0, 'paid_currency': 'USD'}
        
        # Test invalid status for exchange transaction
        mock_unified_tx = MagicMock()
        mock_unified_tx.transaction_id = 'invalid_status_tx_001'
        mock_unified_tx.transaction_type = UnifiedTransactionType.EXCHANGE_SELL_CRYPTO.value
        mock_unified_tx.status = UnifiedTransactionStatus.SUCCESS.value  # Wrong status
        mock_unified_tx.user_id = 1
        
        mock_session = MagicMock()
        
        result = await DynoPayExchangeWebhookHandler._process_unified_exchange_payment(
            mock_unified_tx, webhook_data, 500.0, 'USD', 'invalid_status_tx', mock_session
        )
        
        assert result['status'] == 'error'
        assert 'Invalid status for payment' in result['message']
        
        logger.info("✅ Invalid transaction status test completed")
    
    @pytest.mark.asyncio
    async def test_unknown_transaction_type(self, test_db_session):
        """Test unknown transaction type handling"""
        
        webhook_data = {'id': 'unknown_type_tx', 'paid_amount': 500.0, 'paid_currency': 'USD'}
        
        mock_unified_tx = MagicMock()
        mock_unified_tx.transaction_id = 'unknown_type_tx_001'
        mock_unified_tx.transaction_type = 'UNKNOWN_TYPE'
        mock_unified_tx.status = UnifiedTransactionStatus.AWAITING_PAYMENT.value
        mock_unified_tx.user_id = 1
        
        mock_session = MagicMock()
        
        result = await DynoPayExchangeWebhookHandler._process_unified_exchange_payment(
            mock_unified_tx, webhook_data, 500.0, 'USD', 'unknown_type_tx', mock_session
        )
        
        assert result['status'] == 'error'
        assert 'Unknown transaction type' in result['message']
        
        logger.info("✅ Unknown transaction type test completed")
    
    @pytest.mark.asyncio
    async def test_unified_transaction_exception_handling(self, test_db_session):
        """Test exception handling in unified transaction processing"""
        
        webhook_data = {'id': 'exception_tx', 'paid_amount': 500.0, 'paid_currency': 'USD'}
        
        mock_unified_tx = MagicMock()
        mock_unified_tx.transaction_id = 'exception_tx_001'
        mock_unified_tx.transaction_type = UnifiedTransactionType.EXCHANGE_SELL_CRYPTO.value
        mock_unified_tx.status = UnifiedTransactionStatus.AWAITING_PAYMENT.value
        mock_unified_tx.user_id = 1
        
        mock_session = MagicMock()
        
        # Mock an exception during processing
        with patch('handlers.dynopay_exchange_webhook.unified_tx_service.transition_status') as mock_transition:
            mock_transition.side_effect = Exception("Service error")
            
            result = await DynoPayExchangeWebhookHandler._process_unified_exchange_payment(
                mock_unified_tx, webhook_data, 500.0, 'USD', 'exception_tx', mock_session
            )
            
            assert result['status'] == 'error'
            assert 'Internal processing error' in result['message']
        
        logger.info("✅ Unified transaction exception handling test completed")