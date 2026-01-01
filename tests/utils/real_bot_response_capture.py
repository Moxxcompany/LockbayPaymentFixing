"""
Real Bot Response Capture Utility

This utility actually captures bot responses by polling getUpdates or using webhook capture,
allowing smoke tests to validate real bot behavior instead of just timing.
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from telegram import Bot, Update
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class RealBotResponseCapture:
    """
    Captures actual bot responses using getUpdates polling
    """
    
    def __init__(self, bot: Bot, chat_id: int):
        self.bot = bot
        self.chat_id = chat_id
        self.last_update_id = 0
        self.captured_messages = []
        
    async def send_and_capture_response(
        self, 
        text: str, 
        timeout: float = 10.0,
        expect_buttons: bool = False
    ) -> Dict[str, Any]:
        """Send message and capture actual bot response"""
        start_time = time.time()
        
        try:
            # Send message to bot
            sent_message = await self.bot.send_message(
                chat_id=self.chat_id,
                text=text
            )
            
            # Poll for bot response
            response = await self._poll_for_response(timeout)
            
            response_time = (time.time() - start_time) * 1000
            
            result = {
                'success': response is not None,
                'sent_message_id': sent_message.message_id,
                'response_time_ms': response_time,
                'response': response,
            }
            
            if response:
                result.update({
                    'response_text': response.get('text', ''),
                    'has_keyboard': response.get('reply_markup') is not None,
                    'keyboard_buttons': self._extract_button_texts(response.get('reply_markup')),
                    'message_id': response.get('message_id')
                })
                
                # Validate expected behavior
                if expect_buttons and not result['has_keyboard']:
                    result['validation_error'] = 'Expected buttons but none found'
                    result['success'] = False
                    
            return result
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return {
                'success': False,
                'error': str(e),
                'response_time_ms': response_time
            }
    
    async def _poll_for_response(self, timeout: float) -> Optional[Dict[str, Any]]:
        """Poll getUpdates for bot response"""
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            try:
                # Get updates from Telegram
                updates = await self.bot.get_updates(
                    offset=self.last_update_id + 1,
                    timeout=2,
                    allowed_updates=['message', 'callback_query']
                )
                
                for update in updates:
                    self.last_update_id = max(self.last_update_id, update.update_id)
                    
                    # Look for bot messages to our chat
                    if (update.message and 
                        update.message.chat.id == self.chat_id and 
                        update.message.from_user.is_bot):
                        
                        return {
                            'message_id': update.message.message_id,
                            'text': update.message.text or '',
                            'reply_markup': update.message.reply_markup.to_dict() if update.message.reply_markup else None,
                            'timestamp': update.message.date
                        }
                        
                await asyncio.sleep(0.5)  # Poll every 500ms
                
            except Exception as e:
                logger.warning(f"Polling error: {e}")
                await asyncio.sleep(1)
                
        return None
    
    def _extract_button_texts(self, reply_markup: Optional[Dict]) -> List[str]:
        """Extract button texts from reply markup"""
        if not reply_markup or 'inline_keyboard' not in reply_markup:
            return []
            
        buttons = []
        for row in reply_markup['inline_keyboard']:
            for button in row:
                if 'text' in button:
                    buttons.append(button['text'])
                    
        return buttons
        
    async def validate_response_content(
        self, 
        response: Dict[str, Any], 
        expected_keywords: List[str] = None,
        expected_buttons: List[str] = None
    ) -> Dict[str, Any]:
        """Validate response content against expectations"""
        validation = {
            'valid': True,
            'issues': []
        }
        
        response_text = response.get('response_text', '').lower()
        
        # Check for expected keywords
        if expected_keywords:
            missing_keywords = [kw for kw in expected_keywords if kw.lower() not in response_text]
            if missing_keywords:
                validation['issues'].append(f"Missing keywords: {missing_keywords}")
                validation['valid'] = False
                
        # Check for expected buttons
        if expected_buttons:
            actual_buttons = [btn.lower() for btn in response.get('keyboard_buttons', [])]
            missing_buttons = [btn for btn in expected_buttons if btn.lower() not in ' '.join(actual_buttons)]
            if missing_buttons:
                validation['issues'].append(f"Missing buttons: {missing_buttons}")
                validation['valid'] = False
                
        return validation


class StagingEnvironmentGuard:
    """
    Safety guard to prevent accidental production testing
    """
    
    STAGING_TOKEN_PREFIXES = ['staging', 'test', 'dev']
    PRODUCTION_INDICATORS = ['prod', 'live', 'main']
    
    @classmethod
    def validate_staging_environment(cls, bot_token: str, chat_id: str) -> Dict[str, Any]:
        """Validate that we're in a safe staging environment"""
        issues = []
        
        # Check token prefix
        token_lower = bot_token.lower()
        is_staging_token = any(prefix in token_lower for prefix in cls.STAGING_TOKEN_PREFIXES)
        is_production_token = any(indicator in token_lower for indicator in cls.PRODUCTION_INDICATORS)
        
        if is_production_token:
            issues.append("CRITICAL: Production token detected in bot token")
            
        if not is_staging_token:
            issues.append("WARNING: Bot token doesn't contain staging indicators")
            
        # Validate chat ID is in test range (avoid real user chats)
        try:
            chat_id_int = int(chat_id)
            if chat_id_int > 0:  # Positive IDs are typically real users
                issues.append("WARNING: Positive chat ID detected (may be real user)")
        except ValueError:
            issues.append("ERROR: Invalid chat ID format")
            
        return {
            'safe': len([i for i in issues if 'CRITICAL' in i or 'ERROR' in i]) == 0,
            'issues': issues,
            'staging_indicators': is_staging_token,
            'production_indicators': is_production_token
        }