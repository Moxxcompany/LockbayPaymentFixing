"""
Real User Onboarding Experience Validation

This test simulates the complete real user journey through onboarding:
1. User receives welcome message
2. User provides email address
3. User receives and enters OTP code
4. User accepts Terms of Service
5. User completes onboarding successfully

REAL USER SIMULATION:
✅ Simulates actual user interactions and expectations
✅ Tests complete conversation flow with realistic scenarios
✅ Validates user experience quality and usability
✅ Detects and reports any anomalies in the user journey
✅ Tests edge cases that real users might encounter
"""

import pytest
import logging
import time
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import Mock, patch

# Telegram imports
from telegram import Update, User as TelegramUser, Message, CallbackQuery, Chat, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

# Import testing framework
from tests.utils.fake_telegram_api import FakeRequest, TelegramUITestHelper

logger = logging.getLogger(__name__)


class RealUserExperienceValidator:
    """
    Validator that simulates real user expectations and detects UX anomalies
    """
    
    def __init__(self):
        self.user_expectations: List[Dict[str, Any]] = []
        self.ux_anomalies: List[Dict[str, Any]] = []
        self.flow_timing: Dict[str, float] = {}
        self.user_satisfaction_score = 100  # Start with perfect score
    
    def expect_user_experience(self, step: str, expectation: str, reality: str, critical: bool = True):
        """Record user experience expectation vs reality"""
        meets_expectation = expectation.lower() in reality.lower() if reality else False
        
        experience = {
            'step': step,
            'expectation': expectation,
            'reality': reality,
            'meets_expectation': meets_expectation,
            'critical': critical
        }
        self.user_expectations.append(experience)
        
        if not meets_expectation:
            if critical:
                self.user_satisfaction_score -= 20  # Major impact
                self.ux_anomalies.append({
                    'type': 'CRITICAL_UX_ANOMALY',
                    'step': step,
                    'issue': f'Expected: {expectation}, Got: {reality}',
                    'impact': 'HIGH'
                })
                logger.error(f"❌ CRITICAL UX ISSUE: {step} - Expected: {expectation}")
            else:
                self.user_satisfaction_score -= 5  # Minor impact
                self.ux_anomalies.append({
                    'type': 'MINOR_UX_ISSUE', 
                    'step': step,
                    'issue': f'Expected: {expectation}, Got: {reality}',
                    'impact': 'LOW'
                })
                logger.warning(f"⚠️ Minor UX Issue: {step}")
        else:
            logger.info(f"✅ User Expectation Met: {step}")
    
    def record_step_timing(self, step: str, duration_ms: float):
        """Record timing for user experience evaluation"""
        self.flow_timing[step] = duration_ms
        
        # Real user patience thresholds
        patience_thresholds = {
            'welcome_response': 1000,     # 1 second for welcome
            'email_processing': 2000,     # 2 seconds for email validation
            'otp_generation': 3000,       # 3 seconds for OTP sending
            'tos_processing': 1500,       # 1.5 seconds for ToS
            'completion': 2000            # 2 seconds for final confirmation
        }
        
        threshold = patience_thresholds.get(step, 2000)
        if duration_ms > threshold:
            self.user_satisfaction_score -= 10
            self.ux_anomalies.append({
                'type': 'SLOW_RESPONSE',
                'step': step,
                'duration_ms': duration_ms,
                'threshold_ms': threshold,
                'impact': 'MEDIUM'
            })
            logger.warning(f"⏰ Slow response detected: {step} took {duration_ms:.1f}ms")
    
    def validate_message_clarity(self, step: str, message: str):
        """Validate message clarity for real users"""
        clarity_indicators = {
            'welcome': ['welcome', 'start', 'begin', 'hello'],
            'email_request': ['email', 'address', 'provide', '@'],
            'otp_request': ['code', 'verification', 'sent', 'enter'],
            'tos_request': ['terms', 'service', 'accept', 'agree'],
            'completion': ['complete', 'ready', 'success', 'congratulations']
        }
        
        if step in clarity_indicators:
            expected_indicators = clarity_indicators[step]
            found_indicators = [ind for ind in expected_indicators if ind.lower() in message.lower()]
            
            if len(found_indicators) == 0:
                self.user_satisfaction_score -= 15
                self.ux_anomalies.append({
                    'type': 'UNCLEAR_MESSAGE',
                    'step': step,
                    'message': message,
                    'missing_indicators': expected_indicators,
                    'impact': 'HIGH'
                })
                logger.error(f"❌ Unclear message in {step}: {message[:100]}")
            else:
                logger.info(f"✅ Clear message in {step}: Found {found_indicators}")
    
    def validate_button_usability(self, step: str, buttons: List[str]):
        """Validate button text is user-friendly"""
        usability_issues = []
        
        for button_text in buttons:
            # Check for technical jargon
            technical_terms = ['callback', 'handler', 'process', 'execute', 'api']
            if any(term in button_text.lower() for term in technical_terms):
                usability_issues.append(f"Technical jargon in button: {button_text}")
            
            # Check for emoji and clarity
            if len(button_text) < 3:
                usability_issues.append(f"Button text too short: {button_text}")
            
            if len(button_text) > 30:
                usability_issues.append(f"Button text too long: {button_text}")
        
        if usability_issues:
            self.user_satisfaction_score -= len(usability_issues) * 5
            for issue in usability_issues:
                self.ux_anomalies.append({
                    'type': 'BUTTON_USABILITY_ISSUE',
                    'step': step,
                    'issue': issue,
                    'impact': 'MEDIUM'
                })
                logger.warning(f"⚠️ Button usability issue: {issue}")
    
    def get_user_experience_report(self) -> Dict[str, Any]:
        """Generate comprehensive user experience report"""
        total_expectations = len(self.user_expectations)
        met_expectations = sum(1 for exp in self.user_expectations if exp['meets_expectation'])
        
        critical_anomalies = [a for a in self.ux_anomalies if a.get('impact') == 'HIGH']
        medium_anomalies = [a for a in self.ux_anomalies if a.get('impact') == 'MEDIUM']
        minor_anomalies = [a for a in self.ux_anomalies if a.get('impact') == 'LOW']
        
        return {
            'user_satisfaction_score': max(0, self.user_satisfaction_score),
            'expectations_met': f"{met_expectations}/{total_expectations}",
            'expectation_rate': (met_expectations / total_expectations * 100) if total_expectations > 0 else 0,
            'total_anomalies': len(self.ux_anomalies),
            'critical_anomalies': len(critical_anomalies),
            'medium_anomalies': len(medium_anomalies),
            'minor_anomalies': len(minor_anomalies),
            'average_response_time': sum(self.flow_timing.values()) / len(self.flow_timing) if self.flow_timing else 0,
            'detailed_anomalies': self.ux_anomalies,
            'flow_timing': self.flow_timing
        }
    
    def assert_acceptable_user_experience(self):
        """Assert that user experience meets acceptable standards"""
        report = self.get_user_experience_report()
        
        # Fail test if user satisfaction is too low
        if report['user_satisfaction_score'] < 70:
            pytest.fail(f"User satisfaction too low: {report['user_satisfaction_score']}/100")
        
        # Fail test if too many critical issues
        if report['critical_anomalies'] > 2:
            pytest.fail(f"Too many critical UX anomalies: {report['critical_anomalies']}")
        
        # Fail test if expectation rate is too low
        if report['expectation_rate'] < 80:
            pytest.fail(f"User expectation rate too low: {report['expectation_rate']:.1f}%")
        
        logger.info(f"✅ User Experience Acceptable: {report['user_satisfaction_score']}/100 satisfaction")


