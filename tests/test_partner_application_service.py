"""
Unit Tests for Partner Application Service
Tests notification system for partner applications
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from services.partner_application_service import PartnerApplicationService
from models import PartnerApplication, PartnerApplicationStatus, User


class TestPartnerApplicationService:
    """Test suite for partner application service"""
    
    @pytest.fixture
    def service(self):
        """Create service instance"""
        return PartnerApplicationService()
    
    @pytest.fixture
    def sample_application(self):
        """Sample partner application"""
        return PartnerApplication(
            id=1,
            name="Test Partner",
            telegram_handle="@testpartner",
            email="test@example.com",
            community_type="crypto_trading",
            audience_size="10K-50K",
            primary_region="Africa (Other)",
            monthly_volume="$100-500K",
            commission_tier="silver",
            goals="Testing partner program",
            status=PartnerApplicationStatus.NEW.value,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def sample_user(self):
        """Sample user for Telegram notifications"""
        return User(
            id=1,
            telegram_id=123456789,
            username="testpartner",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @pytest.mark.asyncio
    async def test_submit_application_success(self, service):
        """Test successful application submission"""
        session = AsyncMock(spec=AsyncSession)
        
        with patch.object(service, '_send_admin_notification', new_callable=AsyncMock) as mock_admin:
            with patch.object(service, '_send_applicant_confirmation', new_callable=AsyncMock) as mock_confirmation:
                with patch.object(service, '_send_applicant_telegram_notification', new_callable=AsyncMock) as mock_telegram:
                    result = await service.submit_application(
                        session=session,
                        name="Test Partner",
                        telegram_handle="testpartner",
                        email="test@example.com",
                        community_type="crypto_trading",
                        audience_size="10K-50K",
                        primary_region="Africa (Other)",
                        monthly_volume="$100-500K",
                        commission_tier="silver",
                        goals="Testing"
                    )
                    
                    assert result['success'] is True
                    assert 'application_id' in result
                    assert result['email'] == "test@example.com"
                    
                    # Verify all notifications were called
                    mock_admin.assert_called_once()
                    mock_confirmation.assert_called_once()
                    mock_telegram.assert_called_once()
                    session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_telegram_handle_normalization(self, service):
        """Test telegram handle normalization (adds @ prefix)"""
        session = AsyncMock(spec=AsyncSession)
        
        with patch.object(service, '_send_admin_notification', new_callable=AsyncMock):
            with patch.object(service, '_send_applicant_confirmation', new_callable=AsyncMock):
                with patch.object(service, '_send_applicant_telegram_notification', new_callable=AsyncMock):
                    result = await service.submit_application(
                        session=session,
                        name="Test",
                        telegram_handle="testuser",  # No @ prefix
                        email="test@example.com",
                        community_type="crypto_trading",
                        audience_size="10K-50K",
                        primary_region="Africa (Other)",
                        monthly_volume="$100-500K",
                        commission_tier="silver",
                        goals="Test"
                    )
                    
                    assert result['telegram_handle'] == "@testuser"
    
    @pytest.mark.asyncio
    async def test_applicant_email_confirmation_sent(self, service, sample_application):
        """Test that applicant confirmation email is sent"""
        with patch.object(service.email_service, 'send_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            await service._send_applicant_confirmation(sample_application)
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            
            assert call_args.kwargs['to_email'] == "test@example.com"
            assert "Application Received" in call_args.kwargs['subject']
            assert "Test Partner" in call_args.kwargs['html_content']
            assert "#1" in call_args.kwargs['html_content']
    
    @pytest.mark.asyncio
    async def test_admin_email_notification_sent(self, service, sample_application):
        """Test that admin email notification is sent"""
        with patch.object(service.email_service, 'send_email', new_callable=AsyncMock) as mock_send:
            with patch.object(service, '_send_telegram_admin_notification', new_callable=AsyncMock):
                mock_send.return_value = True
                
                await service._send_admin_notification(sample_application)
                
                mock_send.assert_called_once()
                call_args = mock_send.call_args
                
                assert call_args.kwargs['to_email'] == service.admin_email
                assert "NEW Partner Application" in call_args.kwargs['subject']
                assert "Test Partner" in call_args.kwargs['html_content']
                assert "@testpartner" in call_args.kwargs['html_content']
    
    @pytest.mark.asyncio
    async def test_applicant_telegram_notification_user_found(self, service, sample_application, sample_user):
        """Test Telegram notification sent when applicant has Lockbay account"""
        session = AsyncMock(spec=AsyncSession)
        
        # Mock database query to return user (properly awaitable)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none = MagicMock(return_value=sample_user)
        
        async def mock_execute(*args, **kwargs):
            return result_mock
        
        session.execute = mock_execute
        
        # Mock bot with proper async return value
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock(return_value=True)
        mock_app = MagicMock()
        mock_app.bot = mock_bot
        
        with patch('webhook_server._bot_application', mock_app):
            # Should not raise exception
            await service._send_applicant_telegram_notification(sample_application, session)
            
            # Verify send_message was called
            mock_bot.send_message.assert_called_once()
            call_kwargs = mock_bot.send_message.call_args.kwargs
            
            assert call_kwargs['chat_id'] == 123456789
            assert "Application Received" in call_kwargs['text']
            assert "Test Partner" in call_kwargs['text']
            assert "#1" in call_kwargs['text']
    
    @pytest.mark.asyncio
    async def test_applicant_telegram_notification_user_not_found(self, service, sample_application):
        """Test Telegram notification gracefully skipped when applicant not in Lockbay"""
        session = AsyncMock(spec=AsyncSession)
        
        # Mock database query to return None
        result_mock = AsyncMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute.return_value = result_mock
        
        # Mock bot
        mock_bot = AsyncMock()
        mock_app = MagicMock()
        mock_app.bot = mock_bot
        
        with patch('webhook_server._bot_application', mock_app):
            await service._send_applicant_telegram_notification(sample_application, session)
            
            # Verify no Telegram message was sent
            mock_bot.send_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_admin_telegram_notifications_sent_to_all_admins(self, service, sample_application):
        """Test Telegram notifications sent to all configured admins"""
        mock_bot = AsyncMock()
        mock_app = MagicMock()
        mock_app.bot = mock_bot
        
        with patch('webhook_server._bot_application', mock_app):
            with patch('services.partner_application_service.Config') as mock_config:
                mock_config.ADMIN_IDS = [111, 222, 333]
                
                await service._send_telegram_admin_notification(
                    sample_application,
                    "🥈 Silver (40%)",
                    "Crypto Trading Group"
                )
                
                # Verify message sent to all 3 admins
                assert mock_bot.send_message.call_count == 3
                
                # Check admin IDs
                sent_to = [call.kwargs['chat_id'] for call in mock_bot.send_message.call_args_list]
                assert sent_to == [111, 222, 333]
    
    @pytest.mark.asyncio
    async def test_error_handling_in_submission(self, service):
        """Test error handling during application submission"""
        session = AsyncMock(spec=AsyncSession)
        session.flush.side_effect = Exception("Database error")
        
        result = await service.submit_application(
            session=session,
            name="Test",
            telegram_handle="@test",
            email="test@example.com",
            community_type="crypto_trading",
            audience_size="10K-50K",
            primary_region="Africa (Other)",
            monthly_volume="$100-500K",
            commission_tier="silver",
            goals="Test"
        )
        
        assert result['success'] is False
        assert 'error' in result
        session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_email_notification_failure_logged(self, service, sample_application):
        """Test that email failures are logged but don't crash"""
        with patch.object(service.email_service, 'send_email', new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = Exception("Email service error")
            
            # Should not raise exception
            await service._send_applicant_confirmation(sample_application)
    
    @pytest.mark.asyncio
    async def test_telegram_notification_failure_logged(self, service, sample_application):
        """Test that Telegram failures are logged but don't crash"""
        mock_bot = AsyncMock()
        mock_bot.send_message.side_effect = Exception("Telegram API error")
        mock_app = MagicMock()
        mock_app.bot = mock_bot
        
        with patch('webhook_server._bot_application', mock_app):
            with patch('services.partner_application_service.Config') as mock_config:
                mock_config.ADMIN_IDS = [111]
                
                # Should not raise exception
                await service._send_telegram_admin_notification(
                    sample_application,
                    "🥈 Silver (40%)",
                    "Crypto Trading Group"
                )
