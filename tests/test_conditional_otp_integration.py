"""
Integration tests for ConditionalOTPService with UnifiedTransaction model

Verifies that the service correctly integrates with existing database constraints
and transaction model validation rules.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from models import (
    Base, 
    UnifiedTransaction, 
    UnifiedTransactionType, 
    UnifiedTransactionStatus,
    User
)
from services.conditional_otp_service import ConditionalOTPService


class TestDatabaseConstraintIntegration:
    """Test ConditionalOTPService integration with database constraints"""
    
    @pytest.fixture
    def db_session(self):
        """Create in-memory database for testing"""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Create test user
        user = User(
            user_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        session.add(user)
        session.commit()
        
        yield session
        session.close()
    
    def test_wallet_cashout_otp_constraint_compliance(self, db_session):
        """Test that wallet cashout with OTP complies with database constraints"""
        # Create wallet cashout transaction with OTP requirement
        transaction = UnifiedTransaction(
            transaction_id="UTX123456789012345",
            user_id=1,
            transaction_type=UnifiedTransactionType.WALLET_CASHOUT.value,
            status=UnifiedTransactionStatus.OTP_PENDING.value,
            amount=Decimal("100.00"),
            currency="USD",
            fee_amount=Decimal("5.00"),
            total_amount=Decimal("105.00"),
            fund_movement_type="debit",
            requires_otp=True,  # ConditionalOTPService would set this
            description="Wallet cashout requiring OTP"
        )
        
        # This should succeed - wallet cashout can require OTP
        db_session.add(transaction)
        db_session.commit()
        
        # Verify the transaction was created successfully
        saved_tx = db_session.query(UnifiedTransaction).filter_by(transaction_id="UTX123456789012345").first()
        assert saved_tx is not None
        assert saved_tx.requires_otp is True
        assert saved_tx.transaction_type == UnifiedTransactionType.WALLET_CASHOUT.value
    
    def test_exchange_no_otp_constraint_compliance(self, db_session):
        """Test that exchange transactions without OTP comply with database constraints"""
        # Create exchange transaction without OTP requirement
        transaction = UnifiedTransaction(
            transaction_id="UTX123456789012346",
            user_id=1,
            transaction_type=UnifiedTransactionType.EXCHANGE_SELL_CRYPTO.value,
            status=UnifiedTransactionStatus.PROCESSING.value,
            amount=Decimal("200.00"),
            currency="USD",
            fee_amount=Decimal("10.00"),
            total_amount=Decimal("210.00"),
            fund_movement_type="debit",
            requires_otp=False,  # ConditionalOTPService would set this
            description="Exchange sell crypto - no OTP required"
        )
        
        # This should succeed - exchange can have no OTP
        db_session.add(transaction)
        db_session.commit()
        
        # Verify the transaction was created successfully
        saved_tx = db_session.query(UnifiedTransaction).filter_by(transaction_id="UTX123456789012346").first()
        assert saved_tx is not None
        assert saved_tx.requires_otp is False
        assert saved_tx.transaction_type == UnifiedTransactionType.EXCHANGE_SELL_CRYPTO.value
    
    def test_escrow_no_otp_constraint_compliance(self, db_session):
        """Test that escrow transactions without OTP comply with database constraints"""
        # Create escrow transaction without OTP requirement
        transaction = UnifiedTransaction(
            transaction_id="UTX123456789012347",
            user_id=1,
            transaction_type=UnifiedTransactionType.ESCROW.value,
            status=UnifiedTransactionStatus.PROCESSING.value,
            amount=Decimal("300.00"),
            currency="USD",
            fee_amount=Decimal("0.00"),
            total_amount=Decimal("300.00"),
            fund_movement_type="release",
            requires_otp=False,  # ConditionalOTPService would set this
            description="Escrow release - no OTP required"
        )
        
        # This should succeed - escrow can have no OTP
        db_session.add(transaction)
        db_session.commit()
        
        # Verify the transaction was created successfully
        saved_tx = db_session.query(UnifiedTransaction).filter_by(transaction_id="UTX123456789012347").first()
        assert saved_tx is not None
        assert saved_tx.requires_otp is False
        assert saved_tx.transaction_type == UnifiedTransactionType.ESCROW.value
    
    def test_database_constraint_prevents_invalid_otp_combinations(self, db_session):
        """Test that database constraint prevents non-wallet transactions from requiring OTP"""
        # Try to create exchange transaction with OTP requirement - should fail
        transaction = UnifiedTransaction(
            transaction_id="UTX123456789012348",
            user_id=1,
            transaction_type=UnifiedTransactionType.EXCHANGE_SELL_CRYPTO.value,
            status=UnifiedTransactionStatus.OTP_PENDING.value,
            amount=Decimal("400.00"),
            currency="USD",
            fee_amount=Decimal("20.00"),
            total_amount=Decimal("420.00"),
            fund_movement_type="debit",
            requires_otp=True,  # This violates the constraint
            description="Invalid: Exchange with OTP requirement"
        )
        
        db_session.add(transaction)
        
        # This should fail due to database constraint
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_conditional_otp_service_aligns_with_constraints(self, db_session):
        """Test that ConditionalOTPService decisions align with database constraints"""
        test_cases = [
            {
                "transaction_type": UnifiedTransactionType.WALLET_CASHOUT,
                "expected_otp": True,
                "should_succeed": True
            },
            {
                "transaction_type": UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
                "expected_otp": False,
                "should_succeed": True
            },
            {
                "transaction_type": UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
                "expected_otp": False,
                "should_succeed": True
            },
            {
                "transaction_type": UnifiedTransactionType.ESCROW,
                "expected_otp": False,
                "should_succeed": True
            }
        ]
        
        for i, case in enumerate(test_cases):
            # Get OTP requirement from ConditionalOTPService
            service_otp_decision = ConditionalOTPService.requires_otp_enum(case["transaction_type"])
            
            # Verify service decision matches expected
            assert service_otp_decision == case["expected_otp"], \
                f"ConditionalOTPService gave wrong decision for {case['transaction_type'].value}"
            
            # Create transaction using service decision
            transaction = UnifiedTransaction(
                transaction_id=f"UTX12345678901234{i}",
                user_id=1,
                transaction_type=case["transaction_type"].value,
                status=ConditionalOTPService.get_otp_flow_status_enum(case["transaction_type"]).value,
                amount=Decimal("100.00"),
                currency="USD",
                fee_amount=Decimal("5.00"),
                total_amount=Decimal("105.00"),
                fund_movement_type="debit",
                requires_otp=service_otp_decision,  # Use service decision
                description=f"Test transaction for {case['transaction_type'].value}"
            )
            
            db_session.add(transaction)
            
            if case["should_succeed"]:
                # Should commit successfully
                db_session.commit()
                
                # Verify the transaction was saved correctly
                saved_tx = db_session.query(UnifiedTransaction).filter_by(
                    transaction_id=f"UTX12345678901234{i}"
                ).first()
                assert saved_tx is not None
                assert saved_tx.requires_otp == service_otp_decision
            else:
                # Should fail due to constraint violation
                with pytest.raises(IntegrityError):
                    db_session.commit()
            
            # Reset session for next test case
            db_session.rollback()


class TestStatusFlowIntegration:
    """Test ConditionalOTPService status flow integration"""
    
    def test_wallet_cashout_status_flow(self):
        """Test wallet cashout flows to OTP_PENDING status"""
        tx_type = UnifiedTransactionType.WALLET_CASHOUT
        
        # Service should require OTP
        assert ConditionalOTPService.requires_otp_enum(tx_type) is True
        
        # Service should return OTP_PENDING status
        next_status = ConditionalOTPService.get_otp_flow_status_enum(tx_type)
        assert next_status == UnifiedTransactionStatus.OTP_PENDING
        
        # String version should also work
        next_status_str = ConditionalOTPService.get_otp_flow_status(tx_type.value)
        assert next_status_str == "otp_pending"
    
    def test_exchange_status_flow(self):
        """Test exchange transactions flow directly to PROCESSING (skip OTP)"""
        exchange_types = [
            UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
            UnifiedTransactionType.EXCHANGE_BUY_CRYPTO
        ]
        
        for tx_type in exchange_types:
            # Service should not require OTP
            assert ConditionalOTPService.requires_otp_enum(tx_type) is False
            
            # Service should return PROCESSING status (skip OTP)
            next_status = ConditionalOTPService.get_otp_flow_status_enum(tx_type)
            assert next_status == UnifiedTransactionStatus.PROCESSING
            
            # String version should also work
            next_status_str = ConditionalOTPService.get_otp_flow_status(tx_type.value)
            assert next_status_str == "processing"
    
    def test_escrow_status_flow(self):
        """Test escrow transactions flow directly to PROCESSING (skip OTP)"""
        tx_type = UnifiedTransactionType.ESCROW
        
        # Service should not require OTP
        assert ConditionalOTPService.requires_otp_enum(tx_type) is False
        
        # Service should return PROCESSING status (skip OTP)
        next_status = ConditionalOTPService.get_otp_flow_status_enum(tx_type)
        assert next_status == UnifiedTransactionStatus.PROCESSING
        
        # String version should also work
        next_status_str = ConditionalOTPService.get_otp_flow_status(tx_type.value)
        assert next_status_str == "processing"


class TestModelConstraintValidation:
    """Test that ConditionalOTPService respects all model constraints"""
    
    def test_otp_verified_logic_constraint(self):
        """Test that OTP verified logic aligns with ConditionalOTPService"""
        # From constraint: otp_verified can only be true if requires_otp is true
        
        # Wallet cashout: can have otp_verified=True because requires_otp=True
        tx_type = UnifiedTransactionType.WALLET_CASHOUT
        requires_otp = ConditionalOTPService.requires_otp_enum(tx_type)
        assert requires_otp is True  # So otp_verified can be True
        
        # Exchange/Escrow: cannot have otp_verified=True because requires_otp=False
        non_otp_types = [
            UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
            UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
            UnifiedTransactionType.ESCROW
        ]
        
        for tx_type in non_otp_types:
            requires_otp = ConditionalOTPService.requires_otp_enum(tx_type)
            assert requires_otp is False  # So otp_verified must be False
    
    def test_transaction_type_validation(self):
        """Test that service handles all valid transaction types"""
        valid_types = [
            UnifiedTransactionType.WALLET_CASHOUT,
            UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
            UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
            UnifiedTransactionType.ESCROW
        ]
        
        for tx_type in valid_types:
            # Service should handle all valid types without error
            try:
                requires_otp = ConditionalOTPService.requires_otp_enum(tx_type)
                next_status = ConditionalOTPService.get_otp_flow_status_enum(tx_type)
                reason = ConditionalOTPService.get_requirement_reason(tx_type.value)
                
                # All should return valid values
                assert isinstance(requires_otp, bool)
                assert isinstance(next_status, UnifiedTransactionStatus)
                assert reason is not None
                
            except Exception as e:
                pytest.fail(f"ConditionalOTPService failed to handle valid type {tx_type.value}: {e}")
    
    def test_service_output_types(self):
        """Test that service outputs match expected types for model integration"""
        tx_type = UnifiedTransactionType.WALLET_CASHOUT
        
        # Boolean output for requires_otp field
        requires_otp = ConditionalOTPService.requires_otp_enum(tx_type)
        assert isinstance(requires_otp, bool)
        
        # String output for status field
        status_str = ConditionalOTPService.get_otp_flow_status(tx_type.value)
        assert isinstance(status_str, str)
        assert status_str in ["otp_pending", "processing"]
        
        # Enum output for programmatic use
        status_enum = ConditionalOTPService.get_otp_flow_status_enum(tx_type)
        assert isinstance(status_enum, UnifiedTransactionStatus)
        
        # Summary output for logging/debugging
        summary = ConditionalOTPService.get_otp_decision_summary(tx_type.value)
        assert isinstance(summary, dict)
        assert "requires_otp" in summary
        assert "next_status" in summary
        assert "transaction_type" in summary


class TestBackwardCompatibilityIntegration:
    """Test backward compatibility with existing transaction handling"""
    
    def test_string_transaction_type_handling(self):
        """Test that service handles string transaction types (backward compatibility)"""
        string_types = [
            "wallet_cashout",
            "exchange_sell_crypto", 
            "exchange_buy_crypto",
            "escrow"
        ]
        
        for tx_type_str in string_types:
            # Service should handle string inputs
            requires_otp = ConditionalOTPService.requires_otp(tx_type_str)
            next_status = ConditionalOTPService.get_otp_flow_status(tx_type_str)
            
            assert isinstance(requires_otp, bool)
            assert isinstance(next_status, str)
    
    def test_convenience_function_integration(self):
        """Test convenience functions work with existing code patterns"""
        from services.conditional_otp_service import (
            requires_otp_for_transaction,
            get_next_status_after_authorization
        )
        
        # Test existing patterns
        assert requires_otp_for_transaction("wallet_cashout") is True
        assert requires_otp_for_transaction("exchange_sell_crypto") is False
        
        assert get_next_status_after_authorization("wallet_cashout") == "otp_pending"
        assert get_next_status_after_authorization("escrow") == "processing"
    
    def test_error_handling_for_invalid_types(self):
        """Test service gracefully handles invalid transaction types"""
        invalid_types = ["invalid", "", "random_string", None]
        
        for invalid_type in invalid_types:
            try:
                # Should not crash, should default to False (no OTP)
                if invalid_type is not None:
                    requires_otp = ConditionalOTPService.requires_otp(invalid_type)
                    assert requires_otp is False  # Safe default
                    
                    next_status = ConditionalOTPService.get_otp_flow_status(invalid_type)
                    assert next_status == "processing"  # Safe default
                
            except Exception as e:
                pytest.fail(f"Service should handle invalid type gracefully: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])