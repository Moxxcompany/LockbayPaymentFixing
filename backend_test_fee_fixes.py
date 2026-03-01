#!/usr/bin/env python3
"""
Comprehensive test suite for LockBay fee calculation bug fixes
Testing two specific bugs:
1. Minimum escrow fee of $10 was not applied at exactly $100 threshold (used < instead of <=)
2. When buyer chose 'split' fee and then cancelled, buyer only lost their half of the fee - they should pay the FULL platform fee on cancellation
"""

import sys
import os
import requests
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any

# Add the project root to the Python path
sys.path.insert(0, '/app')

# Load environment variables from backend/.env
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

# Import the FeeCalculator after loading environment
from utils.fee_calculator import FeeCalculator


class LockBayFeeTestSuite:
    def __init__(self, base_url="https://pod-config-deploy.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
            if details:
                print(f"   {details}")
        else:
            print(f"❌ {name}")
            if details:
                print(f"   {details}")
        
        self.test_results.append({
            "name": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def test_backend_health(self) -> bool:
        """Test backend health endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                success = data.get("status") == "ok"
                self.log_test(
                    "Backend health endpoint", 
                    success, 
                    f"Status: {data.get('status')}, Service: {data.get('service')}"
                )
                return success
            else:
                self.log_test(
                    "Backend health endpoint", 
                    False, 
                    f"Status code: {response.status_code}"
                )
                return False
        except Exception as e:
            self.log_test("Backend health endpoint", False, f"Error: {str(e)}")
            return False

    def test_minimum_fee_threshold_exact(self) -> bool:
        """Test Bug Fix #1: Minimum fee should apply at exactly $100"""
        try:
            # Test at exactly $100 - should get $10 minimum fee
            result = FeeCalculator.calculate_escrow_breakdown(
                escrow_amount=Decimal("100.0"),
                fee_split_option='buyer_pays'
            )
            
            expected_fee = Decimal("10.0")  # Minimum fee
            actual_fee = result["total_platform_fee"]
            
            success = actual_fee == expected_fee
            self.log_test(
                "Minimum fee at exactly $100 threshold",
                success,
                f"Expected: ${expected_fee}, Got: ${actual_fee}"
            )
            return success
            
        except Exception as e:
            self.log_test(
                "Minimum fee at exactly $100 threshold", 
                False, 
                f"Error: {str(e)}"
            )
            return False

    def test_minimum_fee_below_threshold(self) -> bool:
        """Test minimum fee applies below $100 threshold"""
        try:
            # Test at $50 - should get $10 minimum fee
            result = FeeCalculator.calculate_escrow_breakdown(
                escrow_amount=Decimal("50.0"),
                fee_split_option='buyer_pays'
            )
            
            expected_fee = Decimal("10.0")  # Minimum fee
            actual_fee = result["total_platform_fee"]
            
            success = actual_fee == expected_fee
            self.log_test(
                "Minimum fee below threshold ($50)",
                success,
                f"Expected: ${expected_fee}, Got: ${actual_fee}"
            )
            return success
            
        except Exception as e:
            self.log_test(
                "Minimum fee below threshold ($50)", 
                False, 
                f"Error: {str(e)}"
            )
            return False

    def test_fee_above_threshold_no_minimum(self) -> bool:
        """Test fee calculation above threshold (no minimum fee)"""
        try:
            # Test at $200 - should get 5% of $200 = $10, no minimum needed
            result = FeeCalculator.calculate_escrow_breakdown(
                escrow_amount=Decimal("200.0"),
                fee_split_option='buyer_pays'
            )
            
            expected_fee = Decimal("10.0")  # 5% of $200
            actual_fee = result["total_platform_fee"]
            
            success = actual_fee == expected_fee
            self.log_test(
                "Fee calculation above threshold ($200)",
                success,
                f"Expected: ${expected_fee}, Got: ${actual_fee}"
            )
            return success
            
        except Exception as e:
            self.log_test(
                "Fee calculation above threshold ($200)", 
                False, 
                f"Error: {str(e)}"
            )
            return False

    def test_fee_split_calculation(self) -> bool:
        """Test fee split calculation for $100"""
        try:
            # Test split fee at $100 - should split $10 minimum fee
            result = FeeCalculator.calculate_escrow_breakdown(
                escrow_amount=Decimal("100.0"),
                fee_split_option='split'
            )
            
            expected_total_fee = Decimal("10.0")  # Minimum fee
            expected_buyer_fee = Decimal("5.0")   # Half
            expected_seller_fee = Decimal("5.0")  # Half
            expected_refundable = Decimal("95.0") # $100 - $5 seller fee
            
            success = (
                result["total_platform_fee"] == expected_total_fee and
                result["buyer_fee_amount"] == expected_buyer_fee and
                result["seller_fee_amount"] == expected_seller_fee and
                result["refundable_amount"] == expected_refundable
            )
            
            self.log_test(
                "Split fee calculation ($100)",
                success,
                f"Total: ${result['total_platform_fee']}, Buyer: ${result['buyer_fee_amount']}, Seller: ${result['seller_fee_amount']}, Refundable: ${result['refundable_amount']}"
            )
            return success
            
        except Exception as e:
            self.log_test(
                "Split fee calculation ($100)", 
                False, 
                f"Error: {str(e)}"
            )
            return False

    def test_fee_split_calculation_300(self) -> bool:
        """Test fee split calculation for $300 (above threshold)"""
        try:
            # Test split fee at $300 - should split $15 fee (5% of $300)
            result = FeeCalculator.calculate_escrow_breakdown(
                escrow_amount=Decimal("300.0"),
                fee_split_option='split'
            )
            
            expected_total_fee = Decimal("15.0")   # 5% of $300
            expected_buyer_fee = Decimal("7.5")    # Half
            expected_seller_fee = Decimal("7.5")   # Half
            expected_refundable = Decimal("292.5") # $300 - $7.5 seller fee
            
            success = (
                result["total_platform_fee"] == expected_total_fee and
                result["buyer_fee_amount"] == expected_buyer_fee and
                result["seller_fee_amount"] == expected_seller_fee and
                result["refundable_amount"] == expected_refundable
            )
            
            self.log_test(
                "Split fee calculation ($300)",
                success,
                f"Total: ${result['total_platform_fee']}, Buyer: ${result['buyer_fee_amount']}, Seller: ${result['seller_fee_amount']}, Refundable: ${result['refundable_amount']}"
            )
            return success
            
        except Exception in e:
            self.log_test(
                "Split fee calculation ($300)", 
                False, 
                f"Error: {str(e)}"
            )
            return False

    def test_cancellation_refund_split_fee_fix(self) -> bool:
        """Test Bug Fix #2: Split fee cancellation - buyer pays FULL platform fee"""
        try:
            # Test cancellation refund calculation for split fee
            result = FeeCalculator.calculate_cancellation_refund_breakdown(
                escrow_amount=100.0,
                buyer_fee_amount=5.0,  # Buyer paid $5
                seller_fee_amount=5.0, # Seller was supposed to pay $5
                fee_split_option='split'
            )
            
            # With the fix: buyer should lose FULL $10 platform fee on cancellation
            expected_refund = Decimal("95.0")        # $100 - $5 (seller fee deducted)
            expected_platform_keeps = Decimal("10.0") # Full $10 fee (buyer $5 + seller $5)
            
            success = (
                result["refund_amount"] == expected_refund and
                result["platform_keeps"] == expected_platform_keeps
            )
            
            self.log_test(
                "Split fee cancellation refund (Bug Fix #2)",
                success,
                f"Refund: ${result['refund_amount']}, Platform keeps: ${result['platform_keeps']} (Full fee: ${result['buyer_fee_paid']} + ${result['seller_fee_not_collected']})"
            )
            return success
            
        except Exception as e:
            self.log_test(
                "Split fee cancellation refund (Bug Fix #2)", 
                False, 
                f"Error: {str(e)}"
            )
            return False

    def test_cancellation_refund_buyer_pays(self) -> bool:
        """Test cancellation refund for buyer_pays option (should be unchanged)"""
        try:
            # Test cancellation refund calculation for buyer_pays
            result = FeeCalculator.calculate_cancellation_refund_breakdown(
                escrow_amount=100.0,
                buyer_fee_amount=10.0,  # Buyer paid full $10
                seller_fee_amount=0.0,  # Seller pays nothing
                fee_split_option='buyer_pays'
            )
            
            # Buyer_pays: buyer loses only what they paid ($10)
            expected_refund = Decimal("90.0")        # $100 - $10 (buyer fee)
            expected_platform_keeps = Decimal("10.0") # $10 fee buyer paid
            
            success = (
                result["refund_amount"] == expected_refund and
                result["platform_keeps"] == expected_platform_keeps
            )
            
            self.log_test(
                "Buyer pays cancellation refund",
                success,
                f"Refund: ${result['refund_amount']}, Platform keeps: ${result['platform_keeps']}"
            )
            return success
            
        except Exception as e:
            self.log_test(
                "Buyer pays cancellation refund", 
                False, 
                f"Error: {str(e)}"
            )
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return summary"""
        print(f"🔍 LockBay Fee Calculation Bug Fix Test Suite")
        print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 Backend URL: {self.base_url}")
        print("=" * 80)
        
        # Test backend connectivity first
        if not self.test_backend_health():
            print("❌ Backend health check failed - aborting tests")
            return self.get_summary()
        
        print("\n📊 Testing Bug Fix #1: Minimum Fee Threshold")
        print("-" * 50)
        self.test_minimum_fee_threshold_exact()
        self.test_minimum_fee_below_threshold()
        self.test_fee_above_threshold_no_minimum()
        
        print("\n📊 Testing Fee Split Calculations")
        print("-" * 50)
        self.test_fee_split_calculation()
        self.test_fee_split_calculation_300()
        
        print("\n📊 Testing Bug Fix #2: Split Fee Cancellation")
        print("-" * 50)
        self.test_cancellation_refund_split_fee_fix()
        self.test_cancellation_refund_buyer_pays()
        
        return self.get_summary()

    def get_summary(self) -> Dict[str, Any]:
        """Get test summary"""
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        return {
            "tests_run": self.tests_run,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_run - self.tests_passed,
            "success_rate": f"{success_rate:.1f}%",
            "test_results": self.test_results,
            "backend_url": self.base_url,
            "timestamp": datetime.now().isoformat()
        }


def main():
    """Run the test suite"""
    tester = LockBayFeeTestSuite()
    summary = tester.run_all_tests()
    
    print("\n" + "=" * 80)
    print("📋 TEST SUMMARY")
    print("=" * 80)
    print(f"Tests Run: {summary['tests_run']}")
    print(f"Tests Passed: {summary['tests_passed']}")
    print(f"Tests Failed: {summary['tests_failed']}")
    print(f"Success Rate: {summary['success_rate']}")
    
    # List failed tests
    failed_tests = [test for test in summary['test_results'] if not test['success']]
    if failed_tests:
        print("\n❌ FAILED TESTS:")
        for test in failed_tests:
            print(f"  • {test['name']}: {test['details']}")
    else:
        print("\n✅ ALL TESTS PASSED!")
    
    # Return exit code based on success
    return 0 if summary['tests_passed'] == summary['tests_run'] else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)