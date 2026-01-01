"""
Simple User Session Testing with Pyrogram

Direct approach for testing bot responses using a real user account.
Simpler than TgIntegration but still effective for basic validation.

Requirements:
pip install pyrogram

Setup:
1. Get API credentials from https://my.telegram.org/apps  
2. Generate session string (see generate_session_string function)
3. Set environment variables
"""

import os
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait

logger = logging.getLogger(__name__)


class SimpleUserTester:
    """
    Simple user session bot testing
    """
    
    def __init__(self):
        self.api_id = int(os.getenv('TELEGRAM_API_ID'))
        self.api_hash = os.getenv('TELEGRAM_API_HASH')
        self.session_string = os.getenv('TELEGRAM_SESSION_STRING')
        self.bot_username = os.getenv('TEST_BOT_USERNAME', '@lockbay_test_bot').replace('@', '')
        
        self.client = Client(
            name="simple_test_session",
            api_id=self.api_id, 
            api_hash=self.api_hash,
            session_string=self.session_string
        )
        
        self.received_messages = []
        self.setup_message_handler()
    
    def setup_message_handler(self):
        """Setup handler to capture bot responses"""
        @self.client.on_message(filters.user(self.bot_username))
        async def message_handler(client, message: Message):
            """Capture all messages from the bot"""
            self.received_messages.append({
                'timestamp': datetime.now(),
                'text': message.text or '',
                'buttons': self._extract_buttons(message),
                'message_id': message.id,
                'has_media': bool(message.media)
            })
            logger.info(f"📨 Received from bot: {message.text[:50] if message.text else 'Media message'}")
    
    def _extract_buttons(self, message: Message) -> List[str]:
        """Extract button texts from message"""
        buttons = []
        if message.reply_markup and hasattr(message.reply_markup, 'inline_keyboard'):
            for row in message.reply_markup.inline_keyboard:
                for button in row:
                    buttons.append(button.text)
        return buttons
    
    async def start_session(self):
        """Start the user session"""
        await self.client.start()
        logger.info("🔧 User session started")
        
    async def stop_session(self):
        """Stop the user session"""
        await self.client.stop()
        logger.info("🔧 User session stopped")
    
    async def send_message_and_wait(self, text: str, wait_time: float = 3.0) -> List[Dict[str, Any]]:
        """Send message to bot and wait for responses"""
        # Clear previous messages
        self.received_messages = []
        
        try:
            # Send message to bot
            await self.client.send_message(self.bot_username, text)
            logger.info(f"📤 Sent to bot: {text}")
            
            # Wait for responses
            await asyncio.sleep(wait_time)
            
            # Return captured responses
            return self.received_messages.copy()
            
        except FloodWait as e:
            logger.warning(f"Rate limited, waiting {e.value} seconds")
            await asyncio.sleep(e.value)
            return []
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return []
    
    async def test_onboarding_sequence(self) -> Dict[str, Any]:
        """Test complete onboarding sequence"""
        results = {
            'start_command': None,
            'email_input': None, 
            'otp_input': None,
            'menu_access': None
        }
        
        # Test /start
        logger.info("🚀 Testing /start command")
        start_responses = await self.send_message_and_wait("/start", 4.0)
        if start_responses:
            results['start_command'] = {
                'success': True,
                'response_count': len(start_responses),
                'first_message': start_responses[0]['text'],
                'has_buttons': len(start_responses[0]['buttons']) > 0,
                'buttons': start_responses[0]['buttons']
            }
            
            # Validate content
            first_text = start_responses[0]['text'].lower()
            results['start_command']['content_check'] = {
                'has_welcome': 'welcome' in first_text,
                'mentions_email': 'email' in first_text,
                'mentions_lockbay': 'lockbay' in first_text
            }
        else:
            results['start_command'] = {'success': False, 'error': 'No response'}
        
        await asyncio.sleep(2)  # Rate limiting prevention
        
        # Test email input
        logger.info("📧 Testing email input")
        email_responses = await self.send_message_and_wait("test.user@lockbay.dev", 4.0)
        if email_responses:
            results['email_input'] = {
                'success': True,
                'response_count': len(email_responses),
                'message_text': email_responses[0]['text'],
                'mentions_otp': 'otp' in email_responses[0]['text'].lower(),
                'mentions_verification': 'verification' in email_responses[0]['text'].lower()
            }
        else:
            results['email_input'] = {'success': False, 'error': 'No response to email'}
            
        await asyncio.sleep(2)
        
        # Test OTP (this will likely fail in real testing, but shows response)
        logger.info("🔢 Testing OTP input")
        otp_responses = await self.send_message_and_wait("123456", 4.0)  
        if otp_responses:
            results['otp_input'] = {
                'success': True,
                'response_count': len(otp_responses),
                'message_text': otp_responses[0]['text'],
                'shows_error': any(word in otp_responses[0]['text'].lower() 
                                 for word in ['invalid', 'incorrect', 'try again'])
            }
        else:
            results['otp_input'] = {'success': False, 'error': 'No response to OTP'}
            
        await asyncio.sleep(2)
        
        # Test menu access
        logger.info("📋 Testing menu access")
        menu_responses = await self.send_message_and_wait("📋 Menu", 3.0)
        if menu_responses:
            results['menu_access'] = {
                'success': True,
                'response_count': len(menu_responses),
                'message_text': menu_responses[0]['text'],
                'has_menu_buttons': len(menu_responses[0]['buttons']) > 0,
                'menu_options': menu_responses[0]['buttons']
            }
        else:
            results['menu_access'] = {'success': False, 'error': 'No response to menu'}
        
        return results
    
    async def test_error_handling(self) -> Dict[str, Any]:
        """Test how bot handles invalid inputs"""
        results = {}
        
        # Test invalid email
        logger.info("❌ Testing invalid email handling")
        invalid_email_responses = await self.send_message_and_wait("not-an-email", 3.0)
        if invalid_email_responses:
            response_text = invalid_email_responses[0]['text'].lower()
            results['invalid_email'] = {
                'success': True,
                'message_text': invalid_email_responses[0]['text'],
                'shows_error_message': any(word in response_text 
                                         for word in ['invalid', 'error', 'valid email', 'try again'])
            }
        else:
            results['invalid_email'] = {'success': False, 'error': 'No error response'}
        
        await asyncio.sleep(2)
        
        # Test unknown command
        logger.info("❓ Testing unknown command handling")
        unknown_responses = await self.send_message_and_wait("/unknown_command", 3.0)
        if unknown_responses:
            results['unknown_command'] = {
                'success': True,
                'message_text': unknown_responses[0]['text'],
                'helpful_response': any(word in unknown_responses[0]['text'].lower()
                                      for word in ['help', 'command', 'menu', 'available'])
            }
        else:
            results['unknown_command'] = {'success': False, 'error': 'No response to unknown command'}
            
        return results
    
    def print_results(self, results: Dict[str, Any], title: str = "Test Results"):
        """Print formatted test results"""
        print(f"\n📊 {title.upper()}")
        print("=" * 60)
        
        for test_name, result in results.items():
            if result and result.get('success'):
                print(f"✅ {test_name}: PASSED")
                if 'message_text' in result:
                    print(f"   Response: {result['message_text'][:80]}...")
                if 'buttons' in result and result['buttons']:
                    print(f"   Buttons: {result['buttons']}")
            else:
                print(f"❌ {test_name}: FAILED")
                if result and 'error' in result:
                    print(f"   Error: {result['error']}")


