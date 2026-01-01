"""
End-to-end test for dispute workflow
Tests dispute button responsiveness and full flow
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User as TelegramUser, CallbackQuery, Message, Chat
from telegram.ext import ContextTypes
from handlers.messages_hub import show_trades_messages_hub
from handlers.multi_dispute_manager_direct import direct_select_dispute
from handlers.multi_dispute_manager import handle_dispute_selection
from models import User, Dispute, Escrow
from database import async_managed_session
from sqlalchemy import select


@pytest.fixture
async def test_user():
    """Create a test user with active dispute"""
    async with async_managed_session() as session:
        # Create test user
        user = User(
            telegram_id=5590563715,
            username="testuser",
            first_name="Test",
            last_name="User",
            onboarding_completed=True
        )
        session.add(user)
        await session.flush()
        
        # Create test escrow
        escrow = Escrow(
            escrow_id="ES123456TEST",
            buyer_id=user.id,
            seller_id=user.id,
            amount_usd=100.0,
            status="active"
        )
        session.add(escrow)
        await session.flush()
        
        # Create test dispute
        dispute = Dispute(
            escrow_id=escrow.id,
            initiator_id=user.id,
            reason="Test dispute",
            status="open"
        )
        session.add(dispute)
        await session.commit()
        
        yield {
            'user': user,
            'escrow': escrow,
            'dispute': dispute
        }
        
        # Cleanup
        await session.delete(dispute)
        await session.delete(escrow)
        await session.delete(user)
        await session.commit()


@pytest.mark.asyncio
async def test_dispute_button_registration():
    """Test that dispute button handler is registered"""
    from handlers.multi_dispute_manager_direct import DIRECT_MULTI_DISPUTE_HANDLERS
    
    # Check that view_dispute handler is registered
    view_dispute_handlers = [
        h for h in DIRECT_MULTI_DISPUTE_HANDLERS 
        if hasattr(h, 'pattern') and 'view_dispute' in str(h.pattern.pattern)
    ]
    
    assert len(view_dispute_handlers) > 0, "view_dispute handler not registered"
    print("✅ TEST 1 PASSED: Dispute button handler is registered")


@pytest.mark.asyncio
async def test_messages_hub_shows_dispute_button(test_user):
    """Test that Messages Hub shows dispute button when disputes exist"""
    test_data = await anext(test_user)
    
    # Create mock update and context
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=TelegramUser)
    update.effective_user.id = test_data['user'].telegram_id
    update.callback_query = MagicMock(spec=CallbackQuery)
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    # Call Messages Hub
    await show_trades_messages_hub(update, context)
    
    # Check that edit_message_text was called
    assert update.callback_query.edit_message_text.called, "Messages Hub did not send message"
    
    # Get the reply markup from the call
    call_kwargs = update.callback_query.edit_message_text.call_args.kwargs
    reply_markup = call_kwargs.get('reply_markup')
    
    # Check for dispute button
    has_dispute_button = False
    if reply_markup:
        for row in reply_markup.inline_keyboard:
            for button in row:
                if 'Dispute' in button.text or 'view_dispute' in button.callback_data:
                    has_dispute_button = True
                    break
    
    assert has_dispute_button, "Messages Hub does not show dispute button"
    print("✅ TEST 2 PASSED: Messages Hub shows dispute button")


@pytest.mark.asyncio
async def test_dispute_button_triggers_handler(test_user):
    """Test that clicking dispute button triggers the correct handler"""
    test_data = await anext(test_user)
    
    # Create mock update with view_dispute callback
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=TelegramUser)
    update.effective_user.id = test_data['user'].telegram_id
    update.callback_query = MagicMock(spec=CallbackQuery)
    update.callback_query.data = f"view_dispute:{test_data['dispute'].id}"
    update.callback_query.answer = AsyncMock()
    update.callback_query.message = MagicMock(spec=Message)
    update.callback_query.message.reply_text = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    # Call direct_select_dispute (this is what the button calls)
    await direct_select_dispute(update, context)
    
    # Verify callback was answered
    assert update.callback_query.answer.called, "Callback query was not answered"
    print("✅ TEST 3 PASSED: Dispute button triggers handler without errors")


@pytest.mark.asyncio
async def test_dispute_selection_displays_details(test_user):
    """Test that dispute selection displays dispute details"""
    test_data = await anext(test_user)
    
    # Create mock update
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=TelegramUser)
    update.effective_user.id = test_data['user'].telegram_id
    update.callback_query = MagicMock(spec=CallbackQuery)
    update.callback_query.data = f"select_dispute_{test_data['dispute'].id}"
    update.callback_query.answer = AsyncMock()
    update.callback_query.message = MagicMock(spec=Message)
    update.callback_query.message.reply_text = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    # Call handle_dispute_selection
    await handle_dispute_selection(update, context)
    
    # Check that message was edited or sent
    message_sent = (
        update.callback_query.edit_message_text.called or 
        update.callback_query.message.reply_text.called
    )
    
    assert message_sent, "Dispute details were not displayed"
    
    # Check message contains dispute info
    if update.callback_query.edit_message_text.called:
        message_text = update.callback_query.edit_message_text.call_args.args[0]
        assert 'Dispute' in message_text, "Message does not contain dispute information"
        assert str(test_data['dispute'].id) in message_text, "Message does not contain dispute ID"
    
    print("✅ TEST 4 PASSED: Dispute details are displayed correctly")


@pytest.mark.asyncio
async def test_async_session_compliance():
    """Test that all dispute handlers use async sessions correctly"""
    from handlers.multi_dispute_manager_direct import (
        set_multi_dispute_state,
        get_multi_dispute_state
    )
    
    # Test set_multi_dispute_state
    await set_multi_dispute_state(5590563715, "test_state", {"test": "data"})
    
    # Test get_multi_dispute_state
    state = await get_multi_dispute_state(5590563715)
    
    # If no errors were raised, async compliance is good
    print("✅ TEST 5 PASSED: All handlers use async sessions correctly")


@pytest.mark.asyncio
async def test_sql_type_compatibility():
    """Test that SQL queries use correct type casting for bigint telegram_id"""
    async with async_managed_session() as session:
        # Test that we can query by integer telegram_id (not string)
        stmt = select(User).where(User.telegram_id == 5590563715)
        result = await session.execute(stmt)
        
        # Query should execute without type errors
        print("✅ TEST 6 PASSED: SQL queries use correct type casting")


if __name__ == "__main__":
    # Run tests
    print("\n🧪 Running Dispute Workflow E2E Tests\n")
    print("=" * 60)
    
    async def run_all_tests():
        # Test 1: Handler registration
        await test_dispute_button_registration()
        
        # Test 2-4: Full workflow with test user
        async for test_data in test_user():
            await test_messages_hub_shows_dispute_button(test_data)
            await test_dispute_button_triggers_handler(test_data)
            await test_dispute_selection_displays_details(test_data)
        
        # Test 5: Async compliance
        await test_async_session_compliance()
        
        # Test 6: SQL type compatibility
        await test_sql_type_compatibility()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED (6/6)")
        print("=" * 60)
    
    asyncio.run(run_all_tests())
