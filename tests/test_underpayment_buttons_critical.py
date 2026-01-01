"""
CRITICAL E2E TEST: Underpayment Action Buttons
Tests the EXACT bug that was fixed: Large underpayments should show buttons (not auto-refund)
"""
import pytest
from decimal import Decimal
from services.enhanced_payment_tolerance_service import EnhancedPaymentToleranceService, PaymentResponse


class TestCriticalUnderpaymentFix:
    """Test the critical fix: Large underpayments OUTSIDE tolerance show buttons"""
    
    @pytest.mark.asyncio
    async def test_large_underpayment_shows_buttons_NOT_autorefund(self):
        """
        CRITICAL FIX TEST: Large underpayment (54% short) should show buttons
        
        Previous Behavior: AUTO_REFUND → Database constraint error ❌
        Fixed Behavior: SELF_SERVICE → Show 3 action buttons ✅
        """
        # Real scenario from production logs
        expected = Decimal("21.00")
        received = Decimal("9.57")
        shortage = expected - received
        shortage_pct = (shortage / expected * 100).quantize(Decimal("0.1"))
        
        print(f"\n📊 Test Scenario:")
        print(f"   Expected: ${expected}")
        print(f"   Received: ${received}")
        print(f"   Shortage: ${shortage} ({shortage_pct}% short)")
        
        decision = EnhancedPaymentToleranceService.analyze_payment_variance(
            expected_amount_usd=expected,
            received_amount_usd=received,
            transaction_type="escrow"
        )
        
        # CRITICAL ASSERTION: Must show buttons (NOT auto-refund)
        assert decision.response_type == PaymentResponse.SELF_SERVICE, \
            f"❌ FAILED: Large underpayment returned {decision.response_type.value} instead of SELF_SERVICE"
        
        # Verify all 3 action buttons exist
        assert "complete_payment" in decision.action_options, "Missing 'Complete Payment' button"
        assert "proceed_partial" in decision.action_options, "Missing 'Proceed Partial' button"
        assert "cancel_refund" in decision.action_options, "Missing 'Cancel & Refund' button"
        
        # Verify button amounts are correct
        assert decision.action_options["complete_payment"]["amount_needed"] == Decimal("11.43")
        assert decision.action_options["proceed_partial"]["escrow_amount"] == Decimal("9.57")
        assert decision.action_options["cancel_refund"]["refund_amount"] == Decimal("9.57")
        
        print(f"✅ CRITICAL FIX VERIFIED: Large underpayment shows 3 action buttons")
        print(f"   💳 Complete Payment: +${shortage}")
        print(f"   📉 Proceed Partial: ${received} escrow")
        print(f"   ❌ Cancel & Refund: ${received} to wallet")
    
    @pytest.mark.asyncio
    async def test_moderate_underpayment_shows_buttons(self):
        """Test moderate underpayment (25% short) shows buttons"""
        expected = Decimal("100.00")
        received = Decimal("75.00")
        
        decision = EnhancedPaymentToleranceService.analyze_payment_variance(
            expected_amount_usd=expected,
            received_amount_usd=received,
            transaction_type="escrow"
        )
        
        assert decision.response_type == PaymentResponse.SELF_SERVICE
        assert "complete_payment" in decision.action_options
        assert "proceed_partial" in decision.action_options
        assert "cancel_refund" in decision.action_options
        
        print("✅ PASSED: Moderate underpayment (25% short) shows buttons")
    
    @pytest.mark.asyncio
    async def test_extreme_underpayment_shows_buttons(self):
        """Test extreme underpayment (90% short) shows buttons"""
        expected = Decimal("100.00")
        received = Decimal("10.00")
        
        decision = EnhancedPaymentToleranceService.analyze_payment_variance(
            expected_amount_usd=expected,
            received_amount_usd=received,
            transaction_type="escrow"
        )
        
        assert decision.response_type == PaymentResponse.SELF_SERVICE
        print("✅ PASSED: Extreme underpayment (90% short) shows buttons")
    
    @pytest.mark.asyncio
    async def test_tiny_underpayment_within_tolerance_auto_accepts(self):
        """
        CORRECT BEHAVIOR: Tiny underpayment WITHIN tolerance should AUTO_ACCEPT
        This is NOT a bug - payments within tolerance proceed automatically
        """
        expected = Decimal("21.00")
        received = Decimal("20.00")  # $1 short, but within 5% tolerance
        
        decision = EnhancedPaymentToleranceService.analyze_payment_variance(
            expected_amount_usd=expected,
            received_amount_usd=received,
            transaction_type="escrow"
        )
        
        # This should AUTO_ACCEPT (not show buttons) - within tolerance
        assert decision.response_type == PaymentResponse.AUTO_ACCEPT
        print("✅ PASSED: Tiny underpayment within tolerance auto-accepts (correct behavior)")
    
    @pytest.mark.asyncio
    async def test_all_significant_underpayments_show_buttons(self):
        """
        Comprehensive test: All significant underpayments (OUTSIDE tolerance) show buttons
        """
        test_cases = [
            (Decimal("100.00"), Decimal("90.00"), "10% short"),
            (Decimal("100.00"), Decimal("75.00"), "25% short"),
            (Decimal("100.00"), Decimal("50.00"), "50% short"),
            (Decimal("100.00"), Decimal("25.00"), "75% short"),
            (Decimal("100.00"), Decimal("10.00"), "90% short"),
            (Decimal("21.00"), Decimal("9.57"), "Real scenario (54% short)"),
            (Decimal("50.00"), Decimal("20.00"), "60% short"),
        ]
        
        print(f"\n📊 Testing {len(test_cases)} significant underpayment scenarios:")
        
        passed = 0
        for expected, received, description in test_cases:
            decision = EnhancedPaymentToleranceService.analyze_payment_variance(
                expected_amount_usd=expected,
                received_amount_usd=received,
                transaction_type="escrow"
            )
            
            if decision.response_type == PaymentResponse.SELF_SERVICE:
                print(f"   ✅ ${expected} → ${received} ({description})")
                passed += 1
            else:
                print(f"   ❌ ${expected} → ${received} ({description}) - Got {decision.response_type.value}")
        
        assert passed == len(test_cases), f"Only {passed}/{len(test_cases)} scenarios showed buttons"
        print(f"\n✅ ALL {len(test_cases)} SIGNIFICANT UNDERPAYMENTS SHOW BUTTONS")


