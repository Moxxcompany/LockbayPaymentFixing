"""
Unified Fee Service - Centralized fee calculation for all cashout methods
Resolves fee policy inconsistencies across the platform
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any
from config import Config

logger = logging.getLogger(__name__)


class UnifiedFeeService:
    """Centralized fee calculation service for all cashout methods"""

    # Platform fee rates (configurable)
    PLATFORM_FEE_PERCENTAGE = Decimal(
        str(getattr(Config, "CASHOUT_PLATFORM_FEE_PERCENT", 0.005))
    )  # 0.5% (0.005 as decimal)

    # Network-specific fees (in USD equivalent)
    NETWORK_FEES = {
        "BTC": Decimal("5.00"),
        "ETH": Decimal("3.00"),
        "USDT-ERC20": Decimal("2.50"),
        "USDT-TRC20": Decimal("1.00"),
        "LTC": Decimal("0.50"),
        "DOGE": Decimal("1.00"),
        "TRX": Decimal("1.50"),
        # "XMR": Decimal("2.00"),  # Removed: FastForex API doesn't support XMR
        "NGN_BANK": Decimal("0.00"),  # Platform absorbs NGN bank fees
    }

    # Minimum fees (to prevent dust)
    MIN_PLATFORM_FEE = Decimal("0.10")
    MIN_CASHOUT_AMOUNT = Decimal(str(getattr(Config, "MIN_CASHOUT_AMOUNT", 5.0)))

    @classmethod
    async def calculate_cashout_fees(
        cls, amount: Decimal, currency: str, cashout_type: str, network: str = None
    ) -> Dict[str, Decimal]:
        """
        Calculate all fees for a cashout
        Returns: {
            'platform_fee': Decimal,
            'network_fee': Decimal,
            'total_fee': Decimal,
            'net_amount': Decimal,
            'fee_policy': str
        }
        """
        try:
            # Validate minimum amount
            if amount < cls.MIN_CASHOUT_AMOUNT:
                raise ValueError(
                    f"Minimum cashout amount is ${cls.MIN_CASHOUT_AMOUNT}"
                )

            # Calculate platform fee
            platform_fee = (amount * cls.PLATFORM_FEE_PERCENTAGE).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            # Apply minimum platform fee
            if platform_fee < cls.MIN_PLATFORM_FEE:
                platform_fee = cls.MIN_PLATFORM_FEE

            # Determine network fee based on cashout type
            network_fee = Decimal("0.00")
            fee_policy = "platform_charges"

            if cashout_type == "crypto":
                # Get network fee based on currency/network
                fee_key = network if network else currency
                network_fee = cls.NETWORK_FEES.get(
                    fee_key, cls.NETWORK_FEES.get(currency, Decimal("2.00"))
                )

            elif cashout_type == "ngn_bank":
                # Platform absorbs NGN bank transfer fees for competitive advantage
                network_fee = Decimal("0.00")
                fee_policy = "platform_absorbs_network_fees"

            # Calculate totals using "fees on top" model
            total_fee = platform_fee + network_fee
            total_cost = amount + total_fee  # User pays: requested amount + fees
            net_amount = amount  # User receives: exactly what they requested

            # Validate amounts are positive
            if amount <= 0:
                raise ValueError(
                    f"Cashout amount must be positive: ${amount}"
                )

            fee_breakdown = {
                "platform_fee": platform_fee,
                "network_fee": network_fee,
                "total_fee": total_fee,
                "total_cost": total_cost,  # Amount debited from wallet
                "net_amount": net_amount,  # Amount user receives (same as requested)
                "fee_policy": fee_policy,
                "breakdown": {
                    "platform_fee_percent": float(cls.PLATFORM_FEE_PERCENTAGE),
                    "network_fee_usd": float(network_fee),
                    "total_fee_percent": float((total_fee / amount) * 100),
                },
            }

            logger.info(
                f"Calculated fees for {cashout_type} cashout: "
                f"Requested: ${amount}, Platform: ${platform_fee}, "
                f"Network: ${network_fee}, Total Cost: ${total_cost}"
            )

            return fee_breakdown

        except Exception as e:
            logger.error(f"Error calculating cashout fees: {e}")
            raise ValueError(f"Fee calculation failed: {str(e)}")

    @classmethod
    def get_fee_preview(
        cls, amount: Decimal, currency: str, cashout_type: str, network: str = None
    ) -> Dict[str, Any]:
        """
        Get fee preview for UI display (synchronous version)
        Returns user-friendly fee breakdown
        """
        try:
            # Calculate platform fee
            platform_fee = (amount * cls.PLATFORM_FEE_PERCENTAGE).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            if platform_fee < cls.MIN_PLATFORM_FEE:
                platform_fee = cls.MIN_PLATFORM_FEE

            # Get network fee
            network_fee = Decimal("0.00")
            network_fee_display = "Free"

            if cashout_type == "crypto":
                fee_key = network if network else currency
                network_fee = cls.NETWORK_FEES.get(
                    fee_key, cls.NETWORK_FEES.get(currency, Decimal("2.00"))
                )
                network_fee_display = f"${network_fee}"

            elif cashout_type == "ngn_bank":
                network_fee_display = "Absorbed by platform"

            total_fee = platform_fee + network_fee
            total_cost = amount + total_fee  # User pays: requested amount + fees
            net_amount = amount  # User receives: exactly what they requested

            return {
                "valid": amount > 0,  # Validate requested amount, not net
                "gross_amount": f"${amount}",
                "platform_fee": f"${platform_fee}",
                "network_fee": network_fee_display,
                "total_fee": f"${total_fee}",
                "total_cost": f"${total_cost}",  # Amount debited from wallet
                "net_amount": f"${net_amount}",  # Amount user receives
                "fee_percentage": f"{float((total_fee / amount) * 100):.1f}%",
                "warnings": [],
            }

        except Exception as e:
            return {"valid": False, "error": str(e)}

    @classmethod
    def get_network_requirements(cls, currency: str) -> Dict[str, Any]:
        """Get network-specific requirements (memo, tag, etc.)"""

        # Network-specific requirements for memo/tag
        NETWORK_REQUIREMENTS = {
            "XRP": {
                "requires_memo": True,
                "memo_name": "Destination Tag",
                "memo_description": "Required for XRP transactions",
                "address_format": r"^r[1-9A-HJ-NP-Za-km-z]{25,34}$",
            },
            "XLM": {
                "requires_memo": True,
                "memo_name": "Memo",
                "memo_description": "Required for Stellar transactions",
                "address_format": r"^G[A-Z0-9]{55}$",
            },
            "BNB": {
                "requires_memo": True,
                "memo_name": "Memo",
                "memo_description": "Required for Binance Chain transactions",
                "address_format": r"^bnb[a-z0-9]{39}$",
            },
            "EOS": {
                "requires_memo": True,
                "memo_name": "Memo",
                "memo_description": "Required for EOS transactions",
                "address_format": r"^[a-z1-5.]{1,12}$",
            },
        }

        return NETWORK_REQUIREMENTS.get(
            currency,
            {
                "requires_memo": False,
                "memo_name": None,
                "memo_description": None,
                "address_format": None,
            },
        )

    @classmethod
    def validate_cashout_address(
        cls, address: str, currency: str, memo: str = None
    ) -> Dict[str, Any]:
        """Validate cashout address with network-specific rules"""

        requirements = cls.get_network_requirements(currency)

        # Basic validation
        if not address or len(address.strip()) < 10:
            return {"valid": False, "error": "Invalid address format"}

        # Check memo requirement
        if requirements.get("requires_memo") and not memo:
            return {
                "valid": False,
                "error": f"{requirements['memo_name']} is required for {currency} transactions",
            }

        # Format validation (if pattern defined)
        if requirements.get("address_format"):
            import re

            if not re.match(requirements["address_format"], address):
                return {"valid": False, "error": f"Invalid {currency} address format"}

        return {
            "valid": True,
            "requires_memo": requirements.get("requires_memo", False),
            "memo_name": requirements.get("memo_name"),
        }
