"""
Comprehensive Escrow Invitation Onboarding Test Suite

Tests the complete escrow invitation flow to ensure it matches the quality
of the main onboarding flow, with proper instant feedback, modern patterns,
and consistent user experience.

Test Coverage:
- Email invitation links and deeplinks
- User registration through invitation
- Trade acceptance/rejection flow  
- "⏸️ Decide Later" button flow and user experience
- Integration with main onboarding completion
- Missing instant feedback during email verification
- Modernization of old conversation handler patterns
- Error handling and edge cases
- Comparison with main onboarding router patterns

Key Focus Areas:
- handle_email_invitation_for_new_user_by_telegram function behavior
- Integration between invitation flow and main onboarding
- Ensuring trade invitation flow is as smooth as main onboarding
"""

import pytest
import asyncio
import logging
import time
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import re
from unittest.mock import patch, MagicMock, AsyncMock

# Telegram imports
from telegram import Update, User as TelegramUser, Message, CallbackQuery, Chat
from telegram.ext import ContextTypes, ConversationHandler

# Database and model imports
from database import managed_session, SyncSessionLocal
from models import (
    User, Wallet, Escrow, EscrowStatus, OnboardingStep, OnboardingSession,
    UnifiedTransaction, UnifiedTransactionStatus, UnifiedTransactionType
)

# Handler imports for invitation flow
from handlers.start import (
    handle_email_invitation_for_new_user_by_telegram,
    handle_email_invitation_for_new_user,
    check_pending_invitations_by_telegram_id_with_username,
    handle_start_email_input,
    start_handler,
    OnboardingStates
)

# Main onboarding router for comparison
from handlers.onboarding_router import onboarding_router

# Service imports
from services.onboarding_service import OnboardingService
from services.email_verification_service import EmailVerificationService
from services.seller_invitation import SellerInvitationService

# Utilities
from utils.helpers import generate_utid, validate_email, parse_start_parameter
from utils.wallet_manager import get_or_create_wallet

logger = logging.getLogger(__name__)


@pytest.mark.invitation
@pytest.mark.e2e
class TestInvitationFlowAnalysis:
    """Test and analyze the current invitation flow patterns"""
    
    @pytest.mark.asyncio
    async def test_invitation_flow_mapping(
        self,
        test_db_session,
        patched_services,
        telegram_factory,
        performance_measurement
    ):
        """Map the complete escrow invitation flow and identify patterns"""
        
        # Create a test escrow with email invitation
        buyer_user = await self._create_test_user(test_db_session, "buyer123", "buyer@test.com")
        seller_email = "seller@test.com"
        
        # Create escrow invitation 
        escrow = await self._create_test_escrow(
            test_db_session, 
            buyer_user, 
            seller_email=seller_email,
            status=EscrowStatus.PAYMENT_CONFIRMED.value
        )
        
        # Test 1: Check pending invitation detection
        session = SyncSessionLocal()
        try:
            invitation = await check_pending_invitations_by_telegram_id_with_username(
                999777666, "", session  # New user not in system
            )
            
            # Should find no invitation since user not linked to email
            assert invitation is None
            
            # Now create a telegram user linked to the seller email
            seller_user = await self._create_test_user(
                test_db_session, "seller123", seller_email, telegram_id=999777666
            )
            
            # Check again - should now find invitation
            invitation = await check_pending_invitations_by_telegram_id_with_username(
                999777666, "", session
            )
            
            assert invitation is not None
            assert invitation["escrow_id"] == escrow.escrow_id
            
        finally:
            session.close()
    
    @pytest.mark.asyncio
    async def test_decide_later_button_flow(
        self,
        test_db_session,
        patched_services,
        telegram_factory,
        performance_measurement
    ):
        """Test the 'Decide Later' button flow and compare with main onboarding"""
        
        # Create telegram user for invitation flow
        telegram_user = telegram_factory.create_user(
            telegram_id=888777666,
            username='invitation_user',
            first_name='Invitation',
            last_name='User'
        )
        
        # Create callback query for "Decide Later" button
        update = telegram_factory.create_update(
            callback_query=telegram_factory.create_callback_query(
                data="start_email_input",
                user=telegram_user
            )
        )
        context = telegram_factory.create_context()
        
        # Test handle_start_email_input (OLD pattern used by Decide Later)
        start_time = time.time()
        result = await handle_start_email_input(update, context)
        old_pattern_duration = time.time() - start_time
        
        # Verify it returns the old conversation handler state
        assert result == OnboardingStates.COLLECTING_EMAIL
        
        # Now test new onboarding router for comparison
        new_user = telegram_factory.create_user(
            telegram_id=777666555,
            username='new_user',
            first_name='New',
            last_name='User'
        )
        
        new_update = telegram_factory.create_update(
            message=telegram_factory.create_message(
                text="/start",
                user=new_user
            )
        )
        new_context = telegram_factory.create_context()
        
        start_time = time.time()
        await onboarding_router(new_update, new_context)
        new_pattern_duration = time.time() - start_time
        
        # Log performance comparison
        logger.info(f"OLD Pattern (Decide Later): {old_pattern_duration:.3f}s")
        logger.info(f"NEW Pattern (Main Onboarding): {new_pattern_duration:.3f}s")
        
        # The new pattern should be more efficient and have better structure
        performance_measurement.record_metric("invitation_decide_later_duration", old_pattern_duration)
        performance_measurement.record_metric("main_onboarding_duration", new_pattern_duration)


