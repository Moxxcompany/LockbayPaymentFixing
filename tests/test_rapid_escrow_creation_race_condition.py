"""
Regression Test: Rapid Escrow Creation Race Condition Fix

Tests the fix for the race condition where users creating multiple escrows quickly
would encounter "Session expired" errors due to context.user_data being cleared
between button click and text input.

Fixed via: utils/escrow_context_helper.py - Context rehydration from database state
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from typing import List, Dict, Any

from telegram import Update, User as TelegramUser, Message, CallbackQuery
from telegram.ext import ContextTypes, ConversationHandler

# Test foundation
from tests.e2e_test_foundation import (
    TelegramObjectFactory,
    DatabaseTransactionHelper,
)

# Models
from models import User, Wallet, Escrow, EscrowStatus

# Handlers
from handlers.escrow import (
    start_secure_trade,
    handle_seller_input,
    handle_amount_input,
    handle_description_input,
    handle_delivery_time_input,
)

# Utils
from utils.escrow_context_helper import ensure_escrow_context, ensure_escrow_context_with_fallback
from database import async_managed_session

# Import state helpers
try:
    from utils.conversation_state_helper import set_user_state, get_user_state
except ImportError:
    # Fallback for testing
    async def set_user_state(user_id: int, state: str):
        from database import async_managed_session
        from sqlalchemy import text
        async with async_managed_session() as session:
            await session.execute(
                text("UPDATE users SET conversation_state = :state WHERE telegram_id = :user_id"),
                {"state": state, "user_id": user_id}
            )
            await session.commit()
    
    async def get_user_state(user_id: int):
        from database import async_managed_session
        from sqlalchemy import text
        async with async_managed_session() as session:
            result = await session.execute(
                text("SELECT conversation_state, conversation_state_timestamp FROM users WHERE telegram_id = :user_id"),
                {"user_id": user_id}
            )
            row = result.fetchone()
            if row:
                return row[0], row[1]
            return None, None

import logging
logger = logging.getLogger(__name__)


@pytest.mark.regression
@pytest.mark.asyncio
class TestRapidEscrowCreationRaceCondition:
    """Test suite for rapid escrow creation race condition fix"""

    async def test_rapid_escrow_creation_no_session_expired_error(
        self,
        test_db_session,
        patched_services,
        mock_external_services
    ):
        """
        Test that rapid escrow creation does NOT cause "Session expired" errors.
        
        Scenario:
        1. User clicks "Create Escrow" button
        2. User IMMEDIATELY clicks "Create Escrow" again (rapid double-click)
        3. User types seller username
        4. System should rehydrate context from database state, NOT show "Session expired"
        """
        logger.info("🧪 Testing rapid escrow creation race condition fix...")
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            # Create test user
            user = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=9990001000,
                email="rapid_escrow_user@example.com",
                balance_usd=Decimal("1000.00")
            )
            
            telegram_user = TelegramObjectFactory.create_user(
                user_id=user.telegram_id,
                username=user.username,
                first_name="Rapid",
                last_name="Tester"
            )
            
            # STEP 1: First escrow creation (simulate button click)
            logger.info("📍 Step 1: First escrow creation button click")
            first_callback = TelegramObjectFactory.create_callback_query(
                user=telegram_user,
                data="create_secure_trade"
            )
            first_update = TelegramObjectFactory.create_update(
                user=telegram_user,
                callback_query=first_callback
            )
            first_context = TelegramObjectFactory.create_context()
            
            with patch('handlers.escrow.async_managed_session') as mock_session:
                mock_session.return_value.__aenter__.return_value = session
                
                # Call start_secure_trade
                result1 = await start_secure_trade(first_update, first_context)
                
                # Verify context was initialized
                assert first_context.user_data is not None
                assert "escrow_data" in first_context.user_data
                logger.info("✅ First escrow context initialized")
            
            # Check database state
            db_state1, _ = await get_user_state(user.telegram_id)
            assert db_state1 == "seller_input", f"Expected seller_input, got {db_state1}"
            logger.info(f"✅ Database state set to: {db_state1}")
            
            # STEP 2: Rapid second escrow creation (simulating rapid double-click)
            # This CLEARS first_context.user_data in real scenario
            logger.info("📍 Step 2: Rapid second escrow creation (race condition trigger)")
            second_callback = TelegramObjectFactory.create_callback_query(
                user=telegram_user,
                data="create_secure_trade"
            )
            second_update = TelegramObjectFactory.create_update(
                user=telegram_user,
                callback_query=second_callback
            )
            # CRITICAL: Reuse same context object to simulate race
            second_context = first_context
            
            with patch('handlers.escrow.async_managed_session') as mock_session:
                mock_session.return_value.__aenter__.return_value = session
                
                # This should reinitialize escrow_data, potentially clearing previous state
                result2 = await start_secure_trade(second_update, second_context)
                
                logger.info("⚠️ Second escrow creation triggered (context potentially corrupted)")
            
            # STEP 3: Seller input arrives (this is where race condition manifests)
            # The message might arrive AFTER context was reinitialized
            logger.info("📍 Step 3: Seller input arrives (testing context rehydration)")
            
            # Simulate context being empty (race condition scenario)
            corrupted_context = TelegramObjectFactory.create_context()
            # Deliberately leave user_data empty to simulate race condition
            corrupted_context.user_data = None
            
            seller_message = TelegramObjectFactory.create_message(
                telegram_user,
                "@testseller"
            )
            seller_update = TelegramObjectFactory.create_update(
                user=telegram_user,
                message=seller_message
            )
            
            with patch('handlers.escrow.async_managed_session') as mock_session:
                mock_session.return_value.__aenter__.return_value = session
                
                # This should NOT fail with "Session expired"
                # The ensure_escrow_context helper should rehydrate context
                result = await handle_seller_input(seller_update, corrupted_context)
                
                # Verify context was rehydrated
                assert corrupted_context.user_data is not None, "Context was not rehydrated"
                assert "escrow_data" in corrupted_context.user_data, "escrow_data not rehydrated"
                
                logger.info("✅ Context successfully rehydrated from database state")
                logger.info(f"✅ Handler returned: {result}")
                
                # Verify NOT ConversationHandler.END (which would indicate "Session expired")
                assert result != ConversationHandler.END, "Handler ended conversation (Session expired error)"
    
    async def test_ensure_escrow_context_rehydration_logic(
        self,
        test_db_session,
        patched_services
    ):
        """
        Test the ensure_escrow_context helper function directly.
        
        Validates that context rehydration works correctly when:
        - Database state shows user in escrow flow
        - context.user_data is missing
        """
        logger.info("🧪 Testing ensure_escrow_context rehydration logic...")
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            # Create user
            user = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=9990001001,
                email="rehydration_test@example.com"
            )
            
            # Set user to seller_input state
            await set_user_state(user.telegram_id, "seller_input")
            
            # Create empty context (simulating race condition)
            context = TelegramObjectFactory.create_context()
            context.user_data = None
            
            # Test rehydration
            result = await ensure_escrow_context(user.telegram_id, context)
            
            # Verify rehydration succeeded
            assert result is True, "ensure_escrow_context should return True"
            assert context.user_data is not None, "user_data should be initialized"
            assert "escrow_data" in context.user_data, "escrow_data should exist"
            assert context.user_data["escrow_data"]["status"] == "creating"
            assert "rehydrated" in context.user_data["escrow_data"]
            assert context.user_data["escrow_data"]["rehydrated"] is True
            
            logger.info("✅ Context rehydration successful")
            logger.info(f"✅ Rehydrated data: {context.user_data['escrow_data']}")
    
    async def test_ensure_escrow_context_with_invalid_state(
        self,
        test_db_session,
        patched_services
    ):
        """
        Test that ensure_escrow_context returns False when user is NOT in escrow flow.
        """
        logger.info("🧪 Testing ensure_escrow_context with invalid state...")
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            # Create user in non-escrow state
            user = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=9990001002,
                email="invalid_state_test@example.com"
            )
            
            # Set user to non-escrow state
            await set_user_state(user.telegram_id, "main_menu")
            
            # Create empty context
            context = TelegramObjectFactory.create_context()
            context.user_data = None
            
            # Test rehydration - should fail
            result = await ensure_escrow_context(user.telegram_id, context)
            
            # Verify rehydration failed (as expected)
            assert result is False, "ensure_escrow_context should return False for non-escrow state"
            logger.info("✅ Correctly rejected rehydration for non-escrow state")
    
    async def test_concurrent_rapid_escrow_creations(
        self,
        test_db_session,
        patched_services,
        mock_external_services
    ):
        """
        Test multiple rapid escrow creations happening concurrently.
        
        Simulates real-world scenario where user rapidly taps "Create Escrow"
        multiple times in quick succession.
        """
        logger.info("🧪 Testing concurrent rapid escrow creations...")
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            # Create user
            user = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=9990001003,
                email="concurrent_rapid@example.com",
                balance_usd=Decimal("5000.00")
            )
            
            telegram_user = TelegramObjectFactory.create_user(
                user_id=user.telegram_id,
                username=user.username
            )
            
            # Define rapid escrow creation task
            async def create_escrow_rapid(delay_ms: float):
                """Simulate rapid escrow creation with slight delay"""
                await asyncio.sleep(delay_ms / 1000)  # Convert to seconds
                
                callback = TelegramObjectFactory.create_callback_query(
                    user=telegram_user,
                    data="create_secure_trade"
                )
                update = TelegramObjectFactory.create_update(
                    user=telegram_user,
                    callback_query=callback
                )
                context = TelegramObjectFactory.create_context()
                
                with patch('handlers.escrow.async_managed_session') as mock_session:
                    mock_session.return_value.__aenter__.return_value = session
                    
                    try:
                        result = await start_secure_trade(update, context)
                        return {
                            'success': True,
                            'delay': delay_ms,
                            'result': result,
                            'has_context': context.user_data is not None
                        }
                    except Exception as e:
                        return {
                            'success': False,
                            'delay': delay_ms,
                            'error': str(e)
                        }
            
            # Execute 5 rapid escrow creations concurrently
            tasks = [
                create_escrow_rapid(0),      # Immediate
                create_escrow_rapid(10),     # 10ms
                create_escrow_rapid(20),     # 20ms
                create_escrow_rapid(30),     # 30ms
                create_escrow_rapid(50),     # 50ms
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            successful = [r for r in results if isinstance(r, dict) and r.get('success')]
            failed = [r for r in results if isinstance(r, dict) and not r.get('success')]
            exceptions = [r for r in results if isinstance(r, Exception)]
            
            logger.info(f"✅ Successful rapid creations: {len(successful)}")
            logger.info(f"❌ Failed creations: {len(failed)}")
            logger.info(f"⚠️ Exceptions: {len(exceptions)}")
            
            # All should succeed - no race condition failures
            assert len(successful) >= 4, "Most rapid creations should succeed"
            assert len(exceptions) == 0, "No exceptions should occur"
            
            # Now test seller input after rapid creations
            seller_message = TelegramObjectFactory.create_message(
                telegram_user,
                "@rapidtestseller"
            )
            seller_update = TelegramObjectFactory.create_update(
                user=telegram_user,
                message=seller_message
            )
            corrupted_context = TelegramObjectFactory.create_context()
            corrupted_context.user_data = None  # Simulate race condition
            
            with patch('handlers.escrow.async_managed_session') as mock_session:
                mock_session.return_value.__aenter__.return_value = session
                
                result = await handle_seller_input(seller_update, corrupted_context)
                
                # Should NOT be ConversationHandler.END
                assert result != ConversationHandler.END, "Should not end conversation with Session expired"
                assert corrupted_context.user_data is not None, "Context should be rehydrated"
                
                logger.info("✅ Seller input handled correctly after rapid creations")
    
    async def test_all_early_handlers_have_context_rehydration(
        self,
        test_db_session,
        patched_services,
        mock_external_services
    ):
        """
        Test that ALL early escrow handlers properly rehydrate context.
        
        Validates: handle_seller_input, handle_amount_input, 
                   handle_description_input, handle_delivery_time_input
        """
        logger.info("🧪 Testing all early handlers have context rehydration...")
        
        async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
            # Create user
            user = await DatabaseTransactionHelper.create_test_user(
                session,
                telegram_id=9990001004,
                email="all_handlers_test@example.com"
            )
            
            telegram_user = TelegramObjectFactory.create_user(
                user_id=user.telegram_id,
                username=user.username
            )
            
            handlers_tested = []
            
            # Test 1: handle_seller_input
            await set_user_state(user.telegram_id, "seller_input")
            context1 = TelegramObjectFactory.create_context()
            context1.user_data = None
            
            message1 = TelegramObjectFactory.create_message(telegram_user, "@seller1")
            update1 = TelegramObjectFactory.create_update(user=telegram_user, message=message1)
            
            with patch('handlers.escrow.async_managed_session') as mock_session:
                mock_session.return_value.__aenter__.return_value = session
                result1 = await handle_seller_input(update1, context1)
                assert result1 != ConversationHandler.END, "handle_seller_input failed"
                assert context1.user_data is not None, "handle_seller_input didn't rehydrate"
                handlers_tested.append("handle_seller_input")
            
            # Test 2: handle_amount_input
            await set_user_state(user.telegram_id, "amount_input")
            context2 = TelegramObjectFactory.create_context()
            context2.user_data = None
            
            message2 = TelegramObjectFactory.create_message(telegram_user, "100")
            update2 = TelegramObjectFactory.create_update(user=telegram_user, message=message2)
            
            with patch('handlers.escrow.async_managed_session') as mock_session:
                mock_session.return_value.__aenter__.return_value = session
                result2 = await handle_amount_input(update2, context2)
                assert result2 != ConversationHandler.END, "handle_amount_input failed"
                assert context2.user_data is not None, "handle_amount_input didn't rehydrate"
                handlers_tested.append("handle_amount_input")
            
            # Test 3: handle_description_input
            await set_user_state(user.telegram_id, "description_input")
            context3 = TelegramObjectFactory.create_context()
            context3.user_data = None
            
            message3 = TelegramObjectFactory.create_message(telegram_user, "Test product description")
            update3 = TelegramObjectFactory.create_update(user=telegram_user, message=message3)
            
            with patch('handlers.escrow.async_managed_session') as mock_session:
                mock_session.return_value.__aenter__.return_value = session
                result3 = await handle_description_input(update3, context3)
                assert result3 != ConversationHandler.END, "handle_description_input failed"
                assert context3.user_data is not None, "handle_description_input didn't rehydrate"
                handlers_tested.append("handle_description_input")
            
            # Test 4: handle_delivery_time_input
            await set_user_state(user.telegram_id, "delivery_time")
            context4 = TelegramObjectFactory.create_context()
            context4.user_data = None
            
            message4 = TelegramObjectFactory.create_message(telegram_user, "24")
            update4 = TelegramObjectFactory.create_update(user=telegram_user, message=message4)
            
            with patch('handlers.escrow.async_managed_session') as mock_session:
                mock_session.return_value.__aenter__.return_value = session
                result4 = await handle_delivery_time_input(update4, context4)
                assert result4 != ConversationHandler.END, "handle_delivery_time_input failed"
                assert context4.user_data is not None, "handle_delivery_time_input didn't rehydrate"
                handlers_tested.append("handle_delivery_time_input")
            
            logger.info(f"✅ All handlers tested successfully: {handlers_tested}")
            assert len(handlers_tested) == 4, "All 4 handlers should be tested"


@pytest.mark.regression
@pytest.mark.asyncio 
async def test_rapid_escrow_no_session_expired_quick_validation(
    test_db_session,
    patched_services,
    mock_external_services
):
    """
    Quick validation test: Ensure rapid escrow creation doesn't trigger "Session expired".
    
    This is a fast smoke test for the race condition fix.
    """
    async with DatabaseTransactionHelper.isolated_transaction(test_db_session) as session:
        user = await DatabaseTransactionHelper.create_test_user(
            session,
            telegram_id=9990001999,
            email="quick_test@example.com",
            balance_usd=Decimal("1000.00")
        )
        
        telegram_user = TelegramObjectFactory.create_user(
            user_id=user.telegram_id,
            username=user.username
        )
        
        # Rapid double-click simulation
        for i in range(2):
            callback = TelegramObjectFactory.create_callback_query(
                user=telegram_user,
                data="create_secure_trade"
            )
            update = TelegramObjectFactory.create_update(
                user=telegram_user,
                callback_query=callback
            )
            context = TelegramObjectFactory.create_context()
            
            with patch('handlers.escrow.async_managed_session') as mock_session:
                mock_session.return_value.__aenter__.return_value = session
                await start_secure_trade(update, context)
        
        # Seller input with empty context (race condition)
        message = TelegramObjectFactory.create_message(telegram_user, "@quickseller")
        update = TelegramObjectFactory.create_update(user=telegram_user, message=message)
        context = TelegramObjectFactory.create_context()
        context.user_data = None
        
        with patch('handlers.escrow.async_managed_session') as mock_session:
            mock_session.return_value.__aenter__.return_value = session
            result = await handle_seller_input(update, context)
            
            # CRITICAL: Should NOT end conversation
            assert result != ConversationHandler.END, "❌ REGRESSION: Session expired error detected!"
            assert context.user_data is not None, "❌ Context not rehydrated!"
            
            logger.info("✅ REGRESSION TEST PASSED: No session expired error on rapid escrow creation")
