"""
Comprehensive pytest validation for recent implementations:
1. Database-backed admin notification queue
2. Seller email population for username-based onboarded sellers

Run with: pytest tests/test_admin_queue_and_seller_email.py -v
"""
import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from models import (
    AdminNotification, User, Escrow, EscrowStatus, Transaction
)
from database import SessionLocal
from services.admin_notification_queue import AdminNotificationQueueService
from config import Config


class TestAdminNotificationModel:
    """Test AdminNotification database model"""
    
    def test_admin_notification_model_has_required_fields(self):
        """Verify AdminNotification model has all required fields"""
        from sqlalchemy import inspect
        mapper = inspect(AdminNotification)
        columns = [col.key for col in mapper.columns]
        
        required_fields = [
            'id', 'notification_type', 'category', 'subject',
            'html_content', 'telegram_message', 'entity_type', 'entity_id',
            'priority', 'status', 'send_email', 'send_telegram',
            'email_sent', 'telegram_sent', 'retry_count', 'max_retries',
            'next_retry_at', 'idempotency_key', 'created_at', 'updated_at'
        ]
        
        for field in required_fields:
            assert field in columns, f"Missing required field: {field}"


class TestAdminNotificationQueueService:
    """Test AdminNotificationQueueService functionality"""
    
    def test_service_has_required_methods(self):
        """Verify service has all required methods"""
        assert hasattr(AdminNotificationQueueService, 'enqueue_notification')
        assert hasattr(AdminNotificationQueueService, 'process_pending_notifications')
        assert hasattr(AdminNotificationQueueService, 'get_queue_stats')
        
        assert callable(AdminNotificationQueueService.enqueue_notification)
        assert callable(AdminNotificationQueueService.process_pending_notifications)
        assert callable(AdminNotificationQueueService.get_queue_stats)
    
    def test_enqueue_notification_creates_record(self):
        """Test that enqueue_notification creates database record"""
        idempotency_key = f'test_enqueue_{datetime.now(timezone.utc).timestamp()}'
        
        success = AdminNotificationQueueService.enqueue_notification(
            notification_type='test_notification',
            category='system',
            subject='Test Notification',
            html_content='<p>Test content</p>',
            telegram_message='Test message',
            entity_type='test',
            entity_id='TEST_ENQUEUE',
            priority=3,
            send_email=False,
            send_telegram=False,
            idempotency_key=idempotency_key
        )
        
        assert success is True, "Enqueue operation should return True"
        
        # Verify record exists in database
        session = SessionLocal()
        try:
            notification = session.query(AdminNotification).filter(
                AdminNotification.idempotency_key == idempotency_key
            ).first()
            
            assert notification is not None, "Notification should exist in database"
            assert notification.notification_type == 'test_notification'
            assert notification.category == 'system'
            assert notification.subject == 'Test Notification'
            assert notification.status == 'pending'
            assert notification.priority == 3
            
            # Cleanup
            session.delete(notification)
            session.commit()
            
        finally:
            session.close()
    
    def test_idempotency_protection_prevents_duplicates(self):
        """Test that idempotency key prevents duplicate notifications"""
        idempotency_key = f'test_duplicate_{datetime.now(timezone.utc).timestamp()}'
        
        # First enqueue
        success1 = AdminNotificationQueueService.enqueue_notification(
            notification_type='test_duplicate',
            category='system',
            subject='Duplicate Test',
            html_content='<p>Test</p>',
            priority=3,
            send_email=False,
            send_telegram=False,
            idempotency_key=idempotency_key
        )
        
        # Second enqueue with same key
        success2 = AdminNotificationQueueService.enqueue_notification(
            notification_type='test_duplicate',
            category='system',
            subject='Duplicate Test',
            html_content='<p>Test</p>',
            priority=3,
            send_email=False,
            send_telegram=False,
            idempotency_key=idempotency_key
        )
        
        assert success1 is True
        assert success2 is True
        
        # Verify only one record exists
        session = SessionLocal()
        try:
            count = session.query(AdminNotification).filter(
                AdminNotification.idempotency_key == idempotency_key
            ).count()
            
            assert count == 1, f"Expected 1 notification, found {count}"
            
            # Cleanup
            session.query(AdminNotification).filter(
                AdminNotification.idempotency_key == idempotency_key
            ).delete()
            session.commit()
            
        finally:
            session.close()
    
    @pytest.mark.asyncio
    async def test_process_pending_notifications(self):
        """Test processing pending notifications from queue"""
        stats_before = AdminNotificationQueueService.get_queue_stats()
        assert isinstance(stats_before, dict)
        assert 'pending' in stats_before
        assert 'sent' in stats_before
        assert 'failed' in stats_before
        
        # Process queue (should not raise exceptions)
        result = await AdminNotificationQueueService.process_pending_notifications(batch_size=5)
        
        assert isinstance(result, dict)
        assert 'processed' in result
        assert 'email_sent' in result
        assert 'telegram_sent' in result
        assert 'failed' in result


class TestSellerEmailPopulation:
    """Test seller email population for username-based sellers"""
    
    def test_escrow_model_has_seller_email_field(self):
        """Verify Escrow model has seller_email field"""
        from sqlalchemy import inspect
        mapper = inspect(Escrow)
        columns = [col.key for col in mapper.columns]
        
        assert 'seller_email' in columns, "Escrow model should have seller_email field"
    
    def test_onboarded_user_has_email_for_population(self):
        """Verify onboarded users have email addresses for population"""
        session = SessionLocal()
        try:
            onboarded_user = session.query(User).filter(
                User.username.isnot(None),
                User.email.isnot(None)
            ).first()
            
            if onboarded_user:
                assert onboarded_user.username is not None
                assert onboarded_user.email is not None
                assert '@' in onboarded_user.email
            else:
                pytest.skip("No onboarded users found in database")
                
        finally:
            session.close()


class TestSchedulerIntegration:
    """Test scheduler integration for admin notification processing"""
    
    def test_scheduler_has_notification_processor_method(self):
        """Verify scheduler has process_admin_notification_queue method"""
        from jobs.scheduler import EscrowScheduler
        
        assert hasattr(EscrowScheduler, 'process_admin_notification_queue')
        assert callable(getattr(EscrowScheduler, 'process_admin_notification_queue'))


class TestUserReset:
    """Test @wealthmint user reset"""
    
    def test_wealthmint_user_reset_successful(self):
        """Verify @wealthmint user was reset to 0 escrows and 0 transactions"""
        session = SessionLocal()
        try:
            user = session.query(User).filter(User.username == 'wealthmint').first()
            
            assert user is not None, "@wealthmint user should exist"
            
            escrow_count = session.query(Escrow).filter(
                (Escrow.buyer_id == user.id) | (Escrow.seller_id == user.id)
            ).count()
            
            transaction_count = session.query(Transaction).filter(
                Transaction.user_id == user.id
            ).count()
            
            assert escrow_count == 0, f"Expected 0 escrows, found {escrow_count}"
            assert transaction_count == 0, f"Expected 0 transactions, found {transaction_count}"
            
        finally:
            session.close()


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
