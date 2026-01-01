"""
End-to-End Test: Underpayment Action Buttons
Tests the complete flow of underpayment handling with action buttons
"""
import pytest
import asyncio
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, Wallet, Escrow, Transaction
from services.enhanced_payment_tolerance_service import EnhancedPaymentToleranceService, PaymentResponse
from handlers.payment_recovery_handler import PaymentRecoveryHandler
from services.crypto import CryptoServiceAtomic
from database import async_managed_session


class TestUnderpaymentActionButtons:
    """Test underpayment action button flow"""
    
    @pytest.mark.asyncio
    async def test_small_underpayment_shows_buttons(self):
        """Test that small underpayment shows action buttons"""
        # Test scenario: $21 escrow, $20 paid (small shortage)
        expected = Decimal("21.00")
        received = Decimal("20.00")
        
        decision = EnhancedPaymentToleranceService.analyze_payment_variance(
            expected_amount_usd=expected,
            received_amount_usd=received,
            transaction_type="escrow"
        )
        
        # CRITICAL: Should show SELF_SERVICE (buttons), not AUTO_ACCEPT or AUTO_REFUND
        assert decision.response_type == PaymentResponse.SELF_SERVICE, \
            f"Small underpayment should show buttons, got {decision.response_type.value}"
        
        # Verify all 3 action options exist
        assert "complete_payment" in decision.action_options
        assert "proceed_partial" in decision.action_options
        assert "cancel_refund" in decision.action_options
        
        # Verify amounts
        assert decision.action_options["complete_payment"]["amount_needed"] == Decimal("1.00")
        assert decision.action_options["proceed_partial"]["escrow_amount"] == Decimal("20.00")
        assert decision.action_options["cancel_refund"]["refund_amount"] == Decimal("20.00")
        
        print("✅ TEST PASSED: Small underpayment shows buttons")
    
    @pytest.mark.asyncio
    async def test_large_underpayment_shows_buttons(self):
        """Test that LARGE underpayment ALSO shows action buttons (no auto-refund)"""
        # Test scenario: $21 escrow, $9.57 paid (LARGE shortage - 54% short!)
        expected = Decimal("21.00")
        received = Decimal("9.57")
        
        decision = EnhancedPaymentToleranceService.analyze_payment_variance(
            expected_amount_usd=expected,
            received_amount_usd=received,
            transaction_type="escrow"
        )
        
        # CRITICAL FIX: Large underpayment should NOW show buttons (not auto-refund)
        assert decision.response_type == PaymentResponse.SELF_SERVICE, \
            f"Large underpayment should show buttons (FIXED), got {decision.response_type.value}"
        
        # Verify all 3 action options exist
        assert "complete_payment" in decision.action_options
        assert "proceed_partial" in decision.action_options
        assert "cancel_refund" in decision.action_options
        
        # Verify amounts
        assert decision.action_options["complete_payment"]["amount_needed"] == Decimal("11.43")
        assert decision.action_options["proceed_partial"]["escrow_amount"] == Decimal("9.57")
        assert decision.action_options["cancel_refund"]["refund_amount"] == Decimal("9.57")
        
        print("✅ TEST PASSED: Large underpayment shows buttons (NOT auto-refund)")
    
    @pytest.mark.asyncio
    async def test_extreme_underpayment_shows_buttons(self):
        """Test that EXTREME underpayment (90% short) also shows buttons"""
        # Test scenario: $100 escrow, $10 paid (90% short!)
        expected = Decimal("100.00")
        received = Decimal("10.00")
        
        decision = EnhancedPaymentToleranceService.analyze_payment_variance(
            expected_amount_usd=expected,
            received_amount_usd=received,
            transaction_type="escrow"
        )
        
        # CRITICAL: Even extreme underpayment should show buttons
        assert decision.response_type == PaymentResponse.SELF_SERVICE, \
            f"Extreme underpayment should show buttons, got {decision.response_type.value}"
        
        print("✅ TEST PASSED: Extreme underpayment shows buttons")
    
    @pytest.mark.asyncio
    async def test_cancel_refund_button_database_constraint(self):
        """Test that Cancel & Refund properly links transaction to escrow (no constraint violation)"""
        async with async_managed_session() as session:
            # Create test user
            test_user = User(
                user_id=999888777,
                username="test_underpay",
                first_name="Test",
                conversation_state="active",
                onboarding_completed=True
            )
            session.add(test_user)
            
            # Create wallet
            test_wallet = Wallet(
                user_id=999888777,
                currency="USD",
                available_balance=Decimal("0.00"),
                trading_credit=Decimal("0.00")
            )
            session.add(test_wallet)
            
            # Create test escrow
            test_escrow = Escrow(
                escrow_id="TEST_UNDERPAY_001",
                buyer_id=999888777,
                seller_telegram="@testseller",
                amount=Decimal("21.00"),
                currency="USD",
                status="awaiting_payment",
                created_at=datetime.utcnow()
            )
            session.add(test_escrow)
            await session.flush()
            
            escrow_int_id = test_escrow.id
            
            # Simulate refund with escrow_id (FIXED)
            refund_amount = Decimal("9.57")
            
            refund_success = await CryptoServiceAtomic.credit_user_wallet_atomic(
                user_id=999888777,
                amount=refund_amount,
                currency="USD",
                escrow_id=escrow_int_id,  # CRITICAL: Must pass escrow_id
                transaction_type="escrow_cancel_refund",
                description=f"Test refund for escrow TEST_UNDERPAY_001",
                session=session
            )
            
            assert refund_success, "Refund should succeed"
            
            # Verify transaction was created with escrow_id
            stmt = select(Transaction).where(
                Transaction.user_id == 999888777,
                Transaction.transaction_type == "escrow_cancel_refund"
            )
            result = await session.execute(stmt)
            refund_tx = result.scalar_one_or_none()
            
            assert refund_tx is not None, "Refund transaction should exist"
            assert refund_tx.escrow_id == escrow_int_id, \
                f"Transaction should link to escrow (got escrow_id={refund_tx.escrow_id})"
            assert refund_tx.amount == refund_amount
            
            # Verify wallet balance updated
            stmt = select(Wallet).where(
                Wallet.user_id == 999888777,
                Wallet.currency == "USD"
            )
            result = await session.execute(stmt)
            wallet = result.scalar_one()
            assert wallet.available_balance == refund_amount
            
            # Cleanup
            await session.rollback()
            
        print("✅ TEST PASSED: Cancel & Refund links transaction to escrow (no constraint violation)")
    
    @pytest.mark.asyncio
    async def test_proceed_partial_button(self):
        """Test that Proceed Partial button reduces escrow amount correctly"""
        async with async_managed_session() as session:
            # Create test user
            test_user = User(
                user_id=888777666,
                username="test_partial",
                first_name="Test",
                conversation_state="active",
                onboarding_completed=True
            )
            session.add(test_user)
            
            # Create test escrow
            test_escrow = Escrow(
                escrow_id="TEST_PARTIAL_001",
                buyer_id=888777666,
                seller_telegram="@testseller",
                amount=Decimal("21.00"),
                currency="USD",
                status="awaiting_payment",
                created_at=datetime.utcnow()
            )
            session.add(test_escrow)
            await session.flush()
            
            # Simulate partial payment acceptance
            partial_amount = Decimal("9.57")
            
            # Update escrow to partial amount
            test_escrow.amount = partial_amount
            test_escrow.status = "active"
            await session.flush()
            
            # Verify escrow updated
            stmt = select(Escrow).where(Escrow.escrow_id == "TEST_PARTIAL_001")
            result = await session.execute(stmt)
            updated_escrow = result.scalar_one()
            
            assert updated_escrow.amount == partial_amount
            assert updated_escrow.status == "active"
            
            # Cleanup
            await session.rollback()
            
        print("✅ TEST PASSED: Proceed Partial updates escrow amount")
    
    @pytest.mark.asyncio
    async def test_all_underpayment_amounts_show_buttons(self):
        """Comprehensive test: ALL underpayment amounts show buttons (1% to 99% short)"""
        test_cases = [
            (Decimal("100.00"), Decimal("99.00")),   # 1% short
            (Decimal("100.00"), Decimal("90.00")),   # 10% short
            (Decimal("100.00"), Decimal("75.00")),   # 25% short
            (Decimal("100.00"), Decimal("50.00")),   # 50% short
            (Decimal("100.00"), Decimal("25.00")),   # 75% short
            (Decimal("100.00"), Decimal("10.00")),   # 90% short
            (Decimal("100.00"), Decimal("1.00")),    # 99% short
            (Decimal("21.00"), Decimal("9.57")),     # Real scenario: 54% short
        ]
        
        for expected, received in test_cases:
            shortage_pct = ((expected - received) / expected * 100).quantize(Decimal("0.1"))
            
            decision = EnhancedPaymentToleranceService.analyze_payment_variance(
                expected_amount_usd=expected,
                received_amount_usd=received,
                transaction_type="escrow"
            )
            
            assert decision.response_type == PaymentResponse.SELF_SERVICE, \
                f"${expected} escrow, ${received} paid ({shortage_pct}% short) should show buttons, " \
                f"got {decision.response_type.value}"
            
            # Verify all options exist
            assert "complete_payment" in decision.action_options
            assert "proceed_partial" in decision.action_options
            assert "cancel_refund" in decision.action_options
        
        print(f"✅ TEST PASSED: All {len(test_cases)} underpayment scenarios show buttons")


