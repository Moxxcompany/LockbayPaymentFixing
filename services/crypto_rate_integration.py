"""
Crypto Rate Integration Service
Integrates forex rates with markup for monetization
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CryptoRateIntegration:
    """Service for integrating forex rates with markup monetization"""

    def __init__(self):
        pass

    async def get_rate_with_markup(
        self, crypto_currency: str, usd_amount: Optional[Decimal] = None
    ) -> Dict:
        """Get cryptocurrency rate with markup applied for monetization"""
        try:
            from services.forex_service import forex_service
            from services.exchange_markup_service import exchange_markup_service

            # Get base rate from FastForex
            base_rate = await forex_service.get_current_rate(crypto_currency)
            if not base_rate:
                return {
                    "success": False,
                    "error": f"Unable to get rate for {crypto_currency}",
                    "final_rate": None,
                }

            # Apply markup for monetization
            markup_info = exchange_markup_service.apply_markup(
                base_rate, crypto_currency, usd_amount
            )

            return {
                "success": True,
                "base_rate": base_rate,
                "final_rate": markup_info["final_rate"],
                "markup_applied": markup_info["markup_applied"],
                "markup_percentage": markup_info["markup_percentage"],
                "markup_model": markup_info["markup_model"],
                "revenue_usd": markup_info.get("revenue_usd", Decimal("0")),
                "tier_applied": markup_info.get("tier_applied"),
                "currency": crypto_currency,
                "usd_amount": usd_amount,
                "timestamp": datetime.utcnow(),
            }

        except Exception as e:
            logger.error(f"Error getting rate with markup for {crypto_currency}: {e}")
            return {"success": False, "error": str(e), "final_rate": None}

    async def create_rate_lock_with_markup(
        self, escrow_id: str, usd_amount: Decimal, crypto_currency: str
    ) -> Dict:
        """Create rate lock with markup applied"""
        try:
            from services.fastforex_service import fastforex_service as forex_service

            # Get rate with markup
            rate_info = await self.get_rate_with_markup(crypto_currency, usd_amount)
            if not rate_info["success"]:
                return rate_info

            final_rate = rate_info["final_rate"]

            # Create rate lock with the marked-up rate
            lock_result = await forex_service.create_rate_lock(
                escrow_id, usd_amount, crypto_currency, final_rate
            )

            if lock_result["success"]:
                # Add markup information to lock result
                lock_result.update(
                    {
                        "base_rate": rate_info["base_rate"],
                        "markup_applied": rate_info["markup_applied"],
                        "markup_percentage": rate_info["markup_percentage"],
                        "markup_model": rate_info["markup_model"],
                        "revenue_usd": rate_info["revenue_usd"],
                        "tier_applied": rate_info.get("tier_applied"),
                    }
                )

            return lock_result

        except Exception as e:
            logger.error(f"Error creating rate lock with markup for {escrow_id}: {e}")
            return {"success": False, "error": str(e)}

    def calculate_crypto_amount_with_markup(
        self, usd_amount: Decimal, crypto_currency: str, final_rate: Decimal
    ) -> Dict:
        """Calculate crypto amount considering markup"""
        try:
            # Calculate crypto amount based on marked-up rate
            crypto_amount = usd_amount / final_rate

            return {
                "success": True,
                "crypto_amount": crypto_amount.quantize(
                    Decimal("0.00000001"), rounding=ROUND_HALF_UP
                ),
                "usd_amount": usd_amount,
                "rate_used": final_rate,
                "currency": crypto_currency,
            }

        except Exception as e:
            logger.error(f"Error calculating crypto amount with markup: {e}")
            return {"success": False, "error": str(e)}


# Global service instance
crypto_rate_integration = CryptoRateIntegration()
