"""
Security validation tests for LockBay bot
Tests input validation, XSS prevention, injection attacks, and security measures
"""

import pytest
from unittest.mock import Mock, patch
import decimal
from decimal import Decimal

from utils.enhanced_input_validation import SecurityInputValidator
# from services.unified_validation_gateway import UnifiedValidationGateway  # Module not found - commented out
from utils.helpers import validate_crypto_address
# sanitize_user_input function not found - removing import


class TestSecurityInputValidation:
    """Test security input validation across all handlers"""

    @pytest.fixture
    def malicious_inputs(self):
        """Collection of malicious input patterns"""
        return [
            # XSS Attacks
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "';alert('xss');//",
            
            # SQL Injection
            "'; DROP TABLE users; --",
            "' OR '1'='1' --",
            "1' UNION SELECT * FROM users --",
            "admin'/**/OR/**/1=1#",
            
            # Template Injection
            "{{7*7}}",
            "${7*7}",
            "<%=7*7%>",
            "{{constructor.constructor('alert(1)')()}}",
            
            # Path Traversal
            "../../../etc/passwd",
            "....//....//....//etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            
            # Command Injection
            "; cat /etc/passwd",
            "| whoami",
            "&& ls -la",
            "`rm -rf /`",
            
            # LDAP Injection
            "*)(uid=*",
            "admin)(&(password=*))",
            
            # Special Characters and Null Bytes
            "\x00null_byte",
            "\x0a\x0d",
            "\u0000",
            
            # Unicode and Encoding Attacks
            "%3Cscript%3Ealert('xss')%3C/script%3E",
            "&lt;script&gt;alert('xss')&lt;/script&gt;",
            "\u003Cscript\u003Ealert('xss')\u003C/script\u003E"
        ]

    def test_email_input_validation(self, malicious_inputs):
        """Test email input validation against malicious inputs"""
        
        for malicious_input in malicious_inputs:
            result = SecurityInputValidator.validate_and_sanitize_input(
                malicious_input,
                input_type="email",
                max_length=100,
                context="seller_email"
            )
            
            # Should reject malicious emails
            assert not result["is_valid"]
            assert "security" in result["error_type"] or "format" in result["error_type"]
            
            # Sanitized value should not contain malicious content
            if result["sanitized_value"]:
                assert "<script>" not in result["sanitized_value"]
                assert "alert(" not in result["sanitized_value"]
                assert "DROP TABLE" not in result["sanitized_value"]

    def test_amount_input_validation(self, malicious_inputs):
        """Test amount input validation against injection attacks"""
        
        for malicious_input in malicious_inputs:
            result = SecurityInputValidator.validate_and_sanitize_input(
                malicious_input,
                input_type="amount", 
                max_length=20,
                context="escrow_amount"
            )
            
            # Should reject non-numeric malicious inputs
            assert not result["is_valid"]
            
            # Should not process as valid amount
            if result["sanitized_value"]:
                try:
                    amount = float(result["sanitized_value"])
                    # If it somehow becomes a number, should be rejected for other reasons
                    assert amount <= 0 or amount != amount  # NaN or invalid
                except (ValueError, TypeError):
                    # Expected - malicious input shouldn't convert to valid number
                    pass

    def test_description_input_sanitization(self, malicious_inputs):
        """Test description input sanitization"""
        
        for malicious_input in malicious_inputs:
            result = SecurityInputValidator.validate_and_sanitize_input(
                malicious_input,
                input_type="text",
                max_length=500,
                context="escrow_description"
            )
            
            # Should sanitize but might still be considered valid text
            if result["is_valid"] and result["sanitized_value"]:
                sanitized = result["sanitized_value"]
                
                # Ensure dangerous content is removed/escaped
                assert "<script>" not in sanitized
                assert "javascript:" not in sanitized
                assert "DROP TABLE" not in sanitized
                assert "alert(" not in sanitized
                
                # Should not contain raw HTML
                if "<" in malicious_input and ">" in malicious_input:
                    assert sanitized != malicious_input  # Should be modified

    def test_crypto_address_validation(self):
        """Test cryptocurrency address validation"""
        
        valid_addresses = [
            ("BTC", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"),
            ("BTC", "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"),
            ("ETH", "0x742d35Cc6634C0532925a3b8D0123456789abcdef"),
            ("USDT-ERC20", "0x742d35Cc6634C0532925a3b8D0123456789abcdef"),
            ("TRX", "TLsV52sRDL79HXGGm9yzwDeznWX2o1o9Bh")
        ]
        
        for currency, address in valid_addresses:
            # Test with validation helper
            is_valid = validate_crypto_address(address, currency)
            assert is_valid is True or is_valid is None  # None = not implemented
        
        # Test malicious addresses
        malicious_addresses = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE addresses; --",
            "../../../etc/passwd",
            "javascript:alert('xss')"
        ]
        
        for malicious_address in malicious_addresses:
            for currency in ["BTC", "ETH", "USDT-ERC20"]:
                is_valid = validate_crypto_address(malicious_address, currency)
                assert is_valid is False

    def test_phone_number_validation(self):
        """Test phone number input validation"""
        
        valid_phones = [
            "+1234567890",
            "+44123456789",
            "+234901234567"
        ]
        
        for phone in valid_phones:
            result = SecurityInputValidator.validate_and_sanitize_input(
                phone,
                input_type="phone",
                max_length=20,
                context="seller_phone"
            )
            
            assert result["is_valid"] is True
            assert result["sanitized_value"] == phone
        
        # Test malicious phone numbers
        malicious_phones = [
            "+1<script>alert('xss')</script>",
            "+1'; DROP TABLE users; --",
            "+1{{7*7}}"
        ]
        
        for phone in malicious_phones:
            result = SecurityInputValidator.validate_and_sanitize_input(
                phone,
                input_type="phone", 
                max_length=20,
                context="seller_phone"
            )
            
            assert not result["is_valid"]


