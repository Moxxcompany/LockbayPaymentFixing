"""
Comprehensive Coverage Tests - Focused on 100% Coverage Achievement
================================================================

This test suite is specifically designed to achieve 100% test coverage across
critical system components with clean, isolated tests that avoid complex dependencies.

Target Modules:
- handlers/dynopay_exchange_webhook.py (34% -> 100%)
- services/crypto.py (coverage TBD -> 100%)  
- services/consolidated_notification_service.py (coverage TBD -> 100%)
- utils/atomic_transactions.py (coverage TBD -> 100%)
- utils/distributed_lock.py (coverage TBD -> 100%)
"""

import pytest
import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from fastapi import HTTPException

# Test configuration
pytestmark = pytest.mark.asyncio

logger = logging.getLogger(__name__)


class TestDynoPayWebhookComprehensiveCoverage:
    """
    Comprehensive coverage tests for DynoPay webhook handler
    Target: Cover all uncovered lines and branches to achieve 100% coverage
    """
    
    async def test_webhook_validation_missing_reference_id(self):
        """Test validation error path - missing reference_id"""
        from handlers.dynopay_exchange_webhook import DynoPayExchangeWebhookHandler
        
        webhook_data = {
            'id': 'test_tx_001',
            'paid_amount': 100.0,
            'paid_currency': 'USD',
            'meta_data': {}  # Missing refId
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data)
        
        assert exc_info.value.status_code == 400
        assert "Missing reference ID" in str(exc_info.value.detail)
    
    async def test_webhook_validation_missing_payment_details(self):
        """Test validation error paths - missing payment details"""
        from handlers.dynopay_exchange_webhook import DynoPayExchangeWebhookHandler
        
        # Test missing paid_amount
        webhook_data = {
            'id': 'test_tx_002',
            'paid_currency': 'USD',
            'meta_data': {'refId': 'EXC_123'}
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data)
        
        assert exc_info.value.status_code == 400
        assert "Missing payment details" in str(exc_info.value.detail)
        
        # Test missing paid_currency
        webhook_data = {
            'id': 'test_tx_003',
            'paid_amount': 100.0,
            'meta_data': {'refId': 'EXC_123'}
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data)
        
        assert exc_info.value.status_code == 400
        assert "Missing payment details" in str(exc_info.value.detail)
    
    async def test_webhook_validation_missing_transaction_id(self):
        """Test validation error path - missing transaction_id"""
        from handlers.dynopay_exchange_webhook import DynoPayExchangeWebhookHandler
        
        webhook_data = {
            'paid_amount': 100.0,
            'paid_currency': 'USD',
            'meta_data': {'refId': 'EXC_123'}
            # Missing 'id' field
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data)
        
        assert exc_info.value.status_code == 400
        assert "Missing transaction ID" in str(exc_info.value.detail)
    
    async def test_webhook_security_validation_development_mode(self):
        """Test security validation in development mode"""
        from handlers.dynopay_exchange_webhook import DynoPayExchangeWebhookHandler
        from config import Config
        
        webhook_data = {
            'id': 'test_tx_004',
            'paid_amount': 100.0,
            'paid_currency': 'USD',
            'meta_data': {'refId': 'EXC_123'}
        }
        
        # Mock development environment
        with patch.object(Config, 'ENV', 'development'), \
             patch('utils.webhook_security.WebhookSecurity.verify_dynopay_webhook', return_value=True), \
             patch('handlers.dynopay_exchange_webhook.DynoPayExchangeWebhookHandler._log_webhook_event', new_callable=AsyncMock), \
             patch('handlers.dynopay_exchange_webhook.DynoPayExchangeWebhookHandler._process_locked_exchange_payment', new_callable=AsyncMock) as mock_process:
            
            mock_process.return_value = {"status": "success", "message": "Payment processed"}
            
            # This should work in development mode with no signature
            result = await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data, headers=None)
            
            assert result["status"] == "success"
    
    async def test_distributed_lock_scenarios(self):
        """Test distributed lock acquisition scenarios"""
        from handlers.dynopay_exchange_webhook import DynoPayExchangeWebhookHandler
        
        webhook_data = {
            'id': 'test_tx_005',
            'paid_amount': 100.0,
            'paid_currency': 'USD',
            'meta_data': {'refId': 'EXC_123'}
        }
        
        # Mock successful lock acquisition
        with patch('utils.webhook_security.WebhookSecurity.verify_dynopay_webhook', return_value=True), \
             patch('handlers.dynopay_exchange_webhook.DynoPayExchangeWebhookHandler._log_webhook_event', new_callable=AsyncMock), \
             patch('handlers.dynopay_exchange_webhook.distributed_lock_service.acquire_payment_lock') as mock_lock:
            
            # Test lock acquisition failure
            mock_lock_result = Mock()
            mock_lock_result.acquired = False
            mock_lock_result.error = "Lock contention"
            mock_lock.__enter__ = Mock(return_value=mock_lock_result)
            mock_lock.__exit__ = Mock(return_value=False)
            
            result = await DynoPayExchangeWebhookHandler.handle_exchange_deposit_webhook(webhook_data)
            
            assert result["status"] == "already_processing"
            assert "Exchange payment is being processed" in result["message"]


