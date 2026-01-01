#!/usr/bin/env python3
"""
State Machine Validation Test Suite
Verify all entity state machines work correctly with proper transition constraints
"""

import asyncio
import logging
import sys
import time
import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal

# Add project root to path
sys.path.insert(0, '/home/runner/workspace')

from utils.entity_state_machines import (
    EscrowStateMachine, CashoutStateMachine, 
    UnifiedTransactionStateMachine
)
from utils.state_machines import (
    StateTransitionContext, StateTransitionResult,
    StateTransitionError, InvalidStateTransitionError
)
from models import (
    Escrow, Cashout, UnifiedTransaction,
    EscrowStatus, CashoutStatus, UnifiedTransactionStatus
)
from database import SessionLocal
from config import Config

logger = logging.getLogger(__name__)


class StateMachineValidationResults:
    """Track state machine validation test results"""
    
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.errors = []
        self.transition_tests = {}
        
    def add_result(self, test_name: str, passed: bool, error: Optional[str] = None,
                   entity_id: Optional[str] = None):
        """Add test result"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            logger.info(f"✅ {test_name} - PASSED")
            if entity_id:
                self.transition_tests[entity_id] = self.transition_tests.get(entity_id, 0) + 1
        else:
            self.failed_tests += 1
            logger.error(f"❌ {test_name} - FAILED: {error}")
            self.errors.append(f"{test_name}: {error}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("STATE MACHINE VALIDATION SUMMARY")
        print("="*80)
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        print(f"Success Rate: {(self.passed_tests/self.total_tests*100):.1f}%" if self.total_tests > 0 else "0.0%")
        
        if self.transition_tests:
            print("\nTRANSITION TESTS PER ENTITY:")
            for entity_id, count in self.transition_tests.items():
                print(f"  {entity_id}: {count} successful transitions")
        
        if self.errors:
            print("\nERRORS:")
            for error in self.errors:
                print(f"  • {error}")
        
        return self.failed_tests == 0


def create_test_escrow(session) -> str:
    """Create a test escrow record"""
    escrow_id = f"test_escrow_{uuid.uuid4()}"
    escrow = Escrow(
        id=escrow_id,
        buyer_id=12345,
        seller_id=54321,
        amount=Decimal("100.00"),
        currency="USD",
        title="State Machine Test Escrow",
        description="Testing escrow state machine",
        status=EscrowStatus.CREATED.value,
        version=1
    )
    session.add(escrow)
    session.commit()
    return escrow_id


def create_test_cashout(session) -> str:
    """Create a test cashout record"""
    cashout_id = f"test_cashout_{uuid.uuid4()}"
    cashout = Cashout(
        id=cashout_id,
        user_id=12345,
        amount=Decimal("75.50"),
        currency="USD",
        status=CashoutStatus.PENDING.value,
        processing_mode="manual",
        version=1
    )
    session.add(cashout)
    session.commit()
    return cashout_id


def create_test_unified_transaction(session) -> str:
    """Create a test unified transaction record"""
    tx_id = f"test_tx_{uuid.uuid4()}"
    tx = UnifiedTransaction(
        id=tx_id,
        user_id=12345,
        amount=Decimal("200.00"),
        currency="USD",
        transaction_type="deposit",
        status=UnifiedTransactionStatus.PENDING.value,
        reference_id="test_ref_123",
        version=1
    )
    session.add(tx)
    session.commit()
    return tx_id


async def test_escrow_state_machine_valid_transitions(results: StateMachineValidationResults):
    """Test valid escrow state transitions"""
    try:
        with SessionLocal() as session:
            escrow_id = create_test_escrow(session)
        
        escrow_sm = EscrowStateMachine(escrow_id)
        
        # Test valid transition sequence: CREATED -> PAYMENT_PENDING -> PAYMENT_CONFIRMED -> AWAITING_SELLER -> ACTIVE -> COMPLETED
        transitions = [
            (EscrowStatus.CREATED.value, EscrowStatus.PAYMENT_PENDING.value, "request_payment"),
            (EscrowStatus.PAYMENT_PENDING.value, EscrowStatus.PAYMENT_CONFIRMED.value, "confirm_payment"),
            (EscrowStatus.PAYMENT_CONFIRMED.value, EscrowStatus.AWAITING_SELLER.value, "await_seller"),
            (EscrowStatus.AWAITING_SELLER.value, EscrowStatus.ACTIVE.value, "activate_escrow"),
            (EscrowStatus.ACTIVE.value, EscrowStatus.COMPLETED.value, "release_funds")
        ]
        
        for from_state, to_state, transition_name in transitions:
            context = StateTransitionContext(
                entity_id=escrow_id,
                entity_type="escrow",
                current_state=from_state,
                target_state=to_state,
                transition_name=transition_name,
                metadata={"test": True},
                user_id=12345,
                financial_impact=True,
                amount=Decimal("100.00"),
                currency="USD"
            )
            
            result = await escrow_sm.transition_to_state(context)
            
            if not result.success:
                results.add_result(f"Escrow Transition ({from_state} → {to_state})", 
                                 False, result.error_message, escrow_id)
                break
            else:
                results.add_result(f"Escrow Transition ({from_state} → {to_state})", 
                                 True, entity_id=escrow_id)
        
        # Clean up
        with SessionLocal() as session:
            session.query(Escrow).filter(Escrow.id == escrow_id).delete()
            session.commit()
        
    except Exception as e:
        results.add_result("Escrow State Machine Valid Transitions", False, str(e))


async def test_escrow_state_machine_invalid_transitions(results: StateMachineValidationResults):
    """Test invalid escrow state transitions are properly blocked"""
    try:
        with SessionLocal() as session:
            escrow_id = create_test_escrow(session)
        
        escrow_sm = EscrowStateMachine(escrow_id)
        
        # Test invalid transitions that should fail
        invalid_transitions = [
            (EscrowStatus.CREATED.value, EscrowStatus.COMPLETED.value, "invalid_direct_complete"),
            (EscrowStatus.PAYMENT_PENDING.value, EscrowStatus.ACTIVE.value, "invalid_skip_confirmation"),
            (EscrowStatus.COMPLETED.value, EscrowStatus.CREATED.value, "invalid_reverse_completion")
        ]
        
        for from_state, to_state, transition_name in invalid_transitions:
            # First set the state to from_state
            if from_state != EscrowStatus.CREATED.value:
                # Set up the from_state first
                with SessionLocal() as session:
                    escrow = session.query(Escrow).filter(Escrow.id == escrow_id).first()
                    if escrow:
                        escrow.status = from_state
                        session.commit()
            
            context = StateTransitionContext(
                entity_id=escrow_id,
                entity_type="escrow",
                current_state=from_state,
                target_state=to_state,
                transition_name=transition_name,
                metadata={"test": True},
                user_id=12345
            )
            
            try:
                result = await escrow_sm.transition_to_state(context)
                
                if result.success:
                    results.add_result(f"Escrow Invalid Transition Block ({from_state} → {to_state})", 
                                     False, "Invalid transition was allowed", escrow_id)
                else:
                    results.add_result(f"Escrow Invalid Transition Block ({from_state} → {to_state})", 
                                     True, entity_id=escrow_id)
                
            except InvalidStateTransitionError:
                # This is expected for invalid transitions
                results.add_result(f"Escrow Invalid Transition Block ({from_state} → {to_state})", 
                                 True, entity_id=escrow_id)
        
        # Clean up
        with SessionLocal() as session:
            session.query(Escrow).filter(Escrow.id == escrow_id).delete()
            session.commit()
        
    except Exception as e:
        results.add_result("Escrow State Machine Invalid Transitions", False, str(e))


async def test_cashout_state_machine_transitions(results: StateMachineValidationResults):
    """Test cashout state machine transitions"""
    try:
        with SessionLocal() as session:
            cashout_id = create_test_cashout(session)
        
        cashout_sm = CashoutStateMachine(cashout_id)
        
        # Test valid cashout transitions: PENDING -> PROCESSING -> COMPLETED
        transitions = [
            (CashoutStatus.PENDING.value, CashoutStatus.PROCESSING.value, "start_processing"),
            (CashoutStatus.PROCESSING.value, CashoutStatus.COMPLETED.value, "complete_cashout")
        ]
        
        for from_state, to_state, transition_name in transitions:
            context = StateTransitionContext(
                entity_id=cashout_id,
                entity_type="cashout",
                current_state=from_state,
                target_state=to_state,
                transition_name=transition_name,
                metadata={"test": True},
                user_id=12345,
                financial_impact=True,
                amount=Decimal("75.50"),
                currency="USD"
            )
            
            result = await cashout_sm.transition_to_state(context)
            
            if not result.success:
                results.add_result(f"Cashout Transition ({from_state} → {to_state})", 
                                 False, result.error_message, cashout_id)
                break
            else:
                results.add_result(f"Cashout Transition ({from_state} → {to_state})", 
                                 True, entity_id=cashout_id)
        
        # Test failure recovery: PROCESSING -> FAILED -> RETRY
        recovery_context = StateTransitionContext(
            entity_id=cashout_id,
            entity_type="cashout", 
            current_state=CashoutStatus.PROCESSING.value,
            target_state=CashoutStatus.FAILED.value,
            transition_name="mark_failed",
            metadata={"error": "Test failure"},
            user_id=12345
        )
        
        # First set state back to processing for failure test
        with SessionLocal() as session:
            cashout = session.query(Cashout).filter(Cashout.id == cashout_id).first()
            if cashout:
                cashout.status = CashoutStatus.PROCESSING.value
                session.commit()
        
        failure_result = await cashout_sm.transition_to_state(recovery_context)
        
        if failure_result.success:
            results.add_result("Cashout Failure Transition", True, entity_id=cashout_id)
            
            # Test retry from failed state
            retry_context = StateTransitionContext(
                entity_id=cashout_id,
                entity_type="cashout",
                current_state=CashoutStatus.FAILED.value,
                target_state=CashoutStatus.PENDING.value,
                transition_name="retry_cashout",
                metadata={"retry_attempt": 1},
                user_id=12345
            )
            
            retry_result = await cashout_sm.transition_to_state(retry_context)
            if retry_result.success:
                results.add_result("Cashout Retry Transition", True, entity_id=cashout_id)
            else:
                results.add_result("Cashout Retry Transition", False, retry_result.error_message, cashout_id)
        else:
            results.add_result("Cashout Failure Transition", False, failure_result.error_message, cashout_id)
        
        # Clean up
        with SessionLocal() as session:
            session.query(Cashout).filter(Cashout.id == cashout_id).delete()
            session.commit()
        
    except Exception as e:
        results.add_result("Cashout State Machine Transitions", False, str(e))


async def test_unified_transaction_state_machine(results: StateMachineValidationResults):
    """Test unified transaction state machine"""
    try:
        with SessionLocal() as session:
            tx_id = create_test_unified_transaction(session)
        
        tx_sm = UnifiedTransactionStateMachine(tx_id)
        
        # Test standard transaction flow: PENDING -> PROCESSING -> CONFIRMED -> COMPLETED
        transitions = [
            (UnifiedTransactionStatus.PENDING.value, UnifiedTransactionStatus.PROCESSING.value, "start_processing"),
            (UnifiedTransactionStatus.PROCESSING.value, UnifiedTransactionStatus.CONFIRMED.value, "confirm_transaction"),
            (UnifiedTransactionStatus.CONFIRMED.value, UnifiedTransactionStatus.COMPLETED.value, "complete_transaction")
        ]
        
        for from_state, to_state, transition_name in transitions:
            context = StateTransitionContext(
                entity_id=tx_id,
                entity_type="unified_transaction",
                current_state=from_state,
                target_state=to_state,
                transition_name=transition_name,
                metadata={"test": True},
                user_id=12345,
                financial_impact=True,
                amount=Decimal("200.00"),
                currency="USD"
            )
            
            result = await tx_sm.transition_to_state(context)
            
            if not result.success:
                results.add_result(f"Transaction Transition ({from_state} → {to_state})", 
                                 False, result.error_message, tx_id)
                break
            else:
                results.add_result(f"Transaction Transition ({from_state} → {to_state})", 
                                 True, entity_id=tx_id)
        
        # Clean up
        with SessionLocal() as session:
            session.query(UnifiedTransaction).filter(UnifiedTransaction.id == tx_id).delete()
            session.commit()
        
    except Exception as e:
        results.add_result("Unified Transaction State Machine", False, str(e))


async def test_state_machine_version_control(results: StateMachineValidationResults):
    """Test state machine optimistic locking and version control"""
    try:
        with SessionLocal() as session:
            escrow_id = create_test_escrow(session)
        
        escrow_sm = EscrowStateMachine(escrow_id)
        
        # Get initial version
        with SessionLocal() as session:
            escrow = session.query(Escrow).filter(Escrow.id == escrow_id).first()
            initial_version = escrow.version if escrow else 0
        
        # Perform state transition
        context = StateTransitionContext(
            entity_id=escrow_id,
            entity_type="escrow",
            current_state=EscrowStatus.CREATED.value,
            target_state=EscrowStatus.PAYMENT_PENDING.value,
            transition_name="request_payment",
            metadata={"version_test": True},
            user_id=12345
        )
        
        result = await escrow_sm.transition_to_state(context)
        
        if not result.success:
            results.add_result("State Machine Version Control", False, result.error_message)
            return
        
        # Check version was incremented
        with SessionLocal() as session:
            escrow = session.query(Escrow).filter(Escrow.id == escrow_id).first()
            final_version = escrow.version if escrow else 0
        
        if final_version != initial_version + 1:
            results.add_result("State Machine Version Control", False, 
                             f"Version not incremented: {initial_version} -> {final_version}")
            return
        
        results.add_result("State Machine Version Control", True, entity_id=escrow_id)
        
        # Test version conflict detection by simulating concurrent modification
        # Manually decrement version to simulate stale data
        with SessionLocal() as session:
            escrow = session.query(Escrow).filter(Escrow.id == escrow_id).first()
            if escrow:
                escrow.version = initial_version  # Revert to old version
                session.commit()
        
        # Try another transition with stale version
        stale_context = StateTransitionContext(
            entity_id=escrow_id,
            entity_type="escrow",
            current_state=EscrowStatus.PAYMENT_PENDING.value,
            target_state=EscrowStatus.PAYMENT_CONFIRMED.value,
            transition_name="confirm_payment",
            metadata={"stale_version_test": True},
            user_id=12345
        )
        
        stale_result = await escrow_sm.transition_to_state(stale_context)
        
        # This should fail due to version mismatch
        if stale_result.success:
            results.add_result("State Machine Version Conflict Detection", False, 
                             "Version conflict not detected")
        else:
            results.add_result("State Machine Version Conflict Detection", True, entity_id=escrow_id)
        
        # Clean up
        with SessionLocal() as session:
            session.query(Escrow).filter(Escrow.id == escrow_id).delete()
            session.commit()
        
    except Exception as e:
        results.add_result("State Machine Version Control", False, str(e))


async def test_state_machine_audit_logging(results: StateMachineValidationResults):
    """Test state machine audit logging functionality"""
    try:
        # This test verifies that state transitions are properly logged
        # We'll check that the audit log messages are generated (captured in logs)
        
        with SessionLocal() as session:
            escrow_id = create_test_escrow(session)
        
        escrow_sm = EscrowStateMachine(escrow_id)
        
        # Capture initial log level to restore later
        logger_level = logger.level
        
        # Set up log capture
        from io import StringIO
        import logging
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        try:
            # Perform a state transition that should generate audit logs
            context = StateTransitionContext(
                entity_id=escrow_id,
                entity_type="escrow",
                current_state=EscrowStatus.CREATED.value,
                target_state=EscrowStatus.PAYMENT_PENDING.value,
                transition_name="request_payment",
                metadata={"audit_test": True},
                user_id=12345,
                financial_impact=True,
                amount=Decimal("100.00"),
                currency="USD"
            )
            
            result = await escrow_sm.transition_to_state(context)
            
            if not result.success:
                results.add_result("State Machine Audit Logging", False, result.error_message)
                return
            
            # Check if audit logs were generated
            log_output = log_capture.getvalue()
            
            # Look for audit log patterns
            audit_patterns = [
                "STATE_TRANSITION_ATTEMPT",
                "FINANCIAL_TRANSITION",
                escrow_id,
                "request_payment"
            ]
            
            missing_patterns = []
            for pattern in audit_patterns:
                if pattern not in log_output:
                    missing_patterns.append(pattern)
            
            if missing_patterns:
                results.add_result("State Machine Audit Logging", False, 
                                 f"Missing audit log patterns: {missing_patterns}")
            else:
                results.add_result("State Machine Audit Logging", True, entity_id=escrow_id)
        
        finally:
            # Clean up logging
            logger.removeHandler(handler)
            logger.setLevel(logger_level)
        
        # Clean up
        with SessionLocal() as session:
            session.query(Escrow).filter(Escrow.id == escrow_id).delete()
            session.commit()
        
    except Exception as e:
        results.add_result("State Machine Audit Logging", False, str(e))


async def main():
    """Run all state machine validation tests"""
    print("🔄 STATE MACHINE VALIDATION TEST SUITE")
    print("="*80)
    
    results = StateMachineValidationResults()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Test escrow state machine valid transitions
        print("\n✅ Testing Escrow Valid State Transitions...")
        await test_escrow_state_machine_valid_transitions(results)
        
        # Test escrow state machine invalid transitions
        print("\n🚫 Testing Escrow Invalid State Transition Blocking...")
        await test_escrow_state_machine_invalid_transitions(results)
        
        # Test cashout state machine
        print("\n💰 Testing Cashout State Machine...")
        await test_cashout_state_machine_transitions(results)
        
        # Test unified transaction state machine
        print("\n🔄 Testing Unified Transaction State Machine...")
        await test_unified_transaction_state_machine(results)
        
        # Test version control and optimistic locking
        print("\n🔒 Testing State Machine Version Control...")
        await test_state_machine_version_control(results)
        
        # Test audit logging
        print("\n📝 Testing State Machine Audit Logging...")
        await test_state_machine_audit_logging(results)
        
    except Exception as e:
        logger.error(f"Critical error during state machine validation: {e}")
        results.add_result("Critical State Machine Error", False, str(e))
    
    # Print summary and exit
    success = results.print_summary()
    
    if success:
        print("\n✅ All state machine validation tests PASSED!")
        print("🎯 State machines are working correctly with proper constraints.")
        return 0
    else:
        print("\n❌ Some state machine validation tests FAILED!")
        print("⚠️ State machine issues must be resolved before production.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)