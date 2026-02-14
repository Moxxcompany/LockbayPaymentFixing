#!/usr/bin/env python3
"""
LockBay Status Server Backend Tests
==================================

Test suite for the LockBay Telegram Bot status server endpoints.
Tests the /health, /status, and / endpoints when running in setup mode
without DATABASE_URL and TELEGRAM_BOT_TOKEN configured.
"""

import sys
import os
import requests
import json
from datetime import datetime
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))


class StatusServerTester:
    """Test the LockBay status server endpoints"""
    
    def __init__(self):
        self.backend_url = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        print(f"Testing backend at: {self.backend_url}")
    
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
    
    def test_health_endpoint_structure(self) -> bool:
        """Test /api/health endpoint returns proper JSON with status, config, and next_steps"""
        try:
            response = requests.get(f"{self.backend_url}/api/health", timeout=10)
            if response.status_code != 200:
                print(f"   Health endpoint returned status {response.status_code}")
                return False
            
            data = response.json()
            print(f"   Health response: {json.dumps(data, indent=2)}")
            
            # Check required top-level fields
            required_fields = ['status', 'config', 'next_steps']
            for field in required_fields:
                if field not in data:
                    print(f"   Missing required field: {field}")
                    return False
            
            # Check status is 'ok'
            if data['status'] != 'ok':
                print(f"   Status is not 'ok': {data['status']}")
                return False
                
            # Check config structure
            config = data['config']
            if not isinstance(config, dict):
                print("   Config is not a dictionary")
                return False
                
            config_fields = ['database_url', 'bot_token']
            for field in config_fields:
                if field not in config:
                    print(f"   Config missing field: {field}")
                    return False
                    
            # Check next_steps is a list
            if not isinstance(data['next_steps'], list):
                print("   next_steps is not a list")
                return False
            
            # Check service field exists
            if 'service' not in data:
                print("   Missing service field")
                return False
                
            # Check mode field exists  
            if 'mode' not in data:
                print("   Missing mode field")
                return False
                
            print("   ✅ Health endpoint has proper JSON structure")
            return True
            
        except Exception as e:
            print(f"   Health endpoint error: {e}")
            return False

    def test_health_endpoint_config_status(self) -> bool:
        """Test health endpoint shows missing config correctly"""
        try:
            response = requests.get(f"{self.backend_url}/api/health", timeout=10)
            data = response.json()
            
            config = data['config']
            
            # Since DATABASE_URL and TELEGRAM_BOT_TOKEN are not configured, they should show as 'missing'
            if config['database_url'] != 'missing':
                print(f"   Expected database_url to be 'missing', got: {config['database_url']}")
                return False
                
            if config['bot_token'] != 'missing':
                print(f"   Expected bot_token to be 'missing', got: {config['bot_token']}")
                return False
                
            # Check that next_steps contains proper guidance
            next_steps = data['next_steps']
            
            db_step_found = any('DATABASE_URL' in step for step in next_steps)
            token_step_found = any('TELEGRAM_BOT_TOKEN' in step or 'BOT_TOKEN' in step for step in next_steps)
            
            if not db_step_found:
                print("   next_steps missing DATABASE_URL guidance")
                return False
                
            if not token_step_found:
                print("   next_steps missing bot token guidance")
                return False
                
            print("   ✅ Health endpoint correctly shows missing config and provides guidance")
            return True
            
        except Exception as e:
            print(f"   Health config test error: {e}")
            return False

    # ==========================================
    # Status Endpoint Tests  
    # ==========================================
    
    def test_status_endpoint_structure(self) -> bool:
        """Test /api/status endpoint returns app info with proper structure"""
        try:
            response = requests.get(f"{self.backend_url}/api/status", timeout=10)
            if response.status_code != 200:
                print(f"   Status endpoint returned status {response.status_code}")
                return False
            
            data = response.json()
            print(f"   Status response: {json.dumps(data, indent=2)}")
            
            # Check required fields
            required_fields = ['app', 'version', 'environment', 'components']
            for field in required_fields:
                if field not in data:
                    print(f"   Missing required field: {field}")
                    return False
            
            # Check app name
            if 'LockBay' not in data['app']:
                print(f"   App name doesn't contain 'LockBay': {data['app']}")
                return False
                
            # Check components structure
            components = data['components']
            if not isinstance(components, dict):
                print("   Components is not a dictionary")
                return False
                
            expected_components = ['fastapi_server', 'postgresql', 'telegram_bot', 'redis']
            for component in expected_components:
                if component not in components:
                    print(f"   Missing component: {component}")
                    return False
                    
            print("   ✅ Status endpoint has proper structure and required fields")
            return True
            
        except Exception as e:
            print(f"   Status endpoint error: {e}")
            return False

    def test_status_endpoint_component_status(self) -> bool:
        """Test status endpoint shows correct component statuses"""
        try:
            response = requests.get(f"{self.backend_url}/api/status", timeout=10)
            data = response.json()
            
            components = data['components']
            
            # FastAPI server should be running
            if components['fastapi_server'] != 'running':
                print(f"   FastAPI server status incorrect: {components['fastapi_server']}")
                return False
                
            # PostgreSQL should show not configured (since no DATABASE_URL)
            if components['postgresql'] != 'not configured':
                print(f"   PostgreSQL status should be 'not configured': {components['postgresql']}")
                return False
                
            # Telegram bot should show not configured (since no BOT_TOKEN)
            if components['telegram_bot'] != 'not configured':
                print(f"   Telegram bot status should be 'not configured': {components['telegram_bot']}")
                return False
                
            # Redis should be optional
            if components['redis'] != 'optional':
                print(f"   Redis status should be 'optional': {components['redis']}")
                return False
                
            print("   ✅ Status endpoint shows correct component statuses")
            return True
            
        except Exception as e:
            print(f"   Status component test error: {e}")
            return False

    # ==========================================
    # Root Endpoint Tests
    # ==========================================
    
    def test_root_endpoint(self) -> bool:
        """Test root / endpoint returns message"""
        try:
            response = requests.get(f"{self.backend_url}/api/", timeout=10)
            if response.status_code != 200:
                print(f"   Root endpoint returned status {response.status_code}")
                return False
            
            data = response.json()
            print(f"   Root response: {json.dumps(data, indent=2)}")
            
            # Check message field exists
            if 'message' not in data:
                print("   Missing message field")
                return False
                
            message = data['message']
            if not isinstance(message, str):
                print("   Message is not a string")
                return False
                
            # Check message contains LockBay
            if 'LockBay' not in message:
                print(f"   Message doesn't contain 'LockBay': {message}")
                return False
                
            # Check mode field
            if 'mode' not in data:
                print("   Missing mode field")
                return False
                
            if data['mode'] != 'setup':
                print(f"   Mode should be 'setup': {data['mode']}")
                return False
                
            print("   ✅ Root endpoint returns proper message and mode")
            return True
            
        except Exception as e:
            print(f"   Root endpoint error: {e}")
            return False

    # ==========================================
    # API Prefix Tests
    # ==========================================
    
    def test_api_prefix_handling(self) -> bool:
        """Test that /api prefix is properly handled by the middleware"""
        try:
            # Test direct endpoint without /api prefix (should work due to middleware)
            response1 = requests.get(f"{self.backend_url}/health", timeout=10)
            response2 = requests.get(f"{self.backend_url}/api/health", timeout=10)
            
            # Both should return the same result
            if response1.status_code != response2.status_code:
                print(f"   API prefix handling inconsistent: {response1.status_code} vs {response2.status_code}")
                return False
                
            if response1.status_code == 200:
                data1 = response1.json()
                data2 = response2.json() 
                
                if data1 != data2:
                    print("   API prefix middleware not working - responses differ")
                    return False
                    
            print("   ✅ API prefix middleware working correctly")
            return True
            
        except Exception as e:
            print(f"   API prefix test error: {e}")
            return False

    # ==========================================
    # Main Test Runner
    # ==========================================

    def run_all_tests(self):
        """Run all status server tests"""
        print("="*80)
        print("🚀 LOCKBAY STATUS SERVER - BACKEND ENDPOINT TESTS")
        print("="*80)
        
        # Health endpoint tests
        self.run_test("Health endpoint returns proper JSON with status, config, and next_steps", 
                     self.test_health_endpoint_structure)
        self.run_test("Health endpoint shows correct config status (missing DB/token)", 
                     self.test_health_endpoint_config_status)
        
        # Status endpoint tests  
        self.run_test("Status endpoint returns app info with proper structure", 
                     self.test_status_endpoint_structure)
        self.run_test("Status endpoint shows correct component statuses", 
                     self.test_status_endpoint_component_status)
        
        # Root endpoint tests
        self.run_test("Root / endpoint returns message", 
                     self.test_root_endpoint)
        
        # API prefix tests
        self.run_test("API prefix middleware handles /api prefix correctly", 
                     self.test_api_prefix_handling)
        
        # Final results
        print("\n" + "="*80)
        print("📊 TEST RESULTS SUMMARY")
        print("="*80)
        print(f"Total tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL BACKEND TESTS PASSED - Status server endpoints working correctly!")
        else:
            print(f"\n⚠️  {self.tests_run - self.tests_passed} tests failed - see details above")
            
        return self.test_results


def main():
    """Run status server backend tests"""
    tester = StatusServerTester()
    results = tester.run_all_tests()
    
    # Exit with error code if any tests failed
    failed_tests = [r for r in results if r["status"] != "PASSED"]
    return len(failed_tests)


if __name__ == "__main__":
    import sys
    sys.exit(main())