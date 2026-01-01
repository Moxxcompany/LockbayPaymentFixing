"""
FastForex Service Fake Provider
Comprehensive test double for FastForex exchange rate service
"""

import asyncio
import logging
from decimal import Decimal
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class FastForexFakeProvider:
    """
    Comprehensive fake provider for FastForex exchange rate service
    
    Features:
    - Deterministic exchange rates based on currency patterns
    - Configurable failure scenarios  
    - Rate caching simulation
    - Historical rate tracking
    """
    
    def __init__(self):
        self.api_key = "test_fastforex_api_key"
        self.base_url = "https://api.fastforex.io"
        
        # Default exchange rates (deterministic for testing)
        self.base_rates = {
            "BTC": Decimal("45000.00"),
            "ETH": Decimal("3000.00"), 
            "LTC": Decimal("150.00"),
            "DOGE": Decimal("0.08"),
            "BCH": Decimal("250.00"),
            "TRX": Decimal("0.10"),
            "USDT": Decimal("1.00"),
            "USD": Decimal("1.00"),
            "NGN": Decimal("0.00067"),  # 1 NGN = 0.00067 USD (1500 NGN per USD)
        }
        
        # State management
        self.failure_mode = None  # None, "api_timeout", "auth_failed", "rate_limit", "invalid_currency"
        self.request_history = []
        self.rate_overrides = {}  # Manual rate overrides for testing
        
        # Simulate rate volatility (small random variations)
        self.volatility_enabled = False
        self.volatility_percentage = Decimal("0.05")  # 5% max variation
        
    def reset_state(self):
        """Reset fake provider state for test isolation"""
        self.failure_mode = None
        self.request_history.clear()
        self.rate_overrides.clear()
        self.volatility_enabled = False
        
    def set_failure_mode(self, mode: Optional[str]):
        """Configure failure scenarios"""
        self.failure_mode = mode
        
    def set_rate_override(self, currency: str, rate: Decimal):
        """Override rate for specific currency"""
        self.rate_overrides[currency] = rate
        
    def enable_volatility(self, enabled: bool = True, percentage: Decimal = Decimal("0.05")):
        """Enable/disable rate volatility simulation"""
        self.volatility_enabled = enabled
        self.volatility_percentage = percentage
    
    async def get_crypto_to_usd_rate(self, crypto_symbol: str) -> Optional[float]:
        """
        Fake crypto to USD rate retrieval
        Returns deterministic rates with optional volatility
        """
        self.request_history.append({
            "method": "get_crypto_to_usd_rate",
            "crypto_symbol": crypto_symbol,
            "timestamp": datetime.now(timezone.utc)
        })
        
        # Simulate failure modes
        if self.failure_mode == "api_timeout":
            raise Exception("FastForex timeout")
        elif self.failure_mode == "auth_failed":
            raise Exception("Invalid API key")
        elif self.failure_mode == "rate_limit":
            raise Exception("Rate limit exceeded")
        elif self.failure_mode == "invalid_currency":
            raise Exception(f"Currency not supported: {crypto_symbol}")
            
        # Map Kraken symbols to standard format
        symbol_map = {
            "XETH": "ETH", "XXBT": "BTC", "XLTC": "LTC", "XXDG": "DOGE",
            "XBCH": "BCH", "XTRX": "TRX", "XUSDT": "USDT", "ZUSD": "USD"
        }
        mapped_symbol = symbol_map.get(crypto_symbol, crypto_symbol)
        
        # Check for rate override
        if mapped_symbol in self.rate_overrides:
            rate = self.rate_overrides[mapped_symbol]
        else:
            # Get base rate
            if mapped_symbol not in self.base_rates:
                raise Exception(f"Currency not supported: {mapped_symbol}")
            rate = self.base_rates[mapped_symbol]
        
        # Apply volatility if enabled
        if self.volatility_enabled and mapped_symbol != "USD":
            import random
            variation = Decimal(random.uniform(-float(self.volatility_percentage), float(self.volatility_percentage)))
            rate = rate * (Decimal("1.0") + variation)
            
        return float(rate)
    
    async def get_live_rate(self, base_currency: str, target_currency: str) -> Dict[str, Any]:
        """
        Fake live rate retrieval for currency pairs
        Supports USD-NGN and other common pairs
        """
        self.request_history.append({
            "method": "get_live_rate",
            "base_currency": base_currency,
            "target_currency": target_currency,
            "timestamp": datetime.now(timezone.utc)
        })
        
        # Simulate failure modes
        if self.failure_mode == "api_timeout":
            raise Exception("FastForex timeout")
        elif self.failure_mode == "auth_failed":
            raise Exception("Invalid API key")
        elif self.failure_mode == "rate_limit":
            raise Exception("Rate limit exceeded")
            
        # Handle USD-NGN rate (most common for the platform)
        if base_currency == "USD" and target_currency == "NGN":
            usd_ngn_rate = Decimal("1500.00")  # Default 1500 NGN per USD
            if "USD_NGN" in self.rate_overrides:
                usd_ngn_rate = self.rate_overrides["USD_NGN"]
            elif self.volatility_enabled:
                import random
                variation = Decimal(random.uniform(-0.02, 0.02))  # 2% variation
                usd_ngn_rate = usd_ngn_rate * (Decimal("1.0") + variation)
                
            return {
                "success": True,
                "rate": usd_ngn_rate,
                "source": "fastforex", 
                "timestamp": datetime.now(timezone.utc),
                "base_currency": base_currency,
                "target_currency": target_currency
            }
        
        # Handle NGN-USD rate (reverse)
        elif base_currency == "NGN" and target_currency == "USD":
            ngn_usd_rate = Decimal("0.00067")  # 1 NGN = 0.00067 USD
            if "NGN_USD" in self.rate_overrides:
                ngn_usd_rate = self.rate_overrides["NGN_USD"]
            elif self.volatility_enabled:
                import random
                variation = Decimal(random.uniform(-0.02, 0.02))
                ngn_usd_rate = ngn_usd_rate * (Decimal("1.0") + variation)
                
            return {
                "success": True,
                "rate": ngn_usd_rate,
                "source": "fastforex",
                "timestamp": datetime.now(timezone.utc),
                "base_currency": base_currency,
                "target_currency": target_currency
            }
        
        # Handle crypto to fiat conversions
        elif base_currency in self.base_rates:
            crypto_usd_rate = await self.get_crypto_to_usd_rate(base_currency)
            
            if target_currency == "USD":
                rate = Decimal(str(crypto_usd_rate))
            elif target_currency == "NGN":
                # Convert via USD
                usd_ngn_rate = Decimal("1500.00")
                if "USD_NGN" in self.rate_overrides:
                    usd_ngn_rate = self.rate_overrides["USD_NGN"]
                rate = Decimal(str(crypto_usd_rate)) * usd_ngn_rate
            else:
                raise Exception(f"Unsupported target currency: {target_currency}")
                
            return {
                "success": True,
                "rate": rate,
                "source": "fastforex",
                "timestamp": datetime.now(timezone.utc), 
                "base_currency": base_currency,
                "target_currency": target_currency
            }
        
        # Unsupported currency pair
        else:
            raise Exception(f"Unsupported currency pair: {base_currency}-{target_currency}")
    
    async def get_multiple_rates(self, base_currency: str, target_currencies: List[str]) -> Dict[str, Any]:
        """
        Fake multiple rate retrieval
        Returns rates for multiple target currencies
        """
        self.request_history.append({
            "method": "get_multiple_rates",
            "base_currency": base_currency,
            "target_currencies": target_currencies,
            "timestamp": datetime.now(timezone.utc)
        })
        
        if self.failure_mode == "api_timeout":
            raise Exception("FastForex timeout")
        elif self.failure_mode == "auth_failed":
            raise Exception("Invalid API key")
            
        rates = {}
        for target_currency in target_currencies:
            try:
                rate_result = await self.get_live_rate(base_currency, target_currency)
                rates[target_currency] = rate_result["rate"]
            except Exception as e:
                rates[target_currency] = None
                logger.warning(f"Failed to get rate for {base_currency}-{target_currency}: {e}")
        
        return {
            "success": True,
            "rates": rates,
            "base_currency": base_currency,
            "timestamp": datetime.now(timezone.utc)
        }
    
    def get_request_history(self) -> List[Dict[str, Any]]:
        """Get history of all requests made to fake provider"""
        return self.request_history.copy()
        
    def clear_history(self):
        """Clear request history"""
        self.request_history.clear()


# Global instance for test patching
fastforex_fake = FastForexFakeProvider()