@pytest.mark.asyncio
async def run_critical_tests():
    """Run critical underpayment button tests"""
    test_suite = TestCriticalUnderpaymentFix()
    
    print("\n" + "="*80)
    print("🔥 CRITICAL FIX VALIDATION: Underpayment Action Buttons")
    print("="*80)
    
    tests = [
        ("CRITICAL: Large underpayment shows buttons (NOT auto-refund)", 
         test_suite.test_large_underpayment_shows_buttons_NOT_autorefund),
        ("Moderate underpayment shows buttons", 
         test_suite.test_moderate_underpayment_shows_buttons),
        ("Extreme underpayment shows buttons", 
         test_suite.test_extreme_underpayment_shows_buttons),
        ("Tiny underpayment within tolerance auto-accepts", 
         test_suite.test_tiny_underpayment_within_tolerance_auto_accepts),
        ("ALL significant underpayments show buttons", 
         test_suite.test_all_significant_underpayments_show_buttons),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔬 Running: {test_name}")
            await test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ FAILED: {test_name}")
            print(f"   Error: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ ERROR: {test_name}")
            print(f"   Error: {e}")
            failed += 1
    
    print("\n" + "="*80)
    print(f"📊 FINAL RESULTS: {passed} PASSED, {failed} FAILED")
    print("="*80)
    
    if failed == 0:
        print("\n🎉 100% TESTS PASSED - CRITICAL FIX VERIFIED!")
        print("✅ Large underpayments NOW show action buttons (not auto-refund)")
        print("✅ All 3 buttons available: Complete Payment, Proceed Partial, Cancel & Refund")
        return True
    else:
        print(f"\n❌ {failed} TEST(S) FAILED - REVIEW NEEDED")
        return False


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_critical_tests())