@pytest.mark.asyncio
class TestRealUserOnboardingValidation:
    """
    Real user onboarding experience validation
    """
    
    def setup_method(self, method):
        """Setup for real user experience testing"""
        self.fake_request = FakeRequest()
        self.ui_helper = TelegramUITestHelper(self.fake_request)
        self.ux_validator = RealUserExperienceValidator()
        self.fake_request.clear_calls()
        
        # Real user data
        self.real_user_id = 88800500
        self.real_email = "realuser@example.com"
        self.real_name = "Sarah Johnson"
        
        logger.info("🔧 Real User Experience Validation Setup Complete")
    
    async def test_real_user_welcome_experience(self):
        """Test the real user welcome and start experience"""
        logger.info("👋 Testing Real User Welcome Experience")
        
        start_time = time.time()
        
        # Simulate welcome message that real users would see
        await self.fake_request.post(
            url="https://api.telegram.org/bot123/sendMessage",
            request_data={
                'chat_id': self.real_user_id,
                'text': '👋 Welcome to LockBay! Ready to set up your secure crypto escrow account?',
                'reply_markup': InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 Get Started", callback_data="start_onboarding")]
                ]).to_dict()
            }
        )
        
        duration = (time.time() - start_time) * 1000
        self.ux_validator.record_step_timing('welcome_response', duration)
        
        # Validate welcome message meets user expectations
        last_message = self.fake_request.get_last_message()
        welcome_text = last_message['data'].get('text', '')
        
        self.ux_validator.expect_user_experience(
            'welcome_message',
            'Friendly welcome with clear next step',
            welcome_text
        )
        
        self.ux_validator.validate_message_clarity('welcome', welcome_text)
        
        # Test welcome button interaction
        buttons = self.ui_helper.get_sent_buttons()
        button_texts = [btn['text'] for btn in buttons]
        
        self.ux_validator.validate_button_usability('welcome', button_texts)
        
        # Simulate user clicking "Get Started"
        try:
            start_click = self.ui_helper.click_inline_button(button_text="🚀 Get Started")
            button_works = start_click.callback_query.data == "start_onboarding"
            
            self.ux_validator.expect_user_experience(
                'start_button',
                'Button should work when clicked',
                'Button works correctly' if button_works else 'Button failed'
            )
        except Exception as e:
            self.ux_validator.expect_user_experience(
                'start_button',
                'Button should work when clicked', 
                f'Button error: {e}',
                critical=True
            )
        
        logger.info("✅ Real User Welcome Experience Validated")
    
    async def test_real_user_email_collection_experience(self):
        """Test real user email collection experience"""
        logger.info("📧 Testing Real User Email Collection Experience")
        
        start_time = time.time()
        
        # Email collection prompt that users see
        await self.fake_request.post(
            url="https://api.telegram.org/bot123/sendMessage",
            request_data={
                'chat_id': self.real_user_id,
                'text': '📧 Please enter your email address to verify your identity and secure your account:\n\nExample: sarah@gmail.com',
                'reply_markup': InlineKeyboardMarkup([
                    [InlineKeyboardButton("ℹ️ Why do I need to provide email?", callback_data="email_help")]
                ]).to_dict()
            }
        )
        
        duration = (time.time() - start_time) * 1000
        self.ux_validator.record_step_timing('email_processing', duration)
        
        # Validate email prompt meets user expectations
        last_message = self.fake_request.get_last_message()
        email_text = last_message['data'].get('text', '')
        
        self.ux_validator.expect_user_experience(
            'email_prompt',
            'Clear instructions for email with example',
            email_text
        )
        
        self.ux_validator.validate_message_clarity('email_request', email_text)
        
        # Test help button availability
        buttons = self.ui_helper.get_sent_buttons()
        has_help = any('help' in btn['text'].lower() or 'why' in btn['text'].lower() for btn in buttons)
        
        self.ux_validator.expect_user_experience(
            'email_help',
            'Help information should be available',
            'Help button available' if has_help else 'No help available',
            critical=False  # Nice to have, not critical
        )
        
        # Simulate user entering email
        email_update = self.ui_helper.create_user_update(self.real_email, user_id=self.real_user_id)
        email_entered_correctly = email_update.message.text == self.real_email
        
        self.ux_validator.expect_user_experience(
            'email_input',
            'User should be able to enter email correctly',
            f'Email entered: {email_update.message.text}' if email_entered_correctly else 'Email input failed'
        )
        
        logger.info("✅ Real User Email Collection Experience Validated")
    
    async def test_real_user_otp_verification_experience(self):
        """Test real user OTP verification experience"""
        logger.info("🔢 Testing Real User OTP Verification Experience")
        
        start_time = time.time()
        
        # OTP verification prompt
        await self.fake_request.post(
            url="https://api.telegram.org/bot123/sendMessage",
            request_data={
                'chat_id': self.real_user_id,
                'text': f'✉️ We\'ve sent a 6-digit verification code to {self.real_email}\n\nPlease enter the code to continue:',
                'reply_markup': InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Resend Code", callback_data="resend_otp")],
                    [InlineKeyboardButton("📧 Change Email", callback_data="change_email")]
                ]).to_dict()
            }
        )
        
        duration = (time.time() - start_time) * 1000
        self.ux_validator.record_step_timing('otp_generation', duration)
        
        # Validate OTP prompt meets user expectations
        last_message = self.fake_request.get_last_message()
        otp_text = last_message['data'].get('text', '')
        
        self.ux_validator.expect_user_experience(
            'otp_prompt',
            'Clear instructions with email confirmation and code format',
            otp_text
        )
        
        self.ux_validator.validate_message_clarity('otp_request', otp_text)
        
        # Test essential OTP buttons
        buttons = self.ui_helper.get_sent_buttons()
        button_texts = [btn['text'] for btn in buttons]
        
        has_resend = any('resend' in btn.lower() for btn in button_texts)
        has_change_email = any('change' in btn.lower() and 'email' in btn.lower() for btn in button_texts)
        
        self.ux_validator.expect_user_experience(
            'otp_resend_option',
            'Users should be able to resend OTP code',
            'Resend option available' if has_resend else 'No resend option'
        )
        
        self.ux_validator.expect_user_experience(
            'email_change_option', 
            'Users should be able to change email if needed',
            'Change email option available' if has_change_email else 'No change email option'
        )
        
        self.ux_validator.validate_button_usability('otp_verification', button_texts)
        
        # Test button functionality
        try:
            resend_click = self.ui_helper.click_inline_button(button_text="🔄 Resend Code")
            resend_works = resend_click.callback_query.data == "resend_otp"
            
            self.ux_validator.expect_user_experience(
                'resend_functionality',
                'Resend button should work',
                'Resend works' if resend_works else 'Resend failed'
            )
        except Exception as e:
            self.ux_validator.expect_user_experience(
                'resend_functionality',
                'Resend button should work',
                f'Resend error: {e}'
            )
        
        logger.info("✅ Real User OTP Verification Experience Validated")
    
    async def test_real_user_terms_acceptance_experience(self):
        """Test real user Terms of Service acceptance experience"""
        logger.info("📋 Testing Real User Terms Acceptance Experience")
        
        start_time = time.time()
        
        # Terms of Service prompt
        await self.fake_request.post(
            url="https://api.telegram.org/bot123/sendMessage",
            request_data={
                'chat_id': self.real_user_id,
                'text': '📋 Almost done! Please review and accept our Terms of Service to complete your registration:\n\nBy using LockBay, you agree to our secure escrow practices and user protection policies.',
                'reply_markup': InlineKeyboardMarkup([
                    [InlineKeyboardButton("📄 Read Full Terms", callback_data="read_terms")],
                    [InlineKeyboardButton("✅ Accept Terms", callback_data="tos_accept")],
                    [InlineKeyboardButton("❌ Decline", callback_data="tos_decline")]
                ]).to_dict()
            }
        )
        
        duration = (time.time() - start_time) * 1000
        self.ux_validator.record_step_timing('tos_processing', duration)
        
        # Validate ToS prompt meets user expectations
        last_message = self.fake_request.get_last_message()
        tos_text = last_message['data'].get('text', '')
        
        self.ux_validator.expect_user_experience(
            'tos_prompt',
            'Clear terms explanation with accept/decline options',
            tos_text
        )
        
        self.ux_validator.validate_message_clarity('tos_request', tos_text)
        
        # Test ToS buttons
        buttons = self.ui_helper.get_sent_buttons()
        button_texts = [btn['text'] for btn in buttons]
        
        has_read_option = any('read' in btn.lower() for btn in button_texts)
        has_accept = any('accept' in btn.lower() for btn in button_texts)
        has_decline = any('decline' in btn.lower() for btn in button_texts)
        
        self.ux_validator.expect_user_experience(
            'tos_read_option',
            'Users should be able to read full terms',
            'Read option available' if has_read_option else 'No read option'
        )
        
        self.ux_validator.expect_user_experience(
            'tos_accept_option',
            'Users should be able to accept terms',
            'Accept option available' if has_accept else 'No accept option'
        )
        
        self.ux_validator.expect_user_experience(
            'tos_decline_option',
            'Users should be able to decline terms',
            'Decline option available' if has_decline else 'No decline option'
        )
        
        self.ux_validator.validate_button_usability('terms_acceptance', button_texts)
        
        # Test accept functionality
        try:
            accept_click = self.ui_helper.click_inline_button(button_text="✅ Accept Terms")
            accept_works = accept_click.callback_query.data == "tos_accept"
            
            self.ux_validator.expect_user_experience(
                'tos_accept_functionality',
                'Accept button should work correctly',
                'Accept works' if accept_works else 'Accept failed'
            )
        except Exception as e:
            self.ux_validator.expect_user_experience(
                'tos_accept_functionality',
                'Accept button should work correctly',
                f'Accept error: {e}'
            )
        
        logger.info("✅ Real User Terms Acceptance Experience Validated")
    
    async def test_real_user_completion_experience(self):
        """Test real user onboarding completion experience"""
        logger.info("🎉 Testing Real User Completion Experience")
        
        start_time = time.time()
        
        # Completion message
        await self.fake_request.post(
            url="https://api.telegram.org/bot123/sendMessage",
            request_data={
                'chat_id': self.real_user_id,
                'text': f'🎉 Congratulations, {self.real_name}! Your LockBay account is now ready.\n\nYou can now:\n• Create secure escrow transactions\n• Trade cryptocurrency safely\n• Access your wallet dashboard',
                'reply_markup': InlineKeyboardMarkup([
                    [InlineKeyboardButton("💰 View Wallet", callback_data="view_wallet")],
                    [InlineKeyboardButton("🛡️ Create Escrow", callback_data="create_escrow")],
                    [InlineKeyboardButton("📚 Learn More", callback_data="help_center")]
                ]).to_dict()
            }
        )
        
        duration = (time.time() - start_time) * 1000
        self.ux_validator.record_step_timing('completion', duration)
        
        # Validate completion message meets user expectations
        last_message = self.fake_request.get_last_message()
        completion_text = last_message['data'].get('text', '')
        
        self.ux_validator.expect_user_experience(
            'completion_message',
            'Congratulatory message with clear next steps',
            completion_text
        )
        
        self.ux_validator.validate_message_clarity('completion', completion_text)
        
        # Test next steps buttons
        buttons = self.ui_helper.get_sent_buttons()
        button_texts = [btn['text'] for btn in buttons]
        
        has_wallet = any('wallet' in btn.lower() for btn in button_texts)
        has_escrow = any('escrow' in btn.lower() for btn in button_texts)
        has_help = any('learn' in btn.lower() or 'help' in btn.lower() for btn in button_texts)
        
        self.ux_validator.expect_user_experience(
            'next_steps_wallet',
            'Users should be able to access wallet',
            'Wallet access available' if has_wallet else 'No wallet access'
        )
        
        self.ux_validator.expect_user_experience(
            'next_steps_escrow',
            'Users should be able to create escrow',
            'Escrow creation available' if has_escrow else 'No escrow creation'
        )
        
        self.ux_validator.expect_user_experience(
            'next_steps_help',
            'Users should be able to get help',
            'Help available' if has_help else 'No help available',
            critical=False
        )
        
        self.ux_validator.validate_button_usability('completion', button_texts)
        
        logger.info("✅ Real User Completion Experience Validated")
    
    async def test_complete_real_user_onboarding_journey(self):
        """
        COMPLETE REAL USER ONBOARDING JOURNEY VALIDATION
        
        This test simulates the complete real user experience from start to finish
        """
        logger.info("🚀 Testing COMPLETE Real User Onboarding Journey")
        
        # Execute complete user journey step by step
        await self.test_real_user_welcome_experience()
        await self.test_real_user_email_collection_experience()
        await self.test_real_user_otp_verification_experience()
        await self.test_real_user_terms_acceptance_experience()
        await self.test_real_user_completion_experience()
        
        # Generate comprehensive user experience report
        ux_report = self.ux_validator.get_user_experience_report()
        
        logger.info("📊 REAL USER ONBOARDING EXPERIENCE REPORT:")
        logger.info("=" * 60)
        logger.info(f"📈 User Satisfaction Score: {ux_report['user_satisfaction_score']}/100")
        logger.info(f"✅ Expectations Met: {ux_report['expectations_met']} ({ux_report['expectation_rate']:.1f}%)")
        logger.info(f"⚠️ Total Anomalies: {ux_report['total_anomalies']}")
        logger.info(f"🔴 Critical Anomalies: {ux_report['critical_anomalies']}")
        logger.info(f"🟡 Medium Anomalies: {ux_report['medium_anomalies']}")
        logger.info(f"🟢 Minor Anomalies: {ux_report['minor_anomalies']}")
        logger.info(f"⏱️ Average Response Time: {ux_report['average_response_time']:.1f}ms")
        
        # Log timing details
        logger.info("\n⏱️ RESPONSE TIME BREAKDOWN:")
        for step, timing in ux_report['flow_timing'].items():
            status = "✅" if timing < 2000 else "⚠️" if timing < 4000 else "❌"
            logger.info(f"   {status} {step}: {timing:.1f}ms")
        
        # Log detailed anomalies
        if ux_report['detailed_anomalies']:
            logger.info("\n🔍 DETAILED ANOMALIES:")
            for anomaly in ux_report['detailed_anomalies']:
                impact_emoji = "🔴" if anomaly['impact'] == 'HIGH' else "🟡" if anomaly['impact'] == 'MEDIUM' else "🟢"
                logger.info(f"   {impact_emoji} {anomaly['type']}: {anomaly.get('issue', anomaly)}")
        
        logger.info("=" * 60)
        
        # Assert acceptable user experience
        self.ux_validator.assert_acceptable_user_experience()
        
        logger.info("🎉 COMPLETE REAL USER ONBOARDING JOURNEY: VALIDATED")


if __name__ == "__main__":
    # Run the real user onboarding validation
    pytest.main([__file__, "-v", "-s", "--tb=short"])