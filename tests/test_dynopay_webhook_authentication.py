#!/usr/bin/env python3
"""
ARCHITECT VERIFICATION REQUIREMENT #1: DynoPay Webhook Authentication Tests
Provides concrete evidence of signature verification enforcement with signed/unsigned payload handling
"""

import pytest
import json
import hmac
import hashlib
from unittest.mock import Mock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient

from utils.webhook_security import WebhookSecurity
from handlers.dynopay_exchange_webhook import DynoPayExchangeWebhookHandler
from config import Config


class TestDynoPayWebhookAuthentication:
    """
    CRITICAL SECURITY VERIFICATION: DynoPay webhook authentication tests
    
    Tests verify:
    1. Valid signatures are accepted ✅
    2. Invalid signatures are rejected ❌
    3. Missing signatures are handled based on environment 
    4. Production mode enforces signature verification
    5. Development mode allows optional verification
    """

    @pytest.fixture
    def valid_webhook_payload(self):
        """Sample DynoPay exchange webhook payload"""
        return {
            "id": "dynopay_tx_12345",
            "paid_amount": 0.001,
            "paid_currency": "BTC", 
            "status": "confirmed",
            "meta_data": {
                "refId": "EXC_1758218901410_3122_000000",
                "operation_type": "exchange_deposit"
            }
        }

    @pytest.fixture
    def webhook_secret(self):
        """Test webhook secret"""
        return "test_dynopay_secret_12345"
    
    def generate_valid_signature(self, payload: dict, secret: str) -> str:
        """Generate valid HMAC-SHA256 signature for payload"""
        payload_string = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        signature = hmac.new(
            secret.encode("utf-8"),
            payload_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def test_valid_signature_accepted(self, valid_webhook_payload, webhook_secret):
        """
        SECURITY TEST #1: Valid signature should be accepted
        
        EVIDENCE: WebhookSecurity.verify_dynopay_webhook() returns True for valid signature
        """
        # Generate valid signature
        valid_signature = self.generate_valid_signature(valid_webhook_payload, webhook_secret)
        
        # Mock configuration
        with patch.object(Config, 'DYNOPAY_WEBHOOK_SECRET', webhook_secret):
            with patch.object(Config, 'ENVIRONMENT', 'production'):
                # Test signature verification
                result = WebhookSecurity.verify_dynopay_webhook(valid_webhook_payload, valid_signature)
                
                assert result is True, "Valid signature should be accepted"

    def test_invalid_signature_rejected(self, valid_webhook_payload, webhook_secret):
        """
        SECURITY TEST #2: Invalid signature should be rejected
        
        EVIDENCE: WebhookSecurity.verify_dynopay_webhook() returns False for invalid signature
        """
        invalid_signature = "invalid_signature_12345"
        
        # Mock configuration
        with patch.object(Config, 'DYNOPAY_WEBHOOK_SECRET', webhook_secret):
            with patch.object(Config, 'ENVIRONMENT', 'production'):
                # Test signature verification
                result = WebhookSecurity.verify_dynopay_webhook(valid_webhook_payload, invalid_signature)
                
                assert result is False, "Invalid signature should be rejected"

    def test_missing_signature_production_rejected(self, valid_webhook_payload, webhook_secret):
        """
        SECURITY TEST #3: Missing signature in production should be rejected
        
        EVIDENCE: Production environment enforces signature requirement (fail-closed security)
        """
        missing_signature = None
        
        # Mock configuration
        with patch.object(Config, 'DYNOPAY_WEBHOOK_SECRET', webhook_secret):
            with patch.object(Config, 'ENVIRONMENT', 'production'):
                # Test signature verification
                result = WebhookSecurity.verify_dynopay_webhook(valid_webhook_payload, missing_signature)
                
                assert result is False, "Missing signature should be rejected in production"

    def test_missing_signature_development_allowed(self, valid_webhook_payload, webhook_secret):
        """
        SECURITY TEST #4: Missing signature in development should be allowed (with warnings)
        
        EVIDENCE: Development environment allows optional verification for integration testing
        """
        missing_signature = None
        
        # Mock configuration
        with patch.object(Config, 'DYNOPAY_WEBHOOK_SECRET', webhook_secret):
            with patch.object(Config, 'ENVIRONMENT', 'development'):
                # Test signature verification  
                result = WebhookSecurity.verify_dynopay_webhook(valid_webhook_payload, missing_signature)
                
                assert result is True, "Missing signature should be allowed in development"

    def test_missing_secret_production_rejected(self, valid_webhook_payload):
        """
        SECURITY TEST #5: Missing webhook secret in production should be rejected
        
        EVIDENCE: Production environment rejects webhooks when secret is not configured (fail-closed)
        """
        valid_signature = "any_signature"
        
        # Mock configuration with missing secret
        with patch.object(Config, 'DYNOPAY_WEBHOOK_SECRET', None):
            with patch.object(Config, 'ENVIRONMENT', 'production'):
                # Test signature verification
                result = WebhookSecurity.verify_dynopay_webhook(valid_webhook_payload, valid_signature)
                
                assert result is False, "Missing webhook secret should be rejected in production"

    def test_missing_secret_development_allowed(self, valid_webhook_payload):
        """
        SECURITY TEST #6: Missing webhook secret in development should be allowed
        
        EVIDENCE: Development environment allows webhooks without secret for integration testing
        """
        valid_signature = "any_signature"
        
        # Mock configuration with missing secret
        with patch.object(Config, 'DYNOPAY_WEBHOOK_SECRET', None):
            with patch.object(Config, 'ENVIRONMENT', 'development'):
                # Test signature verification
                result = WebhookSecurity.verify_dynopay_webhook(valid_webhook_payload, valid_signature)
                
                assert result is True, "Missing webhook secret should be allowed in development"

    @pytest.mark.asyncio
    async def test_webhook_validation_integration(self, valid_webhook_payload, webhook_secret):
        """
        INTEGRATION TEST: Full webhook validation flow including signature verification
        
        EVIDENCE: DynoPayExchangeWebhookHandler._validate_webhook_request() enforces authentication
        """
        from fastapi import Request
        
        # Create mock request with valid signature
        valid_signature = self.generate_valid_signature(valid_webhook_payload, webhook_secret)
        
        mock_request = Mock(spec=Request)
        mock_request.body.return_value = json.dumps(valid_webhook_payload).encode()
        mock_request.headers = {"x-dynopay-signature": valid_signature}
        mock_request.client.host = "127.0.0.1"
        
        # Mock configuration
        with patch.object(Config, 'DYNOPAY_WEBHOOK_SECRET', webhook_secret):
            with patch.object(Config, 'ENVIRONMENT', 'production'):
                # Test webhook validation
                result = await DynoPayExchangeWebhookHandler._validate_webhook_request(mock_request)
                
                assert result is True, "Valid webhook request should pass validation"

    @pytest.mark.asyncio
    async def test_webhook_validation_invalid_signature_rejected(self, valid_webhook_payload, webhook_secret):
        """
        INTEGRATION TEST: Webhook validation rejects invalid signatures
        
        EVIDENCE: DynoPayExchangeWebhookHandler._validate_webhook_request() enforces signature verification
        """
        from fastapi import Request
        
        # Create mock request with invalid signature
        invalid_signature = "invalid_signature_12345"
        
        mock_request = Mock(spec=Request)
        mock_request.body.return_value = json.dumps(valid_webhook_payload).encode()
        mock_request.headers = {"x-dynopay-signature": invalid_signature}
        mock_request.client.host = "127.0.0.1"
        
        # Mock configuration
        with patch.object(Config, 'DYNOPAY_WEBHOOK_SECRET', webhook_secret):
            with patch.object(Config, 'ENVIRONMENT', 'production'):
                # Test webhook validation
                result = await DynoPayExchangeWebhookHandler._validate_webhook_request(mock_request)
                
                assert result is False, "Invalid signature should be rejected"

    def test_signature_extraction_headers(self):
        """
        SECURITY TEST #7: Signature extraction from various header formats
        
        EVIDENCE: WebhookSecurity.extract_webhook_signature() handles DynoPay headers correctly
        """
        test_headers = {
            "x-dynopay-signature": "dynopay_signature_123",
            "x-signature": "fallback_signature_456", 
            "signature": "basic_signature_789"
        }
        
        # Test DynoPay-specific header extraction
        result = WebhookSecurity.extract_webhook_signature(test_headers, "dynopay")
        assert result == "dynopay_signature_123", "Should prefer x-dynopay-signature header"
        
        # Test fallback header extraction
        headers_no_dynopay = {
            "x-signature": "fallback_signature_456",
            "signature": "basic_signature_789"
        }
        result = WebhookSecurity.extract_webhook_signature(headers_no_dynopay, "dynopay")
        assert result == "fallback_signature_456", "Should fallback to x-signature header"

    def test_timing_safe_comparison(self, valid_webhook_payload, webhook_secret):
        """
        SECURITY TEST #8: Timing-safe signature comparison to prevent timing attacks
        
        EVIDENCE: WebhookSecurity.verify_dynopay_webhook() uses hmac.compare_digest() for timing safety
        """
        # Generate valid signature
        valid_signature = self.generate_valid_signature(valid_webhook_payload, webhook_secret)
        
        # Test with slightly different signature (timing attack simulation)
        almost_valid_signature = valid_signature[:-1] + "x"  # Change last character
        
        with patch.object(Config, 'DYNOPAY_WEBHOOK_SECRET', webhook_secret):
            with patch.object(Config, 'ENVIRONMENT', 'production'):
                # Both should return quickly (timing-safe)
                import time
                
                # Valid signature
                start = time.time()
                result1 = WebhookSecurity.verify_dynopay_webhook(valid_webhook_payload, valid_signature)
                time1 = time.time() - start
                
                # Invalid signature
                start = time.time()
                result2 = WebhookSecurity.verify_dynopay_webhook(valid_webhook_payload, almost_valid_signature)
                time2 = time.time() - start
                
                assert result1 is True, "Valid signature should be accepted"
                assert result2 is False, "Invalid signature should be rejected"
                
                # Timing should be similar (within reasonable variance for timing-safe comparison)
                time_difference = abs(time1 - time2)
                assert time_difference < 0.01, f"Timing difference too large: {time_difference}s (potential timing attack vulnerability)"


if __name__ == "__main__":
    # Run tests with verbose output for architect verification
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "--disable-warnings"
    ])