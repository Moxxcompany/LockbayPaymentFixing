#!/usr/bin/env python3
"""
Decimal Precision Utilities for Financial Calculations
Enforces consistent Decimal usage across all monetary operations
"""

import logging
from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import Union, Optional

logger = logging.getLogger(__name__)

# Set global decimal precision for financial calculations
getcontext().prec = 28


class MonetaryDecimal:
    """Enforces Decimal-only monetary operations with proper precision"""

    USD_PRECISION = Decimal("0.01")  # 2 decimal places for USD
    CRYPTO_PRECISION = Decimal("0.00000001")  # 8 decimal places for crypto
    NGN_PRECISION = Decimal("0.01")  # 2 decimal places for NGN
    RATE_PRECISION = Decimal("0.00000001")  # 8 decimal places for exchange rates

    @classmethod
    def to_decimal(
        cls, value: Union[str, int, float, Decimal], context: str = "monetary"
    ) -> Decimal:
        """Safely convert any numeric value to Decimal with validation"""
        if value is None:
            return Decimal("0")

        if isinstance(value, Decimal):
            return value

        try:
            # Convert to string first to avoid float precision issues
            decimal_value = Decimal(str(value))

            # Validate reasonable range for monetary values
            if abs(decimal_value) > Decimal("999999999999"):  # 999 billion limit
                logger.warning(
                    f"Unusually large monetary value: {decimal_value} in context: {context}"
                )

            return decimal_value
        except Exception as e:
            logger.error(
                f"Failed to convert {value} to Decimal in context {context}: {e}"
            )
            return Decimal("0")

    @classmethod
    def quantize_usd(cls, amount: Union[str, int, float, Decimal]) -> Decimal:
        """Quantize amount to USD precision (2 decimal places)"""
        decimal_amount = cls.to_decimal(amount, "USD")
        return decimal_amount.quantize(cls.USD_PRECISION, rounding=ROUND_HALF_UP)

    @classmethod
    def quantize_crypto(cls, amount: Union[str, int, float, Decimal]) -> Decimal:
        """Quantize amount to crypto precision (8 decimal places)"""
        decimal_amount = cls.to_decimal(amount, "crypto")
        return decimal_amount.quantize(cls.CRYPTO_PRECISION, rounding=ROUND_HALF_UP)

    @classmethod
    def quantize_ngn(cls, amount: Union[str, int, float, Decimal]) -> Decimal:
        """Quantize amount to NGN precision (2 decimal places)"""
        decimal_amount = cls.to_decimal(amount, "NGN")
        return decimal_amount.quantize(cls.NGN_PRECISION, rounding=ROUND_HALF_UP)

    @classmethod
    def quantize_rate(cls, rate: Union[str, int, float, Decimal]) -> Decimal:
        """Quantize exchange rate to high precision (8 decimal places)"""
        decimal_rate = cls.to_decimal(rate, "exchange_rate")
        return decimal_rate.quantize(cls.RATE_PRECISION, rounding=ROUND_HALF_UP)

    @classmethod
    def multiply_precise(
        cls,
        amount: Union[str, int, float, Decimal],
        rate: Union[str, int, float, Decimal],
        result_precision: Optional[Decimal] = None,
    ) -> Decimal:
        """Multiply two values with proper precision handling"""
        amount_decimal = cls.to_decimal(amount, "multiply_amount")
        rate_decimal = cls.to_decimal(rate, "multiply_rate")

        result = amount_decimal * rate_decimal

        if result_precision:
            return result.quantize(result_precision, rounding=ROUND_HALF_UP)
        else:
            # Default to USD precision for most monetary calculations
            return result.quantize(cls.USD_PRECISION, rounding=ROUND_HALF_UP)

    @classmethod
    def add_precise(cls, *amounts: Union[str, int, float, Decimal]) -> Decimal:
        """Add multiple amounts with proper precision"""
        total = Decimal("0")
        for amount in amounts:
            amount_decimal = cls.to_decimal(amount, "addition")
            total += amount_decimal

        return cls.quantize_usd(total)

    @classmethod
    def subtract_precise(
        cls,
        minuend: Union[str, int, float, Decimal],
        subtrahend: Union[str, int, float, Decimal],
    ) -> Decimal:
        """Subtract with proper precision"""
        minuend_decimal = cls.to_decimal(minuend, "subtraction_minuend")
        subtrahend_decimal = cls.to_decimal(subtrahend, "subtraction_subtrahend")

        result = minuend_decimal - subtrahend_decimal
        return cls.quantize_usd(result)

    @classmethod
    def divide_precise(
        cls,
        dividend: Union[str, int, float, Decimal],
        divisor: Union[str, int, float, Decimal],
        result_precision: Optional[Decimal] = None,
    ) -> Decimal:
        """Divide with proper precision and zero protection"""
        dividend_decimal = cls.to_decimal(dividend, "divide_dividend")
        divisor_decimal = cls.to_decimal(divisor, "divide_divisor")

        if divisor_decimal == 0:
            logger.error(f"Division by zero attempted: {dividend} / {divisor}")
            return Decimal("0")

        result = dividend_decimal / divisor_decimal

        if result_precision:
            return result.quantize(result_precision, rounding=ROUND_HALF_UP)
        else:
            return result.quantize(cls.RATE_PRECISION, rounding=ROUND_HALF_UP)

    @classmethod
    def compare_amounts(
        cls,
        amount1: Union[str, int, float, Decimal],
        amount2: Union[str, int, float, Decimal],
        tolerance: Union[str, int, float, Decimal] = "0.001",
    ) -> int:
        """Compare two amounts with tolerance. Returns -1, 0, or 1"""
        amount1_decimal = cls.to_decimal(amount1, "compare_amount1")
        amount2_decimal = cls.to_decimal(amount2, "compare_amount2")
        tolerance_decimal = cls.to_decimal(tolerance, "compare_tolerance")

        diff = abs(amount1_decimal - amount2_decimal)

        if diff <= tolerance_decimal:
            return 0  # Equal within tolerance
        elif amount1_decimal > amount2_decimal:
            return 1  # amount1 > amount2
        else:
            return -1  # amount1 < amount2

    @classmethod
    def is_sufficient_balance(
        cls,
        available: Union[str, int, float, Decimal],
        required: Union[str, int, float, Decimal],
        tolerance: Union[str, int, float, Decimal] = "0.01",
    ) -> bool:
        """Check if available balance is sufficient for required amount"""
        available_decimal = cls.to_decimal(available, "balance_available")
        required_decimal = cls.to_decimal(required, "balance_required")
        tolerance_decimal = cls.to_decimal(tolerance, "balance_tolerance")

        # Allow small tolerance for rounding differences
        return available_decimal >= (required_decimal - tolerance_decimal)

    @classmethod
    def format_usd(cls, amount: Union[str, int, float, Decimal]) -> str:
        """Format amount as USD string with proper precision"""
        amount_decimal = cls.quantize_usd(amount)
        return f"${amount_decimal:,.2f}"

    @classmethod
    def format_crypto(
        cls, amount: Union[str, int, float, Decimal], currency: str
    ) -> str:
        """Format amount as crypto string with proper precision"""
        amount_decimal = cls.quantize_crypto(amount)
        # Remove trailing zeros for crypto display
        formatted = f"{amount_decimal:f}".rstrip("0").rstrip(".")
        return f"{formatted} {currency}"

    @classmethod
    def format_ngn(cls, amount: Union[str, int, float, Decimal]) -> str:
        """Format amount as NGN string with proper precision"""
        amount_decimal = cls.quantize_ngn(amount)
        return f"₦{amount_decimal:,.2f}"

    @classmethod
    def validate_positive(
        cls, amount: Union[str, int, float, Decimal], context: str = "amount"
    ) -> Decimal:
        """Validate that amount is positive and return as Decimal"""
        amount_decimal = cls.to_decimal(amount, context)

        if amount_decimal <= 0:
            raise ValueError(
                f"Amount must be positive in context {context}: {amount_decimal}"
            )

        return amount_decimal

    @classmethod
    def safe_percentage(
        cls,
        amount: Union[str, int, float, Decimal],
        percentage: Union[str, int, float, Decimal],
    ) -> Decimal:
        """Calculate percentage of amount safely"""
        amount_decimal = cls.to_decimal(amount, "percentage_amount")
        percentage_decimal = cls.to_decimal(percentage, "percentage_rate")

        # Convert percentage to decimal (e.g., 5% = 0.05)
        if percentage_decimal > 1:
            percentage_decimal = percentage_decimal / Decimal("100")

        result = amount_decimal * percentage_decimal
        return cls.quantize_usd(result)


