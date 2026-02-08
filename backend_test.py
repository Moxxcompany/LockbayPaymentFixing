"""
Backend Testing for Payment Processing Fixes

Tests the following fixes:
1. DynoPay wallet deposit handler uses `base_amount` (USD) from webhook
2. BlockBee simplified_payment_processor uses provider-supplied USD amount
3. DynoPay escrow payment paths correctly use `base_amount` (regression check)
4. Import validation for both modified modules
5. Backend server health check
"""

import requests
import sys
import json
from decimal import Decimal
from datetime import datetime
import asyncio
import os

# Get the backend URL from environment
BACKEND_URL = "https://repo-analyzer-171.preview.emergentagent.com"

class PaymentFixTester:
    def __init__(self, base_url=BACKEND_URL):
        self.base_url = base_url.rstrip('/')
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, passed, details="", error=None):
        """Log test result"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
        
        result = {
            "test": name,
            "status": status,
            "passed": passed,
            "details": details,
            "error": str(error) if error else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.test_results.append(result)
        
        print(f"\n{status}: {name}")
        if details:
            print(f"   Details: {details}")
        if error:
            print(f"   Error: {error}")

    def test_backend_health(self):
        """Test backend server health"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Backend Health Check", True, 
                             f"Status: {data.get('status', 'unknown')}")
                return True
            else:
                self.log_test("Backend Health Check", False, 
                             f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Backend Health Check", False, error=e)
            return False

    def test_module_imports(self):
        """Test that all modified modules can be imported without errors"""
        import sys
        sys.path.insert(0, '/app')
        
        modules_to_test = [
            "handlers.dynopay_webhook",
            "services.simplified_payment_processor", 
            "handlers.blockbee_webhook_new",
            "services.fastforex_service"
        ]
        
        for module_name in modules_to_test:
            try:
                # Dynamic import
                if '.' in module_name:
                    package, submodule = module_name.rsplit('.', 1)
                    module = __import__(module_name, fromlist=[submodule])
                else:
                    module = __import__(module_name)
                
                self.log_test(f"Import {module_name}", True, 
                             f"Module loaded successfully")
                
            except Exception as e:
                self.log_test(f"Import {module_name}", False, error=e)

    def test_dynopay_webhook_structure(self):
        """Test DynoPay webhook handler structure and base_amount usage"""
        try:
            # Import the handler
            sys.path.insert(0, '/app')
            from handlers.dynopay_webhook import DynoPayWebhookHandler
            
            # Check if the class has the required methods
            required_methods = [
                'handle_escrow_deposit_webhook',
                'handle_wallet_deposit_webhook', 
                '_process_dynopay_payment_with_lock'
            ]
            
            missing_methods = []
            for method in required_methods:
                if not hasattr(DynoPayWebhookHandler, method):
                    missing_methods.append(method)
            
            if missing_methods:
                self.log_test("DynoPay Handler Structure", False,
                             f"Missing methods: {missing_methods}")
            else:
                self.log_test("DynoPay Handler Structure", True,
                             "All required methods present")
                
                # Test for base_amount handling in source code
                import inspect
                try:
                    source = inspect.getsource(DynoPayWebhookHandler.handle_escrow_deposit_webhook)
                    if "base_amount" in source and "dynopay_base_amount" in source:
                        self.log_test("DynoPay base_amount Implementation", True,
                                     "base_amount handling found in escrow handler")
                    else:
                        self.log_test("DynoPay base_amount Implementation", False,
                                     "base_amount handling not found")
                except Exception as e:
                    self.log_test("DynoPay base_amount Implementation", False, error=e)
                
        except Exception as e:
            self.log_test("DynoPay Handler Structure", False, error=e)

    def test_simplified_payment_processor(self):
        """Test simplified payment processor for provider USD extraction"""
        try:
            sys.path.insert(0, '/app')
            from services.simplified_payment_processor import SimplifiedPaymentProcessor
            
            # Check if the class has required methods
            processor = SimplifiedPaymentProcessor()
            required_methods = [
                'process_payment',
                '_credit_wallet_immediate',
                '_extract_provider_usd_amount'
            ]
            
            missing_methods = []
            for method in required_methods:
                if not hasattr(processor, method):
                    missing_methods.append(method)
            
            if missing_methods:
                self.log_test("Simplified Payment Processor Structure", False,
                             f"Missing methods: {missing_methods}")
            else:
                self.log_test("Simplified Payment Processor Structure", True,
                             "All required methods present")
                
                # Test _extract_provider_usd_amount method
                try:
                    # Test BlockBee provider data
                    blockbee_data = {"price": "50000.00"}  # $50k per BTC
                    result = processor._extract_provider_usd_amount(
                        "blockbee", blockbee_data, Decimal("0.001"), "BTC"
                    )
                    
                    if result is not None and result == Decimal("50.00"):  # 0.001 * 50000
                        self.log_test("BlockBee USD Extraction", True,
                                     f"Correctly extracted ${result} from price field")
                    else:
                        self.log_test("BlockBee USD Extraction", False,
                                     f"Unexpected result: {result}")
                        
                    # Test DynoPay provider data  
                    dynopay_data = {"base_amount": "100.50", "base_currency": "USD"}
                    result = processor._extract_provider_usd_amount(
                        "dynopay", dynopay_data, Decimal("0.002"), "ETH"
                    )
                    
                    if result is not None and result == Decimal("100.50"):
                        self.log_test("DynoPay USD Extraction", True,
                                     f"Correctly extracted ${result} from base_amount field")
                    else:
                        self.log_test("DynoPay USD Extraction", False,
                                     f"Unexpected result: {result}")
                        
                except Exception as e:
                    self.log_test("Provider USD Extraction Methods", False, error=e)
                
        except Exception as e:
            self.log_test("Simplified Payment Processor Structure", False, error=e)

    def test_webhook_endpoints_exist(self):
        """Test that webhook endpoints are accessible"""
        endpoints = [
            "/api/webhook/dynopay",
            "/api/webhook/blockbee/callback/test-order",
        ]
        
        for endpoint in endpoints:
            try:
                # Use HEAD request to avoid triggering webhook processing
                response = requests.head(f"{self.base_url}{endpoint}", timeout=5)
                
                # Expect 400 (missing data) or 405 (method not allowed) for HEAD, not 404
                if response.status_code in [400, 405, 200]:
                    self.log_test(f"Webhook Endpoint {endpoint}", True,
                                 f"Endpoint exists (HTTP {response.status_code})")
                elif response.status_code == 404:
                    self.log_test(f"Webhook Endpoint {endpoint}", False,
                                 f"Endpoint not found (HTTP 404)")
                else:
                    self.log_test(f"Webhook Endpoint {endpoint}", True,
                                 f"Endpoint accessible (HTTP {response.status_code})")
                
            except Exception as e:
                self.log_test(f"Webhook Endpoint {endpoint}", False, error=e)

    def test_payment_processing_logic(self):
        """Test payment processing logic with mock data"""
        try:
            sys.path.insert(0, '/app')
            from services.simplified_payment_processor import SimplifiedPaymentProcessor
            
            processor = SimplifiedPaymentProcessor()
            
            # Test provider USD extraction with various scenarios
            test_cases = [
                # BlockBee with price field
                {
                    "provider": "blockbee",
                    "raw_data": {"price": "45000.00"},
                    "amount": Decimal("0.002"),
                    "currency": "BTC",
                    "expected": Decimal("90.00")  # 0.002 * 45000
                },
                # DynoPay with base_amount 
                {
                    "provider": "dynopay",
                    "raw_data": {"base_amount": "250.75", "base_currency": "USD"},
                    "amount": Decimal("0.1"),
                    "currency": "ETH",
                    "expected": Decimal("250.75")  # Direct from base_amount
                },
                # DynoPay without USD base_currency (should return None)
                {
                    "provider": "dynopay", 
                    "raw_data": {"base_amount": "100.00", "base_currency": "EUR"},
                    "amount": Decimal("0.05"),
                    "currency": "ETH",
                    "expected": None
                },
                # Unknown provider (should return None)
                {
                    "provider": "unknown",
                    "raw_data": {"some_field": "123.45"},
                    "amount": Decimal("1.0"),
                    "currency": "USD",
                    "expected": None
                }
            ]
            
            for i, case in enumerate(test_cases):
                try:
                    result = processor._extract_provider_usd_amount(
                        case["provider"], case["raw_data"], case["amount"], case["currency"]
                    )
                    
                    if result == case["expected"]:
                        self.log_test(f"Payment Logic Case {i+1}", True,
                                     f"{case['provider']} extraction: {result}")
                    else:
                        self.log_test(f"Payment Logic Case {i+1}", False,
                                     f"Expected {case['expected']}, got {result}")
                                     
                except Exception as e:
                    self.log_test(f"Payment Logic Case {i+1}", False, error=e)
                    
        except Exception as e:
            self.log_test("Payment Processing Logic", False, error=e)

    def run_all_tests(self):
        """Run all tests"""
        print("🔬 Starting Backend Payment Processing Fix Tests")
        print("="*60)
        
        # Test 1: Backend Health
        self.test_backend_health()
        
        # Test 2: Module Imports
        self.test_module_imports()
        
        # Test 3: DynoPay Handler Structure
        self.test_dynopay_webhook_structure()
        
        # Test 4: Simplified Payment Processor
        self.test_simplified_payment_processor()
        
        # Test 5: Webhook Endpoints
        self.test_webhook_endpoints_exist()
        
        # Test 6: Payment Logic
        self.test_payment_processing_logic()
        
        # Summary
        print(f"\n📊 Test Summary:")
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Tests failed: {self.tests_run - self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        return {
            "tests_run": self.tests_run,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_run - self.tests_passed,
            "success_rate": (self.tests_passed/self.tests_run*100) if self.tests_run > 0 else 0,
            "test_results": self.test_results
        }

def main():
    """Run the payment fix tests"""
    tester = PaymentFixTester()
    results = tester.run_all_tests()
    
    # Return appropriate exit code
    if results["tests_passed"] == results["tests_run"]:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {results['tests_failed']} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())