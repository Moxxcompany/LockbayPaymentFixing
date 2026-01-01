"""
Unified Markup System
Simple, consistent markup application across all exchange operations
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Union
import logging

logger = logging.getLogger(__name__)


def apply_markup(
    base_rate: Union[float, Decimal], margin: Union[float, Decimal] = 0.05
) -> Decimal:
    """
    Apply markup to base rate
    Args:
        base_rate: Original exchange rate
        margin: Markup percentage (default 5%)
    Returns:
        Rate with markup applied
    """
    base_rate = Decimal(str(base_rate))
    margin = Decimal(str(margin))

    marked_up_rate = base_rate * (Decimal("1") + margin)
    return marked_up_rate.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


def convert_to_crypto(
    fiat_amount: Union[float, Decimal],
    base_rate: Union[float, Decimal],
    margin: Union[float, Decimal] = 0.05,
) -> Decimal:
    """
    Convert fiat to crypto with markup
    Args:
        fiat_amount: Amount in fiat currency
        base_rate: Base crypto-to-fiat rate
        margin: Markup percentage (default 5%)
    Returns:
        Crypto amount (user gets less crypto due to markup)
    """
    fiat_amount = Decimal(str(fiat_amount))
    rate = apply_markup(base_rate, margin)

    crypto_amount = fiat_amount / rate
    return crypto_amount.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


def convert_to_fiat(
    crypto_amount: Union[float, Decimal],
    base_rate: Union[float, Decimal],
    margin: Union[float, Decimal] = 0.05,
) -> Decimal:
    """
    Convert crypto to fiat with markup
    Args:
        crypto_amount: Amount in cryptocurrency
        base_rate: Base crypto-to-fiat rate
        margin: Markup percentage (default 5%)
    Returns:
        Fiat amount (user gets less fiat due to markup)
    """
    crypto_amount = Decimal(str(crypto_amount))
    base_rate = Decimal(str(base_rate))
    margin = Decimal(str(margin))

    # For selling crypto to fiat, user gets less fiat
    # Apply inverse markup (divide by (1 + margin))
    effective_rate = base_rate / (Decimal("1") + margin)

    fiat_amount = crypto_amount * effective_rate
    return fiat_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_effective_rate(
    base_rate: Union[float, Decimal], margin: Union[float, Decimal], operation: str
) -> Decimal:
    """
    Get effective rate for different operations
    Args:
        base_rate: Original rate
        margin: Markup percentage
        operation: 'buy_crypto' or 'sell_crypto'
    Returns:
        Effective rate with markup
    """
    base_rate = Decimal(str(base_rate))
    margin = Decimal(str(margin))

    if operation == "buy_crypto":
        # User pays more fiat for crypto
        return apply_markup(base_rate, margin)
    elif operation == "sell_crypto":
        # User gets less fiat for crypto
        return base_rate / (Decimal("1") + margin)
    else:
        return base_rate


def calculate_markup_amount(
    amount: Union[float, Decimal], margin: Union[float, Decimal] = 0.05
) -> Decimal:
    """
    Calculate the markup amount in the same currency
    Args:
        amount: Base amount
        margin: Markup percentage
    Returns:
        Markup amount
    """
    amount = Decimal(str(amount))
    margin = Decimal(str(margin))

    markup_amount = amount * margin
    return markup_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
