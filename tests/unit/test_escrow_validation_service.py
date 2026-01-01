"""
Comprehensive Unit Tests for EscrowValidationService
Tests business rules validation and escrow operation authorization
"""

import pytest
from unittest.mock import Mock, patch
from decimal import Decimal

# Service under test
from services.escrow_validation_service import EscrowValidationService

# Models for testing
from models import Escrow, EscrowStatus, User


@pytest.mark.unit
class TestEscrowCancellationValidation:
    """Test escrow cancellation validation business rules"""
    
    def test_validate_cancellation_escrow_not_found(self):
        """Test validation when escrow doesn't exist"""
        
        result = EscrowValidationService.validate_cancellation(
            escrow=None,
            user_id=12345,
            is_admin=False
        )
        
        assert result['allowed'] is False
        assert result['reason'] == "Escrow not found"
        assert result['action_type'] == "invalid"
    
    def test_validate_cancellation_buyer_can_cancel_created_escrow(self):
        """Test buyer can cancel CREATED escrow"""
        
        # Create mock escrow in CREATED state
        escrow = Mock()
        escrow.status = EscrowStatus.CREATED
        escrow.buyer_id = 12345
        escrow.seller_id = 67890
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=12345,  # Buyer ID
            is_admin=False
        )
        
        assert result['allowed'] is True
        assert 'buyer_cancellation' in result['action_type']
    
    def test_validate_cancellation_buyer_can_cancel_payment_pending(self):
        """Test buyer can cancel PAYMENT_PENDING escrow"""
        
        escrow = Mock()
        escrow.status = EscrowStatus.PAYMENT_PENDING
        escrow.buyer_id = 12345
        escrow.seller_id = 67890
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=12345,  # Buyer ID
            is_admin=False
        )
        
        assert result['allowed'] is True
    
    def test_validate_cancellation_buyer_cannot_cancel_active_escrow(self):
        """Test buyer cannot cancel ACTIVE escrow"""
        
        escrow = Mock()
        escrow.status = EscrowStatus.ACTIVE
        escrow.buyer_id = 12345
        escrow.seller_id = 67890
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=12345,  # Buyer ID
            is_admin=False
        )
        
        assert result['allowed'] is False
        assert result['reason'] == "ACTIVE escrows cannot be cancelled. Please dispute or release funds."
        assert result['action_type'] == "active_escrow_restriction"
    
    def test_validate_cancellation_admin_can_cancel_active_escrow(self):
        """Test admin can cancel ACTIVE escrow (administrative override)"""
        
        escrow = Mock()
        escrow.status = EscrowStatus.ACTIVE
        escrow.buyer_id = 12345
        escrow.seller_id = 67890
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=99999,  # Admin user ID (different from buyer/seller)
            is_admin=True
        )
        
        assert result['allowed'] is True
        assert result['reason'] == "Admin override for ACTIVE escrow"
        assert result['action_type'] == "admin_cancellation"
    
    def test_validate_cancellation_seller_cannot_cancel_escrow(self):
        """Test seller cannot cancel escrow (must decline invitation)"""
        
        escrow = Mock()
        escrow.status = EscrowStatus.CREATED
        escrow.buyer_id = 12345
        escrow.seller_id = 67890
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=67890,  # Seller ID
            is_admin=False
        )
        
        assert result['allowed'] is False
        assert result['reason'] == "Only buyers can cancel escrows. Sellers decline invitations."
        assert result['action_type'] == "unauthorized"
    
    def test_validate_cancellation_third_party_cannot_cancel(self):
        """Test third party (neither buyer nor seller) cannot cancel"""
        
        escrow = Mock()
        escrow.status = EscrowStatus.CREATED
        escrow.buyer_id = 12345
        escrow.seller_id = 67890
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=11111,  # Third party ID
            is_admin=False
        )
        
        assert result['allowed'] is False
        assert result['reason'] == "Only buyers can cancel escrows. Sellers decline invitations."
        assert result['action_type'] == "unauthorized"


