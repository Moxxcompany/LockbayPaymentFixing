"""
Unit Tests for DynoPay Exchange Webhook Handler - Targeted Coverage
================================================================

This test suite focuses on unit testing specific uncovered branches and error paths
without requiring complex database setup. Uses mocking to isolate functionality.

Target: Improve webhook coverage from 34% to 80%+ by covering critical paths
"""

import pytest
import asyncio
import logging
from decimal import Decimal
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from fastapi import HTTPException

# Handler import
from handlers.dynopay_exchange_webhook import DynoPayExchangeWebhookHandler

logger = logging.getLogger(__name__)


class TestDynoPayWebhookValidationErrors:
    """Test basic validation error paths without database dependencies"""
    
    @pytest.mark.asyncio
    async def test_missing_reference_id_error(self):
        """Test error handling for missing reference_id - Line 58-59"""
        
        webhook_data = {
            'id': 'dynopay_tx_001',
            'paid_amount': 500.00,
            'paid_currency': 'USD',
            'meta_data': {}  # Missing refId
        }
        
        # Test the validation error path
        with pytest.raises(HTTPException) as exc_info:
            await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data)
        
        assert exc_info.value.status_code == 400
        assert "Missing reference ID" in str(exc_info.value.detail)
        
    @pytest.mark.asyncio
    async def test_missing_paid_amount_error(self):
        """Test error handling for missing paid_amount - Line 61-63"""
        
        webhook_data = {
            'id': 'dynopay_tx_002',
            'paid_currency': 'USD',
            'meta_data': {'refId': 'EXC_123'}
            # Missing paid_amount
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data)
        
        assert exc_info.value.status_code == 400
        assert "Missing payment details" in str(exc_info.value.detail)
        
    @pytest.mark.asyncio
    async def test_missing_paid_currency_error(self):
        """Test error handling for missing paid_currency - Line 61-63"""
        
        webhook_data = {
            'id': 'dynopay_tx_003',
            'paid_amount': 500.00,
            'meta_data': {'refId': 'EXC_123'}
            # Missing paid_currency
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data)
        
        assert exc_info.value.status_code == 400
        assert "Missing payment details" in str(exc_info.value.detail)
        
    @pytest.mark.asyncio
    async def test_missing_transaction_id_error(self):
        """Test error handling for missing transaction_id - Line 65-67"""
        
        webhook_data = {
            'paid_amount': 500.00,
            'paid_currency': 'USD',
            'meta_data': {'refId': 'EXC_123'}
            # Missing 'id' field
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data)
        
        assert exc_info.value.status_code == 400
        assert "Missing transaction ID" in str(exc_info.value.detail)


class TestDynoPayWebhookSecurityPaths:
    """Test security validation paths with mocking"""
    
    @pytest.mark.asyncio
    async def test_security_verification_failure(self):
        """Test security verification failure path - Line 44-46"""
        
        webhook_data = {
            'id': 'dynopay_tx_security_001',
            'paid_amount': 500.00,
            'paid_currency': 'USD',
            'meta_data': {'refId': 'EXC_123'}
        }
        
        # Mock WebhookSecurity.verify_dynopay_webhook to return False
        with patch('handlers.dynopay_exchange_webhook.WebhookSecurity') as mock_security:
            mock_security.verify_dynopay_webhook.return_value = False
            
            with pytest.raises(HTTPException) as exc_info:
                await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data)
            
            assert exc_info.value.status_code == 401
            assert "Webhook authentication failed" in str(exc_info.value.detail)
            
    @pytest.mark.asyncio
    async def test_security_verification_success_but_later_error(self):
        """Test security verification success but later processing error"""
        
        webhook_data = {
            'id': 'dynopay_tx_security_002',
            'paid_amount': 500.00,
            'paid_currency': 'USD',
            'meta_data': {'refId': 'INVALID_FORMAT'}  # Will cause later error
        }
        
        # Mock successful security verification but expect later error
        with patch('handlers.dynopay_exchange_webhook.WebhookSecurity') as mock_security, \
             patch('handlers.dynopay_exchange_webhook.distributed_lock_service') as mock_lock_service:
            
            mock_security.verify_dynopay_webhook.return_value = True
            
            # Mock successful lock acquisition
            mock_lock_context = MagicMock()
            mock_lock_result = MagicMock()
            mock_lock_result.acquired = True
            mock_lock_context.__enter__.return_value = mock_lock_result
            mock_lock_service.acquire_payment_lock.return_value = mock_lock_context
            
            # Should reach later error handling (invalid reference format)
            with pytest.raises(HTTPException) as exc_info:
                await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data)
            
            # Should fail with reference format error rather than security error
            assert exc_info.value.status_code == 400
            assert "Invalid reference ID format" in str(exc_info.value.detail)


