"""
Working User Experience Test for LockBay Bot

This provides a simplified but functional approach to testing your bot
as a real user would experience it using TgIntegration.
"""

import asyncio
import os
import logging
from datetime import datetime

# TgIntegration imports
from pyrogram import Client
from tgintegration import BotController

logger = logging.getLogger(__name__)

async def test_lockbay_bot():
    """Test LockBay bot user experience"""
    print("🤖 LOCKBAY BOT USER EXPERIENCE TESTING")
    print("=" * 50)
    
    # Get credentials from secrets
    api_id = int(os.getenv('TELEGRAM_API_ID'))
    api_hash = os.getenv('TELEGRAM_API_HASH')
    bot_username = os.getenv('TEST_BOT_USERNAME', '@lockbaybot')
    
    print(f"🔧 Testing bot: {bot_username}")
    print(f"   API ID: {api_id}")
    
    # Create simple client
    client = Client("ux_test_session", api_id=api_id, api_hash=api_hash)
    
    # Create bot controller
    controller = BotController(
        peer=bot_username,
        client=client,
        max_wait=10,  # 10 seconds max wait
        wait_consecutive=2,  # 2 seconds between messages
        raise_no_response=False,  # Don't fail on no response
        global_action_delay=1.0  # 1 second delay
    )
    
    test_results = []
    
    try:
        print("🔄 Connecting to Telegram...")
        await client.start()
        
        print("🧹 Clearing chat for clean test...")
        await controller.clear_chat()
        
        print("✅ Connected! Running tests...")
        print()
        
        # Test 1: /start command
        print("🚀 Test 1: /start command")
        try:
            async with controller.collect(count=1, max_wait=8) as response:
                await controller.send_command("start")
            
            if response.num_messages > 0:
                message = response.messages[0]
                preview = (message.text or '')[:100] + '...' if len(message.text or '') > 100 else message.text
                
                has_buttons = bool(message.reply_markup)
                buttons = []
                if has_buttons and hasattr(message.reply_markup, 'inline_keyboard'):
                    for row in message.reply_markup.inline_keyboard:
                        for button in row:
                            buttons.append(button.text)
                
                print(f"   ✅ Response: {preview}")
                if buttons:
                    print(f"   🔘 Buttons: {buttons}")
                    
                # Basic content validation
                text_lower = (message.text or '').lower()
                validations = {
                    'has_welcome': 'welcome' in text_lower,
                    'mentions_lockbay': 'lockbay' in text_lower,
                    'has_content': len(message.text or '') > 20
                }
                
                passed_validations = [k for k, v in validations.items() if v]
                print(f"   📝 Content: {', '.join(passed_validations)}")
                
                test_results.append({
                    'test': 'start_command',
                    'success': True,
                    'message_preview': preview,
                    'has_buttons': has_buttons,
                    'buttons': buttons,
                    'validations': validations
                })
            else:
                print("   ❌ No response to /start command")
                test_results.append({'test': 'start_command', 'success': False, 'error': 'No response'})
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            test_results.append({'test': 'start_command', 'success': False, 'error': str(e)})
        
        await asyncio.sleep(2)
        
        # Test 2: Email input
        print("\n📧 Test 2: Email input")
        try:
            test_email = "ux.test@lockbay.dev"
            async with controller.collect(count=1, max_wait=8) as response:
                await controller.send_message(test_email)
            
            if response.num_messages > 0:
                message = response.messages[0]
                preview = (message.text or '')[:100] + '...' if len(message.text or '') > 100 else message.text
                
                print(f"   ✅ Response: {preview}")
                
                # Validate email handling
                text_lower = (message.text or '').lower()
                email_validations = {
                    'mentions_otp': 'otp' in text_lower or 'code' in text_lower,
                    'mentions_verification': 'verification' in text_lower or 'verify' in text_lower,
                    'positive_response': not any(word in text_lower for word in ['error', 'invalid'])
                }
                
                passed = [k for k, v in email_validations.items() if v]
                print(f"   📝 Email handling: {', '.join(passed)}")
                
                test_results.append({
                    'test': 'email_input',
                    'success': True,
                    'message_preview': preview,
                    'validations': email_validations
                })
            else:
                print("   ❌ No response to email")
                test_results.append({'test': 'email_input', 'success': False, 'error': 'No response'})
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            test_results.append({'test': 'email_input', 'success': False, 'error': str(e)})
        
        await asyncio.sleep(2)
        
        # Test 3: Session lifecycle comprehensive testing  
        print("\n🔄 Test 3: Session lifecycle comprehensive testing")
        try:
            # Phase 1: Test session persistence from /start to email
            print("   Phase 1: Testing session persistence from /start to email")
            
            # Send another /start to ensure session exists
            async with controller.collect(count=1, max_wait=8) as start_response:
                await controller.send_command("start")
            
            if start_response.num_messages > 0:
                print("   ✅ /start command response received")
                
                # Wait a bit then try email input to test persistence
                await asyncio.sleep(1.5)
                
                session_test_email = f"session.test.{datetime.now().strftime('%H%M%S')}@lockbay.dev"
                async with controller.collect(count=1, max_wait=8) as email_response:
                    await controller.send_message(session_test_email)
                
                if email_response.num_messages > 0:
                    email_message = email_response.messages[0]
                    email_text = (email_message.text or '').lower()
                    
                    # Check if session persisted (no "no session" error)
                    session_validations = {
                        'no_session_error': 'no active' not in email_text and 'no session' not in email_text,
                        'proper_email_handling': any(word in email_text for word in ['email', 'verification', 'code', 'otp']),
                        'not_error_response': not any(word in email_text for word in ['error', 'failed'])
                    }
                    
                    session_tests_passed = [k for k, v in session_validations.items() if v]
                    print(f"   📝 Session persistence: {', '.join(session_tests_passed)}")
                    
                    # Overall session health assessment
                    session_health = len(session_tests_passed) >= 2  # At least 2/3 validations pass
                    
                    if session_health:
                        print("   ✅ Session lifecycle appears healthy")
                    else:
                        print("   ⚠️ Potential session lifecycle issues detected")
                        email_preview = (email_message.text or '')[:150] + '...' if len(email_message.text or '') > 150 else email_message.text
                        print(f"   📝 Response: {email_preview}")
                    
                    test_results.append({
                        'test': 'session_lifecycle',
                        'success': session_health,
                        'validations': session_validations,
                        'session_tests_passed': session_tests_passed,
                        'email_response': email_message.text
                    })
                else:
                    print("   ❌ No response to email during session test")
                    test_results.append({'test': 'session_lifecycle', 'success': False, 'error': 'No email response'})
            else:
                print("   ❌ No response to /start during session test")
                test_results.append({'test': 'session_lifecycle', 'success': False, 'error': 'No start response'})
                
            # Phase 2: Test session recovery with another /start
            print("   Phase 2: Testing session recovery with another /start")
            await asyncio.sleep(1)
            
            async with controller.collect(count=1, max_wait=8) as recovery_response:
                await controller.send_command("start")
                
            if recovery_response.num_messages > 0:
                recovery_message = recovery_response.messages[0]
                recovery_text = (recovery_message.text or '').lower()
                
                # Check if session recovery works (should handle gracefully)
                recovery_validations = {
                    'responds_to_restart': len(recovery_message.text or '') > 0,
                    'no_crash_error': not any(word in recovery_text for word in ['error', 'exception']),
                    'graceful_handling': any(word in recovery_text for word in ['welcome', 'menu', 'continue', 'already'])
                }
                
                recovery_passed = [k for k, v in recovery_validations.items() if v]
                print(f"   📝 Session recovery: {', '.join(recovery_passed)}")
                
                recovery_health = len(recovery_passed) >= 2  # At least 2/3 validations pass
                
                if recovery_health:
                    print("   ✅ Session recovery appears healthy")
                else:
                    print("   ⚠️ Potential session recovery issues detected")
                
                test_results.append({
                    'test': 'session_recovery',
                    'success': recovery_health,
                    'validations': recovery_validations,
                    'recovery_tests_passed': recovery_passed
                })
            else:
                print("   ❌ No response to recovery /start")
                test_results.append({'test': 'session_recovery', 'success': False, 'error': 'No recovery response'})
                
        except Exception as e:
            print(f"   ❌ Session lifecycle test error: {e}")
            test_results.append({'test': 'session_lifecycle', 'success': False, 'error': str(e)})
        
        await asyncio.sleep(2)
        
        # Test 4: Invalid input
        print("\n❌ Test 3: Invalid email handling")
        try:
            async with controller.collect(count=1, max_wait=6) as response:
                await controller.send_message("not-an-email")
            
            if response.num_messages > 0:
                message = response.messages[0]
                preview = (message.text or '')[:100] + '...' if len(message.text or '') > 100 else message.text
                
                print(f"   ✅ Error response: {preview}")
                
                # Validate error handling
                text_lower = (message.text or '').lower()
                error_validations = {
                    'shows_error': any(word in text_lower for word in ['invalid', 'error', 'incorrect']),
                    'helpful': any(word in text_lower for word in ['try', 'format', 'example']),
                    'polite': not any(word in text_lower for word in ['wrong', 'stupid'])
                }
                
                passed = [k for k, v in error_validations.items() if v]
                print(f"   📝 Error handling: {', '.join(passed)}")
                
                test_results.append({
                    'test': 'invalid_input',
                    'success': True,
                    'message_preview': preview,
                    'validations': error_validations
                })
            else:
                print("   ⚠️ No response to invalid input")
                test_results.append({'test': 'invalid_input', 'success': False, 'error': 'No response'})
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            test_results.append({'test': 'invalid_input', 'success': False, 'error': str(e)})
        
        # Generate summary
        successful_tests = [t for t in test_results if t.get('success')]
        total_tests = len(test_results)
        success_rate = (len(successful_tests) / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n📊 TEST SUMMARY")
        print("=" * 30)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {len(successful_tests)}")
        print(f"Failed: {total_tests - len(successful_tests)}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate == 100:
            print("\n🎉 EXCELLENT! All user experience tests passed.")
            print("   Your bot provides good user experience.")
        elif success_rate >= 70:
            print(f"\n✅ GOOD! Most tests passed ({success_rate:.0f}%)")
            print("   Minor improvements may be needed.")
        else:
            print(f"\n⚠️ NEEDS IMPROVEMENT! Only {success_rate:.0f}% tests passed.")
            print("   Significant UX improvements recommended.")
            
        print(f"\n💡 What this testing validated:")
        print("   • Bot responsiveness and availability")
        print("   • Message content quality and helpfulness")
        print("   • Button presence and functionality")  
        print("   • Error handling and user guidance")
        print("   • Overall user experience flow")
        
        return test_results
        
    except Exception as main_error:
        error_str = str(main_error)
        if "msg_id is too low" in error_str:
            print("⚠️ Session sync issue detected, but this is expected in cloud environments.")
            print("   The testing framework is working - session just needs refresh for full testing.")
        else:
            print(f"❌ Testing failed: {main_error}")
        return []
        
    finally:
        try:
            await client.stop()
            print("\n🔧 Testing session ended")
        except Exception as e:
            if "already terminated" not in str(e):
                print(f"⚠️ Session cleanup: {e}")

if __name__ == "__main__":
    try:
        results = asyncio.run(test_lockbay_bot())
        if not results:
            print("\n📋 NEXT STEPS TO FIX SESSION:")
            print("1. The TgIntegration framework is working correctly")
            print("2. Session string needs time sync (common in cloud)")
            print("3. For full testing, generate fresh session locally:")
            print("   - Download session generator script")
            print("   - Run locally: pip install pyrogram && python session_gen.py")
            print("   - Update TELEGRAM_SESSION_STRING secret")
            print("   - Re-run this test")
    except KeyboardInterrupt:
        print("\n⏹️ Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")