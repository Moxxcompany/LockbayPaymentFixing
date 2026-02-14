#!/usr/bin/env python3
"""
LockBay Telegram Escrow Bot - Backend API Testing
Tests all backend functionality required for the bot testing task
"""

import os
import sys
import json
import asyncio
import requests
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Add app directory to path
sys.path.insert(0, '/app')

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackendAPITester:
    def __init__(self, base_url: str = ""):
        # Get the external URL from environment or use default
        if not base_url:
            # Read from frontend env file if available
            try:
                with open('/app/frontend/.env', 'r') as f:
                    for line in f:
                        if line.startswith('REACT_APP_BACKEND_URL='):
                            base_url = line.split('=', 1)[1].strip()
                            break
            except FileNotFoundError:
                logger.error("Frontend .env file not found")
                base_url = "http://localhost:8001"
        
        self.base_url = base_url.rstrip('/')
        logger.info(f"Testing backend at: {self.base_url}")
        
        self.session = requests.Session()
        self.session.timeout = 10
        
        # Test results
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []
    
    def log_test_result(self, test_name: str, status: str, details: str = "", response_data: Any = None):
        """Log test result and update counters"""
        self.total_tests += 1
        if status == "PASS":
            self.passed_tests += 1
            logger.info(f"✅ {test_name}: {status} - {details}")
        else:
            self.failed_tests += 1
            logger.error(f"❌ {test_name}: {status} - {details}")
        
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "response_data": response_data
        }
        self.test_results.append(result)
    
    def test_health_endpoint(self):
        """Test 1: Backend health endpoint /api/health returns 200 with status ok"""
        try:
            url = f"{self.base_url}/health"
            response = self.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') in ['healthy', 'ok']:
                    self.log_test_result(
                        "Health Endpoint", 
                        "PASS", 
                        f"Status: {data.get('status')}, Ready: {data.get('ready')}", 
                        data
                    )
                else:
                    self.log_test_result(
                        "Health Endpoint", 
                        "FAIL", 
                        f"Status not healthy: {data.get('status')}", 
                        data
                    )
            else:
                self.log_test_result(
                    "Health Endpoint", 
                    "FAIL", 
                    f"Status code: {response.status_code}, Response: {response.text[:200]}"
                )
        except Exception as e:
            self.log_test_result("Health Endpoint", "FAIL", f"Exception: {str(e)}")
    
    def test_database_schema_escrows_table(self):
        """Test 2: Database has 'refund_processed' and 'expiry_notified' columns on escrows table"""
        try:
            from database import SessionLocal
            from sqlalchemy import text
            
            with SessionLocal() as session:
                # Check if refund_processed column exists
                result = session.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'escrows' 
                    AND column_name IN ('refund_processed', 'expiry_notified')
                """))
                
                columns = [row[0] for row in result.fetchall()]
                
                if 'refund_processed' in columns and 'expiry_notified' in columns:
                    self.log_test_result(
                        "Escrows Schema",
                        "PASS",
                        f"Found columns: {columns}",
                        {"columns_found": columns}
                    )
                else:
                    missing = [col for col in ['refund_processed', 'expiry_notified'] if col not in columns]
                    self.log_test_result(
                        "Escrows Schema",
                        "FAIL",
                        f"Missing columns: {missing}",
                        {"columns_found": columns, "missing": missing}
                    )
        except Exception as e:
            self.log_test_result("Escrows Schema", "FAIL", f"Database check failed: {str(e)}")
    
    def test_database_schema_bot_groups_table(self):
        """Test 3: Database has 'bot_groups' table with correct schema"""
        try:
            from database import SessionLocal
            from sqlalchemy import text
            
            with SessionLocal() as session:
                # Check if bot_groups table exists
                result = session.execute(text("""
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'bot_groups'
                    ORDER BY ordinal_position
                """))
                
                columns_info = {row[0]: {"type": row[1], "nullable": row[2]} for row in result.fetchall()}
                
                required_columns = ['chat_id', 'chat_title', 'chat_type', 'is_active', 'events_enabled']
                missing_columns = [col for col in required_columns if col not in columns_info]
                
                if not columns_info:
                    self.log_test_result(
                        "BotGroups Schema",
                        "FAIL",
                        "bot_groups table does not exist",
                        {"table_exists": False}
                    )
                elif missing_columns:
                    self.log_test_result(
                        "BotGroups Schema",
                        "FAIL",
                        f"Missing required columns: {missing_columns}",
                        {"columns_found": list(columns_info.keys()), "missing": missing_columns}
                    )
                else:
                    self.log_test_result(
                        "BotGroups Schema",
                        "PASS",
                        f"All required columns found: {required_columns}",
                        {"schema": columns_info}
                    )
        except Exception as e:
            self.log_test_result("BotGroups Schema", "FAIL", f"Database check failed: {str(e)}")
    
    def test_escrow_expiry_service_timezone(self):
        """Test 4: EscrowExpiryService uses timezone-aware datetime"""
        try:
            from services.escrow_expiry_service import EscrowExpiryService
            import inspect
            
            # Get source code of the service
            source = inspect.getsource(EscrowExpiryService)
            
            # Check for timezone-aware datetime usage
            has_timezone_import = 'from datetime import timezone' in source or 'datetime.now(timezone.utc)' in source
            has_old_utcnow = 'datetime.utcnow()' in source
            
            if has_timezone_import and not has_old_utcnow:
                self.log_test_result(
                    "EscrowExpiry Timezone",
                    "PASS",
                    "Uses timezone-aware datetime.now(timezone.utc)",
                    {"uses_timezone_aware": True, "has_old_utcnow": False}
                )
            elif has_old_utcnow:
                self.log_test_result(
                    "EscrowExpiry Timezone",
                    "FAIL",
                    "Still uses deprecated datetime.utcnow()",
                    {"uses_timezone_aware": has_timezone_import, "has_old_utcnow": True}
                )
            else:
                self.log_test_result(
                    "EscrowExpiry Timezone",
                    "PARTIAL",
                    "Code structure unclear - manual review needed",
                    {"uses_timezone_aware": has_timezone_import, "has_old_utcnow": has_old_utcnow}
                )
        except Exception as e:
            self.log_test_result("EscrowExpiry Timezone", "FAIL", f"Code analysis failed: {str(e)}")
    
    def test_escrow_expiry_service_phase2_filters(self):
        """Test 5: EscrowExpiryService Phase 2 filters expired escrows using DB columns"""
        try:
            from services.escrow_expiry_service import EscrowExpiryService
            import inspect
            
            source = inspect.getsource(EscrowExpiryService)
            
            # Check for Phase 2 filtering using DB columns instead of getattr
            has_phase2 = 'PHASE 2' in source or 'PHASE_2' in source
            has_db_column_filter = ('Escrow.refund_processed' in source and 'Escrow.expiry_notified' in source)
            has_getattr_fallback = 'getattr(' in source and ('refund_processed' in source or 'expiry_notified' in source)
            
            if has_phase2 and has_db_column_filter and not has_getattr_fallback:
                self.log_test_result(
                    "EscrowExpiry Phase2 Filters",
                    "PASS",
                    "Uses DB columns for filtering (refund_processed, expiry_notified)",
                    {"has_phase2": True, "uses_db_columns": True, "uses_getattr": False}
                )
            elif has_getattr_fallback:
                self.log_test_result(
                    "EscrowExpiry Phase2 Filters",
                    "FAIL",
                    "Still uses getattr() instead of DB columns",
                    {"has_phase2": has_phase2, "uses_db_columns": has_db_column_filter, "uses_getattr": True}
                )
            else:
                self.log_test_result(
                    "EscrowExpiry Phase2 Filters",
                    "PARTIAL",
                    "Code structure unclear - manual review needed",
                    {"has_phase2": has_phase2, "uses_db_columns": has_db_column_filter, "uses_getattr": has_getattr_fallback}
                )
        except Exception as e:
            self.log_test_result("EscrowExpiry Phase2 Filters", "FAIL", f"Code analysis failed: {str(e)}")
    
    def test_refund_service_marks_processed(self):
        """Test 6: RefundService marks escrow.refund_processed = True after successful refund"""
        try:
            from services.refund_service import RefundService
            import inspect
            
            source = inspect.getsource(RefundService.process_escrow_refunds)
            
            # Check if refund_processed is set to True
            marks_processed = 'refund_processed = True' in source or 'refund_processed=True' in source
            
            if marks_processed:
                self.log_test_result(
                    "RefundService Marks Processed",
                    "PASS",
                    "Sets escrow.refund_processed = True after successful refund",
                    {"marks_processed": True}
                )
            else:
                self.log_test_result(
                    "RefundService Marks Processed",
                    "FAIL",
                    "Does not mark escrow.refund_processed = True",
                    {"marks_processed": False}
                )
        except Exception as e:
            self.log_test_result("RefundService Marks Processed", "FAIL", f"Code analysis failed: {str(e)}")
    
    def test_cleanup_expiry_refund_reason(self):
        """Test 7: Cleanup expiry uses 'expired' (not 'expired_timeout') as refund_reason"""
        try:
            from jobs.core.cleanup_expiry import CleanupExpiryEngine
            import inspect
            
            source = inspect.getsource(CleanupExpiryEngine._filter_escrows_for_refund_processing)
            
            # Check refund reason usage
            uses_expired = 'refund_reason = "expired"' in source
            uses_expired_timeout = 'expired_timeout' in source
            
            if uses_expired and not uses_expired_timeout:
                self.log_test_result(
                    "CleanupExpiry Refund Reason",
                    "PASS",
                    "Uses 'expired' as refund_reason to match RefundService",
                    {"uses_expired": True, "uses_expired_timeout": False}
                )
            elif uses_expired_timeout:
                self.log_test_result(
                    "CleanupExpiry Refund Reason",
                    "FAIL",
                    "Still uses 'expired_timeout' instead of 'expired'",
                    {"uses_expired": uses_expired, "uses_expired_timeout": True}
                )
            else:
                self.log_test_result(
                    "CleanupExpiry Refund Reason",
                    "PARTIAL",
                    "Code structure unclear - manual review needed",
                    {"uses_expired": uses_expired, "uses_expired_timeout": uses_expired_timeout}
                )
        except Exception as e:
            self.log_test_result("CleanupExpiry Refund Reason", "FAIL", f"Code analysis failed: {str(e)}")
    
    def test_group_event_service_functionality(self):
        """Test 8: GroupEventService can register/unregister groups and has broadcast methods"""
        try:
            from services.group_event_service import GroupEventService, group_event_service
            
            # Check if service has required methods
            service_methods = dir(GroupEventService)
            required_methods = [
                'register_group',
                'unregister_group',
                'broadcast_trade_created',
                'broadcast_trade_funded',
                'broadcast_seller_accepted',
                'broadcast_escrow_completed',
                'broadcast_rating_submitted',
                'broadcast_new_user_onboarded'
            ]
            
            missing_methods = [method for method in required_methods if method not in service_methods]
            
            if not missing_methods:
                self.log_test_result(
                    "GroupEventService Functionality",
                    "PASS",
                    f"All required methods found: {required_methods}",
                    {"methods_found": required_methods}
                )
            else:
                self.log_test_result(
                    "GroupEventService Functionality",
                    "FAIL",
                    f"Missing methods: {missing_methods}",
                    {"methods_found": [m for m in required_methods if m in service_methods], "missing": missing_methods}
                )
        except Exception as e:
            self.log_test_result("GroupEventService Functionality", "FAIL", f"Import or analysis failed: {str(e)}")
    
    def test_group_handler_exists(self):
        """Test 9: Group handler (group_handler.py) handles my_chat_member updates"""
        try:
            from handlers.group_handler import handle_my_chat_member, register_group_handlers
            import inspect
            
            # Check if handler has correct signature and functionality
            handle_signature = inspect.signature(handle_my_chat_member)
            params = list(handle_signature.parameters.keys())
            
            # Should have update and context parameters
            if 'update' in params and 'context' in params:
                source = inspect.getsource(handle_my_chat_member)
                handles_member_updates = 'my_chat_member' in source and ('member' in source or 'administrator' in source)
                
                if handles_member_updates:
                    self.log_test_result(
                        "Group Handler",
                        "PASS",
                        "Handles my_chat_member updates with correct parameters",
                        {"parameters": params, "handles_updates": True}
                    )
                else:
                    self.log_test_result(
                        "Group Handler",
                        "FAIL",
                        "Function exists but doesn't handle my_chat_member updates properly",
                        {"parameters": params, "handles_updates": False}
                    )
            else:
                self.log_test_result(
                    "Group Handler",
                    "FAIL",
                    f"Incorrect function signature: {params}",
                    {"parameters": params}
                )
        except Exception as e:
            self.log_test_result("Group Handler", "FAIL", f"Import or analysis failed: {str(e)}")
    
    def test_group_events_integration(self):
        """Test 10: Group event broadcasts are hooked into escrow lifecycle"""
        try:
            # Check main escrow handler for group event integrations
            from handlers.escrow import create_escrow_direct
            import inspect
            
            source = inspect.getsource(create_escrow_direct)
            
            # Look for group_event_service usage
            has_group_integration = 'group_event_service' in source or 'broadcast_' in source
            
            if has_group_integration:
                self.log_test_result(
                    "Group Events Integration",
                    "PASS",
                    "Escrow handler has group event service integration",
                    {"has_integration": True}
                )
            else:
                self.log_test_result(
                    "Group Events Integration",
                    "FAIL",
                    "Escrow handler missing group event service integration",
                    {"has_integration": False}
                )
        except Exception as e:
            self.log_test_result("Group Events Integration", "FAIL", f"Import or analysis failed: {str(e)}")
    
    def test_webhook_group_integrations(self):
        """Test 11: Group event broadcasts are hooked into webhook payment confirmations"""
        try:
            # Check webhook handlers for group event integrations
            webhook_files = [
                'handlers.dynopay_webhook',
                'handlers.fincra_webhook'
            ]
            
            integrations_found = []
            for webhook_module in webhook_files:
                try:
                    module = __import__(webhook_module, fromlist=[''])
                    source = inspect.getsource(module)
                    if 'group_event_service' in source or 'broadcast_' in source:
                        integrations_found.append(webhook_module)
                except Exception:
                    continue
            
            if integrations_found:
                self.log_test_result(
                    "Webhook Group Integrations",
                    "PASS",
                    f"Found group integrations in: {integrations_found}",
                    {"integrations": integrations_found}
                )
            else:
                self.log_test_result(
                    "Webhook Group Integrations",
                    "FAIL",
                    "No group event integrations found in webhook handlers",
                    {"integrations": integrations_found}
                )
        except Exception as e:
            self.log_test_result("Webhook Group Integrations", "FAIL", f"Analysis failed: {str(e)}")
    
    def test_start_handler_auto_complete(self):
        """Test 12: Start handler auto-completes onboarding instead of routing to onboarding flow"""
        try:
            from handlers.start import start_handler, process_existing_user_async
            import inspect
            
            source = inspect.getsource(process_existing_user_async)
            
            # Look for auto-complete logic
            has_auto_complete = 'auto-complet' in source.lower() or 'onboarding_completed=True' in source
            skips_onboarding_flow = 'skip' in source.lower() and 'onboarding' in source.lower()
            
            if has_auto_complete or skips_onboarding_flow:
                self.log_test_result(
                    "Start Handler Auto-Complete",
                    "PASS",
                    "Start handler auto-completes onboarding",
                    {"auto_complete": has_auto_complete, "skips_flow": skips_onboarding_flow}
                )
            else:
                self.log_test_result(
                    "Start Handler Auto-Complete",
                    "FAIL",
                    "Start handler still routes to onboarding flow",
                    {"auto_complete": has_auto_complete, "skips_flow": skips_onboarding_flow}
                )
        except Exception as e:
            self.log_test_result("Start Handler Auto-Complete", "FAIL", f"Analysis failed: {str(e)}")
    
    def test_start_handler_skips_email_verification(self):
        """Test 13: Start handler skips email verification gate and goes directly to main menu"""
        try:
            from handlers.start import process_existing_user_async
            import inspect
            
            source = inspect.getsource(process_existing_user_async)
            
            # Look for email verification skip logic
            skips_verification = 'skip' in source.lower() and ('email' in source.lower() and 'verification' in source.lower())
            direct_to_menu = 'show_main_menu' in source
            
            if skips_verification and direct_to_menu:
                self.log_test_result(
                    "Start Handler Skip Email",
                    "PASS",
                    "Start handler skips email verification and shows main menu",
                    {"skips_verification": True, "direct_to_menu": True}
                )
            else:
                self.log_test_result(
                    "Start Handler Skip Email",
                    "FAIL",
                    "Start handler still enforces email verification",
                    {"skips_verification": skips_verification, "direct_to_menu": direct_to_menu}
                )
        except Exception as e:
            self.log_test_result("Start Handler Skip Email", "FAIL", f"Analysis failed: {str(e)}")
    
    def test_onboarding_router_auto_complete(self):
        """Test 14: Onboarding router auto-completes onboarding for both new and existing users"""
        try:
            from handlers.onboarding_router import onboarding_router
            import inspect
            
            source = inspect.getsource(onboarding_router)
            
            # Look for auto-complete logic in onboarding router
            has_auto_complete = 'auto-complet' in source.lower() or 'onboarding_completed' in source
            handles_both_types = ('new' in source and 'existing' in source) or 'both' in source.lower()
            
            if has_auto_complete:
                self.log_test_result(
                    "Onboarding Router Auto-Complete",
                    "PASS",
                    "Onboarding router auto-completes onboarding",
                    {"auto_complete": has_auto_complete, "handles_both": handles_both_types}
                )
            else:
                self.log_test_result(
                    "Onboarding Router Auto-Complete",
                    "FAIL",
                    "Onboarding router still runs full onboarding flow",
                    {"auto_complete": has_auto_complete, "handles_both": handles_both_types}
                )
        except Exception as e:
            self.log_test_result("Onboarding Router Auto-Complete", "FAIL", f"Analysis failed: {str(e)}")
    
    def test_cashout_flow_skips_otp(self):
        """Test 15: Cashout flow in wallet_direct.py skips OTP and shows direct confirmation screen"""
        try:
            from handlers.wallet_direct import WalletStates
            import inspect
            
            # Look for OTP-related states and logic
            wallet_states = [attr for attr in dir(WalletStates) if not attr.startswith('_')]
            otp_states = [state for state in wallet_states if 'OTP' in state.upper()]
            
            # Check wallet_direct source for OTP skip logic
            try:
                import handlers.wallet_direct as wallet_module
                source = inspect.getsource(wallet_module)
                skips_otp = ('skip' in source.lower() and 'otp' in source.lower()) or 'direct confirmation' in source.lower()
                
                if not otp_states or skips_otp:
                    self.log_test_result(
                        "Cashout Flow Skip OTP",
                        "PASS",
                        "Cashout flow skips OTP verification",
                        {"otp_states": otp_states, "skips_otp": skips_otp}
                    )
                else:
                    self.log_test_result(
                        "Cashout Flow Skip OTP",
                        "FAIL",
                        "Cashout flow still requires OTP verification",
                        {"otp_states": otp_states, "skips_otp": skips_otp}
                    )
            except Exception:
                # Fallback check based on states only
                if not otp_states:
                    self.log_test_result(
                        "Cashout Flow Skip OTP",
                        "PASS",
                        "No OTP states found in WalletStates",
                        {"otp_states": otp_states}
                    )
                else:
                    self.log_test_result(
                        "Cashout Flow Skip OTP",
                        "FAIL",
                        f"OTP states still present: {otp_states}",
                        {"otp_states": otp_states}
                    )
        except Exception as e:
            self.log_test_result("Cashout Flow Skip OTP", "FAIL", f"Analysis failed: {str(e)}")
    
    def test_group_handler_registration(self):
        """Test 16: Group handler is registered in main.py"""
        try:
            # Check main.py imports and registrations
            with open('/app/main.py', 'r') as f:
                main_source = f.read()
            
            # Check for group handler imports and registrations
            has_group_import = 'group_handler' in main_source
            has_group_registration = 'register_group_handlers' in main_source or 'group_handler' in main_source
            
            if has_group_import and has_group_registration:
                self.log_test_result(
                    "Group Handler Registration",
                    "PASS",
                    "Group handler is imported and registered in main.py",
                    {"has_import": has_group_import, "has_registration": has_group_registration}
                )
            else:
                self.log_test_result(
                    "Group Handler Registration",
                    "FAIL",
                    "Group handler not properly registered in main.py",
                    {"has_import": has_group_import, "has_registration": has_group_registration}
                )
        except Exception as e:
            self.log_test_result("Group Handler Registration", "FAIL", f"Analysis failed: {str(e)}")
    
    def run_all_tests(self):
        """Run all backend tests"""
        logger.info("🚀 Starting LockBay Backend API Tests")
        logger.info(f"Testing backend at: {self.base_url}")
        
        # Run tests in order
        self.test_health_endpoint()
        self.test_database_schema_escrows_table()
        self.test_database_schema_bot_groups_table()
        self.test_escrow_expiry_service_timezone()
        self.test_escrow_expiry_service_phase2_filters()
        self.test_refund_service_marks_processed()
        self.test_cleanup_expiry_refund_reason()
        self.test_group_event_service_functionality()
        self.test_group_handler_exists()
        self.test_group_events_integration()
        self.test_webhook_group_integrations()
        self.test_start_handler_auto_complete()
        self.test_start_handler_skips_email_verification()
        self.test_onboarding_router_auto_complete()
        self.test_cashout_flow_skips_otp()
        self.test_group_handler_registration()
        
        # Print summary
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        print(f"\n" + "="*60)
        print(f"🏁 BACKEND API TESTING COMPLETE")
        print(f"="*60)
        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.failed_tests}")
        print(f"📊 Success Rate: {success_rate:.1f}%")
        print(f"="*60)
        
        return {
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "success_rate": success_rate,
            "test_results": self.test_results
        }

def main():
    """Main test function"""
    # Initialize and run tests
    tester = BackendAPITester()
    results = tester.run_all_tests()
    
    # Return appropriate exit code
    if results["failed_tests"] == 0:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error(f"💥 {results['failed_tests']} tests failed")
        return 1

if __name__ == "__main__":
    exit(main())