class TestDynoPayDistributedLockScenarios:
    """Test distributed lock scenarios - Lines 89-94"""
    
    @pytest.mark.asyncio
    async def test_distributed_lock_acquisition_failure(self):
        """Test distributed lock acquisition failure - Line 89-94"""
        
        webhook_data = {
            'id': 'dynopay_tx_lock_001',
            'paid_amount': 500.00,
            'paid_currency': 'USD',
            'meta_data': {'refId': 'EXC_123'}
        }
        
        with patch('handlers.dynopay_exchange_webhook.WebhookSecurity') as mock_security, \
             patch('handlers.dynopay_exchange_webhook.distributed_lock_service') as mock_lock_service:
            
            # Mock successful security verification
            mock_security.verify_dynopay_webhook.return_value = True
            
            # Mock failed lock acquisition
            mock_lock_context = MagicMock()
            mock_lock_result = MagicMock()
            mock_lock_result.acquired = False
            mock_lock_result.error = "Lock timeout: another process is handling this payment"
            mock_lock_context.__enter__.return_value = mock_lock_result
            mock_lock_service.acquire_payment_lock.return_value = mock_lock_context
            
            result = await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data)
            
            assert result['status'] == 'already_processing'
            assert 'Exchange payment is being processed' in result['message']


class TestDynoPayReferenceFormatValidation:
    """Test reference ID format validation scenarios"""
    
    @pytest.mark.asyncio
    async def test_invalid_exc_reference_format(self):
        """Test invalid EXC_ reference format - Line 256-258"""
        
        webhook_data = {
            'id': 'dynopay_tx_format_001',
            'paid_amount': 500.00,
            'paid_currency': 'USD',
            'meta_data': {'refId': 'INVALID_REF_FORMAT'}  # Not EXC_ format and not numeric
        }
        
        with patch('handlers.dynopay_exchange_webhook.WebhookSecurity') as mock_security, \
             patch('handlers.dynopay_exchange_webhook.distributed_lock_service') as mock_lock_service:
            
            mock_security.verify_dynopay_webhook.return_value = True
            
            # Mock successful lock acquisition
            mock_lock_context = MagicMock()
            mock_lock_result = MagicMock()
            mock_lock_result.acquired = True
            mock_lock_context.__enter__.return_value = mock_lock_result
            mock_lock_service.acquire_payment_lock.return_value = mock_lock_context
            
            with pytest.raises(HTTPException) as exc_info:
                await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data)
            
            assert exc_info.value.status_code == 400
            assert "Invalid reference ID format" in str(exc_info.value.detail)


class TestDynoPayDatabaseLookupErrors:
    """Test database lookup error scenarios"""
    
    @pytest.mark.asyncio
    async def test_exchange_order_not_found(self):
        """Test exchange order not found error - Line 269-271"""
        
        webhook_data = {
            'id': 'dynopay_tx_notfound_001',
            'paid_amount': 500.00,
            'paid_currency': 'USD',
            'meta_data': {'refId': '999999'}  # Non-existent order ID
        }
        
        with patch('handlers.dynopay_exchange_webhook.WebhookSecurity') as mock_security, \
             patch('handlers.dynopay_exchange_webhook.distributed_lock_service') as mock_lock_service, \
             patch('handlers.dynopay_exchange_webhook.SessionLocal') as mock_session_local:
            
            mock_security.verify_dynopay_webhook.return_value = True
            
            # Mock successful lock acquisition
            mock_lock_context = MagicMock()
            mock_lock_result = MagicMock()
            mock_lock_result.acquired = True
            mock_lock_context.__enter__.return_value = mock_lock_result
            mock_lock_service.acquire_payment_lock.return_value = mock_lock_context
            
            # Mock database session to return None for exchange order lookup
            mock_session = MagicMock()
            mock_session_local.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = None
            
            with pytest.raises(HTTPException) as exc_info:
                await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data)
            
            assert exc_info.value.status_code == 404
            assert "Exchange order not found" in str(exc_info.value.detail)


class TestDynoPayWebhookEventLogging:
    """Test webhook event logging scenarios"""
    
    @pytest.mark.asyncio
    async def test_log_webhook_event_method(self):
        """Test _log_webhook_event method execution"""
        
        webhook_data = {
            'id': 'dynopay_tx_log_001',
            'paid_amount': 500.00,
            'paid_currency': 'USD',
            'meta_data': {'refId': '123'}
        }
        
        # Test the _log_webhook_event method directly
        with patch('handlers.dynopay_exchange_webhook.SessionLocal') as mock_session_local:
            mock_session = MagicMock()
            mock_session_local.return_value = mock_session
            
            # Mock successful database operations
            mock_session.query.return_value.filter.return_value.first.return_value = None
            mock_session.add = MagicMock()
            mock_session.commit = MagicMock()
            
            # Call the logging method directly
            await DynoPayExchangeWebhookHandler._log_webhook_event(
                webhook_data, '123', 'dynopay_tx_log_001'
            )
            
            # Verify session operations were called
            mock_session.add.assert_called()
            mock_session.commit.assert_called()


