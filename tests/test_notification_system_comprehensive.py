"""
Comprehensive Notification System End-to-End Tests
Tests the complete notification flow including:
- Payment confirmations with Telegram available
- Payment confirmations with Telegram failure (email fallback)
- Overpayment/underpayment notifications
- Admin notifications
- Unified notification service for all channels
"""

import pytest
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from telegram.error import TelegramError

from database import managed_session
from services.consolidated_notification_service import (
    ConsolidatedNotificationService,
    NotificationRequest,
    NotificationChannel,
    NotificationPriority,
    NotificationCategory,
    DeliveryStatus
)
from models import User, Escrow, EscrowStatus, Wallet, UserStatus
from config import Config
from sqlalchemy import select, delete

logger = logging.getLogger(__name__)


# No fixtures needed - using managed_session() directly


async def cleanup_test_data(test_user_id: int):
    """Clean up test data"""
    async with managed_session() as session:
        # Delete test escrows
        await session.execute(delete(Escrow).where(Escrow.buyer_id == test_user_id))
        # Delete test wallets
        await session.execute(delete(Wallet).where(Wallet.user_id == test_user_id))
        # Delete test user
        await session.execute(delete(User).where(User.id == test_user_id))
        await session.commit()


async def create_test_user() -> User:
    """Create a test user with verified email and telegram"""
    test_user_id = 999888777  # Unique test user ID
    
    # Clean up any existing test data
    await cleanup_test_data(test_user_id)
    
    async with managed_session() as session:
        user = User(
            id=test_user_id,
            telegram_id=test_user_id,
            username="test_notification_user",
            first_name="Test",
            last_name="User",
            email="test_notifications@example.com",
            email_verified=True,
            is_verified=True,
            status=UserStatus.ACTIVE,
            phone_number="+2348012345678",
            phone_verified=True,
            created_at=datetime.utcnow()
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        # Create wallet for user
        wallet = Wallet(
            user_id=user.id,
            currency="USD",
            balance=Decimal("100.00"),
            frozen_balance=Decimal("0.00")
        )
        session.add(wallet)
        await session.commit()
        
        return user


async def create_test_escrow(user_id: int) -> Escrow:
    """Create a test escrow for payment confirmation tests"""
    async with managed_session() as session:
        escrow = Escrow(
            escrow_id="ES092925TEST",
            buyer_id=user_id,
            amount=Decimal("100.00"),
            currency="USD",
            status=EscrowStatus.PAYMENT_PENDING,
            payment_address="test_btc_address_12345",
            rate=Decimal("50000.00"),
            expected_crypto_amount=Decimal("0.002"),
            rate_locked_until=datetime.utcnow() + timedelta(hours=1),
            created_at=datetime.utcnow()
        )
        session.add(escrow)
        await session.commit()
        await session.refresh(escrow)
        return escrow


@pytest.mark.asyncio
async def test_exact_payment_telegram_notification():
    """Test payment confirmation notification with exact amount via Telegram"""
    logger.info("🧪 TEST: Exact payment confirmation via Telegram")
    
    # Create test data
    test_user = await create_test_user()
    test_escrow = await create_test_escrow(test_user.id)
    notification_service = ConsolidatedNotificationService()
    
    try:
        # Initialize service
        await notification_service.initialize()
        
        # Create notification request for exact payment
        notification_request = NotificationRequest(
            user_id=test_user.id,
            category=NotificationCategory.PAYMENTS,
            priority=NotificationPriority.HIGH,
            title="💰 Payment Confirmed",
            message=f"Your payment of 0.002 BTC ($100.00) for escrow {test_escrow.escrow_id} has been confirmed!",
            template_data={
                "escrow_id": test_escrow.escrow_id,
                "amount_crypto": "0.002",
                "amount_usd": "100.00",
                "currency": "BTC",
                "payment_type": "exact"
            },
            channels=[NotificationChannel.TELEGRAM, NotificationChannel.EMAIL],
            require_delivery=True,
            broadcast_mode=False
        )
        
        # Mock Telegram bot to succeed
        with patch('telegram.Bot.send_message', new_callable=AsyncMock) as mock_telegram:
            mock_telegram.return_value = Mock(message_id=12345)
            
            # Send notification
            results = await notification_service.send_notification(notification_request)
            
            # Verify Telegram was attempted
            assert mock_telegram.called, "Telegram send_message should be called"
            logger.info(f"✅ Telegram notification sent - Results: {list(results.keys())}")
            
            # Verify at least one successful delivery
            successful = any(
                r.status in [DeliveryStatus.SENT, DeliveryStatus.DELIVERED]
                for r in results.values()
            )
            assert successful, f"At least one channel should succeed. Results: {results}"
            
            logger.info("✅ Exact payment notification test passed")
    
    finally:
        # Cleanup
        await cleanup_test_data(test_user.id)


@pytest.mark.asyncio
async def test_telegram_failure_email_fallback():
    """Test that email fallback activates when Telegram fails"""
    logger.info("🧪 TEST: Telegram failure triggers email fallback")
    
    # Create test data
    test_user = await create_test_user()
    test_escrow = await create_test_escrow(test_user.id)
    notification_service = ConsolidatedNotificationService()
    
    try:
        # Initialize service
        await notification_service.initialize()
        
        # Create notification request
        notification_request = NotificationRequest(
            user_id=test_user.id,
            category=NotificationCategory.PAYMENTS,
            priority=NotificationPriority.HIGH,
            title="💰 Payment Confirmed",
            message=f"Your payment for escrow {test_escrow.escrow_id} has been confirmed!",
            template_data={
                "escrow_id": test_escrow.escrow_id,
                "amount": "100.00",
                "currency": "USD"
            },
            channels=[NotificationChannel.TELEGRAM, NotificationChannel.EMAIL],
            require_delivery=True,
            broadcast_mode=False
        )
        
        # Mock Telegram to fail and email to succeed
        with patch('telegram.Bot.send_message', new_callable=AsyncMock) as mock_telegram, \
             patch.object(notification_service.email_service, 'send_email') as mock_email:
            
            # Telegram fails
            mock_telegram.side_effect = TelegramError("Bot was blocked by the user")
            
            # Email succeeds
            mock_email.return_value = True
            
            # Send notification
            results = await notification_service.send_notification(notification_request)
            
            # Verify Telegram was attempted
            assert mock_telegram.called, "Telegram should be attempted first"
            
            # Verify email fallback was triggered
            assert mock_email.called, "Email fallback should be triggered"
            
            logger.info(f"✅ Email fallback activated - Results: {list(results.keys())}")
            
            # Verify at least one successful delivery (email)
            successful = any(
                r.status in [DeliveryStatus.SENT, DeliveryStatus.DELIVERED]
                for r in results.values()
            )
            assert successful, "Email fallback should succeed"
            
            logger.info("✅ Email fallback test passed")
    
    finally:
        # Cleanup
        await cleanup_test_data(test_user.id)


@pytest.mark.asyncio
async def test_overpayment_notification_with_rate_data():
    """Test overpayment notification when rate data is available"""
    logger.info("🧪 TEST: Overpayment notification with rate data")
    
    # Create test data
    test_user = await create_test_user()
    test_escrow = await create_test_escrow(test_user.id)
    notification_service = ConsolidatedNotificationService()
    
    try:
        await notification_service.initialize()
        
        # Simulate overpayment: expected 0.002 BTC, received 0.0025 BTC
        expected_crypto = Decimal("0.002")
        received_crypto = Decimal("0.0025")
        overpayment = received_crypto - expected_crypto
        
        # Calculate USD values using rate
        rate = test_escrow.rate
        expected_usd = expected_crypto * rate
        received_usd = received_crypto * rate
        overpayment_usd = overpayment * rate
        
        notification_request = NotificationRequest(
            user_id=test_user.id,
            category=NotificationCategory.PAYMENTS,
            priority=NotificationPriority.HIGH,
            title="⚠️ Overpayment Detected",
            message=(
                f"⚠️ Overpayment detected for escrow {test_escrow.escrow_id}\n\n"
                f"Expected: {expected_crypto} BTC (${expected_usd:.2f})\n"
                f"Received: {received_crypto} BTC (${received_usd:.2f})\n"
                f"Overpayment: {overpayment} BTC (${overpayment_usd:.2f})\n\n"
                f"The excess will be credited to your wallet."
            ),
            template_data={
                "escrow_id": test_escrow.escrow_id,
                "expected_crypto": str(expected_crypto),
                "received_crypto": str(received_crypto),
                "overpayment_crypto": str(overpayment),
                "expected_usd": str(expected_usd),
                "received_usd": str(received_usd),
                "overpayment_usd": str(overpayment_usd),
                "currency": "BTC",
                "rate": str(rate)
            },
            channels=[NotificationChannel.TELEGRAM, NotificationChannel.EMAIL],
            require_delivery=True,
            broadcast_mode=True
        )
        
        # Mock both channels to succeed
        with patch('telegram.Bot.send_message', new_callable=AsyncMock) as mock_telegram, \
             patch.object(notification_service.email_service, 'send_email') as mock_email:
            
            mock_telegram.return_value = Mock(message_id=12345)
            mock_email.return_value = True
            
            # Send notification
            results = await notification_service.send_notification(notification_request)
            
            # In broadcast mode, both channels should be attempted
            assert mock_telegram.called, "Telegram should be attempted"
            logger.info(f"✅ Overpayment notification sent - Results: {list(results.keys())}")
            
            # Verify at least one successful delivery
            successful = any(
                r.status in [DeliveryStatus.SENT, DeliveryStatus.DELIVERED]
                for r in results.values()
            )
            assert successful, "At least one channel should succeed"
            
            logger.info("✅ Overpayment notification test passed")
    
    finally:
        # Cleanup
        await cleanup_test_data(test_user.id)


@pytest.mark.asyncio
async def test_underpayment_notification_with_rate_data():
    """Test underpayment notification when rate data is available"""
    logger.info("🧪 TEST: Underpayment notification with rate data")
    
    # Create test data
    test_user = await create_test_user()
    test_escrow = await create_test_escrow(test_user.id)
    notification_service = ConsolidatedNotificationService()
    
    try:
        await notification_service.initialize()
        
        # Simulate underpayment: expected 0.002 BTC, received 0.0015 BTC
        expected_crypto = Decimal("0.002")
        received_crypto = Decimal("0.0015")
        shortfall = expected_crypto - received_crypto
        
        # Calculate USD values using rate
        rate = test_escrow.rate
        expected_usd = expected_crypto * rate
        received_usd = received_crypto * rate
        shortfall_usd = shortfall * rate
        
        notification_request = NotificationRequest(
            user_id=test_user.id,
            category=NotificationCategory.PAYMENTS,
            priority=NotificationPriority.CRITICAL,
            title="❌ Underpayment Detected",
            message=(
                f"❌ Underpayment detected for escrow {test_escrow.escrow_id}\n\n"
                f"Expected: {expected_crypto} BTC (${expected_usd:.2f})\n"
                f"Received: {received_crypto} BTC (${received_usd:.2f})\n"
                f"Shortfall: {shortfall} BTC (${shortfall_usd:.2f})\n\n"
                f"Please send the remaining amount to complete the escrow."
            ),
            template_data={
                "escrow_id": test_escrow.escrow_id,
                "expected_crypto": str(expected_crypto),
                "received_crypto": str(received_crypto),
                "shortfall_crypto": str(shortfall),
                "expected_usd": str(expected_usd),
                "received_usd": str(received_usd),
                "shortfall_usd": str(shortfall_usd),
                "currency": "BTC",
                "rate": str(rate)
            },
            channels=[NotificationChannel.TELEGRAM, NotificationChannel.EMAIL],
            require_delivery=True,
            broadcast_mode=True
        )
        
        # Mock both channels
        with patch('telegram.Bot.send_message', new_callable=AsyncMock) as mock_telegram, \
             patch.object(notification_service.email_service, 'send_email') as mock_email:
            
            mock_telegram.return_value = Mock(message_id=12346)
            mock_email.return_value = True
            
            # Send notification
            results = await notification_service.send_notification(notification_request)
            
            # Both should be attempted in broadcast mode
            assert mock_telegram.called, "Telegram should be attempted"
            logger.info(f"✅ Underpayment notification sent - Results: {list(results.keys())}")
            
            # Verify at least one successful delivery
            successful = any(
                r.status in [DeliveryStatus.SENT, DeliveryStatus.DELIVERED]
                for r in results.values()
            )
            assert successful, "At least one channel should succeed"
            
            logger.info("✅ Underpayment notification test passed")
    
    finally:
        # Cleanup
        await cleanup_test_data(test_user.id)


@pytest.mark.asyncio
async def test_admin_payment_notification():
    """Test that admin notifications work for payment events"""
    logger.info("🧪 TEST: Admin payment notification")
    
    # Create test data
    test_user = await create_test_user()
    test_escrow = await create_test_escrow(test_user.id)
    notification_service = ConsolidatedNotificationService()
    
    try:
        await notification_service.initialize()
        
        # Get admin IDs from config
        admin_ids = getattr(Config, 'ADMIN_IDS', [5590563715])
        if not admin_ids:
            admin_ids = [5590563715]
        
        admin_id = admin_ids[0]
        
        # Create admin notification
        notification_request = NotificationRequest(
            user_id=admin_id,
            category=NotificationCategory.ADMIN_ALERTS,
            priority=NotificationPriority.HIGH,
            title="🔔 New Payment Received",
            message=(
                f"💰 Payment received for escrow {test_escrow.escrow_id}\n"
                f"Buyer: {test_user.username} (ID: {test_user.id})\n"
                f"Amount: {test_escrow.amount} {test_escrow.currency}\n"
                f"Status: Payment confirmed\n"
            ),
            template_data={
                "escrow_id": test_escrow.escrow_id,
                "buyer_id": test_user.id,
                "buyer_username": test_user.username,
                "amount": str(test_escrow.amount),
                "currency": test_escrow.currency
            },
            channels=[NotificationChannel.ADMIN_ALERT],
            require_delivery=True,
            admin_notification=True
        )
        
        # Mock Telegram for admin
        with patch('telegram.Bot.send_message', new_callable=AsyncMock) as mock_telegram:
            mock_telegram.return_value = Mock(message_id=12347)
            
            # Send admin notification
            results = await notification_service.send_notification(notification_request)
            
            # Verify admin notification was attempted
            logger.info(f"✅ Admin notification sent - Results: {list(results.keys())}")
            
            # Admin alerts should always attempt delivery
            assert len(results) > 0, "Should have delivery results"
            
            logger.info("✅ Admin notification test passed")
    
    finally:
        # Cleanup
        await cleanup_test_data(test_user.id)


@pytest.mark.asyncio
async def test_notification_service_initialization():
    """Test notification service initializes all channels correctly"""
    logger.info("🧪 TEST: Notification service initialization")
    
    notification_service = ConsolidatedNotificationService()
    # Initialize service
    initialized = await notification_service.initialize()
    
    assert initialized, "Notification service should initialize successfully"
    assert notification_service.initialized, "Service should be marked as initialized"
    
    # Check available channels
    available_channels = notification_service._get_available_channels()
    logger.info(f"✅ Available channels: {[ch.value for ch in available_channels]}")
    
    # Should have at least admin alerts available
    assert NotificationChannel.ADMIN_ALERT in available_channels, \
        "Admin alerts should always be available"
    
    logger.info("✅ Notification service initialization test passed")


@pytest.mark.asyncio
async def test_complete_notification_flow_integration():
    """Integration test for complete notification flow"""
    logger.info("🧪 INTEGRATION TEST: Complete notification flow")
    
    service = ConsolidatedNotificationService()
    test_user = await create_test_user()
    test_escrow = await create_test_escrow(test_user.id)
    
    try:
        await service.initialize()
        
        # Test 1: Telegram working
        logger.info("📱 Test 1: Telegram working")
        with patch('telegram.Bot.send_message', new_callable=AsyncMock) as mock_telegram:
            mock_telegram.return_value = Mock(message_id=12349)
            
            notification = NotificationRequest(
                user_id=test_user.id,
                category=NotificationCategory.PAYMENTS,
                priority=NotificationPriority.HIGH,
                title="💰 Payment Confirmed",
                message=f"Payment confirmed for {test_escrow.escrow_id}",
                channels=[NotificationChannel.TELEGRAM, NotificationChannel.EMAIL],
                broadcast_mode=False
            )
            
            results = await service.send_notification(notification)
            assert len(results) > 0, "Should have results"
            logger.info("✅ Test 1 passed")
        
        # Test 2: Telegram fails, email fallback
        logger.info("📧 Test 2: Telegram fails, email fallback")
        with patch('telegram.Bot.send_message', new_callable=AsyncMock) as mock_telegram, \
             patch.object(service.email_service, 'send_email') as mock_email:
            
            mock_telegram.side_effect = TelegramError("User blocked bot")
            mock_email.return_value = True
            
            notification = NotificationRequest(
                user_id=test_user.id,
                category=NotificationCategory.PAYMENTS,
                priority=NotificationPriority.HIGH,
                title="💰 Payment Confirmed",
                message=f"Payment confirmed for {test_escrow.escrow_id}",
                channels=[NotificationChannel.TELEGRAM, NotificationChannel.EMAIL],
                broadcast_mode=False
            )
            
            results = await service.send_notification(notification)
            assert mock_email.called, "Email fallback should be called"
            logger.info("✅ Test 2 passed")
        
        # Test 3: Admin notification
        logger.info("👨‍💼 Test 3: Admin notification")
        admin_ids = getattr(Config, 'ADMIN_IDS', [5590563715])
        admin_id = admin_ids[0] if admin_ids else 5590563715
        
        with patch('telegram.Bot.send_message', new_callable=AsyncMock) as mock_telegram:
            mock_telegram.return_value = Mock(message_id=12350)
            
            admin_notification = NotificationRequest(
                user_id=admin_id,
                category=NotificationCategory.ADMIN_ALERTS,
                priority=NotificationPriority.HIGH,
                title="🔔 System Alert",
                message="Payment system operational",
                channels=[NotificationChannel.ADMIN_ALERT],
                admin_notification=True
            )
            
            results = await service.send_notification(admin_notification)
            assert len(results) > 0, "Should have admin results"
            logger.info("✅ Test 3 passed")
        
        logger.info("🎉 Complete integration test passed!")
    
    finally:
        # Cleanup
        await cleanup_test_data(test_user.id)


if __name__ == "__main__":
    """Run tests directly for quick verification"""
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s", "--log-cli-level=INFO"]))
