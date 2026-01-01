"""
Fincra Service Fake Provider
Comprehensive test double for Fincra NGN payment service
"""

import asyncio
import logging
from decimal import Decimal
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from models import CashoutErrorCode

logger = logging.getLogger(__name__)


class FincraFakeProvider:
    """
    Comprehensive fake provider for Fincra NGN payment service
    
    Features:
    - Deterministic responses based on input patterns
    - Configurable failure scenarios
    - Balance simulation
    - Webhook event simulation
    - NGN tolerance testing support
    """
    
    def __init__(self):
        self.secret_key = "test_fincra_secret_key"
        self.public_key = "test_fincra_public_key"
        self.business_id = "test_business_id"
        self.webhook_key = "test_webhook_key"
        self.base_url = "https://api.fincra.com"
        self.test_mode = True
        
        # State management for test scenarios
        self.balance_ngn = Decimal("100000.00")  # Default test balance
        self.failure_mode = None  # None, "insufficient_funds", "api_timeout", "auth_failed"
        self.request_history = []
        self.webhook_events = []
        
        # Deterministic response patterns
        self.account_responses = {}
        self.transfer_responses = {}
        
    def reset_state(self):
        """Reset fake provider state for test isolation"""
        self.balance_ngn = Decimal("100000.00")
        self.failure_mode = None
        self.request_history.clear()
        self.webhook_events.clear()
        self.account_responses.clear()
        self.transfer_responses.clear()
        
    def set_failure_mode(self, mode: Optional[str]):
        """Configure failure scenarios: None, 'insufficient_funds', 'api_timeout', 'auth_failed'"""
        self.failure_mode = mode
        
    def set_balance(self, balance_ngn: Decimal):
        """Set available NGN balance for testing"""
        self.balance_ngn = balance_ngn
        
    def add_account_response(self, account_number: str, response: Dict[str, Any]):
        """Pre-configure account verification response for specific account"""
        self.account_responses[account_number] = response
        
    def add_transfer_response(self, reference: str, response: Dict[str, Any]):
        """Pre-configure transfer response for specific reference"""
        self.transfer_responses[reference] = response
    
    async def check_bank_account(self, bank_code: str, account_number: str) -> Optional[Dict]:
        """
        Fake bank account verification
        Returns deterministic responses based on account patterns
        """
        self.request_history.append({
            "method": "check_bank_account",
            "bank_code": bank_code,
            "account_number": account_number,
            "timestamp": datetime.now(timezone.utc)
        })
        
        # Simulate failure modes
        if self.failure_mode == "api_timeout":
            raise Exception("Fincra timeout")
        elif self.failure_mode == "auth_failed":
            raise Exception("Fincra authentication failed")
            
        # Check for pre-configured response
        if account_number in self.account_responses:
            return self.account_responses[account_number]
            
        # Deterministic responses based on account patterns
        if account_number.endswith("0000"):
            # Invalid account pattern
            return None
        elif account_number.endswith("9999"):
            # Timeout simulation account
            await asyncio.sleep(0.1)  # Brief delay to simulate timeout scenario
            raise Exception("Request timeout")
        else:
            # Valid account pattern
            return {
                "success": True,
                "account_name": f"TEST USER {account_number[-4:]}",
                "bank_name": "ACCESS BANK" if bank_code == "044" else "ZENITH BANK",
                "account_number": account_number,
                "bank_code": bank_code
            }
    
    async def process_bank_transfer(
        self,
        amount_ngn: Decimal,
        bank_code: str,
        account_number: str,
        account_name: str,
        reference: str,
        currency: str = "NGN",
        session=None,
        cashout_id: str = None,
        transaction_id: str = None
    ) -> Optional[Dict]:
        """
        Fake bank transfer processing
        Simulates various success/failure scenarios
        """
        self.request_history.append({
            "method": "process_bank_transfer",
            "amount_ngn": float(amount_ngn),
            "bank_code": bank_code,
            "account_number": account_number,
            "reference": reference,
            "timestamp": datetime.now(timezone.utc)
        })
        
        # Simulate failure modes
        if self.failure_mode == "insufficient_funds":
            raise Exception("No_enough_money_in_wallet")
        elif self.failure_mode == "api_timeout":
            raise Exception("Fincra timeout")
        elif self.failure_mode == "auth_failed":
            raise Exception("Fincra authentication failed")
            
        # Check balance
        if amount_ngn > self.balance_ngn:
            raise Exception("No_enough_money_in_wallet")
            
        # Check for pre-configured response
        if reference in self.transfer_responses:
            response = self.transfer_responses[reference].copy()
            # Deduct balance on successful transfer
            if response.get("success"):
                self.balance_ngn -= amount_ngn
            return response
        
        # Generate deterministic response based on reference pattern
        if reference.endswith("_FAIL"):
            return {
                "success": False,
                "message": "Transfer failed",
                "reference": reference,
                "fincra_reference": f"FINCRA_FAIL_{reference}"
            }
        elif reference.endswith("_PENDING"):
            return {
                "success": True,
                "status": "processing",
                "message": "Transfer is being processed",
                "reference": reference,
                "fincra_reference": f"FINCRA_PENDING_{reference}",
                "requires_admin_funding": True
            }
        else:
            # Successful transfer
            self.balance_ngn -= amount_ngn
            return {
                "success": True,
                "status": "successful",
                "message": "Transfer successful",
                "reference": reference,
                "fincra_reference": f"FINCRA_SUCCESS_{reference}",
                "amount": float(amount_ngn),
                "currency": currency,
                "fee": float(amount_ngn * Decimal("0.01"))  # 1% fee
            }
    
    async def get_cached_account_balance(self) -> Optional[Dict]:
        """
        Fake balance retrieval
        Returns current simulated balance
        """
        self.request_history.append({
            "method": "get_cached_account_balance",
            "timestamp": datetime.now(timezone.utc)
        })
        
        if self.failure_mode == "api_timeout":
            raise Exception("Fincra timeout")
        elif self.failure_mode == "auth_failed":
            raise Exception("Fincra authentication failed")
            
        return {
            "success": True,
            "available_balance": float(self.balance_ngn),
            "total_balance": float(self.balance_ngn),
            "currency": "NGN"
        }
    
    async def check_transfer_status_by_reference(self, reference: str) -> Optional[Dict]:
        """
        Fake transfer status check
        Returns status based on reference pattern
        """
        self.request_history.append({
            "method": "check_transfer_status_by_reference",
            "reference": reference,
            "timestamp": datetime.now(timezone.utc)
        })
        
        if self.failure_mode == "api_timeout":
            raise Exception("Fincra timeout")
        elif self.failure_mode == "auth_failed":
            raise Exception("Fincra authentication failed")
        
        # Check for pre-configured response
        if reference in self.transfer_responses:
            return self.transfer_responses[reference]
        
        # Generate status based on reference pattern
        if reference.endswith("_FAIL"):
            return {
                "status": "failed",
                "message": "Transfer failed",
                "reference": reference
            }
        elif reference.endswith("_PENDING"):
            return {
                "status": "processing", 
                "message": "Transfer in progress",
                "reference": reference
            }
        else:
            return {
                "status": "successful",
                "message": "Transfer completed",
                "reference": reference
            }
    
    def generate_webhook_event(self, event_type: str, reference: str, status: str, **kwargs) -> Dict[str, Any]:
        """
        Generate fake webhook event for testing webhook handlers
        """
        event = {
            "event": event_type,
            "data": {
                "reference": reference,
                "status": status,
                "amount": kwargs.get("amount", 1000.0),
                "currency": kwargs.get("currency", "NGN"),
                "customerReference": kwargs.get("customerReference", reference),
                "createdAt": datetime.now(timezone.utc).isoformat(),
                **kwargs
            }
        }
        self.webhook_events.append(event)
        return event
    
    def get_request_history(self) -> List[Dict[str, Any]]:
        """Get history of all requests made to fake provider"""
        return self.request_history.copy()
    
    def get_webhook_events(self) -> List[Dict[str, Any]]:
        """Get all generated webhook events"""
        return self.webhook_events.copy()
        
    def clear_history(self):
        """Clear request history and webhook events"""
        self.request_history.clear()
        self.webhook_events.clear()


# Global instance for test patching
fincra_fake = FincraFakeProvider()