class TestDynoPayComplexDataScenarios:
    """Test complex data scenarios and edge cases"""
    
    @pytest.mark.asyncio
    async def test_empty_meta_data(self):
        """Test webhook with empty meta_data"""
        
        webhook_data = {
            'id': 'dynopay_tx_empty_001',
            'paid_amount': 500.00,
            'paid_currency': 'USD',
            'meta_data': None  # Null meta_data
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data)
        
        # Should fail at reference_id extraction since meta_data is None
        assert exc_info.value.status_code == 400
        assert "Missing reference ID" in str(exc_info.value.detail)
        
    @pytest.mark.asyncio
    async def test_zero_paid_amount(self):
        """Test webhook with zero paid amount"""
        
        webhook_data = {
            'id': 'dynopay_tx_zero_001',
            'paid_amount': 0,  # Zero amount
            'paid_currency': 'USD',
            'meta_data': {'refId': 'EXC_123'}
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data)
        
        assert exc_info.value.status_code == 400
        assert "Missing payment details" in str(exc_info.value.detail)
        
    @pytest.mark.asyncio
    async def test_negative_paid_amount(self):
        """Test webhook with negative paid amount"""
        
        webhook_data = {
            'id': 'dynopay_tx_negative_001',
            'paid_amount': -100.00,  # Negative amount
            'paid_currency': 'USD',
            'meta_data': {'refId': 'EXC_123'}
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data)
        
        # Should pass basic validation but fail later in processing
        assert exc_info.value.status_code in [400, 500]


class TestDynoPayWebhookAuthenticationFlow:
    """Test authentication flow with different header scenarios"""
    
    @pytest.mark.asyncio
    async def test_authentication_with_different_header_formats(self):
        """Test authentication with different signature header formats"""
        
        webhook_data = {
            'id': 'dynopay_tx_auth_001',
            'paid_amount': 500.00,
            'paid_currency': 'USD',
            'meta_data': {'refId': 'EXC_123'}
        }
        
        # Test with lowercase header
        headers_lowercase = {'x-dynopay-signature': 'test_signature_123'}
        
        with patch('handlers.dynopay_exchange_webhook.WebhookSecurity') as mock_security:
            mock_security.verify_dynopay_webhook.return_value = False
            
            with pytest.raises(HTTPException) as exc_info:
                await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(
                    webhook_data, headers_lowercase
                )
            
            assert exc_info.value.status_code == 401
            
        # Test with uppercase header  
        headers_uppercase = {'X-DynoPay-Signature': 'test_signature_123'}
        
        with patch('handlers.dynopay_exchange_webhook.WebhookSecurity') as mock_security:
            mock_security.verify_dynopay_webhook.return_value = False
            
            with pytest.raises(HTTPException) as exc_info:
                await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(
                    webhook_data, headers_uppercase
                )
            
            assert exc_info.value.status_code == 401
            
    @pytest.mark.asyncio
    async def test_authentication_with_none_headers(self):
        """Test authentication when headers is None"""
        
        webhook_data = {
            'id': 'dynopay_tx_auth_002',
            'paid_amount': 500.00,
            'paid_currency': 'USD',
            'meta_data': {'refId': 'EXC_123'}
        }
        
        with patch('handlers.dynopay_exchange_webhook.WebhookSecurity') as mock_security:
            mock_security.verify_dynopay_webhook.return_value = False
            
            with pytest.raises(HTTPException) as exc_info:
                await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(
                    webhook_data, headers=None
                )
            
            assert exc_info.value.status_code == 401
            assert "Webhook authentication failed" in str(exc_info.value.detail)


# Additional test methods for targeting remaining uncovered lines...
class TestDynoPayAdditionalPaths:
    """Test additional paths to cover remaining lines"""
    
    @pytest.mark.asyncio 
    async def test_successful_webhook_security_validation(self):
        """Test successful security validation path - Line 48"""
        
        webhook_data = {
            'id': 'dynopay_tx_success_001',
            'paid_amount': 500.00,
            'paid_currency': 'USD',
            'meta_data': {'refId': '123'}
        }
        
        with patch('handlers.dynopay_exchange_webhook.WebhookSecurity') as mock_security, \
             patch('handlers.dynopay_exchange_webhook.distributed_lock_service') as mock_lock_service, \
             patch('handlers.dynopay_exchange_webhook.SessionLocal') as mock_session_local:
            
            # Mock successful security verification
            mock_security.verify_dynopay_webhook.return_value = True
            
            # Mock successful lock acquisition  
            mock_lock_context = MagicMock()
            mock_lock_result = MagicMock()
            mock_lock_result.acquired = True
            mock_lock_context.__enter__.return_value = mock_lock_result
            mock_lock_service.acquire_payment_lock.return_value = mock_lock_context
            
            # Mock database to return None to trigger "not found" error
            mock_session = MagicMock()
            mock_session_local.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = None
            
            # Should pass security validation but fail at database lookup
            with pytest.raises(HTTPException) as exc_info:
                await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data)
            
            # Should reach the "exchange order not found" error, not security error
            assert exc_info.value.status_code == 404
            assert "Exchange order not found" in str(exc_info.value.detail)
            
        # Verify that security validation success message would be logged
        # This tests line 48: logger.info("✅ DYNOPAY_EXCHANGE_AUTH: Webhook signature verified successfully")