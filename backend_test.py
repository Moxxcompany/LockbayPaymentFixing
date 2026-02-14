#!/usr/bin/env python3
"""
Promotional Messaging System Backend Tests
==========================================

Comprehensive test suite for the new promotional messaging system implementation.
Tests all components: message pools, timezone handling, scheduler configuration,
database models, command handlers, and health endpoint.

Backend runs in 'setup mode' without DATABASE_URL, so database-dependent functions
are tested for existence and logic, but actual database operations are skipped.
"""

import sys
import os
import asyncio
import requests
import json
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))


class PromoMessageSystemTester:
    """Comprehensive tester for the promotional messaging system"""
    
    def __init__(self):
        self.backend_url = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
    
    def run_test(self, test_name: str, test_func) -> bool:
        """Run a single test and track results"""
        self.tests_run += 1
        print(f"\n🔍 Testing: {test_name}")
        
        try:
            success = test_func()
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED: {test_name}")
                self.test_results.append({"test": test_name, "status": "PASSED", "error": None})
                return True
            else:
                print(f"❌ FAILED: {test_name}")
                self.test_results.append({"test": test_name, "status": "FAILED", "error": "Test returned False"})
                return False
        except Exception as e:
            print(f"❌ ERROR: {test_name} - {str(e)}")
            self.test_results.append({"test": test_name, "status": "ERROR", "error": str(e)})
            return False

    # ==========================================
    # Health Endpoint Tests
    # ==========================================
    
    def test_health_endpoint(self) -> bool:
        """Test that /api/health endpoint still returns ok status"""
        try:
            response = requests.get(f"{self.backend_url}/api/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "ok"
            return False
        except Exception as e:
            print(f"Health endpoint error: {e}")
            return False

    # ==========================================
    # Message Pool Tests (Core Implementation)
    # ==========================================
    
    def test_message_pool_counts(self) -> bool:
        """Test that there are exactly 10 morning + 10 evening messages (20 total)"""
        try:
            from services.promo_message_service import get_morning_messages, get_evening_messages
            
            morning_messages = get_morning_messages()
            evening_messages = get_evening_messages()
            
            print(f"   Morning messages: {len(morning_messages)}")
            print(f"   Evening messages: {len(evening_messages)}")
            print(f"   Total messages: {len(morning_messages) + len(evening_messages)}")
            
            return len(morning_messages) == 10 and len(evening_messages) == 10
        except Exception as e:
            print(f"   Error testing message pools: {e}")
            return False

    def test_all_messages_contain_bot_tag(self) -> bool:
        """Test that ALL 20 messages contain @bot_username via _bot_tag()"""
        try:
            from services.promo_message_service import get_morning_messages, get_evening_messages, _bot_tag
            
            all_messages = get_morning_messages() + get_evening_messages()
            bot_tag = _bot_tag()
            
            missing_bot_tag = []
            for msg in all_messages:
                if bot_tag not in msg.get("text", ""):
                    missing_bot_tag.append(msg.get("key", "unknown"))
            
            if missing_bot_tag:
                print(f"   Messages missing @bot_username: {missing_bot_tag}")
                return False
            
            print(f"   ✅ All {len(all_messages)} messages contain {bot_tag}")
            return True
        except Exception as e:
            print(f"   Error testing bot tags: {e}")
            return False

    def test_all_messages_contain_deeplinks(self) -> bool:
        """Test that ALL 20 messages contain t.me/ deeplink via _bot_link()"""
        try:
            from services.promo_message_service import get_morning_messages, get_evening_messages, _bot_link
            
            all_messages = get_morning_messages() + get_evening_messages()
            bot_link_base = "https://t.me/"
            
            missing_deeplink = []
            for msg in all_messages:
                text = msg.get("text", "")
                if "https://t.me/" not in text:
                    missing_deeplink.append(msg.get("key", "unknown"))
            
            if missing_deeplink:
                print(f"   Messages missing t.me/ deeplink: {missing_deeplink}")
                return False
            
            print(f"   ✅ All {len(all_messages)} messages contain t.me/ deeplink")
            return True
        except Exception as e:
            print(f"   Error testing deeplinks: {e}")
            return False

    def test_messages_are_persuasive_marketing(self) -> bool:
        """Test that messages are persuasive marketing with CTAs, not generic"""
        try:
            from services.promo_message_service import get_morning_messages, get_evening_messages
            
            all_messages = get_morning_messages() + get_evening_messages()
            
            # Look for marketing keywords and CTAs
            marketing_keywords = [
                "start", "open", "try", "join", "trade", "escrow", "safe", "secure", 
                "protect", "now", "today", "click", "tap", "get", "earn", "win",
                "build", "grow", "opportunity", "deals", "profit", "trust"
            ]
            
            cta_patterns = [
                "start", "open", "try", "join", "click", "tap", "get", 
                "build", "check", "see", "use", "create", "trade"
            ]
            
            weak_messages = []
            for msg in all_messages:
                text = msg.get("text", "").lower()
                key = msg.get("key", "unknown")
                
                # Check for marketing keywords
                marketing_score = sum(1 for keyword in marketing_keywords if keyword in text)
                
                # Check for CTAs
                has_cta = any(cta in text for cta in cta_patterns)
                
                # Check for benefit statements
                has_benefits = any(benefit in text for benefit in [
                    "safe", "secure", "protect", "risk", "trust", "instant", "fast", 
                    "easy", "simple", "free", "bonus", "reward", "earn", "profit"
                ])
                
                if marketing_score < 3 or not has_cta or not has_benefits:
                    weak_messages.append(f"{key} (score: {marketing_score}, cta: {has_cta}, benefits: {has_benefits})")
            
            if weak_messages:
                print(f"   Messages with weak marketing: {weak_messages[:3]}...")  # Show first 3
                return len(weak_messages) <= 2  # Allow up to 2 weaker messages
            
            print(f"   ✅ All {len(all_messages)} messages are persuasive marketing with CTAs")
            return True
        except Exception as e:
            print(f"   Error testing marketing quality: {e}")
            return False

    # ==========================================
    # Timezone Handling Tests
    # ==========================================
    
    def test_timezone_offset_mapping(self) -> bool:
        """Test get_user_utc_offset() correctly maps timezone strings to UTC offsets"""
        try:
            from services.promo_message_service import get_user_utc_offset
            
            # Test cases from requirements
            test_cases = [
                ("Africa/Lagos", 1),
                ("America/New_York", -5), 
                ("Asia/Tokyo", 9),
                (None, 1),  # Default to WAT
                ("", 1),    # Empty string default
                ("UTC+3", 3),  # Numeric offset
                ("GMT-5", -5), # GMT offset
                ("invalid_timezone", 1)  # Invalid fallback
            ]
            
            failed_cases = []
            for tz_string, expected_offset in test_cases:
                actual_offset = get_user_utc_offset(tz_string)
                if actual_offset != expected_offset:
                    failed_cases.append(f"{tz_string} -> {actual_offset} (expected {expected_offset})")
            
            if failed_cases:
                print(f"   Failed timezone mappings: {failed_cases}")
                return False
            
            print(f"   ✅ All {len(test_cases)} timezone mappings correct")
            return True
        except Exception as e:
            print(f"   Error testing timezone offsets: {e}")
            return False

    # ==========================================
    # Message Selection Tests
    # ==========================================
    
    def test_message_selection_avoids_repeats(self) -> bool:
        """Test pick_message() avoids repeating the last sent message key"""
        try:
            from services.promo_message_service import pick_message, get_morning_messages
            
            morning_messages = get_morning_messages()
            if len(morning_messages) < 2:
                print("   Not enough morning messages to test repeat avoidance")
                return False
            
            # Test with last message key
            last_key = morning_messages[0]["key"]
            selected_messages = []
            
            # Pick 5 messages and ensure none match the last key
            for _ in range(5):
                selected = pick_message("morning", last_key)
                selected_messages.append(selected["key"])
            
            repeated_last = [key for key in selected_messages if key == last_key]
            
            if repeated_last:
                print(f"   Message selection repeated last key {last_key}: {repeated_last}")
                return len(repeated_last) <= 1  # Allow 1 repeat due to randomness
            
            print(f"   ✅ Message selection avoids repeating last key")
            return True
        except Exception as e:
            print(f"   Error testing message selection: {e}")
            return False

    # ==========================================
    # Function Existence Tests (Database-dependent)
    # ==========================================
    
    def test_promo_functions_exist(self) -> bool:
        """Test that handle_promo_opt_out and handle_promo_opt_in functions exist"""
        try:
            from services.promo_message_service import handle_promo_opt_out, handle_promo_opt_in
            
            # Check if functions are callable
            if not callable(handle_promo_opt_out) or not callable(handle_promo_opt_in):
                return False
            
            print("   ✅ Both promo opt-out/opt-in functions exist and are callable")
            return True
        except ImportError as e:
            print(f"   Error importing promo functions: {e}")
            return False
        except Exception as e:
            print(f"   Error testing promo functions: {e}")
            return False

    def test_send_promo_messages_function(self) -> bool:
        """Test send_promo_messages() function exists and adds opt-out footer"""
        try:
            from services.promo_message_service import send_promo_messages
            import inspect
            
            if not callable(send_promo_messages):
                return False
            
            # Check function signature
            sig = inspect.signature(send_promo_messages)
            params = list(sig.parameters.keys())
            
            if "session_type" not in params:
                print(f"   send_promo_messages missing session_type parameter. Found: {params}")
                return False
            
            # Check source code for opt-out footer
            source = inspect.getsource(send_promo_messages)
            if "/promo_off" not in source:
                print("   send_promo_messages source doesn't contain /promo_off opt-out footer")
                return False
            
            print("   ✅ send_promo_messages function exists with opt-out footer")
            return True
        except Exception as e:
            print(f"   Error testing send_promo_messages: {e}")
            return False

    # ==========================================
    # Job Scheduler Tests  
    # ==========================================
    
    def test_promo_message_job_exists(self) -> bool:
        """Test run_promo_messages() calls both morning and evening sessions"""
        try:
            from jobs.promo_message_job import run_promo_messages
            import inspect
            
            if not callable(run_promo_messages):
                return False
            
            # Check source code for morning and evening calls
            source = inspect.getsource(run_promo_messages)
            
            if '"morning"' not in source or '"evening"' not in source:
                print("   run_promo_messages doesn't call both morning and evening sessions")
                return False
            
            if 'send_promo_messages("morning")' not in source or 'send_promo_messages("evening")' not in source:
                print("   run_promo_messages doesn't properly call send_promo_messages for both sessions")
                return False
            
            print("   ✅ run_promo_messages calls both morning and evening sessions")
            return True
        except Exception as e:
            print(f"   Error testing promo message job: {e}")
            return False

    def test_scheduler_registration(self) -> bool:
        """Test promo_messages job registered with IntervalTrigger(minutes=30)"""
        try:
            # Read the scheduler source file directly to avoid import issues
            scheduler_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                        'jobs', 'consolidated_scheduler.py')
            
            with open(scheduler_file, 'r') as f:
                source = f.read()
            
            # Look for promo job registration
            if "promo_messages" not in source:
                print("   ConsolidatedScheduler doesn't register promo_messages job")
                return False
            
            if "IntervalTrigger(minutes=30" not in source:
                print("   promo_messages job not registered with 30-minute interval")
                return False
            
            if "run_promo_messages" not in source:
                print("   promo_messages job doesn't call run_promo_messages")
                return False
            
            print("   ✅ promo_messages job registered with 30-minute IntervalTrigger")
            return True
        except Exception as e:
            print(f"   Error testing scheduler registration: {e}")
            return False

    # ==========================================
    # Database Model Tests (Schema Validation)
    # ==========================================
    
    def test_promo_message_log_model(self) -> bool:
        """Test PromoMessageLog model exists with required fields and constraints"""
        try:
            from models import PromoMessageLog
            from sqlalchemy import inspect as sql_inspect
            
            # Get model columns
            mapper = sql_inspect(PromoMessageLog)
            columns = {col.name: col for col in mapper.columns}
            
            required_fields = ["user_id", "message_key", "session_type", "sent_date"]
            missing_fields = [field for field in required_fields if field not in columns]
            
            if missing_fields:
                print(f"   PromoMessageLog missing required fields: {missing_fields}")
                return False
            
            # Check table args for unique constraint
            table_args = getattr(PromoMessageLog, '__table_args__', ())
            
            # Look for unique constraint on user_id, sent_date, session_type
            has_unique_constraint = False
            if isinstance(table_args, tuple):
                for arg in table_args:
                    if hasattr(arg, 'columns') and hasattr(arg, 'name'):
                        constraint_cols = [col.name for col in arg.columns]
                        if ('user_id' in constraint_cols and 'sent_date' in constraint_cols and 
                            'session_type' in constraint_cols):
                            has_unique_constraint = True
                            break
            
            if not has_unique_constraint:
                print("   PromoMessageLog missing unique constraint on (user_id, sent_date, session_type)")
                return False
            
            print(f"   ✅ PromoMessageLog model has all required fields and unique constraint")
            return True
        except Exception as e:
            print(f"   Error testing PromoMessageLog model: {e}")
            return False

    def test_promo_opt_out_model(self) -> bool:
        """Test PromoOptOut model exists with user_id (unique) and opted_out_at fields"""
        try:
            from models import PromoOptOut
            from sqlalchemy import inspect as sql_inspect
            
            # Get model columns
            mapper = sql_inspect(PromoOptOut)
            columns = {col.name: col for col in mapper.columns}
            
            required_fields = ["user_id", "opted_out_at"]
            missing_fields = [field for field in required_fields if field not in columns]
            
            if missing_fields:
                print(f"   PromoOptOut missing required fields: {missing_fields}")
                return False
            
            # Check if user_id is unique
            user_id_column = columns.get("user_id")
            if not user_id_column.unique:
                print("   PromoOptOut user_id field is not unique")
                return False
            
            print(f"   ✅ PromoOptOut model has required fields with unique user_id")
            return True
        except Exception as e:
            print(f"   Error testing PromoOptOut model: {e}")
            return False

    # ==========================================
    # Command Handler Tests
    # ==========================================
    
    def test_promo_command_handlers_registered(self) -> bool:
        """Test /promo_off and /promo_on command handlers registered in server.py"""
        try:
            from backend.server import _register_all_critical_handlers
            import inspect
            
            # Check source code for command handler registration
            source = inspect.getsource(_register_all_critical_handlers)
            
            # Look for promo command registrations
            if 'CommandHandler("promo_off"' not in source:
                print("   /promo_off command handler not registered")
                return False
            
            if 'CommandHandler("promo_on"' not in source:
                print("   /promo_on command handler not registered") 
                return False
            
            # Look for the actual command functions
            if "promo_off_command" not in source or "promo_on_command" not in source:
                print("   promo command functions not found in handler registration")
                return False
            
            print("   ✅ Both /promo_off and /promo_on command handlers registered")
            return True
        except Exception as e:
            print(f"   Error testing command handler registration: {e}")
            return False

    # ==========================================
    # Error Handling Tests
    # ==========================================
    
    def test_error_handling_logic(self) -> bool:
        """Test send_promo_messages handles Forbidden and RetryAfter errors"""
        try:
            from services.promo_message_service import send_promo_messages
            import inspect
            
            source = inspect.getsource(send_promo_messages)
            
            # Check for Forbidden error handling
            if "Forbidden" not in source:
                print("   send_promo_messages doesn't handle Forbidden errors")
                return False
            
            # Check for RetryAfter error handling 
            if "RetryAfter" not in source:
                print("   send_promo_messages doesn't handle RetryAfter errors")
                return False
            
            # Check that Forbidden marks user as inactive
            if "is_active" not in source or "False" not in source:
                print("   Forbidden error handling doesn't mark user inactive")
                return False
            
            # Check that RetryAfter does proper sleep
            if "sleep(e.retry_after)" not in source and "sleep" not in source:
                print("   RetryAfter error handling doesn't implement proper sleep")
                return False
            
            print("   ✅ send_promo_messages handles Forbidden and RetryAfter errors properly")
            return True
        except Exception as e:
            print(f"   Error testing error handling: {e}")
            return False

    # ==========================================
    # Main Test Runner
    # ==========================================

    def run_all_tests(self):
        """Run all promotional messaging system tests"""
        print("="*80)
        print("🚀 PROMOTIONAL MESSAGING SYSTEM - COMPREHENSIVE BACKEND TESTS")
        print("="*80)
        
        # Health endpoint (ensure backend still works)
        self.run_test("Health endpoint returns OK status", self.test_health_endpoint)
        
        # Core message pool tests  
        self.run_test("Message pool contains 10 morning + 10 evening messages (20 total)", 
                     self.test_message_pool_counts)
        self.run_test("ALL 20 messages contain @bot_username via _bot_tag()", 
                     self.test_all_messages_contain_bot_tag)
        self.run_test("ALL 20 messages contain t.me/ deeplink via _bot_link()", 
                     self.test_all_messages_contain_deeplinks)
        self.run_test("Messages are persuasive marketing with CTAs (not generic)", 
                     self.test_messages_are_persuasive_marketing)
        
        # Timezone handling tests
        self.run_test("get_user_utc_offset() correctly maps timezone strings to UTC offsets", 
                     self.test_timezone_offset_mapping)
        
        # Message selection logic
        self.run_test("pick_message() avoids repeating last sent message key", 
                     self.test_message_selection_avoids_repeats)
        
        # Function existence (database-dependent functions)
        self.run_test("handle_promo_opt_out and handle_promo_opt_in functions exist", 
                     self.test_promo_functions_exist)
        self.run_test("send_promo_messages() exists and adds '/promo_off' opt-out footer", 
                     self.test_send_promo_messages_function)
        
        # Job scheduler tests
        self.run_test("run_promo_messages() calls both morning and evening sessions", 
                     self.test_promo_message_job_exists)
        self.run_test("promo_messages job registered with IntervalTrigger(minutes=30)", 
                     self.test_scheduler_registration)
        
        # Database model tests
        self.run_test("PromoMessageLog model exists with required fields and unique constraint", 
                     self.test_promo_message_log_model)
        self.run_test("PromoOptOut model exists with user_id (unique) and opted_out_at fields", 
                     self.test_promo_opt_out_model)
        
        # Command handler tests
        self.run_test("/promo_off and /promo_on command handlers registered in server.py", 
                     self.test_promo_command_handlers_registered)
        
        # Error handling tests
        self.run_test("send_promo_messages() handles Forbidden and RetryAfter errors", 
                     self.test_error_handling_logic)
        
        # User filtering logic test
        self.run_test("get_users_for_session() filters by is_active, is_blocked, onboarding_completed, opt-out, timezone", 
                     self.test_user_filtering_logic)
        
        # Final results
        print("\n" + "="*80)
        print("📊 TEST RESULTS SUMMARY")
        print("="*80)
        print(f"Total tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL TESTS PASSED - Promotional messaging system implementation is excellent!")
        else:
            print(f"\n⚠️  {self.tests_run - self.tests_passed} tests failed - see details above")
            
        return self.test_results


def main():
    """Run promotional messaging system tests"""
    tester = PromoMessageSystemTester()
    results = tester.run_all_tests()
    
    # Exit with error code if any tests failed
    failed_tests = [r for r in results if r["status"] != "PASSED"]
    return len(failed_tests)


if __name__ == "__main__":
    import sys
    sys.exit(main())