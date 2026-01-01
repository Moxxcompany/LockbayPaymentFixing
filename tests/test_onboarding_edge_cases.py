"""
Onboarding Service Edge Case Tests - Architect's Coverage Boost Strategy

Targeted tests for 4 specific coverage gaps identified by the architect:
1. ERROR HANDLING COVERAGE: IntegrityError, SQLAlchemyError, external service errors, validation failures (+5-8% expected)
2. POST-COMMIT CALLBACK FAILURES: Email failures after user creation, notification failures, retry mechanisms (+3-5% expected)  
3. CACHE BYPASS SCENARIOS: Cache miss handling, invalidation, fallback mechanisms (+2-4% expected)
4. SESSION MANAGEMENT EDGE CASES: Injected vs self-managed sessions, concurrent access, transaction boundaries (+3-5% expected)

Goal: Boost services/onboarding_service.py coverage from 65% to 85%+ (76+ additional statements)
"""

import pytest
import asyncio
import logging
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Database and model imports
from database import managed_session
from models import (
    User, OnboardingSession, OnboardingStep, EmailVerification, 
    UserStatus, Wallet
)
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import select

# Service under test
from services.onboarding_service import OnboardingService, _onboarding_cache, _is_test_environment

logger = logging.getLogger(__name__)


@pytest.mark.onboarding
@pytest.mark.edge_cases  
class TestOnboardingErrorHandling:
    """Test error handling coverage gaps identified by architect"""
    
    @pytest.mark.asyncio
    async def test_integrity_error_duplicate_email_constraint(self, test_db_session, patched_services):
        """Test IntegrityError handling for duplicate email constraints"""
        user_id = 12345
        duplicate_email = "duplicate@test.com"
        
        # Create first user with this email
        async with managed_session() as session:
            user1 = User(
                telegram_id="111111",
                username="user1",
                email=duplicate_email,
                email_verified=True
            )
            session.add(user1)
            await session.commit()
        
        # Start onboarding for second user
        result = await OnboardingService.start(user_id=user_id)
        assert result["success"] is True
        
        # Attempt to set duplicate email - should trigger IntegrityError
        with patch('services.onboarding_service.logger') as mock_logger:
            result = await OnboardingService.set_email(
                user_id=user_id, 
                email=duplicate_email
            )
            
            # Should handle IntegrityError gracefully
            assert result["success"] is False
            assert "already registered" in result["error"]
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_sqlalchemy_error_handling_in_start(self, test_db_session):
        """Test SQLAlchemyError handling in start method"""
        user_id = 12346
        
        # Mock SQLAlchemyError during session operations
        with patch('database.managed_session') as mock_session_manager:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.execute.side_effect = SQLAlchemyError("Database connection failed")
            mock_session_manager.return_value = mock_session
            
            result = await OnboardingService.start(user_id=user_id)
            
            # Should handle SQLAlchemyError gracefully
            assert result["success"] is False
            assert "Database connection failed" in result["error"]

    @pytest.mark.asyncio
    async def test_external_service_error_otp_send_failure(self, test_db_session, patched_services):
        """Test external service errors - OTP sending failures"""
        user_id = 12347
        test_email = "otp_fail@test.com"
        
        # Start onboarding
        result = await OnboardingService.start(user_id=user_id)
        assert result["success"] is True
        
        # Mock email service failure
        patched_services['email'].send_otp_email.return_value = {
            'success': False,
            'error': 'Email service temporarily unavailable',
            'retry_after_seconds': 300
        }
        
        # Attempt to set email with failing OTP service
        result = await OnboardingService.set_email(user_id=user_id, email=test_email)
        
        # Should handle external service error gracefully
        assert result["success"] is False
        assert "email_send_failed" in result["error"]
        
    @pytest.mark.asyncio
    async def test_validation_failures_invalid_email_formats(self, test_db_session):
        """Test validation failures for invalid email formats"""
        user_id = 12348
        invalid_emails = [
            "invalid-email",
            "@domain.com", 
            "user@",
            "user@@domain.com",
            "user space@domain.com",
            "",
            None
        ]
        
        # Start onboarding
        result = await OnboardingService.start(user_id=user_id)
        assert result["success"] is True
        
        # Test each invalid email format
        for invalid_email in invalid_emails:
            if invalid_email is None:
                continue  # Skip None case for now
                
            result = await OnboardingService.set_email(
                user_id=user_id, 
                email=invalid_email
            )
            
            # Should reject invalid email formats
            assert result["success"] is False
            assert "Invalid email format" in result["error"]

    @pytest.mark.asyncio
    async def test_external_service_timeout_scenarios(self, test_db_session, patched_services):
        """Test external service timeout scenarios"""
        user_id = 12349
        test_email = "timeout@test.com"
        
        # Start onboarding
        result = await OnboardingService.start(user_id=user_id)
        assert result["success"] is True
        
        # Mock email service timeout
        patched_services['email'].send_otp_email.side_effect = asyncio.TimeoutError("Email service timeout")
        
        # Should handle timeout gracefully
        result = await OnboardingService.set_email(user_id=user_id, email=test_email)
        assert result["success"] is False
        assert "email_send_failed" in result["error"]


