"""
Comprehensive test coverage for ConditionalOTPService

Tests the exact document specification:
- OTP Required: ONLY for wallet balance cashouts
- No OTP Required: Exchange deposits, escrow releases, escrow refunds
"""

import pytest
from unittest.mock import patch
import logging

from services.conditional_otp_service import (
    ConditionalOTPService,
    OTPRequirementReason,
    requires_otp_for_transaction,
    get_next_status_after_authorization
)
from models import UnifiedTransactionType, UnifiedTransactionStatus


class TestConditionalOTPService:
    """Test suite for ConditionalOTPService following document specification"""
    
    def test_wallet_cashout_requires_otp(self):
        """Test that wallet cashouts require OTP as per document specification"""
        # Test with string input
        assert ConditionalOTPService.requires_otp("wallet_cashout") is True
        
        # Test with enum input
        assert ConditionalOTPService.requires_otp_enum(UnifiedTransactionType.WALLET_CASHOUT) is True
        
        # Test convenience function
        assert requires_otp_for_transaction("wallet_cashout") is True
    
    def test_exchange_sell_crypto_no_otp(self):
        """Test that exchange sell crypto transactions don't require OTP"""
        # Test with string input
        assert ConditionalOTPService.requires_otp("exchange_sell_crypto") is False
        
        # Test with enum input
        assert ConditionalOTPService.requires_otp_enum(UnifiedTransactionType.EXCHANGE_SELL_CRYPTO) is False
        
        # Test convenience function
        assert requires_otp_for_transaction("exchange_sell_crypto") is False
    
    def test_exchange_buy_crypto_no_otp(self):
        """Test that exchange buy crypto transactions don't require OTP"""
        # Test with string input
        assert ConditionalOTPService.requires_otp("exchange_buy_crypto") is False
        
        # Test with enum input
        assert ConditionalOTPService.requires_otp_enum(UnifiedTransactionType.EXCHANGE_BUY_CRYPTO) is False
        
        # Test convenience function
        assert requires_otp_for_transaction("exchange_buy_crypto") is False
    
    def test_escrow_no_otp(self):
        """Test that escrow transactions (releases and refunds) don't require OTP"""
        # Test with string input
        assert ConditionalOTPService.requires_otp("escrow") is False
        
        # Test with enum input
        assert ConditionalOTPService.requires_otp_enum(UnifiedTransactionType.ESCROW) is False
        
        # Test convenience function
        assert requires_otp_for_transaction("escrow") is False
    
    def test_invalid_transaction_type_defaults_to_no_otp(self):
        """Test that unknown/invalid transaction types default to no OTP for safety"""
        # Test with invalid string
        assert ConditionalOTPService.requires_otp("invalid_type") is False
        assert ConditionalOTPService.requires_otp("") is False
        assert ConditionalOTPService.requires_otp("random_string") is False
        
        # Test convenience function with invalid input
        assert requires_otp_for_transaction("invalid_type") is False


