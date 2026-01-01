"""
Comprehensive Callback Handler Coverage Tests for Onboarding Router

Targets the remaining uncovered callback handlers, user interactions, and navigation flows.
Current progress: 29% -> Goal: 95%+ coverage

Focus areas:
- All callback handlers (start, resend, change email, terms accept/decline, cancel, help)
- Message handlers and text input processing
- Render functions for all onboarding steps
- Navigation flows and user journeys
- Validation logic and error responses
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

# Direct imports for unit testing
import sys
sys.path.append('.')

@pytest.mark.asyncio
async def test_all_callback_handlers():
    """Test all callback handlers comprehensively"""
    from handlers.onboarding_router import handle_callback_query, OnboardingCallbacks
    
    mock_update = MagicMock()
    mock_update.callback_query.data = OnboardingCallbacks.START
    mock_update.callback_query.from_user.id = 123
    mock_update.callback_query.answer = AsyncMock()
    mock_context = MagicMock()
    
    # Test START callback
    with patch('handlers.onboarding_router.onboarding_router') as mock_router:
        await handle_callback_query(mock_update, mock_context)
        mock_router.assert_called_once()
    
    # Test RESEND_OTP callback
    mock_update.callback_query.data = OnboardingCallbacks.RESEND_OTP
    with patch('handlers.onboarding_router.get_or_create_user', return_value=(MagicMock(id=123), False)), \
         patch('handlers.onboarding_router.transition') as mock_transition:
        mock_transition.return_value = {"success": True}
        await handle_callback_query(mock_update, mock_context)
        mock_transition.assert_called_with(123, "resend_otp")
    
    # Test CHANGE_EMAIL callback
    mock_update.callback_query.data = OnboardingCallbacks.CHANGE_EMAIL
    with patch('handlers.onboarding_router.get_or_create_user', return_value=(MagicMock(id=123), False)), \
         patch('handlers.onboarding_router.transition') as mock_transition:
        mock_transition.return_value = {"success": True, "current_step": "capture_email"}
        await handle_callback_query(mock_update, mock_context)
        mock_transition.assert_called_with(123, "reset_email")
    
    # Test TOS_ACCEPT callback
    mock_update.callback_query.data = OnboardingCallbacks.TOS_ACCEPT
    with patch('handlers.onboarding_router.get_or_create_user', return_value=(MagicMock(id=123), False)), \
         patch('handlers.onboarding_router.transition') as mock_transition:
        mock_transition.return_value = {"success": True, "current_step": "done"}
        await handle_callback_query(mock_update, mock_context)
        mock_transition.assert_called_with(123, "accept_terms")
    
    # Test TOS_DECLINE callback
    mock_update.callback_query.data = OnboardingCallbacks.TOS_DECLINE
    with patch('handlers.onboarding_router.safe_edit_message_text') as mock_edit:
        await handle_callback_query(mock_update, mock_context)
        mock_edit.assert_called_once()
    
    # Test CANCEL callback
    mock_update.callback_query.data = OnboardingCallbacks.CANCEL
    with patch('handlers.onboarding_router.safe_edit_message_text') as mock_edit:
        await handle_callback_query(mock_update, mock_context)
        mock_edit.assert_called_once()

@pytest.mark.asyncio
async def test_help_callbacks():
    """Test all help callback handlers"""
    from handlers.onboarding_router import handle_callback_query, OnboardingCallbacks
    
    mock_update = MagicMock()
    mock_update.callback_query.from_user.id = 123
    mock_update.callback_query.answer = AsyncMock()
    mock_context = MagicMock()
    
    # Test HELP_EMAIL callback
    mock_update.callback_query.data = OnboardingCallbacks.HELP_EMAIL
    with patch('handlers.onboarding_router.safe_answer_callback_query') as mock_answer:
        await handle_callback_query(mock_update, mock_context)
        mock_answer.assert_called_once()
        # Verify help text contains expected content
        call_args = str(mock_answer.call_args)
        assert "email" in call_args.lower()
    
    # Test HELP_OTP callback
    mock_update.callback_query.data = OnboardingCallbacks.HELP_OTP
    with patch('handlers.onboarding_router.safe_answer_callback_query') as mock_answer:
        await handle_callback_query(mock_update, mock_context)
        mock_answer.assert_called_once()
        call_args = str(mock_answer.call_args)
        assert "code" in call_args.lower() or "otp" in call_args.lower()
    
    # Test HELP_TERMS callback
    mock_update.callback_query.data = OnboardingCallbacks.HELP_TERMS
    with patch('handlers.onboarding_router.safe_answer_callback_query') as mock_answer:
        await handle_callback_query(mock_update, mock_context)
        mock_answer.assert_called_once()
        call_args = str(mock_answer.call_args)
        assert "terms" in call_args.lower() or "service" in call_args.lower()

@pytest.mark.asyncio
async def test_message_handlers():
    """Test all message handlers comprehensively"""
    from handlers.onboarding_router import handle_message
    
    mock_update = MagicMock()
    mock_update.message.from_user.id = 123
    mock_update.message.text = "test@example.com"
    mock_context = MagicMock()
    
    mock_user = MagicMock()
    mock_user.id = 123
    mock_user.current_onboarding_step = "capture_email"
    
    # Test email input handling
    with patch('handlers.onboarding_router.get_or_create_user', return_value=(mock_user, False)), \
         patch('handlers.onboarding_router._handle_email_input') as mock_email_handler:
        await handle_message(mock_update, mock_context)
        mock_email_handler.assert_called_once()
    
    # Test OTP input handling
    mock_user.current_onboarding_step = "verify_otp"
    mock_update.message.text = "123456"
    with patch('handlers.onboarding_router.get_or_create_user', return_value=(mock_user, False)), \
         patch('handlers.onboarding_router._handle_otp_input') as mock_otp_handler:
        await handle_message(mock_update, mock_context)
        mock_otp_handler.assert_called_once()
    
    # Test completed onboarding
    mock_user.current_onboarding_step = "done"
    mock_update.message.reply_text = AsyncMock()
    with patch('handlers.onboarding_router.get_or_create_user', return_value=(mock_user, False)):
        await handle_message(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()

@pytest.mark.asyncio
async def test_render_functions_comprehensive():
    """Test all render functions for comprehensive coverage"""
    
    # Test _render_email_step
    from handlers.onboarding_router import _render_email_step
    mock_update = MagicMock()
    mock_update.effective_message.edit_text = AsyncMock()
    mock_update.effective_message.reply_text = AsyncMock()
    
    await _render_email_step(mock_update)
    # Should call either edit_text or reply_text
    assert mock_update.effective_message.edit_text.called or mock_update.effective_message.reply_text.called
    
    # Test _render_email_step with error
    await _render_email_step(mock_update, error="invalid_email")
    
    # Test _render_otp_step
    from handlers.onboarding_router import _render_otp_step
    await _render_otp_step(mock_update, email="test@example.com")
    
    # Test _render_otp_step with attempts
    await _render_otp_step(mock_update, email="test@example.com", remaining_attempts=3, max_attempts=5)
    
    # Test _render_otp_step with error
    await _render_otp_step(mock_update, email="test@example.com", error="otp_invalid")
    
    # Test _render_terms_step
    from handlers.onboarding_router import _render_terms_step
    await _render_terms_step(mock_update)
    
    # Test _render_completion_step
    from handlers.onboarding_router import _render_completion_step
    await _render_completion_step(mock_update, email="test@example.com")

@pytest.mark.asyncio
async def test_send_error_function():
    """Test _send_error function for all error types"""
    from handlers.onboarding_router import _send_error
    
    mock_update = MagicMock()
    mock_update.effective_message.reply_text = AsyncMock()
    
    # Test all error types
    error_types = ["invalid_email", "email_taken", "otp_invalid", "system_error"]
    
    for error_type in error_types:
        await _send_error(mock_update, error_type)
        mock_update.effective_message.reply_text.assert_called()

@pytest.mark.asyncio
async def test_validation_functions():
    """Test validation functions and edge cases"""
    from handlers.onboarding_router import _handle_email_input, _handle_otp_input
    
    mock_update = MagicMock()
    mock_update.message.reply_text = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 123
    
    # Test valid email
    with patch('handlers.onboarding_router.transition') as mock_transition:
        mock_transition.return_value = {"success": True, "current_step": "verify_otp"}
        await _handle_email_input(mock_update, mock_user, "test@example.com")
        mock_transition.assert_called_once()
    
    # Test invalid email
    with patch('handlers.onboarding_router.validate_email', return_value=False):
        await _handle_email_input(mock_update, mock_user, "invalid-email")
        mock_update.message.reply_text.assert_called()
    
    # Test valid OTP
    with patch('handlers.onboarding_router.transition') as mock_transition:
        mock_transition.return_value = {"success": True, "current_step": "accept_tos"}
        await _handle_otp_input(mock_update, mock_user, "123456")
        mock_transition.assert_called_once()
    
    # Test invalid OTP format
    await _handle_otp_input(mock_update, mock_user, "12345")  # Too short
    mock_update.message.reply_text.assert_called()
    
    await _handle_otp_input(mock_update, mock_user, "1234567")  # Too long
    mock_update.message.reply_text.assert_called()
    
    await _handle_otp_input(mock_update, mock_user, "abcdef")  # Non-numeric
    mock_update.message.reply_text.assert_called()

@pytest.mark.asyncio
async def test_step_transitions_comprehensive():
    """Test all step transition scenarios"""
    from handlers.onboarding_router import transition
    
    # Test successful email transition
    with patch('handlers.onboarding_router.OnboardingService.set_email') as mock_service:
        mock_service.return_value = {"success": True, "current_step": "verify_otp"}
        result = await transition(123, "set_email", "test@example.com")
        assert result["success"] is True
        assert result["current_step"] == "verify_otp"
    
    # Test failed email transition
    with patch('handlers.onboarding_router.OnboardingService.set_email') as mock_service:
        mock_service.return_value = {"success": False, "error": "Email already taken"}
        result = await transition(123, "set_email", "taken@example.com")
        assert result["success"] is False
        assert "already taken" in result["error"]
    
    # Test successful OTP transition
    with patch('handlers.onboarding_router.OnboardingService.verify_otp') as mock_service:
        mock_service.return_value = {"success": True, "current_step": "accept_tos"}
        result = await transition(123, "verify_otp", "123456")
        assert result["success"] is True
        assert result["current_step"] == "accept_tos"
    
    # Test failed OTP transition
    with patch('handlers.onboarding_router.OnboardingService.verify_otp') as mock_service:
        mock_service.return_value = {"success": False, "error": "Invalid code"}
        result = await transition(123, "verify_otp", "000000")
        assert result["success"] is False
        assert "Invalid" in result["error"]
    
    # Test successful terms acceptance
    with patch('handlers.onboarding_router.OnboardingService.accept_tos') as mock_service:
        mock_service.return_value = {"success": True, "current_step": "done"}
        result = await transition(123, "accept_terms")
        assert result["success"] is True
        assert result["current_step"] == "done"

def test_text_constants_comprehensive():
    """Test all text constants and templates"""
    from handlers.onboarding_router import OnboardingText
    
    # Test all message templates
    templates = [
        OnboardingText.WELCOME,
        OnboardingText.EMAIL_PROMPT,
        OnboardingText.OTP_PROMPT,
        OnboardingText.TERMS_PROMPT,
        OnboardingText.COMPLETION
    ]
    
    for template in templates:
        assert isinstance(template, str)
        assert len(template) > 0
    
    # Test all error messages
    for error_key, error_message in OnboardingText.ERROR_MESSAGES.items():
        assert isinstance(error_message, str)
        assert len(error_message) > 0
    
    # Test all progress indicators
    for step_key, indicator in OnboardingText.PROGRESS_INDICATORS.items():
        assert isinstance(indicator, str)
        assert "Step" in indicator
    
    # Test all progress bars
    for step_key, bar in OnboardingText.PROGRESS_BARS.items():
        assert isinstance(bar, str)
        assert "🟦" in bar or "⬜" in bar

@pytest.mark.asyncio
async def test_cache_operations():
    """Test cache operations and invalidation"""
    from handlers.onboarding_router import invalidate_user_cache_async, _user_lookup_cache
    
    # Test cache invalidation with success
    with patch('handlers.onboarding_router.run_io_task') as mock_io:
        await invalidate_user_cache_async("123")
        mock_io.assert_called_once()
    
    # Test cache get/set operations
    cache_key = "test_user_123"
    test_data = {"id": 123, "step": "capture_email"}
    
    _user_lookup_cache.set(cache_key, test_data)
    retrieved_data = _user_lookup_cache.get(cache_key)
    assert retrieved_data == test_data
    
    _user_lookup_cache.delete(cache_key)
    assert _user_lookup_cache.get(cache_key) is None

@pytest.mark.asyncio
async def test_user_stats_rendering():
    """Test user stats rendering in completion step"""
    from handlers.onboarding_router import _render_completion_step
    
    mock_update = MagicMock()
    mock_update.effective_message.edit_text = AsyncMock()
    mock_update.effective_message.reply_text = AsyncMock()
    
    # Mock session and stats query
    with patch('handlers.onboarding_router.managed_session') as mock_session_manager:
        mock_session = AsyncMock()
        mock_session_manager.return_value.__aenter__.return_value = mock_session
        
        # Mock stats results
        mock_result = MagicMock()
        mock_result.scalar.return_value = 150.50  # Mock balance
        mock_session.execute.return_value = mock_result
        
        await _render_completion_step(mock_update, email="test@example.com")
        
        # Should execute database queries for stats
        assert mock_session.execute.call_count >= 1

if __name__ == "__main__":
    # Run tests directly
    import subprocess
    result = subprocess.run([
        "python", "-m", "pytest", __file__, 
        "--cov=handlers.onboarding_router", 
        "--cov-report=term", 
        "--cov-report=html:htmlcov_callback",
        "-v"
    ], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print(f"Exit code: {result.returncode}")