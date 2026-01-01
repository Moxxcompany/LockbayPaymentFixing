"""
Unit Tests for Onboarding Router Coverage - Direct Function Testing

This suite focuses on unit testing specific functions in handlers/onboarding_router.py
to achieve 95%+ coverage without complex database dependencies.

Target: Push coverage from 53% to 95%+ by testing:
- Exception handling paths
- Callback routing logic  
- Input validation
- Step rendering functions
- Cache and idempotency logic
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

# Direct function imports for unit testing
from handlers.onboarding_router import (
    _get_user_lock, _get_step_signature, _should_suppress_duplicate,
    _record_step_render, OnboardingCallbacks, OnboardingText
)


class TestUtilityFunctions:
    """Test utility functions for coverage"""
    
    def test_get_user_lock_new_user(self):
        """Test _get_user_lock creates new lock for new user"""
        user_id = 999999999
        lock1 = _get_user_lock(user_id)
        lock2 = _get_user_lock(user_id) 
        
        # Should return same lock for same user
        assert lock1 is lock2
        assert isinstance(lock1, asyncio.Lock)
    
    def test_get_step_signature_with_email(self):
        """Test _get_step_signature with email"""
        signature = _get_step_signature("capture_email", "test@example.com")
        assert signature == "capture_email:test@example.com"
    
    def test_get_step_signature_without_email(self):
        """Test _get_step_signature without email"""
        signature = _get_step_signature("verify_otp", None)
        assert signature == "verify_otp:"
        
        signature2 = _get_step_signature("verify_otp")
        assert signature2 == "verify_otp:"
    
    def test_should_suppress_duplicate_no_cache(self):
        """Test _should_suppress_duplicate with no cached data"""
        # Clear any existing cache first
        from handlers.onboarding_router import _step_cache
        _step_cache.clear()
        
        should_suppress, message_id = _should_suppress_duplicate(123, "test_signature")
        assert should_suppress is False
        assert message_id is None
    
    def test_record_and_suppress_duplicate_flow(self):
        """Test full flow: record step then check suppression"""
        from handlers.onboarding_router import _step_cache
        _step_cache.clear()
        
        user_id = 456
        signature = "test_flow_signature"
        message_id = 789
        
        # Record step
        _record_step_render(user_id, signature, message_id)
        
        # Check suppression (should trigger line 61)
        should_suppress, returned_message_id = _should_suppress_duplicate(user_id, signature)
        
        assert should_suppress is True  # This triggers the missing line 61
        assert returned_message_id == message_id


class TestCallbackConstants:
    """Test callback and text constants for coverage"""
    
    def test_onboarding_callbacks_constants(self):
        """Test OnboardingCallbacks constants are defined"""
        assert OnboardingCallbacks.START == "ob:start"
        assert OnboardingCallbacks.RESEND_OTP == "ob:resend"
        assert OnboardingCallbacks.CHANGE_EMAIL == "ob:change:email"
        assert OnboardingCallbacks.TOS_ACCEPT == "ob:tos:accept"
        assert OnboardingCallbacks.TOS_DECLINE == "ob:tos:decline"
        assert OnboardingCallbacks.CANCEL == "ob:cancel"
        assert OnboardingCallbacks.HELP_EMAIL == "ob:help:email"
        assert OnboardingCallbacks.HELP_OTP == "ob:help:otp"
        assert OnboardingCallbacks.HELP_TERMS == "ob:help:terms"
    
    def test_onboarding_text_constants(self):
        """Test OnboardingText constants and templates"""
        # Test progress indicators
        assert "📧 Step 1/3" in OnboardingText.PROGRESS_INDICATORS.values()
        assert "🔐 Step 2/3" in OnboardingText.PROGRESS_INDICATORS.values()
        assert "📋 Step 3/3" in OnboardingText.PROGRESS_INDICATORS.values()
        
        # Test progress bars  
        assert "🟦⬜⬜" in OnboardingText.PROGRESS_BARS.values()
        assert "🟦🟦⬜" in OnboardingText.PROGRESS_BARS.values()
        assert "🟦🟦🟦" in OnboardingText.PROGRESS_BARS.values()
        
        # Test error messages
        assert "invalid_email" in OnboardingText.ERROR_MESSAGES
        assert "email_taken" in OnboardingText.ERROR_MESSAGES
        assert "otp_invalid" in OnboardingText.ERROR_MESSAGES
        assert "system_error" in OnboardingText.ERROR_MESSAGES
        
        # Test message templates contain expected content
        assert "Welcome to LockBay" in OnboardingText.WELCOME
        assert "Enter your email address" in OnboardingText.EMAIL_PROMPT
        assert "Enter the 6-digit code" in OnboardingText.OTP_PROMPT
        assert "Accept Terms" in OnboardingText.TERMS_PROMPT
        assert "Account Setup Complete" in OnboardingText.COMPLETION


@pytest.mark.asyncio 
class TestMockedAsyncFunctions:
    """Test async functions with heavy mocking to avoid database dependencies"""
    
    async def test_get_or_create_user_none_input(self):
        """Test get_or_create_user with None telegram_user - line 180"""
        from handlers.onboarding_router import get_or_create_user
        
        # Mock session
        mock_session = MagicMock()
        
        # Test None input (should trigger line 180)
        user, is_new = await get_or_create_user(mock_session, None)
        
        assert user is None
        assert is_new is False
    
    async def test_render_step_unknown_step(self):
        """Test render_step with unknown step"""
        from handlers.onboarding_router import render_step
        
        # Mock update
        mock_update = MagicMock()
        
        with patch('handlers.onboarding_router.logger') as mock_logger:
            await render_step(mock_update, "unknown_step_name")
            
            # Should log warning for unknown step
            mock_logger.warning.assert_called_once_with("Unknown onboarding step: unknown_step_name")
    
    async def test_transition_unknown_action(self):
        """Test transition with unknown action"""
        from handlers.onboarding_router import transition
        
        result = await transition(123, "unknown_action", "test_data")
        
        assert result["success"] is False
        assert "Unknown action" in result["error"]
    
    async def test_transition_set_email_action(self):
        """Test transition with set_email action"""
        from handlers.onboarding_router import transition
        
        with patch('handlers.onboarding_router.OnboardingService.set_email') as mock_service:
            mock_service.return_value = {"success": True, "current_step": "verify_otp"}
            
            result = await transition(123, "set_email", "test@example.com")
            
            mock_service.assert_called_once_with(123, "test@example.com", session=None)
            assert result["success"] is True
    
    async def test_transition_verify_otp_action(self):
        """Test transition with verify_otp action"""
        from handlers.onboarding_router import transition
        
        with patch('handlers.onboarding_router.OnboardingService.verify_otp') as mock_service:
            mock_service.return_value = {"success": True, "current_step": "accept_tos"}
            
            result = await transition(123, "verify_otp", "123456")
            
            mock_service.assert_called_once_with(123, "123456", session=None)
            assert result["success"] is True
    
    async def test_transition_accept_terms_action(self):
        """Test transition with accept_terms action"""
        from handlers.onboarding_router import transition
        
        with patch('handlers.onboarding_router.OnboardingService.accept_tos') as mock_service:
            mock_service.return_value = {"success": True, "current_step": "done"}
            
            result = await transition(123, "accept_terms")
            
            mock_service.assert_called_once_with(123)
            assert result["success"] is True
    
    async def test_transition_resend_otp_action(self):
        """Test transition with resend_otp action"""
        from handlers.onboarding_router import transition
        
        with patch('handlers.onboarding_router.OnboardingService.resend_otp') as mock_service:
            mock_service.return_value = {"success": True, "message": "OTP sent"}
            
            result = await transition(123, "resend_otp")
            
            mock_service.assert_called_once_with(123, session=None)
            assert result["success"] is True
    
    async def test_transition_reset_email_action(self):
        """Test transition with reset_email action"""
        from handlers.onboarding_router import transition
        
        with patch('handlers.onboarding_router.OnboardingService.reset_to_step') as mock_service:
            mock_service.return_value = {"success": True, "current_step": "capture_email"}
            
            result = await transition(123, "reset_email")
            
            mock_service.assert_called_once()
            assert result["success"] is True
    
    async def test_transition_exception_handling(self):
        """Test transition exception handling"""
        from handlers.onboarding_router import transition
        
        with patch('handlers.onboarding_router.OnboardingService.set_email', side_effect=Exception("service error")):
            result = await transition(123, "set_email", "test@example.com")
            
            assert result["success"] is False
            assert "service error" in result["error"]
    
    async def test_invalidate_user_cache_async(self):
        """Test invalidate_user_cache_async"""
        from handlers.onboarding_router import invalidate_user_cache_async
        
        with patch('handlers.onboarding_router.run_io_task') as mock_io_task, \
             patch('handlers.onboarding_router._user_lookup_cache') as mock_cache:
            
            await invalidate_user_cache_async("123")
            
            mock_io_task.assert_called_once()
            assert mock_cache.delete.call_count == 2  # Called twice for different cache keys
    
    async def test_invalidate_user_cache_async_exception(self):
        """Test invalidate_user_cache_async exception handling"""
        from handlers.onboarding_router import invalidate_user_cache_async
        
        with patch('handlers.onboarding_router.run_io_task', side_effect=Exception("cache error")), \
             patch('handlers.onboarding_router.logger') as mock_logger:
            
            await invalidate_user_cache_async("123")
            
            # Should log warning but not raise exception
            mock_logger.warning.assert_called_once()


@pytest.mark.asyncio
class TestRenderFunctionsMocked:
    """Test render functions with mocking to avoid complex dependencies"""
    
    async def test_render_step_capture_email(self):
        """Test render_step routing to email step"""
        from handlers.onboarding_router import render_step
        from models import OnboardingStep
        
        mock_update = MagicMock()
        
        with patch('handlers.onboarding_router._render_email_step') as mock_render:
            await render_step(mock_update, OnboardingStep.CAPTURE_EMAIL.value, test_param="value")
            
            mock_render.assert_called_once_with(mock_update, test_param="value")
    
    async def test_render_step_verify_otp(self):
        """Test render_step routing to OTP step"""
        from handlers.onboarding_router import render_step
        from models import OnboardingStep
        
        mock_update = MagicMock()
        
        with patch('handlers.onboarding_router._render_otp_step') as mock_render:
            await render_step(mock_update, OnboardingStep.VERIFY_OTP.value, email="test@example.com")
            
            mock_render.assert_called_once_with(mock_update, email="test@example.com")
    
    async def test_render_step_accept_tos(self):
        """Test render_step routing to terms step"""
        from handlers.onboarding_router import render_step
        from models import OnboardingStep
        
        mock_update = MagicMock()
        
        with patch('handlers.onboarding_router._render_terms_step') as mock_render:
            await render_step(mock_update, OnboardingStep.ACCEPT_TOS.value)
            
            mock_render.assert_called_once_with(mock_update)
    
    async def test_render_step_done(self):
        """Test render_step routing to completion step"""
        from handlers.onboarding_router import render_step
        from models import OnboardingStep
        
        mock_update = MagicMock()
        
        with patch('handlers.onboarding_router._render_completion_step') as mock_render:
            await render_step(mock_update, OnboardingStep.DONE.value, email="test@example.com")
            
            mock_render.assert_called_once_with(mock_update, email="test@example.com")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])