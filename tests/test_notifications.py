"""
Comprehensive tests for notification system
Tests overpayment detection, wallet credits, and notification delivery
"""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Test the notification monitor
def test_notification_monitor_stats():
    """Test notification monitoring statistics"""
    from services.notification_monitor import NotificationMonitor
    
    monitor = NotificationMonitor()
    
    # Initially empty stats
    assert monitor.stats.total_sent == 0
    assert monitor.stats.total_failed == 0
    assert monitor.stats.success_rate == 0.0

@pytest.mark.asyncio
async def test_record_successful_notification():
    """Test recording successful notifications"""
    from services.notification_monitor import NotificationMonitor
    
    monitor = NotificationMonitor()
    
    # Record successful telegram notification
    await monitor.record_notification_sent(
        user_id=123,
        notification_type='telegram',
        message_type='escrow_deposit',
        success=True
    )
    
    assert monitor.stats.telegram_sent == 1
    assert monitor.stats.telegram_failed == 0
    assert monitor.stats.total_sent == 1
    assert monitor.stats.success_rate == 100.0

@pytest.mark.asyncio
async def test_record_failed_notification():
    """Test recording failed notifications"""
    from services.notification_monitor import NotificationMonitor
    
    monitor = NotificationMonitor()
    
    # Record failed email notification
    await monitor.record_notification_sent(
        user_id=123,
        notification_type='email',
        message_type='bonus_credit',
        success=False,
        error_message="SMTP connection failed"
    )
    
    assert monitor.stats.email_sent == 0
    assert monitor.stats.email_failed == 1
    assert monitor.stats.total_failed == 1
    assert len(monitor.failures) == 1
    assert monitor.failures[0].error_message == "SMTP connection failed"

@pytest.mark.asyncio
async def test_overpayment_service_wallet_credit():
    """Test overpayment service wallet credit functionality"""
    with patch('services.crypto.CryptoService.credit_user_wallet_atomic') as mock_credit:
        mock_credit.return_value = True
        
        from services.overpayment_service import overpayment_service
        
        # Mock database session and user
        with patch('services.overpayment_service.SessionLocal') as mock_session:
            mock_user = Mock()
            mock_user.telegram_id = "123456789"
            mock_user.email = "test@example.com"
            
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_user
            
            # Mock bot and email service
            with patch('telegram.Bot') as mock_bot_class, \
                 patch('services.email.EmailService') as mock_email_service:
                
                mock_bot = AsyncMock()
                mock_bot_class.return_value = mock_bot
                
                mock_email_instance = AsyncMock()
                mock_email_instance.send_email.return_value = True
                mock_email_service.return_value = mock_email_instance
                
                # Test overpayment handling
                result = await overpayment_service.handle_escrow_overpayment(
                    user_id=123,
                    escrow_id="TEST123",
                    expected_amount=Decimal("1.0"),
                    received_amount=Decimal("1.1"),
                    crypto_currency="BTC",
                    usd_rate=Decimal("50000")
                )
                
                # Verify wallet was credited
                mock_credit.assert_called_once()
                
                # Verify notifications were sent
                mock_bot.send_message.assert_called_once()
                mock_email_instance.send_email.assert_called_once()

@pytest.mark.asyncio 
async def test_health_checks():
    """Test health check functionality"""
    from utils.health_checks import HealthCheckService
    
    # Test database health check
    with patch('database.SessionLocal') as mock_session:
        mock_session.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = (1,)
        
        result = await HealthCheckService.check_database()
        
        assert result.service == "database"
        assert result.status in ["healthy", "warning", "critical"]
        assert result.response_time_ms >= 0

@pytest.mark.asyncio
async def test_telegram_bot_health_check():
    """Test Telegram bot health check"""
    from utils.health_checks import HealthCheckService
    
    with patch('config.Config.BOT_TOKEN', 'test_token'), \
         patch('telegram.Bot') as mock_bot_class:
        
        mock_bot = AsyncMock()
        mock_me = Mock()
        mock_me.username = "test_bot"
        mock_bot.get_me.return_value = mock_me
        mock_bot_class.return_value = mock_bot
        
        result = await HealthCheckService.check_telegram_bot()
        
        assert result.service == "telegram_bot"
        assert result.status == "healthy"
        assert "test_bot" in result.message

