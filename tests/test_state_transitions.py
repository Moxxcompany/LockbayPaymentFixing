"""
Comprehensive State Transition Security Test Suite
==================================================

This test suite validates state transition security across all 6 entity types:
- Escrow, Exchange, Cashout, UnifiedTransaction, User, and Dispute

## Purpose

Regression testing to ensure state transition vulnerabilities are fixed:
1. Terminal states cannot be overwritten (COMPLETED, SUCCESS, CANCELLED, etc.)
2. Invalid backward transitions are blocked (PROCESSING → PENDING)
3. Valid transitions still work correctly
4. StateTransitionService centralized validation works

## Test Coverage

- **Terminal State Protection**: ~30 tests
- **Backward Transition Blocking**: ~20 tests
- **Valid Transition Verification**: ~25 tests
- **Edge Cases & Integration**: ~20 tests
- **Total**: 80-100 comprehensive tests

## Usage

Run all tests:
    pytest tests/test_state_transitions.py -v

Run specific entity tests:
    pytest tests/test_state_transitions.py::TestEscrowStateTransitions -v

Run with coverage:
    pytest tests/test_state_transitions.py --cov=utils --cov=services -v
"""

import pytest
from typing import List, Set

# Import validators and service
from utils.escrow_state_validator import EscrowStateValidator, StateTransitionError
from utils.exchange_state_validator import ExchangeStateValidator
from utils.cashout_state_validator import CashoutStateValidator
from utils.unified_transaction_state_validator import UnifiedTransactionStateValidator
from services.state_transition_service import StateTransitionService