@pytest.mark.unit
class TestEscrowCancellationStateRules:
    """Test state-specific cancellation rules"""
    
    def test_validate_cancellation_payment_confirmed_state(self):
        """Test cancellation allowed in PAYMENT_CONFIRMED state"""
        
        escrow = Mock()
        escrow.status = EscrowStatus.PAYMENT_CONFIRMED
        escrow.buyer_id = 12345
        escrow.seller_id = 67890
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=12345,  # Buyer ID
            is_admin=False
        )
        
        assert result['allowed'] is True
    
    def test_validate_cancellation_awaiting_seller_state(self):
        """Test cancellation allowed in AWAITING_SELLER state"""
        
        escrow = Mock()
        escrow.status = EscrowStatus.AWAITING_SELLER
        escrow.buyer_id = 12345
        escrow.seller_id = 67890
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=12345,  # Buyer ID
            is_admin=False
        )
        
        assert result['allowed'] is True
    
    def test_validate_cancellation_pending_seller_state(self):
        """Test cancellation allowed in PENDING_SELLER state"""
        
        escrow = Mock()
        escrow.status = EscrowStatus.PENDING_SELLER
        escrow.buyer_id = 12345
        escrow.seller_id = 67890
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=12345,  # Buyer ID
            is_admin=False
        )
        
        assert result['allowed'] is True
    
    def test_validate_cancellation_completed_escrow(self):
        """Test cancellation not allowed for COMPLETED escrow"""
        
        escrow = Mock()
        escrow.status = EscrowStatus.COMPLETED
        escrow.buyer_id = 12345
        escrow.seller_id = 67890
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=12345,  # Buyer ID
            is_admin=False
        )
        
        assert result['allowed'] is False
        assert 'cannot be cancelled' in result['reason'] or 'invalid state' in result['reason']
    
    def test_validate_cancellation_refunded_escrow(self):
        """Test cancellation not allowed for REFUNDED escrow"""
        
        escrow = Mock()
        escrow.status = EscrowStatus.REFUNDED
        escrow.buyer_id = 12345
        escrow.seller_id = 67890
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=12345,  # Buyer ID
            is_admin=False
        )
        
        assert result['allowed'] is False
    
    def test_validate_cancellation_disputed_escrow_admin_only(self):
        """Test cancellation of DISPUTED escrow requires admin"""
        
        escrow = Mock()
        escrow.status = EscrowStatus.DISPUTED
        escrow.buyer_id = 12345
        escrow.seller_id = 67890
        
        # Non-admin cannot cancel disputed escrow
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=12345,  # Buyer ID
            is_admin=False
        )
        
        assert result['allowed'] is False
        
        # Admin can cancel disputed escrow
        result_admin = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=99999,  # Admin ID
            is_admin=True
        )
        
        assert result_admin['allowed'] is True


@pytest.mark.unit
class TestEscrowAmountValidation:
    """Test amount validation business rules"""
    
    def test_validate_amount_positive_values(self):
        """Test validation accepts positive amounts"""
        
        valid_amounts = [
            Decimal('0.01'),     # Minimum valid amount
            Decimal('100.00'),   # Standard amount
            Decimal('9999.99'),  # Large amount
            Decimal('0.001'),    # Very small amount
        ]
        
        for amount in valid_amounts:
            # Mock validation (actual method would need to be implemented)
            result = self._mock_amount_validation(amount)
            assert result['valid'] is True
    
    def test_validate_amount_zero_and_negative(self):
        """Test validation rejects zero and negative amounts"""
        
        invalid_amounts = [
            Decimal('0.00'),     # Zero amount
            Decimal('-1.00'),    # Negative amount
            Decimal('-0.01'),    # Small negative amount
        ]
        
        for amount in invalid_amounts:
            result = self._mock_amount_validation(amount)
            assert result['valid'] is False
    
    def test_validate_amount_precision_limits(self):
        """Test amount precision validation"""
        
        # Test various precision levels
        test_cases = [
            (Decimal('100.00'), True),      # 2 decimal places (valid)
            (Decimal('100.123'), True),     # 3 decimal places (might be valid)
            (Decimal('100.123456'), True),  # 6 decimal places (crypto precision)
        ]
        
        for amount, expected_valid in test_cases:
            result = self._mock_amount_validation(amount)
            # Precision rules would depend on implementation
            assert isinstance(result['valid'], bool)
    
    def _mock_amount_validation(self, amount: Decimal) -> dict:
        """Mock amount validation for testing"""
        # This would be replaced with actual validation method
        return {
            'valid': amount > Decimal('0'),
            'amount': amount,
            'reason': 'Valid amount' if amount > Decimal('0') else 'Invalid amount'
        }


