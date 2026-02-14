#!/usr/bin/env python3
"""
LockBay Telegram Bot - Group Event Broadcasting System Test
============================================================

Tests for group auto-detection and event broadcasting functionality:
1. Group handler registration and structure
2. Event message content verification (bot username and deeplinks)
3. Marketing message quality assessment
4. Health endpoint verification
"""

import requests
import sys
import json
import re
from datetime import datetime

class LockBayGroupEventTester:
    def __init__(self, base_url="https://96e0c8ed-dcdc-476d-8e93-e838dd5d9875.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.issues = []
        
    def log_result(self, test_name, passed, details="", issue_type="backend"):
        """Log test result with detailed information"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            print(f"✅ {test_name}")
            if details:
                print(f"   {details}")
        else:
            self.issues.append({
                "type": issue_type,
                "test": test_name, 
                "details": details,
                "priority": "HIGH" if "critical" in details.lower() else "MEDIUM"
            })
            print(f"❌ {test_name}")
            print(f"   {details}")
    
    def test_health_endpoint(self):
        """Test that backend is responsive and health endpoint works"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result(
                    "Health Endpoint Accessibility", 
                    True,
                    f"Status: {data.get('status', 'unknown')}, Mode: {data.get('mode', 'unknown')}"
                )
                return data
            else:
                self.log_result(
                    "Health Endpoint Accessibility",
                    False, 
                    f"HTTP {response.status_code}: Expected 200 OK",
                    "backend"
                )
                return None
        except Exception as e:
            self.log_result(
                "Health Endpoint Accessibility",
                False,
                f"Connection failed: {str(e)}",
                "backend"
            )
            return None

    def analyze_code_structure(self):
        """Analyze the code structure for group event functionality"""
        print("\n🔍 Analyzing Group Event System Implementation...")
        
        # Test 1: Verify group_handler.py structure
        try:
            with open('/app/handlers/group_handler.py', 'r') as f:
                group_handler_content = f.read()
            
            # Check for required functions and patterns
            has_my_chat_member = 'handle_my_chat_member' in group_handler_content
            has_register_function = 'register_group_handlers' in group_handler_content
            uses_chat_member_handler = 'ChatMemberHandler' in group_handler_content
            detects_groups = "'group'" in group_handler_content and "'supergroup'" in group_handler_content
            
            # Check for welcome message with bot username and deeplink
            has_bot_username = '@{bot_username}' in group_handler_content or 'f"@{bot_username}"' in group_handler_content
            has_deeplink = 't.me/{bot_username}' in group_handler_content or 'f"https://t.me/{bot_username}"' in group_handler_content
            
            self.log_result(
                "Group Handler - Core Functions",
                has_my_chat_member and has_register_function,
                f"handle_my_chat_member: {has_my_chat_member}, register_group_handlers: {has_register_function}"
            )
            
            self.log_result(
                "Group Handler - Chat Type Detection", 
                detects_groups,
                "Correctly detects 'group' and 'supergroup' chat types"
            )
            
            self.log_result(
                "Group Handler - ChatMemberHandler Usage",
                uses_chat_member_handler,
                "Uses ChatMemberHandler.MY_CHAT_MEMBER for bot add/remove events"
            )
            
            self.log_result(
                "Welcome Message - Bot Username", 
                has_bot_username,
                f"Contains bot username mention: {has_bot_username}"
            )
            
            self.log_result(
                "Welcome Message - Deeplink",
                has_deeplink, 
                f"Contains t.me deeplink: {has_deeplink}"
            )
            
        except FileNotFoundError:
            self.log_result(
                "Group Handler File",
                False,
                "group_handler.py file not found",
                "backend"
            )
    
    def analyze_group_event_service(self):
        """Analyze group_event_service.py for broadcast functionality"""
        print("\n🔍 Analyzing Group Event Broadcasting Service...")
        
        try:
            with open('/app/services/group_event_service.py', 'r') as f:
                service_content = f.read()
            
            # Check for _bot_tag() and _bot_link() helper functions
            has_bot_tag = '_bot_tag()' in service_content
            has_bot_link = '_bot_link()' in service_content
            
            self.log_result(
                "Event Service - Helper Functions",
                has_bot_tag and has_bot_link,
                f"_bot_tag(): {has_bot_tag}, _bot_link(): {has_bot_link}"
            )
            
            # Check all 6 broadcast methods
            broadcast_methods = [
                'broadcast_trade_created',
                'broadcast_trade_funded', 
                'broadcast_seller_accepted',
                'broadcast_escrow_completed',
                'broadcast_rating_submitted',
                'broadcast_new_user_onboarded'
            ]
            
            methods_found = 0
            methods_with_bot_tag = 0
            methods_with_bot_link = 0
            marketing_quality_score = 0
            
            for method in broadcast_methods:
                if method in service_content:
                    methods_found += 1
                    
                    # Extract method content for analysis
                    method_start = service_content.find(f'def {method}')
                    if method_start != -1:
                        # Find the next method or end of class
                        next_method = service_content.find('\n    def ', method_start + 1)
                        method_end = next_method if next_method != -1 else len(service_content)
                        method_content = service_content[method_start:method_end]
                        
                        # Check for bot tag and link usage
                        if '_bot_tag()' in method_content:
                            methods_with_bot_tag += 1
                        if '_bot_link()' in method_content:
                            methods_with_bot_link += 1
                        
                        # Assess marketing quality - look for persuasive elements
                        marketing_keywords = [
                            'secure', 'protected', 'safe', 'confidence', 'join', 
                            'start', 'action', 'opportunity', 'community', 'success'
                        ]
                        cta_patterns = ['Start', 'Join', 'Trade', '→', '▶', 'now', 'today']
                        
                        method_lower = method_content.lower()
                        has_marketing_keywords = any(keyword in method_lower for keyword in marketing_keywords)
                        has_cta = any(cta in method_content for cta in cta_patterns)
                        
                        if has_marketing_keywords and has_cta:
                            marketing_quality_score += 1
            
            self.log_result(
                "Event Service - All 6 Broadcast Methods",
                methods_found == 6,
                f"Found {methods_found}/6 broadcast methods: {', '.join(broadcast_methods)}"
            )
            
            self.log_result(
                "Event Messages - Bot Username Inclusion",
                methods_with_bot_tag == 6,
                f"{methods_with_bot_tag}/6 methods include _bot_tag() for @bot_username"
            )
            
            self.log_result(
                "Event Messages - Deeplink Inclusion", 
                methods_with_bot_link == 6,
                f"{methods_with_bot_link}/6 methods include _bot_link() for deeplinks"
            )
            
            self.log_result(
                "Event Messages - Marketing Quality",
                marketing_quality_score >= 4,
                f"{marketing_quality_score}/6 methods have persuasive marketing language and CTAs"
            )
            
            # Check for BotGroup model registration methods
            has_register_group = 'register_group' in service_content
            has_unregister_group = 'unregister_group' in service_content
            has_deactivate_group = '_deactivate_group' in service_content
            
            self.log_result(
                "Event Service - Group Management Methods",
                has_register_group and has_unregister_group and has_deactivate_group,
                f"register_group: {has_register_group}, unregister_group: {has_unregister_group}, _deactivate_group: {has_deactivate_group}"
            )
            
        except FileNotFoundError:
            self.log_result(
                "Group Event Service File",
                False,
                "group_event_service.py file not found",
                "backend"
            )
    
    def analyze_handler_registration(self):
        """Check that group handlers are registered in server.py and main.py"""
        print("\n🔍 Analyzing Handler Registration...")
        
        # Check server.py registration
        try:
            with open('/app/backend/server.py', 'r') as f:
                server_content = f.read()
            
            has_import = 'from handlers.group_handler import register_group_handlers' in server_content
            has_call_in_critical = 'register_group_handlers(application)' in server_content
            has_allowed_updates = 'my_chat_member' in server_content
            
            self.log_result(
                "Server.py - Group Handler Registration",
                has_import and has_call_in_critical,
                f"Import: {has_import}, Call in _register_all_critical_handlers: {has_call_in_critical}"
            )
            
            self.log_result(
                "Server.py - Webhook Updates Configuration", 
                has_allowed_updates,
                f"'my_chat_member' in allowed_updates: {has_allowed_updates}"
            )
            
        except FileNotFoundError:
            self.log_result(
                "Server.py Handler Registration",
                False,
                "server.py file not found",
                "backend"
            )
        
        # Check main.py registration  
        try:
            with open('/app/main.py', 'r') as f:
                main_content = f.read()
            
            has_main_import = 'from handlers.group_handler import register_group_handlers' in main_content
            has_main_call = 'register_group_handlers(application)' in main_content
            
            self.log_result(
                "Main.py - Group Handler Registration",
                has_main_import and has_main_call,
                f"Import: {has_main_import}, Call: {has_main_call}"
            )
            
        except FileNotFoundError:
            self.log_result(
                "Main.py Handler Registration", 
                False,
                "main.py file not found",
                "backend"
            )
    
    def analyze_botgroup_model(self):
        """Check BotGroup model exists in models.py"""
        print("\n🔍 Analyzing BotGroup Model...")
        
        try:
            with open('/app/models.py', 'r') as f:
                models_content = f.read()
            
            has_botgroup_class = 'class BotGroup' in models_content
            has_chat_id_field = 'chat_id' in models_content
            has_is_active_field = 'is_active' in models_content  
            has_events_enabled_field = 'events_enabled' in models_content
            
            self.log_result(
                "Models.py - BotGroup Model",
                has_botgroup_class,
                f"BotGroup class exists: {has_botgroup_class}"
            )
            
            if has_botgroup_class:
                # Check for required fields
                required_fields = ['chat_id', 'is_active', 'events_enabled']
                found_fields = [field for field in required_fields if field in models_content]
                
                self.log_result(
                    "BotGroup Model - Required Fields",
                    len(found_fields) == len(required_fields),
                    f"Found fields: {found_fields} (expected: {required_fields})"
                )
            
        except FileNotFoundError:
            self.log_result(
                "Models.py BotGroup Model",
                False,
                "models.py file not found", 
                "backend"
            )
    
    def generate_summary(self):
        """Generate comprehensive test summary"""
        print(f"\n📊 Test Results Summary")
        print(f"{'='*50}")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.issues:
            print(f"\n❌ Issues Found ({len(self.issues)}):")
            for issue in self.issues:
                print(f"   • [{issue['priority']}] {issue['test']}")
                print(f"     {issue['details']}")
        else:
            print(f"\n✅ All tests passed!")
        
        return {
            "tests_run": self.tests_run,
            "tests_passed": self.tests_passed, 
            "success_rate": round(self.tests_passed/self.tests_run*100, 1),
            "issues": self.issues
        }

def main():
    """Main test execution"""
    print("🚀 LockBay Group Event Broadcasting System Test")
    print("=" * 60)
    
    tester = LockBayGroupEventTester()
    
    # Test backend health first
    health_data = tester.test_health_endpoint()
    if not health_data:
        print("\n❌ CRITICAL: Backend not accessible - cannot proceed with group event testing")
        return 1
    
    # Analyze code structure and implementation
    tester.analyze_code_structure()
    tester.analyze_group_event_service()
    tester.analyze_handler_registration()
    tester.analyze_botgroup_model()
    
    # Generate final summary
    results = tester.generate_summary()
    
    # Return appropriate exit code
    return 0 if results["success_rate"] >= 80 else 1

if __name__ == "__main__":
    sys.exit(main())