def generate_session_string():
    """Helper function to generate session string"""
    setup_code = '''
# Run this once to generate your session string:

from pyrogram import Client
import os

api_id = int(input("Enter your API ID: "))
api_hash = input("Enter your API Hash: ")

async def main():
    async with Client("my_session", api_id, api_hash) as client:
        print("Session string:", client.session.string)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
'''
    return setup_code


# Example usage
async def run_simple_user_tests():
    """Run simple user experience tests"""
    tester = SimpleUserTester()
    
    try:
        await tester.start_session()
        
        print("🚀 Running Simple User Experience Tests...")
        
        # Run onboarding tests
        onboarding_results = await tester.test_onboarding_sequence()
        tester.print_results(onboarding_results, "Onboarding Flow")
        
        # Run error handling tests
        error_results = await tester.test_error_handling()
        tester.print_results(error_results, "Error Handling")
        
        # Overall assessment
        total_tests = len(onboarding_results) + len(error_results)
        passed_tests = sum(1 for r in list(onboarding_results.values()) + list(error_results.values()) 
                          if r and r.get('success'))
        
        print(f"\n📈 OVERALL RESULTS:")
        print(f"   Tests passed: {passed_tests}/{total_tests}")
        print(f"   Success rate: {(passed_tests/total_tests)*100:.1f}%")
        
    finally:
        await tester.stop_session()


if __name__ == "__main__":
    # Check if session string needs to be generated
    if not os.getenv('TELEGRAM_SESSION_STRING'):
        print("⚠️ Session string not found. Generate one using:")
        print(generate_session_string())
    else:
        asyncio.run(run_simple_user_tests())