class TestCryptoServiceComprehensiveCoverage:
    """
    Comprehensive coverage tests for CryptoServiceAtomic
    Target: Achieve 100% line and branch coverage
    """
    
    @pytest.mark.asyncio
    async def test_get_real_time_exchange_rate_usd(self):
        """Test USD exchange rate (should return 1.0)"""
        from services.crypto import CryptoServiceAtomic
        
        rate = await CryptoServiceAtomic.get_real_time_exchange_rate("USD")
        assert rate == 1.0
    
    @pytest.mark.asyncio
    async def test_get_real_time_exchange_rate_with_api(self):
        """Test exchange rate with FastForex API"""
        from services.crypto import CryptoServiceAtomic
        from config import Config
        
        with patch.object(Config, 'FASTFOREX_API_KEY', 'test_key'), \
             patch('services.fastforex_service.fastforex_service.get_crypto_to_usd_rate', new_callable=AsyncMock) as mock_rate:
            
            mock_rate.return_value = 50000.0
            
            rate = await CryptoServiceAtomic.get_real_time_exchange_rate("BTC")
            assert rate == 50000.0
    
    @pytest.mark.asyncio
    async def test_get_real_time_exchange_rate_api_failure(self):
        """Test exchange rate API failure handling"""
        from services.crypto import CryptoServiceAtomic
        from services.fastforex_service import FastForexAPIError
        from config import Config
        
        with patch.object(Config, 'FASTFOREX_API_KEY', 'test_key'), \
             patch('services.fastforex_service.fastforex_service.get_crypto_to_usd_rate', new_callable=AsyncMock) as mock_rate:
            
            mock_rate.side_effect = FastForexAPIError("API Error")
            
            with pytest.raises(ValueError, match="Real-time exchange rate service unavailable"):
                await CryptoServiceAtomic.get_real_time_exchange_rate("BTC")
    
    @pytest.mark.asyncio
    async def test_get_real_time_exchange_rate_no_api_key(self):
        """Test exchange rate without API key"""
        from services.crypto import CryptoServiceAtomic
        from config import Config
        
        with patch.object(Config, 'FASTFOREX_API_KEY', None):
            with pytest.raises(ValueError, match="Real-time exchange rate service unavailable"):
                await CryptoServiceAtomic.get_real_time_exchange_rate("BTC")
    
    @pytest.mark.asyncio
    async def test_generate_wallet_deposit_address_success(self):
        """Test successful wallet deposit address generation"""
        from services.crypto import CryptoServiceAtomic
        from config import Config
        
        # Mock successful address generation
        with patch.object(Config, 'WEBHOOK_URL', 'https://test.com'), \
             patch('services.payment_processor_manager.payment_manager.create_payment_address', new_callable=AsyncMock) as mock_create:
            
            mock_create.return_value = (
                {
                    'success': True,
                    'address': 'bc1qtest123',
                    'amount': 1.0,
                    'currency': 'BTC'
                }, 
                'dynopay'
            )
            
            result = await CryptoServiceAtomic.generate_wallet_deposit_address("BTC", 123)
            
            assert result['success'] is True
            assert result['address'] == 'bc1qtest123'
    
    @pytest.mark.asyncio
    async def test_generate_wallet_deposit_address_no_webhook_url(self):
        """Test wallet deposit address generation without webhook URL"""
        from services.crypto import CryptoServiceAtomic
        from config import Config
        
        with patch.object(Config, 'WEBHOOK_URL', None), \
             patch.object(Config, 'BLOCKBEE_CALLBACK_URL', None):
            
            with pytest.raises(ValueError, match="No webhook URL configured"):
                await CryptoServiceAtomic.generate_wallet_deposit_address("BTC", 123)


