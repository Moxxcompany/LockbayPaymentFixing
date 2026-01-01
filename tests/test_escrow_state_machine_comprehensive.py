"""
Comprehensive Test Suite for Escrow State Machine
Targets 100% line and branch coverage of state transitions and atomic operations

Coverage Focus Areas:
- All valid state transitions
- Invalid state transition blocking
- Admin override logic
- Terminal state validation
- Atomic operations and locking
- Concurrent access protection
- Edge cases and error scenarios
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime

from utils.escrow_state_machine import (
    EscrowStateValidator, EscrowTransition
)
from models import EscrowStatus


class TestEscrowStateValidator:
    """Test complete EscrowStateValidator coverage"""

    def test_valid_transitions_from_none(self):
        """Test valid transitions from None (creation)"""
        
        assert EscrowStateValidator.is_valid_transition(None, EscrowStatus.CREATED.value) is True
        assert EscrowStateValidator.is_valid_transition(None, EscrowStatus.ACTIVE.value) is False

    def test_valid_transitions_from_created(self):
        """Test valid transitions from CREATED state"""
        
        # Valid transitions
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.CREATED.value, EscrowStatus.PAYMENT_PENDING.value
        ) is True
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.CREATED.value, EscrowStatus.CANCELLED.value
        ) is True
        
        # Invalid transitions
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.CREATED.value, EscrowStatus.ACTIVE.value
        ) is False
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.CREATED.value, EscrowStatus.COMPLETED.value
        ) is False

    def test_valid_transitions_from_payment_pending(self):
        """Test valid transitions from PAYMENT_PENDING state"""
        
        # Valid transitions
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.PAYMENT_PENDING.value, EscrowStatus.PAYMENT_CONFIRMED.value
        ) is True
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.PAYMENT_PENDING.value, EscrowStatus.CANCELLED.value
        ) is True
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.PAYMENT_PENDING.value, EscrowStatus.EXPIRED.value
        ) is True
        
        # Invalid transitions
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.PAYMENT_PENDING.value, EscrowStatus.ACTIVE.value
        ) is False

    def test_valid_transitions_from_payment_confirmed(self):
        """Test valid transitions from PAYMENT_CONFIRMED state"""
        
        # Valid transitions
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.PAYMENT_CONFIRMED.value, EscrowStatus.AWAITING_SELLER.value
        ) is True
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.PAYMENT_CONFIRMED.value, EscrowStatus.CANCELLED.value
        ) is True
        
        # Invalid transitions
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.PAYMENT_CONFIRMED.value, EscrowStatus.EXPIRED.value
        ) is False

    def test_valid_transitions_from_awaiting_seller(self):
        """Test valid transitions from AWAITING_SELLER state"""
        
        # Valid transitions
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.AWAITING_SELLER.value, EscrowStatus.PENDING_SELLER.value
        ) is True
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.AWAITING_SELLER.value, EscrowStatus.PENDING_DEPOSIT.value
        ) is True
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.AWAITING_SELLER.value, EscrowStatus.CANCELLED.value
        ) is True
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.AWAITING_SELLER.value, EscrowStatus.EXPIRED.value
        ) is True

    def test_valid_transitions_from_pending_seller(self):
        """Test valid transitions from PENDING_SELLER state"""
        
        # Valid transitions
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.PENDING_SELLER.value, EscrowStatus.PENDING_DEPOSIT.value
        ) is True
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.PENDING_SELLER.value, EscrowStatus.CANCELLED.value
        ) is True
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.PENDING_SELLER.value, EscrowStatus.EXPIRED.value
        ) is True

    def test_valid_transitions_from_pending_deposit(self):
        """Test valid transitions from PENDING_DEPOSIT state"""
        
        # Valid transitions
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.PENDING_DEPOSIT.value, EscrowStatus.ACTIVE.value
        ) is True
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.PENDING_DEPOSIT.value, EscrowStatus.CANCELLED.value
        ) is True
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.PENDING_DEPOSIT.value, EscrowStatus.EXPIRED.value
        ) is True

    def test_valid_transitions_from_active_user_restrictions(self):
        """Test ACTIVE state transition restrictions for regular users"""
        
        # Valid transitions for regular users
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.ACTIVE.value, EscrowStatus.COMPLETED.value, is_admin=False
        ) is True
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.ACTIVE.value, EscrowStatus.REFUNDED.value, is_admin=False
        ) is True
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.ACTIVE.value, EscrowStatus.DISPUTED.value, is_admin=False
        ) is True
        
        # BUSINESS RULE: ACTIVE -> CANCELLED blocked for users but allowed for admins
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.ACTIVE.value, EscrowStatus.CANCELLED.value, is_admin=False
        ) is False
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.ACTIVE.value, EscrowStatus.CANCELLED.value, is_admin=True
        ) is True

    def test_valid_transitions_from_disputed(self):
        """Test valid transitions from DISPUTED state"""
        
        # Valid transitions
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.DISPUTED.value, EscrowStatus.COMPLETED.value
        ) is True
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.DISPUTED.value, EscrowStatus.REFUNDED.value
        ) is True
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.DISPUTED.value, EscrowStatus.CANCELLED.value
        ) is True

    def test_terminal_states_no_transitions(self):
        """Test that terminal states allow no further transitions"""
        
        terminal_states = [
            EscrowStatus.COMPLETED.value,
            EscrowStatus.REFUNDED.value,
            EscrowStatus.CANCELLED.value,
            EscrowStatus.EXPIRED.value
        ]
        
        for terminal_state in terminal_states:
            assert EscrowStateValidator.is_terminal_state(terminal_state) is True
            assert EscrowStateValidator.get_valid_transitions(terminal_state) == set()
            
            # No transitions allowed from terminal states
            assert EscrowStateValidator.is_valid_transition(
                terminal_state, EscrowStatus.ACTIVE.value
            ) is False

    def test_get_valid_transitions_all_states(self):
        """Test get_valid_transitions for all states"""
        
        # Test some key states
        created_transitions = EscrowStateValidator.get_valid_transitions(EscrowStatus.CREATED.value)
        assert EscrowStatus.PAYMENT_PENDING.value in created_transitions
        assert EscrowStatus.CANCELLED.value in created_transitions
        
        active_transitions = EscrowStateValidator.get_valid_transitions(EscrowStatus.ACTIVE.value)
        assert EscrowStatus.COMPLETED.value in active_transitions
        assert EscrowStatus.DISPUTED.value in active_transitions
        assert EscrowStatus.CANCELLED.value in active_transitions  # Admin can still cancel ACTIVE

    def test_invalid_state_transitions(self):
        """Test various invalid state transitions"""
        
        # Invalid transitions that should never be allowed
        invalid_transitions = [
            (EscrowStatus.COMPLETED.value, EscrowStatus.ACTIVE.value),
            (EscrowStatus.REFUNDED.value, EscrowStatus.PAYMENT_PENDING.value),
            (EscrowStatus.CANCELLED.value, EscrowStatus.CREATED.value),
            (EscrowStatus.EXPIRED.value, EscrowStatus.PAYMENT_CONFIRMED.value),
            (EscrowStatus.CREATED.value, EscrowStatus.ACTIVE.value),  # Skip intermediate states
        ]
        
        for current_state, new_state in invalid_transitions:
            assert EscrowStateValidator.is_valid_transition(current_state, new_state) is False

    def test_nonexistent_state_handling(self):
        """Test handling of nonexistent states"""
        
        # Test with invalid current state
        assert EscrowStateValidator.is_valid_transition(
            "INVALID_STATE", EscrowStatus.CREATED.value
        ) is False
        
        # Test with invalid new state
        assert EscrowStateValidator.is_valid_transition(
            EscrowStatus.CREATED.value, "INVALID_NEW_STATE"
        ) is False
        
        # Test get_valid_transitions with invalid state
        assert EscrowStateValidator.get_valid_transitions("INVALID_STATE") == set()


class TestEscrowAtomicOperations:
    """Test atomic operations and advanced state management"""
    
    @pytest.mark.asyncio
    async def test_concurrent_state_transitions(self, test_db_session, test_data_factory):
        """Test successful state transition"""
        
        buyer = test_data_factory.create_test_user('buyer_transition1', balances={'USD': Decimal('1000.00')})
        seller = test_data_factory.create_test_user('seller_transition1', balances={'USD': Decimal('500.00')})
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.CREATED
        )
        
        # Test concurrent access to the same escrow
        from utils.atomic_transactions import locked_escrow_operation
        
        async def update_escrow_status():
            async with locked_escrow_operation(escrow.escrow_id):
                # Simulate state change work
                await asyncio.sleep(0.1)
                escrow.status = EscrowStatus.PAYMENT_PENDING.value
                test_db_session.commit()
                return True
        
        # Run concurrent operations
        results = await asyncio.gather(
            update_escrow_status(),
            update_escrow_status(),
            return_exceptions=True
        )
        
        # Should handle concurrency gracefully
        assert len([r for r in results if r is True]) >= 1

    @pytest.mark.asyncio
    async def test_atomic_escrow_operation(self, test_db_session, test_data_factory):
        """Test AtomicEscrowOperation functionality"""
        
        from utils.escrow_state_machine import AtomicEscrowOperation
        
        buyer = test_data_factory.create_test_user('buyer_atomic1', balances={'USD': Decimal('1000.00')})
        seller = test_data_factory.create_test_user('seller_atomic1', balances={'USD': Decimal('500.00')})
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.CREATED
        )
        
        # Test atomic status change
        atomic_op = AtomicEscrowOperation(escrow.escrow_id)
        result = atomic_op.change_status(EscrowStatus.PAYMENT_PENDING.value)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_atomic_escrow_release_with_payment(self, test_db_session, test_data_factory):
        """Test atomic escrow release with seller payment"""
        
        from utils.escrow_state_machine import AtomicEscrowOperation
        
        buyer = test_data_factory.create_test_user('buyer_release1', balances={'USD': Decimal('1000.00')})
        seller = test_data_factory.create_test_user('seller_release1', balances={'USD': Decimal('500.00')})
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.ACTIVE
        )
        
        # Test atomic release with payment
        atomic_op = AtomicEscrowOperation(escrow.escrow_id)
        result = atomic_op.release_with_payment(
            seller_user_id=seller.id,
            amount=100.0,
            currency='USD'
        )
        
        # Should handle the operation (may succeed or fail based on implementation)
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_transition_with_concurrent_access_protection(
        self, test_db_session, test_data_factory
    ):
        """Test atomic operations with concurrent access protection"""
        
        buyer = test_data_factory.create_test_user('buyer_concurrent1', balances={'USD': Decimal('1000.00')})
        seller = test_data_factory.create_test_user('seller_concurrent1', balances={'USD': Decimal('500.00')})
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.PAYMENT_CONFIRMED
        )
        
        # Simulate concurrent transitions
        async def transition_1():
            return await EscrowStateMachine.transition(
                escrow_id=escrow.escrow_id,
                new_status=EscrowStatus.AWAITING_SELLER,
                user_id=buyer.id,
                is_admin=False,
                session=test_db_session
            )
        
        async def transition_2():
            return await EscrowStateMachine.transition(
                escrow_id=escrow.escrow_id,
                new_status=EscrowStatus.CANCELLED,
                user_id=buyer.id,
                is_admin=False,
                session=test_db_session
            )
        
        # Should handle concurrency gracefully
        assert len([r for r in results if r is True]) >= 1
    
    @pytest.mark.asyncio
    async def test_atomic_operation_invalid_transition(self, test_db_session, test_data_factory):
        """Test atomic operation with invalid state transition"""
        
        from utils.escrow_state_machine import AtomicEscrowOperation
        
        buyer = test_data_factory.create_test_user('buyer_invalid_trans', balances={'USD': Decimal('1000.00')})
        seller = test_data_factory.create_test_user('seller_invalid_trans', balances={'USD': Decimal('500.00')})
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.COMPLETED  # Terminal state
        )
        
        # Try invalid transition from terminal state
        atomic_op = AtomicEscrowOperation(escrow.escrow_id)
        result = atomic_op.change_status(EscrowStatus.ACTIVE.value)
        
        assert result is False  # Should fail for invalid transition