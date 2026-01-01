"""
ORM Typing Helpers - Strategic Foundation Module
Type-safe converters to resolve Column[Type] vs Type incompatibilities

This module provides standardized type-safe converters to extract values from
SQLAlchemy Column objects while maintaining proper typing discipline.

Key Functions:
- as_int(): Extract integer values from Column[int] objects
- as_str(): Extract string values from Column[str] objects  
- as_decimal(): Extract Decimal values from Column[Decimal] objects
- as_bool(): Extract boolean values from Column[bool] objects
- as_datetime(): Extract datetime values from Column[datetime] objects
- safe_getattr(): Safe attribute access with None handling

Usage Examples:
    # Instead of: user.id (Column[int]) -> function expecting int
    # Use: as_int(user.id) -> int
    
    # Instead of: if wallet.available_balance: (Column[Decimal] boolean)
    # Use: if as_decimal(wallet.available_balance) > 0:
    
    # Instead of: escrow.status (Column[str]) -> function expecting str  
    # Use: as_str(escrow.status) -> str
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, Union, overload
from sqlalchemy import Column
from sqlalchemy.sql.elements import ColumnElement

logger = logging.getLogger(__name__)


@overload
def as_int(value: None) -> None: ...

@overload
def as_int(value: int) -> int: ...

@overload
def as_int(value: Any) -> Optional[int]: ...

def as_int(value: Any) -> Optional[int]:
    """
    Type-safe extraction of integer values from SQLAlchemy Column objects.
    
    Args:
        value: Column[int], ColumnElement[int], int, or None
        
    Returns:
        Integer value or None if input is None/invalid
        
    Examples:
        user_id = as_int(user.id)  # Column[int] -> int
        escrow_id = as_int(escrow.id)  # Column[int] -> int
    """
    if value is None:
        return None
    
    # Already an integer
    if isinstance(value, int):
        return value
    
    # SQLAlchemy Column/ColumnElement - attempt to extract value
    if hasattr(value, '__getattribute__'):
        try:
            # For bound instances, try to get the actual value
            if hasattr(value, '_sa_instance_state'):
                # Safe conversion - convert to string first to avoid type issues
                try:
                    return int(str(value))
                except (ValueError, TypeError):
                    return None
            # For unbound Column objects, we can't extract - return None
            logger.warning(f"Cannot extract value from unbound Column: {value}")
            return None
        except (ValueError, TypeError, AttributeError):
            logger.warning(f"Failed to convert Column to int: {value}")
            return None
    
    # Try direct conversion for other types
    try:
        return int(value)
    except (ValueError, TypeError):
        logger.warning(f"Cannot convert value to int: {value} (type: {type(value)})")
        return None


@overload
def as_str(value: None) -> None: ...

@overload
def as_str(value: str) -> str: ...

@overload
def as_str(value: Any) -> Optional[str]: ...

def as_str(value: Any) -> Optional[str]:
    """
    Type-safe extraction of string values from SQLAlchemy Column objects.
    
    Args:
        value: Column[str], ColumnElement[str], str, or None
        
    Returns:
        String value or None if input is None/invalid
        
    Examples:
        status = as_str(escrow.status)  # Column[str] -> str
        currency = as_str(wallet.currency)  # Column[str] -> str
    """
    if value is None:
        return None
    
    # Already a string
    if isinstance(value, str):
        return value
    
    # SQLAlchemy Column/ColumnElement - attempt to extract value
    if hasattr(value, '__getattribute__'):
        try:
            # For bound instances, try to get the actual value
            if hasattr(value, '_sa_instance_state'):
                return str(value)
            # For unbound Column objects, we can't extract - return None
            logger.warning(f"Cannot extract value from unbound Column: {value}")
            return None
        except (ValueError, TypeError, AttributeError):
            logger.warning(f"Failed to convert Column to str: {value}")
            return None
    
    # Try direct conversion for other types
    try:
        return str(value)
    except (ValueError, TypeError):
        logger.warning(f"Cannot convert value to str: {value} (type: {type(value)})")
        return None


@overload
def as_decimal(value: None) -> None: ...

@overload
def as_decimal(value: Decimal) -> Decimal: ...

@overload
def as_decimal(value: Any) -> Optional[Decimal]: ...

def as_decimal(value: Any) -> Optional[Decimal]:
    """
    Type-safe extraction of Decimal values from SQLAlchemy Column objects.
    
    Args:
        value: Column[Decimal], ColumnElement[Decimal], Decimal, float, int, or None
        
    Returns:
        Decimal value or None if input is None/invalid
        
    Examples:
        balance = as_decimal(wallet.available_balance)  # Column[Decimal] -> Decimal
        amount = as_decimal(transaction.amount)  # Column[Decimal] -> Decimal
    """
    if value is None:
        return None
    
    # Already a Decimal
    if isinstance(value, Decimal):
        return value
    
    # Handle numeric types
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    
    # SQLAlchemy Column/ColumnElement - attempt to extract value
    if hasattr(value, '__getattribute__'):
        try:
            # For bound instances, try to get the actual value
            if hasattr(value, '_sa_instance_state'):
                return Decimal(str(value))
            # For unbound Column objects, we can't extract - return None
            logger.warning(f"Cannot extract value from unbound Column: {value}")
            return None
        except (ValueError, TypeError, AttributeError):
            logger.warning(f"Failed to convert Column to Decimal: {value}")
            return None
    
    # Try direct conversion for other types
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        logger.warning(f"Cannot convert value to Decimal: {value} (type: {type(value)})")
        return None


@overload
def as_bool(value: None) -> None: ...

@overload
def as_bool(value: bool) -> bool: ...

@overload
def as_bool(value: Any) -> Optional[bool]: ...

def as_bool(value: Any) -> Optional[bool]:
    """
    Type-safe extraction of boolean values from SQLAlchemy Column objects.
    
    Args:
        value: Column[bool], ColumnElement[bool], bool, or None
        
    Returns:
        Boolean value or None if input is None/invalid
        
    Examples:
        is_verified = as_bool(account.is_verified)  # Column[bool] -> bool
        is_active = as_bool(user.is_active)  # Column[bool] -> bool
    """
    if value is None:
        return None
    
    # Already a boolean
    if isinstance(value, bool):
        return value
    
    # SQLAlchemy Column/ColumnElement - attempt to extract value
    if hasattr(value, '__getattribute__'):
        try:
            # For bound instances, try to get the actual value
            if hasattr(value, '_sa_instance_state'):
                return bool(value)
            # For unbound Column objects, we can't extract - return None
            logger.warning(f"Cannot extract value from unbound Column: {value}")
            return None
        except (ValueError, TypeError, AttributeError):
            logger.warning(f"Failed to convert Column to bool: {value}")
            return None
    
    # Try direct conversion for other types
    try:
        return bool(value)
    except (ValueError, TypeError):
        logger.warning(f"Cannot convert value to bool: {value} (type: {type(value)})")
        return None


@overload
def as_datetime(value: None) -> None: ...

@overload
def as_datetime(value: datetime) -> datetime: ...

@overload
def as_datetime(value: Any) -> Optional[datetime]: ...

def as_datetime(value: Any) -> Optional[datetime]:
    """
    Type-safe extraction of datetime values from SQLAlchemy Column objects.
    
    Args:
        value: Column[datetime], ColumnElement[datetime], datetime, or None
        
    Returns:
        datetime value or None if input is None/invalid
        
    Examples:
        created_at = as_datetime(escrow.created_at)  # Column[datetime] -> datetime
        updated_at = as_datetime(user.updated_at)  # Column[datetime] -> datetime
    """
    if value is None:
        return None
    
    # Already a datetime
    if isinstance(value, datetime):
        return value
    
    # SQLAlchemy Column/ColumnElement - attempt to extract value
    if hasattr(value, '__getattribute__'):
        try:
            # For bound instances, try to get the actual value
            if hasattr(value, '_sa_instance_state'):
                if isinstance(value, datetime):
                    return value
                return None
            # For unbound Column objects, we can't extract - return None
            logger.warning(f"Cannot extract value from unbound Column: {value}")
            return None
        except (ValueError, TypeError, AttributeError):
            logger.warning(f"Failed to convert Column to datetime: {value}")
            return None
    
    logger.warning(f"Cannot convert value to datetime: {value} (type: {type(value)})")
    return None


def safe_getattr(obj: Any, attr: str, default: Any = None) -> Any:
    """
    Safe attribute access with None handling and Column value extraction.
    
    Args:
        obj: Object to get attribute from (may be None)
        attr: Attribute name to access
        default: Default value if obj is None or attribute doesn't exist
        
    Returns:
        Attribute value with proper type extraction, or default
        
    Examples:
        user_id = safe_getattr(update.effective_user, 'id', 0)
        status = safe_getattr(cashout, 'status', 'unknown')
    """
    if obj is None:
        return default
    
    try:
        value = getattr(obj, attr, default)
        
        # If we got a Column/ColumnElement, try to extract the actual value
        if hasattr(value, '__getattribute__') and hasattr(value, '_sa_instance_state'):
            return value
        
        return value
    except (AttributeError, TypeError):
        return default


def is_column_truthy(value: Union[Column, ColumnElement, Any]) -> bool:
    """
    Safe boolean evaluation of Column objects and regular values.
    
    Args:
        value: Column object, ColumnElement, or any value
        
    Returns:
        Boolean result of truthiness evaluation
        
    Examples:
        if is_column_truthy(wallet.available_balance):  # Safe Column[Decimal] check
        if is_column_truthy(user.is_active):  # Safe Column[bool] check
    """
    if value is None:
        return False
    
    # For Column/ColumnElement objects, try to extract value first
    if hasattr(value, '__getattribute__'):
        try:
            # For bound instances, try to get the actual value
            if hasattr(value, '_sa_instance_state'):
                # Extract based on type
                if isinstance(value, bool):
                    return value
                elif isinstance(value, (int, float, Decimal)):
                    return value != 0
                elif isinstance(value, str):
                    return len(value) > 0
                else:
                    return bool(value)
            # For unbound Column objects, return False (can't evaluate)
            return False
        except (ValueError, TypeError, AttributeError):
            return False
    
    # Regular truthiness evaluation
    return bool(value)


@overload
def extract_column_value(column_value: None, expected_type: Optional[type] = None) -> None: ...

@overload
def extract_column_value(column_value: Any, expected_type: Optional[type] = None) -> Any: ...

def extract_column_value(column_value: Any, expected_type: Optional[type] = None) -> Any:
    """
    Generic column value extraction with type validation.
    
    Args:
        column_value: SQLAlchemy Column/ColumnElement or regular value
        expected_type: Expected Python type for validation (optional)
        
    Returns:
        Extracted value with proper typing or None
        
    Examples:
        user_id = extract_column_value(user.id, int)
        balance = extract_column_value(wallet.available_balance, Decimal)
    """
    if column_value is None:
        return None
    
    # If already the expected type, return as-is
    if expected_type and isinstance(column_value, expected_type):
        return column_value
    
    # For Column/ColumnElement, try extraction
    if hasattr(column_value, '__getattribute__'):
        try:
            if hasattr(column_value, '_sa_instance_state'):
                extracted = column_value
                if expected_type and not isinstance(extracted, expected_type):
                    # Try type conversion using the type-safe helpers
                    if expected_type == int:
                        return as_int(extracted)
                    elif expected_type == str:
                        return as_str(extracted)
                    elif expected_type == Decimal:
                        return as_decimal(extracted)
                    elif expected_type == bool:
                        return as_bool(extracted)
                    elif expected_type == datetime:
                        return extracted if isinstance(extracted, datetime) else None
                return extracted
        except (ValueError, TypeError, AttributeError):
            logger.warning(f"Failed to extract value from Column: {column_value}")
            return None
    
    # Direct type conversion for non-Column values
    if expected_type:
        try:
            if expected_type == int:
                # Use str() first to avoid Column/ColumnElement issues
                return int(str(column_value)) if not isinstance(column_value, (Column, ColumnElement)) else None
            elif expected_type == str:
                return str(column_value)
            elif expected_type == Decimal:
                return Decimal(str(column_value))
            elif expected_type == bool:
                return bool(column_value)
            elif expected_type == datetime:
                return column_value if isinstance(column_value, datetime) else None
        except (ValueError, TypeError):
            logger.warning(f"Failed to convert value to {expected_type}: {column_value}")
            return None
    
    return column_value