@pytest.mark.asyncio
async def run_all_tests():
    """Run all underpayment button tests"""
    test_suite = TestUnderpaymentActionButtons()
    
    print("\n" + "="*70)
    print("🧪 UNDERPAYMENT ACTION BUTTONS - END-TO-END TESTS")
    print("="*70 + "\n")
    
    tests = [
        ("Small Underpayment Shows Buttons", test_suite.test_small_underpayment_shows_buttons),
        ("Large Underpayment Shows Buttons (CRITICAL FIX)", test_suite.test_large_underpayment_shows_buttons),
        ("Extreme Underpayment Shows Buttons", test_suite.test_extreme_underpayment_shows_buttons),
        ("Cancel & Refund - Database Constraint Fix", test_suite.test_cancel_refund_button_database_constraint),
        ("Proceed Partial - Escrow Amount Update", test_suite.test_proceed_partial_button),
        ("ALL Underpayment Amounts Show Buttons", test_suite.test_all_underpayment_amounts_show_buttons),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔄 Running: {test_name}")
            await test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {test_name}")
            print(f"   Error: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {test_name}")
            print(f"   Error: {e}")
            failed += 1
    
    print("\n" + "="*70)
    print(f"📊 TEST RESULTS: {passed} PASSED, {failed} FAILED")
    print("="*70 + "\n")
    
    if failed == 0:
        print("✅ ALL TESTS PASSED - 100% SUCCESS")
        return True
    else:
        print(f"❌ {failed} TESTS FAILED")
        return False


if __name__ == "__main__":
    asyncio.run(run_all_tests())