class TestConsolidatedNotificationServiceCoverage:
    """
    Comprehensive coverage tests for ConsolidatedNotificationService
    Target: Achieve 100% line and branch coverage of all notification channels
    """
    
    def test_notification_service_initialization(self):
        """Test notification service initialization"""
        from services.consolidated_notification_service import ConsolidatedNotificationService
        
        service = ConsolidatedNotificationService()
        
        assert service.email_service is not None
        assert service.delivery_stats is not None
        assert service.initialized is False  # Not initialized until async init
    
    @pytest.mark.asyncio
    async def test_notification_service_async_initialization(self):
        """Test async initialization of notification service"""
        from services.consolidated_notification_service import ConsolidatedNotificationService
        
        with patch('services.consolidated_notification_service.Config') as mock_config:
            mock_config.TWILIO_ACCOUNT_SID = "test_sid"
            mock_config.TWILIO_AUTH_TOKEN = "test_token"
            
            service = ConsolidatedNotificationService()
            await service.initialize()
            
            assert service.initialized is True
    
    @pytest.mark.asyncio
    async def test_telegram_notification_success(self):
        """Test successful Telegram notification delivery"""
        from services.consolidated_notification_service import (
            ConsolidatedNotificationService,
            NotificationRequest,
            NotificationChannel,
            NotificationCategory,
            NotificationPriority
        )
        
        service = ConsolidatedNotificationService()
        
        with patch('telegram.Bot.send_message', new_callable=AsyncMock) as mock_send:
            mock_send.return_value.message_id = 123
            
            notification = NotificationRequest(
                user_id=456,
                category=NotificationCategory.PAYMENTS,
                priority=NotificationPriority.NORMAL,
                title="Test Payment",
                message="Payment successful",
                channels=[NotificationChannel.TELEGRAM]
            )
            
            result = await service._send_telegram_notification(notification, 456)
            
            assert result.status.value == "sent"
            assert result.message_id == "123"
    
    @pytest.mark.asyncio
    async def test_email_notification_success(self):
        """Test successful email notification delivery"""
        from services.consolidated_notification_service import (
            ConsolidatedNotificationService,
            NotificationRequest,
            NotificationChannel,
            NotificationCategory,
            NotificationPriority
        )
        
        service = ConsolidatedNotificationService()
        
        with patch.object(service.email_service, 'send_notification_email', new_callable=AsyncMock) as mock_email:
            mock_email.return_value = {
                'success': True,
                'message_id': 'email_123'
            }
            
            notification = NotificationRequest(
                user_id=456,
                category=NotificationCategory.PAYMENTS,
                priority=NotificationPriority.NORMAL,
                title="Test Payment",
                message="Payment successful",
                channels=[NotificationChannel.EMAIL]
            )
            
            result = await service._send_email_notification(notification, "test@example.com")
            
            assert result.status.value == "sent"
            assert result.message_id == "email_123"


class TestAtomicTransactionsCoverage:
    """
    Comprehensive coverage tests for atomic transactions utility
    Target: Cover all transaction contexts, rollback scenarios, sync/async patterns
    """
    
    @pytest.mark.asyncio
    async def test_async_atomic_transaction_success(self):
        """Test successful async atomic transaction"""
        from utils.atomic_transactions import async_atomic_transaction
        
        async with async_atomic_transaction() as session:
            # Transaction should be created successfully
            assert session is not None
            # Session should have the expected attributes for database operations
            assert hasattr(session, 'add')
            assert hasattr(session, 'commit')
            assert hasattr(session, 'rollback')
    
    def test_sync_atomic_transaction_success(self):
        """Test successful sync atomic transaction"""
        from utils.atomic_transactions import atomic_transaction
        
        with atomic_transaction() as session:
            # Transaction should be created successfully
            assert session is not None
            # Session should have the expected attributes for database operations
            assert hasattr(session, 'add')
            assert hasattr(session, 'commit')
            assert hasattr(session, 'rollback')
    
    @pytest.mark.asyncio
    async def test_async_atomic_transaction_with_provided_session(self):
        """Test async atomic transaction with provided session"""
        from utils.atomic_transactions import async_atomic_transaction
        from database import managed_session
        
        async with managed_session() as provided_session:
            async with async_atomic_transaction(provided_session) as session:
                # Should use the provided session
                assert session is provided_session
                # Should track transaction depth
                assert hasattr(session, '_atomic_transaction_depth')


class TestDistributedLockCoverage:
    """
    Comprehensive coverage tests for distributed lock service
    Target: Cover acquisition, release, timeout, contention scenarios, cleanup
    """
    
    def test_distributed_lock_service_initialization(self):
        """Test distributed lock service initialization"""
        from utils.distributed_lock import DistributedLockService
        
        service = DistributedLockService(default_timeout=300)
        
        assert service.default_timeout == 300
        assert service.service_id.startswith("lockservice_")
    
    def test_generate_lock_key(self):
        """Test lock key generation"""
        from utils.distributed_lock import DistributedLockService
        
        service = DistributedLockService()
        
        key = service.generate_lock_key("payment", "order_123", "additional")
        
        assert isinstance(key, str)
        assert len(key) == 32  # SHA256 hash truncated to 32 chars
        
        # Same inputs should generate same key
        key2 = service.generate_lock_key("payment", "order_123", "additional")
        assert key == key2
        
        # Different inputs should generate different keys
        key3 = service.generate_lock_key("payment", "order_456", "additional")
        assert key != key3
    
    def test_acquire_payment_lock_context_manager_interface(self):
        """Test payment lock context manager interface"""
        from utils.distributed_lock import DistributedLockService
        
        service = DistributedLockService()
        
        # Test the context manager interface
        lock_context = service.acquire_payment_lock("order_123", "tx_456")
        
        # Should have context manager methods
        assert hasattr(lock_context, '__enter__')
        assert hasattr(lock_context, '__exit__')