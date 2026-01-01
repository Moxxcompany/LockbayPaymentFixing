"""
Datetime helper utilities to ensure consistent timezone handling across the application.

CRITICAL: User model uses timezone-naive datetimes (DateTime(timezone=False))
This module provides utilities to prevent timezone-aware datetimes from being
accidentally inserted into User table columns.
"""

from datetime import datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def ensure_naive_datetime(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Convert timezone-aware datetime to naive UTC datetime.
    
    Args:
        dt: Datetime that may be timezone-aware or naive
        
    Returns:
        Naive datetime in UTC, or None if input is None
        
    Example:
        >>> aware_dt = datetime.now(timezone.utc)
        >>> naive_dt = ensure_naive_datetime(aware_dt)
        >>> assert naive_dt.tzinfo is None
    """
    if dt is None:
        return None
        
    if dt.tzinfo is not None:
        # Convert to UTC and remove timezone info
        utc_dt = dt.astimezone(timezone.utc)
        return utc_dt.replace(tzinfo=None)
    
    return dt


def get_naive_utc_now() -> datetime:
    """
    Get current UTC time as naive datetime.
    
    This is the recommended way to get timestamps for User model fields.
    
    Returns:
        Current UTC time without timezone info
        
    Example:
        >>> now = get_naive_utc_now()
        >>> assert now.tzinfo is None
    """
    return datetime.utcnow()


def validate_user_timestamps(created_at: Optional[datetime], 
                             updated_at: Optional[datetime],
                             last_activity: Optional[datetime] = None) -> tuple[Optional[datetime], Optional[datetime], Optional[datetime]]:
    """
    Validate and convert User model timestamps to ensure they're timezone-naive.
    
    Args:
        created_at: User creation timestamp
        updated_at: User last update timestamp
        last_activity: User last activity timestamp
        
    Returns:
        Tuple of (created_at, updated_at, last_activity) as naive datetimes
        
    Raises:
        Warning log if timezone-aware datetimes are detected
        
    Example:
        >>> created, updated, activity = validate_user_timestamps(
        ...     created_at=datetime.now(timezone.utc),
        ...     updated_at=datetime.now(timezone.utc)
        ... )
        >>> assert all(dt is None or dt.tzinfo is None 
        ...           for dt in [created, updated, activity])
    """
    result = []
    for name, dt in [("created_at", created_at), 
                      ("updated_at", updated_at), 
                      ("last_activity", last_activity)]:
        if dt is not None and dt.tzinfo is not None:
            logger.warning(
                f"⚠️ TIMEZONE_MISMATCH: User.{name} has timezone info "
                f"({dt.tzinfo}). Converting to naive UTC datetime. "
                f"This may indicate a bug in the calling code."
            )
        result.append(ensure_naive_datetime(dt))
    
    return tuple(result)
