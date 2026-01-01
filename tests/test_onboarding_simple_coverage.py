"""
Simple Onboarding Coverage Tests - No Complex Fixtures

Direct unit tests for handlers/onboarding_router.py functions
to achieve 95%+ coverage without database fixture dependencies.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

# Direct imports 
import sys
import os
sys.path.append('.')

# Skip complex fixtures by importing directly
def test_get_user_lock():
    """Test _get_user_lock creates locks properly"""
    from handlers.onboarding_router import _get_user_lock
    
    user_id = 999999999
    lock1 = _get_user_lock(user_id)
    lock2 = _get_user_lock(user_id) 
    
    assert lock1 is lock2
    assert isinstance(lock1, asyncio.Lock)

def test_get_step_signature():
    """Test step signature generation"""
    from handlers.onboarding_router import _get_step_signature
    
    sig1 = _get_step_signature("capture_email", "test@example.com")
    assert sig1 == "capture_email:test@example.com"
    
    sig2 = _get_step_signature("verify_otp", None)
    assert sig2 == "verify_otp:"
    
    sig3 = _get_step_signature("verify_otp")
    assert sig3 == "verify_otp:"

def test_duplicate_suppression_flow():
    """Test the complete duplicate suppression flow - targets line 61"""
    from handlers.onboarding_router import (
        _should_suppress_duplicate, _record_step_render, _step_cache
    )
    
    # Clear cache first
    _step_cache.clear()
    
    user_id = 456789
    signature = "test_flow_signature"
    message_id = 789
    
    # Initially no suppression
    should_suppress, returned_id = _should_suppress_duplicate(user_id, signature)
    assert should_suppress is False
    assert returned_id is None
    
    # Record the step
    _record_step_render(user_id, signature, message_id)
    
    # Now should suppress (this triggers line 61)
    should_suppress, returned_id = _should_suppress_duplicate(user_id, signature)
    assert should_suppress is True  # This exercises line 61!
    assert returned_id == message_id

def test_onboarding_constants():
    """Test all onboarding constants"""
    from handlers.onboarding_router import OnboardingCallbacks, OnboardingText
    
    # Test callbacks
    assert OnboardingCallbacks.START == "ob:start"
    assert OnboardingCallbacks.RESEND_OTP == "ob:resend"
    assert OnboardingCallbacks.CHANGE_EMAIL == "ob:change:email"
    assert OnboardingCallbacks.TOS_ACCEPT == "ob:tos:accept"
    assert OnboardingCallbacks.TOS_DECLINE == "ob:tos:decline"
    assert OnboardingCallbacks.CANCEL == "ob:cancel"
    
    # Test text constants
    assert "Welcome to LockBay" in OnboardingText.WELCOME
    assert "Enter your email address" in OnboardingText.EMAIL_PROMPT
    assert "Enter the 6-digit code" in OnboardingText.OTP_PROMPT
    assert "Accept Terms" in OnboardingText.TERMS_PROMPT
    assert "Account Setup Complete" in OnboardingText.COMPLETION
    
    # Test error messages
    assert "invalid_email" in OnboardingText.ERROR_MESSAGES
    assert "system_error" in OnboardingText.ERROR_MESSAGES

@pytest.mark.asyncio
async def test_get_or_create_user_none_input():
    """Test get_or_create_user with None input - line 180"""
    from handlers.onboarding_router import get_or_create_user
    
    mock_session = MagicMock()
    
    # Test None input (triggers line 180)
    user, is_new = await get_or_create_user(mock_session, None)
    
    assert user is None
    assert is_new is False

@pytest.mark.asyncio
async def test_transition_functions():
    """Test all transition actions"""
    from handlers.onboarding_router import transition
    
    # Test unknown action
    result = await transition(123, "unknown_action", "data")
    assert result["success"] is False
    assert "Unknown action" in result["error"]
    
    # Test set_email action
    with patch('handlers.onboarding_router.OnboardingService.set_email') as mock:
        mock.return_value = {"success": True, "current_step": "verify_otp"}
        result = await transition(123, "set_email", "test@example.com")
        assert result["success"] is True
        mock.assert_called_once()
    
    # Test verify_otp action  
    with patch('handlers.onboarding_router.OnboardingService.verify_otp') as mock:
        mock.return_value = {"success": True, "current_step": "accept_tos"}
        result = await transition(123, "verify_otp", "123456")
        assert result["success"] is True
        mock.assert_called_once()
    
    # Test accept_terms action
    with patch('handlers.onboarding_router.OnboardingService.accept_tos') as mock:
        mock.return_value = {"success": True, "current_step": "done"}
        result = await transition(123, "accept_terms")
        assert result["success"] is True
        mock.assert_called_once()
    
    # Test resend_otp action
    with patch('handlers.onboarding_router.OnboardingService.resend_otp') as mock:
        mock.return_value = {"success": True, "message": "OTP sent"}
        result = await transition(123, "resend_otp")
        assert result["success"] is True
        mock.assert_called_once()
    
    # Test reset_email action
    with patch('handlers.onboarding_router.OnboardingService.reset_to_step') as mock:
        mock.return_value = {"success": True, "current_step": "capture_email"}
        result = await transition(123, "reset_email")
        assert result["success"] is True
        mock.assert_called_once()
    
    # Test exception handling
    with patch('handlers.onboarding_router.OnboardingService.set_email', side_effect=Exception("error")):
        result = await transition(123, "set_email", "test@example.com")
        assert result["success"] is False
        assert "error" in result["error"]

@pytest.mark.asyncio
async def test_render_step_routing():
    """Test render_step routes to correct functions"""
    from handlers.onboarding_router import render_step
    from models import OnboardingStep
    
    mock_update = MagicMock()
    
    # Test email step routing
    with patch('handlers.onboarding_router._render_email_step') as mock:
        await render_step(mock_update, OnboardingStep.CAPTURE_EMAIL.value)
        mock.assert_called_once()
    
    # Test OTP step routing
    with patch('handlers.onboarding_router._render_otp_step') as mock:
        await render_step(mock_update, OnboardingStep.VERIFY_OTP.value, email="test@example.com")
        mock.assert_called_once()
    
    # Test terms step routing
    with patch('handlers.onboarding_router._render_terms_step') as mock:
        await render_step(mock_update, OnboardingStep.ACCEPT_TOS.value)
        mock.assert_called_once()
    
    # Test completion step routing
    with patch('handlers.onboarding_router._render_completion_step') as mock:
        await render_step(mock_update, OnboardingStep.DONE.value)
        mock.assert_called_once()
    
    # Test unknown step (should log warning)
    with patch('handlers.onboarding_router.logger') as mock_logger:
        await render_step(mock_update, "unknown_step")
        mock_logger.warning.assert_called_once()

@pytest.mark.asyncio
async def test_invalidate_user_cache_async():
    """Test cache invalidation"""
    from handlers.onboarding_router import invalidate_user_cache_async
    
    with patch('handlers.onboarding_router.run_io_task') as mock_io, \
         patch('handlers.onboarding_router._user_lookup_cache') as mock_cache:
        
        await invalidate_user_cache_async("123")
        
        mock_io.assert_called_once()
        assert mock_cache.delete.call_count == 2
    
    # Test exception handling
    with patch('handlers.onboarding_router.run_io_task', side_effect=Exception("cache error")), \
         patch('handlers.onboarding_router.logger') as mock_logger:
        
        await invalidate_user_cache_async("123")
        mock_logger.warning.assert_called_once()

if __name__ == "__main__":
    # Run tests directly
    import subprocess
    result = subprocess.run([
        "python", "-m", "pytest", __file__, 
        "--cov=handlers.onboarding_router", 
        "--cov-report=term", 
        "--cov-report=html:htmlcov_simple",
        "-v"
    ], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print(f"Exit code: {result.returncode}")