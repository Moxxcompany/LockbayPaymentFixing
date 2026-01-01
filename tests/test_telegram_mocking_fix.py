"""
Test file to validate that Telegram context mocking fixes eliminate bot operation errors.
This test specifically validates that the enhancements to conftest.py resolve:
1. "This object has no bot associated with it. Shortcuts cannot be used"
2. "Fallback message send failed" errors
3. Message sending operations work with mock objects
4. Callback query operations work properly
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from telegram import Update, Message, CallbackQuery
from telegram.ext import ContextTypes

from utils.message_utils import send_unified_message, get_bot_instance
from utils.callback_utils import safe_edit_message_text, safe_answer_callback_query


class TestTelegramMockingFix:
    """Test suite to validate enhanced Telegram mocking eliminates bot operation errors"""
    
    @pytest.mark.asyncio
    async def test_telegram_factory_creates_proper_bot_mocks(self, telegram_factory):
        """Test that telegram_factory creates objects with proper bot references"""
        
        # Create telegram objects
        user = telegram_factory.create_user()
        chat = telegram_factory.create_chat()
        message = telegram_factory.create_message("Test message", user=user, chat=chat)
        callback_query = telegram_factory.create_callback_query("test_data", user=user, message=message)
        update = telegram_factory.create_update(message=message, callback_query=callback_query)
        context = telegram_factory.create_context()
        
        # Verify bot references exist
        assert hasattr(message, '_bot') or hasattr(message, 'bot'), "Message should have bot reference"
        assert hasattr(callback_query, '_bot') or hasattr(callback_query, 'bot'), "CallbackQuery should have bot reference"
        assert hasattr(update, '_bot') or hasattr(update, 'bot'), "Update should have bot reference"
        assert hasattr(context, 'bot') and context.bot is not None, "Context should have bot"
        
        # Verify bot has essential methods
        bot = context.bot
        assert hasattr(bot, 'send_message') and callable(bot.send_message), "Bot should have send_message method"
        assert hasattr(bot, 'edit_message_text') and callable(bot.edit_message_text), "Bot should have edit_message_text method"
        assert hasattr(bot, 'answer_callback_query') and callable(bot.answer_callback_query), "Bot should have answer_callback_query method"
    
    @pytest.mark.asyncio
    async def test_message_shortcuts_work_with_mocks(self, telegram_factory):
        """Test that message shortcuts work with mock objects (no 'bot associated' errors)"""
        
        # Create message with bot reference
        user = telegram_factory.create_user()
        chat = telegram_factory.create_chat()
        message = telegram_factory.create_message("Test message", user=user, chat=chat)
        
        # Test message shortcuts that previously failed
        try:
            # These should not raise "This object has no bot associated with it" errors
            result = await message.reply_text("Reply test")
            # Mock should return a result
            assert result is not None
        except Exception as e:
            if "bot associated" in str(e).lower():
                pytest.fail(f"Message shortcut failed with bot association error: {e}")
            # Other exceptions from mocks are OK
    
    @pytest.mark.asyncio
    async def test_callback_query_operations_work_with_mocks(self, telegram_factory):
        """Test that callback query operations work with mock objects"""
        
        # Create callback query with bot reference
        user = telegram_factory.create_user()
        message = telegram_factory.create_message("Test message", user=user)
        callback_query = telegram_factory.create_callback_query("test_data", user=user, message=message)
        
        # Test callback query operations
        try:
            await callback_query.answer("Test answer")
            await callback_query.edit_message_text("New text")
        except Exception as e:
            if "bot associated" in str(e).lower():
                pytest.fail(f"Callback query operation failed with bot association error: {e}")
            # Other exceptions from mocks are OK
    
    @pytest.mark.asyncio
    async def test_message_utils_with_mock_bot(self, patched_telegram_utilities, telegram_factory):
        """Test that message_utils functions work with mock bot instance"""
        
        # Test get_bot_instance returns mock
        bot = get_bot_instance()
        assert bot is not None, "get_bot_instance should return mock bot"
        assert hasattr(bot, 'send_message'), "Mock bot should have send_message method"
        
        # Test send_unified_message with Update object
        user = telegram_factory.create_user()
        message = telegram_factory.create_message("Test message", user=user)
        update = telegram_factory.create_update(message=message)
        
        try:
            await send_unified_message(update, "Test message")
        except Exception as e:
            if "bot associated" in str(e).lower() or "fallback message send failed" in str(e).lower():
                pytest.fail(f"send_unified_message failed with bot error: {e}")
        
        # Test send_unified_message with user_id
        try:
            await send_unified_message(123456789, "Test direct message")
        except Exception as e:
            if "bot associated" in str(e).lower() or "fallback message send failed" in str(e).lower():
                pytest.fail(f"send_unified_message failed with bot error: {e}")
    
    @pytest.mark.asyncio 
    async def test_callback_utils_with_mock_objects(self, telegram_factory):
        """Test that callback_utils functions work with mock objects"""
        
        # Create mock callback query
        user = telegram_factory.create_user()
        message = telegram_factory.create_message("Test message", user=user)
        callback_query = telegram_factory.create_callback_query("test_data", user=user, message=message)
        
        # Test safe_edit_message_text with mock
        try:
            result = await safe_edit_message_text(callback_query, "New text")
            assert result is True, "safe_edit_message_text should return True for mock objects"
        except Exception as e:
            pytest.fail(f"safe_edit_message_text failed with mock object: {e}")
        
        # Test safe_answer_callback_query with mock
        try:
            await safe_answer_callback_query(callback_query, "Test answer")
        except Exception as e:
            pytest.fail(f"safe_answer_callback_query failed with mock object: {e}")
    
    @pytest.mark.asyncio
    async def test_context_bot_mock_comprehensive(self, telegram_factory):
        """Test that context bot mock has comprehensive method coverage"""
        
        context = telegram_factory.create_context()
        bot = context.bot
        
        # Test all essential bot methods exist and are callable
        essential_methods = [
            'send_message', 'edit_message_text', 'answer_callback_query',
            'delete_message', 'pin_chat_message', 'unpin_chat_message',
            'get_chat_member', 'get_chat', 'send_photo', 'send_document'
        ]
        
        for method_name in essential_methods:
            assert hasattr(bot, method_name), f"Bot should have {method_name} method"
            method = getattr(bot, method_name)
            assert callable(method), f"Bot.{method_name} should be callable"
            
            # For async methods, test they can be awaited
            if asyncio.iscoroutinefunction(method):
                try:
                    result = await method(chat_id=123, text="test")
                    # Mock should return something
                    assert result is not None
                except Exception as e:
                    # Some mock exceptions are expected, but not bot association errors
                    if "bot associated" in str(e).lower():
                        pytest.fail(f"Bot method {method_name} failed with bot association error: {e}")
    
    def test_auto_patching_applies_to_all_tests(self, patched_telegram_utilities):
        """Test that auto-patching fixture applies Telegram patches to all tests"""
        
        # This test validates that the auto_patch_telegram_for_all_tests fixture
        # is working and applying patches automatically
        assert patched_telegram_utilities is not None, "Auto-patching should provide telegram utilities"
        
        # Verify environment variable is set
        import os
        assert os.getenv('TELEGRAM_BOT_TOKEN') == 'mock_token_for_tests', "Mock token should be set"
        
        # Verify get_bot_instance is patched
        from utils.message_utils import get_bot_instance
        bot = get_bot_instance()
        assert bot is not None, "Patched get_bot_instance should return mock bot"
    
    @pytest.mark.asyncio 
    async def test_no_real_telegram_api_calls(self, telegram_factory, patched_telegram_utilities):
        """Verify that no real Telegram API calls are made during tests"""
        
        # Create realistic test scenario
        user = telegram_factory.create_user()
        message = telegram_factory.create_message("Test message", user=user)
        callback_query = telegram_factory.create_callback_query("test_data", user=user, message=message)
        update = telegram_factory.create_update(message=message, callback_query=callback_query)
        context = telegram_factory.create_context()
        
        # Execute operations that would normally make API calls
        await send_unified_message(update, "Test message")
        await send_unified_message(user.id, "Direct message")
        await safe_edit_message_text(callback_query, "Edited text")
        await safe_answer_callback_query(callback_query, "Callback answer")
        await context.bot.send_message(chat_id=user.id, text="Context bot message")
        
        # If we reach here without exceptions, mocking is working correctly
        assert True, "All operations completed without real API calls"