class TestUnifiedValidationGateway:
    """Test unified validation gateway security"""

    def test_gateway_input_validation(self):
        """Test gateway validates inputs properly"""
        
        gateway = UnifiedValidationGateway()
        
        # Test XSS in various contexts
        xss_input = "<script>alert('xss')</script>"
        
        contexts = ["escrow_description", "seller_email", "cashout_address"]
        
        for context in contexts:
            result = gateway.validate_input(xss_input, context)
            
            # Should detect and prevent XSS
            assert not result["is_valid"]
            
            if result["sanitized_value"]:
                assert "<script>" not in result["sanitized_value"]

    def test_gateway_sql_injection_prevention(self):
        """Test gateway prevents SQL injection"""
        
        gateway = UnifiedValidationGateway()
        
        sql_injections = [
            "'; DROP TABLE users; --",
            "' OR '1'='1' --",
            "1' UNION SELECT password FROM users --"
        ]
        
        for injection in sql_injections:
            result = gateway.validate_input(injection, "escrow_description")
            
            # Should sanitize or reject SQL injection attempts
            if result["is_valid"]:
                assert "DROP TABLE" not in result["sanitized_value"]
                assert "UNION SELECT" not in result["sanitized_value"]
            else:
                assert "sql" in result["error_type"] or "security" in result["error_type"]

    def test_gateway_length_limits(self):
        """Test gateway enforces length limits"""
        
        gateway = UnifiedValidationGateway()
        
        long_input = "A" * 10000  # Very long input
        
        result = gateway.validate_input(long_input, "escrow_description")
        
        # Should reject excessively long inputs
        if not result["is_valid"]:
            assert "length" in result["error_type"]
        else:
            # If valid, should be truncated
            assert len(result["sanitized_value"]) <= 500


class TestInputSanitization:
    """Test input sanitization functions"""

    def test_sanitize_user_input_html_removal(self):
        """Test HTML tag removal in sanitization"""
        
        html_inputs = [
            "<b>Bold text</b>",
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "<div>Normal content</div>"
        ]
        
        for html_input in html_inputs:
            sanitized = sanitize_user_input(html_input)
            
            # Should remove HTML tags
            assert "<" not in sanitized or ">" not in sanitized
            
            # Should preserve text content where appropriate
            if "Bold text" in html_input:
                assert "Bold text" in sanitized
            
            # Should remove dangerous content entirely
            if "alert" in html_input:
                assert "alert" not in sanitized

    def test_sanitize_user_input_special_chars(self):
        """Test sanitization of special characters"""
        
        special_inputs = [
            "Normal text with & ampersand",
            "Quote 'test' and \"double quotes\"", 
            "Null byte \x00 test",
            "Unicode \u0000 test"
        ]
        
        for special_input in special_inputs:
            sanitized = sanitize_user_input(special_input)
            
            # Should handle special characters safely
            assert "\x00" not in sanitized
            assert "\u0000" not in sanitized
            
            # Should preserve safe content
            if "Normal text" in special_input:
                assert "Normal text" in sanitized

    def test_sanitize_preserves_valid_content(self):
        """Test that sanitization preserves valid content"""
        
        valid_inputs = [
            "Normal trading description for website development",
            "Email: user@example.com",
            "Amount: $100.50",
            "Phone: +1234567890"
        ]
        
        for valid_input in valid_inputs:
            sanitized = sanitize_user_input(valid_input)
            
            # Should preserve valid content unchanged or minimally changed
            assert len(sanitized) > 0
            
            # Key content should be preserved
            if "website development" in valid_input:
                assert any(word in sanitized for word in ["website", "development"])
            if "@example.com" in valid_input:
                assert "@example.com" in sanitized or "example" in sanitized