class FinancialValidation:
    """Validation utilities for financial operations"""

    @classmethod
    def validate_transaction_amount(
        cls,
        amount: Union[str, int, float, Decimal],
        min_amount: Union[str, int, float, Decimal] = "0.01",
        max_amount: Union[str, int, float, Decimal] = "1000000",
    ) -> Decimal:
        """Validate transaction amount is within acceptable range"""
        amount_decimal = MonetaryDecimal.validate_positive(amount, "transaction")
        min_decimal = MonetaryDecimal.to_decimal(min_amount, "min_limit")
        max_decimal = MonetaryDecimal.to_decimal(max_amount, "max_limit")

        if amount_decimal < min_decimal:
            raise ValueError(f"Amount {amount_decimal} below minimum {min_decimal}")

        if amount_decimal > max_decimal:
            raise ValueError(f"Amount {amount_decimal} exceeds maximum {max_decimal}")

        return MonetaryDecimal.quantize_usd(amount_decimal)

    @classmethod
    def validate_exchange_rate(cls, rate: Union[str, int, float, Decimal]) -> Decimal:
        """Validate exchange rate is reasonable"""
        rate_decimal = MonetaryDecimal.validate_positive(rate, "exchange_rate")

        # Sanity check - rate should not be extremely high or low
        if rate_decimal < Decimal("0.00000001") or rate_decimal > Decimal("10000000"):
            raise ValueError(
                f"Exchange rate {rate_decimal} is outside reasonable range"
            )

        return MonetaryDecimal.quantize_rate(rate_decimal)

    @classmethod
    def validate_balance_operation(
        cls,
        current_balance: Union[str, int, float, Decimal],
        operation_amount: Union[str, int, float, Decimal],
        operation_type: str,
    ) -> tuple[Decimal, Decimal]:
        """Validate balance operation (debit/credit) and return proper Decimals"""
        current_decimal = MonetaryDecimal.to_decimal(current_balance, "current_balance")
        amount_decimal = MonetaryDecimal.validate_positive(
            operation_amount, f"{operation_type}_amount"
        )

        if operation_type == "debit" and current_decimal < amount_decimal:
            raise ValueError(
                f"Insufficient balance: {current_decimal} < {amount_decimal}"
            )

        return current_decimal, amount_decimal

    @classmethod
    def format_crypto_amount(cls, amount: Union[str, int, float, Decimal]) -> str:
        """Format crypto amount to avoid scientific notation"""
        decimal_amount = cls.to_decimal(amount, "crypto_display")
        
        # For very small amounts, show up to 8 decimal places but remove trailing zeros
        if abs(decimal_amount) < 1:
            formatted = f"{float(decimal_amount):.8f}".rstrip('0').rstrip('.')
        else:
            # For larger amounts, show reasonable precision
            formatted = f"{float(decimal_amount):.6f}".rstrip('0').rstrip('.')
        
        return formatted if formatted != '' else '0'