# Import all status enums
from models import (
    EscrowStatus,
    ExchangeStatus,
    CashoutStatus,
    UnifiedTransactionStatus,
    UserStatus,
    DisputeStatus
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def assert_transition_blocked(validator_class, current, target, entity_id="test_id"):
    """
    Assert that a state transition is blocked by the validator.
    
    Args:
        validator_class: Validator class (e.g., EscrowStateValidator)
        current: Current status enum
        target: Target status enum
        entity_id: Entity ID for logging
    
    Raises:
        AssertionError: If transition is not blocked
    """
    is_valid, message = validator_class.validate_transition(current, target, entity_id)
    assert not is_valid, f"Expected blocked transition but got valid: {message}"


def assert_transition_allowed(validator_class, current, target, entity_id="test_id"):
    """
    Assert that a state transition is allowed by the validator.
    
    Args:
        validator_class: Validator class (e.g., EscrowStateValidator)
        current: Current status enum
        target: Target status enum
        entity_id: Entity ID for logging
    
    Raises:
        AssertionError: If transition is blocked
    """
    is_valid, message = validator_class.validate_transition(current, target, entity_id)
    assert is_valid, f"Expected valid transition but got: {message}"


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def all_escrow_statuses() -> List[EscrowStatus]:
    """Returns list of all EscrowStatus values"""
    return list(EscrowStatus)


@pytest.fixture
def terminal_escrow_statuses() -> List[EscrowStatus]:
    """Returns list of terminal EscrowStatus values"""
    return [
        EscrowStatus.COMPLETED,
        EscrowStatus.REFUNDED,
        EscrowStatus.CANCELLED
    ]


@pytest.fixture
def all_exchange_statuses() -> List[ExchangeStatus]:
    """Returns list of all ExchangeStatus values"""
    return list(ExchangeStatus)


@pytest.fixture
def terminal_exchange_statuses() -> List[ExchangeStatus]:
    """Returns list of terminal ExchangeStatus values"""
    return [
        ExchangeStatus.COMPLETED,
        ExchangeStatus.CANCELLED
    ]


@pytest.fixture
def all_cashout_statuses() -> List[CashoutStatus]:
    """Returns list of all CashoutStatus values"""
    return list(CashoutStatus)


@pytest.fixture
def terminal_cashout_statuses() -> List[CashoutStatus]:
    """Returns list of terminal CashoutStatus values"""
    return [
        CashoutStatus.SUCCESS,
        CashoutStatus.CANCELLED
    ]


@pytest.fixture
def all_unified_transaction_statuses() -> List[UnifiedTransactionStatus]:
    """Returns list of all UnifiedTransactionStatus values"""
    return list(UnifiedTransactionStatus)


@pytest.fixture
def terminal_unified_transaction_statuses() -> List[UnifiedTransactionStatus]:
    """Returns list of terminal UnifiedTransactionStatus values"""
    return [
        UnifiedTransactionStatus.SUCCESS,
        UnifiedTransactionStatus.CANCELLED,
        UnifiedTransactionStatus.REFUNDED
    ]


# ============================================================================
# TEST CLASS 1: ESCROW STATE TRANSITIONS
# ============================================================================

class TestEscrowStateTransitions:
    """
    Test suite for Escrow state transition validation.
    
    Covers:
    - Terminal state protection (COMPLETED, REFUNDED, CANCELLED, DISPUTED)
    - Backward transitions (ACTIVE → PAYMENT_PENDING)
    - Valid forward transitions
    - Edge cases
    """
    
    # --- Terminal State Protection Tests ---
    
    def test_cannot_overwrite_completed_status(self, all_escrow_statuses):
        """Terminal COMPLETED status cannot be changed to any other status except DISPUTED"""
        current = EscrowStatus.COMPLETED
        
        # DISPUTED is allowed from COMPLETED (dispute can reopen)
        allowed_transitions = {EscrowStatus.DISPUTED}
        
        for target in all_escrow_statuses:
            if target != current and target not in allowed_transitions:
                assert_transition_blocked(EscrowStateValidator, current, target, "ES_TEST_001")
    
    def test_cannot_overwrite_refunded_status(self, all_escrow_statuses):
        """Terminal REFUNDED status cannot be changed to any other status"""
        current = EscrowStatus.REFUNDED
        
        for target in all_escrow_statuses:
            if target != current:
                assert_transition_blocked(EscrowStateValidator, current, target, "ES_TEST_002")
    
    def test_cannot_overwrite_cancelled_status(self, all_escrow_statuses):
        """Terminal CANCELLED status cannot be changed to any other status"""
        current = EscrowStatus.CANCELLED
        
        for target in all_escrow_statuses:
            if target != current:
                assert_transition_blocked(EscrowStateValidator, current, target, "ES_TEST_003")
    
    # --- Backward Transition Tests ---
    
    def test_cannot_revert_active_to_payment_pending(self):
        """ACTIVE cannot revert to PAYMENT_PENDING (backward transition)"""
        assert_transition_blocked(
            EscrowStateValidator,
            EscrowStatus.ACTIVE,
            EscrowStatus.PAYMENT_PENDING,
            "ES_TEST_004"
        )
    
    def test_cannot_revert_active_to_created(self):
        """ACTIVE cannot revert to CREATED (backward transition)"""
        assert_transition_blocked(
            EscrowStateValidator,
            EscrowStatus.ACTIVE,
            EscrowStatus.CREATED,
            "ES_TEST_005"
        )
    
    def test_cannot_revert_payment_confirmed_to_pending_deposit(self):
        """PAYMENT_CONFIRMED cannot revert to PENDING_DEPOSIT"""
        assert_transition_blocked(
            EscrowStateValidator,
            EscrowStatus.PAYMENT_CONFIRMED,
            EscrowStatus.PENDING_DEPOSIT,
            "ES_TEST_006"
        )
    
    def test_cannot_revert_awaiting_seller_to_payment_pending(self):
        """AWAITING_SELLER cannot revert to PAYMENT_PENDING"""
        assert_transition_blocked(
            EscrowStateValidator,
            EscrowStatus.AWAITING_SELLER,
            EscrowStatus.PAYMENT_PENDING,
            "ES_TEST_007"
        )
    
    # --- Valid Transition Tests ---
    
    def test_valid_transition_created_to_payment_pending(self):
        """Valid transition from CREATED to PAYMENT_PENDING"""
        assert_transition_allowed(
            EscrowStateValidator,
            EscrowStatus.CREATED,
            EscrowStatus.PAYMENT_PENDING,
            "ES_TEST_008"
        )
    
    def test_valid_transition_payment_pending_to_payment_confirmed(self):
        """Valid transition from PAYMENT_PENDING to PAYMENT_CONFIRMED"""
        assert_transition_allowed(
            EscrowStateValidator,
            EscrowStatus.PAYMENT_PENDING,
            EscrowStatus.PAYMENT_CONFIRMED,
            "ES_TEST_009"
        )
    
    def test_valid_transition_payment_confirmed_to_active(self):
        """Valid transition from PAYMENT_CONFIRMED to ACTIVE"""
        assert_transition_allowed(
            EscrowStateValidator,
            EscrowStatus.PAYMENT_CONFIRMED,
            EscrowStatus.ACTIVE,
            "ES_TEST_010"
        )
    
    def test_valid_transition_active_to_completed(self):
        """Valid transition from ACTIVE to COMPLETED"""
        assert_transition_allowed(
            EscrowStateValidator,
            EscrowStatus.ACTIVE,
            EscrowStatus.COMPLETED,
            "ES_TEST_011"
        )
    
    def test_valid_transition_active_to_disputed(self):
        """Valid transition from ACTIVE to DISPUTED"""
        assert_transition_allowed(
            EscrowStateValidator,
            EscrowStatus.ACTIVE,
            EscrowStatus.DISPUTED,
            "ES_TEST_012"
        )
    
    def test_valid_transition_disputed_to_completed(self):
        """Valid transition from DISPUTED to COMPLETED (dispute resolved)"""
        assert_transition_allowed(
            EscrowStateValidator,
            EscrowStatus.DISPUTED,
            EscrowStatus.COMPLETED,
            "ES_TEST_013"
        )
    
    def test_valid_transition_disputed_to_refunded(self):
        """Valid transition from DISPUTED to REFUNDED (dispute resolved with refund)"""
        assert_transition_allowed(
            EscrowStateValidator,
            EscrowStatus.DISPUTED,
            EscrowStatus.REFUNDED,
            "ES_TEST_014"
        )
    
    def test_valid_transition_created_to_cancelled(self):
        """Valid transition from CREATED to CANCELLED"""
        assert_transition_allowed(
            EscrowStateValidator,
            EscrowStatus.CREATED,
            EscrowStatus.CANCELLED,
            "ES_TEST_015"
        )
    
    # --- Edge Cases ---
    
    def test_same_status_transition_is_noop(self):
        """Same status transition should be allowed (no-op)"""
        is_valid, message = EscrowStateValidator.validate_transition(
            EscrowStatus.ACTIVE,
            EscrowStatus.ACTIVE,
            "ES_TEST_016"
        )
        assert is_valid
        assert "no" in message.lower() or "same" in message.lower()


# ============================================================================
# TEST CLASS 2: EXCHANGE STATE TRANSITIONS
# ============================================================================

class TestExchangeStateTransitions:
    """
    Test suite for Exchange state transition validation.
    
    Covers:
    - Terminal state protection (COMPLETED, CANCELLED)
    - Backward transitions (PROCESSING → AWAITING_DEPOSIT)
    - Valid forward transitions
    - Edge cases
    """
    
    # --- Terminal State Protection Tests ---
    
    def test_cannot_overwrite_completed_status(self, all_exchange_statuses):
        """Terminal COMPLETED status cannot be changed to any other status"""
        current = ExchangeStatus.COMPLETED
        
        for target in all_exchange_statuses:
            if target != current:
                assert_transition_blocked(ExchangeStateValidator, current, target, "EX_TEST_001")
    
    def test_cannot_overwrite_cancelled_status(self, all_exchange_statuses):
        """Terminal CANCELLED status cannot be changed to any other status"""
        current = ExchangeStatus.CANCELLED
        
        for target in all_exchange_statuses:
            if target != current:
                assert_transition_blocked(ExchangeStateValidator, current, target, "EX_TEST_002")
    
    # --- Backward Transition Tests ---
    
    def test_cannot_revert_payment_received_to_awaiting_deposit(self):
        """PAYMENT_RECEIVED cannot revert to AWAITING_DEPOSIT"""
        assert_transition_blocked(
            ExchangeStateValidator,
            ExchangeStatus.PAYMENT_RECEIVED,
            ExchangeStatus.AWAITING_DEPOSIT,
            "EX_TEST_003"
        )
    
    def test_cannot_revert_payment_confirmed_to_rate_locked(self):
        """PAYMENT_CONFIRMED cannot revert to RATE_LOCKED"""
        assert_transition_blocked(
            ExchangeStateValidator,
            ExchangeStatus.PAYMENT_CONFIRMED,
            ExchangeStatus.RATE_LOCKED,
            "EX_TEST_004"
        )
    
    def test_cannot_revert_processing_to_payment_received(self):
        """PROCESSING cannot revert to PAYMENT_RECEIVED"""
        assert_transition_blocked(
            ExchangeStateValidator,
            ExchangeStatus.PROCESSING,
            ExchangeStatus.PAYMENT_RECEIVED,
            "EX_TEST_005"
        )
    
    def test_cannot_revert_processing_to_created(self):
        """PROCESSING cannot revert to CREATED"""
        assert_transition_blocked(
            ExchangeStateValidator,
            ExchangeStatus.PROCESSING,
            ExchangeStatus.CREATED,
            "EX_TEST_006"
        )
    
    # --- Valid Transition Tests ---
    
    def test_valid_transition_created_to_awaiting_deposit(self):
        """Valid transition from CREATED to AWAITING_DEPOSIT"""
        assert_transition_allowed(
            ExchangeStateValidator,
            ExchangeStatus.CREATED,
            ExchangeStatus.AWAITING_DEPOSIT,
            "EX_TEST_007"
        )
    
    def test_valid_transition_awaiting_deposit_to_payment_received(self):
        """Valid transition from AWAITING_DEPOSIT to PAYMENT_RECEIVED"""
        assert_transition_allowed(
            ExchangeStateValidator,
            ExchangeStatus.AWAITING_DEPOSIT,
            ExchangeStatus.PAYMENT_RECEIVED,
            "EX_TEST_008"
        )
    
    def test_valid_transition_payment_received_to_payment_confirmed(self):
        """Valid transition from PAYMENT_RECEIVED to PAYMENT_CONFIRMED"""
        assert_transition_allowed(
            ExchangeStateValidator,
            ExchangeStatus.PAYMENT_RECEIVED,
            ExchangeStatus.PAYMENT_CONFIRMED,
            "EX_TEST_009"
        )
    
    def test_valid_transition_payment_confirmed_to_processing(self):
        """Valid transition from PAYMENT_CONFIRMED to PROCESSING"""
        assert_transition_allowed(
            ExchangeStateValidator,
            ExchangeStatus.PAYMENT_CONFIRMED,
            ExchangeStatus.PROCESSING,
            "EX_TEST_010"
        )
    
    def test_valid_transition_processing_to_completed(self):
        """Valid transition from PROCESSING to COMPLETED"""
        assert_transition_allowed(
            ExchangeStateValidator,
            ExchangeStatus.PROCESSING,
            ExchangeStatus.COMPLETED,
            "EX_TEST_011"
        )
    
    def test_valid_transition_processing_to_failed(self):
        """Valid transition from PROCESSING to FAILED"""
        assert_transition_allowed(
            ExchangeStateValidator,
            ExchangeStatus.PROCESSING,
            ExchangeStatus.FAILED,
            "EX_TEST_012"
        )
    
    def test_valid_transition_failed_to_awaiting_deposit(self):
        """Valid transition from FAILED to AWAITING_DEPOSIT (retry)"""
        assert_transition_allowed(
            ExchangeStateValidator,
            ExchangeStatus.FAILED,
            ExchangeStatus.AWAITING_DEPOSIT,
            "EX_TEST_013"
        )
    
    def test_valid_transition_created_to_cancelled(self):
        """Valid transition from CREATED to CANCELLED"""
        assert_transition_allowed(
            ExchangeStateValidator,
            ExchangeStatus.CREATED,
            ExchangeStatus.CANCELLED,
            "EX_TEST_014"
        )
    
    # --- Edge Cases ---
    
    def test_same_status_transition_is_noop(self):
        """Same status transition should be allowed (no-op)"""
        is_valid, message = ExchangeStateValidator.validate_transition(
            ExchangeStatus.PROCESSING,
            ExchangeStatus.PROCESSING,
            "EX_TEST_015"
        )
        assert is_valid


# ============================================================================
# TEST CLASS 3: CASHOUT STATE TRANSITIONS
# ============================================================================

class TestCashoutStateTransitions:
    """
    Test suite for Cashout state transition validation.
    
    Covers:
    - Terminal state protection (SUCCESS, CANCELLED)
    - Backward transitions (SUCCESS → PENDING)
    - Valid forward transitions
    - Edge cases
    """
    
    # --- Terminal State Protection Tests ---
    
    def test_cannot_overwrite_success_status(self, all_cashout_statuses):
        """Terminal SUCCESS status cannot be changed to any other status"""
        current = CashoutStatus.SUCCESS
        
        for target in all_cashout_statuses:
            if target != current:
                assert_transition_blocked(CashoutStateValidator, current, target, "CO_TEST_001")
    
    def test_cannot_overwrite_cancelled_status(self, all_cashout_statuses):
        """Terminal CANCELLED status cannot be changed to any other status"""
        current = CashoutStatus.CANCELLED
        
        for target in all_cashout_statuses:
            if target != current:
                assert_transition_blocked(CashoutStateValidator, current, target, "CO_TEST_002")
    
    def test_completed_can_only_transition_to_success(self):
        """COMPLETED can only transition to SUCCESS"""
        current = CashoutStatus.COMPLETED
        
        # SUCCESS is allowed
        assert_transition_allowed(CashoutStateValidator, current, CashoutStatus.SUCCESS, "CO_TEST_003")
        
        # All others should be blocked
        blocked_targets = [
            CashoutStatus.PENDING,
            CashoutStatus.PROCESSING,
            CashoutStatus.FAILED,
            CashoutStatus.CANCELLED
        ]
        for target in blocked_targets:
            assert_transition_blocked(CashoutStateValidator, current, target, "CO_TEST_003B")
    
    # --- Backward Transition Tests ---
    
    def test_cannot_revert_processing_to_pending(self):
        """PROCESSING cannot revert to PENDING"""
        assert_transition_blocked(
            CashoutStateValidator,
            CashoutStatus.PROCESSING,
            CashoutStatus.PENDING,
            "CO_TEST_004"
        )
    
    def test_cannot_revert_executing_to_approved(self):
        """EXECUTING cannot revert to APPROVED"""
        assert_transition_blocked(
            CashoutStateValidator,
            CashoutStatus.EXECUTING,
            CashoutStatus.APPROVED,
            "CO_TEST_005"
        )
    
    def test_cannot_revert_completed_to_processing(self):
        """COMPLETED cannot revert to PROCESSING"""
        assert_transition_blocked(
            CashoutStateValidator,
            CashoutStatus.COMPLETED,
            CashoutStatus.PROCESSING,
            "CO_TEST_006"
        )
    
    def test_cannot_revert_admin_approved_to_pending(self):
        """ADMIN_APPROVED cannot revert to PENDING"""
        assert_transition_blocked(
            CashoutStateValidator,
            CashoutStatus.ADMIN_APPROVED,
            CashoutStatus.PENDING,
            "CO_TEST_007"
        )
    
    # --- Valid Transition Tests ---
    
    def test_valid_transition_pending_to_otp_pending(self):
        """Valid transition from PENDING to OTP_PENDING"""
        assert_transition_allowed(
            CashoutStateValidator,
            CashoutStatus.PENDING,
            CashoutStatus.OTP_PENDING,
            "CO_TEST_008"
        )
    
    def test_valid_transition_otp_pending_to_approved(self):
        """Valid transition from OTP_PENDING to APPROVED"""
        assert_transition_allowed(
            CashoutStateValidator,
            CashoutStatus.OTP_PENDING,
            CashoutStatus.APPROVED,
            "CO_TEST_009"
        )
    
    def test_valid_transition_approved_to_processing(self):
        """Valid transition from APPROVED to PROCESSING"""
        assert_transition_allowed(
            CashoutStateValidator,
            CashoutStatus.APPROVED,
            CashoutStatus.PROCESSING,
            "CO_TEST_010"
        )
    
    def test_valid_transition_processing_to_completed(self):
        """Valid transition from PROCESSING to COMPLETED"""
        assert_transition_allowed(
            CashoutStateValidator,
            CashoutStatus.PROCESSING,
            CashoutStatus.COMPLETED,
            "CO_TEST_011"
        )
    
    def test_valid_transition_completed_to_success(self):
        """Valid transition from COMPLETED to SUCCESS"""
        assert_transition_allowed(
            CashoutStateValidator,
            CashoutStatus.COMPLETED,
            CashoutStatus.SUCCESS,
            "CO_TEST_012"
        )
    
    def test_valid_transition_processing_to_failed(self):
        """Valid transition from PROCESSING to FAILED"""
        assert_transition_allowed(
            CashoutStateValidator,
            CashoutStatus.PROCESSING,
            CashoutStatus.FAILED,
            "CO_TEST_013"
        )
    
    def test_valid_transition_failed_to_pending(self):
        """Valid transition from FAILED to PENDING (retry)"""
        assert_transition_allowed(
            CashoutStateValidator,
            CashoutStatus.FAILED,
            CashoutStatus.PENDING,
            "CO_TEST_014"
        )
    
    def test_valid_transition_pending_to_cancelled(self):
        """Valid transition from PENDING to CANCELLED"""
        assert_transition_allowed(
            CashoutStateValidator,
            CashoutStatus.PENDING,
            CashoutStatus.CANCELLED,
            "CO_TEST_015"
        )
    
    # --- Edge Cases ---
    
    def test_same_status_transition_is_noop(self):
        """Same status transition should be allowed (no-op)"""
        is_valid, message = CashoutStateValidator.validate_transition(
            CashoutStatus.PROCESSING,
            CashoutStatus.PROCESSING,
            "CO_TEST_016"
        )
        assert is_valid


# ============================================================================
# TEST CLASS 4: UNIFIED TRANSACTION STATE TRANSITIONS
# ============================================================================

class TestUnifiedTransactionStateTransitions:
    """
    Test suite for UnifiedTransaction state transition validation.
    
    Covers:
    - Terminal state protection (SUCCESS, CANCELLED, REFUNDED)
    - Backward transitions (SUCCESS → PROCESSING)
    - Valid forward transitions across 4 phases
    - Edge cases
    """
    
    # --- Terminal State Protection Tests ---
    
    def test_cannot_overwrite_refunded_status(self, all_unified_transaction_statuses):
        """Terminal REFUNDED status cannot be changed to any other status"""
        current = UnifiedTransactionStatus.REFUNDED
        
        for target in all_unified_transaction_statuses:
            if target != current:
                assert_transition_blocked(
                    UnifiedTransactionStateValidator,
                    current,
                    target,
                    "UT_TEST_003"
                )
    
    # --- Backward Transition Tests ---
    
    def test_cannot_revert_success_to_processing(self):
        """SUCCESS cannot revert to PROCESSING"""
        assert_transition_blocked(
            UnifiedTransactionStateValidator,
            UnifiedTransactionStatus.SUCCESS,
            UnifiedTransactionStatus.PROCESSING,
            "UT_TEST_004"
        )
    
    def test_cannot_revert_processing_to_pending(self):
        """PROCESSING cannot revert to PENDING"""
        assert_transition_blocked(
            UnifiedTransactionStateValidator,
            UnifiedTransactionStatus.PROCESSING,
            UnifiedTransactionStatus.PENDING,
            "UT_TEST_005"
        )
    
    def test_cannot_revert_funds_released_to_funds_held(self):
        """FUNDS_RELEASED cannot revert to FUNDS_HELD"""
        assert_transition_blocked(
            UnifiedTransactionStateValidator,
            UnifiedTransactionStatus.FUNDS_RELEASED,
            UnifiedTransactionStatus.FUNDS_HELD,
            "UT_TEST_006"
        )
    
    def test_cannot_revert_payment_confirmed_to_awaiting_payment(self):
        """PAYMENT_CONFIRMED cannot revert to AWAITING_PAYMENT"""
        assert_transition_blocked(
            UnifiedTransactionStateValidator,
            UnifiedTransactionStatus.PAYMENT_CONFIRMED,
            UnifiedTransactionStatus.AWAITING_PAYMENT,
            "UT_TEST_007"
        )
    
    # --- Valid Transition Tests: Initiation Phase ---
    
    def test_valid_transition_pending_to_awaiting_payment(self):
        """Valid transition from PENDING to AWAITING_PAYMENT"""
        assert_transition_allowed(
            UnifiedTransactionStateValidator,
            UnifiedTransactionStatus.PENDING,
            UnifiedTransactionStatus.AWAITING_PAYMENT,
            "UT_TEST_008"
        )
    
    def test_valid_transition_awaiting_payment_to_payment_confirmed(self):
        """Valid transition from AWAITING_PAYMENT to PAYMENT_CONFIRMED"""
        assert_transition_allowed(
            UnifiedTransactionStateValidator,
            UnifiedTransactionStatus.AWAITING_PAYMENT,
            UnifiedTransactionStatus.PAYMENT_CONFIRMED,
            "UT_TEST_009"
        )
    
    # --- Valid Transition Tests: Authorization Phase ---
    
    def test_valid_transition_payment_confirmed_to_funds_held(self):
        """Valid transition from PAYMENT_CONFIRMED to FUNDS_HELD"""
        assert_transition_allowed(
            UnifiedTransactionStateValidator,
            UnifiedTransactionStatus.PAYMENT_CONFIRMED,
            UnifiedTransactionStatus.FUNDS_HELD,
            "UT_TEST_010"
        )
    
    def test_valid_transition_funds_held_to_awaiting_approval(self):
        """Valid transition from FUNDS_HELD to AWAITING_APPROVAL"""
        assert_transition_allowed(
            UnifiedTransactionStateValidator,
            UnifiedTransactionStatus.FUNDS_HELD,
            UnifiedTransactionStatus.AWAITING_APPROVAL,
            "UT_TEST_011"
        )
    
    def test_valid_transition_awaiting_approval_to_otp_pending(self):
        """Valid transition from AWAITING_APPROVAL to OTP_PENDING"""
        assert_transition_allowed(
            UnifiedTransactionStateValidator,
            UnifiedTransactionStatus.AWAITING_APPROVAL,
            UnifiedTransactionStatus.OTP_PENDING,
            "UT_TEST_012"
        )
    
    def test_valid_transition_otp_pending_to_processing(self):
        """Valid transition from OTP_PENDING to PROCESSING"""
        assert_transition_allowed(
            UnifiedTransactionStateValidator,
            UnifiedTransactionStatus.OTP_PENDING,
            UnifiedTransactionStatus.PROCESSING,
            "UT_TEST_013"
        )
    
    # --- Valid Transition Tests: Execution Phase ---
    
    def test_valid_transition_processing_to_external_pending(self):
        """Valid transition from PROCESSING to EXTERNAL_PENDING"""
        assert_transition_allowed(
            UnifiedTransactionStateValidator,
            UnifiedTransactionStatus.PROCESSING,
            UnifiedTransactionStatus.EXTERNAL_PENDING,
            "UT_TEST_014"
        )
    
    def test_valid_transition_external_pending_to_funds_released(self):
        """Valid transition from EXTERNAL_PENDING to FUNDS_RELEASED"""
        assert_transition_allowed(
            UnifiedTransactionStateValidator,
            UnifiedTransactionStatus.EXTERNAL_PENDING,
            UnifiedTransactionStatus.FUNDS_RELEASED,
            "UT_TEST_015"
        )
    
    def test_valid_transition_funds_released_to_completed(self):
        """Valid transition from FUNDS_RELEASED to COMPLETED"""
        assert_transition_allowed(
            UnifiedTransactionStateValidator,
            UnifiedTransactionStatus.FUNDS_RELEASED,
            UnifiedTransactionStatus.COMPLETED,
            "UT_TEST_016"
        )
    
    def test_valid_transition_completed_to_success(self):
        """Valid transition from COMPLETED to SUCCESS"""
        assert_transition_allowed(
            UnifiedTransactionStateValidator,
            UnifiedTransactionStatus.COMPLETED,
            UnifiedTransactionStatus.SUCCESS,
            "UT_TEST_017"
        )
    
    # --- Valid Transition Tests: Terminal Phase ---
    
    def test_valid_transition_processing_to_failed(self):
        """Valid transition from PROCESSING to FAILED"""
        assert_transition_allowed(
            UnifiedTransactionStateValidator,
            UnifiedTransactionStatus.PROCESSING,
            UnifiedTransactionStatus.FAILED,
            "UT_TEST_018"
        )
    
    def test_valid_transition_pending_to_cancelled(self):
        """Valid transition from PENDING to CANCELLED"""
        assert_transition_allowed(
            UnifiedTransactionStateValidator,
            UnifiedTransactionStatus.PENDING,
            UnifiedTransactionStatus.CANCELLED,
            "UT_TEST_019"
        )
    
    # --- Edge Cases ---
    
    def test_same_status_transition_is_noop(self):
        """Same status transition should be allowed (no-op)"""
        is_valid, message = UnifiedTransactionStateValidator.validate_transition(
            UnifiedTransactionStatus.PROCESSING,
            UnifiedTransactionStatus.PROCESSING,
            "UT_TEST_020"
        )
        assert is_valid


# ============================================================================
# TEST CLASS 5: USER STATE TRANSITIONS (Basic - No Formal Validator)
# ============================================================================

class TestUserStateTransitions:
    """
    Test suite for User state transitions (basic validation).
    
    Note: User doesn't have a formal state validator yet, so these tests
    verify graceful handling through StateTransitionService.
    """
    
    @pytest.mark.asyncio
    async def test_service_handles_user_entity_gracefully(self):
        """StateTransitionService handles user entity type gracefully"""
        result = await StateTransitionService.transition_entity_status(
            entity_type="user",
            entity_id="USER_TEST_001",
            current_status=UserStatus.ACTIVE,
            new_status=UserStatus.SUSPENDED,
            context="TEST"
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_user_active_to_suspended(self):
        """User can transition from ACTIVE to SUSPENDED"""
        result = await StateTransitionService.transition_entity_status(
            entity_type="user",
            entity_id="USER_TEST_002",
            current_status=UserStatus.ACTIVE,
            new_status=UserStatus.SUSPENDED,
            context="ADMIN_ACTION"
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_user_active_to_banned(self):
        """User can transition from ACTIVE to BANNED"""
        result = await StateTransitionService.transition_entity_status(
            entity_type="user",
            entity_id="USER_TEST_003",
            current_status=UserStatus.ACTIVE,
            new_status=UserStatus.BANNED,
            context="ADMIN_ACTION"
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_user_pending_verification_to_active(self):
        """User can transition from PENDING_VERIFICATION to ACTIVE"""
        result = await StateTransitionService.transition_entity_status(
            entity_type="user",
            entity_id="USER_TEST_004",
            current_status=UserStatus.PENDING_VERIFICATION,
            new_status=UserStatus.ACTIVE,
            context="VERIFICATION_COMPLETE"
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_user_suspended_to_active(self):
        """User can transition from SUSPENDED to ACTIVE (unbanned)"""
        result = await StateTransitionService.transition_entity_status(
            entity_type="user",
            entity_id="USER_TEST_005",
            current_status=UserStatus.SUSPENDED,
            new_status=UserStatus.ACTIVE,
            context="ADMIN_UNBAN"
        )
        assert result is True


# ============================================================================
# TEST CLASS 6: DISPUTE STATE TRANSITIONS (Basic - No Formal Validator)
# ============================================================================

class TestDisputeStateTransitions:
    """
    Test suite for Dispute state transitions (basic validation).
    
    Note: Dispute doesn't have a formal state validator yet, so these tests
    verify graceful handling through StateTransitionService.
    """
    
    @pytest.mark.asyncio
    async def test_service_handles_dispute_entity_gracefully(self):
        """StateTransitionService handles dispute entity type gracefully"""
        result = await StateTransitionService.transition_entity_status(
            entity_type="dispute",
            entity_id="DISPUTE_TEST_001",
            current_status=DisputeStatus.OPEN,
            new_status=DisputeStatus.UNDER_REVIEW,
            context="TEST"
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_dispute_open_to_under_review(self):
        """Dispute can transition from OPEN to UNDER_REVIEW"""
        result = await StateTransitionService.transition_entity_status(
            entity_type="dispute",
            entity_id="DISPUTE_TEST_002",
            current_status=DisputeStatus.OPEN,
            new_status=DisputeStatus.UNDER_REVIEW,
            context="ADMIN_REVIEW"
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_dispute_under_review_to_resolved(self):
        """Dispute can transition from UNDER_REVIEW to RESOLVED"""
        result = await StateTransitionService.transition_entity_status(
            entity_type="dispute",
            entity_id="DISPUTE_TEST_003",
            current_status=DisputeStatus.UNDER_REVIEW,
            new_status=DisputeStatus.RESOLVED,
            context="ADMIN_RESOLUTION"
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_dispute_open_to_resolved(self):
        """Dispute can transition from OPEN to RESOLVED (quick resolution)"""
        result = await StateTransitionService.transition_entity_status(
            entity_type="dispute",
            entity_id="DISPUTE_TEST_004",
            current_status=DisputeStatus.OPEN,
            new_status=DisputeStatus.RESOLVED,
            context="QUICK_RESOLUTION"
        )
        assert result is True


# ============================================================================
# TEST CLASS 7: STATE TRANSITION SERVICE INTEGRATION TESTS
# ============================================================================

class TestStateTransitionService:
    """
    Integration tests for StateTransitionService centralized validation.
    
    Tests:
    - Service validates all 6 entity types
    - Service blocks invalid transitions
    - Service allows valid transitions
    - Error handling and edge cases
    """
    
    # --- Service Validation for All Entity Types ---
    
    @pytest.mark.asyncio
    async def test_service_validates_escrow_transitions(self):
        """Service correctly validates escrow transitions"""
        # Valid transition
        result = await StateTransitionService.transition_entity_status(
            entity_type="escrow",
            entity_id="SERVICE_TEST_ES_001",
            current_status=EscrowStatus.CREATED,
            new_status=EscrowStatus.PAYMENT_PENDING,
            context="WEBHOOK"
        )
        assert result is True
        
        # Invalid transition
        result = await StateTransitionService.transition_entity_status(
            entity_type="escrow",
            entity_id="SERVICE_TEST_ES_002",
            current_status=EscrowStatus.COMPLETED,
            new_status=EscrowStatus.CREATED,
            context="WEBHOOK"
        )
        assert result is False
    
    @pytest.mark.asyncio
    async def test_service_validates_exchange_transitions(self):
        """Service correctly validates exchange transitions"""
        # Valid transition
        result = await StateTransitionService.transition_entity_status(
            entity_type="exchange",
            entity_id="SERVICE_TEST_EX_001",
            current_status=ExchangeStatus.AWAITING_DEPOSIT,
            new_status=ExchangeStatus.PAYMENT_RECEIVED,
            context="WEBHOOK"
        )
        assert result is True
        
        # Invalid transition
        result = await StateTransitionService.transition_entity_status(
            entity_type="exchange",
            entity_id="SERVICE_TEST_EX_002",
            current_status=ExchangeStatus.COMPLETED,
            new_status=ExchangeStatus.CREATED,
            context="WEBHOOK"
        )
        assert result is False
    
    @pytest.mark.asyncio
    async def test_service_validates_cashout_transitions(self):
        """Service correctly validates cashout transitions"""
        # Valid transition (APPROVED -> PROCESSING)
        result = await StateTransitionService.transition_entity_status(
            entity_type="cashout",
            entity_id="SERVICE_TEST_CO_001",
            current_status=CashoutStatus.APPROVED,
            new_status=CashoutStatus.PROCESSING,
            context="WEBHOOK"
        )
        assert result is True
        
        # Invalid transition
        result = await StateTransitionService.transition_entity_status(
            entity_type="cashout",
            entity_id="SERVICE_TEST_CO_002",
            current_status=CashoutStatus.SUCCESS,
            new_status=CashoutStatus.PENDING,
            context="WEBHOOK"
        )
        assert result is False
    
    @pytest.mark.asyncio
    async def test_service_validates_unified_transaction_transitions(self):
        """Service correctly validates unified transaction transitions"""
        # Valid transition
        result = await StateTransitionService.transition_entity_status(
            entity_type="unified_transaction",
            entity_id="SERVICE_TEST_UT_001",
            current_status=UnifiedTransactionStatus.PENDING,
            new_status=UnifiedTransactionStatus.PROCESSING,
            context="WEBHOOK"
        )
        assert result is True
        
        # Invalid transition
        result = await StateTransitionService.transition_entity_status(
            entity_type="unified_transaction",
            entity_id="SERVICE_TEST_UT_002",
            current_status=UnifiedTransactionStatus.SUCCESS,
            new_status=UnifiedTransactionStatus.PENDING,
            context="WEBHOOK"
        )
        assert result is False
    
    # --- Invalid Entity Type Handling ---
    
    @pytest.mark.asyncio
    async def test_service_raises_error_for_unknown_entity_type(self):
        """Service raises ValueError for unknown entity types"""
        with pytest.raises(ValueError, match="Unknown entity_type"):
            await StateTransitionService.transition_entity_status(
                entity_type="unknown_entity",
                entity_id="SERVICE_TEST_UNKNOWN_001",
                current_status=CashoutStatus.PENDING,  # type: ignore
                new_status=CashoutStatus.SUCCESS,  # type: ignore
                context="TEST"
            )
    
    # --- Terminal State Protection via Service ---
    
    @pytest.mark.asyncio
    async def test_service_blocks_escrow_completed_to_created(self):
        """Service blocks COMPLETED → CREATED for escrow"""
        result = await StateTransitionService.transition_entity_status(
            entity_type="escrow",
            entity_id="SERVICE_TEST_TERMINAL_001",
            current_status=EscrowStatus.COMPLETED,
            new_status=EscrowStatus.CREATED,
            context="ADMIN"
        )
        assert result is False
    
    @pytest.mark.asyncio
    async def test_service_blocks_exchange_completed_to_awaiting(self):
        """Service blocks COMPLETED → AWAITING_DEPOSIT for exchange"""
        result = await StateTransitionService.transition_entity_status(
            entity_type="exchange",
            entity_id="SERVICE_TEST_TERMINAL_002",
            current_status=ExchangeStatus.COMPLETED,
            new_status=ExchangeStatus.AWAITING_DEPOSIT,
            context="ADMIN"
        )
        assert result is False
    
    @pytest.mark.asyncio
    async def test_service_blocks_cashout_success_to_pending(self):
        """Service blocks SUCCESS → PENDING for cashout"""
        result = await StateTransitionService.transition_entity_status(
            entity_type="cashout",
            entity_id="SERVICE_TEST_TERMINAL_003",
            current_status=CashoutStatus.SUCCESS,
            new_status=CashoutStatus.PENDING,
            context="RETRY"
        )
        assert result is False
    
    # --- Edge Cases ---
    
    @pytest.mark.asyncio
    async def test_service_handles_same_status_transition(self):
        """Service allows same-status transitions (no-op)"""
        result = await StateTransitionService.transition_entity_status(
            entity_type="escrow",
            entity_id="SERVICE_TEST_SAME_001",
            current_status=EscrowStatus.ACTIVE,
            new_status=EscrowStatus.ACTIVE,
            context="DUPLICATE_WEBHOOK"
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_service_handles_empty_entity_id(self):
        """Service handles empty/None entity IDs gracefully"""
        result = await StateTransitionService.transition_entity_status(
            entity_type="escrow",
            entity_id="",  # Empty string instead of None
            current_status=EscrowStatus.CREATED,
            new_status=EscrowStatus.PAYMENT_PENDING,
            context="TEST"
        )
        assert result is True
    
    # --- Context-Specific Behavior ---
    
    @pytest.mark.asyncio
    async def test_service_validates_webhook_context(self):
        """Service validates transitions in webhook context"""
        result = await StateTransitionService.transition_entity_status(
            entity_type="exchange",
            entity_id="SERVICE_TEST_WEBHOOK_001",
            current_status=ExchangeStatus.PAYMENT_RECEIVED,
            new_status=ExchangeStatus.PROCESSING,
            context="WEBHOOK_PAYMENT_CONFIRMATION"
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_service_validates_admin_context(self):
        """Service validates transitions in admin context"""
        result = await StateTransitionService.transition_entity_status(
            entity_type="cashout",
            entity_id="SERVICE_TEST_ADMIN_001",
            current_status=CashoutStatus.FAILED,
            new_status=CashoutStatus.PENDING,
            context="ADMIN_RETRY"
        )
        assert result is True
    
    # --- Comprehensive Terminal State Protection ---
    
    @pytest.mark.asyncio
    async def test_service_protects_all_terminal_states(self):
        """Service protects all terminal states across all entity types"""
        terminal_tests = [
            ("escrow", EscrowStatus.COMPLETED, EscrowStatus.CREATED),
            ("escrow", EscrowStatus.REFUNDED, EscrowStatus.ACTIVE),
            ("escrow", EscrowStatus.CANCELLED, EscrowStatus.CREATED),
            ("exchange", ExchangeStatus.COMPLETED, ExchangeStatus.CREATED),
            ("exchange", ExchangeStatus.CANCELLED, ExchangeStatus.AWAITING_DEPOSIT),
            ("cashout", CashoutStatus.SUCCESS, CashoutStatus.PROCESSING),
            ("cashout", CashoutStatus.CANCELLED, CashoutStatus.PENDING),
            ("unified_transaction", UnifiedTransactionStatus.SUCCESS, UnifiedTransactionStatus.PENDING),
            ("unified_transaction", UnifiedTransactionStatus.CANCELLED, UnifiedTransactionStatus.PROCESSING),
            ("unified_transaction", UnifiedTransactionStatus.REFUNDED, UnifiedTransactionStatus.FUNDS_HELD),
        ]
        
        for entity_type, current, target in terminal_tests:
            result = await StateTransitionService.transition_entity_status(
                entity_type=entity_type,
                entity_id=f"TERMINAL_TEST_{entity_type.upper()}",
                current_status=current,
                new_status=target,
                context="TEST"
            )
            assert result is False, f"Terminal state {current} should not transition to {target}"