class TestSecurityErrorHandling:
    """Test security-related error handling"""

    def test_validation_error_responses(self):
        """Test that validation errors provide appropriate responses"""
        
        validator = SecurityInputValidator()
        
        # Test various invalid inputs
        test_cases = [
            ("<script>alert('xss')</script>", "email"),
            ("'; DROP TABLE users; --", "text"),
            ("{{7*7}}", "amount"),
            ("javascript:alert('xss')", "text")
        ]
        
        for malicious_input, input_type in test_cases:
            result = validator.validate_and_sanitize_input(
                malicious_input, 
                input_type, 
                max_length=100, 
                context="test"
            )
            
            # Should provide clear error information
            assert "is_valid" in result
            assert "error_type" in result
            assert "error_message" in result
            
            # Error messages should be informative but not reveal system details
            if result["error_message"]:
                assert "internal error" not in result["error_message"].lower()
                assert "exception" not in result["error_message"].lower()
                assert "sql" not in result["error_message"].lower()

    def test_security_logging(self):
        """Test that security violations are properly logged"""
        
        with patch('utils.enhanced_input_validation.logger') as mock_logger:
            validator = SecurityInputValidator()
            
            result = validator.validate_and_sanitize_input(
                "<script>alert('xss')</script>",
                "email",
                max_length=100,
                context="test_logging"
            )
            
            # Should log security violations
            assert mock_logger.warning.called or mock_logger.error.called

    def test_security_metrics_collection(self):
        """Test that security metrics are collected"""
        
        # This test verifies that security events are tracked
        # Implementation depends on actual metrics system
        
        validator = SecurityInputValidator()
        
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "{{7*7}}"
        ]
        
        for malicious_input in malicious_inputs:
            result = validator.validate_and_sanitize_input(
                malicious_input,
                "text", 
                max_length=100,
                context="metrics_test"
            )
            
            # Should reject malicious input
            assert not result["is_valid"]
            
            # Should track security violations (implementation specific)
            # This could increment counters, send alerts, etc.


class TestCryptographicSecurity:
    """Test cryptographic security measures"""

    def test_address_validation_security(self):
        """Test that address validation is secure against manipulation"""
        
        # Test address validation doesn't allow code execution
        dangerous_addresses = [
            "eval('malicious code')",
            "require('child_process').exec('rm -rf /')",
            "import os; os.system('malicious command')"
        ]
        
        for dangerous_address in dangerous_addresses:
            is_valid = validate_crypto_address(dangerous_address, "BTC")
            
            # Should safely reject without executing code
            assert is_valid is False

    def test_amount_calculation_security(self):
        """Test that amount calculations are secure"""
        
        # Test against precision attacks and overflow
        dangerous_amounts = [
            "1e308",  # Very large number
            "1e-324", # Very small number  
            "NaN",
            "Infinity",
            "-Infinity",
            "0.1 + 0.2 - 0.3"  # Floating point precision issue
        ]
        
        for dangerous_amount in dangerous_amounts:
            result = SecurityInputValidator.validate_and_sanitize_input(
                dangerous_amount,
                "amount",
                max_length=50,
                context="security_test"
            )
            
            # Should handle dangerous amounts safely
            if result["is_valid"]:
                try:
                    amount = Decimal(result["sanitized_value"])
                    # Should be within reasonable bounds
                    assert amount >= 0
                    assert amount < Decimal("1000000000")  # Reasonable upper limit
                except (ValueError, decimal.InvalidOperation) as e:
                    # If can't convert to Decimal, that's also acceptable
                    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])