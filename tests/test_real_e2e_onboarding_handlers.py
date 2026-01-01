"""
TRUE End-to-End Onboarding Handler Testing

This test suite exercises the REAL onboarding_router handler with:
✅ Real telegram.ext.Application routing
✅ Real database persistence validation  
✅ Real business logic testing (email validation, OTP, ToS)
✅ Mock only external services (email/SMS deterministically)
✅ 100% success threshold for critical onboarding path

REAL COMPONENTS TESTED:
- onboarding_router (actual handler routing)
- OnboardingService (real business logic)
- Database persistence (User, OnboardingSession creation)
- Real Update object routing through handlers
- Complete /start → email → OTP → ToS flow
"""

import pytest
import asyncio
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal

# Telegram imports
from telegram import Update, User as TelegramUser, Message, CallbackQuery, Chat, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, ContextTypes

# REAL imports from actual codebase
from handlers.onboarding_router import onboarding_router, OnboardingCallbacks
from handlers.start import OnboardingStates
from database import managed_session
from models import User, OnboardingSession, OnboardingStep
from services.onboarding_service import OnboardingService

# Import testing framework
from tests.utils.fake_telegram_api import FakeRequest, TelegramUITestHelper

logger = logging.getLogger(__name__)


class E2EOnboardingValidator:
    """
    Strict validator for end-to-end onboarding flow
    100% success threshold - any failure fails the test
    """
    
    def __init__(self):
        self.test_results: List[Dict[str, Any]] = []
        self.database_validations: List[Dict[str, Any]] = []
        self.handler_validations: List[Dict[str, Any]] = []
    
    def record_test(self, test_name: str, success: bool, details: str = "", critical: bool = True):
        """Record test result with strict failure handling"""
        result = {
            'test': test_name,
            'success': success,
            'details': details,
            'critical': critical,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        if not success:
            logger.error(f"❌ CRITICAL E2E FAILURE: {test_name} - {details}")
            if critical:
                pytest.fail(f"E2E onboarding test failed: {test_name} - {details}")
        else:
            logger.info(f"✅ E2E SUCCESS: {test_name}")
    
    def record_database_validation(self, operation: str, user_id: int, expected: Any, actual: Any):
        """Record database state validation"""
        success = expected == actual
        validation = {
            'operation': operation,
            'user_id': user_id,
            'expected': expected,
            'actual': actual,
            'success': success
        }
        self.database_validations.append(validation)
        
        if not success:
            logger.error(f"❌ DB VALIDATION FAILED: {operation} - Expected: {expected}, Got: {actual}")
            pytest.fail(f"Database validation failed: {operation} - Expected: {expected}, Got: {actual}")
        else:
            logger.info(f"✅ DB VALIDATION: {operation} - {expected}")
    
    def record_handler_validation(self, handler: str, update_type: str, response_valid: bool, details: str = ""):
        """Record handler response validation"""
        validation = {
            'handler': handler,
            'update_type': update_type,
            'response_valid': response_valid,
            'details': details
        }
        self.handler_validations.append(validation)
        
        if not response_valid:
            logger.error(f"❌ HANDLER VALIDATION FAILED: {handler} - {details}")
            pytest.fail(f"Handler validation failed: {handler} - {details}")
        else:
            logger.info(f"✅ HANDLER VALIDATION: {handler} - {update_type}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive test summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for t in self.test_results if t['success'])
        
        db_total = len(self.database_validations)
        db_passed = sum(1 for v in self.database_validations if v['success'])
        
        handler_total = len(self.handler_validations)
        handler_passed = sum(1 for v in self.handler_validations if v['response_valid'])
        
        return {
            'tests': {'total': total_tests, 'passed': passed_tests, 'failed': total_tests - passed_tests},
            'database': {'total': db_total, 'passed': db_passed, 'failed': db_total - db_passed},
            'handlers': {'total': handler_total, 'passed': handler_passed, 'failed': handler_total - handler_passed},
            'overall_success': passed_tests == total_tests and db_passed == db_total and handler_passed == handler_total
        }


@pytest.mark.asyncio 
class TestRealE2EOnboardingHandlers:
    """
    TRUE end-to-end onboarding testing with real handlers and database
    """
    
    def setup_method(self, method):
        """Setup for real E2E testing"""
        self.fake_request = FakeRequest()
        self.ui_helper = TelegramUITestHelper(self.fake_request)
        self.validator = E2EOnboardingValidator()
        self.fake_request.clear_calls()
        
        # Test user data - using unique IDs to avoid conflicts
        self.test_user_id = 88800200  # Different from UI tests
        self.test_email = "e2etest@example.com"
        self.test_otp = "123456"
        
        logger.info("🔧 Real E2E Onboarding Test Setup Complete")
    
    async def teardown_method(self, method):
        """Cleanup test data"""
        try:
            async with managed_session() as session:
                from sqlalchemy import delete, select
                
                # Clean up with proper user resolution
                result = await session.execute(select(User).where(User.telegram_id == str(self.test_user_id)))
                user = result.scalar_one_or_none()
                
                if user:
                    await session.execute(delete(OnboardingSession).where(OnboardingSession.user_id == user.id))
                    await session.execute(delete(User).where(User.id == user.id))
                    await session.commit()
                    logger.info(f"🧹 E2E test data cleaned up for user.id={user.id}")
                    
        except Exception as e:
            logger.warning(f"E2E cleanup warning: {e}")
    
    async def _create_real_telegram_context(self) -> ContextTypes.DEFAULT_TYPE:
        """Create REAL telegram context for handler testing"""
        # Create a real Application instance for proper context
        app = Application.builder().token("123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh").build()
        
        # Initialize the application (required for context creation)
        await app.initialize()
        
        # Create context from application
        context = ContextTypes.DEFAULT_TYPE.from_update(None, app)
        context.bot = self.ui_helper.bot  # Use our testing bot
        context.user_data = {}
        context.chat_data = {}
        
        return context
    
    async def _validate_database_user_creation(self, telegram_id: int) -> Optional[User]:
        """Validate user was created in database"""
        async with managed_session() as session:
            from sqlalchemy import select
            result = await session.execute(select(User).where(User.telegram_id == str(telegram_id)))
            user = result.scalar_one_or_none()
            
            self.validator.record_database_validation(
                'user_creation', 
                telegram_id, 
                'User exists', 
                'User exists' if user else 'User missing'
            )
            
            return user
    
    async def _validate_onboarding_session_creation(self, user_id: int) -> Optional[OnboardingSession]:
        """Validate onboarding session was created"""
        async with managed_session() as session:
            from sqlalchemy import select
            result = await session.execute(select(OnboardingSession).where(OnboardingSession.user_id == user_id))
            session_obj = result.scalar_one_or_none()
            
            self.validator.record_database_validation(
                'onboarding_session_creation',
                user_id,
                'Session exists',
                'Session exists' if session_obj else 'Session missing'
            )
            
            return session_obj
    
    async def _validate_onboarding_step_progression(self, user_id: int, expected_step: str) -> str:
        """Validate onboarding step progression"""
        async with managed_session() as session:
            from sqlalchemy import select
            result = await session.execute(select(OnboardingSession).where(OnboardingSession.user_id == user_id))
            session_obj = result.scalar_one_or_none()
            
            actual_step = session_obj.current_step if session_obj else 'missing'
            
            self.validator.record_database_validation(
                f'step_progression_to_{expected_step}',
                user_id,
                expected_step,
                actual_step
            )
            
            return actual_step
    
    async def _validate_email_persistence(self, user_id: int, expected_email: str) -> str:
        """Validate email was persisted"""
        async with managed_session() as session:
            from sqlalchemy import select
            result = await session.execute(select(OnboardingSession).where(OnboardingSession.user_id == user_id))
            session_obj = result.scalar_one_or_none()
            
            actual_email = session_obj.email if session_obj else 'missing'
            
            self.validator.record_database_validation(
                'email_persistence',
                user_id,
                expected_email,
                actual_email
            )
            
            return actual_email
    
    async def _validate_terms_acceptance(self, user_id: int) -> bool:
        """Validate terms were accepted"""
        async with managed_session() as session:
            from sqlalchemy import select
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            terms_accepted = user.terms_accepted if user else False
            
            self.validator.record_database_validation(
                'terms_acceptance',
                user_id,
                True,
                terms_accepted
            )
            
            return terms_accepted
    
    async def test_real_onboarding_start_handler(self):
        """Test REAL /start command through onboarding_router"""
        logger.info("📱 Testing REAL /start handler")
        
        # Create REAL Telegram objects
        telegram_user = TelegramUser(
            id=self.test_user_id,
            is_bot=False,
            first_name="E2ETest",
            username="e2etest_user"
        )
        
        chat = Chat(id=self.test_user_id, type="private")
        
        message = Message(
            message_id=2001,
            date=datetime.now(),
            chat=chat,
            from_user=telegram_user,
            text="/start"
        )
        
        update = Update(
            update_id=2001,
            message=message
        )
        
        # Create REAL context
        context = await self._create_real_telegram_context()
        
        # Execute REAL onboarding_router
        start_time = time.time()
        
        try:
            await onboarding_router(update, context)
            duration = (time.time() - start_time) * 1000
            
            self.validator.record_test('onboarding_router_execution', True, f"Executed in {duration:.1f}ms")
            
            # Validate handler response
            sent_messages = self.fake_request.get_calls_by_method('sendMessage')
            response_sent = len(sent_messages) > 0
            
            self.validator.record_handler_validation(
                'onboarding_router', 
                'start_message', 
                response_sent, 
                f"Messages sent: {len(sent_messages)}"
            )
            
            # Validate database state
            user = await self._validate_database_user_creation(self.test_user_id)
            if user:
                await self._validate_onboarding_session_creation(user.id)
                await self._validate_onboarding_step_progression(user.id, OnboardingStep.CAPTURE_EMAIL.value)
            
            self.validator.record_test('start_handler_complete', True, "All validations passed")
            
        except Exception as e:
            self.validator.record_test('onboarding_router_execution', False, f"Exception: {e}")
            logger.error(f"❌ Start handler failed: {e}")
    
    async def test_real_email_input_handler(self):
        """Test REAL email input through onboarding_router"""
        logger.info("📧 Testing REAL email input handler")
        
        # First create user with start
        await self.test_real_onboarding_start_handler()
        
        # Create email input update
        telegram_user = TelegramUser(
            id=self.test_user_id,
            is_bot=False,
            first_name="E2ETest",
            username="e2etest_user"
        )
        
        chat = Chat(id=self.test_user_id, type="private")
        
        message = Message(
            message_id=2002,
            date=datetime.now(),
            chat=chat,
            from_user=telegram_user,
            text=self.test_email
        )
        
        update = Update(
            update_id=2002,
            message=message
        )
        
        # Create REAL context
        context = await self._create_real_telegram_context()
        
        # Mock email service
        with patch('services.email_verification_service.EmailVerificationService.send_otp_email') as mock_email:
            mock_email.return_value = {'success': True, 'message_id': 'E2E_TEST_EMAIL'}
            
            try:
                await onboarding_router(update, context)
                
                self.validator.record_test('email_handler_execution', True, "Email handler executed")
                
                # Validate email service was called
                email_service_called = mock_email.called
                self.validator.record_test('email_service_called', email_service_called, f"Called: {email_service_called}")
                
                # Validate database state
                user = await self._validate_database_user_creation(self.test_user_id)
                if user:
                    await self._validate_email_persistence(user.id, self.test_email)
                    await self._validate_onboarding_step_progression(user.id, OnboardingStep.VERIFY_OTP.value)
                
                self.validator.record_test('email_handler_complete', True, "All email validations passed")
                
            except Exception as e:
                self.validator.record_test('email_handler_execution', False, f"Exception: {e}")
                logger.error(f"❌ Email handler failed: {e}")
    
    async def test_real_otp_verification_handler(self):
        """Test REAL OTP verification through onboarding_router"""
        logger.info("🔢 Testing REAL OTP verification handler")
        
        # Setup: Complete email input first
        await self.test_real_email_input_handler()
        
        # Set OTP in database for verification
        async with managed_session() as session:
            from sqlalchemy import select, update as sql_update
            result = await session.execute(select(User).where(User.telegram_id == str(self.test_user_id)))
            user = result.scalar_one_or_none()
            
            if user:
                # Set OTP for verification
                await session.execute(
                    sql_update(OnboardingSession)
                    .where(OnboardingSession.user_id == user.id)
                    .values(email_otp=self.test_otp)
                )
                await session.commit()
        
        # Create OTP input update
        telegram_user = TelegramUser(
            id=self.test_user_id,
            is_bot=False,
            first_name="E2ETest",
            username="e2etest_user"
        )
        
        chat = Chat(id=self.test_user_id, type="private")
        
        message = Message(
            message_id=2003,
            date=datetime.now(),
            chat=chat,
            from_user=telegram_user,
            text=self.test_otp
        )
        
        update = Update(
            update_id=2003,
            message=message
        )
        
        # Create REAL context
        context = await self._create_real_telegram_context()
        
        try:
            await onboarding_router(update, context)
            
            self.validator.record_test('otp_handler_execution', True, "OTP handler executed")
            
            # Validate database state progression
            user = await self._validate_database_user_creation(self.test_user_id)
            if user:
                await self._validate_onboarding_step_progression(user.id, OnboardingStep.ACCEPT_TOS.value)
            
            self.validator.record_test('otp_handler_complete', True, "All OTP validations passed")
            
        except Exception as e:
            self.validator.record_test('otp_handler_execution', False, f"Exception: {e}")
            logger.error(f"❌ OTP handler failed: {e}")
    
    async def test_real_tos_acceptance_handler(self):
        """Test REAL Terms of Service acceptance through onboarding_router"""
        logger.info("📋 Testing REAL ToS acceptance handler")
        
        # Setup: Complete OTP verification first
        await self.test_real_otp_verification_handler()
        
        # Create REAL CallbackQuery for ToS acceptance
        telegram_user = TelegramUser(
            id=self.test_user_id,
            is_bot=False,
            first_name="E2ETest",
            username="e2etest_user"
        )
        
        chat = Chat(id=self.test_user_id, type="private")
        
        original_message = Message(
            message_id=2004,
            date=datetime.now(),
            chat=chat,
            from_user=telegram_user,
            text="Please accept our Terms of Service"
        )
        
        callback_query = CallbackQuery(
            id="e2e_callback_001",
            from_user=telegram_user,
            chat_instance="e2e_chat_instance",
            data=OnboardingCallbacks.TOS_ACCEPT,  # REAL callback data
            message=original_message
        )
        
        update = Update(
            update_id=2004,
            callback_query=callback_query
        )
        
        # Create REAL context
        context = await self._create_real_telegram_context()
        
        try:
            await onboarding_router(update, context)
            
            self.validator.record_test('tos_handler_execution', True, "ToS handler executed")
            
            # Validate Terms acceptance in database
            user = await self._validate_database_user_creation(self.test_user_id)
            if user:
                await self._validate_terms_acceptance(user.id)
                await self._validate_onboarding_step_progression(user.id, OnboardingStep.DONE.value)
            
            self.validator.record_test('tos_handler_complete', True, "All ToS validations passed")
            
        except Exception as e:
            self.validator.record_test('tos_handler_execution', False, f"Exception: {e}")
            logger.error(f"❌ ToS handler failed: {e}")
    
    async def test_complete_real_e2e_onboarding_flow(self):
        """
        COMPLETE REAL END-TO-END ONBOARDING FLOW TEST
        
        This test runs the complete flow: /start → email → OTP → ToS
        with REAL handlers, REAL database persistence, and REAL business logic
        """
        logger.info("🎯 Running COMPLETE REAL E2E Onboarding Flow")
        
        with patch('services.email_verification_service.EmailVerificationService.send_otp_email') as mock_email:
            mock_email.return_value = {'success': True, 'message_id': 'COMPLETE_E2E_TEST'}
            
            # Execute complete flow
            await self.test_real_onboarding_start_handler()
            await self.test_real_email_input_handler() 
            await self.test_real_otp_verification_handler()
            await self.test_real_tos_acceptance_handler()
            
            # Final validation: Complete onboarding state
            user = await self._validate_database_user_creation(self.test_user_id)
            if user:
                # Validate final state
                async with managed_session() as session:
                    from sqlalchemy import select
                    result = await session.execute(select(User).where(User.id == user.id))
                    final_user = result.scalar_one_or_none()
                    
                    if final_user:
                        # Check completion criteria
                        email_verified = final_user.email_verified
                        terms_accepted = final_user.terms_accepted
                        
                        self.validator.record_database_validation(
                            'final_email_verified', user.id, True, email_verified
                        )
                        self.validator.record_database_validation(
                            'final_terms_accepted', user.id, True, terms_accepted
                        )
                        
                        # Check onboarding session completion
                        result = await session.execute(select(OnboardingSession).where(OnboardingSession.user_id == user.id))
                        final_session = result.scalar_one_or_none()
                        
                        if final_session:
                            final_step = final_session.current_step
                            self.validator.record_database_validation(
                                'final_onboarding_step', user.id, OnboardingStep.DONE.value, final_step
                            )
            
            # Generate comprehensive summary
            summary = self.validator.get_summary()
            
            logger.info("📊 COMPLETE REAL E2E ONBOARDING TEST SUMMARY:")
            logger.info(f"   Tests: {summary['tests']['passed']}/{summary['tests']['total']} passed")
            logger.info(f"   Database Validations: {summary['database']['passed']}/{summary['database']['total']} passed")
            logger.info(f"   Handler Validations: {summary['handlers']['passed']}/{summary['handlers']['total']} passed")
            logger.info(f"   Overall Success: {summary['overall_success']}")
            
            if not summary['overall_success']:
                pytest.fail(f"E2E onboarding flow failed - Summary: {summary}")
            
            logger.info("🎉 COMPLETE REAL E2E ONBOARDING FLOW: PASSED")


if __name__ == "__main__":
    # Run the real end-to-end onboarding tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])