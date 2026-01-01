"""
Comprehensive Test Suite for EscrowValidationService
Targets 100% line and branch coverage of business rules and admin overrides

Coverage Focus Areas:
- Cancellation validation rules
- Admin override logic
- Business rule enforcement
- State-specific validations
- Permission checks
- Error handling
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from services.escrow_validation_service import EscrowValidationService
from models import Escrow, EscrowStatus, User


class TestEscrowValidationService:
    """Test complete EscrowValidationService coverage"""

    def test_validate_cancellation_created_state_by_buyer(self, test_db_session, test_data_factory):
        """Test cancellation validation for CREATED state by buyer"""
        
        buyer = test_data_factory.create_test_user('buyer_created1', balances={'USD': Decimal('1000.00')})
        seller = test_data_factory.create_test_user('seller_created1', balances={'USD': Decimal('500.00')})
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.CREATED
        )
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=buyer.id,
            is_admin=False,
            session=test_db_session
        )
        
        assert result['allowed'] is True
        assert result['action_type'] == 'user_cancellation'

    def test_validate_cancellation_created_state_by_seller_denied(self, test_db_session, test_data_factory):
        """Test cancellation validation for CREATED state by seller (should be denied)"""
        
        buyer = test_data_factory.create_test_user('buyer_created2', balances={'USD': Decimal('1000.00')})
        seller = test_data_factory.create_test_user('seller_created2', balances={'USD': Decimal('500.00')})
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.CREATED
        )
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=seller.id,  # Seller trying to cancel
            is_admin=False,
            session=test_db_session
        )
        
        assert result['allowed'] is False
        assert result['action_type'] == 'unauthorized'
        assert 'sellers decline invitations' in result['reason'].lower()

    def test_validate_cancellation_active_state_by_user_denied(self, test_db_session, test_data_factory):
        """Test cancellation validation for ACTIVE state by regular user (should be denied)"""
        
        buyer = test_data_factory.create_test_user('buyer_active1', balances={'USD': Decimal('1000.00')})
        seller = test_data_factory.create_test_user('seller_active1', balances={'USD': Decimal('500.00')})
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.ACTIVE
        )
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=buyer.id,
            is_admin=False,
            session=test_db_session
        )
        
        assert result['allowed'] is False
        assert result['action_type'] == 'active_escrow_restriction'
        assert 'ACTIVE escrows cannot be cancelled' in result['reason']

    def test_validate_cancellation_active_state_by_admin_allowed(self, test_db_session, test_data_factory):
        """Test cancellation validation for ACTIVE state by admin (should be allowed)"""
        
        buyer = test_data_factory.create_test_user('buyer_active2', balances={'USD': Decimal('1000.00')})
        seller = test_data_factory.create_test_user('seller_active2', balances={'USD': Decimal('500.00')})
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.ACTIVE
        )
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=buyer.id,
            is_admin=True,  # Admin override
            session=test_db_session
        )
        
        assert result['allowed'] is True
        assert result['action_type'] == 'admin_cancellation'
        assert 'Admin override' in result['reason']

    def test_validate_cancellation_payment_pending_state(self, test_db_session, test_data_factory):
        """Test cancellation validation for PAYMENT_PENDING state"""
        
        buyer = test_data_factory.create_test_user('buyer_pending1', balances={'USD': Decimal('1000.00')})
        seller = test_data_factory.create_test_user('seller_pending1', balances={'USD': Decimal('500.00')})
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.PAYMENT_PENDING
        )
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=buyer.id,
            is_admin=False,
            session=test_db_session
        )
        
        assert result['allowed'] is True

    def test_validate_cancellation_payment_confirmed_state(self, test_db_session, test_data_factory):
        """Test cancellation validation for PAYMENT_CONFIRMED state"""
        
        buyer = test_data_factory.create_test_user('buyer_confirmed1', balances={'USD': Decimal('1000.00')})
        seller = test_data_factory.create_test_user('seller_confirmed1', balances={'USD': Decimal('500.00')})
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.PAYMENT_CONFIRMED
        )
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=buyer.id,
            is_admin=False,
            session=test_db_session
        )
        
        assert result['allowed'] is True

    def test_validate_cancellation_awaiting_seller_state(self, test_db_session, test_data_factory):
        """Test cancellation validation for AWAITING_SELLER state"""
        
        buyer = test_data_factory.create_test_user('buyer_awaiting1', balances={'USD': Decimal('1000.00')})
        seller = test_data_factory.create_test_user('seller_awaiting1', balances={'USD': Decimal('500.00')})
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.AWAITING_SELLER
        )
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=buyer.id,
            is_admin=False,
            session=test_db_session
        )
        
        assert result['allowed'] is True

    def test_validate_cancellation_pending_seller_state(self, test_db_session, test_data_factory):
        """Test cancellation validation for PENDING_SELLER state"""
        
        buyer = test_data_factory.create_test_user('buyer_pseller1', balances={'USD': Decimal('1000.00')})
        seller = test_data_factory.create_test_user('seller_pseller1', balances={'USD': Decimal('500.00')})
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.PENDING_SELLER
        )
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=buyer.id,
            is_admin=False,
            session=test_db_session
        )
        
        assert result['allowed'] is True

    def test_validate_cancellation_pending_deposit_state(self, test_db_session, test_data_factory):
        """Test cancellation validation for PENDING_DEPOSIT state"""
        
        buyer = test_data_factory.create_test_user('buyer_pdeposit1', balances={'USD': Decimal('1000.00')})
        seller = test_data_factory.create_test_user('seller_pdeposit1', balances={'USD': Decimal('500.00')})
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.PENDING_DEPOSIT
        )
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=buyer.id,
            is_admin=False,
            session=test_db_session
        )
        
        assert result['allowed'] is True

    def test_validate_cancellation_disputed_state_by_admin(self, test_db_session, test_data_factory):
        """Test cancellation validation for DISPUTED state by admin"""
        
        buyer = test_data_factory.create_test_user('buyer_disputed1', balances={'USD': Decimal('1000.00')})
        seller = test_data_factory.create_test_user('seller_disputed1', balances={'USD': Decimal('500.00')})
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.DISPUTED
        )
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=buyer.id,
            is_admin=True,
            session=test_db_session
        )
        
        assert result['allowed'] is True

    def test_validate_cancellation_terminal_states(self, test_db_session, test_data_factory):
        """Test cancellation validation for terminal states (should be denied)"""
        
        buyer = test_data_factory.create_test_user('buyer_terminal1', balances={'USD': Decimal('1000.00')})
        seller = test_data_factory.create_test_user('seller_terminal1', balances={'USD': Decimal('500.00')})
        
        # Test COMPLETED state
        escrow_completed = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.COMPLETED
        )
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow_completed,
            user_id=buyer.id,
            is_admin=False,
            session=test_db_session
        )
        
        assert result['allowed'] is False

    def test_validate_cancellation_nonexistent_escrow(self, test_db_session):
        """Test cancellation validation for nonexistent escrow"""
        
        result = EscrowValidationService.validate_cancellation(
            escrow=None,
            user_id=999999,
            is_admin=False,
            session=test_db_session
        )
        
        assert result['allowed'] is False
        assert result['action_type'] == 'invalid'
        assert 'not found' in result['reason']

    def test_validate_cancellation_refunded_state(self, test_db_session, test_data_factory):
        """Test cancellation validation for REFUNDED state (terminal)"""
        
        buyer = test_data_factory.create_test_user('buyer_refunded1', balances={'USD': Decimal('1000.00')})
        seller = test_data_factory.create_test_user('seller_refunded1', balances={'USD': Decimal('500.00')})
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.REFUNDED
        )
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=buyer.id,
            is_admin=False,
            session=test_db_session
        )
        
        assert result['allowed'] is False

    def test_validate_cancellation_cancelled_state(self, test_db_session, test_data_factory):
        """Test cancellation validation for already CANCELLED state"""
        
        buyer = test_data_factory.create_test_user('buyer_cancelled1', balances={'USD': Decimal('1000.00')})
        seller = test_data_factory.create_test_user('seller_cancelled1', balances={'USD': Decimal('500.00')})
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.CANCELLED
        )
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=buyer.id,
            is_admin=False,
            session=test_db_session
        )
        
        assert result['allowed'] is False

    def test_validate_cancellation_expired_state(self, test_db_session, test_data_factory):
        """Test cancellation validation for EXPIRED state"""
        
        buyer = test_data_factory.create_test_user('buyer_expired1', balances={'USD': Decimal('1000.00')})
        seller = test_data_factory.create_test_user('seller_expired1', balances={'USD': Decimal('500.00')})
        
        escrow = test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.EXPIRED
        )
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=buyer.id,
            is_admin=False,
            session=test_db_session
        )
        
        assert result['allowed'] is False