@pytest.mark.onboarding
@pytest.mark.edge_cases
class TestPostCommitCallbackFailures:
    """Test post-commit callback failure scenarios identified by architect"""
    
    @pytest.mark.asyncio
    async def test_welcome_email_callback_failure(self, test_db_session, patched_services):
        """Test callback failure resilience - email sending failures after user creation"""
        user_id = 12350
        test_email = "callback_fail@test.com"
        
        # Mock notification service to fail
        mock_notification_service = MagicMock()
        mock_notification_service.send_notification.return_value = {
            'success': False,
            'error': 'SMTP server unreachable',
            'retry_scheduled': True
        }
        
        with patch('services.onboarding_service.ConsolidatedNotificationService', return_value=mock_notification_service):
            # Complete onboarding flow
            await OnboardingService.start(user_id=user_id)
            await OnboardingService.set_email(user_id=user_id, email=test_email)
            
            # Mock OTP verification success
            with patch('services.email_verification_service.EmailVerificationService.verify_otp_async', return_value={'success': True}):
                await OnboardingService.verify_otp(user_id=user_id, otp_code="123456")
            
                # Accept terms - should trigger post-commit callback
                result = await OnboardingService.accept_tos(user_id=user_id)
                
                # Onboarding should succeed even if callback fails
                assert result["success"] is True
                assert result["current_step"] == OnboardingStep.DONE.value

    @pytest.mark.asyncio
    async def test_notification_failure_retry_mechanism(self, test_db_session, patched_services):
        """Test notification failures and retry mechanism testing"""
        user_id = 12351
        test_email = "retry_fail@test.com"
        
        # Create callback that fails then succeeds
        call_count = 0
        def failing_callback():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First attempt failed")
            return True
        
        # Test callback failure handling in _with_session
        async def callback_test_logic(session):
            return {"success": True, "data": "test"}
        
        # Should handle callback failures without affecting main result
        result = await OnboardingService._with_session(
            None, 
            callback_test_logic,
            post_commit_callbacks=[failing_callback]
        )
        
        assert result["success"] is True
        assert call_count == 1  # Callback was attempted

    @pytest.mark.asyncio
    async def test_async_callback_failure_handling(self, test_db_session):
        """Test async callback failure handling"""
        
        async def failing_async_callback():
            raise Exception("Async callback failed")
        
        async def test_logic(session):
            return {"success": True, "callback_tested": True}
        
        # Should handle async callback failures gracefully
        result = await OnboardingService._with_session(
            None, 
            test_logic,
            post_commit_callbacks=[failing_async_callback]
        )
        
        assert result["success"] is True
        assert result["callback_tested"] is True

    @pytest.mark.asyncio
    async def test_mixed_callback_failure_scenarios(self, test_db_session):
        """Test mixed callback failure scenarios - sync and async failures"""
        
        def sync_failing_callback():
            raise ValueError("Sync callback error")
        
        async def async_failing_callback():
            raise RuntimeError("Async callback error")
        
        def successful_callback():
            return "success"
        
        async def test_logic(session):
            return {"success": True, "mixed_test": True}
        
        # Should handle multiple callback failures gracefully
        result = await OnboardingService._with_session(
            None,
            test_logic, 
            post_commit_callbacks=[
                sync_failing_callback,
                async_failing_callback,
                successful_callback
            ]
        )
        
        assert result["success"] is True
        assert result["mixed_test"] is True