class TestOTPFlowStatus:
    """Test OTP flow status determination based on transaction type"""
    
    def test_wallet_cashout_status_flow(self):
        """Test that wallet cashouts flow to OTP_PENDING status"""
        # Test string version
        status = ConditionalOTPService.get_otp_flow_status("wallet_cashout")
        assert status == "otp_pending"
        
        # Test enum version
        status_enum = ConditionalOTPService.get_otp_flow_status_enum(UnifiedTransactionType.WALLET_CASHOUT)
        assert status_enum == UnifiedTransactionStatus.OTP_PENDING
        
        # Test convenience function
        next_status = get_next_status_after_authorization("wallet_cashout")
        assert next_status == "otp_pending"
    
    def test_exchange_status_flow(self):
        """Test that exchange transactions flow directly to PROCESSING (skip OTP)"""
        # Test exchange sell crypto
        status = ConditionalOTPService.get_otp_flow_status("exchange_sell_crypto")
        assert status == "processing"
        
        status_enum = ConditionalOTPService.get_otp_flow_status_enum(UnifiedTransactionType.EXCHANGE_SELL_CRYPTO)
        assert status_enum == UnifiedTransactionStatus.PROCESSING
        
        # Test exchange buy crypto
        status = ConditionalOTPService.get_otp_flow_status("exchange_buy_crypto")
        assert status == "processing"
        
        status_enum = ConditionalOTPService.get_otp_flow_status_enum(UnifiedTransactionType.EXCHANGE_BUY_CRYPTO)
        assert status_enum == UnifiedTransactionStatus.PROCESSING
        
        # Test convenience functions
        assert get_next_status_after_authorization("exchange_sell_crypto") == "processing"
        assert get_next_status_after_authorization("exchange_buy_crypto") == "processing"
    
    def test_escrow_status_flow(self):
        """Test that escrow transactions flow directly to PROCESSING (skip OTP)"""
        status = ConditionalOTPService.get_otp_flow_status("escrow")
        assert status == "processing"
        
        status_enum = ConditionalOTPService.get_otp_flow_status_enum(UnifiedTransactionType.ESCROW)
        assert status_enum == UnifiedTransactionStatus.PROCESSING
        
        # Test convenience function
        assert get_next_status_after_authorization("escrow") == "processing"
    
    def test_invalid_type_status_flow(self):
        """Test that invalid types default to PROCESSING (no OTP, safe default)"""
        status = ConditionalOTPService.get_otp_flow_status("invalid_type")
        assert status == "processing"
        
        assert get_next_status_after_authorization("invalid_type") == "processing"


class TestOTPRequirementReasons:
    """Test OTP requirement reason classification"""
    
    def test_wallet_cashout_reason(self):
        """Test wallet cashout reason classification"""
        reason = ConditionalOTPService.get_requirement_reason("wallet_cashout")
        assert reason == OTPRequirementReason.WALLET_CASHOUT_REQUIRED
    
    def test_exchange_reasons(self):
        """Test exchange transaction reason classifications"""
        # Exchange sell crypto
        reason = ConditionalOTPService.get_requirement_reason("exchange_sell_crypto")
        assert reason == OTPRequirementReason.EXCHANGE_NO_OTP
        
        # Exchange buy crypto
        reason = ConditionalOTPService.get_requirement_reason("exchange_buy_crypto")
        assert reason == OTPRequirementReason.EXCHANGE_NO_OTP
    
    def test_escrow_reason(self):
        """Test escrow transaction reason classification"""
        reason = ConditionalOTPService.get_requirement_reason("escrow")
        assert reason == OTPRequirementReason.ESCROW_NO_OTP
    
    def test_unknown_type_reason(self):
        """Test unknown transaction type reason classification"""
        reason = ConditionalOTPService.get_requirement_reason("invalid_type")
        assert reason == OTPRequirementReason.UNKNOWN_TYPE
        
        reason = ConditionalOTPService.get_requirement_reason("")
        assert reason == OTPRequirementReason.UNKNOWN_TYPE


