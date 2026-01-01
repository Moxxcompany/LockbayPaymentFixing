"""
User Experience Testing with TgIntegration

This demonstrates automated user-facing testing that can validate:
- Actual bot responses and message content
- Button functionality and inline keyboards  
- Complete conversation flows
- Welcome messages, error messages, etc.

Requirements:
pip install tgintegration pyrogram

Setup:
1. Get API credentials from https://my.telegram.org/apps
2. Create test user account Telegram session
3. Set environment variables:
   - TELEGRAM_API_ID=your_api_id
   - TELEGRAM_API_HASH=your_api_hash  
   - TELEGRAM_SESSION_STRING=your_session_string
   - TEST_BOT_USERNAME=@your_test_bot_username
"""

import pytest
import asyncio
import os
from typing import List

from pyrogram import Client
from tgintegration import BotController
from tgintegration.containers import InlineResultContainer


class UserExperienceTestFramework:
    """
    Framework for testing actual user experience with real bot responses
    """
    
    def __init__(self):
        self.api_id = int(os.getenv('TELEGRAM_API_ID'))
        self.api_hash = os.getenv('TELEGRAM_API_HASH')
        self.session_string = os.getenv('TELEGRAM_SESSION_STRING')
        self.bot_username = os.getenv('TEST_BOT_USERNAME', '@lockbay_test_bot')
        
        # Initialize user client (acts as real user)
        self.client = Client(
            name="test_user_session",
            api_id=self.api_id,
            api_hash=self.api_hash,
            session_string=self.session_string
        )
        
        # Bot controller for testing interactions
        self.controller = BotController(
            peer=self.bot_username,
            client=self.client,
            max_wait=15,  # Wait up to 15 seconds for responses
            wait_consecutive=2,  # Wait 2 seconds between consecutive messages
            raise_no_response=True,  # Fail test if no response
            global_action_delay=1.5  # 1.5 second delay between actions
        )
    
    async def start_session(self):
        """Start user session for testing"""
        await self.client.start()
        await self.controller.clear_chat()  # Clean slate for testing
        
    async def stop_session(self):
        """Stop user session"""
        await self.client.stop()
    
    async def test_onboarding_flow_complete(self) -> dict:
        """Test complete onboarding flow as real user"""
        results = {
            'start_command': None,
            'email_collection': None,
            'otp_verification': None,
            'terms_acceptance': None,
            'welcome_message': None
        }
        
        # Test 1: /start command
        async with self.controller.collect(count=1, max_wait=10) as response:
            await self.controller.send_command("start")
        
        if response.num_messages > 0:
            start_message = response.messages[0]
            results['start_command'] = {
                'success': True,
                'message_text': start_message.text,
                'has_keyboard': bool(start_message.reply_markup),
                'buttons': self._extract_button_texts(start_message.reply_markup) if start_message.reply_markup else []
            }
            
            # Validate expected content
            expected_keywords = ['welcome', 'email', 'lockbay']
            found_keywords = [kw for kw in expected_keywords if kw.lower() in start_message.text.lower()]
            results['start_command']['content_validation'] = {
                'expected_keywords': expected_keywords,
                'found_keywords': found_keywords,
                'validation_passed': len(found_keywords) >= 2
            }
        else:
            results['start_command'] = {'success': False, 'error': 'No response to /start command'}
        
        await asyncio.sleep(2)  # Wait between tests
        
        # Test 2: Email collection
        test_email = "ux.test@lockbay.dev"
        async with self.controller.collect(count=1, max_wait=10) as response:
            await self.controller.send_message(test_email)
            
        if response.num_messages > 0:
            email_response = response.messages[0] 
            results['email_collection'] = {
                'success': True,
                'message_text': email_response.text,
                'email_accepted': 'otp' in email_response.text.lower() or 'verification' in email_response.text.lower()
            }
        else:
            results['email_collection'] = {'success': False, 'error': 'No response to email'}
            
        await asyncio.sleep(2)
        
        # Test 3: OTP verification (simulate)
        test_otp = "123456"
        async with self.controller.collect(count=1, max_wait=10) as response:
            await self.controller.send_message(test_otp)
            
        if response.num_messages > 0:
            otp_response = response.messages[0]
            results['otp_verification'] = {
                'success': True,
                'message_text': otp_response.text,
                'has_terms_button': 'terms' in otp_response.text.lower() or bool(otp_response.reply_markup)
            }
        else:
            results['otp_verification'] = {'success': False, 'error': 'No response to OTP'}
            
        await asyncio.sleep(2)
        
        # Test 4: Button interaction (if available)
        if results['otp_verification'].get('success') and results['otp_verification'].get('has_terms_button'):
            # Try to interact with terms acceptance button
            async with self.controller.collect(count=1, max_wait=10) as response:
                # This would click the first inline button if available
                await self.controller.send_callback_query_by_text("Accept")
                
            if response.num_messages > 0:
                terms_response = response.messages[0]
                results['terms_acceptance'] = {
                    'success': True,
                    'message_text': terms_response.text,
                    'shows_welcome': 'welcome' in terms_response.text.lower()
                }
        
        return results
    
    async def test_menu_navigation(self) -> dict:
        """Test menu navigation and commands"""
        results = {}
        
        # Test menu command
        async with self.controller.collect(count=1, max_wait=8) as response:
            await self.controller.send_message("📋 Menu")
            
        if response.num_messages > 0:
            menu_response = response.messages[0]
            results['menu_command'] = {
                'success': True,
                'message_text': menu_response.text,
                'has_menu_options': bool(menu_response.reply_markup),
                'menu_buttons': self._extract_button_texts(menu_response.reply_markup) if menu_response.reply_markup else []
            }
        else:
            results['menu_command'] = {'success': False, 'error': 'No menu response'}
            
        return results
    
    async def test_error_handling(self) -> dict:
        """Test how bot handles invalid inputs"""
        results = {}
        
        # Test invalid email
        async with self.controller.collect(count=1, max_wait=8) as response:
            await self.controller.send_message("invalid-email")
            
        if response.num_messages > 0:
            error_response = response.messages[0]
            results['invalid_email'] = {
                'success': True,
                'message_text': error_response.text,
                'shows_error_message': any(word in error_response.text.lower() 
                                         for word in ['invalid', 'error', 'try again', 'correct'])
            }
        else:
            results['invalid_email'] = {'success': False, 'error': 'No error response'}
            
        return results
    
    def _extract_button_texts(self, reply_markup) -> List[str]:
        """Extract button texts from inline keyboard"""
        buttons = []
        if hasattr(reply_markup, 'inline_keyboard'):
            for row in reply_markup.inline_keyboard:
                for button in row:
                    if hasattr(button, 'text'):
                        buttons.append(button.text)
        return buttons


