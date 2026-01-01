"""
Onboarding Service 95%+ Coverage Push Test Suite

This test suite is specifically designed to push the onboarding service coverage
from 62% to 95%+ by targeting the identified 128 missing lines and 33 partial lines.

Focus Areas:
- Exception handling in _with_session method (lines 77-79)
- Database integrity errors (lines 310-312) 
- External service failures (lines 335-337)
- Post-commit callback execution (lines 93, 96, 98)
- Edge cases and error conditions throughout the service

Target Lines:
Missing: [77, 78, 79, 93, 96, 98, 134, 135, 136, 138, 142, 143, 164, 165, 166, 
         178, 183, 212, 213, 215, 216, 217, 218, 220, 221, 222, 223, 224, 226, 
         245, 249, 250, 255, 256, 257, 258, 259, 260, 261, 277, 278, 279, 286, 
         293, 297, 310, 311, 312, 321, 335, 336, 337, 360, 361, 362, 373, 377, 
         404, 416, 426, 427, 428, 452, 456, 462, 473, 475, 476, 477, 478, 480, 
         481, 512, 517, 518, 521, 532, 533, 572, 579, 584, 585, 586, 601, 607, 
         608, 611, 612, 621, 622, 627, 638, 639, 640, 661, 673, 674, 675, 704, 
         705, 706, 712, 714, 715, 716, 719, 720, 723, 724, 725, 726, 727, 728, 
         730, 732, 734, 735, 736, 737, 738, 764, 779, 780, 781, 807, 809, 810, 812]
"""

import pytest
import asyncio
import logging
import os
from unittest.mock import patch, MagicMock, AsyncMock, Mock
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from services.onboarding_service import OnboardingService
from models import User, OnboardingSession, OnboardingStep, EmailVerification
from database import managed_session

logger = logging.getLogger(__name__)


@pytest.mark.onboarding_coverage
@pytest.mark.asyncio
class TestOnboardingServiceSessionManagement:
    """Test session management edge cases and error handling"""

    async def test_with_session_flush_exception_handling(self, test_db_session):
        """Test exception handling in _with_session flush operations (lines 77-79)"""
        
        # Create a mock session that raises exception on flush
        mock_session = AsyncMock()
        mock_session.flush.side_effect = Exception("Flush failed")
        
        # Mock function to pass to _with_session
        async def mock_fn(session):
            return {"test": "result"}
        
        # Test flush exception handling
        with patch('services.onboarding_service.logger') as mock_logger:
            result = await OnboardingService._with_session(mock_session, mock_fn)
            
            # Verify result is returned despite flush exception
            assert result == {"test": "result"}
            
            # Verify exception was logged (line 79)
            mock_logger.debug.assert_called_once()
            assert "Session flush skipped" in mock_logger.debug.call_args[0][0]

    async def test_with_session_async_flush_handling(self, test_db_session):
        """Test async flush result handling (lines 76-77)"""
        
        # Create a mock session with async flush result
        mock_session = AsyncMock()
        mock_flush_result = AsyncMock()
        mock_session.flush.return_value = mock_flush_result
        
        async def mock_fn(session):
            return {"test": "async_flush"}
        
        result = await OnboardingService._with_session(mock_session, mock_fn)
        
        # Verify async flush was awaited (line 77)
        mock_flush_result.__await__.assert_called_once()
        assert result == {"test": "async_flush"}

    async def test_with_session_post_commit_callbacks(self, test_db_session):
        """Test post-commit callback execution (lines 93, 96, 98)"""
        
        # Create sync and async callbacks
        sync_callback = Mock()
        async_callback = AsyncMock()
        failing_callback = Mock(side_effect=Exception("Callback failed"))
        
        callbacks = [sync_callback, async_callback, failing_callback]
        
        async def mock_fn(session):
            return {"test": "callbacks"}
        
        with patch('services.onboarding_service.logger') as mock_logger:
            result = await OnboardingService._with_session(None, mock_fn, callbacks)
            
            # Verify all callbacks were attempted
            sync_callback.assert_called_once()
            async_callback.assert_called_once() 
            failing_callback.assert_called_once()
            
            # Verify callback failure was logged (line 98)
            mock_logger.error.assert_called_once()
            assert "Post-commit callback failed" in mock_logger.error.call_args[0][0]
            
            assert result == {"test": "callbacks"}


