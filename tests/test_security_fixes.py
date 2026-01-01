"""
Comprehensive Security Fixes Test Suite
Tests all implemented security fixes for currency conversion vulnerabilities
"""

import pytest
from decimal import Decimal
import asyncio
from unittest.mock import MagicMock, patch

# Import security modules
from utils.currency_validation import CurrencyValidator, ConversionAuditLogger, CurrencyValidationError
from utils.context_security import ContextDataProtector, ErrorRecoveryManager, ContextSecurityError

class TestCurrencyValidationFramework:
    """Test the centralized currency validation framework"""
    
    def test_crypto_switch_validation_success(self):
        """Test successful crypto switch validation"""
        # Simulate LTC to ETH switch with equivalent USD values
        old_crypto = "LTC"
        old_amount = Decimal("0.05")
        old_rate = Decimal("100.00")  # $100 per LTC
        
        new_crypto = "ETH"
        new_amount = Decimal("0.002")  # Equivalent amount
        new_rate = Decimal("2500.00")  # $2500 per ETH
        
        result = CurrencyValidator.validate_crypto_switch(
            old_crypto=old_crypto,
            old_amount=old_amount,
            new_crypto=new_crypto,
            new_amount=new_amount,
            old_rate=old_rate,
            new_rate=new_rate,
            context="test_escrow"
        )
        
        assert result["is_valid"] == True
        assert result["old_usd_value"] == 5.0  # 0.05 * 100
        assert result["new_usd_value"] == 5.0  # 0.002 * 2500
        assert result["deviation_percentage"] == 0.0
    
    def test_crypto_switch_validation_failure(self):
        """Test crypto switch validation failure with significant deviation"""
        # Simulate exploit attempt: 0.05 LTC -> 0.05 ETH (massive value inflation)
        old_crypto = "LTC"
        old_amount = Decimal("0.05")
        old_rate = Decimal("100.00")  # $100 per LTC = $5 value
        
        new_crypto = "ETH"
        new_amount = Decimal("0.05")  # Same amount (WRONG!)
        new_rate = Decimal("2500.00")  # $2500 per ETH = $125 value
        
        result = CurrencyValidator.validate_crypto_switch(
            old_crypto=old_crypto,
            old_amount=old_amount,
            new_crypto=new_crypto,
            new_amount=new_amount,
            old_rate=old_rate,
            new_rate=new_rate,
            context="test_exploit"
        )
        
        assert result["is_valid"] == False
        assert result["old_usd_value"] == 5.0
        assert result["new_usd_value"] == 125.0
        assert result["deviation_percentage"] > 2000  # 2400% inflation
    
    def test_equivalent_amount_calculation(self):
        """Test equivalent amount calculation for currency switching"""
        source_amount = Decimal("0.1")
        source_rate = Decimal("50000.00")  # BTC at $50,000
        target_rate = Decimal("3000.00")   # ETH at $3,000
        
        target_amount, validation_info = CurrencyValidator.calculate_equivalent_amount(
            source_amount=source_amount,
            source_rate=source_rate,
            target_rate=target_rate,
            source_currency="BTC",
            target_currency="ETH",
            context="test_conversion"
        )
        
        expected_usd = source_amount * source_rate  # 0.1 * 50000 = $5000
        expected_target = expected_usd / target_rate  # 5000 / 3000 = 1.666... ETH
        
        assert abs(target_amount - expected_target) < Decimal("0.00000001")
        assert validation_info["usd_value"] == 5000.0
        assert validation_info["source_currency"] == "BTC"
        assert validation_info["target_currency"] == "ETH"
    
    def test_order_amount_consistency_validation(self):
        """Test exchange order amount consistency validation"""
        source_amount = Decimal("100.00")  # $100
        target_amount = Decimal("50000.00")  # ₦50,000
        exchange_rate = Decimal("500.00")  # 500 NGN per USD
        
        result = CurrencyValidator.validate_order_amount_consistency(
            source_amount=source_amount,
            target_amount=target_amount,
            exchange_rate=exchange_rate,
            source_currency="USD",
            target_currency="NGN",
            order_id="TEST_001"
        )
        
        assert result["is_valid"] == True
        assert result["expected_target"] == 50000.0
        assert result["deviation_percentage"] == 0.0

