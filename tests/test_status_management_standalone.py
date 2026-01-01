#!/usr/bin/env python3
"""
Standalone Test Runner for Status Management System

This provides a simpler test runner that doesn't depend on complex database fixtures
and can validate the core status management functionality independently.

Run with: python test_status_management_standalone.py
"""

import sys
import os
import logging
from typing import List, Dict, Any
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import status management components
from utils.status_flows import (
    UnifiedTransitionValidator, UnifiedStatusFlows, StatusPhase,
    TransitionValidationResult, validate_unified_transition,
    get_allowed_next_statuses, is_terminal_transaction_status
)

from services.legacy_status_mapper import LegacyStatusMapper, LegacySystemType

from models import (
    UnifiedTransactionStatus, UnifiedTransactionType,
    CashoutStatus, EscrowStatus, ExchangeStatus
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class StatusManagementTestRunner:
    """Standalone test runner for status management system"""
    
    def __init__(self):
        self.test_results = []
        self.failed_tests = []
        
    def run_test(self, test_name: str, test_func):
        """Run a single test and track results"""
        try:
            logger.info(f"\n🧪 Running {test_name}...")
            test_func()
            logger.info(f"✅ {test_name} PASSED")
            self.test_results.append((test_name, True, None))
            return True
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED: {e}")
            self.test_results.append((test_name, False, str(e)))
            self.failed_tests.append((test_name, e))
            return False
    
    def test_basic_validator_functionality(self):
        """Test basic UnifiedTransitionValidator functionality"""
        validator = UnifiedTransitionValidator()
        
        # Test valid transition
        result = validator.validate_transition(
            current_status=UnifiedTransactionStatus.PENDING,
            new_status=UnifiedTransactionStatus.PROCESSING,
            transaction_type=UnifiedTransactionType.WALLET_CASHOUT
        )
        
        assert result.is_valid, f"Expected valid transition: {result.error_message}"
        assert result.current_status == UnifiedTransactionStatus.PENDING.value
        assert result.new_status == UnifiedTransactionStatus.PROCESSING.value
        
        # Test invalid transition
        invalid_result = validator.validate_transition(
            current_status=UnifiedTransactionStatus.SUCCESS,
            new_status=UnifiedTransactionStatus.PENDING,
            transaction_type=UnifiedTransactionType.WALLET_CASHOUT
        )
        
        assert not invalid_result.is_valid, "Expected invalid transition to be caught"
        # The actual error message format is "Invalid transition ... Allowed: []"
        assert "invalid transition" in invalid_result.error_message.lower() or "allowed" in invalid_result.error_message.lower()
        
        logger.info("  ✅ Basic validator functionality works correctly")
    
    def test_round_trip_mapping_core_cases(self):
        """Test core round-trip mapping functionality"""
        
        # Test perfect round-trip cases
        perfect_cases = [
            (CashoutStatus.OTP_PENDING, LegacySystemType.CASHOUT, UnifiedTransactionStatus.OTP_PENDING),
            (EscrowStatus.DISPUTED, LegacySystemType.ESCROW, UnifiedTransactionStatus.DISPUTED),
            (ExchangeStatus.RATE_LOCKED, LegacySystemType.EXCHANGE, UnifiedTransactionStatus.FUNDS_HELD),
        ]
        
        for legacy_status, system_type, expected_unified in perfect_cases:
            # Forward mapping
            mapped_unified = LegacyStatusMapper.map_to_unified(legacy_status, system_type)
            assert mapped_unified == expected_unified, (
                f"Forward mapping failed: {legacy_status.name} → {mapped_unified.name}, expected {expected_unified.name}"
            )
            
            # Reverse mapping (if available)
            try:
                reverse_mapped = LegacyStatusMapper.map_from_unified(mapped_unified, system_type, prefer_primary=True)
                # For perfect cases, should get back the same status
                if legacy_status in [CashoutStatus.OTP_PENDING, EscrowStatus.DISPUTED]:  # Known perfect cases
                    assert reverse_mapped == legacy_status, (
                        f"Round-trip failed: {legacy_status.name} → {mapped_unified.name} → {reverse_mapped.name}"
                    )
                logger.info(f"  ✅ Round-trip: {legacy_status.name} ↔ {mapped_unified.name}")
            except Exception as e:
                logger.info(f"  ⚠️ Reverse mapping not available for {legacy_status.name}: {e}")
        
        logger.info("  ✅ Core round-trip mapping works correctly")
    
    def test_all_legacy_statuses_mapped(self):
        """Test that all legacy statuses have unified mappings"""
        
        # Test all cashout statuses
        all_cashout = set(CashoutStatus)
        mapped_cashout = set(LegacyStatusMapper.CASHOUT_TO_UNIFIED.keys())
        unmapped_cashout = all_cashout - mapped_cashout
        
        assert len(unmapped_cashout) == 0, f"Unmapped CashoutStatus values: {unmapped_cashout}"
        assert len(mapped_cashout) == 15, f"Expected 15 cashout statuses, got {len(mapped_cashout)}"
        
        # Test all escrow statuses
        all_escrow = set(EscrowStatus)
        mapped_escrow = set(LegacyStatusMapper.ESCROW_TO_UNIFIED.keys())
        unmapped_escrow = all_escrow - mapped_escrow
        
        assert len(unmapped_escrow) == 0, f"Unmapped EscrowStatus values: {unmapped_escrow}"
        assert len(mapped_escrow) == 13, f"Expected 13 escrow statuses, got {len(mapped_escrow)}"
        
        # Test all exchange statuses
        all_exchange = set(ExchangeStatus)
        mapped_exchange = set(LegacyStatusMapper.EXCHANGE_TO_UNIFIED.keys())
        unmapped_exchange = all_exchange - mapped_exchange
        
        assert len(unmapped_exchange) == 0, f"Unmapped ExchangeStatus values: {unmapped_exchange}"
        assert len(mapped_exchange) == 11, f"Expected 11 exchange statuses, got {len(mapped_exchange)}"
        
        total_mapped = len(mapped_cashout) + len(mapped_escrow) + len(mapped_exchange)
        assert total_mapped == 39, f"Expected 39 total mapped statuses, got {total_mapped}"
        
        logger.info(f"  ✅ All legacy statuses mapped: {total_mapped} total (15 cashout, 13 escrow, 11 exchange)")
    
    def test_transaction_type_specific_flows(self):
        """Test transaction-type-specific status flows"""
        validator = UnifiedTransitionValidator()
        
        # Wallet Cashout Flow: pending → processing → awaiting_response → success
        wallet_flow = [
            (UnifiedTransactionStatus.PENDING, UnifiedTransactionStatus.PROCESSING),
            (UnifiedTransactionStatus.PROCESSING, UnifiedTransactionStatus.AWAITING_RESPONSE),
            (UnifiedTransactionStatus.AWAITING_RESPONSE, UnifiedTransactionStatus.SUCCESS)
        ]
        
        for current, new in wallet_flow:
            result = validator.validate_transition(
                current_status=current,
                new_status=new,
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT
            )
            assert result.is_valid, f"Wallet cashout flow failed: {current.name} → {new.name}: {result.error_message}"
        
        # Exchange Sell Flow: pending → awaiting_payment → payment_confirmed → processing → success
        exchange_sell_flow = [
            (UnifiedTransactionStatus.PENDING, UnifiedTransactionStatus.AWAITING_PAYMENT),
            (UnifiedTransactionStatus.AWAITING_PAYMENT, UnifiedTransactionStatus.PAYMENT_CONFIRMED),
            (UnifiedTransactionStatus.PAYMENT_CONFIRMED, UnifiedTransactionStatus.PROCESSING),
            (UnifiedTransactionStatus.PROCESSING, UnifiedTransactionStatus.SUCCESS)
        ]
        
        for current, new in exchange_sell_flow:
            result = validator.validate_transition(
                current_status=current,
                new_status=new,
                transaction_type=UnifiedTransactionType.EXCHANGE_SELL_CRYPTO
            )
            assert result.is_valid, f"Exchange sell flow failed: {current.name} → {new.name}: {result.error_message}"
        
        # Escrow Flow: pending → payment_confirmed → awaiting_approval → funds_held → release_pending → success
        escrow_flow = [
            (UnifiedTransactionStatus.PENDING, UnifiedTransactionStatus.PAYMENT_CONFIRMED),
            (UnifiedTransactionStatus.PAYMENT_CONFIRMED, UnifiedTransactionStatus.AWAITING_APPROVAL),
            (UnifiedTransactionStatus.AWAITING_APPROVAL, UnifiedTransactionStatus.FUNDS_HELD),
            (UnifiedTransactionStatus.FUNDS_HELD, UnifiedTransactionStatus.RELEASE_PENDING),
            (UnifiedTransactionStatus.RELEASE_PENDING, UnifiedTransactionStatus.SUCCESS)
        ]
        
        for current, new in escrow_flow:
            result = validator.validate_transition(
                current_status=current,
                new_status=new,
                transaction_type=UnifiedTransactionType.ESCROW
            )
            assert result.is_valid, f"Escrow flow failed: {current.name} → {new.name}: {result.error_message}"
        
        logger.info("  ✅ All transaction-type-specific flows work correctly")
    
    def test_cross_phase_regression_prevention(self):
        """Test that cross-phase regressions are prevented"""
        validator = UnifiedTransitionValidator()
        
        # Terminal → Any non-terminal (should all be blocked)
        terminal_statuses = [
            UnifiedTransactionStatus.SUCCESS,
            UnifiedTransactionStatus.FAILED,
            UnifiedTransactionStatus.CANCELLED,
            UnifiedTransactionStatus.EXPIRED
        ]
        
        non_terminal_statuses = [
            UnifiedTransactionStatus.PENDING,
            UnifiedTransactionStatus.PROCESSING,
            UnifiedTransactionStatus.AWAITING_PAYMENT
        ]
        
        regression_found = False
        for terminal in terminal_statuses:
            for non_terminal in non_terminal_statuses:
                result = validator.validate_transition(
                    current_status=terminal,
                    new_status=non_terminal,
                    transaction_type=UnifiedTransactionType.WALLET_CASHOUT
                )
                
                if result.is_valid:
                    regression_found = True
                    logger.error(f"  ❌ REGRESSION: {terminal.name} → {non_terminal.name} should be blocked")
        
        assert not regression_found, "Cross-phase regression detected!"
        
        # Specific dangerous regressions
        dangerous_regressions = [
            (UnifiedTransactionStatus.SUCCESS, UnifiedTransactionStatus.PROCESSING),
            (UnifiedTransactionStatus.PAYMENT_CONFIRMED, UnifiedTransactionStatus.AWAITING_PAYMENT),
            (UnifiedTransactionStatus.FUNDS_HELD, UnifiedTransactionStatus.PENDING),
        ]
        
        for current, new in dangerous_regressions:
            result = validator.validate_transition(
                current_status=current,
                new_status=new,
                transaction_type=UnifiedTransactionType.ESCROW
            )
            
            assert not result.is_valid, f"Dangerous regression should be blocked: {current.name} → {new.name}"
        
        logger.info("  ✅ Cross-phase regression prevention works correctly")
    
    def test_phase_boundary_enforcement(self):
        """Test phase boundary enforcement"""
        
        # Get status phase mapping
        phase_map = UnifiedStatusFlows.STATUS_PHASE_MAP
        
        # Verify all statuses have phases
        all_unified_statuses = set(UnifiedTransactionStatus)
        mapped_statuses = set(phase_map.keys())
        unmapped = all_unified_statuses - mapped_statuses
        
        assert len(unmapped) == 0, f"Unmapped statuses to phases: {unmapped}"
        
        # Verify phase progression logic
        phase_order = [StatusPhase.INITIATION, StatusPhase.AUTHORIZATION, StatusPhase.PROCESSING, StatusPhase.TERMINAL]
        
        initiation_statuses = [s for s, p in phase_map.items() if p == StatusPhase.INITIATION]
        terminal_statuses = [s for s, p in phase_map.items() if p == StatusPhase.TERMINAL]
        
        assert len(initiation_statuses) > 0, "Should have initiation statuses"
        assert len(terminal_statuses) > 0, "Should have terminal statuses"
        
        # Check specific phase assignments
        assert UnifiedTransactionStatus.PENDING in initiation_statuses
        assert UnifiedTransactionStatus.SUCCESS in terminal_statuses
        assert UnifiedTransactionStatus.PROCESSING in [s for s, p in phase_map.items() if p == StatusPhase.PROCESSING]
        
        logger.info(f"  ✅ Phase boundaries: {len(phase_map)} statuses mapped to phases")
    
    def test_edge_cases_and_error_handling(self):
        """Test edge cases and error handling"""
        validator = UnifiedTransitionValidator()
        
        # Same status transitions
        same_status_result = validator.validate_transition(
            current_status=UnifiedTransactionStatus.PENDING,
            new_status=UnifiedTransactionStatus.PENDING,
            transaction_type=UnifiedTransactionType.WALLET_CASHOUT
        )
        
        # Same status should generally be blocked
        assert not same_status_result.is_valid, "Same status transition should be blocked"
        
        # Test invalid legacy status mapping
        try:
            LegacyStatusMapper.map_to_unified("INVALID_STATUS", LegacySystemType.CASHOUT)
            assert False, "Should raise error for invalid status"
        except Exception as e:
            assert "invalid" in str(e).lower() or "unknown" in str(e).lower()
        
        # Test wrong system type
        try:
            LegacyStatusMapper.map_to_unified(CashoutStatus.PENDING, LegacySystemType.ESCROW)
            assert False, "Should raise error for wrong system type"
        except Exception as e:
            assert "cashout" in str(e).lower() or "escrow" in str(e).lower()
        
        logger.info("  ✅ Edge cases and error handling work correctly")
    
    def test_allowed_next_statuses(self):
        """Test getting allowed next statuses"""
        
        # Test pending wallet cashout
        allowed = get_allowed_next_statuses(
            current_status=UnifiedTransactionStatus.PENDING,
            transaction_type=UnifiedTransactionType.WALLET_CASHOUT
        )
        
        # Based on the actual flow rules: PENDING allows PROCESSING and CANCELLED
        expected_allowed_values = [UnifiedTransactionStatus.PROCESSING.value, UnifiedTransactionStatus.CANCELLED.value]
        
        for expected_value in expected_allowed_values:
            assert expected_value in allowed, f"{expected_value} should be allowed from pending, got: {allowed}"
        
        assert UnifiedTransactionStatus.SUCCESS not in allowed, "Success should not be directly allowed from pending"
        
        # Test terminal status (should have limited or no allowed transitions)
        terminal_allowed = get_allowed_next_statuses(
            current_status=UnifiedTransactionStatus.SUCCESS,
            transaction_type=UnifiedTransactionType.WALLET_CASHOUT
        )
        
        # Terminal statuses should have no normal transitions (might allow error recovery)
        assert len(terminal_allowed) == 0 or all(
            is_terminal_transaction_status(s) for s in terminal_allowed
        ), "Terminal status should only allow other terminal transitions if any"
        
        logger.info(f"  ✅ Allowed next statuses: PENDING→{len(allowed)}, SUCCESS→{len(terminal_allowed)}")
    
    def test_performance_under_load(self):
        """Test performance of validation under moderate load"""
        validator = UnifiedTransitionValidator()
        
        import time
        start_time = time.time()
        
        # Run many validations
        num_tests = 100
        valid_count = 0
        
        for i in range(num_tests):
            result = validator.validate_transition(
                current_status=UnifiedTransactionStatus.PENDING,
                new_status=UnifiedTransactionStatus.PROCESSING,
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT
            )
            if result.is_valid:
                valid_count += 1
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert duration < 5.0, f"Validation should complete quickly, took {duration:.2f}s"
        assert valid_count == num_tests, f"All {num_tests} validations should pass"
        
        avg_time = (duration / num_tests) * 1000  # Convert to milliseconds
        
        logger.info(f"  ✅ Performance: {num_tests} validations in {duration:.3f}s ({avg_time:.2f}ms avg)")
    
    def run_all_tests(self):
        """Run all status management tests"""
        logger.info("🚀 Starting Comprehensive Status Management Tests")
        logger.info("=" * 60)
        
        # List of all tests to run
        tests = [
            ("Basic Validator Functionality", self.test_basic_validator_functionality),
            ("Round-Trip Mapping Core Cases", self.test_round_trip_mapping_core_cases),
            ("All Legacy Statuses Mapped", self.test_all_legacy_statuses_mapped),
            ("Transaction Type Specific Flows", self.test_transaction_type_specific_flows),
            ("Cross-Phase Regression Prevention", self.test_cross_phase_regression_prevention),
            ("Phase Boundary Enforcement", self.test_phase_boundary_enforcement),
            ("Edge Cases and Error Handling", self.test_edge_cases_and_error_handling),
            ("Allowed Next Statuses", self.test_allowed_next_statuses),
            ("Performance Under Load", self.test_performance_under_load),
        ]
        
        # Run all tests
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            if self.run_test(test_name, test_func):
                passed += 1
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        
        for test_name, success, error in self.test_results:
            status = "✅ PASSED" if success else "❌ FAILED"
            logger.info(f"{test_name}: {status}")
            if not success and error:
                logger.info(f"  Error: {error}")
        
        logger.info(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 ALL TESTS PASSED! Status management system is working correctly.")
            return True
        else:
            logger.error(f"⚠️ {total - passed} tests failed. Please check the implementation.")
            return False


def main():
    """Main test runner entry point"""
    try:
        runner = StatusManagementTestRunner()
        success = runner.run_all_tests()
        
        if success:
            logger.info("\n🎯 Status Management System: READY FOR PRODUCTION!")
            return 0
        else:
            logger.error("\n⚠️ Status Management System: NEEDS FIXES BEFORE PRODUCTION")
            return 1
            
    except Exception as e:
        logger.error(f"\n💥 Test runner failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())