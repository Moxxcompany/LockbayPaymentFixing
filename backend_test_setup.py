#!/usr/bin/env python3
"""
LockBay Telegram Escrow Bot - Setup Mode Backend Testing
Tests the minimal status endpoints when running in setup mode
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, Any

class LockBaySetupTester:
    def __init__(self):
        # Read backend URL from frontend env
        self.base_url = ""
        try:
            with open('/app/frontend/.env', 'r') as f:
                for line in f:
                    if line.startswith('REACT_APP_BACKEND_URL='):
                        self.base_url = line.split('=', 1)[1].strip()
                        break
        except FileNotFoundError:
            self.base_url = "http://localhost:8001"
        
        self.base_url = self.base_url.rstrip('/')
        print(f"Testing backend at: {self.base_url}")
        
        self.session = requests.Session()
        self.session.timeout = 10
        
        self.total_tests = 0
        self.passed_tests = 0
        self.test_results = []
    
    def test_result(self, test_name: str, passed: bool, details: str = "", response_data: Any = None):
        """Record test result"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            print(f"✅ {test_name}: PASS - {details}")
        else:
            print(f"❌ {test_name}: FAIL - {details}")
        
        self.test_results.append({
            "test": test_name,
            "status": "PASS" if passed else "FAIL",
            "details": details,
            "response_data": response_data,
            "timestamp": datetime.now().isoformat()
        })
    
    def test_health_endpoint(self):
        """Test /api/health endpoint"""
        try:
            url = f"{self.base_url}/api/health"
            response = self.session.get(url)
            
            if response.status_code != 200:
                self.test_result(
                    "Health Endpoint Status", 
                    False, 
                    f"Expected 200, got {response.status_code}: {response.text[:200]}"
                )
                return
            
            data = response.json()
            
            # Check required fields
            required_fields = ['status', 'service', 'mode', 'config', 'next_steps']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                self.test_result(
                    "Health Endpoint Structure",
                    False,
                    f"Missing fields: {missing_fields}",
                    data
                )
                return
            
            # Check status is 'ok'
            if data.get('status') != 'ok':
                self.test_result(
                    "Health Status Check",
                    False,
                    f"Expected status 'ok', got '{data.get('status')}'",
                    data
                )
            else:
                self.test_result("Health Status Check", True, "Status is 'ok'", data)
            
            # Check mode is 'setup'
            if data.get('mode') != 'setup':
                self.test_result(
                    "Health Mode Check",
                    False,
                    f"Expected mode 'setup', got '{data.get('mode')}'",
                    data
                )
            else:
                self.test_result("Health Mode Check", True, "Mode is 'setup'", data)
            
            # Check service name
            if data.get('service') != 'lockbay-status':
                self.test_result(
                    "Health Service Check",
                    False,
                    f"Expected service 'lockbay-status', got '{data.get('service')}'",
                    data
                )
            else:
                self.test_result("Health Service Check", True, "Service is 'lockbay-status'", data)
            
            # Check config structure
            config = data.get('config', {})
            expected_config = ['database_url', 'bot_token']
            config_missing = [field for field in expected_config if field not in config]
            
            if config_missing:
                self.test_result(
                    "Health Config Structure",
                    False,
                    f"Config missing fields: {config_missing}",
                    data
                )
            else:
                self.test_result("Health Config Structure", True, "Config has required fields", data)
                
                # Check config values are 'missing' (expected in setup mode)
                if config.get('database_url') == 'missing' and config.get('bot_token') == 'missing':
                    self.test_result("Health Config Values", True, "Both config values are 'missing' as expected", data)
                else:
                    self.test_result(
                        "Health Config Values", 
                        False, 
                        f"Expected missing configs, got db={config.get('database_url')}, bot={config.get('bot_token')}", 
                        data
                    )
            
            # Check next_steps array
            next_steps = data.get('next_steps', [])
            if not isinstance(next_steps, list):
                self.test_result("Health Next Steps Type", False, "next_steps should be an array", data)
            else:
                self.test_result("Health Next Steps Type", True, f"next_steps array has {len(next_steps)} items", data)
                
                # Should contain setup instructions
                if len(next_steps) >= 2:
                    db_step_found = any('DATABASE_URL' in step for step in next_steps)
                    bot_step_found = any('TELEGRAM_BOT_TOKEN' in step for step in next_steps)
                    
                    if db_step_found and bot_step_found:
                        self.test_result("Health Next Steps Content", True, "Contains DATABASE_URL and BOT_TOKEN setup steps", data)
                    else:
                        self.test_result("Health Next Steps Content", False, "Missing expected setup steps", data)
                else:
                    self.test_result("Health Next Steps Content", False, f"Expected at least 2 steps, got {len(next_steps)}", data)
            
        except requests.exceptions.RequestException as e:
            self.test_result("Health Endpoint", False, f"Request failed: {str(e)}")
        except json.JSONDecodeError as e:
            self.test_result("Health Endpoint", False, f"Invalid JSON response: {str(e)}")
        except Exception as e:
            self.test_result("Health Endpoint", False, f"Unexpected error: {str(e)}")
    
    def test_status_endpoint(self):
        """Test /api/status endpoint"""
        try:
            url = f"{self.base_url}/api/status"
            response = self.session.get(url)
            
            if response.status_code != 200:
                self.test_result(
                    "Status Endpoint",
                    False,
                    f"Expected 200, got {response.status_code}: {response.text[:200]}"
                )
                return
            
            data = response.json()
            
            # Check required fields
            required_fields = ['app', 'version', 'environment', 'components']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                self.test_result(
                    "Status Endpoint Structure",
                    False,
                    f"Missing fields: {missing_fields}",
                    data
                )
                return
            
            # Check app name
            if data.get('app') != 'LockBay Telegram Escrow Bot':
                self.test_result(
                    "Status App Name",
                    False,
                    f"Expected 'LockBay Telegram Escrow Bot', got '{data.get('app')}'",
                    data
                )
            else:
                self.test_result("Status App Name", True, "App name is correct", data)
            
            # Check components structure
            components = data.get('components', {})
            expected_components = ['fastapi_server', 'postgresql', 'telegram_bot', 'redis']
            
            components_missing = [comp for comp in expected_components if comp not in components]
            if components_missing:
                self.test_result(
                    "Status Components Structure",
                    False,
                    f"Missing components: {components_missing}",
                    data
                )
            else:
                self.test_result("Status Components Structure", True, "All expected components present", data)
                
                # Check component statuses
                if components.get('fastapi_server') == 'running':
                    self.test_result("Status FastAPI Component", True, "FastAPI server running", data)
                else:
                    self.test_result("Status FastAPI Component", False, f"Expected 'running', got '{components.get('fastapi_server')}'", data)
                
                if components.get('postgresql') == 'not configured':
                    self.test_result("Status PostgreSQL Component", True, "PostgreSQL not configured (expected)", data)
                else:
                    self.test_result("Status PostgreSQL Component", False, f"Expected 'not configured', got '{components.get('postgresql')}'", data)
                
                if components.get('telegram_bot') == 'not configured':
                    self.test_result("Status Telegram Component", True, "Telegram bot not configured (expected)", data)
                else:
                    self.test_result("Status Telegram Component", False, f"Expected 'not configured', got '{components.get('telegram_bot')}'", data)
            
        except requests.exceptions.RequestException as e:
            self.test_result("Status Endpoint", False, f"Request failed: {str(e)}")
        except json.JSONDecodeError as e:
            self.test_result("Status Endpoint", False, f"Invalid JSON response: {str(e)}")
        except Exception as e:
            self.test_result("Status Endpoint", False, f"Unexpected error: {str(e)}")
    
    def test_root_endpoint(self):
        """Test /api/ root endpoint"""
        try:
            url = f"{self.base_url}/api/"
            response = self.session.get(url)
            
            if response.status_code != 200:
                self.test_result(
                    "Root Endpoint",
                    False,
                    f"Expected 200, got {response.status_code}: {response.text[:200]}"
                )
                return
            
            data = response.json()
            
            # Check for message and mode
            if 'message' not in data:
                self.test_result("Root Endpoint Message", False, "Missing 'message' field", data)
            else:
                message = data['message']
                if 'LockBay Telegram Escrow Bot' in message and 'Status Server' in message:
                    self.test_result("Root Endpoint Message", True, "Message contains expected content", data)
                else:
                    self.test_result("Root Endpoint Message", False, f"Unexpected message: {message}", data)
            
            if data.get('mode') != 'setup':
                self.test_result("Root Endpoint Mode", False, f"Expected mode 'setup', got '{data.get('mode')}'", data)
            else:
                self.test_result("Root Endpoint Mode", True, "Mode is 'setup'", data)
            
        except requests.exceptions.RequestException as e:
            self.test_result("Root Endpoint", False, f"Request failed: {str(e)}")
        except json.JSONDecodeError as e:
            self.test_result("Root Endpoint", False, f"Invalid JSON response: {str(e)}")
        except Exception as e:
            self.test_result("Root Endpoint", False, f"Unexpected error: {str(e)}")
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting LockBay Setup Mode Backend Tests")
        print(f"Testing backend at: {self.base_url}")
        print("="*60)
        
        self.test_health_endpoint()
        print()
        self.test_status_endpoint()
        print()
        self.test_root_endpoint()
        
        # Summary
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        print("\n" + "="*60)
        print("🏁 BACKEND TESTING COMPLETE")
        print("="*60)
        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.total_tests - self.passed_tests}")
        print(f"📊 Success Rate: {success_rate:.1f}%")
        print("="*60)
        
        return {
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.total_tests - self.passed_tests,
            "success_rate": success_rate,
            "test_results": self.test_results
        }

def main():
    """Main test function"""
    tester = LockBaySetupTester()
    results = tester.run_all_tests()
    
    return 0 if results["failed_tests"] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())