@pytest.mark.onboarding_coverage
@pytest.mark.asyncio 
class TestOnboardingServiceEmailHandling:
    """Test email validation and duplicate handling"""

    async def test_set_email_invalid_format(self, test_db_session):
        """Test invalid email format validation (line 286)"""
        
        # Test various invalid email formats
        invalid_emails = [
            "invalid-email",
            "@domain.com", 
            "user@",
            "user space@domain.com",
            "",
            None
        ]
        
        for email in invalid_emails:
            result = await OnboardingService.set_email(
                user_id=1, 
                email=email, 
                session=test_db_session
            )
            
            assert result["success"] is False
            assert "Invalid email format" in result["error"]

    async def test_set_email_no_active_session(self, test_db_session):
        """Test error when no active onboarding session exists (line 293)"""
        
        # Test with user that has no onboarding session
        result = await OnboardingService.set_email(
            user_id=99999,  # Non-existent user
            email="test@example.com",
            session=test_db_session
        )
        
        assert result["success"] is False
        assert "No active onboarding session" in result["error"]

    async def test_set_email_wrong_step(self, test_db_session):
        """Test error when not in correct step for email capture (line 297)"""
        
        # Create user and onboarding session in wrong step
        user = User(telegram_id="12345", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.VERIFY_OTP.value,  # Wrong step
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        result = await OnboardingService.set_email(
            user_id=user.id,
            email="new@example.com",
            session=test_db_session
        )
        
        assert result["success"] is False
        assert "Invalid step for email capture" in result["error"]

    async def test_set_email_integrity_error_handling(self, test_db_session):
        """Test database integrity error handling for duplicate emails (lines 310-312)"""
        
        # Create first user with verified email
        user1 = User(telegram_id="11111", email="duplicate@test.com", email_verified=True)
        test_db_session.add(user1)
        
        # Create second user for onboarding
        user2 = User(telegram_id="22222", email="temp@test.com")
        test_db_session.add(user2)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user2.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Mock IntegrityError during query execution
        with patch('sqlalchemy.ext.asyncio.AsyncSession.execute') as mock_execute:
            mock_execute.side_effect = IntegrityError("Duplicate email", None, None)
            
            with patch('services.onboarding_service.logger') as mock_logger:
                result = await OnboardingService.set_email(
                    user_id=user2.id,
                    email="duplicate@test.com",
                    session=test_db_session
                )
                
                assert result["success"] is False
                assert "Email address is already registered" in result["error"]
                
                # Verify warning was logged (line 311)
                mock_logger.warning.assert_called_once()
                assert "Email constraint error" in mock_logger.warning.call_args[0][0]

    async def test_set_email_otp_service_failure(self, test_db_session):
        """Test OTP service failure handling (lines 335-337)"""
        
        # Create user and onboarding session
        user = User(telegram_id="33333", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Mock OTP service to raise exception
        with patch('services.email_verification_service.EmailVerificationService.send_otp_async') as mock_otp:
            mock_otp.side_effect = Exception("Email service down")
            
            with patch('services.onboarding_service.logger') as mock_logger:
                result = await OnboardingService.set_email(
                    user_id=user.id,
                    email="valid@example.com",
                    session=test_db_session
                )
                
                assert result["success"] is False
                assert "email_send_failed" in result["error"]
                
                # Verify error was logged (line 336)
                mock_logger.error.assert_called_once()
                assert "OTP send failed" in mock_logger.error.call_args[0][0]

    async def test_set_email_general_exception_handling(self, test_db_session):
        """Test general exception handling in set_email (lines 360-362)"""
        
        # Mock the _with_session to raise exception
        with patch.object(OnboardingService, '_with_session') as mock_with_session:
            mock_with_session.side_effect = Exception("Database connection lost")
            
            with patch('services.onboarding_service.logger') as mock_logger:
                result = await OnboardingService.set_email(
                    user_id=1,
                    email="test@example.com"
                )
                
                assert result["success"] is False
                assert "Database connection lost" in result["error"]
                
                # Verify error was logged (line 361)
                mock_logger.error.assert_called_once()
                assert "Error setting email for user 1" in mock_logger.error.call_args[0][0]


@pytest.mark.onboarding_coverage
@pytest.mark.asyncio
class TestOnboardingServiceOTPVerification:
    """Test OTP verification edge cases and error handling"""

    async def test_verify_otp_no_active_session(self, test_db_session):
        """Test OTP verification with no active session (line 373)"""
        
        result = await OnboardingService.verify_otp(
            user_id=99999,  # Non-existent user
            otp_code="123456",
            session=test_db_session
        )
        
        assert result["success"] is False
        assert "No active onboarding session" in result["error"]

    async def test_verify_otp_wrong_step(self, test_db_session):
        """Test OTP verification in wrong step (line 377)"""
        
        # Create user and onboarding session in wrong step
        user = User(telegram_id="44444", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.ACCEPT_TOS.value,  # Wrong step
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        result = await OnboardingService.verify_otp(
            user_id=user.id,
            otp_code="123456",
            session=test_db_session
        )
        
        assert result["success"] is False
        assert "Invalid step for OTP verification" in result["error"]
        assert result["current_step"] == OnboardingStep.ACCEPT_TOS.value


@pytest.mark.onboarding_coverage
@pytest.mark.asyncio
class TestOnboardingServiceCacheAndPerformance:
    """Test caching behavior and performance scenarios"""

    async def test_start_with_cache_disabled_in_tests(self, test_db_session):
        """Test cache bypass in test environment"""
        
        # Ensure we're in test environment
        with patch('services.onboarding_service._is_test_environment', return_value=True):
            with patch('services.onboarding_service._onboarding_cache') as mock_cache:
                # Create user
                user = User(telegram_id="55555", email="test@cache.com", email_verified=False)
                test_db_session.add(user)
                await test_db_session.commit()
                
                result = await OnboardingService.start(
                    user_id=user.id,
                    session=test_db_session
                )
                
                # Verify cache was not used (bypassed in tests)
                mock_cache.get.assert_not_called()
                assert result["success"] is True

    async def test_start_with_cache_hit(self, test_db_session):
        """Test cache hit scenario for completed onboarding"""
        
        with patch('services.onboarding_service._is_test_environment', return_value=False):
            cached_data = {"email_verified": True}
            
            with patch('services.onboarding_service._onboarding_cache') as mock_cache:
                mock_cache.get.return_value = cached_data
                
                result = await OnboardingService.start(
                    user_id=1,
                    session=test_db_session
                )
                
                # Verify cache was used
                mock_cache.get.assert_called_once_with("onboarding_user_1")
                assert result["success"] is True
                assert result["completed"] is True
                assert result["current_step"] == OnboardingStep.DONE.value


@pytest.mark.onboarding_coverage
@pytest.mark.asyncio
class TestOnboardingServiceAdvancedScenarios:
    """Test advanced scenarios and edge cases"""

    async def test_start_general_exception_handling(self, test_db_session):
        """Test general exception handling in start method (lines 277-279)"""
        
        with patch.object(OnboardingService, '_with_session') as mock_with_session:
            mock_with_session.side_effect = SQLAlchemyError("Database error")
            
            with patch('services.onboarding_service.logger') as mock_logger:
                result = await OnboardingService.start(user_id=1)
                
                assert result["success"] is False
                assert "Database error" in result["error"]
                
                # Verify error was logged (line 278)
                mock_logger.error.assert_called_once()
                assert "Error starting onboarding for user 1" in mock_logger.error.call_args[0][0]

    async def test_session_creation_with_metadata(self, test_db_session):
        """Test onboarding session creation with metadata (lines 255-261)"""
        
        # Create user
        user = User(telegram_id="66666", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.commit()
        
        # Test creating session with metadata
        result = await OnboardingService.start(
            user_id=user.id,
            invite_token="test_token",
            user_agent="TestAgent/1.0",
            ip_address="192.168.1.1",
            referral_source="telegram",
            session=test_db_session
        )
        
        assert result["success"] is True
        assert result["invite_token"] == "test_token"
        
        # Verify metadata was stored in session
        from sqlalchemy import select
        session_query = await test_db_session.execute(
            select(OnboardingSession).where(OnboardingSession.user_id == user.id)
        )
        onboarding_session = session_query.scalar_one()
        
        assert onboarding_session.user_agent == "TestAgent/1.0"
        assert onboarding_session.ip_address == "192.168.1.1"
        assert onboarding_session.referral_source == "telegram"

    async def test_session_update_existing_metadata(self, test_db_session):
        """Test updating existing session metadata (lines 255-261)"""
        
        # Create user and existing session
        user = User(telegram_id="77777", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            user_agent="OldAgent/1.0"
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Update with new metadata
        result = await OnboardingService.start(
            user_id=user.id,
            user_agent="NewAgent/2.0",
            ip_address="10.0.0.1",
            referral_source="website",
            session=test_db_session
        )
        
        assert result["success"] is True
        
        # Verify metadata was updated
        await test_db_session.refresh(onboarding_session)
        assert onboarding_session.user_agent == "NewAgent/2.0"
        assert onboarding_session.ip_address == "10.0.0.1" 
        assert onboarding_session.referral_source == "website"

    async def test_flush_commit_in_test_environment(self, test_db_session):
        """Test flush and commit handling in test environment (lines 244-250)"""
        
        # Create user
        user = User(telegram_id="88888", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.commit()
        
        # Mock test environment and flush behavior
        with patch('services.onboarding_service._is_test_environment', return_value=True):
            # Mock session to track flush/commit calls
            with patch.object(test_db_session, 'flush', return_value=None) as mock_flush:
                with patch.object(test_db_session, 'commit') as mock_commit:
                    result = await OnboardingService.start(
                        user_id=user.id,
                        session=test_db_session
                    )
                    
                    assert result["success"] is True
                    # In test environment, commit should be called for visibility
                    mock_commit.assert_called()

    async def test_flush_exception_handling_in_session_creation(self, test_db_session):
        """Test flush exception handling during session creation (line 250)"""
        
        # Create user
        user = User(telegram_id="99999", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.commit()
        
        # Mock flush to raise exception
        with patch.object(test_db_session, 'flush') as mock_flush:
            mock_flush.side_effect = Exception("Flush failed")
            
            with patch('services.onboarding_service.logger') as mock_logger:
                result = await OnboardingService.start(
                    user_id=user.id,
                    session=test_db_session
                )
                
                # Should still succeed despite flush exception
                assert result["success"] is True
                
                # Verify exception was logged (line 250)
                mock_logger.debug.assert_called_once()
                assert "Session flush/commit handling" in mock_logger.debug.call_args[0][0]


@pytest.mark.onboarding_coverage
@pytest.mark.asyncio
class TestOnboardingServiceWelcomeEmailHandling:
    """Test welcome email handling and notification service integration"""

    async def test_welcome_email_background_task_success(self, test_db_session):
        """Test successful welcome email sending"""
        
        with patch('services.onboarding_service.ConsolidatedNotificationService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.send_notification.return_value = {"success": True}
            
            with patch('services.email_templates.get_welcome_email_template') as mock_template:
                mock_template.return_value = {"html_content": "<html>Welcome</html>"}
                
                # Test welcome email sending
                await OnboardingService._send_welcome_email_background_task(
                    user_email="test@example.com",
                    user_name="Test User", 
                    user_id=1
                )
                
                # Verify notification service was called
                mock_service.send_notification.assert_called_once()

    async def test_welcome_email_service_failure(self, test_db_session):
        """Test welcome email service failure handling"""
        
        with patch('services.onboarding_service.ConsolidatedNotificationService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.send_notification.return_value = {"success": False, "error": "Service down"}
            
            with patch('services.email_templates.get_welcome_email_template') as mock_template:
                mock_template.return_value = {"html_content": "<html>Welcome</html>"}
                
                with patch('services.onboarding_service.logger') as mock_logger:
                    await OnboardingService._send_welcome_email_background_task(
                        user_email="test@example.com",
                        user_name="Test User",
                        user_id=1
                    )
                    
                    # Verify warning was logged for failed email
                    mock_logger.warning.assert_called_once()
                    assert "Welcome email queueing failed" in mock_logger.warning.call_args[0][0]

    async def test_welcome_email_exception_handling(self, test_db_session):
        """Test welcome email exception handling"""
        
        with patch('services.onboarding_service.ConsolidatedNotificationService') as mock_service_class:
            mock_service_class.side_effect = Exception("Service initialization failed")
            
            with patch('services.onboarding_service.logger') as mock_logger:
                await OnboardingService._send_welcome_email_background_task(
                    user_email="test@example.com",
                    user_name="Test User",
                    user_id=1
                )
                
                # Verify error was logged but didn't raise
                mock_logger.error.assert_called_once()
                assert "Error sending welcome email" in mock_logger.error.call_args[0][0]


@pytest.mark.onboarding_coverage
@pytest.mark.asyncio
class TestOnboardingServiceHelperMethods:
    """Test helper methods and utility functions"""

    async def test_get_active_session_with_expired_session(self, test_db_session):
        """Test _get_active_session with expired session"""
        
        # Create user with expired onboarding session
        user = User(telegram_id="expired_user", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        expired_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() - timedelta(hours=1)  # Expired
        )
        test_db_session.add(expired_session)
        await test_db_session.commit()
        
        # Try to get active session
        active_session = await OnboardingService._get_active_session(
            test_db_session, user.id
        )
        
        # Should return None for expired session
        assert active_session is None

    async def test_advance_to_step_with_invalid_transition(self, test_db_session):
        """Test _advance_to_step with invalid step transition"""
        
        # Create user and session
        user = User(telegram_id="step_user", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.DONE.value,  # Terminal state
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Try to advance from terminal state
        result = await OnboardingService._advance_to_step(
            user.id, OnboardingStep.CAPTURE_EMAIL, session=test_db_session
        )
        
        # Should fail due to invalid transition
        assert result["success"] is False
        assert "Invalid step transition" in result["error"]


@pytest.mark.onboarding_coverage
@pytest.mark.asyncio
class TestOnboardingServiceContextDataHandling:
    """Test context data storage and management"""

    async def test_context_data_initialization_when_none(self, test_db_session):
        """Test context_data initialization when it's None (line 321)"""
        
        # Create user and session with no context_data
        user = User(telegram_id="context_user", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            context_data=None  # Explicitly None
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Mock successful OTP service
        with patch('services.email_verification_service.EmailVerificationService.send_otp_async') as mock_otp:
            mock_otp.return_value = {"success": True, "expires_in_minutes": 15}
            
            with patch.object(OnboardingService, '_advance_to_step') as mock_advance:
                mock_advance.return_value = {"success": True}
                
                result = await OnboardingService.set_email(
                    user_id=user.id,
                    email="test@example.com",
                    session=test_db_session
                )
                
                assert result["success"] is True
                
                # Verify context_data was initialized
                await test_db_session.refresh(onboarding_session)
                assert onboarding_session.context_data is not None
                assert isinstance(onboarding_session.context_data, dict)
                assert "email_captured_at" in onboarding_session.context_data