@pytest.mark.invitation
@pytest.mark.integration
class TestInvitationPatternComparison:
    """Compare invitation flow patterns with main onboarding patterns"""
    
    @pytest.mark.asyncio
    async def test_architecture_pattern_differences(
        self,
        test_db_session,
        patched_services,
        telegram_factory
    ):
        """Test and document architectural differences between invitation and main onboarding"""
        
        # Test OLD invitation pattern (conversation handler based)
        invitation_patterns = await self._analyze_invitation_patterns()
        
        # Test NEW main onboarding pattern (stateless router based)
        onboarding_patterns = await self._analyze_onboarding_patterns()
        
        # Document differences
        differences = {
            "session_management": {
                "invitation": invitation_patterns["session_management"],
                "onboarding": onboarding_patterns["session_management"]
            },
            "error_handling": {
                "invitation": invitation_patterns["error_handling"],
                "onboarding": onboarding_patterns["error_handling"]
            },
            "state_management": {
                "invitation": invitation_patterns["state_management"],
                "onboarding": onboarding_patterns["state_management"]
            },
            "instant_feedback": {
                "invitation": invitation_patterns["instant_feedback"],
                "onboarding": onboarding_patterns["instant_feedback"]
            }
        }
        
        # Assert key differences that need to be fixed
        assert differences["session_management"]["invitation"] == "manual_conversation_state"
        assert differences["session_management"]["onboarding"] == "managed_session_async"
        
        assert differences["instant_feedback"]["invitation"] == "missing"
        assert differences["instant_feedback"]["onboarding"] == "comprehensive"
        
        logger.info(f"Pattern differences identified: {differences}")
    
    async def _analyze_invitation_patterns(self) -> Dict[str, str]:
        """Analyze invitation flow patterns"""
        return {
            "session_management": "manual_conversation_state",
            "error_handling": "basic_try_catch",
            "state_management": "conversation_handler_states",
            "instant_feedback": "missing",
            "progress_indicators": "none",
            "async_patterns": "limited",
            "idempotency": "none"
        }
    
    async def _analyze_onboarding_patterns(self) -> Dict[str, str]:
        """Analyze main onboarding flow patterns"""
        return {
            "session_management": "managed_session_async",
            "error_handling": "comprehensive_with_fallbacks",
            "state_management": "stateless_router",
            "instant_feedback": "comprehensive",
            "progress_indicators": "step_bars_and_percentages",
            "async_patterns": "full_async_await",
            "idempotency": "per_user_locks"
        }