class TestOTPDecisionSummary:
    """Test comprehensive OTP decision summary functionality"""
    
    def test_wallet_cashout_summary(self):
        """Test wallet cashout decision summary"""
        summary = ConditionalOTPService.get_otp_decision_summary("wallet_cashout")
        
        expected = {
            "transaction_type": "wallet_cashout",
            "requires_otp": True,
            "next_status": "otp_pending",
            "reason": "wallet_cashout_required",
            "summary": "OTP Required - wallet_cashout_required"
        }
        
        assert summary == expected
    
    def test_exchange_sell_summary(self):
        """Test exchange sell crypto decision summary"""
        summary = ConditionalOTPService.get_otp_decision_summary("exchange_sell_crypto")
        
        expected = {
            "transaction_type": "exchange_sell_crypto",
            "requires_otp": False,
            "next_status": "processing",
            "reason": "exchange_no_otp",
            "summary": "No OTP Required - exchange_no_otp"
        }
        
        assert summary == expected
    
    def test_exchange_buy_summary(self):
        """Test exchange buy crypto decision summary"""
        summary = ConditionalOTPService.get_otp_decision_summary("exchange_buy_crypto")
        
        expected = {
            "transaction_type": "exchange_buy_crypto",
            "requires_otp": False,
            "next_status": "processing",
            "reason": "exchange_no_otp",
            "summary": "No OTP Required - exchange_no_otp"
        }
        
        assert summary == expected
    
    def test_escrow_summary(self):
        """Test escrow decision summary"""
        summary = ConditionalOTPService.get_otp_decision_summary("escrow")
        
        expected = {
            "transaction_type": "escrow",
            "requires_otp": False,
            "next_status": "processing",
            "reason": "escrow_no_otp",
            "summary": "No OTP Required - escrow_no_otp"
        }
        
        assert summary == expected
    
    def test_invalid_type_summary(self):
        """Test invalid transaction type decision summary"""
        summary = ConditionalOTPService.get_otp_decision_summary("invalid_type")
        
        expected = {
            "transaction_type": "invalid_type",
            "requires_otp": False,
            "next_status": "processing",
            "reason": "unknown_type",
            "summary": "No OTP Required - unknown_type"
        }
        
        assert summary == expected


class TestLoggingAndDebug:
    """Test logging and debugging functionality"""
    
    @patch('services.conditional_otp_service.logger')
    def test_logging_for_wallet_cashout(self, mock_logger):
        """Test that appropriate logs are generated for wallet cashout"""
        ConditionalOTPService.requires_otp("wallet_cashout")
        mock_logger.debug.assert_called_with("🔐 OTP Required: wallet_cashout - wallet balance cashout")
    
    @patch('services.conditional_otp_service.logger')
    def test_logging_for_exchange(self, mock_logger):
        """Test that appropriate logs are generated for exchange transactions"""
        ConditionalOTPService.requires_otp("exchange_sell_crypto")
        mock_logger.debug.assert_called_with("✅ No OTP Required: exchange_sell_crypto - exchange/escrow transaction")
    
    @patch('services.conditional_otp_service.logger')
    def test_logging_for_escrow(self, mock_logger):
        """Test that appropriate logs are generated for escrow transactions"""
        ConditionalOTPService.requires_otp("escrow")
        mock_logger.debug.assert_called_with("✅ No OTP Required: escrow - exchange/escrow transaction")
    
    @patch('services.conditional_otp_service.logger')
    def test_warning_for_unknown_type(self, mock_logger):
        """Test that warnings are logged for unknown transaction types"""
        ConditionalOTPService.requires_otp("invalid_type")
        mock_logger.warning.assert_called_with("⚠️ Unknown transaction type: invalid_type, defaulting to no OTP")


