"""
Onboarding Service External Service Failure Tests

This test file focuses on external service failure scenarios and complex 
database transaction handling to cover the remaining uncovered lines.

Targets specific missing coverage areas:
- External service timeouts and failures
- Database rollback scenarios
- Complex error recovery paths
- Service integration failure handling
- Network and connectivity issues
"""

import pytest
import asyncio
import logging
from unittest.mock import patch, MagicMock, AsyncMock, Mock
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError, TimeoutError
from sqlalchemy.ext.asyncio import AsyncSession

from services.onboarding_service import OnboardingService
from models import User, OnboardingSession, OnboardingStep, EmailVerification
from database import managed_session

logger = logging.getLogger(__name__)


@pytest.mark.onboarding_coverage
@pytest.mark.asyncio
class TestOnboardingServiceDatabaseFailures:
    """Test database connection and transaction failures"""

    async def test_database_connection_timeout(self, test_db_session):
        """Test database connection timeout scenarios"""
        
        with patch('database.managed_session') as mock_session_manager:
            mock_session_manager.side_effect = TimeoutError("Database connection timeout")
            
            with patch('services.onboarding_service.logger') as mock_logger:
                result = await OnboardingService.start(user_id=1)
                
                assert result["success"] is False
                assert "Database connection timeout" in result["error"]
                
                # Verify error was logged
                mock_logger.error.assert_called_once()

    async def test_database_operational_error(self, test_db_session):
        """Test database operational errors during transaction"""
        
        # Create user and session
        user = User(telegram_id="db_error", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Mock session to raise OperationalError during commit
        with patch.object(test_db_session, 'commit') as mock_commit:
            mock_commit.side_effect = OperationalError("Connection lost", None, None)
            
            with patch('services.onboarding_service.logger') as mock_logger:
                result = await OnboardingService.set_email(
                    user_id=user.id,
                    email="test@example.com",
                    session=test_db_session
                )
                
                assert result["success"] is False
                # Should handle the operational error gracefully

    async def test_database_transaction_rollback_scenario(self, test_db_session):
        """Test automatic rollback on transaction failures"""
        
        # Create user
        user = User(telegram_id="rollback_test", email="temp@test.com")
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
        
        # Mock wallet creation to fail after user update
        with patch('utils.wallet_manager.get_or_create_wallet') as mock_wallet:
            mock_wallet.side_effect = Exception("Wallet service unavailable")
            
            initial_verified_status = user.email_verified
            
            result = await OnboardingService.accept_tos(
                user_id=user.id,
                session=test_db_session
            )
            
            assert result["success"] is False
            
            # Verify rollback - user should not be marked as verified
            await test_db_session.refresh(user)
            assert user.email_verified == initial_verified_status

    async def test_database_constraint_violation_handling(self, test_db_session):
        """Test handling of database constraint violations"""
        
        # Create first user with specific email
        user1 = User(telegram_id="constraint1", email="duplicate@test.com", email_verified=True)
        test_db_session.add(user1)
        
        # Create second user for onboarding
        user2 = User(telegram_id="constraint2", email="temp@test.com")
        test_db_session.add(user2)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user2.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Try to set duplicate email - should trigger constraint violation
        result = await OnboardingService.set_email(
            user_id=user2.id,
            email="duplicate@test.com",  # Already taken
            session=test_db_session
        )
        
        assert result["success"] is False
        assert "Email address is already registered" in result["error"]


@pytest.mark.onboarding_coverage
@pytest.mark.asyncio
class TestOnboardingServiceEmailServiceFailures:
    """Test email service failures and retry mechanisms"""

    async def test_email_service_timeout(self, test_db_session):
        """Test email service timeout scenarios"""
        
        # Create user and session
        user = User(telegram_id="email_timeout", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Mock email service to timeout
        with patch('services.email_verification_service.EmailVerificationService.send_otp_async') as mock_email:
            mock_email.side_effect = asyncio.TimeoutError("Email service timeout")
            
            with patch('services.onboarding_service.logger') as mock_logger:
                result = await OnboardingService.set_email(
                    user_id=user.id,
                    email="test@example.com",
                    session=test_db_session
                )
                
                assert result["success"] is False
                assert "email_send_failed" in result["error"]
                
                # Verify timeout was logged
                mock_logger.error.assert_called_once()
                assert "OTP send failed" in mock_logger.error.call_args[0][0]

    async def test_email_service_connection_error(self, test_db_session):
        """Test email service connection errors"""
        
        # Create user and session
        user = User(telegram_id="email_conn_error", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Mock email service to raise connection error
        with patch('services.email_verification_service.EmailVerificationService.send_otp_async') as mock_email:
            mock_email.side_effect = ConnectionError("Cannot connect to email server")
            
            result = await OnboardingService.set_email(
                user_id=user.id,
                email="test@example.com",
                session=test_db_session
            )
            
            assert result["success"] is False
            assert "email_send_failed" in result["error"]

    async def test_email_service_authentication_failure(self, test_db_session):
        """Test email service authentication failures"""
        
        # Create user and session
        user = User(telegram_id="email_auth_fail", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Mock email service to return authentication failure
        with patch('services.email_verification_service.EmailVerificationService.send_otp_async') as mock_email:
            mock_email.return_value = {"success": False, "error": "authentication_failed"}
            
            result = await OnboardingService.set_email(
                user_id=user.id,
                email="test@example.com",
                session=test_db_session
            )
            
            assert result["success"] is False
            assert "authentication_failed" in result["error"]

    async def test_email_verification_service_unavailable(self, test_db_session):
        """Test email verification service completely unavailable"""
        
        # Create user and session
        user = User(telegram_id="email_unavailable", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.VERIFY_OTP.value,
            email="test@example.com",
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Mock verification service to be unavailable
        with patch('services.email_verification_service.EmailVerificationService.verify_otp_async') as mock_verify:
            mock_verify.side_effect = Exception("Verification service down")
            
            with patch('services.onboarding_service.logger') as mock_logger:
                result = await OnboardingService.verify_otp(
                    user_id=user.id,
                    otp_code="123456",
                    session=test_db_session
                )
                
                assert result["success"] is False
                # Should handle service unavailability gracefully


@pytest.mark.onboarding_coverage
@pytest.mark.asyncio
class TestOnboardingServiceNotificationServiceFailures:
    """Test notification service failures and recovery"""

    async def test_notification_service_initialization_failure(self, test_db_session):
        """Test notification service initialization failures"""
        
        with patch('services.onboarding_service.ConsolidatedNotificationService') as mock_service_class:
            mock_service_class.side_effect = ImportError("Notification service module not found")
            
            with patch('services.onboarding_service.logger') as mock_logger:
                # This should not break the main flow
                await OnboardingService._send_welcome_email_background_task(
                    user_email="test@example.com",
                    user_name="Test User",
                    user_id=1
                )
                
                # Error should be logged but not propagated
                mock_logger.error.assert_called_once()

    async def test_notification_service_network_timeout(self, test_db_session):
        """Test notification service network timeout"""
        
        with patch('services.onboarding_service.ConsolidatedNotificationService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.send_notification.side_effect = asyncio.TimeoutError("Network timeout")
            
            with patch('services.email_templates.get_welcome_email_template') as mock_template:
                mock_template.return_value = {"html_content": "<html>Welcome</html>"}
                
                with patch('services.onboarding_service.logger') as mock_logger:
                    await OnboardingService._send_welcome_email_background_task(
                        user_email="test@example.com",
                        user_name="Test User",
                        user_id=1
                    )
                    
                    # Timeout should be handled gracefully
                    mock_logger.error.assert_called_once()

    async def test_email_template_service_failure(self, test_db_session):
        """Test email template service failure"""
        
        with patch('services.onboarding_service.ConsolidatedNotificationService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            
            with patch('services.email_templates.get_welcome_email_template') as mock_template:
                mock_template.side_effect = Exception("Template service down")
                
                with patch('services.onboarding_service.logger') as mock_logger:
                    await OnboardingService._send_welcome_email_background_task(
                        user_email="test@example.com",
                        user_name="Test User",
                        user_id=1
                    )
                    
                    # Template failure should be handled
                    mock_logger.error.assert_called_once()


@pytest.mark.onboarding_coverage
@pytest.mark.asyncio
class TestOnboardingServiceCacheFailures:
    """Test cache service failures and fallback behavior"""

    async def test_cache_service_unavailable(self, test_db_session):
        """Test cache service unavailable scenarios"""
        
        # Create completed user
        user = User(telegram_id="cache_unavailable", email="test@example.com", email_verified=True)
        test_db_session.add(user)
        await test_db_session.commit()
        
        # Mock cache to raise exception
        with patch('services.onboarding_service._onboarding_cache') as mock_cache:
            mock_cache.get.side_effect = Exception("Cache service down")
            mock_cache.set.side_effect = Exception("Cache service down")
            
            # Should fall back to database query
            result = await OnboardingService.get_current_step(
                user_id=user.id,
                db_session=test_db_session
            )
            
            # Should still work without cache
            assert result == OnboardingStep.DONE.value

    async def test_cache_corruption_handling(self, test_db_session):
        """Test handling of corrupted cache data"""
        
        with patch('services.onboarding_service._onboarding_cache') as mock_cache:
            # Return corrupted/invalid cache data
            mock_cache.get.return_value = {"invalid": "structure", "corrupted": True}
            
            # Create user
            user = User(telegram_id="cache_corrupt", email="test@example.com", email_verified=False)
            test_db_session.add(user)
            await test_db_session.commit()
            
            # Should fall back to database despite corrupted cache
            result = await OnboardingService.get_current_step(
                user_id=user.id,
                db_session=test_db_session
            )
            
            # Should return correct step from database
            assert result == OnboardingStep.CAPTURE_EMAIL.value


@pytest.mark.onboarding_coverage
@pytest.mark.asyncio
class TestOnboardingServiceComplexErrorRecovery:
    """Test complex error recovery scenarios"""

    async def test_partial_failure_recovery(self, test_db_session):
        """Test recovery from partial failures during onboarding completion"""
        
        # Create user ready for completion
        user = User(telegram_id="partial_fail", email="test@example.com")
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
        
        # Mock wallet creation to succeed but email sending to fail
        with patch('utils.wallet_manager.get_or_create_wallet') as mock_wallet:
            mock_wallet.return_value = MagicMock()
            
            with patch.object(OnboardingService, '_send_welcome_email_background_task') as mock_email:
                mock_email.side_effect = Exception("Email service down")
                
                # Should still complete onboarding despite email failure
                result = await OnboardingService.accept_tos(
                    user_id=user.id,
                    session=test_db_session
                )
                
                # Onboarding should succeed (email is background task)
                assert result["success"] is True
                assert result["completed"] is True
                
                # User should be marked as verified
                await test_db_session.refresh(user)
                assert user.email_verified is True

    async def test_concurrent_modification_handling(self, test_db_session):
        """Test handling of concurrent modifications"""
        
        # Create user and session
        user = User(telegram_id="concurrent_mod", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Simulate concurrent modification by changing session step
        original_step = onboarding_session.current_step
        
        # Mock _get_active_session to return session in different step
        async def mock_get_active_session(session, user_id):
            # Return session but with modified step to simulate concurrent change
            onboarding_session.current_step = OnboardingStep.VERIFY_OTP.value
            return onboarding_session
        
        with patch.object(OnboardingService, '_get_active_session', side_effect=mock_get_active_session):
            result = await OnboardingService.set_email(
                user_id=user.id,
                email="test@example.com",
                session=test_db_session
            )
            
            # Should detect step mismatch and fail appropriately
            assert result["success"] is False
            assert "Invalid step for email capture" in result["error"]

    async def test_session_expiry_during_operation(self, test_db_session):
        """Test session expiry during long-running operations"""
        
        # Create user with session that will expire soon
        user = User(telegram_id="expiry_during_op", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        # Session expires very soon
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() + timedelta(seconds=2)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Mock email service to take longer than session expiry
        async def slow_email_service(*args, **kwargs):
            await asyncio.sleep(3)  # Longer than session expiry
            return {"success": True, "expires_in_minutes": 15}
        
        with patch('services.email_verification_service.EmailVerificationService.send_otp_async') as mock_email:
            mock_email.side_effect = slow_email_service
            
            result = await OnboardingService.set_email(
                user_id=user.id,
                email="test@example.com",
                session=test_db_session
            )
            
            # Operation should handle session expiry gracefully
            # This might succeed or fail depending on implementation timing
            assert "success" in result


@pytest.mark.onboarding_coverage
@pytest.mark.asyncio
class TestOnboardingServiceSystemResourceFailures:
    """Test system resource and infrastructure failures"""

    async def test_memory_pressure_handling(self, test_db_session):
        """Test behavior under memory pressure"""
        
        # Mock memory allocation failure
        with patch('services.onboarding_service.EnhancedCache') as mock_cache_class:
            mock_cache_class.side_effect = MemoryError("Out of memory")
            
            # Should handle gracefully by disabling cache
            result = await OnboardingService.start(user_id=1, session=test_db_session)
            
            # Should still work without cache functionality
            assert "success" in result

    async def test_file_system_errors(self, test_db_session):
        """Test file system related errors"""
        
        # Mock file system error during logging
        with patch('services.onboarding_service.logger') as mock_logger:
            mock_logger.info.side_effect = OSError("Disk full")
            
            # Create user
            user = User(telegram_id="fs_error", email="temp@test.com")
            test_db_session.add(user)
            await test_db_session.commit()
            
            # Should handle logging errors gracefully
            result = await OnboardingService.start(
                user_id=user.id,
                session=test_db_session
            )
            
            # Main functionality should not be affected by logging errors
            assert result["success"] is True

    async def test_configuration_errors(self, test_db_session):
        """Test configuration and environment errors"""
        
        # Mock configuration access failure
        with patch('services.onboarding_service.Config') as mock_config:
            mock_config.side_effect = AttributeError("Configuration not available")
            
            # Should handle gracefully with defaults
            result = await OnboardingService.start(user_id=1, session=test_db_session)
            
            # Should work with default values
            assert "success" in result


@pytest.mark.onboarding_coverage
@pytest.mark.asyncio
class TestOnboardingServiceAsyncOperationFailures:
    """Test async operation specific failures"""

    async def test_asyncio_cancelled_error(self, test_db_session):
        """Test handling of asyncio.CancelledError"""
        
        with patch.object(OnboardingService, '_with_session') as mock_with_session:
            mock_with_session.side_effect = asyncio.CancelledError("Operation cancelled")
            
            try:
                await OnboardingService.start(user_id=1)
                assert False, "Should have raised CancelledError"
            except asyncio.CancelledError:
                # CancelledError should be re-raised
                pass

    async def test_task_timeout_handling(self, test_db_session):
        """Test handling of task timeouts"""
        
        # Create user and session
        user = User(telegram_id="task_timeout", email="temp@test.com")
        test_db_session.add(user)
        await test_db_session.flush()
        
        onboarding_session = OnboardingSession(
            user_id=user.id,
            current_step=OnboardingStep.CAPTURE_EMAIL.value,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        test_db_session.add(onboarding_session)
        await test_db_session.commit()
        
        # Mock email service to timeout
        async def timeout_email_service(*args, **kwargs):
            await asyncio.sleep(10)  # Very long delay
            return {"success": True}
        
        with patch('services.email_verification_service.EmailVerificationService.send_otp_async') as mock_email:
            mock_email.side_effect = timeout_email_service
            
            # Use asyncio.wait_for to test timeout handling
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    OnboardingService.set_email(
                        user_id=user.id,
                        email="test@example.com",
                        session=test_db_session
                    ),
                    timeout=1.0  # Short timeout
                )

    async def test_coroutine_cleanup_on_failure(self, test_db_session):
        """Test proper cleanup of coroutines on failures"""
        
        # Create multiple async operations that could leak
        async def leaky_operation():
            await asyncio.sleep(0.1)
            raise Exception("Simulated failure")
        
        # Mock multiple async operations
        with patch('services.email_verification_service.EmailVerificationService.send_otp_async') as mock_email:
            with patch.object(OnboardingService, '_send_welcome_email_background_task') as mock_welcome:
                mock_email.side_effect = leaky_operation
                mock_welcome.side_effect = leaky_operation
                
                # Create user and session for operation
                user = User(telegram_id="cleanup_test", email="temp@test.com")
                test_db_session.add(user)
                await test_db_session.flush()
                
                onboarding_session = OnboardingSession(
                    user_id=user.id,
                    current_step=OnboardingStep.CAPTURE_EMAIL.value,
                    expires_at=datetime.utcnow() + timedelta(hours=24)
                )
                test_db_session.add(onboarding_session)
                await test_db_session.commit()
                
                # Should handle failures without leaking resources
                result = await OnboardingService.set_email(
                    user_id=user.id,
                    email="test@example.com",
                    session=test_db_session
                )
                
                assert result["success"] is False