"""
Type Safety Helpers for SQLAlchemy Models
Addresses common LSP type checking issues
"""

from typing import Any, Optional
from telegram import Update
from decimal import Decimal


def safe_column_value(column_or_value: Any, default: Any = None) -> Any:
    """Safely extract value from SQLAlchemy Column or return the value itself"""
    if hasattr(column_or_value, "__table__"):
        # This is likely a SQLAlchemy column, return the actual value
        return (
            getattr(column_or_value, "_sa_instance_state", column_or_value) or default
        )
    return column_or_value if column_or_value is not None else default


def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float, handling SQLAlchemy columns"""
    try:
        if value is None:
            return default
        if hasattr(value, "__float__"):
            return float(value)
        return float(str(value))
    except (ValueError, TypeError, AttributeError):
        return default


def safe_int_conversion(value: Any, default: int = 0) -> int:
    """Safely convert value to int, handling SQLAlchemy columns"""
    try:
        if value is None:
            return default
        if hasattr(value, "__int__"):
            return int(value)
        return int(str(value))
    except (ValueError, TypeError, AttributeError):
        return default


def safe_str_conversion(value: Any, default: str = "") -> str:
    """Safely convert value to string, handling SQLAlchemy columns"""
    try:
        if value is None:
            return default
        return str(value)
    except (ValueError, TypeError, AttributeError):
        return default


def safe_bool_conversion(value: Any, default: bool = False) -> bool:
    """Safely convert value to bool, handling SQLAlchemy columns"""
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if hasattr(value, "__bool__"):
            return bool(value)
        return bool(str(value).lower() in ("true", "1", "yes", "on"))
    except (ValueError, TypeError, AttributeError):
        return default


def safe_decimal_conversion(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    """Safely convert value to Decimal, handling SQLAlchemy columns"""
    try:
        if value is None:
            return default
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))
    except (ValueError, TypeError, AttributeError):
        return default


def safe_query_check(query_or_update: Optional[Update]) -> bool:
    """Check if update object has valid callback query"""
    if not query_or_update:
        return False
    return (
        hasattr(query_or_update, "callback_query")
        and query_or_update.callback_query is not None
    )


def safe_message_check(update: Optional[Update]) -> bool:
    """Check if update object has valid message"""
    if not update:
        return False
    return hasattr(update, "message") and update.message is not None


def safe_user_data_get(context: Any, key: str, default: Any = None) -> Any:
    """Safely get value from user_data context"""
    if not context:
        return default
    if not hasattr(context, "user_data") or context.user_data is None:
        return default
    return context.user_data.get(key, default)


def safe_user_data_pop(context: Any, key: str, default: Any = None) -> Any:
    """Safely pop value from user_data context"""
    if not context:
        return default
    if not hasattr(context, "user_data") or context.user_data is None:
        return default
    return context.user_data.pop(key, default)
