"""
Enhanced Caching System with Memory Management and Performance Optimization
"""

import time
import threading
import logging
from typing import Any, Optional, Dict, Tuple
from collections import OrderedDict
import sys

logger = logging.getLogger(__name__)


class EnhancedCache:
    """Memory-optimized cache with LRU eviction and performance monitoring"""

    def __init__(
        self, default_ttl: int = 300, max_size: int = 1000, cleanup_interval: int = 300
    ):
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.cleanup_interval = cleanup_interval

        # OPTIMIZED: Use OrderedDict for O(1) LRU operations
        self._cache: OrderedDict[str, Tuple[Any, float, int]] = (
            OrderedDict()
        )  # key -> (value, expiry, access_count)
        self._lock = threading.RLock()

        # Performance metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._last_cleanup = time.time()

        # Memory tracking
        self._memory_limit = 100 * 1024 * 1024  # 100MB default limit
        self._estimated_size = 0

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value with automatic memory management"""
        with self._lock:
            expiry_time = time.time() + (ttl if ttl is not None else self.default_ttl)

            # Remove existing key if present
            if key in self._cache:
                del self._cache[key]

            # Add new value
            self._cache[key] = (value, expiry_time, 1)

            # Update estimated memory size
            self._estimated_size += self._estimate_size(value)

            # OPTIMIZED: Trigger cleanup if needed
            self._cleanup_if_needed()

    def get(self, key: str) -> Optional[Any]:
        """Get value with LRU updating"""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            value, expiry_time, access_count = self._cache[key]
            current_time = time.time()

            # Check expiry
            if current_time > expiry_time:
                del self._cache[key]
                self._estimated_size -= self._estimate_size(value)
                self._misses += 1
                return None

            # Update access pattern (LRU)
            self._cache.move_to_end(key)
            self._cache[key] = (value, expiry_time, access_count + 1)
            self._hits += 1

            return value

    def delete(self, key: str) -> bool:
        """Delete specific key"""
        with self._lock:
            if key in self._cache:
                value, _, _ = self._cache[key]
                self._estimated_size -= self._estimate_size(value)
                del self._cache[key]
                return True
            return False

    def _cleanup_if_needed(self) -> None:
        """Intelligent cleanup based on size and time"""
        current_time = time.time()

        # Size-based cleanup
        while len(self._cache) > self.max_size:
            self._evict_lru()

        # Memory-based cleanup
        while self._estimated_size > self._memory_limit:
            self._evict_lru()

        # Time-based cleanup
        if current_time - self._last_cleanup > self.cleanup_interval:
            self._cleanup_expired()
            self._last_cleanup = current_time

    def _evict_lru(self) -> None:
        """Evict least recently used item"""
        if self._cache:
            key, (value, _, _) = self._cache.popitem(last=False)  # Remove oldest
            self._estimated_size -= self._estimate_size(value)
            self._evictions += 1

    def _cleanup_expired(self) -> None:
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = []

        for key, (value, expiry_time, _) in self._cache.items():
            if current_time > expiry_time:
                expired_keys.append(key)

        for key in expired_keys:
            value, _, _ = self._cache[key]
            self._estimated_size -= self._estimate_size(value)
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    def _estimate_size(self, value: Any) -> int:
        """Estimate memory size of value"""
        try:
            return sys.getsizeof(value)
        except Exception as e:
            logger.debug(f"Could not estimate size for value: {e}")
            return 1024  # Default estimate

    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.2f}%",
            "evictions": self._evictions,
            "estimated_memory_mb": self._estimated_size / (1024 * 1024),
            "memory_limit_mb": self._memory_limit / (1024 * 1024),
        }

    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._estimated_size = 0
            logger.info("Cache cleared")

    def set_memory_limit(self, limit_mb: int) -> None:
        """Set memory limit in MB"""
        self._memory_limit = limit_mb * 1024 * 1024
        self._cleanup_if_needed()
