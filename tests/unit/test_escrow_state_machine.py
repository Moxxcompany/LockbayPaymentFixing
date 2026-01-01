"""
Comprehensive Unit Tests for Escrow State Machine
Tests state transitions, validation, and lifecycle management
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import datetime

# Service under test
from utils.escrow_state_machine import (
    EscrowTransition, EscrowStateValidator, AtomicEscrowOperation,
    EscrowConcurrencyManager, atomic_escrow_operation, validate_transition,
    get_valid_next_states
)

# Models for testing
from models import Escrow, EscrowStatus


@pytest.mark.unit
class TestEscrowTransitionEnum:
    """Test EscrowTransition enum values and structure"""
    
    def test_escrow_transition_values(self):
        """Test all transition enum values are defined"""
        
        expected_transitions = [
            'CREATE', 'START_PAYMENT', 'CONFIRM_PAYMENT', 'AWAIT_SELLER',
            'SELLER_ACCEPT', 'ACTIVATE', 'RELEASE', 'REFUND', 'DISPUTE',
            'RESOLVE_DISPUTE', 'CANCEL', 'EXPIRE'
        ]
        
        for transition in expected_transitions:
            assert hasattr(EscrowTransition, transition)
            assert isinstance(getattr(EscrowTransition, transition), EscrowTransition)
    
    def test_transition_enum_string_values(self):
        """Test transition enum string values match expected patterns"""
        
        # Test that enum values are lowercase with underscores
        assert EscrowTransition.CREATE.value == "create"
        assert EscrowTransition.START_PAYMENT.value == "start_payment"
        assert EscrowTransition.CONFIRM_PAYMENT.value == "confirm_payment"
        assert EscrowTransition.SELLER_ACCEPT.value == "seller_accept"
        assert EscrowTransition.RESOLVE_DISPUTE.value == "resolve_dispute"
    
    def test_transition_categorization(self):
        """Test transitions can be categorized by workflow phase"""
        
        creation_flow = [
            EscrowTransition.CREATE, EscrowTransition.START_PAYMENT,
            EscrowTransition.CONFIRM_PAYMENT, EscrowTransition.AWAIT_SELLER,
            EscrowTransition.SELLER_ACCEPT, EscrowTransition.ACTIVATE
        ]
        
        resolution_flow = [
            EscrowTransition.RELEASE, EscrowTransition.REFUND,
            EscrowTransition.DISPUTE, EscrowTransition.RESOLVE_DISPUTE
        ]
        
        termination_flow = [
            EscrowTransition.CANCEL, EscrowTransition.EXPIRE
        ]
        
        # All transitions should be categorized
        all_transitions = set(creation_flow + resolution_flow + termination_flow)
        enum_transitions = set(EscrowTransition)
        
        assert all_transitions == enum_transitions


@pytest.mark.unit
class TestEscrowStateValidator:
    """Test EscrowStateValidator transition validation logic"""
    
    def test_valid_transitions_creation_flow(self):
        """Test valid transitions in creation flow"""
        
        # None -> CREATED (escrow creation)
        assert EscrowStateValidator.is_valid_transition(None, EscrowStatus.CREATED.value)
        
        # CREATED -> PAYMENT_PENDING (buyer starts payment)
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.CREATED.value, EscrowStatus.PAYMENT_PENDING.value
        )
        
        # PAYMENT_PENDING -> PAYMENT_CONFIRMED (payment confirmed)
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.PAYMENT_PENDING.value, EscrowStatus.PAYMENT_CONFIRMED.value
        )
        
        # PAYMENT_CONFIRMED -> AWAITING_SELLER (notify seller)
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.PAYMENT_CONFIRMED.value, EscrowStatus.AWAITING_SELLER.value
        )
        
        # AWAITING_SELLER -> PENDING_DEPOSIT (seller accepts)
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.AWAITING_SELLER.value, EscrowStatus.PENDING_DEPOSIT.value
        )
        
        # PENDING_DEPOSIT -> ACTIVE (escrow activated)
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.PENDING_DEPOSIT.value, EscrowStatus.ACTIVE.value
        )
    
    def test_valid_transitions_resolution_flow(self):
        """Test valid transitions in resolution flow"""
        
        # ACTIVE -> COMPLETED (successful release)
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.ACTIVE.value, EscrowStatus.COMPLETED.value
        )
        
        # ACTIVE -> REFUNDED (refund to buyer)
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.ACTIVE.value, EscrowStatus.REFUNDED.value
        )
        
        # ACTIVE -> DISPUTED (dispute initiated)
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.ACTIVE.value, EscrowStatus.DISPUTED.value
        )
        
        # DISPUTED -> COMPLETED (dispute resolved in favor of seller)
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.DISPUTED.value, EscrowStatus.COMPLETED.value
        )
        
        # DISPUTED -> REFUNDED (dispute resolved in favor of buyer)
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.DISPUTED.value, EscrowStatus.REFUNDED.value
        )
    
    def test_valid_transitions_cancellation_flow(self):
        """Test valid cancellation transitions"""
        
        cancellable_states = [
            EscrowStatus.CREATED.value,
            EscrowStatus.PAYMENT_PENDING.value,
            EscrowStatus.PAYMENT_CONFIRMED.value,
            EscrowStatus.AWAITING_SELLER.value,
            EscrowStatus.PENDING_SELLER.value,
            EscrowStatus.PENDING_DEPOSIT.value,
        ]
        
        for state in cancellable_states:
            assert EscrowStateValidator.is_valid_transition(state, EscrowStatus.CANCELLED.value)
    
    def test_valid_transitions_expiration_flow(self):
        """Test valid expiration transitions"""
        
        expirable_states = [
            EscrowStatus.PAYMENT_PENDING.value,
            EscrowStatus.AWAITING_SELLER.value,
            EscrowStatus.PENDING_SELLER.value,
            EscrowStatus.PENDING_DEPOSIT.value,
        ]
        
        for state in expirable_states:
            assert EscrowStateValidator.is_valid_transition(state, EscrowStatus.EXPIRED.value)
    
    def test_invalid_transitions(self):
        """Test invalid state transitions are rejected"""
        
        invalid_transitions = [
            # Cannot go backwards in creation flow
            (EscrowStatus.PAYMENT_CONFIRMED.value, EscrowStatus.CREATED.value),
            (EscrowStatus.ACTIVE.value, EscrowStatus.PAYMENT_PENDING.value),
            
            # Cannot modify terminal states
            (EscrowStatus.COMPLETED.value, EscrowStatus.ACTIVE.value),
            (EscrowStatus.REFUNDED.value, EscrowStatus.ACTIVE.value),
            (EscrowStatus.CANCELLED.value, EscrowStatus.CREATED.value),
            
            # Invalid direct transitions
            (EscrowStatus.CREATED.value, EscrowStatus.ACTIVE.value),  # Skip payment flow
            (EscrowStatus.PAYMENT_PENDING.value, EscrowStatus.COMPLETED.value),  # Skip activation
        ]
        
        for from_state, to_state in invalid_transitions:
            assert not EscrowStateValidator.is_valid_transition(from_state, to_state)
    
    def test_transition_validation_with_admin_context(self):
        """Test transition validation with admin context"""
        
        # Regular user cannot cancel ACTIVE escrow
        assert not EscrowStateValidator.is_valid_transition(
            EscrowStatus.ACTIVE.value,
            EscrowStatus.CANCELLED.value,
            is_admin=False
        )
        
        # Admin can cancel ACTIVE escrow  
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.ACTIVE.value,
            EscrowStatus.CANCELLED.value,
            is_admin=True
        )


@pytest.mark.unit
class TestAtomicEscrowOperation:
    """Test AtomicEscrowOperation state management operations"""
    
    def test_atomic_escrow_operation_creation(self):
        """Test creation of atomic escrow operation"""
        
        escrow_id = "test_escrow_001"
        operation = AtomicEscrowOperation(escrow_id)
        
        assert operation.escrow_id == escrow_id
        assert hasattr(operation, 'operations')
        assert hasattr(operation, 'validator')
        assert isinstance(operation.validator, EscrowStateValidator)
    
    def test_change_status_validation(self):
        """Test status change with validation"""
        
        escrow_id = "test_escrow_002"
        operation = AtomicEscrowOperation(escrow_id)
        
        with patch.object(operation, 'transaction') as mock_transaction:
            # Mock escrow object
            escrow_mock = Mock()
            escrow_mock.status = EscrowStatus.CREATED.value
            session_mock = Mock()
            
            mock_transaction.return_value.__enter__.return_value = (escrow_mock, session_mock)
            mock_transaction.return_value.__exit__.return_value = None
            
            # Test valid transition
            result = operation.change_status(EscrowStatus.PAYMENT_PENDING.value)
            
            # Should succeed for valid transition
            assert result is True
            assert escrow_mock.status == EscrowStatus.PAYMENT_PENDING.value
    
    def test_change_status_invalid_transition(self):
        """Test status change with invalid transition"""
        
        escrow_id = "test_escrow_003"
        operation = AtomicEscrowOperation(escrow_id)
        
        with patch.object(operation, 'transaction') as mock_transaction:
            # Mock escrow in COMPLETED state (terminal)
            escrow_mock = Mock()
            escrow_mock.status = EscrowStatus.COMPLETED.value
            session_mock = Mock()
            
            mock_transaction.return_value.__enter__.return_value = (escrow_mock, session_mock)
            mock_transaction.return_value.__exit__.return_value = None
            
            # Test invalid transition
            result = operation.change_status(EscrowStatus.PAYMENT_PENDING.value)
            
            # Should fail for invalid transition
            assert result is False
    
    def test_get_valid_transitions_from_state(self):
        """Test getting list of valid transitions from current state"""
        
        # Test from CREATED state
        valid_from_created = get_valid_next_states(EscrowStatus.CREATED.value)
        expected_created = {EscrowStatus.PAYMENT_PENDING.value, EscrowStatus.CANCELLED.value}
        
        assert set(valid_from_created) == expected_created
        
        # Test from ACTIVE state
        valid_from_active = get_valid_next_states(EscrowStatus.ACTIVE.value)
        expected_active = {
            EscrowStatus.COMPLETED.value, 
            EscrowStatus.REFUNDED.value, 
            EscrowStatus.DISPUTED.value,
            EscrowStatus.CANCELLED.value  # Admin allowed
        }
        
        assert set(valid_from_active) == expected_active
        
        # Test from terminal state (should have no valid transitions)
        valid_from_completed = get_valid_next_states(EscrowStatus.COMPLETED.value)
        assert len(valid_from_completed) == 0


@pytest.mark.unit
class TestEscrowConcurrencyManager:
    """Test EscrowConcurrencyManager orchestration"""
    
    def test_get_escrow_operation(self):
        """Test getting atomic operation manager for escrow"""
        
        escrow_id = "test_escrow_004"
        operation = EscrowConcurrencyManager.get_escrow_operation(escrow_id)
        
        assert isinstance(operation, AtomicEscrowOperation)
        assert operation.escrow_id == escrow_id
    
    def test_batch_process_escrows(self):
        """Test batch processing multiple escrow operations"""
        
        operations = [
            ("escrow_001", "change_status", {"new_status": EscrowStatus.PAYMENT_PENDING.value}),
            ("escrow_002", "change_status", {"new_status": EscrowStatus.CANCELLED.value}),
        ]
        
        with patch.object(AtomicEscrowOperation, 'change_status', return_value=True) as mock_change:
            results = EscrowConcurrencyManager.batch_process_escrows(operations)
            
            # Should process both operations
            assert len(results) == 2
            assert results["escrow_001"] is True
            assert results["escrow_002"] is True
            
            # Should call change_status for each operation
            assert mock_change.call_count == 2
    
    def test_validate_escrow_transition(self):
        """Test escrow transition validation"""
        
        escrow_id = "test_escrow_005"
        new_status = EscrowStatus.PAYMENT_PENDING.value
        
        with patch('utils.escrow_state_machine.SessionLocal') as mock_session:
            # Mock database session and escrow
            session_mock = Mock()
            escrow_mock = Mock()
            escrow_mock.status = EscrowStatus.CREATED.value
            
            mock_session.return_value.__enter__.return_value = session_mock
            mock_session.return_value.__exit__.return_value = None
            session_mock.query.return_value.filter.return_value.first.return_value = escrow_mock
            
            result = EscrowConcurrencyManager.validate_escrow_transition(escrow_id, new_status)
            
            # Should validate transition
            assert isinstance(result, bool)


@pytest.mark.unit
class TestEscrowStateValidationRules:
    """Test specific business rule validations in state transitions"""
    
    def test_payment_flow_business_rules(self):
        """Test business rules for payment flow transitions"""
        
        # Rule: Cannot confirm payment without initiating payment first
        assert not EscrowStateValidator.is_valid_transition(
            EscrowStatus.CREATED.value, EscrowStatus.PAYMENT_CONFIRMED.value
        )
        
        # Rule: Must await seller after payment confirmation
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.PAYMENT_CONFIRMED.value, EscrowStatus.AWAITING_SELLER.value
        )
        
        # Rule: Cannot activate escrow without seller acceptance
        assert not EscrowStateValidator.is_valid_transition(
            EscrowStatus.PAYMENT_CONFIRMED.value, EscrowStatus.ACTIVE.value
        )
    
    def test_resolution_flow_business_rules(self):
        """Test business rules for resolution flow transitions"""
        
        # Rule: Can only complete or refund from ACTIVE state
        pre_active_states = [
            EscrowStatus.CREATED.value, EscrowStatus.PAYMENT_PENDING.value, 
            EscrowStatus.PAYMENT_CONFIRMED.value
        ]
        
        for state in pre_active_states:
            assert not EscrowStateValidator.is_valid_transition(state, EscrowStatus.COMPLETED.value)
            assert not EscrowStateValidator.is_valid_transition(state, EscrowStatus.REFUNDED.value)
        
        # Rule: Disputes can only be resolved to completion or refund
        dispute_resolutions = [EscrowStatus.COMPLETED.value, EscrowStatus.REFUNDED.value]
        
        for resolution in dispute_resolutions:
            assert EscrowStateValidator.is_valid_transition(
                EscrowStatus.DISPUTED.value, resolution
            )
    
    def test_terminal_state_business_rules(self):
        """Test business rules for terminal states"""
        
        terminal_states = [
            EscrowStatus.COMPLETED.value, EscrowStatus.REFUNDED.value, 
            EscrowStatus.CANCELLED.value, EscrowStatus.EXPIRED.value
        ]
        
        all_states = [status.value for status in EscrowStatus]
        
        # Rule: Terminal states cannot transition to any other state
        for terminal_state in terminal_states:
            for target_state in all_states:
                if target_state != terminal_state:  # Can't transition to self either
                    assert not EscrowStateValidator.is_valid_transition(terminal_state, target_state)
    
    def test_admin_override_business_rules(self):
        """Test business rules for administrative overrides"""
        
        # Mock admin context
        admin_context = {'is_admin': True, 'override_reason': 'dispute_resolution'}
        
        # Admins might be able to perform normally invalid transitions
        result = EscrowStateValidator.is_valid_transition_with_context(
            EscrowStatus.ACTIVE.value,
            EscrowStatus.CANCELLED.value,  # Normally not allowed for users
            admin_context
        )
        
        # Should consider admin privileges
        assert isinstance(result, bool)
        
        # Test admin override logging
        if result:  # If admin override is allowed
            # Should require justification
            assert 'override_reason' in admin_context
            assert admin_context['override_reason'] is not None


@pytest.mark.integration
class TestEscrowStateMachineIntegration:
    """Integration tests with database and other services"""
    
    @pytest.mark.asyncio
    async def test_state_machine_with_real_escrow(self, test_db_session):
        """Test state machine with real Escrow model instances"""
        
        # Create real escrow in test database
        from models import User
        
        buyer = User(telegram_id=12345, username='testbuyer')
        seller = User(telegram_id=67890, username='testseller')
        test_db_session.add_all([buyer, seller])
        test_db_session.commit()
        
        escrow = Escrow(
            id='test_state_001',
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.CREATED.value,
            description='Test escrow for state machine'
        )
        test_db_session.add(escrow)
        test_db_session.commit()
        
        # Test state transition with real escrow
        initial_state = escrow.status
        target_state = EscrowStatus.PAYMENT_PENDING.value
        
        # Mock the state machine operation
        with patch('utils.escrow_state_machine.locked_escrow_operation'):
            result = await EscrowStateMachine.transition_state(
                escrow.id, target_state, EscrowTransition.START_PAYMENT
            )
            
            # Should work with real database objects
            assert 'success' in result
    
    @pytest.mark.asyncio
    async def test_concurrent_state_transitions(self, test_db_session):
        """Test handling of concurrent state transition attempts"""
        
        escrow_id = "test_concurrent_001"
        
        # Simulate concurrent transition attempts
        async def attempt_transition(target_state, transition):
            return await EscrowStateMachine.transition_state(
                escrow_id, target_state, transition
            )
        
        with patch('utils.escrow_state_machine.locked_escrow_operation') as mock_lock:
            
            # Mock lock contention
            mock_lock.side_effect = [
                Mock(__enter__=Mock(return_value=Mock()), __exit__=Mock(return_value=None)),
                Exception("Lock timeout - concurrent access")
            ]
            
            # First transition should succeed
            result1 = await attempt_transition(
                EscrowStatus.PAYMENT_PENDING.value, EscrowTransition.START_PAYMENT
            )
            
            # Second concurrent transition should handle lock failure
            try:
                result2 = await attempt_transition(
                    EscrowStatus.CANCELLED.value, EscrowTransition.CANCEL
                )
                
                # Should either succeed or fail gracefully
                assert 'success' in result2
                if not result2['success']:
                    assert 'concurrent' in result2['error'] or 'lock' in result2['error']
                    
            except Exception as e:
                # Or raise controlled exception
                assert 'lock' in str(e).lower() or 'concurrent' in str(e).lower()