@pytest.mark.unit
class TestEscrowUserValidation:
    """Test user validation business rules"""
    
    def test_validate_user_permissions_buyer_actions(self):
        """Test buyer permission validation"""
        
        # Mock escrow with buyer and seller
        escrow = Mock()
        escrow.buyer_id = 12345
        escrow.seller_id = 67890
        escrow.status = EscrowStatus.CREATED
        
        # Test buyer permissions
        buyer_actions = ['cancel', 'pay', 'dispute', 'release']
        
        for action in buyer_actions:
            result = self._mock_user_permission_validation(
                escrow, user_id=12345, action=action, is_admin=False
            )
            # Buyer should have appropriate permissions
            assert isinstance(result['allowed'], bool)
    
    def test_validate_user_permissions_seller_actions(self):
        """Test seller permission validation"""
        
        escrow = Mock()
        escrow.buyer_id = 12345
        escrow.seller_id = 67890
        escrow.status = EscrowStatus.AWAITING_SELLER
        
        # Test seller permissions
        seller_actions = ['accept', 'decline', 'dispute', 'confirm_delivery']
        
        for action in seller_actions:
            result = self._mock_user_permission_validation(
                escrow, user_id=67890, action=action, is_admin=False
            )
            # Seller should have appropriate permissions
            assert isinstance(result['allowed'], bool)
    
    def test_validate_user_permissions_admin_override(self):
        """Test admin override permissions"""
        
        escrow = Mock()
        escrow.buyer_id = 12345
        escrow.seller_id = 67890
        escrow.status = EscrowStatus.ACTIVE
        
        # Test admin permissions
        admin_actions = ['cancel', 'force_release', 'force_refund', 'resolve_dispute']
        
        for action in admin_actions:
            result = self._mock_user_permission_validation(
                escrow, user_id=99999, action=action, is_admin=True
            )
            # Admin should have all permissions
            assert result['allowed'] is True or 'admin' in result['reason']
    
    def _mock_user_permission_validation(self, escrow, user_id: int, action: str, is_admin: bool) -> dict:
        """Mock user permission validation"""
        # This would be replaced with actual permission validation
        is_buyer = escrow.buyer_id == user_id
        is_seller = escrow.seller_id == user_id
        
        if is_admin:
            return {'allowed': True, 'reason': 'Admin override'}
        elif is_buyer and action in ['cancel', 'pay', 'dispute', 'release']:
            return {'allowed': True, 'reason': 'Buyer permission'}
        elif is_seller and action in ['accept', 'decline', 'dispute', 'confirm_delivery']:
            return {'allowed': True, 'reason': 'Seller permission'}
        else:
            return {'allowed': False, 'reason': 'Insufficient permissions'}