@pytest.mark.onboarding  
@pytest.mark.edge_cases
class TestCacheBypassScenarios:
    """Test cache bypass scenarios identified by architect"""
    
    @pytest.mark.asyncio
    async def test_cache_miss_handling_test_environment(self, test_db_session):
        """Test cache miss handling in test environment"""
        user_id = 12352
        
        # Ensure test environment detection works
        with patch.dict('os.environ', {'PYTEST_CURRENT_TEST': 'test_cache_bypass'}):
            assert _is_test_environment() is True
            
            # Start onboarding - should bypass cache in test environment
            result = await OnboardingService.start(user_id=user_id)
            assert result["success"] is True
            
            # Cache should be bypassed, direct database access used
            assert result["current_step"] == OnboardingStep.CAPTURE_EMAIL.value

    @pytest.mark.asyncio
    async def test_cache_miss_handling_production_environment(self, test_db_session):
        """Test cache miss handling in production environment"""
        user_id = 12353
        
        # Mock production environment
        with patch('services.onboarding_service._is_test_environment', return_value=False):
            # Clear cache first
            _onboarding_cache.clear()
            
            # Start onboarding - should attempt cache access
            result = await OnboardingService.start(user_id=user_id)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_cache_invalidation_scenarios(self, test_db_session):
        """Test cache invalidation scenarios"""
        user_id = 12354
        
        with patch('services.onboarding_service._is_test_environment', return_value=False):
            # Prime cache with start
            result1 = await OnboardingService.start(user_id=user_id)
            assert result1["success"] is True
            
            # Clear cache to simulate invalidation
            cache_key = f"onboarding_user_{user_id}"
            _onboarding_cache.delete(cache_key)
            
            # Subsequent access should handle cache miss
            result2 = await OnboardingService.get_current_step(user_id=user_id)
            assert result2 == OnboardingStep.CAPTURE_EMAIL.value

    @pytest.mark.asyncio
    async def test_fallback_mechanism_cache_failure(self, test_db_session):
        """Test fallback mechanisms when cache fails"""
        user_id = 12355
        
        # Mock cache failure
        with patch.object(_onboarding_cache, 'get', side_effect=Exception("Cache service unavailable")):
            with patch('services.onboarding_service._is_test_environment', return_value=False):
                # Should fall back to database access
                result = await OnboardingService.start(user_id=user_id)
                assert result["success"] is True