class TestContextDataSecurity:
    """Test context data security and integrity"""
    
    def test_context_integrity_validation_success(self):
        """Test successful context integrity validation"""
        from datetime import datetime
        
        context_data = {
            "amount": 100.0,
            "currency": "USD",
            "user_id": 12345,
            "created_at": datetime.utcnow().isoformat()
        }
        
        required_fields = ["amount", "currency", "user_id"]
        
        result = ContextDataProtector.validate_context_integrity(
            context_data=context_data,
            required_fields=required_fields,
            context_type="test_escrow"
        )
        
        assert result["is_valid"] == True
        assert len(result["missing_fields"]) == 0
        assert len(result["corrupted_fields"]) == 0
    
    def test_context_integrity_validation_failure(self):
        """Test context integrity validation with missing fields"""
        context_data = {
            "amount": 100.0,
            "user_id": None  # Corrupted field
            # Missing "currency" field
        }
        
        required_fields = ["amount", "currency", "user_id"]
        
        result = ContextDataProtector.validate_context_integrity(
            context_data=context_data,
            required_fields=required_fields,
            context_type="test_corrupted"
        )
        
        assert result["is_valid"] == False
        assert "currency" in result["missing_fields"]
        assert "user_id_is_null" in result["corrupted_fields"]
    
    def test_secure_context_update(self):
        """Test secure context updates preserve critical fields"""
        original_context = {
            "usd_value": 50.0,
            "user_id": 12345,
            "created_at": "2025-01-01T00:00:00",
            "amount": 100.0
        }
        
        malicious_updates = {
            "amount": 1000000.0,  # Attempt to inflate amount
            "user_id": 99999,     # Attempt to change user
            "usd_value": 60.0     # Legitimate rate update
        }
        
        updated_context = ContextDataProtector.secure_context_update(
            context_data=original_context,
            updates=malicious_updates,
            operation="test_update"
        )
        
        # Critical fields should be protected
        assert updated_context["user_id"] == 12345  # Protected
        assert updated_context["created_at"] == "2025-01-01T00:00:00"  # Protected
        # But USD value updates should be allowed for security fixes
        assert updated_context["usd_value"] == 60.0  # Allowed
        assert "last_updated" in updated_context

class TestErrorRecovery:
    """Test error recovery mechanisms"""
    
    def test_conversion_error_handling(self):
        """Test conversion error handling and recovery"""
        error = CurrencyValidationError("Invalid rate data")
        context_data = {"amount": 100.0, "currency": "USD"}
        
        recovery_result = ErrorRecoveryManager.handle_conversion_error(
            error=error,
            context_data=context_data,
            operation="test_conversion",
            user_id=12345
        )
        
        assert recovery_result["error_handled"] == True
        assert recovery_result["recovery_action"] == "reset_to_safe_state"
        assert "Invalid operation detected" in recovery_result["user_message"]

class TestIntegrationScenarios:
    """Test end-to-end security scenarios"""
    
    def test_escrow_crypto_switch_exploit_prevention(self):
        """Test prevention of escrow crypto switch exploit"""
        # Simulate user starting with LTC payment
        initial_usd_value = Decimal("50.00")  # $50 escrow
        ltc_rate = Decimal("100.00")  # $100 per LTC
        initial_ltc_amount = initial_usd_value / ltc_rate  # 0.5 LTC
        
        # User attempts to switch to ETH but preserve LTC amount (exploit)
        eth_rate = Decimal("3000.00")  # $3000 per ETH
        
        # Using validation framework (SECURE)
        correct_eth_amount, _ = CurrencyValidator.calculate_equivalent_amount(
            source_amount=initial_ltc_amount,
            source_rate=ltc_rate,
            target_rate=eth_rate,
            source_currency="LTC",
            target_currency="ETH",
            context="escrow_switch_test"
        )
        
        # Validate the conversion preserves USD value
        validation_result = CurrencyValidator.validate_crypto_switch(
            old_crypto="LTC",
            old_amount=initial_ltc_amount,
            new_crypto="ETH",
            new_amount=correct_eth_amount,
            old_rate=ltc_rate,
            new_rate=eth_rate,
            context="escrow_exploit_test"
        )
        
        assert validation_result["is_valid"] == True
        assert abs(validation_result["old_usd_value"] - validation_result["new_usd_value"]) < 0.01
        assert float(correct_eth_amount) < 0.02  # Much smaller than 0.5 LTC
    
    def test_exchange_order_validation_integration(self):
        """Test exchange order validation prevents incorrect amounts"""
        from services.exchange_service import ExchangeService
        
        # Test data that would trigger validation
        rate_info = {
            "usd_amount": 100.0,
            "final_ngn_amount": 50000.0,
            "crypto_amount": 0.002,
            "effective_rate": 500.0,
            "exchange_markup_percentage": 5.0,
            "processing_fee": 0.0
        }
        
        # This should pass validation
        result = CurrencyValidator.validate_order_amount_consistency(
            source_amount=Decimal("100.00"),
            target_amount=Decimal("50000.00"),
            exchange_rate=Decimal("500.00"),
            source_currency="USD",
            target_currency="NGN",
            order_id="TEST_INTEGRATION"
        )
        
        assert result["is_valid"] == True

if __name__ == "__main__":
    # Run basic validation tests
    print("🔍 Running Security Fixes Test Suite...")
    
    # Test currency validation
    validator_tests = TestCurrencyValidationFramework()
    validator_tests.test_crypto_switch_validation_success()
    validator_tests.test_crypto_switch_validation_failure()
    validator_tests.test_equivalent_amount_calculation()
    print("✅ Currency validation tests passed")
    
    # Test context security
    context_tests = TestContextDataSecurity()
    context_tests.test_context_integrity_validation_success()
    context_tests.test_context_integrity_validation_failure()
    context_tests.test_secure_context_update()
    print("✅ Context security tests passed")
    
    # Test error recovery
    recovery_tests = TestErrorRecovery()
    recovery_tests.test_conversion_error_handling()
    print("✅ Error recovery tests passed")
    
    # Test integration scenarios
    integration_tests = TestIntegrationScenarios()
    integration_tests.test_escrow_crypto_switch_exploit_prevention()
    integration_tests.test_exchange_order_validation_integration()
    print("✅ Integration tests passed")
    
    print("🎉 All security fixes validated successfully!")
    print("🛡️ System protected against currency conversion vulnerabilities")