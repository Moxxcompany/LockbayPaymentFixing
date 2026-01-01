"""
Onboarding Router Coverage Boost to 70%+ - Targeted High-ROI Tests

This test suite focuses on the 5 architect-identified high-ROI areas to boost 
coverage from current 24% to 70%+ for handlers/onboarding_router.py

Target Areas:
1. EMAIL FLOW COVERAGE (+8-12% expected)
2. OTP HANDLING COVERAGE (+6-10% expected) 
3. TERMS OF SERVICE COVERAGE (+4-8% expected)
4. NAVIGATION & CONTROL FLOW COVERAGE (+6-10% expected)
5. INPUT METHOD COVERAGE (+4-8% expected)

Current: 24% (125/516 statements) -> Goal: 70%+ (361/516 statements)
Need: ~236 additional statements covered
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, call
from datetime import datetime, timedelta
from typing import Optional

# Direct imports for testing
import sys
sys.path.append('.')

from models import User, OnboardingStep
from telegram import Update, CallbackQuery, Message, Chat
from telegram.ext import ContextTypes

# ============================================================================
# 1. EMAIL FLOW COVERAGE TESTS (+8-12% expected)
# ============================================================================

class TestEmailFlowCoverage:
    """Test all email flow paths and validation scenarios"""
    
    @pytest.mark.asyncio
    async def test_email_input_invalid_formats(self):
        """Test _handle_email_input with various invalid email formats"""
        from handlers.onboarding_router import _handle_email_input
        
        mock_update = MagicMock()
        mock_message = MagicMock()
        mock_message.reply_text = AsyncMock()
        mock_update.message = mock_message
        mock_user = MagicMock(id=123)
        mock_session = MagicMock()
        
        invalid_emails = [
            "",  # Empty
            "   ",  # Whitespace only  
            "invalid",  # No @ or domain
            "@domain.com",  # No username
            "user@",  # No domain
            "user.domain.com",  # Missing @
            "user@domain",  # No TLD
            "user space@domain.com",  # Space in username
            "user@domain .com",  # Space in domain
            "a" * 255 + "@domain.com",  # Too long
            "user@@domain.com",  # Double @
            "user@domain..com",  # Double dots
            "user@.domain.com",  # Leading dot in domain
        ]
        
        for email in invalid_emails:
            mock_message.reply_text.reset_mock()
            
            with patch('handlers.onboarding_router.validate_email', return_value=False):
                await _handle_email_input(mock_update, None, mock_user, email, mock_session)
            
            mock_message.reply_text.assert_called()
            args, kwargs = mock_message.reply_text.call_args
            assert "Invalid email format" in args[0]

    @pytest.mark.asyncio
    async def test_email_input_digit_confusion(self):
        """Test _handle_email_input when user enters 6-digit code instead of email"""
        from handlers.onboarding_router import _handle_email_input
        
        mock_update = MagicMock()
        mock_message = MagicMock()
        mock_message.reply_text = AsyncMock()
        mock_update.message = mock_message
        mock_user = MagicMock(id=123)
        mock_session = MagicMock()
        
        # Test 6-digit input (likely OTP confusion)
        await _handle_email_input(mock_update, None, mock_user, "123456", mock_session)
        
        mock_message.reply_text.assert_called()
        args, kwargs = mock_message.reply_text.call_args
        assert "verification code" in args[0]
        assert "email address" in args[0]

    @pytest.mark.asyncio
    async def test_email_input_valid_formats(self):
        """Test _handle_email_input with valid email formats"""
        from handlers.onboarding_router import _handle_email_input
        
        mock_update = MagicMock()
        mock_message = MagicMock()
        mock_message.reply_text = AsyncMock()
        mock_update.message = mock_message
        mock_user = MagicMock(id=123)
        mock_session = MagicMock()
        
        valid_emails = [
            "user@domain.com",
            "user.name@domain.com", 
            "user+tag@domain.com",
            "user123@domain123.com",
            "user@subdomain.domain.com",
            "a@b.co",  # Minimal valid email
        ]
        
        for email in valid_emails:
            mock_message.reply_text.reset_mock()
            
            with patch('handlers.onboarding_router.validate_email', return_value=True), \
                 patch('handlers.onboarding_router.transition') as mock_transition, \
                 patch('handlers.onboarding_router.render_step') as mock_render, \
                 patch('handlers.onboarding_router.safe_edit_message_text') as mock_edit:
                
                mock_transition.return_value = {"success": True, "current_step": "verify_otp"}
                
                await _handle_email_input(mock_update, None, mock_user, email, mock_session)
                
                mock_transition.assert_called_with(123, "set_email", email, session=mock_session)
                mock_render.assert_called()

    @pytest.mark.asyncio
    async def test_email_input_already_registered(self):
        """Test _handle_email_input when email is already registered"""
        from handlers.onboarding_router import _handle_email_input
        
        mock_update = MagicMock()
        mock_message = MagicMock()
        mock_message.reply_text = AsyncMock()
        mock_update.message = mock_message
        mock_user = MagicMock(id=123)
        mock_session = MagicMock()
        
        with patch('handlers.onboarding_router.validate_email', return_value=True), \
             patch('handlers.onboarding_router.transition') as mock_transition, \
             patch('handlers.onboarding_router.safe_edit_message_text'):
            
            mock_transition.return_value = {
                "success": False, 
                "error": "Email already registered with another account"
            }
            
            await _handle_email_input(mock_update, None, mock_user, "test@example.com", mock_session)
            
            mock_message.reply_text.assert_called()
            args, kwargs = mock_message.reply_text.call_args
            assert "already registered" in args[0]

    @pytest.mark.asyncio
    async def test_email_input_rate_limit(self):
        """Test _handle_email_input with rate limiting error"""
        from handlers.onboarding_router import _handle_email_input
        
        mock_update = MagicMock()
        mock_message = MagicMock()
        mock_message.reply_text = AsyncMock()
        mock_update.message = mock_message
        mock_user = MagicMock(id=123)
        mock_session = MagicMock()
        
        with patch('handlers.onboarding_router.validate_email', return_value=True), \
             patch('handlers.onboarding_router.transition') as mock_transition, \
             patch('handlers.onboarding_router.safe_edit_message_text'):
            
            mock_transition.return_value = {
                "success": False,
                "error": "Rate limit exceeded"
            }
            
            await _handle_email_input(mock_update, None, mock_user, "test@example.com", mock_session)
            
            mock_message.reply_text.assert_called()
            args, kwargs = mock_message.reply_text.call_args
            assert "too many attempts" in args[0] or "wait" in args[0]


# ============================================================================
# 2. OTP HANDLING COVERAGE TESTS (+6-10% expected)
# ============================================================================

class TestOTPHandlingCoverage:
    """Test all OTP handling paths and validation scenarios"""
    
    @pytest.mark.asyncio
    async def test_otp_input_valid_formats(self):
        """Test _handle_otp_input with valid OTP formats"""
        from handlers.onboarding_router import _handle_otp_input
        
        mock_update = MagicMock()
        mock_message = MagicMock()
        mock_message.reply_text = AsyncMock()
        mock_update.message = mock_message
        mock_user = MagicMock(id=123)
        mock_session = MagicMock()
        
        valid_otps = ["123456", "000000", "999999", " 123456 "]  # Including whitespace
        
        for otp in valid_otps:
            mock_message.reply_text.reset_mock()
            
            with patch('handlers.onboarding_router.transition') as mock_transition, \
                 patch('handlers.onboarding_router.render_step') as mock_render:
                
                mock_transition.return_value = {"success": True, "current_step": "accept_tos"}
                
                await _handle_otp_input(mock_update, None, mock_user, otp, mock_session)
                
                mock_transition.assert_called_with(123, "verify_otp", otp.strip(), session=mock_session)
                mock_render.assert_called()

    @pytest.mark.asyncio  
    async def test_otp_input_invalid_formats(self):
        """Test _handle_otp_input with invalid OTP formats"""
        from handlers.onboarding_router import _handle_otp_input
        
        mock_update = MagicMock()
        mock_message = MagicMock() 
        mock_message.reply_text = AsyncMock()
        mock_update.message = mock_message
        mock_user = MagicMock(id=123)
        mock_session = MagicMock()
        
        invalid_otps = [
            "",  # Empty
            "12345",  # Too short
            "1234567",  # Too long
            "12345a",  # Contains letters
            "12 34 56",  # Contains spaces
            "123-456",  # Contains dashes
            "abcdef",  # All letters
        ]
        
        for otp in invalid_otps:
            mock_message.reply_text.reset_mock()
            
            await _handle_otp_input(mock_update, None, mock_user, otp, mock_session)
            
            mock_message.reply_text.assert_called()
            args, kwargs = mock_message.reply_text.call_args
            assert ("6-digit" in args[0] or "Invalid" in args[0] or "format" in args[0])

    @pytest.mark.asyncio
    async def test_otp_input_incorrect_code(self):
        """Test _handle_otp_input with incorrect OTP code"""
        from handlers.onboarding_router import _handle_otp_input
        
        mock_update = MagicMock()
        mock_message = MagicMock()
        mock_message.reply_text = AsyncMock()
        mock_update.message = mock_message
        mock_user = MagicMock(id=123)
        mock_session = MagicMock()
        
        with patch('handlers.onboarding_router.transition') as mock_transition:
            mock_transition.return_value = {
                "success": False,
                "error": "Invalid OTP code"
            }
            
            await _handle_otp_input(mock_update, None, mock_user, "123456", mock_session)
            
            mock_message.reply_text.assert_called()
            args, kwargs = mock_message.reply_text.call_args
            assert "Wrong code" in args[0] or "Invalid" in args[0]

    @pytest.mark.asyncio
    async def test_otp_input_expired_code(self):
        """Test _handle_otp_input with expired OTP code"""
        from handlers.onboarding_router import _handle_otp_input
        
        mock_update = MagicMock()
        mock_message = MagicMock()
        mock_message.reply_text = AsyncMock()
        mock_update.message = mock_message
        mock_user = MagicMock(id=123)
        mock_session = MagicMock()
        
        with patch('handlers.onboarding_router.transition') as mock_transition:
            mock_transition.return_value = {
                "success": False,
                "error": "OTP expired"
            }
            
            await _handle_otp_input(mock_update, None, mock_user, "123456", mock_session)
            
            mock_message.reply_text.assert_called()
            args, kwargs = mock_message.reply_text.call_args
            assert "expired" in args[0] or "Expired" in args[0]

    @pytest.mark.asyncio
    async def test_handle_resend_otp(self):
        """Test _handle_resend_otp functionality"""
        from handlers.onboarding_router import _handle_resend_otp
        
        mock_update = MagicMock()
        mock_query = MagicMock()
        mock_query.edit_message_text = AsyncMock()
        mock_update.callback_query = mock_query
        mock_user = MagicMock(id=123)
        mock_session = MagicMock()
        
        with patch('handlers.onboarding_router.transition') as mock_transition, \
             patch('handlers.onboarding_router.render_step') as mock_render:
            
            mock_transition.return_value = {"success": True, "current_step": "verify_otp"}
            
            await _handle_resend_otp(mock_update, None, mock_user, mock_session)
            
            mock_transition.assert_called_with(123, "resend_otp", None, session=mock_session)
            mock_render.assert_called()


# ============================================================================
# 3. TERMS OF SERVICE COVERAGE TESTS (+4-8% expected)
# ============================================================================

class TestTermsOfServiceCoverage:
    """Test all Terms of Service acceptance/decline scenarios"""
    
    @pytest.mark.asyncio
    async def test_handle_accept_terms_success(self):
        """Test _handle_accept_terms with successful acceptance"""
        from handlers.onboarding_router import _handle_accept_terms
        
        mock_update = MagicMock()
        mock_query = MagicMock()
        mock_query.edit_message_text = AsyncMock()
        mock_update.callback_query = mock_query
        mock_user = MagicMock(id=123)
        mock_session = MagicMock()
        
        with patch('handlers.onboarding_router.transition') as mock_transition, \
             patch('handlers.onboarding_router.render_step') as mock_render, \
             patch('handlers.onboarding_router.run_background_task') as mock_background:
            
            mock_transition.return_value = {"success": True, "current_step": "done"}
            
            await _handle_accept_terms(mock_update, None, mock_user, mock_session)
            
            mock_transition.assert_called_with(123, "accept_terms", True, session=mock_session)
            mock_render.assert_called()

    @pytest.mark.asyncio
    async def test_handle_accept_terms_failure(self):
        """Test _handle_accept_terms with acceptance failure"""
        from handlers.onboarding_router import _handle_accept_terms
        
        mock_update = MagicMock()
        mock_query = MagicMock()
        mock_query.edit_message_text = AsyncMock()
        mock_update.callback_query = mock_query
        mock_user = MagicMock(id=123)
        mock_session = MagicMock()
        
        with patch('handlers.onboarding_router.transition') as mock_transition, \
             patch('handlers.onboarding_router._send_error') as mock_error:
            
            mock_transition.return_value = {"success": False, "error": "Terms acceptance failed"}
            
            await _handle_accept_terms(mock_update, None, mock_user, mock_session)
            
            mock_error.assert_called_with(mock_update, "system_error")

    @pytest.mark.asyncio 
    async def test_handle_decline_terms(self):
        """Test _handle_decline_terms functionality"""
        from handlers.onboarding_router import _handle_decline_terms
        
        mock_update = MagicMock()
        mock_query = MagicMock()
        mock_query.edit_message_text = AsyncMock()
        mock_update.callback_query = mock_query
        mock_user = MagicMock(id=123)
        
        await _handle_decline_terms(mock_update, None, mock_user)
        
        mock_query.edit_message_text.assert_called()
        args, kwargs = mock_query.edit_message_text.call_args
        assert "cannot proceed" in args[0] or "declined" in args[0]


# ============================================================================
# 4. NAVIGATION & CONTROL FLOW COVERAGE TESTS (+6-10% expected)
# ============================================================================

class TestNavigationControlFlowCoverage:
    """Test all navigation and control flow scenarios"""
    
    @pytest.mark.asyncio
    async def test_handle_cancel(self):
        """Test _handle_cancel functionality"""
        from handlers.onboarding_router import _handle_cancel
        
        mock_update = MagicMock()
        mock_query = MagicMock()
        mock_query.edit_message_text = AsyncMock()
        mock_update.callback_query = mock_query
        mock_user = MagicMock(id=123)
        
        with patch('handlers.onboarding_router.OnboardingService.cancel') as mock_cancel:
            mock_cancel.return_value = {"success": True}
            
            await _handle_cancel(mock_update, None, mock_user)
            
            mock_cancel.assert_called_with(123)
            mock_query.edit_message_text.assert_called()
            args, kwargs = mock_query.edit_message_text.call_args
            assert "cancelled" in args[0] or "stopped" in args[0]

    @pytest.mark.asyncio
    async def test_handle_change_email(self):
        """Test _handle_change_email functionality"""
        from handlers.onboarding_router import _handle_change_email
        
        mock_update = MagicMock()
        mock_query = MagicMock()
        mock_query.edit_message_text = AsyncMock()
        mock_update.callback_query = mock_query
        mock_user = MagicMock(id=123)
        mock_session = MagicMock()
        
        with patch('handlers.onboarding_router.OnboardingService.reset_to_email') as mock_reset, \
             patch('handlers.onboarding_router.render_step') as mock_render:
            
            mock_reset.return_value = {"success": True, "current_step": "capture_email"}
            
            await _handle_change_email(mock_update, None, mock_user, mock_session)
            
            mock_reset.assert_called_with(123, session=mock_session)
            mock_render.assert_called()

    @pytest.mark.asyncio
    async def test_show_help_email(self):
        """Test _show_help functionality for email help"""
        from handlers.onboarding_router import _show_help
        
        mock_update = MagicMock()
        mock_query = MagicMock()
        mock_query.edit_message_text = AsyncMock()
        mock_update.callback_query = mock_query
        
        await _show_help(mock_update, None, "email")
        
        mock_query.edit_message_text.assert_called()
        args, kwargs = mock_query.edit_message_text.call_args
        assert "email" in args[0].lower()

    @pytest.mark.asyncio
    async def test_show_help_otp(self):
        """Test _show_help functionality for OTP help"""
        from handlers.onboarding_router import _show_help
        
        mock_update = MagicMock()
        mock_query = MagicMock()
        mock_query.edit_message_text = AsyncMock()
        mock_update.callback_query = mock_query
        
        await _show_help(mock_update, None, "otp")
        
        mock_query.edit_message_text.assert_called()
        args, kwargs = mock_query.edit_message_text.call_args
        assert "code" in args[0] or "verification" in args[0]

    @pytest.mark.asyncio
    async def test_show_main_menu(self):
        """Test _show_main_menu functionality"""
        from handlers.onboarding_router import _show_main_menu
        
        mock_update = MagicMock()
        mock_query = MagicMock()
        mock_query.edit_message_text = AsyncMock()
        mock_update.callback_query = mock_query
        mock_user = MagicMock(id=123)
        
        with patch('handlers.onboarding_router.main_menu_keyboard') as mock_keyboard:
            mock_keyboard.return_value = MagicMock()
            
            await _show_main_menu(mock_update, None, mock_user)
            
            mock_query.edit_message_text.assert_called()
            mock_keyboard.assert_called()


# ============================================================================
# 5. INPUT METHOD COVERAGE TESTS (+4-8% expected)
# ============================================================================

class TestInputMethodCoverage:
    """Test all input method scenarios - callbacks vs text"""
    
    @pytest.mark.asyncio
    async def test_handle_callback_routing(self):
        """Test _handle_callback with all callback types"""
        from handlers.onboarding_router import _handle_callback, OnboardingCallbacks
        
        mock_update = MagicMock()
        mock_query = MagicMock()
        mock_update.callback_query = mock_query
        mock_user = MagicMock(id=123)
        mock_session = MagicMock()
        
        # Test all callback routing
        callback_handlers = [
            (OnboardingCallbacks.START, '_handle_start'),
            (OnboardingCallbacks.RESEND_OTP, '_handle_resend_otp'),
            (OnboardingCallbacks.CHANGE_EMAIL, '_handle_change_email'),
            (OnboardingCallbacks.TOS_ACCEPT, '_handle_accept_terms'),
            (OnboardingCallbacks.TOS_DECLINE, '_handle_decline_terms'),
            (OnboardingCallbacks.CANCEL, '_handle_cancel'),
            (OnboardingCallbacks.HELP_EMAIL, '_show_help'),
            (OnboardingCallbacks.HELP_OTP, '_show_help'),
            (OnboardingCallbacks.HELP_TERMS, '_show_help'),
        ]
        
        for callback_data, handler_name in callback_handlers:
            mock_query.data = callback_data
            
            with patch(f'handlers.onboarding_router.{handler_name}') as mock_handler, \
                 patch('handlers.onboarding_router.safe_answer_callback_query') as mock_answer:
                
                await _handle_callback(mock_update, None, mock_user, mock_session)
                
                mock_answer.assert_called()
                mock_handler.assert_called()

    @pytest.mark.asyncio
    async def test_handle_callback_legacy_patterns(self):
        """Test _handle_callback with legacy callback patterns"""
        from handlers.onboarding_router import _handle_callback
        
        mock_update = MagicMock()
        mock_query = MagicMock()
        mock_update.callback_query = mock_query
        mock_user = MagicMock(id=123)
        mock_session = MagicMock()
        
        # Test legacy patterns
        legacy_callbacks = [
            "reject_terms_and_conditions",
            "accept_terms_and_conditions",
        ]
        
        for callback_data in legacy_callbacks:
            mock_query.data = callback_data
            
            with patch('handlers.onboarding_router._handle_decline_terms') as mock_decline, \
                 patch('handlers.onboarding_router._handle_accept_terms') as mock_accept, \
                 patch('handlers.onboarding_router.safe_answer_callback_query'):
                
                await _handle_callback(mock_update, None, mock_user, mock_session)
                
                if "reject" in callback_data:
                    mock_decline.assert_called()
                else:
                    mock_accept.assert_called()

    @pytest.mark.asyncio
    async def test_handle_text_input_routing(self):
        """Test _handle_text_input with different input scenarios"""
        from handlers.onboarding_router import _handle_text_input
        
        mock_update = MagicMock()
        mock_message = MagicMock()
        mock_update.message = mock_message
        mock_user = MagicMock(id=123)
        mock_session = MagicMock()
        
        # Test /start command routing
        mock_message.text = "/start"
        
        with patch('handlers.onboarding_router._handle_start') as mock_start:
            await _handle_text_input(mock_update, None, mock_user, mock_session)
            mock_start.assert_called()

    @pytest.mark.asyncio
    async def test_handle_text_input_step_routing(self):
        """Test _handle_text_input routing based on onboarding step"""
        from handlers.onboarding_router import _handle_text_input
        
        mock_update = MagicMock()
        mock_message = MagicMock()
        mock_message.text = "test@example.com"
        mock_update.message = mock_message
        mock_user = MagicMock(id=123, current_onboarding_step="capture_email")
        mock_session = MagicMock()
        
        # Test email step routing
        with patch('handlers.onboarding_router.OnboardingService.get_current_step') as mock_get_step, \
             patch('handlers.onboarding_router._handle_email_input') as mock_email:
            
            mock_get_step.return_value = "capture_email"
            
            await _handle_text_input(mock_update, None, mock_user, mock_session)
            
            mock_email.assert_called_with(mock_update, None, mock_user, "test@example.com", mock_session)

        # Test OTP step routing
        mock_message.text = "123456"
        with patch('handlers.onboarding_router.OnboardingService.get_current_step') as mock_get_step, \
             patch('handlers.onboarding_router._handle_otp_input') as mock_otp:
            
            mock_get_step.return_value = "verify_otp"
            
            await _handle_text_input(mock_update, None, mock_user, mock_session)
            
            mock_otp.assert_called_with(mock_update, None, mock_user, "123456", mock_session)


# ============================================================================
# ADDITIONAL COVERAGE BOOSTERS - Error Paths & Edge Cases
# ============================================================================

class TestAdditionalCoverageBoosts:
    """Additional tests to cover remaining gaps and error paths"""
    
    @pytest.mark.asyncio
    async def test_get_or_create_user_constraint_violation(self):
        """Test get_or_create_user with database constraint violations"""
        from handlers.onboarding_router import get_or_create_user
        from sqlalchemy.exc import IntegrityError
        
        mock_session = MagicMock()
        mock_telegram_user = MagicMock()
        mock_telegram_user.id = 123
        mock_telegram_user.username = "testuser"
        mock_telegram_user.first_name = "Test"
        mock_telegram_user.last_name = "User"
        
        # Mock constraint violation on user creation
        mock_session.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # Initial check - no user
            IntegrityError("", "", ""),  # Constraint violation on insert
            MagicMock(scalar_one_or_none=MagicMock(return_value=MagicMock(id=456))),  # Find existing after error
        ]
        
        with patch('handlers.onboarding_router.logger') as mock_logger:
            user, is_new = await get_or_create_user(mock_session, mock_telegram_user)
            
            assert user is not None
            assert is_new is False
            mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_onboarding_router_no_user(self):
        """Test onboarding_router when no user in update"""
        from handlers.onboarding_router import onboarding_router
        
        mock_update = MagicMock()
        mock_update.effective_user = None
        mock_context = MagicMock()
        
        # Should return early without error
        result = await onboarding_router(mock_update, mock_context)
        assert result is None

    @pytest.mark.asyncio 
    async def test_onboarding_router_duplicate_suppression(self):
        """Test onboarding_router duplicate suppression logic"""
        from handlers.onboarding_router import onboarding_router
        
        mock_update = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 123
        mock_update.effective_user = mock_user
        mock_context = MagicMock()
        
        with patch('handlers.onboarding_router._get_user_lock') as mock_lock, \
             patch('handlers.onboarding_router.get_or_create_user') as mock_get_user, \
             patch('handlers.onboarding_router.OnboardingService') as mock_service, \
             patch('handlers.onboarding_router._should_suppress_duplicate') as mock_suppress, \
             patch('handlers.onboarding_router.managed_session'):
            
            mock_lock.return_value.__aenter__ = AsyncMock()
            mock_lock.return_value.__aexit__ = AsyncMock()
            mock_get_user.return_value = (MagicMock(id=123, email_verified=False), False)
            mock_service.get_current_step.return_value = "capture_email"
            mock_service.get_session_info.return_value = {"email": "test@example.com"}
            mock_suppress.return_value = (True, 12345)  # Should suppress with message ID
            
            await onboarding_router(mock_update, mock_context)
            
            mock_suppress.assert_called()

    @pytest.mark.asyncio
    async def test_render_step_idempotent(self):
        """Test render_step_idempotent functionality"""
        from handlers.onboarding_router import render_step_idempotent
        
        mock_update = MagicMock()
        
        with patch('handlers.onboarding_router._should_suppress_duplicate') as mock_suppress, \
             patch('handlers.onboarding_router.render_step') as mock_render, \
             patch('handlers.onboarding_router._record_step_render') as mock_record:
            
            # Test non-duplicate case
            mock_suppress.return_value = (False, None)
            
            await render_step_idempotent(mock_update, "capture_email", 123, "test@example.com")
            
            mock_render.assert_called()
            mock_record.assert_called()

    @pytest.mark.asyncio
    async def test_transition_unknown_action(self):
        """Test transition function with unknown action"""
        from handlers.onboarding_router import transition
        
        result = await transition(123, "unknown_action", "data")
        
        assert result["success"] is False
        assert "Unknown action" in result["error"]

    @pytest.mark.asyncio
    async def test_send_error(self):
        """Test _send_error functionality"""
        from handlers.onboarding_router import _send_error, OnboardingText
        
        mock_update = MagicMock()
        mock_message = MagicMock()
        mock_message.reply_text = AsyncMock()
        mock_update.message = mock_message
        
        await _send_error(mock_update, "invalid_email")
        
        mock_message.reply_text.assert_called()
        args, kwargs = mock_message.call_args
        expected_error = OnboardingText.ERROR_MESSAGES["invalid_email"]
        # The error message should contain the expected error text
        assert any(expected_error in str(arg) for arg in args)

    @pytest.mark.asyncio
    async def test_send_error_with_custom_message(self):
        """Test _send_error with custom message"""
        from handlers.onboarding_router import _send_error
        
        mock_update = MagicMock()
        mock_message = MagicMock()
        mock_message.reply_text = AsyncMock()
        mock_update.message = mock_message
        
        await _send_error(mock_update, "system_error", "Custom error message")
        
        mock_message.reply_text.assert_called()
        args, kwargs = mock_message.reply_text.call_args
        assert "Custom error message" in args[0]


# ============================================================================
# MAIN ENTRY POINT TESTS
# ============================================================================

class TestMainEntryPoints:
    """Test main entry point functions for full coverage"""
    
    @pytest.mark.asyncio
    async def test_start_new_user_onboarding(self):
        """Test start_new_user_onboarding function"""
        from handlers.onboarding_router import start_new_user_onboarding
        
        mock_update = MagicMock()
        mock_context = MagicMock()
        
        with patch('handlers.onboarding_router.onboarding_router') as mock_router:
            await start_new_user_onboarding(mock_update, mock_context)
            mock_router.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_onboarding_start(self):
        """Test handle_onboarding_start entry point"""
        from handlers.onboarding_router import handle_onboarding_start
        
        mock_update = MagicMock()
        mock_context = MagicMock()
        
        with patch('handlers.onboarding_router.onboarding_router') as mock_router:
            await handle_onboarding_start(mock_update, mock_context)
            mock_router.assert_called_once()

    @pytest.mark.asyncio 
    async def test_handle_cancel_onboarding(self):
        """Test handle_cancel_onboarding entry point"""
        from handlers.onboarding_router import handle_cancel_onboarding
        
        mock_update = MagicMock()
        mock_update.effective_user.id = 123
        mock_context = MagicMock()
        
        with patch('handlers.onboarding_router.get_or_create_user') as mock_get_user, \
             patch('handlers.onboarding_router._handle_cancel') as mock_cancel, \
             patch('handlers.onboarding_router.managed_session'):
            
            mock_get_user.return_value = (MagicMock(id=123), False)
            
            await handle_cancel_onboarding(mock_update, mock_context)
            
            mock_cancel.assert_called()

    @pytest.mark.asyncio
    async def test_onboarding_text_handler(self):
        """Test onboarding_text_handler entry point"""
        from handlers.onboarding_router import onboarding_text_handler
        
        mock_update = MagicMock()
        mock_context = MagicMock()
        
        with patch('handlers.onboarding_router.onboarding_router') as mock_router:
            await onboarding_text_handler(mock_update, mock_context)
            mock_router.assert_called_once()

    @pytest.mark.asyncio
    async def test_onboarding_callback_handler(self):
        """Test onboarding_callback_handler entry point"""
        from handlers.onboarding_router import onboarding_callback_handler
        
        mock_update = MagicMock()
        mock_context = MagicMock()
        
        with patch('handlers.onboarding_router.onboarding_router') as mock_router:
            await onboarding_callback_handler(mock_update, mock_context)
            mock_router.assert_called_once()