class TestDocumentSpecificationCompliance:
    """Test compliance with exact document specification requirements"""
    
    def test_document_requirement_wallet_cashout_only(self):
        """Test that ONLY wallet cashouts require OTP as per document"""
        # Document: "OTP Required: ONLY for wallet balance cashouts"
        all_transaction_types = [
            UnifiedTransactionType.WALLET_CASHOUT,
            UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
            UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,
            UnifiedTransactionType.ESCROW
        ]
        
        otp_required_types = [
            tx_type for tx_type in all_transaction_types 
            if ConditionalOTPService.requires_otp_enum(tx_type)
        ]
        
        # Should be exactly one type requiring OTP
        assert len(otp_required_types) == 1
        assert otp_required_types[0] == UnifiedTransactionType.WALLET_CASHOUT
    
    def test_document_requirement_no_otp_cases(self):
        """Test all cases that should NOT require OTP per document"""
        # Document: "No OTP Required: Exchange deposits, escrow releases, escrow refunds"
        no_otp_types = [
            UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,   # Exchange deposits → buyer wallet
            UnifiedTransactionType.EXCHANGE_BUY_CRYPTO,    # Exchange deposits → buyer wallet
            UnifiedTransactionType.ESCROW                  # Escrow releases and refunds
        ]
        
        for tx_type in no_otp_types:
            assert ConditionalOTPService.requires_otp_enum(tx_type) is False, \
                f"Transaction type {tx_type.value} should not require OTP per document specification"
    
    def test_simple_binary_logic(self):
        """Test that the logic is simple binary as required by document"""
        # Document: "Simple binary decision: wallet cashout = OTP, everything else = no OTP"
        
        # Wallet cashout = OTP
        assert ConditionalOTPService.requires_otp("wallet_cashout") is True
        
        # Everything else = no OTP
        other_types = ["exchange_sell_crypto", "exchange_buy_crypto", "escrow"]
        for tx_type in other_types:
            assert ConditionalOTPService.requires_otp(tx_type) is False
    
    def test_no_risk_based_controls(self):
        """Test that there are no risk-based controls as per document simplification"""
        # Document: "No risk-based controls needed"
        # The service should not have any risk assessment logic
        
        # Same transaction type should always return same result regardless of context
        for _ in range(10):  # Test multiple times to ensure consistency
            assert ConditionalOTPService.requires_otp("wallet_cashout") is True
            assert ConditionalOTPService.requires_otp("exchange_sell_crypto") is False
            assert ConditionalOTPService.requires_otp("escrow") is False
    
    def test_no_amount_thresholds(self):
        """Test that there are no amount thresholds as per document simplification"""
        # Document: "No amount thresholds"
        # The service should not consider amounts in OTP decisions
        
        # Method signatures don't include amount parameters
        assert hasattr(ConditionalOTPService, 'requires_otp')
        
        # Verify the method only takes transaction_type parameter
        import inspect
        sig = inspect.signature(ConditionalOTPService.requires_otp)
        params = list(sig.parameters.keys())
        assert params == ['transaction_type'], "Method should only accept transaction_type parameter"
    
    def test_no_user_verification_levels(self):
        """Test that there are no user verification levels as per document simplification"""
        # Document: "No user verification levels"
        # The service should not consider user verification status in OTP decisions
        
        # Method signatures don't include user parameters
        assert hasattr(ConditionalOTPService, 'requires_otp')
        
        # Verify the method only takes transaction_type parameter
        import inspect
        sig = inspect.signature(ConditionalOTPService.requires_otp)
        params = list(sig.parameters.keys())
        assert params == ['transaction_type'], "Method should only accept transaction_type parameter"


class TestBackwardCompatibility:
    """Test backward compatibility with existing systems"""
    
    def test_convenience_functions_work(self):
        """Test that convenience functions maintain backward compatibility"""
        # Test convenience function
        assert requires_otp_for_transaction("wallet_cashout") is True
        assert requires_otp_for_transaction("exchange_sell_crypto") is False
        
        # Test status convenience function
        assert get_next_status_after_authorization("wallet_cashout") == "otp_pending"
        assert get_next_status_after_authorization("escrow") == "processing"
    
    def test_string_and_enum_compatibility(self):
        """Test that both string and enum inputs work for backward compatibility"""
        # String inputs
        assert ConditionalOTPService.requires_otp("wallet_cashout") is True
        assert ConditionalOTPService.get_otp_flow_status("wallet_cashout") == "otp_pending"
        
        # Enum inputs
        assert ConditionalOTPService.requires_otp_enum(UnifiedTransactionType.WALLET_CASHOUT) is True
        assert ConditionalOTPService.get_otp_flow_status_enum(UnifiedTransactionType.WALLET_CASHOUT) == UnifiedTransactionStatus.OTP_PENDING
    
    def test_exports_available(self):
        """Test that all expected exports are available"""
        from services.conditional_otp_service import (
            ConditionalOTPService,
            OTPRequirementReason,
            requires_otp_for_transaction,
            get_next_status_after_authorization
        )
        
        assert ConditionalOTPService is not None
        assert OTPRequirementReason is not None
        assert requires_otp_for_transaction is not None
        assert get_next_status_after_authorization is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])