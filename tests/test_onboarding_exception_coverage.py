"""
Exception Coverage Tests for Onboarding Router

Targets specific uncovered exception handling paths identified in coverage analysis:
- IntegrityError handling (lines 211-262)
- Message edit failures (lines 302-304) 
- Transition errors (lines 352-354)
- Cache invalidation errors (lines 363-364)
- Callback editing errors (lines 432-434)
- General router errors (lines 459-461)
- Input validation errors (lines 660-662, 774-776)

Goal: Push coverage from 24% to 95%+ by targeting specific uncovered branches.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.exc import IntegrityError

# Direct imports for unit testing
import sys
sys.path.append('.')

@pytest.mark.asyncio
async def test_get_or_create_user_integrity_error():
    """Test IntegrityError handling in get_or_create_user - lines 211-262"""
    from handlers.onboarding_router import get_or_create_user
    
    mock_session = AsyncMock()
    mock_telegram_user = MagicMock()
    mock_telegram_user.id = 123456789
    mock_telegram_user.username = "testuser"
    mock_telegram_user.first_name = "Test"
    mock_telegram_user.last_name = "User"
    
    # Mock initial add operation to raise IntegrityError (line 217)
    mock_session.add.side_effect = IntegrityError("statement", "params", "orig")
    
    # Mock successful rollback and recovery query (lines 232-235)
    mock_session.rollback = AsyncMock()
    mock_session.expunge_all = MagicMock()
    
    # Mock successful user fetch after rollback
    from models import User
    existing_user = User(id=1, telegram_id=123456789)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_session.execute.return_value = mock_result
    
    # Execute test - should trigger IntegrityError path and recovery
    user, is_new = await get_or_create_user(mock_session, mock_telegram_user)
    
    # Verify IntegrityError handling was triggered
    assert user == existing_user
    assert is_new is False
    mock_session.expunge_all.assert_called_once()
    mock_session.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_get_or_create_user_fetch_failure_after_integrity_error():
    """Test fetch failure after IntegrityError - lines 260-262"""
    from handlers.onboarding_router import get_or_create_user
    
    mock_session = AsyncMock()
    mock_telegram_user = MagicMock()
    mock_telegram_user.id = 123456789
    
    # Mock IntegrityError on add
    mock_session.add.side_effect = IntegrityError("statement", "params", "orig")
    mock_session.rollback = AsyncMock()
    mock_session.expunge_all = MagicMock()
    
    # Mock fetch failure after rollback (line 260-262)
    mock_session.execute.side_effect = Exception("Database connection lost")
    
    # Should re-raise the fetch exception
    with pytest.raises(Exception, match="Database connection lost"):
        await get_or_create_user(mock_session, mock_telegram_user)

@pytest.mark.asyncio
async def test_render_step_idempotent_edit_failure():
    """Test message edit failure in render_step_idempotent - lines 302-304"""
    from handlers.onboarding_router import render_step_idempotent
    
    mock_update = MagicMock()
    mock_update.effective_message = MagicMock()
    mock_update.effective_message.reply_text = AsyncMock()
    
    with patch('handlers.onboarding_router._should_suppress_duplicate', return_value=(True, 12345)), \
         patch('handlers.onboarding_router.safe_edit_message_text', side_effect=Exception("Edit failed")), \
         patch('handlers.onboarding_router.logger') as mock_logger:
        
        await render_step_idempotent(mock_update, "capture_email", 123, "test@example.com")
        
        # Should log debug message when edit fails (line 303)
        mock_logger.debug.assert_called_once()
        assert "Could not edit existing message" in str(mock_logger.debug.call_args)

@pytest.mark.asyncio
async def test_transition_general_exception():
    """Test general exception handling in transition - lines 352-354"""
    from handlers.onboarding_router import transition
    
    with patch('handlers.onboarding_router.OnboardingService.set_email', side_effect=Exception("Service unavailable")):
        result = await transition(123, "set_email", "test@example.com")
        
        # Should catch exception and return error (lines 352-354)
        assert result["success"] is False
        assert "Service unavailable" in result["error"]

@pytest.mark.asyncio
async def test_invalidate_user_cache_async_exception():
    """Test cache invalidation exception handling - lines 363-364"""
    from handlers.onboarding_router import invalidate_user_cache_async
    
    with patch('handlers.onboarding_router.run_io_task', side_effect=Exception("Cache server down")), \
         patch('handlers.onboarding_router.logger') as mock_logger:
        
        # Should not raise exception, only log warning (lines 363-364)
        await invalidate_user_cache_async("123")
        
        mock_logger.warning.assert_called_once()
        assert "Cache invalidation failed" in str(mock_logger.warning.call_args)

@pytest.mark.asyncio
async def test_onboarding_router_general_exception():
    """Test general exception handling in onboarding_router - lines 459-461"""
    from handlers.onboarding_router import onboarding_router
    
    mock_update = MagicMock()
    mock_update.effective_user.id = 123
    mock_context = MagicMock()
    
    with patch('handlers.onboarding_router.get_or_create_user', side_effect=Exception("Database error")), \
         patch('handlers.onboarding_router._send_error') as mock_send_error:
        
        await onboarding_router(mock_update, mock_context)
        
        # Should call _send_error with system_error (line 461)
        mock_send_error.assert_called_once_with(mock_update, "system_error")

@pytest.mark.asyncio 
async def test_handle_email_input_exception():
    """Test exception handling in _handle_email_input - lines 660-662"""
    from handlers.onboarding_router import _handle_email_input
    
    mock_update = MagicMock()
    mock_update.message.reply_text = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 123
    
    with patch('handlers.onboarding_router.transition', side_effect=Exception("Service down")):
        await _handle_email_input(mock_update, mock_user, "test@example.com")
        
        # Should reply with error message (lines 660-662)
        mock_update.message.reply_text.assert_called_once()
        call_args = str(mock_update.message.reply_text.call_args)
        assert "temporarily unavailable" in call_args or "try again" in call_args

@pytest.mark.asyncio
async def test_handle_otp_input_exception():
    """Test exception handling in _handle_otp_input - lines 774-776"""
    from handlers.onboarding_router import _handle_otp_input
    
    mock_update = MagicMock()
    mock_update.message.reply_text = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 123
    
    with patch('handlers.onboarding_router.transition', side_effect=Exception("OTP service error")):
        await _handle_otp_input(mock_update, mock_user, "123456")
        
        # Should reply with error message (lines 774-776)
        mock_update.message.reply_text.assert_called_once()
        call_args = str(mock_update.message.reply_text.call_args)
        assert "temporarily unavailable" in call_args or "try again" in call_args

@pytest.mark.asyncio
async def test_callback_edit_message_exception():
    """Test callback message edit exception - lines 432-434"""
    from handlers.onboarding_router import onboarding_router
    
    mock_update = MagicMock()
    mock_update.effective_user.id = 123
    mock_update.message.reply_text = AsyncMock()
    mock_context = MagicMock()
    
    # Mock user with existing onboarding
    mock_user = MagicMock()
    mock_user.id = 123
    mock_user.current_onboarding_step = "capture_email"
    
    with patch('handlers.onboarding_router.get_or_create_user', return_value=(mock_user, False)), \
         patch('handlers.onboarding_router._should_suppress_duplicate', return_value=(True, 12345)), \
         patch('handlers.onboarding_router.safe_edit_message_text', side_effect=Exception("Edit failed")):
        
        # Should handle edit exception gracefully (lines 432-434)
        await onboarding_router(mock_update, mock_context)
        
        # Should send gentle fallback message
        assert mock_update.message.reply_text.called

def test_non_async_utility_functions_coverage():
    """Test non-async utility functions for additional coverage"""
    from handlers.onboarding_router import OnboardingText
    
    # Test error message access
    assert OnboardingText.ERROR_MESSAGES["invalid_email"] is not None
    assert OnboardingText.ERROR_MESSAGES["email_taken"] is not None
    assert OnboardingText.ERROR_MESSAGES["otp_invalid"] is not None
    assert OnboardingText.ERROR_MESSAGES["system_error"] is not None
    
    # Test progress indicators
    assert OnboardingText.PROGRESS_INDICATORS["capture_email"] is not None
    assert OnboardingText.PROGRESS_INDICATORS["verify_otp"] is not None
    assert OnboardingText.PROGRESS_INDICATORS["accept_tos"] is not None
    
    # Test progress bars
    assert OnboardingText.PROGRESS_BARS["capture_email"] is not None
    assert OnboardingText.PROGRESS_BARS["verify_otp"] is not None
    assert OnboardingText.PROGRESS_BARS["accept_tos"] is not None

@pytest.mark.asyncio
async def test_render_steps_for_all_onboarding_steps():
    """Test render_step for all onboarding step types"""
    from handlers.onboarding_router import render_step
    from models import OnboardingStep
    
    mock_update = MagicMock()
    
    # Test all step types to improve coverage
    with patch('handlers.onboarding_router._render_email_step') as mock_email, \
         patch('handlers.onboarding_router._render_otp_step') as mock_otp, \
         patch('handlers.onboarding_router._render_terms_step') as mock_terms, \
         patch('handlers.onboarding_router._render_completion_step') as mock_completion:
        
        # Test email step
        await render_step(mock_update, OnboardingStep.CAPTURE_EMAIL.value)
        mock_email.assert_called_once()
        
        # Test OTP step
        await render_step(mock_update, OnboardingStep.VERIFY_OTP.value, email="test@example.com")
        mock_otp.assert_called_once()
        
        # Test terms step
        await render_step(mock_update, OnboardingStep.ACCEPT_TOS.value)
        mock_terms.assert_called_once()
        
        # Test completion step
        await render_step(mock_update, OnboardingStep.DONE.value, email="test@example.com")
        mock_completion.assert_called_once()

if __name__ == "__main__":
    # Run tests directly
    import subprocess
    result = subprocess.run([
        "python", "-m", "pytest", __file__, 
        "--cov=handlers.onboarding_router", 
        "--cov-report=term", 
        "--cov-report=html:htmlcov_exception",
        "-v"
    ], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print(f"Exit code: {result.returncode}")