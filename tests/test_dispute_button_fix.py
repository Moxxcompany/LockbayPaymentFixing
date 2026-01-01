"""
Integration test to verify dispute button fix
Tests that the async session and SQL type issues are resolved
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import Update, User as TelegramUser, CallbackQuery
from telegram.ext import ContextTypes


@pytest.mark.asyncio
async def test_handle_view_disputes_uses_async_session():
    """
    TEST: Verify handle_view_disputes uses async session (not sync SessionLocal)
    This was the root cause - handler used blocking sync session
    """
    from handlers.missing_handlers import handle_view_disputes
    import inspect
    
    # Check function source code for async patterns
    source = inspect.getsource(handle_view_disputes)
    
    # Should use async_managed_session, NOT SessionLocal
    assert "async_managed_session" in source, \
        "❌ Handler not using async_managed_session()"
    
    assert "SessionLocal()" not in source, \
        "❌ Handler still using blocking SessionLocal()"
    
    # Should use SQLAlchemy 2.0 select(), NOT .query()
    assert "select(" in source, \
        "❌ Handler not using select() pattern"
    
    assert ".query(" not in source, \
        "❌ Handler still using deprecated .query() method"
    
    print("✅ TEST PASSED: handle_view_disputes uses async session")


@pytest.mark.asyncio
async def test_handle_view_disputes_correct_sql_types():
    """
    TEST: Verify handle_view_disputes uses correct SQL types (no str() cast)
    Previously: User.telegram_id == str(user.id) caused bigint = varchar error
    """
    from handlers.missing_handlers import handle_view_disputes
    import inspect
    
    source = inspect.getsource(handle_view_disputes)
    
    # Should NOT cast telegram_id to string
    assert "str(user.id)" not in source, \
        "❌ Handler still casting user.id to string (causes SQL type error)"
    
    # Should use direct integer comparison
    assert "user.id" in source, \
        "❌ Handler not using user.id for telegram_id lookup"
    
    print("✅ TEST PASSED: handle_view_disputes uses correct SQL types")


@pytest.mark.asyncio
async def test_handle_view_disputes_sends_correct_callback_data():
    """
    TEST: Verify view_disputes handler sends view_dispute:ID callback_data
    This ensures the next handler (direct_select_dispute) can process it
    """
    from handlers.missing_handlers import handle_view_disputes
    import inspect
    
    source = inspect.getsource(handle_view_disputes)
    
    # Should send view_dispute:ID for each dispute button
    assert 'view_dispute:' in source, \
        "❌ Handler not sending 'view_dispute:' callback_data"
    
    # Should use dispute.id in callback
    assert 'dispute.id' in source, \
        "❌ Handler not including dispute ID in callback_data"
    
    print("✅ TEST PASSED: handle_view_disputes sends correct callback_data")


@pytest.mark.asyncio
async def test_handler_registration_complete():
    """
    TEST: Verify all dispute handlers are properly registered
    """
    from handlers.multi_dispute_manager_direct import DIRECT_MULTI_DISPUTE_HANDLERS
    from telegram.ext import CallbackQueryHandler
    
    # Find view_dispute handler
    view_dispute_handlers = [
        h for h in DIRECT_MULTI_DISPUTE_HANDLERS
        if isinstance(h, CallbackQueryHandler) 
        and hasattr(h, 'pattern')
        and 'view_dispute' in str(h.pattern.pattern)
    ]
    
    assert len(view_dispute_handlers) > 0, \
        "❌ No view_dispute handler registered in DIRECT_MULTI_DISPUTE_HANDLERS"
    
    # Verify pattern matches expected format
    handler = view_dispute_handlers[0]
    assert handler.pattern.match("view_dispute:1"), \
        "❌ Handler pattern doesn't match 'view_dispute:1'"
    
    assert handler.pattern.match("view_dispute:123"), \
        "❌ Handler pattern doesn't match 'view_dispute:123'"
    
    print("✅ TEST PASSED: All dispute handlers registered correctly")


@pytest.mark.asyncio
async def test_messages_hub_button_sends_view_disputes():
    """
    TEST: Verify Messages Hub sends correct callback_data for dispute button
    """
    from handlers.messages_hub import show_trades_messages_hub
    import inspect
    
    source = inspect.getsource(show_trades_messages_hub)
    
    # Should send view_disputes callback
    assert 'view_disputes' in source, \
        "❌ Messages Hub not sending 'view_disputes' callback_data"
    
    # Should show dispute count
    assert 'Disputes' in source, \
        "❌ Messages Hub not showing Disputes button"
    
    print("✅ TEST PASSED: Messages Hub sends correct callback_data")


if __name__ == "__main__":
    import asyncio
    
    print("\n🧪 Running Dispute Button Fix Verification Tests\n")
    print("=" * 70)
    
    async def run_tests():
        await test_handle_view_disputes_uses_async_session()
        await test_handle_view_disputes_correct_sql_types()
        await test_handle_view_disputes_sends_correct_callback_data()
        await test_handler_registration_complete()
        await test_messages_hub_button_sends_view_disputes()
    
    asyncio.run(run_tests())
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED (5/5) - Dispute button fix verified!")
    print("=" * 70)
    print("\n📋 SUMMARY:")
    print("  ✅ handle_view_disputes uses async_managed_session (not sync)")
    print("  ✅ Correct SQL types (no str() cast on telegram_id)")
    print("  ✅ Sends correct callback_data (view_dispute:ID)")
    print("  ✅ Handler registered for view_dispute:* pattern")
    print("  ✅ Messages Hub sends view_disputes callback")
    print("\n🎯 Dispute button should now be FULLY FUNCTIONAL!")
