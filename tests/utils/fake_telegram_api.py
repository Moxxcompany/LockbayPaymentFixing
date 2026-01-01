"""
FakeRequest harness for testing real Telegram bot interactions without external dependencies.
Captures outbound Bot API calls and provides helpers for simulating button clicks.
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Union
from unittest.mock import Mock
from datetime import datetime

from telegram import (
    Update, Message, User as TelegramUser, Chat, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
)
from telegram.request import BaseRequest


class FakeRequest:
    """
    Fake HTTP request handler that captures all outbound Bot API calls
    and returns deterministic responses for testing.
    """
    
    def __init__(self):
        self.calls = []  # Store all API calls
        self.responses = {}  # Predefined responses
        self.message_counter = 1000  # Auto-increment message IDs
        
    async def post(
        self,
        url: str,
        request_data: Optional[Dict[str, Any]] = None,
        read_timeout: Optional[float] = None,
        write_timeout: Optional[float] = None,
        connect_timeout: Optional[float] = None,
        pool_timeout: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Capture outbound API calls and return fake responses"""
        
        data = request_data or {}
        
        # Store the call for inspection
        call_record = {
            'endpoint': url,
            'data': data,
            'timestamp': datetime.now(),
            'method': self._extract_method(url)
        }
        self.calls.append(call_record)
        
        # Generate appropriate response based on method
        method = call_record['method']
        
        if method == 'sendMessage':
            message_id = self.message_counter
            self.message_counter += 1
            
            return {
                'ok': True,
                'result': {
                    'message_id': message_id,
                    'date': int(datetime.now().timestamp()),
                    'chat': {
                        'id': data.get('chat_id', 12345),
                        'type': 'private'
                    },
                    'from': {
                        'id': 987654321,
                        'is_bot': True,
                        'first_name': 'TestBot'
                    },
                    'text': data.get('text', ''),
                    'reply_markup': data.get('reply_markup')
                }
            }
            
        elif method == 'editMessageText':
            return {
                'ok': True,
                'result': {
                    'message_id': data.get('message_id', 1001),
                    'date': int(datetime.now().timestamp()),
                    'chat': {
                        'id': data.get('chat_id', 12345),
                        'type': 'private'
                    },
                    'from': {
                        'id': 987654321,
                        'is_bot': True,
                        'first_name': 'TestBot'
                    },
                    'text': data.get('text', ''),
                    'reply_markup': data.get('reply_markup')
                }
            }
            
        elif method == 'editMessageReplyMarkup':
            return {
                'ok': True,
                'result': {
                    'message_id': data.get('message_id', 1001),
                    'date': int(datetime.now().timestamp()),
                    'chat': {
                        'id': data.get('chat_id', 12345),
                        'type': 'private'
                    },
                    'reply_markup': data.get('reply_markup')
                }
            }
            
        elif method == 'answerCallbackQuery':
            return {
                'ok': True,
                'result': True
            }
            
        else:
            # Default response for other methods
            return {
                'ok': True,
                'result': {}
            }
    
    def _extract_method(self, endpoint: str) -> str:
        """Extract API method name from endpoint"""
        if '/' in endpoint:
            return endpoint.split('/')[-1]
        return endpoint
    
    def get_calls_by_method(self, method: str) -> List[Dict[str, Any]]:
        """Get all calls for a specific API method"""
        return [call for call in self.calls if call['method'] == method]
    
    def get_last_call(self, method: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the most recent call, optionally filtered by method"""
        if method:
            calls = self.get_calls_by_method(method)
            return calls[-1] if calls else None
        return self.calls[-1] if self.calls else None
    
    def get_last_message(self) -> Optional[Dict[str, Any]]:
        """Get the last sent message"""
        return self.get_last_call('sendMessage')
    
    def get_last_keyboard(self) -> Optional[InlineKeyboardMarkup]:
        """Get the last sent inline keyboard"""
        last_msg = self.get_last_message()
        if last_msg and 'reply_markup' in last_msg['data']:
            return last_msg['data']['reply_markup']
        return None
    
    def clear_calls(self):
        """Clear all recorded calls"""
        self.calls = []


class TelegramUITestHelper:
    """
    Helper class for simulating Telegram UI interactions using FakeRequest
    """
    
    def __init__(self, fake_request: FakeRequest):
        self.fake_request = fake_request
        self.user_id = 12345
        self.chat_id = 12345
        self.callback_query_counter = 2000
        
    def create_user_update(self, text: str, user_id: Optional[int] = None) -> Update:
        """Create an Update representing a user message"""
        user_id = user_id or self.user_id
        
        telegram_user = TelegramUser(
            id=user_id,
            is_bot=False,
            first_name="TestUser",
            username="testuser"
        )
        
        chat = Chat(
            id=self.chat_id,
            type=Chat.PRIVATE
        )
        
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=chat,
            from_user=telegram_user,
            text=text
        )
        
        return Update(
            update_id=1,
            message=message
        )
    
    def create_callback_query_update(
        self, 
        callback_data: str, 
        message_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> Update:
        """Create an Update representing a button click (callback query)"""
        user_id = user_id or self.user_id
        message_id = message_id or 1001
        
        telegram_user = TelegramUser(
            id=user_id,
            is_bot=False,
            first_name="TestUser",
            username="testuser"
        )
        
        chat = Chat(
            id=self.chat_id,
            type=Chat.PRIVATE
        )
        
        # Create the original message that had the button
        original_message = Message(
            message_id=message_id,
            date=datetime.now(),
            chat=chat,
            from_user=telegram_user,
            text="Original message with buttons"
        )
        
        callback_query = CallbackQuery(
            id=str(self.callback_query_counter),
            from_user=telegram_user,
            chat_instance="test_chat_instance",
            message=original_message,
            data=callback_data
        )
        
        self.callback_query_counter += 1
        
        return Update(
            update_id=2,
            callback_query=callback_query
        )
    
    def click_inline_button(
        self, 
        button_text: Optional[str] = None,
        callback_data: Optional[str] = None,
        message_id: Optional[int] = None
    ) -> Update:
        """
        Click an inline keyboard button by text or callback_data.
        Returns the Update that would be sent to the bot.
        """
        keyboard = self.fake_request.get_last_keyboard()
        
        if not keyboard:
            raise ValueError("No keyboard found in last message")
        
        # Find the button by text or callback_data
        found_callback_data = None
        
        if isinstance(keyboard, dict) and 'inline_keyboard' in keyboard:
            # Handle raw dict format
            inline_kb = keyboard.get('inline_keyboard', [])
            if isinstance(inline_kb, list):
                for row in inline_kb:
                    if isinstance(row, list):
                        for button in row:
                            if button_text and button.get('text') == button_text:
                                found_callback_data = button.get('callback_data')
                                break
                            elif callback_data and button.get('callback_data') == callback_data:
                                found_callback_data = callback_data
                                break
                    if found_callback_data:
                        break
        elif hasattr(keyboard, 'inline_keyboard'):
            # Handle InlineKeyboardMarkup object
            for row in keyboard.inline_keyboard:
                for button in row:
                    if button_text and button.text == button_text:
                        found_callback_data = str(button.callback_data or '')
                        break
                    elif callback_data and button.callback_data == callback_data:
                        found_callback_data = str(callback_data)
                        break
                if found_callback_data:
                    break
        
        if not found_callback_data:
            available_buttons = self._extract_button_info(keyboard)
            raise ValueError(
                f"Button not found. Available buttons: {available_buttons}. "
                f"Searched for text='{button_text}' or callback_data='{callback_data}'"
            )
        
        return self.create_callback_query_update(found_callback_data, message_id)
    
    def _extract_button_info(self, keyboard) -> List[Dict[str, str]]:
        """Extract button information for debugging"""
        buttons = []
        
        if isinstance(keyboard, dict) and 'inline_keyboard' in keyboard:
            for row in keyboard['inline_keyboard']:
                for button in row:
                    buttons.append({
                        'text': button.get('text', ''),
                        'callback_data': button.get('callback_data', '')
                    })
        elif hasattr(keyboard, 'inline_keyboard'):
            for row in keyboard.inline_keyboard:
                for button in row:
                    buttons.append({
                        'text': str(button.text),
                        'callback_data': str(button.callback_data or '')
                    })
        
        return buttons
    
    def get_sent_text(self) -> str:
        """Get the text of the last sent message"""
        last_call = self.fake_request.get_last_call('sendMessage')
        if last_call:
            return last_call['data'].get('text', '')
        return ''
    
    def get_sent_buttons(self) -> List[Dict[str, str]]:
        """Get information about buttons in the last sent message"""
        keyboard = self.fake_request.get_last_keyboard()
        if keyboard:
            return self._extract_button_info(keyboard)
        return []
    
    def assert_message_contains(self, text: str):
        """Assert that the last sent message contains specific text"""
        sent_text = self.get_sent_text()
        assert text in sent_text, f"Expected '{text}' in message, got: '{sent_text}'"
    
    def assert_button_exists(self, button_text: str):
        """Assert that a button with specific text exists"""
        buttons = self.get_sent_buttons()
        button_texts = [btn['text'] for btn in buttons]
        assert button_text in button_texts, f"Button '{button_text}' not found. Available: {button_texts}"