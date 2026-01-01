"""
E2E test for dispute button workflow
Tests the complete flow from button click to dispute display
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User as TelegramUser, CallbackQuery, Message, Chat
from telegram.ext import ContextTypes


@pytest.mark.asyncio
async def test_dispute_button_click_to_display():
    """
    E2E TEST: Click "Disputes (1)" button → Shows dispute list
    
    Flow:
    1. User clicks "⚠️ Disputes (1)" button in Messages Hub
    2. Sends callback_data="view_disputes" 
    3. handle_view_disputes processes it
    4. Shows list of disputes with "View Dispute #123" buttons
    """
    from handlers.missing_handlers import handle_view_disputes
    from models import User, Dispute, Escrow
    from database import async_managed_session
    from sqlalchemy import select
    
    # Setup: Create test data
    async with async_managed_session() as session:
        # Create test user
        stmt = select(User).where(User.telegram_id == 5590563715)
        result = await session.execute(stmt)
        test_user = result.scalar_one_or_none()
        
        if not test_user:
            test_user = User(
                telegram_id=5590563715,
                username="testuser",
                first_name="Test",
                last_name="User"
            )
            session.add(test_user)
            await session.flush()
        
        # Create test escrow
        stmt = select(Escrow).where(Escrow.escrow_id == "ES_TEST_DISPUTE")
        result = await session.execute(stmt)
        test_escrow = result.scalar_one_or_none()
        
        if not test_escrow:
            test_escrow = Escrow(
                escrow_id="ES_TEST_DISPUTE",
                buyer_id=test_user.id,
                currency="BTC",
                amount_crypto=0.001,
                status="pending"
            )
            session.add(test_escrow)
            await session.flush()
        
        # Create test dispute
        stmt = select(Dispute).where(Dispute.escrow_id == test_escrow.id)
        result = await session.execute(stmt)
        test_dispute = result.scalar_one_or_none()
        
        if not test_dispute:
            test_dispute = Dispute(
                escrow_id=test_escrow.id,
                initiator_id=test_user.id,
                reason="Test dispute for E2E testing",
                status="open"
            )
            session.add(test_dispute)
            await session.commit()
        else:
            dispute_id = test_dispute.id
    
    # Mock Telegram objects
    mock_user = MagicMock(spec=TelegramUser)
    mock_user.id = 5590563715
    mock_user.username = "testuser"
    
    mock_message = MagicMock(spec=Message)
    mock_chat = MagicMock(spec=Chat)
    mock_chat.id = 5590563715
    mock_message.chat = mock_chat
    
    mock_query = MagicMock(spec=CallbackQuery)
    mock_query.data = "view_disputes"
    mock_query.answer = AsyncMock()
    mock_query.edit_message_text = AsyncMock()
    
    update = MagicMock(spec=Update)
    update.effective_user = mock_user
    update.callback_query = mock_query
    update.message = mock_message
    
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    # Execute: Call the handler
    await handle_view_disputes(update, context)
    
    # Verify: Check that response was sent
    assert mock_query.edit_message_text.called, "❌ Handler did not send response"
    
    # Get the call arguments
    call_args = mock_query.edit_message_text.call_args
    message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
    
    # Verify message contains dispute info
    assert "Disputes" in message_text, f"❌ Message doesn't contain 'Disputes': {message_text}"
    
    # Verify reply markup has dispute buttons
    reply_markup = call_args[1].get('reply_markup')
    assert reply_markup is not None, "❌ No reply markup (buttons) in response"
    
    # Check if buttons contain view_dispute callback
    buttons_found = False
    for row in reply_markup.inline_keyboard:
        for button in row:
            if button.callback_data and "view_dispute:" in button.callback_data:
                buttons_found = True
                break
    
    assert buttons_found, "❌ No 'view_dispute:' buttons found in response"
    
    print("✅ E2E TEST PASSED: Dispute button workflow works end-to-end!")
    print(f"   - User clicked 'Disputes' button")
    print(f"   - Handler processed callback_data='view_disputes'")
    print(f"   - Response shows dispute list")
    print(f"   - Buttons include 'view_dispute:123' for next step")


@pytest.mark.asyncio
async def test_view_specific_dispute():
    """
    E2E TEST: Click "View Dispute #123" → Shows dispute details
    
    Flow:
    1. User clicks "View Dispute #123" button
    2. Sends callback_data="view_dispute:123"
    3. direct_select_dispute processes it
    4. Shows dispute details and chat
    """
    from handlers.multi_dispute_manager_direct import direct_select_dispute
    from models import User, Dispute, Escrow
    from database import async_managed_session
    from sqlalchemy import select
    
    # Get test dispute ID
    async with async_managed_session() as session:
        stmt = select(User).where(User.telegram_id == 5590563715)
        result = await session.execute(stmt)
        test_user = result.scalar_one_or_none()
        
        if test_user:
            stmt = select(Dispute).where(Dispute.initiator_id == test_user.id)
            result = await session.execute(stmt)
            test_dispute = result.scalar_one_or_none()
            
            if test_dispute:
                dispute_id = test_dispute.id
            else:
                pytest.skip("No test dispute found")
        else:
            pytest.skip("No test user found")
    
    # Mock Telegram objects
    mock_user = MagicMock(spec=TelegramUser)
    mock_user.id = 5590563715
    
    mock_query = MagicMock(spec=CallbackQuery)
    mock_query.data = f"view_dispute:{dispute_id}"
    mock_query.answer = AsyncMock()
    mock_query.edit_message_text = AsyncMock()
    
    update = MagicMock(spec=Update)
    update.effective_user = mock_user
    update.callback_query = mock_query
    
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    # Execute: Call the handler
    await direct_select_dispute(update, context)
    
    # Verify: Check that response was sent
    assert mock_query.edit_message_text.called, "❌ Handler did not send response"
    
    call_args = mock_query.edit_message_text.call_args
    message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
    
    # Verify message contains dispute details
    assert "Dispute" in message_text or "dispute" in message_text, \
        f"❌ Message doesn't contain dispute info: {message_text}"
    
    print("✅ E2E TEST PASSED: View specific dispute works!")
    print(f"   - User clicked 'View Dispute #{dispute_id}'")
    print(f"   - Handler processed callback_data='view_dispute:{dispute_id}'")
    print(f"   - Response shows dispute details")


if __name__ == "__main__":
    import asyncio
    
    print("\n🧪 Running Dispute Button E2E Tests\n")
    print("=" * 70)
    
    async def run_tests():
        await test_dispute_button_click_to_display()
        await test_view_specific_dispute()
    
    asyncio.run(run_tests())
    
    print("\n" + "=" * 70)
    print("✅ ALL E2E TESTS PASSED - Dispute button fully functional!")
    print("=" * 70)
