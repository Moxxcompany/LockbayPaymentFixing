"""
Webhook User Cache - Fast caching for webhook user data
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Simple in-memory cache for webhook user data
_webhook_user_cache: Dict[str, Any] = {}

def get_cached_user_fast(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Fast cache lookup for webhook user data
    
    Args:
        user_id: User ID to look up
        
    Returns:
        Cached user data or None if not cached
    """
    try:
        return _webhook_user_cache.get(user_id)
    except Exception as e:
        logger.error(f"Error accessing webhook user cache for {user_id}: {e}")
        return None

def cache_webhook_user(user_id: str, user_data: Dict[str, Any]) -> bool:
    """
    Cache webhook user data
    
    Args:
        user_id: User ID to cache
        user_data: User data to cache
        
    Returns:
        True if successful
    """
    try:
        _webhook_user_cache[user_id] = user_data
        return True
    except Exception as e:
        logger.error(f"Error caching webhook user data for {user_id}: {e}")
        return False

def invalidate_webhook_user_cache(user_id: str) -> bool:
    """
    Invalidate cached webhook user data
    
    Args:
        user_id: User ID to invalidate
        
    Returns:
        True if successful
    """
    try:
        _webhook_user_cache.pop(user_id, None)
        return True
    except Exception as e:
        logger.error(f"Error invalidating webhook user cache for {user_id}: {e}")
        return False