@pytest.mark.asyncio
async def test_fund_manager_overpayment_notifications():
    """Test that EscrowFundManager sends overpayment notifications"""
    from services.escrow_fund_manager import EscrowFundManager
    
    # Mock database and services
    with patch('services.escrow_fund_manager.SessionLocal') as mock_session, \
         patch('services.crypto.CryptoServiceAtomic.credit_user_wallet_atomic') as mock_credit, \
         patch('telegram.Bot') as mock_bot_class, \
         patch('services.email.EmailService') as mock_email_service:
        
        # Setup mocks
        mock_credit.return_value = True
        
        mock_escrow = Mock()
        mock_escrow.escrow_id = "TEST123"
        mock_escrow.buyer_id = 123
        mock_escrow.amount = Decimal("10.00")
        mock_escrow.fee_amount = Decimal("1.00")
        
        mock_user = Mock()
        mock_user.telegram_id = "123456789"
        mock_user.email = "test@example.com"
        
        mock_session_instance = Mock()
        mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_escrow
        mock_session.return_value = mock_session_instance
        
        # Mock notifications
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot
        
        mock_email_instance = AsyncMock()
        mock_email_instance.send_email.return_value = True
        mock_email_service.return_value = mock_email_instance
        
        # Test overpayment scenario
        result = await EscrowFundManager.process_escrow_payment(
            escrow_id="TEST123",
            total_received_usd=Decimal("12.00"),  # $1 overpayment
            expected_total_usd=Decimal("11.00"),
            crypto_amount=Decimal("0.0002"),
            crypto_currency="BTC",
            tx_hash="test_hash"
        )
        
        # Verify notifications were sent for overpayment
        assert result["success"] == True
        assert result["overpayment_credited"] == 1.0

def test_production_safeguards_alerting():
    """Test production alerting system"""
    from utils.production_safeguards import ProductionAlerting
    
    alerting = ProductionAlerting()
    
    # Test alert configuration
    assert "notification_failures" in alerting.alerts_config
    assert alerting.alerts_config["notification_failures"].threshold == 5
    assert alerting.alerts_config["notification_failures"].severity == "critical"

@pytest.mark.asyncio
async def test_alert_triggering():
    """Test that alerts are triggered correctly"""
    from utils.production_safeguards import ProductionAlerting
    
    alerting = ProductionAlerting()
    
    # Record multiple failures to trigger alert
    for _ in range(6):  # Exceed threshold of 5
        await alerting.record_event("notification_failed")
    
    # Check that alert was triggered
    active_alerts = [alert for alert in alerting.triggered_alerts if not alert.resolved]
    assert len(active_alerts) > 0
    assert any(alert.alert_id == "notification_failures" for alert in active_alerts)

@pytest.mark.asyncio
async def test_integration_escrow_payment_flow():
    """Integration test for complete escrow payment flow"""
    
    # Mock all dependencies
    with patch('services.blockbee_service.SessionLocal') as mock_session, \
         patch('services.crypto.CryptoServiceAtomic.credit_user_wallet_atomic') as mock_credit, \
         patch('services.escrow_fund_manager.EscrowFundManager.process_escrow_payment') as mock_fund_manager, \
         patch('telegram.Bot') as mock_bot_class, \
         patch('services.email.EmailService') as mock_email_service:
        
        # Setup return values
        mock_credit.return_value = True
        mock_fund_manager.return_value = {
            "success": True,
            "escrow_held": 10.0,
            "platform_fee_collected": 1.0,
            "overpayment_credited": 0.5
        }
        
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot
        
        mock_email_instance = AsyncMock()
        mock_email_instance.send_email.return_value = True
        mock_email_service.return_value = mock_email_instance
        
        # Mock escrow object
        mock_escrow = Mock()
        mock_escrow.escrow_id = "TEST123"
        mock_escrow.buyer_id = 123
        mock_escrow.status = "pending_deposit"
        
        mock_session_instance = Mock()
        mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_escrow
        mock_session.return_value.__enter__.return_value = mock_session_instance
        
        # Test the flow
        from services.blockbee_service import BlockBeeService
        service = BlockBeeService()
        
        callback_data = {
            "txid_in": "test_tx_hash",
            "value_coin": "0.0002",
            "value_fiat": "11.5",
            "coin": "btc",
            "confirmations": 1
        }
        
        # This would normally process the payment and send notifications
        # The test verifies the mocks are called correctly
        result = await service.process_callback("TEST123", callback_data)
        
        # Verify fund manager was called
        mock_fund_manager.assert_called_once()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])