"""
Simple In-Memory Caching System
Improves performance by caching frequently accessed data
"""

import time
import logging
from typing import Any, Optional, Dict, Callable
from functools import wraps

logger = logging.getLogger(__name__)


class SimpleCache:
    """Thread-safe in-memory cache with TTL support"""

    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0, "evictions": 0}

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        self._cleanup_expired()

        if key in self._cache:
            entry = self._cache[key]
            if entry["expires_at"] > time.time():
                self.stats["hits"] += 1
                return entry["value"]
            else:
                # Expired
                del self._cache[key]
                self.stats["evictions"] += 1

        self.stats["misses"] += 1
        return default

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL"""
        if ttl is None:
            ttl = self.default_ttl

        self._cache[key] = {
            "value": value,
            "created_at": time.time(),
            "expires_at": time.time() + ttl,
        }
        self.stats["sets"] += 1

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if key in self._cache:
            del self._cache[key]
            self.stats["deletes"] += 1
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries"""
        cleared_count = len(self._cache)
        self._cache.clear()
        self.stats["deletes"] += cleared_count

    def exists(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        return self.get(key, None) is not None

    def _cleanup_expired(self) -> None:
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key
            for key, entry in self._cache.items()
            if entry["expires_at"] <= current_time
        ]

        for key in expired_keys:
            del self._cache[key]
            self.stats["evictions"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            **self.stats,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
            "cache_size": len(self._cache),
        }

    def get_info(self) -> Dict[str, Any]:
        """Get detailed cache information"""
        self._cleanup_expired()

        entries_by_age = {}
        current_time = time.time()

        for key, entry in self._cache.items():
            age_seconds = current_time - entry["created_at"]
            age_range = self._get_age_range(age_seconds)
            entries_by_age[age_range] = entries_by_age.get(age_range, 0) + 1

        return {
            "stats": self.get_stats(),
            "entries_by_age": entries_by_age,
            "default_ttl": self.default_ttl,
        }

    def _get_age_range(self, age_seconds: float) -> str:
        """Categorize entry age"""
        if age_seconds < 60:
            return "< 1 minute"
        elif age_seconds < 300:
            return "1-5 minutes"
        elif age_seconds < 900:
            return "5-15 minutes"
        elif age_seconds < 3600:
            return "15-60 minutes"
        else:
            return "> 1 hour"


# Global cache instances
user_cache = SimpleCache(default_ttl=300)  # 5 minutes
escrow_cache = SimpleCache(default_ttl=180)  # 3 minutes
crypto_rates_cache = SimpleCache(default_ttl=60)  # 1 minute
general_cache = SimpleCache(default_ttl=600)  # 10 minutes


def cache_result(
    cache_instance: SimpleCache = general_cache,
    ttl: Optional[int] = None,
    key_prefix: str = "",
):
    """
    Decorator to cache function results

    Usage:
        @cache_result(user_cache, ttl=300, key_prefix="user_")
        def get_user_data(user_id):
            return expensive_database_call(user_id)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"

            # Try to get from cache
            cached_result = cache_instance.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result

            # Execute function and cache result
            try:
                result = await func(*args, **kwargs)
                cache_instance.set(cache_key, result, ttl)
                logger.debug(f"Cached result for {cache_key}")
                return result
            except Exception as e:
                logger.error(f"Error in cached function {func.__name__}: {e}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"

            # Try to get from cache
            cached_result = cache_instance.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result

            # Execute function and cache result
            try:
                result = func(*args, **kwargs)
                cache_instance.set(cache_key, result, ttl)
                logger.debug(f"Cached result for {cache_key}")
                return result
            except Exception as e:
                logger.error(f"Error in cached function {func.__name__}: {e}")
                raise

        # Return appropriate wrapper based on whether function is async
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Specialized cache functions
def cache_user_data(ttl: int = 300):
    """Cache user data with 5-minute default TTL"""
    return cache_result(user_cache, ttl=ttl, key_prefix="user_")


def cache_escrow_data(ttl: int = 180):
    """Cache escrow data with 3-minute default TTL"""
    return cache_result(escrow_cache, ttl=ttl, key_prefix="escrow_")


def cache_crypto_rates(ttl: int = 60):
    """Cache crypto rates with 1-minute default TTL"""
    return cache_result(crypto_rates_cache, ttl=ttl, key_prefix="rates_")


def invalidate_user_cache(user_id: int):
    """Invalidate all cached data for a specific user"""
    keys_to_delete = []
    for key in user_cache._cache.keys():
        if f"user_{user_id}" in key or f"_{user_id}_" in key:
            keys_to_delete.append(key)

    for key in keys_to_delete:
        user_cache.delete(key)

    logger.info(f"Invalidated {len(keys_to_delete)} cache entries for user {user_id}")


def invalidate_escrow_cache(escrow_id: str):
    """Invalidate all cached data for a specific escrow"""
    keys_to_delete = []
    for key in escrow_cache._cache.keys():
        if escrow_id in key:
            keys_to_delete.append(key)

    for key in keys_to_delete:
        escrow_cache.delete(key)

    logger.info(
        f"Invalidated {len(keys_to_delete)} cache entries for escrow {escrow_id}"
    )


def get_all_cache_stats() -> Dict[str, Any]:
    """Get statistics for all cache instances"""
    return {
        "user_cache": user_cache.get_stats(),
        "escrow_cache": escrow_cache.get_stats(),
        "crypto_rates_cache": crypto_rates_cache.get_stats(),
        "general_cache": general_cache.get_stats(),
    }
