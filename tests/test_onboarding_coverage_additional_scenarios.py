"""
Additional Onboarding Service Coverage Tests

This test file covers additional scenarios and methods to push coverage beyond 95%.
Focuses on remaining uncovered lines including helper methods, advanced error scenarios,
and complex business logic paths.

Covers remaining methods:
- accept_tos() method and related error paths
- get_current_step() method
- _get_active_session() helper
- _advance_to_step() helper  
- Various database transaction scenarios
- Complex error recovery paths
"""

import pytest
import asyncio
import logging
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from services.onboarding_service import OnboardingService
from models import User, OnboardingSession, OnboardingStep, EmailVerification, Wallet
from database import managed_session

logger = logging.getLogger(__name__)


@pytest.mark.onboarding_coverage
@pytest.mark.asyncio
class TestOnboardingServiceAcceptTOS:
    """Test terms of service acceptance functionality"""

    async def test_accept_tos_no_active_session(self, test_db_session):
        """Test accept_tos with no active session"""
        
        result = await OnboardingService.accept_tos(
            user_id=99999,  # Non-existent user
            session=test_db_session
        )
        
        assert result["success"] is False
        assert "No active onboarding session" in result["error"]

    async def test_accept_tos_wrong_step(self, test_db_session):
        """Test accept_tos in wrong step"""
        
        # Create user and onboarding session in wrong step
        user = User(telegram_id="tos_user", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,  # Wrong step
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        result = await OnboardingService.accept_tos(
            user_id=user.id,
            session=test_db_session
        )
        
        assert result["success"] is False
        assert "Invalid step for terms acceptance" in result["error"]

    async def test_accept_tos_successful_completion(self, test_db_session):
        """Test successful TOS acceptance and onboarding completion"""
        
        # Create user in correct step
        user = User(telegram_id="tos_success", email="test@example.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.ACCEPT_TOS.value,
            email="test@example.com",
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Mock welcome email sending
        with patch.object(OnboardingService, '_send_welcome_email_background_task') as mock_email:
            with patch('utils.wallet_manager.get_or_create_wallet') as mock_wallet:
                mock_wallet.return_value = MagicMock()
                
                result = await OnboardingService.accept_tos(
                    user_id=user.id,
                    session=test_db_session
                )
                
                assert result["success"] is True
                assert result["completed"] is True
                assert result["current_step"] == OnboardingStep.DONE.value
                
                # Verify user was marked as email verified
                await test_db_session.refresh(user)
                assert user.email_verified is True
                assert user.email == "test@example.com"
                
                # Verify welcome email was queued
                mock_email.assert_called_once()

    async def test_accept_tos_wallet_creation_failure(self, test_db_session):
        """Test TOS acceptance with wallet creation failure"""
        
        # Create user in correct step
        user = User(telegram_id="wallet_fail", email="test@example.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.ACCEPT_TOS.value,
            email="test@example.com",
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Mock wallet creation to fail
        with patch('utils.wallet_manager.get_or_create_wallet') as mock_wallet:
            mock_wallet.side_effect = Exception("Wallet service down")
            
            with patch('services.onboarding_service.logger') as mock_logger:
                result = await OnboardingService.accept_tos(
                    user_id=user.id,
                    session=test_db_session
                )
                
                assert result["success"] is False
                assert "wallet_creation_failed" in result["error"]
                
                # Verify error was logged
                mock_logger.error.assert_called_once()
                assert "Wallet creation failed" in mock_logger.error.call_args[0][0]

    async def test_accept_tos_general_exception_handling(self, test_db_session):
        """Test general exception handling in accept_tos"""
        
        with patch.object(OnboardingService, '_with_session') as mock_with_session:
            mock_with_session.side_effect = SQLAlchemyError("Database connection lost")
            
            with patch('services.onboarding_service.logger') as mock_logger:
                result = await OnboardingService.accept_tos(user_id=1)
                
                assert result["success"] is False
                assert "Database connection lost" in result["error"]
                
                # Verify error was logged
                mock_logger.error.assert_called_once()
                assert "Error accepting terms for user 1" in mock_logger.error.call_args[0][0]


@pytest.mark.onboarding_coverage
@pytest.mark.asyncio
class TestOnboardingServiceGetCurrentStep:
    """Test get_current_step method and related functionality"""

    async def test_get_current_step_with_completed_user(self, test_db_session):
        """Test get_current_step for user with completed onboarding"""
        
        # Create user with verified email
        user = User(telegram_id="completed_user", email="test@example.com", email_verified=True)
        test_db_session.add(user)
        await test_db_session.commit()
        
        # Test with cache disabled
        with patch('services.onboarding_service._is_test_environment', return_value=True):
            result = await OnboardingService.get_current_step(
                user_id=user.id,
                db_session=test_db_session
            )
            
            assert result == OnboardingStep.DONE.value

    async def test_get_current_step_with_cache_hit(self, test_db_session):
        """Test get_current_step with cache hit"""
        
        with patch('services.onboarding_service._is_test_environment', return_value=False):
            with patch('services.onboarding_service._onboarding_cache') as mock_cache:
                mock_cache.get.return_value = {"current_step": OnboardingStep.VERIFY_OTP.value}
                
                result = await OnboardingService.get_current_step(user_id=1)
                
                assert result == OnboardingStep.VERIFY_OTP.value
                mock_cache.get.assert_called_once_with("onboarding_step_1")

    async def test_get_current_step_no_user_found(self, test_db_session):
        """Test get_current_step with non-existent user"""
        
        result = await OnboardingService.get_current_step(
            user_id=99999,
            db_session=test_db_session
        )
        
        assert result is None

    async def test_get_current_step_no_onboarding_session(self, test_db_session):
        """Test get_current_step with user but no onboarding session"""
        
        # Create user without onboarding session
        user = User(telegram_id="no_session", email="temp@test.com", email_verified=False)
        test_db_session.add(user)
        await test_db_session.commit()
        
        result = await OnboardingService.get_current_step(
            user_id=user.id,
            db_session=test_db_session
        )
        
        # Should default to CAPTURE_EMAIL for users without sessions
        assert result == OnboardingStep.CAPTURE_EMAIL.value

    async def test_get_current_step_exception_handling(self, test_db_session):
        """Test exception handling in get_current_step"""
        
        with patch.object(OnboardingService, '_with_session') as mock_with_session:
            mock_with_session.side_effect = Exception("Database error")
            
            with patch('services.onboarding_service.logger') as mock_logger:
                result = await OnboardingService.get_current_step(user_id=1)
                
                assert result is None
                
                # Verify error was logged
                mock_logger.error.assert_called_once()
                assert "Error getting current step for user 1" in mock_logger.error.call_args[0][0]


@pytest.mark.onboarding_coverage
@pytest.mark.asyncio
class TestOnboardingServiceHelperMethods:
    """Test helper methods comprehensively"""

    async def test_get_active_session_multiple_sessions(self, test_db_session):
        """Test _get_active_session with multiple sessions (should get latest)"""
        
        # Create user
        user = User(telegram_id="multi_session", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        # Create multiple sessions (some expired)
        old_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired
            created_at=datetime.utcnow() - timedelta(hours=2)
        )
        
        current_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.VERIFY_OTP.value,
            expires_at=datetime.utcnow() + timedelta(hours=24),  # Valid
            created_at=datetime.utcnow()
        )
        
        test_db_session.add_all([old_session, current_session])
        await test_db_session.commit()
        
        # Should return the valid session
        active_session = await OnboardingService._get_active_session(
            test_db_session, user.id
        )
        
        assert active_session is not None
        assert active_session.id == current_session.id
        assert active_session.current_step == OnboardingStep.VERIFY_OTP.value

    async def test_advance_to_step_success(self, test_db_session):
        """Test successful step advancement"""
        
        # Create user and session
        user = User(telegram_id="advance_user", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Advance to next step
        result = await OnboardingService._advance_to_step(
            user.id,
            OnboardingStep.VERIFY_OTP,
            session=test_db_session
        )
        
        assert result["success"] is True
        assert result["current_step"] == OnboardingStep.VERIFY_OTP.value
        
        # Verify session was updated
        await test_db_session.refresh(onboarding_session)
        assert onboarding_session.current_step == OnboardingStep.VERIFY_OTP.value

    async def test_advance_to_step_no_session(self, test_db_session):
        """Test step advancement with no active session"""
        
        result = await OnboardingService._advance_to_step(
            99999,  # Non-existent user
            OnboardingStep.VERIFY_OTP,
            session=test_db_session
        )
        
        assert result["success"] is False
        assert "No active onboarding session" in result["error"]

    async def test_advance_to_step_invalid_transition(self, test_db_session):
        """Test invalid step transition"""
        
        # Create user and session in terminal state
        user = User(telegram_id="invalid_transition", email="temp@test.com")
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
            user.id,
            OnboardingStep.CAPTURE_EMAIL,
            session=test_db_session
        )
        
        assert result["success"] is False
        assert "Invalid step transition" in result["error"]


@pytest.mark.onboarding_coverage
@pytest.mark.asyncio
class TestOnboardingServiceDatabaseTransactionScenarios:
    """Test complex database transaction scenarios"""

    async def test_database_rollback_on_integrity_error(self, test_db_session):
        """Test database rollback on integrity constraint violations"""
        
        # Create user
        user = User(telegram_id="rollback_user", email="rollback@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Mock database to raise IntegrityError during email setting
        with patch.object(test_db_session, 'execute') as mock_execute:
            mock_execute.side_effect = IntegrityError("Constraint violation", None, None)
            
            result = await OnboardingService.set_email(
                user_id=user.id,
                email="duplicate@test.com",
                session=test_db_session
            )
            
            assert result["success"] is False
            assert "Email address is already registered" in result["error"]

    async def test_concurrent_session_access(self, test_db_session):
        """Test handling of concurrent session access scenarios"""
        
        # Create user and session
        user = User(telegram_id="concurrent_user", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Simulate concurrent modification by updating session externally
        onboarding_session.current_step = OnboardingStep.VERIFY_OTP.value
        
        # Now try to set email (which expects CAPTURE_EMAIL step)
        result = await OnboardingService.set_email(
            user_id=user.id,
            email="test@example.com",
            session=test_db_session
        )
        
        # Should handle step validation properly
        assert result["success"] is False
        assert "Invalid step for email capture" in result["error"]

    async def test_session_expiry_edge_case(self, test_db_session):
        """Test session expiry edge cases"""
        
        # Create user with session that expires very soon
        user = User(telegram_id="expiry_user", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        # Session expires in 1 second
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() + timedelta(seconds=1)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Wait for expiry
        await asyncio.sleep(1.1)
        
        # Try to use expired session
        result = await OnboardingService.set_email(
            user_id=user.id,
            email="test@example.com",
            session=test_db_session
        )
        
        assert result["success"] is False
        assert "No active onboarding session" in result["error"]


@pytest.mark.onboarding_coverage
@pytest.mark.asyncio
class TestOnboardingServicePerformanceAndCaching:
    """Test performance monitoring and caching behavior"""

    async def test_performance_tracking_decorator(self, test_db_session):
        """Test that performance tracking decorator is working"""
        
        # Create user
        user = User(telegram_id="perf_user", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.commit()
        
        # Mock performance monitor
        with patch('services.onboarding_performance_monitor.track_onboarding_performance') as mock_track:
            # The decorator should be called automatically
            result = await OnboardingService.start(
                user_id=user.id,
                session=test_db_session
            )
            
            assert result["success"] is True
            # Performance tracking should have been called via decorator

    async def test_cache_set_after_successful_completion(self, test_db_session):
        """Test cache is set after successful onboarding completion"""
        
        # Create user ready for TOS acceptance
        user = User(telegram_id="cache_user", email="test@example.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.ACCEPT_TOS.value,
            email="test@example.com",
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Mock cache and other services
        with patch('services.onboarding_service._is_test_environment', return_value=False):
            with patch('services.onboarding_service._onboarding_cache') as mock_cache:
                with patch.object(OnboardingService, '_send_welcome_email_background_task'):
                    with patch('utils.wallet_manager.get_or_create_wallet'):
                        result = await OnboardingService.accept_tos(
                            user_id=user.id,
                            session=test_db_session
                        )
                        
                        assert result["success"] is True
                        
                        # Cache should be updated
                        cache_calls = mock_cache.set.call_args_list
                        assert len(cache_calls) > 0
                        
                        # Should cache the completion status
                        for call in cache_calls:
                            args, kwargs = call
                            if "onboarding_user_" in args[0]:
                                cached_data = args[1]
                                assert "email_verified" in cached_data or "completed" in cached_data

    async def test_cache_invalidation_on_step_change(self, test_db_session):
        """Test cache invalidation when onboarding step changes"""
        
        # Create user and session
        user = User(telegram_id="cache_invalidate", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Mock cache behavior
        with patch('services.onboarding_service._is_test_environment', return_value=False):
            with patch('services.onboarding_service._onboarding_cache') as mock_cache:
                with patch('services.email_verification_service.EmailVerificationService.send_otp_async') as mock_otp:
                    mock_otp.return_value = {"success": True, "expires_in_minutes": 15}
                    
                    result = await OnboardingService.set_email(
                        user_id=user.id,
                        email="test@example.com",
                        session=test_db_session
                    )
                    
                    assert result["success"] is True
                    
                    # Cache should be invalidated/updated
                    mock_cache.delete.assert_called()


@pytest.mark.onboarding_coverage
@pytest.mark.asyncio
class TestOnboardingServiceEdgeCasesAndBoundaryConditions:
    """Test edge cases and boundary conditions"""

    async def test_very_long_email_address(self, test_db_session):
        """Test handling of very long email addresses"""
        
        # Create user and session
        user = User(telegram_id="long_email", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Very long but valid email
        long_email = "a" * 100 + "@" + "b" * 100 + ".com"
        
        result = await OnboardingService.set_email(
            user_id=user.id,
            email=long_email,
            session=test_db_session
        )
        
        # Should handle validation appropriately
        assert result["success"] is False  # Should fail due to length validation

    async def test_unicode_email_address(self, test_db_session):
        """Test handling of unicode characters in email"""
        
        # Create user and session
        user = User(telegram_id="unicode_email", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Unicode email
        unicode_email = "tëst@exâmple.com"
        
        result = await OnboardingService.set_email(
            user_id=user.id,
            email=unicode_email,
            session=test_db_session
        )
        
        # Should handle validation appropriately
        assert result["success"] is False  # Should fail validation

    async def test_onboarding_session_context_data_edge_cases(self, test_db_session):
        """Test context_data handling edge cases"""
        
        # Create user and session with malformed context_data
        user = User(telegram_id="context_edge", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            context_data={"malformed": "data", "nested": {"deep": {"value": 123}}}
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
                
                # Verify context_data was properly updated
                await test_db_session.refresh(onboarding_session)
                assert "email_captured_at" in onboarding_session.context_data
                assert "malformed" in onboarding_session.context_data  # Preserved existing data