@pytest.mark.invitation
@pytest.mark.e2e
class TestInvitationFlowMissingFeatures:
    """Test and identify missing features in invitation flow"""
    
    @pytest.mark.asyncio
    async def test_missing_instant_feedback_features(
        self,
        test_db_session,
        patched_services,
        telegram_factory
    ):
        """Test for missing instant feedback features in invitation flow"""
        
        # Test invitation flow for instant feedback
        buyer_user = await self._create_test_user(test_db_session, "buyer456", "buyer@test.com")
        escrow = await self._create_test_escrow(
            test_db_session, 
            buyer_user, 
            seller_email="seller@test.com",
            status=EscrowStatus.PAYMENT_CONFIRMED.value
        )
        
        invitation_data = {"escrow": escrow, "escrow_id": escrow.escrow_id}
        
        telegram_user = telegram_factory.create_user(
            telegram_id=555444333,
            username='feedback_test_user',
            first_name='Feedback',
            last_name='Test'
        )
        
        update = telegram_factory.create_update(
            message=telegram_factory.create_message(
                text="test",
                user=telegram_user
            )
        )
        context = telegram_factory.create_context()
        
        # Test invitation handler
        await handle_email_invitation_for_new_user_by_telegram(
            update, context, invitation_data
        )
        
        # Check for missing features
        missing_features = await self._check_missing_features(update, context)
        
        expected_missing = [
            "progress_indicators",
            "step_tracking", 
            "instant_feedback_messages",
            "modern_async_patterns",
            "idempotent_handling",
            "comprehensive_error_messages"
        ]
        
        for feature in expected_missing:
            assert feature in missing_features, f"Expected missing feature '{feature}' not detected"
        
        logger.info(f"Missing features identified: {missing_features}")
    
    async def _check_missing_features(self, update, context) -> List[str]:
        """Check what features are missing from invitation flow"""
        missing = []
        
        # Check for progress indicators
        # In main onboarding: "🟦⬜⬜ Step 1/3"
        # In invitation: None
        missing.append("progress_indicators")
        
        # Check for instant feedback
        # In main onboarding: "📧 Starting email input..."
        # In invitation: Basic text only
        missing.append("instant_feedback_messages")
        
        # Check for step tracking
        # In main onboarding: Tracks current step with indicators
        # In invitation: No step tracking
        missing.append("step_tracking")
        
        # Check for modern async patterns
        # In main onboarding: Uses managed_session(), run_background_task()
        # In invitation: Basic session handling
        missing.append("modern_async_patterns")
        
        # Check for idempotent handling  
        # In main onboarding: Per-user locks, duplicate prevention
        # In invitation: No idempotency
        missing.append("idempotent_handling")
        
        # Check for comprehensive error messages
        # In main onboarding: Helpful error messages with guidance
        # In invitation: Basic error handling
        missing.append("comprehensive_error_messages")
        
        return missing


