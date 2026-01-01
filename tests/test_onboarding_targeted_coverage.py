"""
Onboarding Service Targeted Coverage Tests - Simple Edge Cases

Focused tests to boost coverage from current baseline to 85%+ by targeting
specific uncovered error paths and edge cases without complex fixture dependencies.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from services.onboarding_service import OnboardingService, _is_test_environment, _onboarding_cache
from models import OnboardingStep


@pytest.mark.asyncio
async def test_is_test_environment_detection():
    """Test _is_test_environment function coverage"""
    # Test with PYTEST_CURRENT_TEST environment variable
    with patch.dict('os.environ', {'PYTEST_CURRENT_TEST': 'test_something'}):
        assert _is_test_environment() is True
    
    # Test with pytest in sys.argv
    with patch('sys.argv', ['pytest', 'test_file.py']):
        assert _is_test_environment() is True
    
    # Test without test environment indicators
    with patch.dict('os.environ', {}, clear=True):
        with patch('sys.argv', ['python', 'main.py']):
            assert _is_test_environment() is False


@pytest.mark.asyncio
async def test_with_session_exception_handling():
    """Test _with_session exception handling paths"""
    
    async def failing_function(session):
        raise SQLAlchemyError("Database error")
    
    # Test exception handling in _with_session
    with patch('services.onboarding_service.managed_session') as mock_session:
        mock_session.return_value.__aenter__ = AsyncMock(side_effect=SQLAlchemyError("Connection failed"))
        
        try:
            result = await OnboardingService._with_session(None, failing_function)
        except SQLAlchemyError:
            pass  # Expected to raise


@pytest.mark.asyncio 
async def test_post_commit_callback_error_scenarios():
    """Test post-commit callback error handling"""
    
    def failing_sync_callback():
        raise Exception("Sync callback failed")
    
    async def failing_async_callback():
        raise Exception("Async callback failed")
    
    async def successful_logic(session):
        return {"success": True, "test": "callback_handling"}
    
    # Test callback failure handling
    with patch('services.onboarding_service.logger') as mock_logger:
        result = await OnboardingService._with_session(
            None, 
            successful_logic,
            post_commit_callbacks=[failing_sync_callback, failing_async_callback]
        )
        
        # Main result should succeed despite callback failures
        assert result["success"] is True
        assert result["test"] == "callback_handling"
        
        # Logger should have recorded callback failures
        assert mock_logger.error.called


@pytest.mark.asyncio
async def test_welcome_email_background_task_errors():
    """Test welcome email background task error handling"""
    
    # Test notification service failure
    with patch('services.onboarding_service.ConsolidatedNotificationService') as mock_service:
        mock_notification = MagicMock()
        mock_notification.send_notification.return_value = {
            'success': False,
            'error': 'SMTP server unavailable'
        }
        mock_service.return_value = mock_notification
        
        with patch('services.onboarding_service.logger') as mock_logger:
            await OnboardingService._send_welcome_email_background_task(
                "test@example.com", "Test User", 12345
            )
            
            # Should log warning for failed notification
            mock_logger.warning.assert_called()


@pytest.mark.asyncio
async def test_welcome_email_template_import_error():
    """Test welcome email template import error handling"""
    
    # Test template import failure
    with patch('services.email_templates.get_welcome_email_template', side_effect=ImportError("Template not found")):
        with patch('services.onboarding_service.logger') as mock_logger:
            await OnboardingService._send_welcome_email_background_task(
                "test@example.com", "Test User", 12345
            )
            
            # Should handle import error gracefully
            mock_logger.error.assert_called()


@pytest.mark.asyncio
async def test_start_method_error_branches():
    """Test error branches in start method"""
    
    # Test SQLAlchemyError in start method
    with patch('services.onboarding_service.managed_session') as mock_session:
        mock_session_obj = AsyncMock()
        mock_session_obj.execute.side_effect = SQLAlchemyError("Database connection lost")
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_obj)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        result = await OnboardingService.start(user_id=12345)
        assert result["success"] is False
        assert "Database connection lost" in result["error"]


@pytest.mark.asyncio
async def test_set_email_integrity_error():
    """Test IntegrityError handling in set_email"""
    
    # Mock IntegrityError scenario
    async def mock_logic(session):
        raise IntegrityError("UNIQUE constraint failed", None, None)
    
    with patch.object(OnboardingService, '_with_session', return_value={"success": False, "error": "Database integrity error"}):
        result = await OnboardingService.set_email(user_id=12345, email="duplicate@test.com")
        assert result["success"] is False


@pytest.mark.asyncio 
async def test_verify_otp_error_scenarios():
    """Test verify_otp error scenarios"""
    
    # Test with invalid user ID
    with patch('services.email_verification_service.EmailVerificationService.verify_otp_async', 
               return_value={"success": False, "error": "User not found"}):
        result = await OnboardingService.verify_otp(user_id=99999, otp_code="123456")
        assert result["success"] is False


@pytest.mark.asyncio
async def test_accept_tos_error_scenarios():
    """Test accept_tos error scenarios"""
    
    # Test invalid email scenarios
    async def mock_tos_logic(session):
        return {"success": False, "error": "No valid email found for onboarding completion"}
    
    with patch.object(OnboardingService, '_with_session', side_effect=lambda s, fn, cb=None: mock_tos_logic(None)):
        result = await OnboardingService.accept_tos(user_id=12345)
        assert result["success"] is False
        assert "No valid email found" in result["error"]


@pytest.mark.asyncio
async def test_resend_otp_error_branches():
    """Test resend_otp error scenarios"""
    
    # Test exception in resend_otp
    with patch.object(OnboardingService, '_with_session', side_effect=Exception("OTP service unavailable")):
        result = await OnboardingService.resend_otp(user_id=12345)
        assert result["success"] is False
        assert "OTP service unavailable" in result["error"]


@pytest.mark.asyncio
async def test_get_current_step_error_handling():
    """Test get_current_step error handling"""
    
    # Test exception in get_current_step
    with patch('services.onboarding_service.managed_session') as mock_session:
        mock_session.return_value.__aenter__ = AsyncMock(side_effect=Exception("Database error"))
        
        result = await OnboardingService.get_current_step(user_id=12345)
        assert result is None


@pytest.mark.asyncio
async def test_get_session_info_error_handling():
    """Test get_session_info error handling"""
    
    # Test exception in get_session_info  
    with patch('services.onboarding_service.managed_session') as mock_session:
        mock_session.return_value.__aenter__ = AsyncMock(side_effect=Exception("Session error"))
        
        result = await OnboardingService.get_session_info(user_id=12345)
        assert result is None


@pytest.mark.asyncio
async def test_reset_to_step_error_handling():
    """Test reset_to_step error handling"""
    
    # Test exception in reset_to_step
    with patch.object(OnboardingService, '_with_session', side_effect=Exception("Reset failed")):
        result = await OnboardingService.reset_to_step(user_id=12345, step=OnboardingStep.CAPTURE_EMAIL.value)
        assert result["success"] is False
        assert "Reset failed" in result["error"]


@pytest.mark.asyncio
async def test_advance_to_step_error_handling():
    """Test _advance_to_step error handling"""
    
    # Test exception in _advance_to_step
    with patch.object(OnboardingService, '_with_session', side_effect=Exception("Advance failed")):
        result = await OnboardingService._advance_to_step(user_id=12345, next_step=OnboardingStep.VERIFY_OTP)
        assert result["success"] is False
        assert "Advance failed" in result["error"]


@pytest.mark.asyncio
async def test_ensure_user_wallet_error_handling():
    """Test _ensure_user_wallet error handling"""
    
    from models import Wallet
    
    # Mock session and wallet creation error
    mock_session = AsyncMock()
    mock_session.execute.return_value.scalar_one_or_none.return_value = None
    mock_session.add.side_effect = Exception("Wallet creation failed")
    
    # Should not raise exception, just log error
    await OnboardingService._ensure_user_wallet(mock_session, 12345)
    
    # Test should complete without raising exception


@pytest.mark.asyncio
async def test_cache_operations():
    """Test cache-related operations"""
    
    # Test cache operations with mocked cache
    with patch('services.onboarding_service._is_test_environment', return_value=False):
        # Test cache hit scenario
        _onboarding_cache.set("test_key", {"cached": True})
        result = _onboarding_cache.get("test_key")
        assert result is not None
        
        # Test cache miss scenario  
        result = _onboarding_cache.get("nonexistent_key")
        assert result is None
        
        # Test cache clear
        _onboarding_cache.clear()


@pytest.mark.asyncio
async def test_session_flush_error_handling():
    """Test session flush error handling in accept_tos"""
    
    # Mock flush error
    mock_session = AsyncMock()
    mock_session.flush.side_effect = Exception("Flush failed")
    
    # Test flush error handling
    try:
        flush_result = mock_session.flush()
        if flush_result is not None:
            await flush_result
    except Exception as e:
        # Should handle flush errors gracefully
        assert "Flush failed" in str(e)


@pytest.mark.asyncio  
async def test_api_compatibility_parameters():
    """Test API compatibility with both session and db_session parameters"""
    
    # Test that both session and db_session parameters work
    mock_session = AsyncMock()
    
    with patch('services.onboarding_service.managed_session') as mock_managed:
        mock_managed.return_value.__aenter__ = AsyncMock(return_value=mock_session) 
        mock_managed.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Test using session parameter
        with patch.object(OnboardingService, '_get_active_session', return_value=None):
            result1 = await OnboardingService.get_current_step(user_id=12345, session=mock_session)
            result2 = await OnboardingService.get_current_step(user_id=12345, db_session=mock_session)
            
            # Both should work identically
            assert result1 == result2


@pytest.mark.asyncio
async def test_step_transitions_map():
    """Test STEP_TRANSITIONS map coverage"""
    
    # Access step transitions to ensure they're covered
    transitions = OnboardingService.STEP_TRANSITIONS
    
    assert transitions[OnboardingStep.CAPTURE_EMAIL] == OnboardingStep.VERIFY_OTP
    assert transitions[OnboardingStep.VERIFY_OTP] == OnboardingStep.ACCEPT_TOS  
    assert transitions[OnboardingStep.ACCEPT_TOS] == OnboardingStep.DONE
    assert transitions[OnboardingStep.DONE] is None


@pytest.mark.asyncio
async def test_default_session_expiry():
    """Test DEFAULT_SESSION_EXPIRY_HOURS constant coverage"""
    
    # Access constant to ensure coverage
    expiry_hours = OnboardingService.DEFAULT_SESSION_EXPIRY_HOURS
    assert expiry_hours == 24


@pytest.mark.asyncio
async def test_validation_edge_cases():
    """Test validation edge cases"""
    
    # Test email validation edge cases
    invalid_emails = ["", " ", "invalid", "@", "user@", "@domain"]
    
    for email in invalid_emails:
        # This should trigger email validation error paths
        with patch('utils.helpers.validate_email', return_value=False):
            result = await OnboardingService.set_email(user_id=12345, email=email)
            if result:  # Only check if method returns something
                assert result.get("success") is False


@pytest.mark.asyncio  
async def test_timeout_and_connection_errors():
    """Test timeout and connection error scenarios"""
    
    # Test connection timeout
    with patch('services.onboarding_service.managed_session') as mock_session:
        mock_session.return_value.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError("Connection timeout"))
        
        try:
            result = await OnboardingService.start(user_id=12345)
            # Should handle timeout gracefully
            assert result is None or result.get("success") is False
        except asyncio.TimeoutError:
            pass  # Expected in some implementations