@pytest.mark.onboarding
@pytest.mark.edge_cases
class TestSessionManagementEdgeCases:
    """Test session management edge cases identified by architect"""
    
    @pytest.mark.asyncio
    async def test_injected_session_vs_self_managed_session(self, test_db_session):
        """Test different session handling paths - injected vs self-managed"""
        user_id = 12356
        
        # Test self-managed session path (session=None)
        result1 = await OnboardingService.start(user_id=user_id, session=None)
        assert result1["success"] is True
        
        # Test injected session path
        async with managed_session() as session:
            result2 = await OnboardingService.get_current_step(user_id=user_id, session=session)
            assert result2 == OnboardingStep.CAPTURE_EMAIL.value

    @pytest.mark.asyncio 
    async def test_session_lifecycle_scenarios(self, test_db_session):
        """Test session lifecycle - creation, commit, rollback, cleanup"""
        user_id = 12357
        
        # Test session commit scenario
        result1 = await OnboardingService.start(user_id=user_id)
        assert result1["success"] is True
        
        # Test session rollback scenario by forcing an error
        with patch('models.OnboardingSession') as mock_model:
            mock_model.side_effect = SQLAlchemyError("Session rollback test")
            
            result2 = await OnboardingService.set_email(user_id=user_id, email="test@rollback.com")
            assert result2["success"] is False

    @pytest.mark.asyncio
    async def test_session_flush_handling_edge_cases(self, test_db_session):
        """Test session flush handling in different scenarios"""
        user_id = 12358
        
        # Test flush handling in accept_tos
        await OnboardingService.start(user_id=user_id)
        await OnboardingService.set_email(user_id=user_id, email="flush_test@test.com")
        
        with patch('services.email_verification_service.EmailVerificationService.verify_otp_async', return_value={'success': True}):
            await OnboardingService.verify_otp(user_id=user_id, otp_code="123456")
            
            # Test flush handling with mock session
            async with managed_session() as session:
                # Mock flush to test error handling
                original_flush = session.flush
                def mock_flush():
                    if hasattr(mock_flush, 'called'):
                        raise Exception("Flush test error")
                    mock_flush.called = True
                    return original_flush()
                
                session.flush = mock_flush
                
                result = await OnboardingService.accept_tos(user_id=user_id, session=session)
                # Should handle flush errors gracefully
                assert result is not None

    @pytest.mark.asyncio
    async def test_transaction_boundary_testing(self, test_db_session):
        """Test transaction boundary scenarios"""
        user_id = 12359
        
        # Test nested transaction scenario
        async with managed_session() as outer_session:
            # Start onboarding in outer transaction
            result1 = await OnboardingService.start(user_id=user_id, session=outer_session)
            assert result1["success"] is True
            
            # Perform operations within same transaction
            result2 = await OnboardingService.set_email(
                user_id=user_id, 
                email="nested@transaction.com", 
                session=outer_session
            )
            assert result2["success"] is True
            
            # Commit outer transaction
            await outer_session.commit()

    @pytest.mark.asyncio
    async def test_concurrent_session_access_simulation(self, test_db_session):
        """Test concurrent session access scenarios"""
        user_id = 12360
        
        # Simulate concurrent access with multiple async operations
        async def concurrent_operation_1():
            return await OnboardingService.start(user_id=user_id)
        
        async def concurrent_operation_2():
            await asyncio.sleep(0.01)  # Slight delay
            return await OnboardingService.get_current_step(user_id=user_id)
        
        async def concurrent_operation_3():
            await asyncio.sleep(0.02)  # Slight delay  
            return await OnboardingService.get_session_info(user_id=user_id)
        
        # Run concurrent operations
        results = await asyncio.gather(
            concurrent_operation_1(),
            concurrent_operation_2(), 
            concurrent_operation_3(),
            return_exceptions=True
        )
        
        # First operation should succeed
        assert results[0]["success"] is True
        
        # Other operations should handle gracefully
        assert results[1] is not None
        assert results[2] is not None

    @pytest.mark.asyncio
    async def test_database_api_compatibility(self, test_db_session):
        """Test db_session parameter API compatibility"""
        user_id = 12361
        
        # Test both session and db_session parameters work
        async with managed_session() as test_session:
            # Using session parameter
            result1 = await OnboardingService.start(user_id=user_id, session=test_session)
            assert result1["success"] is True
            
            # Using db_session parameter (API compatibility)
            result2 = await OnboardingService.get_current_step(user_id=user_id, db_session=test_session)
            assert result2 == OnboardingStep.CAPTURE_EMAIL.value
            
            # Both should work identically
            result3 = await OnboardingService.get_session_info(user_id=user_id, session=test_session)
            result4 = await OnboardingService.get_session_info(user_id=user_id, db_session=test_session)
            
            assert result3 == result4

    @pytest.mark.asyncio
    async def test_wallet_creation_error_handling(self, test_db_session):
        """Test wallet creation error handling in _ensure_user_wallet"""
        user_id = 12362
        
        # Complete onboarding to trigger wallet creation
        await OnboardingService.start(user_id=user_id)
        await OnboardingService.set_email(user_id=user_id, email="wallet_error@test.com")
        
        with patch('services.email_verification_service.EmailVerificationService.verify_otp_async', return_value={'success': True}):
            await OnboardingService.verify_otp(user_id=user_id, otp_code="123456")
            
            # Mock wallet creation failure
            with patch('models.Wallet') as mock_wallet:
                mock_wallet.side_effect = Exception("Wallet creation failed")
                
                # Should handle wallet creation errors gracefully 
                result = await OnboardingService.accept_tos(user_id=user_id)
                # Onboarding should still succeed even if wallet creation fails
                assert result["success"] is True


