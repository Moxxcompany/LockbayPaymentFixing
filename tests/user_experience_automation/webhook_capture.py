"""
Webhook Capture System for Bot Response Validation

This approach intercepts outgoing bot messages to validate content without
needing a separate user session. Works by capturing webhook calls.

Note: This is more complex but provides complete message validation capability.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WebhookCaptureFramework:
    """
    Framework for capturing and validating bot responses via webhook interception
    """
    
    def __init__(self):
        self.captured_messages = []
        self.test_session_id = None
        
    def setup_capture_webhook(self, port: int = 8888):
        """
        Setup webhook capture server (conceptual implementation)
        In practice, this would require modifying your bot's webhook handling
        """
        webhook_config = {
            'capture_port': port,
            'capture_endpoint': f'http://localhost:{port}/capture',
            'message_types': ['sendMessage', 'editMessageText', 'sendPhoto', 'sendDocument'],
            'capture_filters': {
                'test_user_only': True,
                'include_keyboards': True,
                'include_media': True
            }
        }
        return webhook_config
    
    def start_test_session(self, test_user_id: str) -> str:
        """Start a new test session for message capture"""
        self.test_session_id = f"test_{int(time.time())}_{test_user_id}"
        self.captured_messages = []
        logger.info(f"🔧 Started webhook capture session: {self.test_session_id}")
        return self.test_session_id
    
    def capture_outgoing_message(self, webhook_data: Dict[str, Any]):
        """
        Capture outgoing bot message from webhook
        This would be called by your modified webhook handler
        """
        captured_message = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.test_session_id,
            'method': webhook_data.get('method'),  # sendMessage, etc.
            'chat_id': webhook_data.get('chat_id'),
            'text': webhook_data.get('text', ''),
            'reply_markup': webhook_data.get('reply_markup'),
            'message_id': webhook_data.get('message_id'),
            'raw_data': webhook_data
        }
        
        self.captured_messages.append(captured_message)
        logger.info(f"📨 Captured outgoing message: {captured_message['text'][:50]}...")
        
    def validate_message_sequence(self, expected_sequence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate captured messages against expected sequence"""
        validation_results = {
            'sequence_matched': False,
            'message_count': len(self.captured_messages),
            'expected_count': len(expected_sequence),
            'validations': []
        }
        
        for i, expected in enumerate(expected_sequence):
            if i < len(self.captured_messages):
                captured = self.captured_messages[i]
                validation = self._validate_single_message(captured, expected)
                validation['position'] = i
                validation_results['validations'].append(validation)
            else:
                validation_results['validations'].append({
                    'position': i,
                    'valid': False,
                    'error': 'Message not captured'
                })
        
        validation_results['sequence_matched'] = all(v['valid'] for v in validation_results['validations'])
        return validation_results
        
    def _validate_single_message(self, captured: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single captured message against expectations"""
        validation = {'valid': True, 'issues': []}
        
        # Validate text content
        if 'text_contains' in expected:
            for keyword in expected['text_contains']:
                if keyword.lower() not in captured['text'].lower():
                    validation['issues'].append(f"Missing keyword: {keyword}")
                    validation['valid'] = False
        
        # Validate buttons
        if 'buttons' in expected:
            captured_buttons = self._extract_button_texts(captured.get('reply_markup'))
            for button_text in expected['buttons']:
                if button_text not in captured_buttons:
                    validation['issues'].append(f"Missing button: {button_text}")
                    validation['valid'] = False
        
        # Validate message type
        if 'method' in expected:
            if captured['method'] != expected['method']:
                validation['issues'].append(f"Wrong method: expected {expected['method']}, got {captured['method']}")
                validation['valid'] = False
                
        return validation
        
    def _extract_button_texts(self, reply_markup: Optional[Dict]) -> List[str]:
        """Extract button texts from reply markup"""
        if not reply_markup or 'inline_keyboard' not in reply_markup:
            return []
            
        buttons = []
        for row in reply_markup.get('inline_keyboard', []):
            for button in row:
                if 'text' in button:
                    buttons.append(button['text'])
        return buttons
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        report = {
            'session_id': self.test_session_id,
            'test_timestamp': datetime.now().isoformat(),
            'total_messages_captured': len(self.captured_messages),
            'message_details': [],
            'summary': {
                'has_welcome_message': False,
                'has_error_handling': False,
                'has_buttons': False,
                'average_response_length': 0
            }
        }
        
        total_length = 0
        for msg in self.captured_messages:
            detail = {
                'timestamp': msg['timestamp'],
                'method': msg['method'],
                'text_preview': msg['text'][:100],
                'text_length': len(msg['text']),
                'has_buttons': bool(msg['reply_markup']),
                'button_count': len(self._extract_button_texts(msg['reply_markup']))
            }
            report['message_details'].append(detail)
            total_length += len(msg['text'])
            
            # Update summary
            if 'welcome' in msg['text'].lower():
                report['summary']['has_welcome_message'] = True
            if any(word in msg['text'].lower() for word in ['error', 'invalid', 'try again']):
                report['summary']['has_error_handling'] = True
            if msg['reply_markup']:
                report['summary']['has_buttons'] = True
                
        if self.captured_messages:
            report['summary']['average_response_length'] = total_length / len(self.captured_messages)
            
        return report


class WebhookTestScenarios:
    """
    Predefined test scenarios for webhook capture testing
    """
    
    @staticmethod
    def onboarding_flow_expectations() -> List[Dict[str, Any]]:
        """Expected message sequence for onboarding flow"""
        return [
            {
                'method': 'sendMessage',
                'text_contains': ['welcome', 'lockbay'],
                'buttons': ['Start Onboarding', 'Learn More']
            },
            {
                'method': 'sendMessage', 
                'text_contains': ['email', 'address'],
                'buttons': []
            },
            {
                'method': 'sendMessage',
                'text_contains': ['otp', 'verification', 'sent'],
                'buttons': []
            },
            {
                'method': 'sendMessage',
                'text_contains': ['terms', 'service'],
                'buttons': ['Accept Terms', 'View Terms']
            },
            {
                'method': 'sendMessage',
                'text_contains': ['welcome', 'complete', 'ready'],
                'buttons': ['Main Menu', 'Get Started']
            }
        ]
    
    @staticmethod  
    def error_handling_expectations() -> List[Dict[str, Any]]:
        """Expected responses for error scenarios"""
        return [
            {
                'method': 'sendMessage',
                'text_contains': ['invalid', 'email', 'format'],
                'buttons': []
            },
            {
                'method': 'sendMessage',
                'text_contains': ['incorrect', 'otp', 'try again'],
                'buttons': ['Resend OTP']
            },
            {
                'method': 'sendMessage',
                'text_contains': ['help', 'command', 'available'],
                'buttons': ['Main Menu', 'Help']
            }
        ]


# Integration example showing how to modify your webhook handler
webhook_integration_example = '''
# Example of integrating webhook capture into your existing bot

from tests.test_webhook_capture_system import WebhookCaptureFramework

# Global test framework instance
test_framework = WebhookCaptureFramework()

# Modified webhook handler (conceptual)
async def enhanced_webhook_handler(update, context):
    """Enhanced webhook handler with test capture capability"""
    
    # Your existing webhook logic
    result = await original_webhook_handler(update, context)
    
    # Capture outgoing messages for testing
    if context.bot._test_mode and hasattr(context, 'outgoing_messages'):
        for message_data in context.outgoing_messages:
            test_framework.capture_outgoing_message(message_data)
    
    return result

# Test runner example
async def run_webhook_capture_test():
    """Example test using webhook capture"""
    
    # Start test session
    session_id = test_framework.start_test_session("test_user_123")
    
    # Trigger bot interaction (via API or user simulation)
    await trigger_bot_interaction("/start", user_id="test_user_123")
    await trigger_bot_interaction("test@example.com", user_id="test_user_123")
    await trigger_bot_interaction("123456", user_id="test_user_123")
    
    # Wait for message capture
    await asyncio.sleep(5)
    
    # Validate captured sequence
    expected_sequence = WebhookTestScenarios.onboarding_flow_expectations()
    validation_results = test_framework.validate_message_sequence(expected_sequence)
    
    # Generate report
    report = test_framework.generate_test_report()
    
    print(f"✅ Webhook capture test complete")
    print(f"📊 Messages captured: {report['total_messages_captured']}")
    print(f"🎯 Sequence validation: {'PASSED' if validation_results['sequence_matched'] else 'FAILED'}")
    
    return validation_results, report
'''


if __name__ == "__main__":
    print("🔗 Webhook Capture System for Bot Testing")
    print("=" * 50)
    print("""
This approach requires modifying your bot's webhook handling to capture
outgoing messages. Benefits:

✅ Complete message content validation
✅ Button and keyboard testing  
✅ Sequence flow validation
✅ No separate user account needed
✅ Integration with existing test suite

Implementation steps:
1. Modify webhook handler to capture outgoing messages
2. Add test mode flag to bot configuration
3. Create test scenarios with expected message sequences
4. Run tests and validate captured messages

See webhook_integration_example for implementation details.
""")
    
    # Demonstrate framework usage
    framework = WebhookCaptureFramework()
    
    # Show expected onboarding sequence
    expected = WebhookTestScenarios.onboarding_flow_expectations()
    print(f"\n📋 Expected Onboarding Sequence ({len(expected)} messages):")
    for i, expectation in enumerate(expected, 1):
        print(f"   {i}. {expectation['method']} - Contains: {expectation['text_contains']}")
        if expectation['buttons']:
            print(f"      Buttons: {expectation['buttons']}")
            
    print(f"\n💡 This approach provides the most comprehensive validation")
    print(f"   but requires integration with your existing bot code.")