# Pytest test cases
@pytest.mark.asyncio
class TestUserExperienceAutomation:
    
    @pytest.fixture(scope="class")
    async def ux_framework(self):
        """Setup user experience testing framework"""
        if not all([
            os.getenv('TELEGRAM_API_ID'),
            os.getenv('TELEGRAM_API_HASH'), 
            os.getenv('TELEGRAM_SESSION_STRING')
        ]):
            pytest.skip("Telegram credentials not configured")
            
        framework = UserExperienceTestFramework()
        await framework.start_session()
        yield framework
        await framework.stop_session()
    
    async def test_complete_onboarding_user_experience(self, ux_framework):
        """Test complete onboarding as real user"""
        results = await ux_framework.test_onboarding_flow_complete()
        
        # Validate start command worked
        assert results['start_command']['success'], "Start command failed"
        assert results['start_command']['content_validation']['validation_passed'], "Start message content validation failed"
        
        # Validate email collection  
        assert results['email_collection']['success'], "Email collection failed"
        assert results['email_collection']['email_accepted'], "Email was not accepted by bot"
        
        # Log results for analysis
        print("\n🔍 COMPLETE ONBOARDING TEST RESULTS:")
        print("=" * 50)
        for step, result in results.items():
            status = "✅ PASS" if result and result.get('success') else "❌ FAIL"
            print(f"{step}: {status}")
            if result and result.get('message_text'):
                print(f"   Response: {result['message_text'][:100]}...")
                
    async def test_menu_user_experience(self, ux_framework):
        """Test menu navigation experience"""
        results = await ux_framework.test_menu_navigation()
        
        assert results['menu_command']['success'], "Menu command failed"
        
        print("\n📋 MENU NAVIGATION TEST RESULTS:")
        print("=" * 50)
        menu_result = results['menu_command']
        print(f"Menu Response: {menu_result.get('message_text', 'No text')[:100]}...")
        print(f"Menu Buttons: {menu_result.get('menu_buttons', [])}")
        
    async def test_error_handling_user_experience(self, ux_framework):
        """Test error handling from user perspective"""
        results = await ux_framework.test_error_handling()
        
        assert results['invalid_email']['success'], "Error handling test failed"
        assert results['invalid_email']['shows_error_message'], "Bot didn't show proper error message"
        
        print("\n❌ ERROR HANDLING TEST RESULTS:")
        print("=" * 50)
        error_result = results['invalid_email']
        print(f"Error Response: {error_result.get('message_text', 'No text')}")
        

if __name__ == "__main__":
    # Example of running tests programmatically
    import asyncio
    
    async def run_example_test():
        framework = UserExperienceTestFramework()
        await framework.start_session()
        
        print("🚀 Running User Experience Test...")
        results = await framework.test_onboarding_flow_complete()
        
        print("\n📊 TEST RESULTS SUMMARY:")
        print("=" * 50)
        for step, result in results.items():
            status = "✅" if result and result.get('success') else "❌"
            print(f"{status} {step}")
            
        await framework.stop_session()
    
    # Uncomment to run example
    # asyncio.run(run_example_test())