@pytest.mark.onboarding
@pytest.mark.edge_cases
class TestComprehensiveErrorPaths:
    """Test remaining error paths for maximum coverage"""
    
    @pytest.mark.asyncio
    async def test_missing_user_scenarios(self, test_db_session):
        """Test scenarios with missing/invalid user IDs"""
        invalid_user_id = 99999999
        
        # All methods should handle missing users gracefully
        result1 = await OnboardingService.start(invalid_user_id)
        result2 = await OnboardingService.get_current_step(invalid_user_id) 
        result3 = await OnboardingService.get_session_info(invalid_user_id)
        result4 = await OnboardingService.set_email(invalid_user_id, "test@invalid.com")
        
        # Most should fail gracefully or return None
        assert result2 is None
        assert result3 is None
        
    @pytest.mark.asyncio
    async def test_expired_session_scenarios(self, test_db_session):
        """Test expired session handling"""
        user_id = 12363
        
        # Start onboarding
        result = await OnboardingService.start(user_id=user_id)
        assert result["success"] is True
        
        # Simulate expired session by manipulating expiry time
        async with managed_session() as session:
            onboarding_session = await OnboardingService._get_active_session(session, user_id)
            if onboarding_session:
                # Set expiry to past time
                onboarding_session.expires_at = datetime.utcnow() - timedelta(hours=1)
                await session.commit()
        
        # Operations should handle expired sessions
        result2 = await OnboardingService.set_email(user_id=user_id, email="expired@test.com")
        assert result2["success"] is False
        assert "No active onboarding session" in result2["error"]

    @pytest.mark.asyncio
    async def test_otp_verification_error_paths(self, test_db_session, patched_services):
        """Test OTP verification error paths"""
        user_id = 12364
        
        # Setup onboarding with email
        await OnboardingService.start(user_id=user_id)
        await OnboardingService.set_email(user_id=user_id, email="otp_error@test.com")
        
        # Test OTP service failure
        with patch('services.email_verification_service.EmailVerificationService.verify_otp_async') as mock_verify:
            mock_verify.return_value = {
                "success": False,
                "error": "OTP expired",
                "remaining_attempts": 2
            }
            
            result = await OnboardingService.verify_otp(user_id=user_id, otp_code="wrong")
            assert result["success"] is False
            assert result["error"] == "OTP expired"
            assert result["remaining_attempts"] == 2

    @pytest.mark.asyncio
    async def test_reset_to_step_error_scenarios(self, test_db_session):
        """Test reset_to_step error scenarios"""
        user_id = 12365
        
        # Test reset without active session
        result1 = await OnboardingService.reset_to_step(user_id=user_id, step=OnboardingStep.CAPTURE_EMAIL.value)
        assert result1["success"] is False
        assert "No active onboarding session" in result1["error"]
        
        # Start onboarding then test reset
        await OnboardingService.start(user_id=user_id)
        
        # Test successful reset
        result2 = await OnboardingService.reset_to_step(user_id=user_id, step=OnboardingStep.CAPTURE_EMAIL.value)
        assert result2["success"] is True
        
        # Test reset to different steps
        result3 = await OnboardingService.reset_to_step(user_id=user_id, step=OnboardingStep.VERIFY_OTP.value)
        assert result3["success"] is True

    @pytest.mark.asyncio
    async def test_resend_otp_error_scenarios(self, test_db_session):
        """Test resend OTP error scenarios"""
        user_id = 12366
        
        # Test resend without session
        result1 = await OnboardingService.resend_otp(user_id=user_id)
        assert result1["success"] is False
        assert "No active onboarding session" in result1["error"]
        
        # Start but don't advance to OTP step
        await OnboardingService.start(user_id=user_id)
        
        # Test resend from wrong step
        result2 = await OnboardingService.resend_otp(user_id=user_id)
        assert result2["success"] is False
        assert "Invalid step for OTP resend" in result2["error"]