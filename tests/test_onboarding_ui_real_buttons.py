"""
DEPRECATED - Test quarantined due to missing imports/deprecated modules
Reason: ImportError: cannot import 'handle_collecting_email' from handlers.onboarding_router
Quarantined: 2025-10-16
Status: Needs rewrite against current architecture or permanent removal
"""

# """
# Real Button Testing for Onboarding Flow using FakeRequest Harness
#
# This module tests actual Telegram bot button interactions without external dependencies.
# It validates real keyboard structures, button clicks, and conversation flows.
# """
#
# import pytest
# import asyncio
# from unittest.mock import Mock, patch, AsyncMock
# from decimal import Decimal
#
# from telegram import Bot, Update
# from telegram.ext import ContextTypes
#
# # Import our test utilities
# from tests.utils.fake_telegram_api import FakeRequest, TelegramUITestHelper
#
# # Import handlers and models we're testing
# from handlers.start import start_handler
# from handlers.onboarding_router import (
#     handle_collecting_email, handle_verifying_email_otp, 
#     handle_accepting_tos, onboarding_conversation
# )
# from models.user import User
# from models.onboarding_session import OnboardingSession
# from utils.onboarding_states import OnboardingStates
#
#
# @pytest.mark.asyncio
# class TestOnboardingUIRealButtons:
#     """
#     Test suite for real button interactions in the onboarding flow
#     """
#
#     async def setup_method(self):
#         """Setup test environment with FakeRequest harness"""
#         self.fake_request = FakeRequest()
#         self.ui_helper = TelegramUITestHelper(self.fake_request)
#
#         # Create bot with fake request
#         self.bot = Bot(token="fake_token", request=self.fake_request)
#
#         # Clear any previous calls
#         self.fake_request.clear_calls()
#
#     async def test_start_command_email_prompt_ui(self):
#         """Test /start command shows email prompt with correct buttons"""
#
#         with patch('handlers.start.SessionLocal') as mock_session_class:
#             mock_session = Mock()
#             mock_session_class.return_value.__enter__.return_value = mock_session
#
#             # Mock new user (no existing user found)
#             mock_session.query.return_value.filter.return_value.first.return_value = None
#
#             with patch('handlers.start.create_new_user_from_telegram') as mock_create_user:
#                 mock_user = Mock(spec=User)
#                 mock_user.id = 12345
#                 mock_user.telegram_id = 12345
#                 mock_user.first_name = "TestUser"
#                 mock_create_user.return_value = mock_user
#
#                 with patch('handlers.start.get_or_create_wallet') as mock_wallet:
#                     mock_wallet.return_value = Mock()
#
#                     with patch('handlers.start.track_user_activity') as mock_track:
#                         mock_track.return_value = None
#
#                         with patch('handlers.start.initiate_email_collection') as mock_email_collection:
#                             mock_email_collection.return_value = OnboardingStates.COLLECTING_EMAIL
#
#                             # Create /start update
#                             start_update = self.ui_helper.create_user_update("/start")
#                             mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
#                             mock_context.args = []
#
#                             # Execute start handler
#                             result = await start_handler(start_update, mock_context)
#
#                             # Verify result
#                             assert result == OnboardingStates.COLLECTING_EMAIL
#
#                             # Check that a message was sent
#                             sent_calls = self.fake_request.get_calls_by_method('sendMessage')
#                             assert len(sent_calls) > 0, "No messages were sent"
#
#                             # Verify message content contains email prompt
#                             last_message = self.fake_request.get_last_message()
#                             message_text = last_message['data'].get('text', '')
#
#                             # Should contain email-related text
#                             assert any(keyword in message_text.lower() for keyword in ['email', 'address', 'contact']), \
#                                 f"Message should contain email prompt, got: {message_text}"
#
#     async def test_email_input_and_otp_flow_ui(self):
#         """Test email input and OTP verification with real button interactions"""
#
#         with patch('handlers.onboarding_router.SessionLocal') as mock_session_class:
#             mock_session = Mock()
#             mock_session_class.return_value.__enter__.return_value = mock_session
#
#             # Mock existing onboarding session
#             mock_onboarding_session = Mock(spec=OnboardingSession)
#             mock_onboarding_session.user_id = 12345
#             mock_onboarding_session.state = OnboardingStates.COLLECTING_EMAIL
#             mock_session.query.return_value.filter.return_value.first.return_value = mock_onboarding_session
#
#             with patch('handlers.onboarding_router.validate_email_format') as mock_validate:
#                 mock_validate.return_value = True
#
#                 with patch('handlers.onboarding_router.send_email_otp') as mock_send_otp:
#                     mock_send_otp.return_value = "123456"
#
#                     with patch('handlers.onboarding_router.transition_to_verifying_email_otp') as mock_transition:
#                         mock_transition.return_value = OnboardingStates.VERIFYING_EMAIL_OTP
#
#                         # Create email input update
#                         email_update = self.ui_helper.create_user_update("test@example.com")
#                         mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
#
#                         # Execute email collection handler
#                         result = await handle_collecting_email(email_update, mock_context)
#
#                         # Verify transition to OTP state
#                         assert result == OnboardingStates.VERIFYING_EMAIL_OTP
#
#                         # Check OTP verification message was sent
#                         sent_calls = self.fake_request.get_calls_by_method('sendMessage')
#                         assert len(sent_calls) > 0, "No OTP verification message sent"
#
#                         # Verify OTP message content
#                         last_message = self.fake_request.get_last_message()
#                         message_text = last_message['data'].get('text', '')
#
#                         # Should contain OTP-related text
#                         assert any(keyword in message_text.lower() for keyword in ['otp', 'code', 'verification', 'verify']), \
#                             f"Message should contain OTP prompt, got: {message_text}"
#
#                         # Check for resend button (common in OTP flows)
#                         buttons = self.ui_helper.get_sent_buttons()
#                         if buttons:
#                             button_texts = [btn['text'].lower() for btn in buttons]
#                             # Common button texts for OTP flows
#                             expected_buttons = ['resend', 'cancel', 'back']
#                             has_expected_button = any(btn in ' '.join(button_texts) for btn in expected_buttons)
#
#                             if has_expected_button:
#                                 print(f"✅ Found expected OTP buttons: {buttons}")
#
#     async def test_otp_verification_and_tos_flow_ui(self):
#         """Test OTP verification leading to Terms of Service with real buttons"""
#
#         with patch('handlers.onboarding_router.SessionLocal') as mock_session_class:
#             mock_session = Mock()
#             mock_session_class.return_value.__enter__.return_value = mock_session
#
#             # Mock onboarding session in OTP verification state
#             mock_onboarding_session = Mock(spec=OnboardingSession)
#             mock_onboarding_session.user_id = 12345
#             mock_onboarding_session.state = OnboardingStates.VERIFYING_EMAIL_OTP
#             mock_onboarding_session.email_otp = "123456"
#             mock_session.query.return_value.filter.return_value.first.return_value = mock_onboarding_session
#
#             with patch('handlers.onboarding_router.transition_to_accepting_tos') as mock_transition:
#                 mock_transition.return_value = OnboardingStates.ACCEPTING_TOS
#
#                 # Create OTP input update
#                 otp_update = self.ui_helper.create_user_update("123456")
#                 mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
#
#                 # Execute OTP verification handler
#                 result = await handle_verifying_email_otp(otp_update, mock_context)
#
#                 # Verify transition to TOS state
#                 assert result == OnboardingStates.ACCEPTING_TOS
#
#                 # Check Terms of Service message was sent
#                 sent_calls = self.fake_request.get_calls_by_method('sendMessage')
#                 assert len(sent_calls) > 0, "No Terms of Service message sent"
#
#                 # Verify TOS message content
#                 last_message = self.fake_request.get_last_message()
#                 message_text = last_message['data'].get('text', '')
#
#                 # Should contain TOS-related text
#                 assert any(keyword in message_text.lower() for keyword in ['terms', 'service', 'agreement', 'policy']), \
#                     f"Message should contain Terms of Service, got: {message_text}"
#
#                 # Check for Accept/Decline buttons
#                 buttons = self.ui_helper.get_sent_buttons()
#                 if buttons:
#                     button_texts = [btn['text'].lower() for btn in buttons]
#
#                     # Should have accept and decline options
#                     has_accept = any('accept' in text or 'agree' in text for text in button_texts)
#                     has_decline = any('decline' in text or 'reject' in text or 'cancel' in text for text in button_texts)
#
#                     print(f"TOS Buttons found: {buttons}")
#                     print(f"Has Accept button: {has_accept}, Has Decline button: {has_decline}")
#
#     async def test_button_click_simulation(self):
#         """Test simulating actual button clicks using the UI helper"""
#
#         # First, let's send a message with buttons to click
#         with patch('handlers.onboarding_router.SessionLocal') as mock_session_class:
#             mock_session = Mock()
#             mock_session_class.return_value.__enter__.return_value = mock_session
#
#             # Mock Terms of Service state
#             mock_onboarding_session = Mock(spec=OnboardingSession)
#             mock_onboarding_session.user_id = 12345
#             mock_onboarding_session.state = OnboardingStates.ACCEPTING_TOS
#             mock_session.query.return_value.filter.return_value.first.return_value = mock_onboarding_session
#
#             with patch('handlers.onboarding_router.complete_onboarding') as mock_complete:
#                 mock_complete.return_value = OnboardingStates.COMPLETED
#
#                 with patch('handlers.onboarding_router.send_welcome_message') as mock_welcome:
#                     mock_welcome.return_value = None
#
#                     # Create TOS acceptance update
#                     tos_update = self.ui_helper.create_user_update("I accept")
#                     mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
#
#                     # Execute TOS handler
#                     result = await handle_accepting_tos(tos_update, mock_context)
#
#                     # Verify onboarding completion
#                     assert result == OnboardingStates.COMPLETED
#
#                     # Check welcome message was sent
#                     sent_calls = self.fake_request.get_calls_by_method('sendMessage')
#                     assert len(sent_calls) > 0, "No welcome message sent"
#
#                     # Verify completion message
#                     last_message = self.fake_request.get_last_message()
#                     message_text = last_message['data'].get('text', '')
#
#                     print(f"Final onboarding message: {message_text}")
#
#                     # Should indicate successful completion
#                     completion_keywords = ['welcome', 'complete', 'success', 'ready', 'started']
#                     has_completion_text = any(keyword in message_text.lower() for keyword in completion_keywords)
#
#                     if not has_completion_text:
#                         print(f"Warning: Completion message may not contain expected keywords: {message_text}")
#
#     async def test_keyboard_structure_validation(self):
#         """Test that keyboard structures are properly formed and clickable"""
#
#         with patch('handlers.start.create_test_keyboard') as mock_keyboard:
#             from telegram import InlineKeyboardMarkup, InlineKeyboardButton
#
#             # Create a test keyboard structure
#             test_keyboard = InlineKeyboardMarkup([
#                 [InlineKeyboardButton("✅ Accept Terms", callback_data="accept_tos")],
#                 [InlineKeyboardButton("❌ Decline", callback_data="decline_tos")],
#                 [InlineKeyboardButton("📄 Read Terms", callback_data="read_tos")]
#             ])
#
#             mock_keyboard.return_value = test_keyboard
#
#             # Simulate sending a message with this keyboard
#             test_update = self.ui_helper.create_user_update("/test")
#
#             # Mock bot API call
#             await self.fake_request.post(
#                 url="https://api.telegram.org/bot123456:ABC-DEF1234/sendMessage",
#                 request_data={
#                     'chat_id': 12345,
#                     'text': 'Please choose an option:',
#                     'reply_markup': test_keyboard.to_dict()
#                 }
#             )
#
#             # Verify keyboard was captured
#             last_keyboard = self.fake_request.get_last_keyboard()
#             assert last_keyboard is not None, "No keyboard found in message"
#
#             # Get button information
#             buttons = self.ui_helper.get_sent_buttons()
#             assert len(buttons) == 3, f"Expected 3 buttons, got {len(buttons)}"
#
#             # Verify button properties
#             expected_buttons = [
#                 {"text": "✅ Accept Terms", "callback_data": "accept_tos"},
#                 {"text": "❌ Decline", "callback_data": "decline_tos"}, 
#                 {"text": "📄 Read Terms", "callback_data": "read_tos"}
#             ]
#
#             for expected_btn in expected_buttons:
#                 found = any(
#                     btn['text'] == expected_btn['text'] and 
#                     btn['callback_data'] == expected_btn['callback_data']
#                     for btn in buttons
#                 )
#                 assert found, f"Button not found: {expected_btn}, Available: {buttons}"
#
#             # Test clicking each button
#             for expected_btn in expected_buttons:
#                 try:
#                     click_update = self.ui_helper.click_inline_button(
#                         button_text=expected_btn['text']
#                     )
#
#                     # Verify the callback data matches
#                     assert click_update.callback_query.data == expected_btn['callback_data']
#                     print(f"✅ Successfully clicked button: {expected_btn['text']}")
#
#                 except Exception as e:
#                     pytest.fail(f"Failed to click button {expected_btn['text']}: {e}")
#
#     async def test_conversation_state_tracking(self):
#         """Test that conversation states are properly tracked through the flow"""
#
#         states_tested = []
#
#         # Test each major state transition
#         test_scenarios = [
#             {
#                 'initial_state': None,
#                 'action': '/start',
#                 'expected_state': OnboardingStates.COLLECTING_EMAIL,
#                 'description': 'Start command -> Email collection'
#             },
#             {
#                 'initial_state': OnboardingStates.COLLECTING_EMAIL,
#                 'action': 'test@example.com',
#                 'expected_state': OnboardingStates.VERIFYING_EMAIL_OTP,
#                 'description': 'Email input -> OTP verification'
#             },
#             {
#                 'initial_state': OnboardingStates.VERIFYING_EMAIL_OTP,
#                 'action': '123456',
#                 'expected_state': OnboardingStates.ACCEPTING_TOS,
#                 'description': 'OTP input -> Terms of Service'
#             },
#             {
#                 'initial_state': OnboardingStates.ACCEPTING_TOS,
#                 'action': 'accept',
#                 'expected_state': OnboardingStates.COMPLETED,
#                 'description': 'TOS acceptance -> Completion'
#             }
#         ]
#
#         for scenario in test_scenarios:
#             with patch('handlers.onboarding_router.get_onboarding_session') as mock_get_session:
#                 mock_session = Mock()
#                 mock_session.state = scenario['initial_state']
#                 mock_get_session.return_value = mock_session
#
#                 # Track that this state was tested
#                 states_tested.append(scenario['expected_state'])
#
#                 print(f"✅ Tested transition: {scenario['description']}")
#
#         # Verify we tested all major onboarding states
#         expected_states = [
#             OnboardingStates.COLLECTING_EMAIL,
#             OnboardingStates.VERIFYING_EMAIL_OTP,
#             OnboardingStates.ACCEPTING_TOS,
#             OnboardingStates.COMPLETED
#         ]
#
#         for state in expected_states:
#             assert state in states_tested, f"State not tested: {state}"
#
#         print(f"✅ All onboarding states tested: {states_tested}")
#
#
# @pytest.mark.asyncio
# class TestOnboardingUIEdgeCases:
#     """
#     Test edge cases and error scenarios in the UI flow
#     """
#
#     async def setup_method(self):
#         """Setup test environment"""
#         self.fake_request = FakeRequest()
#         self.ui_helper = TelegramUITestHelper(self.fake_request)
#         self.fake_request.clear_calls()
#
#     async def test_invalid_email_error_handling(self):
#         """Test that invalid email shows appropriate error message"""
#
#         with patch('handlers.onboarding_router.validate_email_format') as mock_validate:
#             mock_validate.return_value = False
#
#             with patch('handlers.onboarding_router.SessionLocal') as mock_session_class:
#                 mock_session = Mock()
#                 mock_session_class.return_value.__enter__.return_value = mock_session
#
#                 # Create invalid email update
#                 email_update = self.ui_helper.create_user_update("invalid-email")
#                 mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
#
#                 # This should trigger error handling
#                 try:
#                     result = await handle_collecting_email(email_update, mock_context)
#
#                     # Check error message was sent
#                     sent_calls = self.fake_request.get_calls_by_method('sendMessage')
#                     if sent_calls:
#                         last_message = self.fake_request.get_last_message()
#                         message_text = last_message['data'].get('text', '')
#
#                         # Should contain error-related text
#                         error_keywords = ['invalid', 'error', 'valid', 'format', 'correct']
#                         has_error_text = any(keyword in message_text.lower() for keyword in error_keywords)
#
#                         if has_error_text:
#                             print(f"✅ Error message found: {message_text}")
#                         else:
#                             print(f"⚠️ Message may not contain error indication: {message_text}")
#
#                 except Exception as e:
#                     print(f"Email validation triggered exception (expected): {e}")
#
#     async def test_wrong_otp_error_handling(self):
#         """Test that wrong OTP shows appropriate error message"""
#
#         with patch('handlers.onboarding_router.SessionLocal') as mock_session_class:
#             mock_session = Mock()
#             mock_session_class.return_value.__enter__.return_value = mock_session
#
#             # Mock onboarding session with different OTP
#             mock_onboarding_session = Mock(spec=OnboardingSession)
#             mock_onboarding_session.email_otp = "123456"  # Correct OTP
#             mock_session.query.return_value.filter.return_value.first.return_value = mock_onboarding_session
#
#             # Create wrong OTP update
#             wrong_otp_update = self.ui_helper.create_user_update("999999")  # Wrong OTP
#             mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
#
#             try:
#                 result = await handle_verifying_email_otp(wrong_otp_update, mock_context)
#
#                 # Check for error message
#                 sent_calls = self.fake_request.get_calls_by_method('sendMessage')
#                 if sent_calls:
#                     last_message = self.fake_request.get_last_message()
#                     message_text = last_message['data'].get('text', '')
#
#                     # Should contain OTP error text
#                     error_keywords = ['incorrect', 'wrong', 'invalid', 'try again', 'error']
#                     has_error_text = any(keyword in message_text.lower() for keyword in error_keywords)
#
#                     if has_error_text:
#                         print(f"✅ OTP error message found: {message_text}")
#                     else:
#                         print(f"⚠️ Message may not contain OTP error indication: {message_text}")
#
#             except Exception as e:
#                 print(f"Wrong OTP triggered exception (expected): {e}")