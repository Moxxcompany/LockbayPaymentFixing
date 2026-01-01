"""
Kraken Service Fake Provider
Comprehensive test double for Kraken crypto exchange service
"""

import asyncio
import logging
from decimal import Decimal
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from models import CashoutErrorCode

logger = logging.getLogger(__name__)


class KrakenFakeProvider:
    """
    Comprehensive fake provider for Kraken crypto exchange service
    
    Features:
    - Deterministic responses based on input patterns  
    - Configurable failure scenarios
    - Balance simulation with multiple currencies
    - Withdrawal simulation with tx tracking
    - Address validation testing
    """
    
    def __init__(self):
        self.api_key = "test_kraken_api_key"
        self.secret_key = "test_kraken_secret_key"
        self.base_url = "https://api.kraken.com"
        
        # State management for test scenarios
        self.balances = {
            "USD": Decimal("10000.00"),
            "BTC": Decimal("1.0"),
            "ETH": Decimal("10.0"),
            "LTC": Decimal("100.0"),
            "USDT": Decimal("10000.0")
        }
        self.failure_mode = None  # None, "insufficient_funds", "api_timeout", "auth_failed", "addr_not_found"
        self.request_history = []
        self.withdrawal_history = []
        
        # Pre-configured responses
        self.address_responses = {}
        self.withdrawal_responses = {}
        
    def reset_state(self):
        """Reset fake provider state for test isolation"""
        self.balances = {
            "USD": Decimal("10000.00"),
            "BTC": Decimal("1.0"), 
            "ETH": Decimal("10.0"),
            "LTC": Decimal("100.0"),
            "USDT": Decimal("10000.0")
        }
        self.failure_mode = None
        self.request_history.clear()
        self.withdrawal_history.clear()
        self.address_responses.clear()
        self.withdrawal_responses.clear()
        
    def set_failure_mode(self, mode: Optional[str]):
        """Configure failure scenarios"""
        self.failure_mode = mode
        
    def set_balance(self, currency: str, amount: Decimal):
        """Set balance for specific currency"""
        self.balances[currency] = amount
        
    def add_address_response(self, currency: str, address: str, response: Dict[str, Any]):
        """Pre-configure address validation response"""
        key = f"{currency}_{address}"
        self.address_responses[key] = response
        
    def add_withdrawal_response(self, currency: str, address: str, response: Dict[str, Any]):
        """Pre-configure withdrawal response"""
        key = f"{currency}_{address}"
        self.withdrawal_responses[key] = response
    
    async def check_balance(self) -> Dict[str, Any]:
        """
        Fake balance check
        Returns current simulated balances
        """
        self.request_history.append({
            "method": "check_balance",
            "timestamp": datetime.now(timezone.utc)
        })
        
        # Simulate failure modes
        if self.failure_mode == "api_timeout":
            raise Exception("Kraken timeout")
        elif self.failure_mode == "auth_failed":
            raise Exception("EAPI:Invalid key")
            
        # Return balance data in Kraken format
        balance_data = {}
        for currency, amount in self.balances.items():
            if amount > 0:  # Only return currencies with positive balance
                kraken_currency = self._map_to_kraken_currency(currency)
                balance_data[kraken_currency] = {
                    "total": float(amount),
                    "available": float(amount),
                    "locked": 0.0
                }
                
        return {
            "success": True,
            "balances": balance_data
        }
    
    def _map_to_kraken_currency(self, currency: str) -> str:
        """Map standard currency codes to Kraken format"""
        mapping = {
            "USD": "ZUSD",
            "BTC": "XXBT", 
            "ETH": "XETH",
            "LTC": "XLTC",
            "USDT": "XUSDT"
        }
        return mapping.get(currency, currency)
    
    def _map_from_kraken_currency(self, kraken_currency: str) -> str:
        """Map Kraken currency codes to standard format"""
        mapping = {
            "ZUSD": "USD",
            "XXBT": "BTC",
            "XETH": "ETH", 
            "XLTC": "LTC",
            "XUSDT": "USDT"
        }
        return mapping.get(kraken_currency, kraken_currency)
    
    async def validate_address(self, currency: str, address: str) -> Dict[str, Any]:
        """
        Fake address validation
        Returns validation result based on address patterns
        """
        self.request_history.append({
            "method": "validate_address",
            "currency": currency,
            "address": address,
            "timestamp": datetime.now(timezone.utc)
        })
        
        # Simulate failure modes
        if self.failure_mode == "api_timeout":
            raise Exception("Kraken timeout")
        elif self.failure_mode == "auth_failed":
            raise Exception("EAPI:Invalid key")
        elif self.failure_mode == "addr_not_found":
            raise Exception("Unknown withdraw key")
            
        # Check for pre-configured response
        key = f"{currency}_{address}"
        if key in self.address_responses:
            return self.address_responses[key]
            
        # Deterministic responses based on address patterns
        if address.endswith("_INVALID"):
            return {
                "success": False,
                "error": "Invalid address format",
                "currency": currency,
                "address": address
            }
        elif address.endswith("_UNKNOWN"):
            raise Exception("Unknown withdraw key")
        else:
            # Valid address
            return {
                "success": True,
                "currency": currency,
                "address": address,
                "validated": True
            }
    
    async def withdraw_crypto(
        self,
        currency: str,
        amount: Decimal,
        address: str,
        memo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fake crypto withdrawal
        Simulates withdrawal with various success/failure scenarios
        """
        self.request_history.append({
            "method": "withdraw_crypto",
            "currency": currency,
            "amount": float(amount),
            "address": address,
            "memo": memo,
            "timestamp": datetime.now(timezone.utc)
        })
        
        # Simulate failure modes
        if self.failure_mode == "insufficient_funds":
            raise Exception("EGeneral:Insufficient funds")
        elif self.failure_mode == "api_timeout":
            raise Exception("Kraken timeout")
        elif self.failure_mode == "auth_failed":
            raise Exception("EAPI:Invalid key")
        elif self.failure_mode == "addr_not_found":
            raise Exception("Unknown withdraw key")
            
        # Check balance
        if currency not in self.balances or amount > self.balances[currency]:
            raise Exception("EGeneral:Insufficient funds")
            
        # Check for pre-configured response
        key = f"{currency}_{address}"
        if key in self.withdrawal_responses:
            response = self.withdrawal_responses[key].copy()
            # Deduct balance on successful withdrawal
            if response.get("success"):
                self.balances[currency] -= amount
                # Record withdrawal
                self.withdrawal_history.append({
                    "currency": currency,
                    "amount": float(amount),
                    "address": address,
                    "txid": response.get("txid"),
                    "refid": response.get("refid"),
                    "timestamp": datetime.now(timezone.utc)
                })
            return response
        
        # Generate deterministic response based on address pattern
        if address.endswith("_FAIL"):
            return {
                "success": False,
                "error": "Withdrawal failed",
                "currency": currency,
                "amount": float(amount),
                "address": address
            }
        elif address.endswith("_PENDING"):
            # Deduct balance for pending withdrawal
            self.balances[currency] -= amount
            withdrawal_data = {
                "currency": currency,
                "amount": float(amount),
                "address": address,
                "txid": None,  # Pending withdrawals don't have txid yet
                "refid": f"KRAKEN_PENDING_{currency}_{len(self.withdrawal_history)}",
                "status": "pending",
                "timestamp": datetime.now(timezone.utc)
            }
            self.withdrawal_history.append(withdrawal_data)
            return {
                "success": True,
                "refid": withdrawal_data["refid"],
                "status": "pending",
                "currency": currency,
                "amount": float(amount)
            }
        else:
            # Successful withdrawal
            self.balances[currency] -= amount
            withdrawal_data = {
                "currency": currency,
                "amount": float(amount),
                "address": address,
                "txid": f"test_tx_{currency}_{len(self.withdrawal_history)}",
                "refid": f"KRAKEN_SUCCESS_{currency}_{len(self.withdrawal_history)}",
                "status": "success",
                "timestamp": datetime.now(timezone.utc)
            }
            self.withdrawal_history.append(withdrawal_data)
            return {
                "success": True,
                "txid": withdrawal_data["txid"],
                "refid": withdrawal_data["refid"],
                "currency": currency,
                "amount": float(amount)
            }
    
    async def check_withdrawal_status(self, refid: str) -> Dict[str, Any]:
        """
        Fake withdrawal status check
        Returns status of previous withdrawals
        """
        self.request_history.append({
            "method": "check_withdrawal_status",
            "refid": refid,
            "timestamp": datetime.now(timezone.utc)
        })
        
        if self.failure_mode == "api_timeout":
            raise Exception("Kraken timeout")
        elif self.failure_mode == "auth_failed":
            raise Exception("EAPI:Invalid key")
        
        # Find withdrawal in history
        for withdrawal in self.withdrawal_history:
            if withdrawal["refid"] == refid:
                return {
                    "success": True,
                    "status": withdrawal["status"],
                    "currency": withdrawal["currency"],
                    "amount": withdrawal["amount"],
                    "txid": withdrawal.get("txid"),
                    "refid": refid
                }
        
        # Not found
        return {
            "success": False,
            "error": "Withdrawal not found",
            "refid": refid
        }
    
    def get_request_history(self) -> List[Dict[str, Any]]:
        """Get history of all requests made to fake provider"""
        return self.request_history.copy()
    
    def get_withdrawal_history(self) -> List[Dict[str, Any]]:
        """Get history of all withdrawals"""
        return self.withdrawal_history.copy()
        
    def clear_history(self):
        """Clear request and withdrawal history"""
        self.request_history.clear()
        self.withdrawal_history.clear()


# Global instance for test patching
kraken_fake = KrakenFakeProvider()