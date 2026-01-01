"""
Centralized data normalization utilities for type safety and consistency.

This module provides normalizers for data types that require consistent 
handling across the LockBay platform, particularly for database operations.
"""

import logging
from typing import Union, Optional

logger = logging.getLogger(__name__)


def normalize_telegram_id(value: Union[int, str, None]) -> Optional[int]:
    """
    Normalize telegram_id to integer for consistent database operations.
    
    Args:
        value: Telegram ID as int, str (digits), or None
        
    Returns:
        Integer telegram_id or None if input is None
        
    Raises:
        TypeError: If value cannot be converted to int
        ValueError: If string value contains non-digit characters
        
    Examples:
        >>> normalize_telegram_id(5590563715)
        5590563715
        >>> normalize_telegram_id("5590563715")
        5590563715
        >>> normalize_telegram_id(None)
        None
    """
    if value is None:
        return None
        
    if isinstance(value, int):
        if value < 0:
            raise ValueError(f"Telegram ID cannot be negative: {value}")
        return value
        
    if isinstance(value, str):
        # Handle empty/whitespace strings
        value = value.strip()
        if not value:
            return None
            
        # Check if string contains only digits
        if not value.isdigit():
            raise ValueError(f"Telegram ID must contain only digits: {value}")
            
        telegram_id = int(value)
        if telegram_id < 0:
            raise ValueError(f"Telegram ID cannot be negative: {telegram_id}")
        return telegram_id
    
    # Handle other types
    try:
        return int(value)
    except (TypeError, ValueError) as e:
        raise TypeError(f"Cannot convert telegram_id to int: {value} (type: {type(value)})") from e


def normalize_user_id(value: Union[int, str, None]) -> Optional[int]:
    """
    Normalize database user_id to integer.
    
    Args:
        value: User ID as int, str (digits), or None
        
    Returns:
        Integer user_id or None if input is None
        
    Raises:
        TypeError: If value cannot be converted to int
        ValueError: If string value contains non-digit characters or is negative
    """
    if value is None:
        return None
        
    if isinstance(value, int):
        if value <= 0:
            raise ValueError(f"Database user ID must be positive: {value}")
        return value
        
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
            
        if not value.isdigit():
            raise ValueError(f"User ID must contain only digits: {value}")
            
        user_id = int(value)
        if user_id <= 0:
            raise ValueError(f"Database user ID must be positive: {user_id}")
        return user_id
    
    try:
        user_id = int(value)
        if user_id <= 0:
            raise ValueError(f"Database user ID must be positive: {user_id}")
        return user_id
    except (TypeError, ValueError) as e:
        raise TypeError(f"Cannot convert user_id to int: {value} (type: {type(value)})") from e