"""
DEPRECATED - Test quarantined due to missing imports/deprecated modules
Reason: Missing test utilities module 'tests.utils.fake_telegram_api' (FakeRequest, TelegramUITestHelper)
Quarantined: 2025-10-16
Status: Needs rewrite against current architecture or permanent removal
"""

# """
# Comprehensive End-to-End Onboarding Flow Testing with Anomaly Detection
#
# This test suite uses the Real Bot Button Testing Framework to validate the complete
# user onboarding journey and detect anomalies, errors, and unexpected behaviors.
#
# **TESTING STRATEGY:**
# 1. Happy Path Testing - Normal flow through all states
# 2. Edge Case Testing - Invalid inputs, timeouts, errors
# 3. Button Interaction Testing - All UI elements and flows  
# 4. State Transition Validation - Proper flow between onboarding states
# 5. Data Persistence Testing - User data correctly saved
# 6. Performance Anomaly Detection - Slow responses, timeouts
# 7. Error Recovery Testing - System handles failures gracefully
#
# **REAL HANDLERS TESTED:**
# - onboarding_router (main entry point)
# - start_handler (initial /start command)
# - handle_collecting_email (email input processing)
# - handle_verifying_email_otp (OTP verification)
# - handle_accepting_tos (terms acceptance)
# - All button click handlers and callbacks
# """
#
# import pytest
# import asyncio
# import logging
# import time
# from datetime import datetime, timedelta
# from unittest.mock import Mock, patch, AsyncMock
# from typing import List, Dict, Any, Optional
#
# # Telegram imports
# from telegram import Bot, Update, InlineKeyboardMarkup, InlineKeyboardButton
# from telegram.ext import ContextTypes
#
# # Import our Real Bot Button Testing Framework
# from tests.utils.fake_telegram_api import FakeRequest, TelegramUITestHelper
#
# # Import the real handlers we're testing
# from handlers.start import start_handler, OnboardingStates
# from handlers.onboarding_router import (
#     onboarding_router,
#     handle_collecting_email,
#     handle_verifying_email_otp, 
#     handle_accepting_tos,
#     onboarding_text_handler,
#     onboarding_callback_handler
# )
#
# # Import models for data validation
# from models.user import User
# from models.onboarding_session import OnboardingSession
#
# logger = logging.getLogger(__name__)
#
#
# class OnboardingAnomalyDetector:
#     """
#     Detects anomalies in the onboarding flow during testing
#     """
#
#     def __init__(self):
#         self.anomalies: List[Dict[str, Any]] = []
#         self.performance_metrics: Dict[str, List[float]] = {}
#         self.expected_flow = [
#             OnboardingStates.COLLECTING_EMAIL,
#             OnboardingStates.VERIFYING_EMAIL_OTP,
#             OnboardingStates.ACCEPTING_TOS,
#             OnboardingStates.ONBOARDING_SHOWCASE
#         ]
#
#     def record_step_timing(self, step_name: str, duration_ms: float):
#         """Record timing for performance anomaly detection"""
#         if step_name not in self.performance_metrics:
#             self.performance_metrics[step_name] = []
#         self.performance_metrics[step_name].append(duration_ms)
#
#     def detect_timing_anomaly(self, step_name: str, duration_ms: float) -> bool:
#         """Detect if a step took unusually long"""
#         # Define expected timing thresholds (in milliseconds)
#         expected_thresholds = {
#             'start_handler': 500,
#             'email_collection': 300,
#             'otp_verification': 400,
#             'tos_acceptance': 200,
#             'button_click': 100
#         }
#
#         threshold = expected_thresholds.get(step_name, 1000)
#         if duration_ms > threshold:
#             self.anomalies.append({
#                 'type': 'performance_anomaly',
#                 'step': step_name,
#                 'duration_ms': duration_ms,
#                 'threshold_ms': threshold,
#                 'severity': 'HIGH' if duration_ms > threshold * 3 else 'MEDIUM'
#             })
#             return True
#         return False
#
#     def detect_flow_anomaly(self, expected_state: int, actual_state: int):
#         """Detect unexpected state transitions"""
#         if expected_state != actual_state:
#             self.anomalies.append({
#                 'type': 'flow_anomaly',
#                 'expected_state': expected_state,
#                 'actual_state': actual_state,
#                 'severity': 'HIGH'
#             })
#
#     def detect_ui_anomaly(self, expected_buttons: List[str], actual_buttons: List[str]):
#         """Detect missing or unexpected buttons"""
#         missing_buttons = set(expected_buttons) - set(actual_buttons)
#         unexpected_buttons = set(actual_buttons) - set(expected_buttons)
#
#         if missing_buttons or unexpected_buttons:
#             self.anomalies.append({
#                 'type': 'ui_anomaly',
#                 'missing_buttons': list(missing_buttons),
#                 'unexpected_buttons': list(unexpected_buttons),
#                 'severity': 'MEDIUM'
#             })
#
#     def detect_error_anomaly(self, step_name: str, error: Exception):
#         """Record unexpected errors"""
#         self.anomalies.append({
#             'type': 'error_anomaly',
#             'step': step_name,
#             'error_type': type(error).__name__,
#             'error_message': str(error),
#             'severity': 'HIGH'
#         })
#
#     def get_anomaly_report(self) -> Dict[str, Any]:
#         """Generate comprehensive anomaly report"""
#         return {
#             'total_anomalies': len(self.anomalies),
#             'anomalies_by_type': self._group_anomalies_by_type(),
#             'anomalies_by_severity': self._group_anomalies_by_severity(),
#             'performance_summary': self._summarize_performance(),
#             'detailed_anomalies': self.anomalies
#         }
#
#     def _group_anomalies_by_type(self) -> Dict[str, int]:
#         """Group anomalies by type"""
#         type_counts = {}
#         for anomaly in self.anomalies:
#             anomaly_type = anomaly['type']
#             type_counts[anomaly_type] = type_counts.get(anomaly_type, 0) + 1
#         return type_counts
#
#     def _group_anomalies_by_severity(self) -> Dict[str, int]:
#         """Group anomalies by severity"""
#         severity_counts = {}
#         for anomaly in self.anomalies:
#             severity = anomaly['severity']
#             severity_counts[severity] = severity_counts.get(severity, 0) + 1
#         return severity_counts
#
#     def _summarize_performance(self) -> Dict[str, Dict[str, float]]:
#         """Summarize performance metrics"""
#         summary = {}
#         for step, timings in self.performance_metrics.items():
#             if timings:
#                 summary[step] = {
#                     'avg_ms': sum(timings) / len(timings),
#                     'max_ms': max(timings),
#                     'min_ms': min(timings),
#                     'samples': len(timings)
#                 }
#         return summary
#
#
# @pytest.mark.asyncio
# class TestE2EOnboardingAnomalyDetection:
#     """
#     Comprehensive end-to-end onboarding flow testing with anomaly detection
#     """
#
#     async def setup_method(self):
#         """Setup test environment with Real Bot Button Testing Framework"""
#         self.fake_request = FakeRequest()
#         self.ui_helper = TelegramUITestHelper(self.fake_request)
#         self.bot = Bot(token="fake_token", request=self.fake_request)
#         self.anomaly_detector = OnboardingAnomalyDetector()
#
#         # Clear any previous calls
#         self.fake_request.clear_calls()
#         logger.info("🔧 E2E Onboarding Test Setup Complete")
#
#     async def test_complete_happy_path_onboarding(self):
#         """
#         Test the complete happy path onboarding flow and detect anomalies
#
#         This is the primary test that validates users can complete onboarding
#         without any issues and detects any anomalies in the process.
#         """
#         logger.info("🚀 Starting Complete Happy Path Onboarding Test")
#
#         test_user_id = 99999001
#         test_email = "happypath@example.com"
#         test_otp = "123456"
#
#         # STEP 1: Test /start command
#         start_time = time.time()
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
#                 mock_user.id = test_user_id
#                 mock_user.telegram_id = test_user_id
#                 mock_user.first_name = "HappyPath"
#                 mock_create_user.return_value = mock_user
#
#                 with patch('handlers.start.get_or_create_wallet') as mock_wallet:
#                     mock_wallet.return_value = Mock()
#
#                     with patch('handlers.start.track_user_activity') as mock_track:
#                         mock_track.return_value = None
#
#                         # Create /start update
#                         start_update = self.ui_helper.create_user_update("/start", user_id=test_user_id)
#                         mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
#                         mock_context.args = []
#                         mock_context.bot = self.bot
#
#                         try:
#                             # Execute start handler
#                             result = await start_handler(start_update, mock_context)
#
#                             # Record timing
#                             duration = (time.time() - start_time) * 1000
#                             self.anomaly_detector.record_step_timing('start_handler', duration)
#
#                             # Detect timing anomalies
#                             if self.anomaly_detector.detect_timing_anomaly('start_handler', duration):
#                                 logger.warning(f"⚠️ TIMING ANOMALY: Start handler took {duration:.1f}ms")
#
#                             # Validate expected flow state
#                             if hasattr(result, '__name__') or isinstance(result, int):
#                                 expected_state = OnboardingStates.COLLECTING_EMAIL
#                                 if result != expected_state:
#                                     self.anomaly_detector.detect_flow_anomaly(expected_state, result)
#                                     logger.warning(f"⚠️ FLOW ANOMALY: Expected {expected_state}, got {result}")
#                                 else:
#                                     logger.info(f"✅ STEP 1: Start handler completed correctly - State: {result}")
#
#                             # Check that messages were sent
#                             sent_messages = self.fake_request.get_calls_by_method('sendMessage')
#                             if not sent_messages:
#                                 self.anomaly_detector.detect_error_anomaly('start_handler', 
#                                     Exception("No messages sent by start handler"))
#                                 logger.error("❌ ANOMALY: Start handler sent no messages")
#                             else:
#                                 logger.info(f"✅ STEP 1: {len(sent_messages)} messages sent")
#
#                                 # Validate message content
#                                 last_message = self.fake_request.get_last_message()
#                                 message_text = last_message['data'].get('text', '')
#
#                                 # Check for email-related keywords
#                                 email_keywords = ['email', 'address', 'contact', 'verify']
#                                 if not any(keyword in message_text.lower() for keyword in email_keywords):
#                                     self.anomaly_detector.detect_ui_anomaly(['email_prompt'], ['unknown_prompt'])
#                                     logger.warning(f"⚠️ UI ANOMALY: Message may not contain email prompt: {message_text[:100]}")
#
#                                 # Check for buttons if expected
#                                 buttons = self.ui_helper.get_sent_buttons()
#                                 if buttons:
#                                     logger.info(f"✅ STEP 1: Found {len(buttons)} buttons: {[btn['text'] for btn in buttons]}")
#
#                         except Exception as e:
#                             self.anomaly_detector.detect_error_anomaly('start_handler', e)
#                             logger.error(f"❌ STEP 1 ERROR: {e}")
#
#         # STEP 2: Test email input
#         start_time = time.time()
#
#         with patch('handlers.onboarding_router.SessionLocal') as mock_session_class:
#             mock_session = Mock()
#             mock_session_class.return_value.__enter__.return_value = mock_session
#
#             # Mock onboarding session
#             mock_onboarding_session = Mock(spec=OnboardingSession)
#             mock_onboarding_session.user_id = test_user_id
#             mock_onboarding_session.state = OnboardingStates.COLLECTING_EMAIL
#             mock_session.query.return_value.filter.return_value.first.return_value = mock_onboarding_session
#
#             with patch('handlers.onboarding_router.validate_email_format') as mock_validate:
#                 mock_validate.return_value = True
#
#                 with patch('handlers.onboarding_router.send_email_otp') as mock_send_otp:
#                     mock_send_otp.return_value = test_otp
#
#                     with patch('handlers.onboarding_router.transition_to_verifying_email_otp') as mock_transition:
#                         mock_transition.return_value = OnboardingStates.VERIFYING_EMAIL_OTP
#
#                         try:
#                             # Create email input update
#                             email_update = self.ui_helper.create_user_update(test_email, user_id=test_user_id)
#                             mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
#                             mock_context.bot = self.bot
#
#                             # Execute email collection handler
#                             result = await handle_collecting_email(email_update, mock_context)
#
#                             # Record timing
#                             duration = (time.time() - start_time) * 1000
#                             self.anomaly_detector.record_step_timing('email_collection', duration)
#
#                             # Validate flow transition
#                             expected_state = OnboardingStates.VERIFYING_EMAIL_OTP
#                             if result != expected_state:
#                                 self.anomaly_detector.detect_flow_anomaly(expected_state, result)
#                                 logger.warning(f"⚠️ FLOW ANOMALY: Expected {expected_state}, got {result}")
#                             else:
#                                 logger.info(f"✅ STEP 2: Email collection completed - State: {result}")
#
#                             # Check OTP message was sent
#                             otp_messages = self.fake_request.get_calls_by_method('sendMessage')
#                             if otp_messages:
#                                 last_message = self.fake_request.get_last_message()
#                                 message_text = last_message['data'].get('text', '')
#
#                                 # Check for OTP-related keywords
#                                 otp_keywords = ['otp', 'code', 'verification', 'verify', 'sent']
#                                 if any(keyword in message_text.lower() for keyword in otp_keywords):
#                                     logger.info(f"✅ STEP 2: OTP message sent with correct content")
#                                 else:
#                                     self.anomaly_detector.detect_ui_anomaly(['otp_message'], ['unknown_message'])
#                                     logger.warning(f"⚠️ UI ANOMALY: OTP message may be incorrect: {message_text[:100]}")
#
#                         except Exception as e:
#                             self.anomaly_detector.detect_error_anomaly('email_collection', e)
#                             logger.error(f"❌ STEP 2 ERROR: {e}")
#
#         # STEP 3: Test OTP verification
#         start_time = time.time()
#
#         with patch('handlers.onboarding_router.SessionLocal') as mock_session_class:
#             mock_session = Mock()
#             mock_session_class.return_value.__enter__.return_value = mock_session
#
#             # Mock onboarding session in OTP state
#             mock_onboarding_session = Mock(spec=OnboardingSession)
#             mock_onboarding_session.user_id = test_user_id
#             mock_onboarding_session.state = OnboardingStates.VERIFYING_EMAIL_OTP
#             mock_onboarding_session.email_otp = test_otp
#             mock_session.query.return_value.filter.return_value.first.return_value = mock_onboarding_session
#
#             with patch('handlers.onboarding_router.transition_to_accepting_tos') as mock_transition:
#                 mock_transition.return_value = OnboardingStates.ACCEPTING_TOS
#
#                 try:
#                     # Create OTP input update
#                     otp_update = self.ui_helper.create_user_update(test_otp, user_id=test_user_id)
#                     mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
#                     mock_context.bot = self.bot
#
#                     # Execute OTP verification handler
#                     result = await handle_verifying_email_otp(otp_update, mock_context)
#
#                     # Record timing
#                     duration = (time.time() - start_time) * 1000
#                     self.anomaly_detector.record_step_timing('otp_verification', duration)
#
#                     # Validate flow transition
#                     expected_state = OnboardingStates.ACCEPTING_TOS
#                     if result != expected_state:
#                         self.anomaly_detector.detect_flow_anomaly(expected_state, result)
#                         logger.warning(f"⚠️ FLOW ANOMALY: Expected {expected_state}, got {result}")
#                     else:
#                         logger.info(f"✅ STEP 3: OTP verification completed - State: {result}")
#
#                     # Check Terms of Service message
#                     tos_messages = self.fake_request.get_calls_by_method('sendMessage')
#                     if tos_messages:
#                         last_message = self.fake_request.get_last_message()
#                         message_text = last_message['data'].get('text', '')
#
#                         # Check for TOS-related keywords
#                         tos_keywords = ['terms', 'service', 'agreement', 'policy', 'accept']
#                         if any(keyword in message_text.lower() for keyword in tos_keywords):
#                             logger.info(f"✅ STEP 3: Terms of Service message sent")
#                         else:
#                             self.anomaly_detector.detect_ui_anomaly(['tos_message'], ['unknown_message'])
#                             logger.warning(f"⚠️ UI ANOMALY: TOS message may be incorrect: {message_text[:100]}")
#
#                         # Check for Accept/Decline buttons
#                         buttons = self.ui_helper.get_sent_buttons()
#                         if buttons:
#                             button_texts = [btn['text'].lower() for btn in buttons]
#                             expected_buttons = ['accept', 'decline', 'agree']
#
#                             has_accept = any('accept' in text or 'agree' in text for text in button_texts)
#                             has_decline = any('decline' in text or 'cancel' in text for text in button_texts)
#
#                             if has_accept and has_decline:
#                                 logger.info(f"✅ STEP 3: Found Accept/Decline buttons")
#                             else:
#                                 self.anomaly_detector.detect_ui_anomaly(['accept_button', 'decline_button'], button_texts)
#                                 logger.warning(f"⚠️ UI ANOMALY: Missing expected buttons: {button_texts}")
#
#                 except Exception as e:
#                     self.anomaly_detector.detect_error_anomaly('otp_verification', e)
#                     logger.error(f"❌ STEP 3 ERROR: {e}")
#
#         # STEP 4: Test Terms of Service acceptance
#         start_time = time.time()
#
#         with patch('handlers.onboarding_router.SessionLocal') as mock_session_class:
#             mock_session = Mock()
#             mock_session_class.return_value.__enter__.return_value = mock_session
#
#             # Mock onboarding session in TOS state
#             mock_onboarding_session = Mock(spec=OnboardingSession)
#             mock_onboarding_session.user_id = test_user_id
#             mock_onboarding_session.state = OnboardingStates.ACCEPTING_TOS
#             mock_session.query.return_value.filter.return_value.first.return_value = mock_onboarding_session
#
#             with patch('handlers.onboarding_router.complete_onboarding') as mock_complete:
#                 mock_complete.return_value = OnboardingStates.ONBOARDING_SHOWCASE
#
#                 with patch('handlers.onboarding_router.send_welcome_message') as mock_welcome:
#                     mock_welcome.return_value = None
#
#                     try:
#                         # Test button click simulation
#                         if self.fake_request.get_calls_by_method('sendMessage'):
#                             # Try to click Accept button
#                             try:
#                                 accept_click = self.ui_helper.click_inline_button(button_text="Accept")
#                                 logger.info(f"✅ STEP 4: Successfully clicked Accept button")
#
#                                 # Record button click timing
#                                 button_duration = (time.time() - start_time) * 1000
#                                 self.anomaly_detector.record_step_timing('button_click', button_duration)
#
#                             except ValueError as e:
#                                 logger.info(f"ℹ️ STEP 4: Button click simulation not available: {e}")
#
#                         # Test TOS acceptance via text input
#                         tos_update = self.ui_helper.create_user_update("I accept", user_id=test_user_id)
#                         mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
#                         mock_context.bot = self.bot
#
#                         # Execute TOS acceptance handler
#                         result = await handle_accepting_tos(tos_update, mock_context)
#
#                         # Record timing
#                         duration = (time.time() - start_time) * 1000
#                         self.anomaly_detector.record_step_timing('tos_acceptance', duration)
#
#                         # Validate completion
#                         expected_state = OnboardingStates.ONBOARDING_SHOWCASE
#                         if result != expected_state:
#                             self.anomaly_detector.detect_flow_anomaly(expected_state, result)
#                             logger.warning(f"⚠️ FLOW ANOMALY: Expected {expected_state}, got {result}")
#                         else:
#                             logger.info(f"✅ STEP 4: Terms acceptance completed - State: {result}")
#
#                         # Check welcome/completion message
#                         completion_messages = self.fake_request.get_calls_by_method('sendMessage')
#                         if completion_messages:
#                             last_message = self.fake_request.get_last_message()
#                             message_text = last_message['data'].get('text', '')
#
#                             # Check for completion keywords
#                             completion_keywords = ['welcome', 'complete', 'success', 'ready', 'started']
#                             if any(keyword in message_text.lower() for keyword in completion_keywords):
#                                 logger.info(f"✅ STEP 4: Completion message sent")
#                             else:
#                                 self.anomaly_detector.detect_ui_anomaly(['completion_message'], ['unknown_message'])
#                                 logger.warning(f"⚠️ UI ANOMALY: Completion message may be incorrect: {message_text[:100]}")
#
#                     except Exception as e:
#                         self.anomaly_detector.detect_error_anomaly('tos_acceptance', e)
#                         logger.error(f"❌ STEP 4 ERROR: {e}")
#
#         # Generate comprehensive anomaly report
#         anomaly_report = self.anomaly_detector.get_anomaly_report()
#
#         logger.info("📊 ONBOARDING ANOMALY REPORT:")
#         logger.info(f"   Total Anomalies: {anomaly_report['total_anomalies']}")
#         logger.info(f"   By Type: {anomaly_report['anomalies_by_type']}")
#         logger.info(f"   By Severity: {anomaly_report['anomalies_by_severity']}")
#         logger.info(f"   Performance Summary: {anomaly_report['performance_summary']}")
#
#         if anomaly_report['total_anomalies'] > 0:
#             logger.warning("⚠️ ANOMALIES DETECTED - Review detailed report")
#             for anomaly in anomaly_report['detailed_anomalies']:
#                 logger.warning(f"   {anomaly['type']}: {anomaly}")
#         else:
#             logger.info("✅ NO ANOMALIES DETECTED - Onboarding flow is healthy")
#
#         # Assert test success based on anomaly severity
#         high_severity_anomalies = [a for a in self.anomaly_detector.anomalies if a.get('severity') == 'HIGH']
#         if high_severity_anomalies:
#             pytest.fail(f"HIGH SEVERITY ANOMALIES DETECTED: {high_severity_anomalies}")
#
#         logger.info("🎉 COMPLETE HAPPY PATH ONBOARDING TEST: PASSED")
#
#     async def test_edge_case_scenarios(self):
#         """
#         Test various edge cases and error scenarios to detect anomalies
#         """
#         logger.info("🔍 Starting Edge Case Scenarios Testing")
#
#         edge_cases = [
#             {
#                 'name': 'invalid_email',
#                 'input': 'invalid-email',
#                 'expected_behavior': 'error_message_or_retry'
#             },
#             {
#                 'name': 'empty_input',
#                 'input': '',
#                 'expected_behavior': 'prompt_for_input'
#             },
#             {
#                 'name': 'wrong_otp',
#                 'input': '999999',
#                 'expected_behavior': 'otp_error_message'
#             },
#             {
#                 'name': 'special_characters',
#                 'input': '!@#$%^&*()',
#                 'expected_behavior': 'input_validation'
#             }
#         ]
#
#         for case in edge_cases:
#             logger.info(f"🧪 Testing edge case: {case['name']}")
#
#             try:
#                 # Create test update with edge case input
#                 edge_update = self.ui_helper.create_user_update(case['input'])
#                 mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
#                 mock_context.bot = self.bot
#
#                 # Test with email collection handler
#                 with patch('handlers.onboarding_router.SessionLocal') as mock_session_class:
#                     mock_session = Mock()
#                     mock_session_class.return_value.__enter__.return_value = mock_session
#
#                     # Configure mocks based on edge case
#                     if case['name'] == 'invalid_email':
#                         with patch('handlers.onboarding_router.validate_email_format') as mock_validate:
#                             mock_validate.return_value = False
#
#                             result = await handle_collecting_email(edge_update, mock_context)
#
#                             # Check if system handled invalid email appropriately
#                             error_messages = self.fake_request.get_calls_by_method('sendMessage')
#                             if error_messages:
#                                 last_message = self.fake_request.get_last_message()
#                                 message_text = last_message['data'].get('text', '')
#
#                                 error_keywords = ['invalid', 'error', 'valid', 'format']
#                                 if any(keyword in message_text.lower() for keyword in error_keywords):
#                                     logger.info(f"✅ Edge Case {case['name']}: Handled correctly")
#                                 else:
#                                     self.anomaly_detector.detect_ui_anomaly(['error_message'], ['unexpected_message'])
#                                     logger.warning(f"⚠️ Edge Case {case['name']}: May not show proper error")
#
#                     logger.info(f"✅ Edge case {case['name']}: Completed testing")
#
#             except Exception as e:
#                 # Edge cases may throw exceptions - that's often expected behavior
#                 logger.info(f"ℹ️ Edge case {case['name']}: Exception (may be expected): {e}")
#
#         logger.info("✅ EDGE CASE SCENARIOS TESTING: Completed")
#
#     async def test_button_interaction_anomalies(self):
#         """
#         Test button interactions and detect UI anomalies
#         """
#         logger.info("🔘 Starting Button Interaction Anomaly Testing")
#
#         # Create test keyboard
#         test_keyboard = InlineKeyboardMarkup([
#             [InlineKeyboardButton("✅ Accept Terms", callback_data="accept_tos")],
#             [InlineKeyboardButton("❌ Decline", callback_data="decline_tos")],
#             [InlineKeyboardButton("📄 Read Terms", callback_data="read_tos")]
#         ])
#
#         # Send message with test keyboard
#         await self.fake_request.post(
#             url="https://api.telegram.org/bot123/sendMessage",
#             request_data={
#                 'chat_id': 12345,
#                 'text': 'Please choose an option:',
#                 'reply_markup': test_keyboard.to_dict()
#             }
#         )
#
#         # Test button detection
#         buttons = self.ui_helper.get_sent_buttons()
#         expected_buttons = ["✅ Accept Terms", "❌ Decline", "📄 Read Terms"]
#
#         if len(buttons) != len(expected_buttons):
#             self.anomaly_detector.detect_ui_anomaly(expected_buttons, [btn['text'] for btn in buttons])
#             logger.warning(f"⚠️ BUTTON ANOMALY: Expected {len(expected_buttons)}, got {len(buttons)}")
#
#         # Test clicking each button
#         for expected_btn in expected_buttons:
#             start_time = time.time()
#
#             try:
#                 click_update = self.ui_helper.click_inline_button(button_text=expected_btn)
#
#                 # Record button click timing
#                 duration = (time.time() - start_time) * 1000
#                 self.anomaly_detector.record_step_timing('button_click', duration)
#
#                 if self.anomaly_detector.detect_timing_anomaly('button_click', duration):
#                     logger.warning(f"⚠️ BUTTON TIMING ANOMALY: {expected_btn} took {duration:.1f}ms")
#
#                 logger.info(f"✅ Button click test: {expected_btn}")
#
#             except Exception as e:
#                 self.anomaly_detector.detect_error_anomaly('button_interaction', e)
#                 logger.error(f"❌ Button click failed: {expected_btn} - {e}")
#
#         logger.info("✅ BUTTON INTERACTION ANOMALY TESTING: Completed")
#
#     async def test_performance_anomalies(self):
#         """
#         Test for performance anomalies in the onboarding flow
#         """
#         logger.info("⚡ Starting Performance Anomaly Testing")
#
#         # Test multiple iterations to detect performance patterns
#         iterations = 5
#         for i in range(iterations):
#             start_time = time.time()
#
#             # Simulate start handler multiple times
#             start_update = self.ui_helper.create_user_update("/start")
#             mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
#
#             with patch('handlers.start.SessionLocal') as mock_session_class:
#                 mock_session = Mock()
#                 mock_session_class.return_value.__enter__.return_value = mock_session
#                 mock_session.query.return_value.filter.return_value.first.return_value = None
#
#                 with patch('handlers.start.create_new_user_from_telegram') as mock_create_user:
#                     mock_user = Mock(spec=User)
#                     mock_user.id = 99999999
#                     mock_create_user.return_value = mock_user
#
#                     with patch('handlers.start.get_or_create_wallet') as mock_wallet:
#                         mock_wallet.return_value = Mock()
#
#                         try:
#                             await start_handler(start_update, mock_context)
#
#                             duration = (time.time() - start_time) * 1000
#                             self.anomaly_detector.record_step_timing(f'performance_test_{i}', duration)
#
#                             logger.info(f"Performance iteration {i+1}: {duration:.1f}ms")
#
#                         except Exception as e:
#                             logger.info(f"Performance iteration {i+1}: Exception {e}")
#
#         # Analyze performance trends
#         performance_summary = self.anomaly_detector._summarize_performance()
#         logger.info(f"📊 Performance Summary: {performance_summary}")
#
#         # Detect significant performance variations
#         all_timings = []
#         for step, timings in self.anomaly_detector.performance_metrics.items():
#             all_timings.extend(timings)
#
#         if all_timings:
#             avg_time = sum(all_timings) / len(all_timings)
#             max_time = max(all_timings)
#
#             if max_time > avg_time * 3:  # More than 3x average
#                 self.anomaly_detector.anomalies.append({
#                     'type': 'performance_variation_anomaly',
#                     'avg_time_ms': avg_time,
#                     'max_time_ms': max_time,
#                     'variation_factor': max_time / avg_time,
#                     'severity': 'MEDIUM'
#                 })
#                 logger.warning(f"⚠️ PERFORMANCE VARIATION ANOMALY: Max {max_time:.1f}ms vs Avg {avg_time:.1f}ms")
#
#         logger.info("✅ PERFORMANCE ANOMALY TESTING: Completed")
#
#
# @pytest.mark.asyncio
# class TestOnboardingDataPersistence:
#     """
#     Test data persistence throughout the onboarding flow
#     """
#
#     async def setup_method(self):
#         """Setup test environment"""
#         self.fake_request = FakeRequest()
#         self.ui_helper = TelegramUITestHelper(self.fake_request)
#         self.anomaly_detector = OnboardingAnomalyDetector()
#         self.fake_request.clear_calls()
#
#     async def test_user_data_persistence_anomalies(self):
#         """
#         Test that user data is properly persisted throughout onboarding
#         """
#         logger.info("💾 Starting User Data Persistence Testing")
#
#         test_data = {
#             'user_id': 99999002,
#             'email': 'persistence@example.com',
#             'first_name': 'Persistence',
#             'username': 'persistence_user'
#         }
#
#         # Mock database session to track data persistence
#         with patch('handlers.onboarding_router.SessionLocal') as mock_session_class:
#             mock_session = Mock()
#             mock_session_class.return_value.__enter__.return_value = mock_session
#
#             # Track what data gets saved
#             saved_data = []
#
#             def track_add(obj):
#                 saved_data.append({
#                     'type': type(obj).__name__,
#                     'data': obj.__dict__ if hasattr(obj, '__dict__') else str(obj)
#                 })
#                 return obj
#
#             mock_session.add.side_effect = track_add
#
#             # Mock onboarding session
#             mock_onboarding_session = Mock(spec=OnboardingSession)
#             mock_onboarding_session.user_id = test_data['user_id']
#             mock_onboarding_session.email = test_data['email']
#             mock_session.query.return_value.filter.return_value.first.return_value = mock_onboarding_session
#
#             # Test email collection with data persistence
#             email_update = self.ui_helper.create_user_update(
#                 test_data['email'], 
#                 user_id=test_data['user_id']
#             )
#             mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
#
#             with patch('handlers.onboarding_router.validate_email_format') as mock_validate:
#                 mock_validate.return_value = True
#
#                 with patch('handlers.onboarding_router.send_email_otp') as mock_send_otp:
#                     mock_send_otp.return_value = "123456"
#
#                     try:
#                         await handle_collecting_email(email_update, mock_context)
#
#                         # Check if data was properly saved
#                         if mock_session.add.called:
#                             logger.info(f"✅ Data persistence: {len(saved_data)} objects saved")
#                             for data in saved_data:
#                                 logger.info(f"   Saved: {data['type']}")
#                         else:
#                             self.anomaly_detector.detect_error_anomaly('data_persistence', 
#                                 Exception("No data saved to database"))
#                             logger.warning("⚠️ DATA PERSISTENCE ANOMALY: No data saved")
#
#                         # Check if email was preserved
#                         if hasattr(mock_onboarding_session, 'email') and mock_onboarding_session.email == test_data['email']:
#                             logger.info("✅ Email data preserved correctly")
#                         else:
#                             self.anomaly_detector.detect_error_anomaly('email_persistence',
#                                 Exception("Email data not preserved"))
#                             logger.warning("⚠️ EMAIL PERSISTENCE ANOMALY")
#
#                     except Exception as e:
#                         self.anomaly_detector.detect_error_anomaly('data_persistence_test', e)
#                         logger.error(f"❌ Data persistence test error: {e}")
#
#         logger.info("✅ USER DATA PERSISTENCE TESTING: Completed")
#
#
# if __name__ == "__main__":
#     # Run the comprehensive onboarding anomaly detection tests
#     pytest.main([__file__, "-v", "-s", "--tb=short"])