"""
Exchange Rate Markup Service
Implements configurable markup models for monetizing cryptocurrency exchange rates
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict
from enum import Enum

from config import Config

logger = logging.getLogger(__name__)


class MarkupModel(Enum):
    """Exchange rate markup models"""

    PERCENTAGE = "percentage"  # Fixed percentage markup
    SPREAD = "spread"  # Bid/ask spread model
    TIERED = "tiered"  # Volume-based tiered markup
    FLAT_FEE = "flat_fee"  # Fixed fee markup
    HYBRID = "hybrid"  # Combination of percentage + flat fee


class ExchangeMarkupService:
    """Service for applying configurable markup to exchange rates"""

    def __init__(self):
        # Load configuration from environment
        self.markup_enabled = Config.EXCHANGE_MARKUP_ENABLED
        self.markup_model = MarkupModel(Config.EXCHANGE_MARKUP_MODEL)
        self.default_markup_percentage = Decimal(str(Config.DEFAULT_MARKUP_PERCENTAGE))
        self.flat_fee_usd = Decimal(str(Config.FLAT_FEE_USD))

        # Tiered markup configuration
        self.tier_thresholds = self._load_tier_config()

        # Currency-specific markups
        self.currency_markups = self._load_currency_markups()

        logger.info(
            f"Exchange markup service initialized: model={self.markup_model.value}, enabled={self.markup_enabled}"
        )

    def _load_tier_config(self) -> Dict[str, Decimal]:
        """Load tiered markup configuration"""
        return {
            "tier_1_threshold": Decimal(str(Config.TIER_1_THRESHOLD)),  # $0-100
            "tier_1_markup": Decimal(str(Config.TIER_1_MARKUP)),  # 3%
            "tier_2_threshold": Decimal(str(Config.TIER_2_THRESHOLD)),  # $100-500
            "tier_2_markup": Decimal(str(Config.TIER_2_MARKUP)),  # 2%
            "tier_3_threshold": Decimal(str(Config.TIER_3_THRESHOLD)),  # $500-1000
            "tier_3_markup": Decimal(str(Config.TIER_3_MARKUP)),  # 1.5%
            "tier_4_markup": Decimal(str(Config.TIER_4_MARKUP)),  # $1000+ = 1%
        }

    def _load_currency_markups(self) -> Dict[str, Decimal]:
        """Load unified crypto markup for all currencies (LockBay unified system)"""
        # Use unified LOCKBAY_CRYPTO_EXCHANGE_MARKUP for all cryptocurrencies
        unified_markup = Decimal(str(Config.LOCKBAY_CRYPTO_EXCHANGE_MARKUP))
        return {
            "BTC": unified_markup,
            "ETH": unified_markup,
            "USDT": Decimal("0.0"),  # No markup for USDT (already USD equivalent)
            "USDT-TRC20": Decimal("0.0"),  # No markup for USDT-TRC20
            "USDT-ERC20": Decimal("0.0"),  # No markup for USDT-ERC20
            "LTC": unified_markup,
            "DOGE": unified_markup,
            "BCH": unified_markup,
            "BNB": unified_markup,
            "TRX": unified_markup,
        }

    def apply_markup(
        self,
        base_rate: Decimal,
        crypto_currency: str,
        usd_amount: Decimal = None,
        operation: str = "sell_crypto",
    ) -> Dict:
        """
        Apply unified markup system to exchange rate

        Args:
            base_rate: Raw exchange rate from API
            crypto_currency: Currency symbol (BTC, ETH, etc.)
            usd_amount: Transaction amount in USD (for tiered model)
            operation: 'buy_crypto' or 'sell_crypto'

        Returns:
            Dict with markup details and final rate
        """
        try:
            if not self.markup_enabled:
                return {
                    "final_rate": base_rate,
                    "markup_applied": Decimal("0"),
                    "markup_percentage": Decimal("0"),
                    "markup_model": "disabled",
                    "base_rate": base_rate,
                }

            # Use unified markup system
            from utils.markup_utils import get_effective_rate, calculate_markup_amount

            markup_info = self._calculate_markup(base_rate, crypto_currency, usd_amount)
            markup_percentage = markup_info["markup_percentage"] / 100

            # Apply unified markup based on operation
            final_rate = get_effective_rate(base_rate, markup_percentage, operation)
            markup_applied = calculate_markup_amount(base_rate, markup_percentage)

            return {
                "final_rate": final_rate.quantize(
                    Decimal("0.00000001"), rounding=ROUND_HALF_UP
                ),
                "markup_applied": markup_applied.quantize(
                    Decimal("0.00000001"), rounding=ROUND_HALF_UP
                ),
                "markup_percentage": markup_info["markup_percentage"],
                "markup_model": "unified",
                "base_rate": base_rate,
                "revenue_usd": markup_info.get("revenue_usd", Decimal("0")),
                "tier_applied": markup_info.get("tier_applied"),
                "currency_override": markup_info.get("currency_override", False),
                "operation": operation,
            }

        except Exception as e:
            logger.error(f"Error applying markup to {crypto_currency} rate: {e}")
            # Return original rate on error
            return {
                "final_rate": base_rate,
                "markup_applied": Decimal("0"),
                "markup_percentage": Decimal("0"),
                "markup_model": "error",
                "base_rate": base_rate,
                "error": str(e),
            }

    def _calculate_markup(
        self, base_rate: Decimal, crypto_currency: str, usd_amount: Decimal = None
    ) -> Dict:
        """Calculate markup based on selected model"""

        if self.markup_model == MarkupModel.PERCENTAGE:
            return self._calculate_percentage_markup(base_rate, crypto_currency)

        elif self.markup_model == MarkupModel.SPREAD:
            return self._calculate_spread_markup(base_rate, crypto_currency)

        elif self.markup_model == MarkupModel.TIERED:
            return self._calculate_tiered_markup(base_rate, crypto_currency, usd_amount)

        elif self.markup_model == MarkupModel.FLAT_FEE:
            return self._calculate_flat_fee_markup(base_rate, crypto_currency)

        elif self.markup_model == MarkupModel.HYBRID:
            return self._calculate_hybrid_markup(base_rate, crypto_currency, usd_amount)

        else:
            # Default to percentage model
            return self._calculate_percentage_markup(base_rate, crypto_currency)

    def _calculate_percentage_markup(
        self, base_rate: Decimal, crypto_currency: str
    ) -> Dict:
        """Calculate fixed percentage markup"""
        # Check for currency-specific override
        markup_percentage = self.currency_markups.get(
            crypto_currency, self.default_markup_percentage
        )

        markup_amount = base_rate * (markup_percentage / Decimal("100"))

        return {
            "markup_amount": markup_amount,
            "markup_percentage": markup_percentage,
            "currency_override": crypto_currency in self.currency_markups,
        }

    def _calculate_spread_markup(
        self, base_rate: Decimal, crypto_currency: str
    ) -> Dict:
        """Calculate bid/ask spread markup (simulates exchange spread)"""
        # Spread model: create artificial spread around market rate
        spread_percentage = self.currency_markups.get(
            crypto_currency, self.default_markup_percentage
        )

        # For buying crypto: user pays above market rate
        markup_amount = base_rate * (spread_percentage / Decimal("200"))  # Half spread

        return {
            "markup_amount": markup_amount,
            "markup_percentage": spread_percentage / Decimal("2"),  # Effective markup
            "spread_model": True,
        }

    def _calculate_tiered_markup(
        self, base_rate: Decimal, crypto_currency: str, usd_amount: Decimal
    ) -> Dict:
        """Calculate volume-based tiered markup"""
        if not usd_amount:
            # Fallback to default if no amount provided
            return self._calculate_percentage_markup(base_rate, crypto_currency)

        # Determine tier based on USD amount
        if usd_amount <= self.tier_thresholds["tier_1_threshold"]:
            markup_percentage = self.tier_thresholds["tier_1_markup"]
            tier = "tier_1"
        elif usd_amount <= self.tier_thresholds["tier_2_threshold"]:
            markup_percentage = self.tier_thresholds["tier_2_markup"]
            tier = "tier_2"
        elif usd_amount <= self.tier_thresholds["tier_3_threshold"]:
            markup_percentage = self.tier_thresholds["tier_3_markup"]
            tier = "tier_3"
        else:
            markup_percentage = self.tier_thresholds["tier_4_markup"]
            tier = "tier_4"

        markup_amount = base_rate * (markup_percentage / Decimal("100"))

        return {
            "markup_amount": markup_amount,
            "markup_percentage": markup_percentage,
            "tier_applied": tier,
            "usd_amount": usd_amount,
        }

    def _calculate_flat_fee_markup(
        self, base_rate: Decimal, crypto_currency: str
    ) -> Dict:
        """Calculate flat fee markup in USD equivalent"""
        # Convert flat fee to crypto rate reduction
        markup_amount = self.flat_fee_usd  # Flat fee in USD
        markup_percentage = (markup_amount / base_rate) * Decimal("100")

        return {
            "markup_amount": markup_amount,
            "markup_percentage": markup_percentage,
            "flat_fee_usd": self.flat_fee_usd,
        }

    def _calculate_hybrid_markup(
        self, base_rate: Decimal, crypto_currency: str, usd_amount: Decimal
    ) -> Dict:
        """Calculate hybrid markup (percentage + flat fee)"""
        # Percentage component
        percentage_markup = self.currency_markups.get(
            crypto_currency, self.default_markup_percentage
        )
        percentage_amount = base_rate * (percentage_markup / Decimal("100"))

        # Flat fee component
        flat_fee_amount = self.flat_fee_usd

        total_markup = percentage_amount + flat_fee_amount
        effective_percentage = (total_markup / base_rate) * Decimal("100")

        return {
            "markup_amount": total_markup,
            "markup_percentage": effective_percentage,
            "percentage_component": percentage_amount,
            "flat_fee_component": flat_fee_amount,
            "hybrid_model": True,
        }

    def calculate_revenue(self, markup_info: Dict, crypto_amount: Decimal) -> Decimal:
        """Calculate expected revenue from markup"""
        try:
            markup_per_unit = markup_info.get("markup_applied", Decimal("0"))
            total_revenue = markup_per_unit * crypto_amount
            return total_revenue.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except Exception as e:
            logger.error(f"Error calculating revenue: {e}")
            return Decimal("0")

    def get_markup_summary(
        self, crypto_currency: str, usd_amount: Decimal = None
    ) -> Dict:
        """Get markup information without applying to a specific rate"""
        try:
            sample_rate = Decimal("50000")  # Sample rate for calculation
            markup_info = self._calculate_markup(
                sample_rate, crypto_currency, usd_amount
            )

            return {
                "markup_enabled": self.markup_enabled,
                "markup_model": self.markup_model.value,
                "currency": crypto_currency,
                "markup_percentage": markup_info.get("markup_percentage", Decimal("0")),
                "tier_applied": markup_info.get("tier_applied"),
                "currency_override": markup_info.get("currency_override", False),
                "usd_amount": usd_amount,
            }
        except Exception as e:
            logger.error(f"Error getting markup summary: {e}")
            return {"error": str(e)}

    def get_revenue_projection(
        self, daily_volume_usd: Decimal, currency_breakdown: Dict[str, Decimal]
    ) -> Dict:
        """Project daily/monthly revenue based on volume"""
        try:
            daily_revenue = Decimal("0")
            currency_revenues = {}

            for currency, volume in currency_breakdown.items():
                sample_rate = Decimal("50000")  # Sample for calculation
                markup_info = self._calculate_markup(sample_rate, currency, volume)
                markup_percentage = markup_info.get("markup_percentage", Decimal("0"))

                currency_revenue = volume * (markup_percentage / Decimal("100"))
                currency_revenues[currency] = currency_revenue
                daily_revenue += currency_revenue

            monthly_revenue = daily_revenue * Decimal("30")
            annual_revenue = daily_revenue * Decimal("365")

            return {
                "daily_revenue": daily_revenue.quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                ),
                "monthly_revenue": monthly_revenue.quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                ),
                "annual_revenue": annual_revenue.quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                ),
                "currency_breakdown": currency_revenues,
                "total_volume": daily_volume_usd,
            }
        except Exception as e:
            logger.error(f"Error calculating revenue projection: {e}")
            return {"error": str(e)}


# Global service instance
exchange_markup_service = ExchangeMarkupService()
