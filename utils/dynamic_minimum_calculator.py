"""
Dynamic minimum amount calculator for crypto cashouts
Prevents user errors by showing real-time minimums
"""

import logging
from decimal import Decimal
from typing import Dict, Optional
from services.crypto import CryptoServiceAtomic
from config import Config

logger = logging.getLogger(__name__)

class DynamicMinimumCalculator:
    """Calculate dynamic minimum amounts for crypto cashouts"""
    
    @classmethod
    async def get_crypto_minimum_usd(cls, crypto_type: str) -> Optional[Decimal]:
        """Get real-time USD minimum for a cryptocurrency"""
        try:
            # Get current crypto price from FastForex
            crypto_price = await CryptoServiceAtomic.get_real_time_exchange_rate(crypto_type)
            crypto_price_decimal = Decimal(str(crypto_price))
            
            # Get Kraken minimum in crypto units
            min_crypto_amount = Config.KRAKEN_MINIMUM_WITHDRAWALS_CRYPTO.get(
                crypto_type, Decimal('0.00001')
            )
            
            # Calculate USD equivalent
            min_usd = min_crypto_amount * crypto_price_decimal
            
            # Round up to nearest $0.50 for user-friendly amounts
            min_usd_rounded = (min_usd + Decimal('0.49')).quantize(Decimal('0.50'))
            
            logger.info(f"💰 {crypto_type} minimum: {min_crypto_amount} = ${min_usd_rounded}")
            return min_usd_rounded
            
        except Exception as e:
            logger.error(f"Error calculating minimum for {crypto_type}: {e}")
            return None
    
    @classmethod
    async def get_suggested_amounts(cls, crypto_type: str) -> Dict[str, Decimal]:
        """Get suggested amounts including minimum and popular values"""
        try:
            minimum_usd = await cls.get_crypto_minimum_usd(crypto_type)
            
            if not minimum_usd:
                # Fallback amounts if API fails
                return {
                    "minimum": Decimal("25.00"),
                    "small": Decimal("50.00"), 
                    "medium": Decimal("100.00"),
                    "large": Decimal("250.00")
                }
            
            # Generate user-friendly suggested amounts
            suggestions = {
                "minimum": minimum_usd,
                "small": minimum_usd * Decimal("2"),      # 2x minimum
                "medium": minimum_usd * Decimal("4"),     # 4x minimum  
                "large": minimum_usd * Decimal("10")      # 10x minimum
            }
            
            # Ensure reasonable maximums
            for key, value in suggestions.items():
                if value > Decimal("1000"):
                    suggestions[key] = Decimal("1000")
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating suggestions for {crypto_type}: {e}")
            return {
                "minimum": Decimal("25.00"),
                "small": Decimal("50.00"),
                "medium": Decimal("100.00"), 
                "large": Decimal("250.00")
            }
    
    @classmethod
    async def validate_amount_against_minimum(cls, crypto_type: str, amount_usd: Decimal) -> Dict[str, any]:
        """Validate if amount meets minimum requirements"""
        try:
            minimum_usd = await cls.get_crypto_minimum_usd(crypto_type)
            
            if not minimum_usd:
                return {"valid": True, "message": ""}
            
            if amount_usd >= minimum_usd:
                return {"valid": True, "message": ""}
            else:
                shortage = minimum_usd - amount_usd
                return {
                    "valid": False,
                    "minimum_required": minimum_usd,
                    "shortage": shortage,
                    "message": f"Minimum ${minimum_usd} required for {crypto_type}. You need ${shortage} more."
                }
                
        except Exception as e:
            logger.error(f"Error validating amount for {crypto_type}: {e}")
            return {"valid": True, "message": ""}  # Allow on error