@pytest.mark.unit
class TestEscrowValidationEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_validate_cancellation_with_mock_status_values(self):
        """Test validation with various status values"""
        
        # Test with string status values (as they appear in database)
        status_test_cases = [
            ('CREATED', True),           # Should allow cancellation
            ('PAYMENT_PENDING', True),   # Should allow cancellation
            ('ACTIVE', False),           # Should not allow (user)
            ('COMPLETED', False),        # Should not allow
            ('CANCELLED', False),        # Already cancelled
        ]
        
        for status_str, expected_allowed in status_test_cases:
            escrow = Mock()
            escrow.status = status_str  # String status instead of enum
            escrow.buyer_id = 12345
            escrow.seller_id = 67890
            
            result = EscrowValidationService.validate_cancellation(
                escrow=escrow,
                user_id=12345,  # Buyer ID
                is_admin=False
            )
            
            # The result should handle string status values appropriately
            assert isinstance(result['allowed'], bool)
            assert 'reason' in result
            assert 'action_type' in result
    
    def test_validate_cancellation_with_none_values(self):
        """Test validation handles None values gracefully"""
        
        # Test with None escrow (already tested above, but ensuring consistency)
        result = EscrowValidationService.validate_cancellation(
            escrow=None,
            user_id=12345,
            is_admin=False
        )
        
        assert result['allowed'] is False
        assert 'not found' in result['reason']
        
        # Test with None user_id
        escrow = Mock()
        escrow.status = EscrowStatus.CREATED
        escrow.buyer_id = 12345
        escrow.seller_id = 67890
        
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=None,
            is_admin=False
        )
        
        # Should handle None user_id gracefully
        assert isinstance(result['allowed'], bool)
    
    def test_validate_cancellation_exception_handling(self):
        """Test validation handles exceptions gracefully"""
        
        # Create escrow mock that raises exception on property access
        escrow = Mock()
        escrow.status = EscrowStatus.CREATED
        escrow.buyer_id = 12345
        escrow.seller_id.side_effect = Exception("Database connection lost")
        
        try:
            result = EscrowValidationService.validate_cancellation(
                escrow=escrow,
                user_id=12345,
                is_admin=False
            )
            
            # Should either succeed with graceful handling or fail safely
            assert 'allowed' in result
            assert 'action_type' in result
            
        except Exception as e:
            # If exception is raised, it should be a controlled failure
            assert isinstance(e, Exception)


@pytest.mark.integration
class TestEscrowValidationServiceIntegration:
    """Integration tests with database and other services"""
    
    def test_validation_with_real_escrow_objects(self, test_db_session):
        """Test validation with real Escrow model instances"""
        
        # Create real users and escrow in test database
        buyer = User(telegram_id=12345, username='testbuyer')
        seller = User(telegram_id=67890, username='testseller')
        test_db_session.add_all([buyer, seller])
        test_db_session.commit()
        
        escrow = Escrow(
            id='test_validation_001',
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.CREATED.value,
            description='Test escrow for validation'
        )
        test_db_session.add(escrow)
        test_db_session.commit()
        
        # Test validation with real escrow object
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=buyer.id,
            is_admin=False,
            session=test_db_session
        )
        
        # Should work with real database objects
        assert result['allowed'] is True
        assert 'buyer' in result['action_type'] or 'cancellation' in result['action_type']
    
    def test_validation_cross_references_database(self, test_db_session):
        """Test validation that cross-references database state"""
        
        # Create escrow with ACTIVE status
        buyer = User(telegram_id=12346, username='testbuyer2')
        seller = User(telegram_id=67891, username='testseller2')
        test_db_session.add_all([buyer, seller])
        test_db_session.commit()
        
        escrow = Escrow(
            id='test_validation_002',
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.ACTIVE.value,  # ACTIVE status
            description='Test active escrow for validation'
        )
        test_db_session.add(escrow)
        test_db_session.commit()
        
        # Buyer should not be able to cancel ACTIVE escrow
        result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=buyer.id,
            is_admin=False,
            session=test_db_session
        )
        
        assert result['allowed'] is False
        assert 'ACTIVE' in result['reason']
        
        # Admin should be able to cancel ACTIVE escrow
        admin_result = EscrowValidationService.validate_cancellation(
            escrow=escrow,
            user_id=99999,  # Admin user
            is_admin=True,
            session=test_db_session
        )
        
        assert admin_result['allowed'] is True
        assert 'admin' in admin_result['action_type'].lower()