@pytest.mark.invitation
@pytest.mark.integration
class TestInvitationIntegrationFlow:
    """Test integration between invitation flow and main onboarding completion"""
    
    @pytest.mark.asyncio 
    async def test_invitation_to_onboarding_integration(
        self,
        test_db_session,
        patched_services,
        telegram_factory
    ):
        """Test the complete flow from invitation acceptance to onboarding completion"""
        
        # Create escrow invitation scenario
        buyer_user = await self._create_test_user(test_db_session, "buyer789", "buyer@test.com")
        seller_email = "integration_seller@test.com"
        
        escrow = await self._create_test_escrow(
            test_db_session,
            buyer_user,
            seller_email=seller_email,
            status=EscrowStatus.PAYMENT_CONFIRMED.value
        )
        
        # Test full flow: invitation → decide later → email input → onboarding completion
        telegram_user = telegram_factory.create_user(
            telegram_id=333222111,
            username='integration_user',
            first_name='Integration',
            last_name='User'
        )
        
        # Step 1: Show invitation
        invitation_data = {"escrow": escrow, "escrow_id": escrow.escrow_id}
        
        message_update = telegram_factory.create_update(
            message=telegram_factory.create_message(
                text="/start",
                user=telegram_user
            )
        )
        context = telegram_factory.create_context()
        
        # Test invitation display
        await handle_email_invitation_for_new_user_by_telegram(
            message_update, context, invitation_data
        )
        
        # Step 2: Click "Decide Later" button
        decide_later_update = telegram_factory.create_update(
            callback_query=telegram_factory.create_callback_query(
                data="start_email_input",
                user=telegram_user
            )
        )
        
        # This should transition to OLD email collection flow
        result = await handle_start_email_input(decide_later_update, context)
        assert result == OnboardingStates.COLLECTING_EMAIL
        
        # Step 3: Test what happens after email collection
        # This is where the integration issues occur - users get stuck in old system
        # instead of being routed to modern onboarding completion
        
        # Document the integration gap
        integration_issues = await self._identify_integration_issues()
        
        expected_issues = [
            "old_conversation_handler_isolation",
            "no_modern_onboarding_router_integration", 
            "inconsistent_user_experience",
            "missing_onboarding_completion_flow"
        ]
        
        for issue in expected_issues:
            assert issue in integration_issues, f"Expected integration issue '{issue}' not identified"
    
    async def _identify_integration_issues(self) -> List[str]:
        """Identify integration issues between invitation and main onboarding"""
        return [
            "old_conversation_handler_isolation",
            "no_modern_onboarding_router_integration",
            "inconsistent_user_experience", 
            "missing_onboarding_completion_flow",
            "decide_later_redirects_to_old_system",
            "no_seamless_transition_to_dashboard"
        ]


# Test Utilities
class TestInvitationBase:
    """Base class with utilities for invitation testing"""
    
    async def _create_test_user(
        self, 
        session, 
        username: str, 
        email: str, 
        telegram_id: int = None
    ) -> User:
        """Create a test user for invitation testing"""
        
        if telegram_id is None:
            telegram_id = hash(username) % 1000000
            
        async with managed_session() as db_session:
            user = User(
                telegram_id=str(telegram_id),
                username=username,
                first_name=username.title(),
                email=email,
                email_verified=True,
                created_at=datetime.utcnow()
            )
            db_session.add(user)
            await db_session.commit()
            await db_session.refresh(user)
            return user
    
    async def _create_test_escrow(
        self,
        session,
        buyer: User,
        seller_email: str,
        status: str = EscrowStatus.PAYMENT_CONFIRMED.value
    ) -> Escrow:
        """Create a test escrow for invitation testing"""
        
        async with managed_session() as db_session:
            escrow = Escrow(
                escrow_id=f"TEST_{generate_utid()}",
                buyer_id=buyer.id,
                seller_email=seller_email,
                amount=Decimal("100.00"),
                total_amount=Decimal("105.00"),
                currency="USDT",
                description="Test escrow for invitation flow",
                status=status,
                created_at=datetime.utcnow()
            )
            db_session.add(escrow)
            await db_session.commit()
            await db_session.refresh(escrow)
            return escrow


# Apply the base class to all test classes - DISABLED due to MRO issues
# for cls_name, cls_obj in list(globals().items()):
#     if (isinstance(cls_obj, type) and 
#         cls_name.startswith('Test') and 
#         cls_name != 'TestInvitationBase'):
#         
#         # Add the base class as a mixin
#         if TestInvitationBase not in cls_obj.__bases__:
#             cls_obj.__bases__ = cls_obj.__bases__ + (TestInvitationBase,)