"""
Telegram Bot API Fake Provider
Comprehensive test double for Telegram Bot interactions
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone
from telegram import Update, User as TelegramUser, Message, CallbackQuery, Chat
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class TelegramFakeProvider:
    """
    Comprehensive fake provider for Telegram Bot API
    
    Features:
    - Message sending simulation
    - Update/Context object factories  
    - Chat state tracking
    - Callback query handling
    - File upload simulation
    """
    
    def __init__(self):
        self.bot_token = "test_bot_token"
        self.bot_username = "TestLockBayBot"
        
        # State management
        self.sent_messages = []
        self.edited_messages = []
        self.answered_callbacks = []
        self.deleted_messages = []
        self.user_chats = {}  # user_id -> chat_data
        self.failure_mode = None  # None, "network_error", "forbidden", "rate_limit"
        
        # Message ID counter for realistic simulation
        self.message_id_counter = 1000
        
    def reset_state(self):
        """Reset fake provider state for test isolation"""
        self.sent_messages.clear()
        self.edited_messages.clear()
        self.answered_callbacks.clear()
        self.deleted_messages.clear()
        self.user_chats.clear()
        self.failure_mode = None
        self.message_id_counter = 1000
        
    def set_failure_mode(self, mode: Optional[str]):
        """Configure failure scenarios"""
        self.failure_mode = mode
    
    def _get_next_message_id(self) -> int:
        """Get next message ID for realistic simulation"""
        self.message_id_counter += 1
        return self.message_id_counter
    
    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup=None,
        parse_mode: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fake message sending
        Simulates Telegram Bot API send_message method
        """
        # Simulate failure modes
        if self.failure_mode == "network_error":
            raise Exception("Network error: Unable to connect to Telegram")
        elif self.failure_mode == "forbidden":
            raise Exception("Forbidden: bot was blocked by the user")
        elif self.failure_mode == "rate_limit":
            raise Exception("Too Many Requests: retry after 30")
            
        message_id = self._get_next_message_id()
        message_data = {
            "message_id": message_id,
            "chat_id": chat_id,
            "text": text,
            "reply_markup": reply_markup,
            "parse_mode": parse_mode,
            "timestamp": datetime.now(timezone.utc),
            **kwargs
        }
        
        self.sent_messages.append(message_data)
        
        # Return fake Message object structure
        return {
            "message_id": message_id,
            "date": int(datetime.now(timezone.utc).timestamp()),
            "chat": {"id": chat_id, "type": "private"},
            "text": text,
            "from": {
                "id": 123456789,
                "is_bot": True,
                "first_name": "LockBay",
                "username": self.bot_username
            }
        }
    
    async def edit_message_text(
        self,
        text: str,
        chat_id: Optional[int] = None,
        message_id: Optional[int] = None,
        reply_markup=None,
        parse_mode: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fake message editing
        Simulates Telegram Bot API edit_message_text method
        """
        if self.failure_mode == "network_error":
            raise Exception("Network error: Unable to connect to Telegram")
        elif self.failure_mode == "forbidden":
            raise Exception("Forbidden: bot was blocked by the user")
            
        edit_data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "new_text": text,
            "reply_markup": reply_markup,
            "parse_mode": parse_mode,
            "timestamp": datetime.now(timezone.utc),
            **kwargs
        }
        
        self.edited_messages.append(edit_data)
        
        return {
            "message_id": message_id,
            "date": int(datetime.now(timezone.utc).timestamp()),
            "chat": {"id": chat_id, "type": "private"},
            "text": text,
            "edit_date": int(datetime.now(timezone.utc).timestamp())
        }
    
    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False,
        **kwargs
    ) -> bool:
        """
        Fake callback query answering
        Simulates Telegram Bot API answer_callback_query method
        """
        if self.failure_mode == "network_error":
            raise Exception("Network error: Unable to connect to Telegram")
            
        callback_data = {
            "callback_query_id": callback_query_id,
            "text": text,
            "show_alert": show_alert,
            "timestamp": datetime.now(timezone.utc),
            **kwargs
        }
        
        self.answered_callbacks.append(callback_data)
        return True
    
    async def delete_message(self, chat_id: int, message_id: int) -> bool:
        """
        Fake message deletion
        Simulates Telegram Bot API delete_message method
        """
        if self.failure_mode == "network_error":
            raise Exception("Network error: Unable to connect to Telegram")
            
        delete_data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "timestamp": datetime.now(timezone.utc)
        }
        
        self.deleted_messages.append(delete_data)
        return True
    
    def create_update_object(
        self,
        user_id: int,
        chat_id: Optional[int] = None,
        message_text: Optional[str] = None,
        callback_data: Optional[str] = None,
        message_id: Optional[int] = None,
        first_name: str = "Test",
        last_name: str = "User",
        username: Optional[str] = None
    ) -> Update:
        """
        Factory method to create realistic Update objects for testing
        """
        if chat_id is None:
            chat_id = user_id  # Default to private chat
            
        # Create TelegramUser object
        telegram_user = TelegramUser(
            id=user_id,
            is_bot=False,
            first_name=first_name,
            last_name=last_name,
            username=username
        )
        
        # Create Chat object
        chat = Chat(id=chat_id, type=Chat.PRIVATE)
        
        update_data = {"update_id": self._get_next_message_id()}
        
        if callback_data:
            # Create CallbackQuery update
            callback_query = CallbackQuery(
                id=f"callback_{self._get_next_message_id()}",
                from_user=telegram_user,
                chat_instance="test_chat_instance",
                data=callback_data
            )
            
            # If we have message_id, create a message for the callback
            if message_id:
                message = Message(
                    message_id=message_id,
                    date=datetime.now(timezone.utc),
                    chat=chat,
                    from_user=telegram_user
                )
                callback_query._message = message
                
            update_data["callback_query"] = callback_query
        else:
            # Create Message update
            if message_id is None:
                message_id = self._get_next_message_id()
                
            # Create message data dict for Telegram Message object
            message_data = {
                "message_id": message_id,
                "date": datetime.now(timezone.utc),
                "chat": chat._to_dict(),
                "from": telegram_user._to_dict(),
            }
            
            if message_text:
                message_data["text"] = message_text
                
            # Create Message from dict data instead of directly instantiating
            from telegram import Message
            message = Message.de_json(message_data, bot=None)
            update_data["message"] = message
        
        return Update.de_json(update_data, bot=None)
    
    def create_context_object(
        self,
        user_data: Optional[Dict] = None,
        chat_data: Optional[Dict] = None,
        bot_data: Optional[Dict] = None
    ) -> ContextTypes.DEFAULT_TYPE:
        """
        Factory method to create realistic Context objects for testing
        """
        from unittest.mock import MagicMock
        
        # Create mock context with realistic structure
        context = MagicMock()
        context.user_data = user_data or {}
        context.chat_data = chat_data or {}
        context.bot_data = bot_data or {}
        
        # Mock bot methods to use our fake provider
        context.bot.send_message = self.send_message
        context.bot.edit_message_text = self.edit_message_text
        context.bot.answer_callback_query = self.answer_callback_query
        context.bot.delete_message = self.delete_message
        
        return context
    
    def get_sent_messages(self, chat_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all sent messages, optionally filtered by chat_id"""
        if chat_id:
            return [msg for msg in self.sent_messages if msg["chat_id"] == chat_id]
        return self.sent_messages.copy()
    
    def get_last_message(self, chat_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get the last sent message, optionally filtered by chat_id"""
        messages = self.get_sent_messages(chat_id)
        return messages[-1] if messages else None
    
    def get_edited_messages(self, chat_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all edited messages, optionally filtered by chat_id"""
        if chat_id:
            return [msg for msg in self.edited_messages if msg["chat_id"] == chat_id]
        return self.edited_messages.copy()
    
    def get_answered_callbacks(self) -> List[Dict[str, Any]]:
        """Get all answered callback queries"""
        return self.answered_callbacks.copy()
    
    def clear_history(self):
        """Clear all message history"""
        self.sent_messages.clear()
        self.edited_messages.clear()
        self.answered_callbacks.clear()
        self.deleted_messages.clear()


# Global instance for test patching
telegram_fake = TelegramFakeProvider()