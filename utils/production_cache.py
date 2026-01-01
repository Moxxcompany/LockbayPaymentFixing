"""
Production-ready caching system for high-performance bot operations
Implements multi-layer caching with TTL, LRU eviction, and memory management
"""

import time
import logging
from typing import Dict, Any, Optional, Union
from threading import RLock
from collections import OrderedDict
import psutil
import os

logger = logging.getLogger(__name__)

class ProductionCache:
    """High-performance production cache with memory management"""
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 300, max_memory_mb: int = 64):
        # PERFORMANCE OPTIMIZATION: Increased cache size and memory limits for better crypto rate caching
        self.max_size = max_size  # Increased to 10000 to handle crypto rates + user data
        self.default_ttl = default_ttl  # Increased to 300 seconds (5 minutes) for better cache longevity  
        self.max_memory_mb = max_memory_mb  # Increased to 64MB for modern server capacity
        self.cache: OrderedDict = OrderedDict()
        self.metadata: Dict[str, Dict] = {}
        self.lock = RLock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'memory_cleanups': 0,
            'last_cleanup': time.time()
        }
        
        # MEMORY LEAK FIX: Add periodic cleanup timer
        self._last_aggressive_cleanup = time.time()
        self._aggressive_cleanup_interval = 300  # 5 minutes
        self._last_zero_cleanup_log = 0  # Reduce log spam
        
        # LOGGING THROTTLE: Time-based throttling for cache operations
        self._last_routine_cleanup_log = 0  # Time-based throttle for routine cleanups
        self._routine_log_interval = 60  # Log routine cleanups at most once per minute
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache with TTL check"""
        with self.lock:
            if key not in self.cache:
                self.stats['misses'] += 1
                return None
            
            # Check TTL
            metadata = self.metadata.get(key, {})
            if self._is_expired(metadata):
                self._remove_key(key)
                self.stats['misses'] += 1
                return None
            
            # Move to end (LRU)
            self.cache.move_to_end(key)
            self.stats['hits'] += 1
            return self.cache[key]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set item in cache with TTL and memory management"""
        with self.lock:
            current_time = time.time()
            ttl = ttl or self.default_ttl
            
            # Check memory usage before adding
            if self._should_cleanup_memory():
                self._cleanup_memory()
            
            # Remove oldest item if at capacity
            if key not in self.cache and len(self.cache) >= self.max_size:
                self._evict_oldest()
            
            # Store item with metadata
            self.cache[key] = value
            self.metadata[key] = {
                'created_at': current_time,
                'ttl': ttl,
                'expires_at': current_time + ttl,
                'access_count': 1
            }
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return True
    
    def delete(self, key: str) -> bool:
        """Delete item from cache"""
        with self.lock:
            if key in self.cache:
                self._remove_key(key)
                return True
            return False
    
    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.metadata.clear()
            logger.info("🗑️ Production cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            # Memory usage
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'hit_rate': f"{hit_rate:.1f}%",
                'evictions': self.stats['evictions'],
                'memory_cleanups': self.stats['memory_cleanups'],
                'memory_usage_mb': f"{memory_mb:.1f}",
                'expired_items': self._count_expired_items()
            }
    
    def _is_expired(self, metadata: Dict) -> bool:
        """Check if item is expired"""
        if not metadata:
            return True
        return time.time() > metadata.get('expires_at', 0)
    
    def _remove_key(self, key: str):
        """Remove key and its metadata"""
        self.cache.pop(key, None)
        self.metadata.pop(key, None)
    
    def _evict_oldest(self):
        """Evict oldest item (LRU)"""
        if self.cache:
            oldest_key = next(iter(self.cache))
            self._remove_key(oldest_key)
            self.stats['evictions'] += 1
    
    def _should_cleanup_memory(self) -> bool:
        """Check if memory cleanup is needed"""
        try:
            # PERFORMANCE FIX: Check time-based cleanup first
            current_time = time.time()
            time_since_cleanup = current_time - self.stats['last_cleanup']
            
            # Force cleanup every 2 minutes regardless of memory
            if time_since_cleanup > 120:
                return True
            
            # Check memory pressure
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            return memory_mb > self.max_memory_mb
        except Exception as e:
            logger.debug(f"Could not check memory pressure: {e}")
            return False
    
    def _cleanup_memory(self):
        """Optimized memory cleanup with better efficiency"""
        with self.lock:
            original_size = len(self.cache)
            current_time = time.time()
            
            # EFFICIENCY FIX: Build expired keys list more efficiently
            expired_keys = []
            for key, metadata in self.metadata.items():
                if current_time > metadata.get('expires_at', 0):
                    expired_keys.append(key)
            
            # Remove expired items
            for key in expired_keys:
                self._remove_key(key)
            
            # MEMORY LEAK FIX: More aggressive cleanup when memory is high
            memory_pressure = self._get_memory_pressure()
            if memory_pressure > 0.8:  # High memory pressure
                # Remove 30% of oldest items when memory is high
                items_to_remove = max(1, int(len(self.cache) * 0.3))
                keys_to_remove = list(self.cache.keys())[:items_to_remove]
                
                for key in keys_to_remove:
                    self._remove_key(key)
                    self.stats['evictions'] += 1
                    
            elif len(self.cache) > self.max_size * 0.8:
                # Standard cleanup: remove 15% of oldest items
                items_to_remove = max(1, int(len(self.cache) * 0.15))
                keys_to_remove = list(self.cache.keys())[:items_to_remove]
                
                for key in keys_to_remove:
                    self._remove_key(key)
                    self.stats['evictions'] += 1
            
            cleaned = original_size - len(self.cache)
            self.stats['memory_cleanups'] += 1
            self.stats['last_cleanup'] = current_time
            
            # BALANCED LOGGING: Smart logging that reduces noise while maintaining visibility
            # Strategy: Always log significant events immediately, throttle routine single-item cleanups
            
            if cleaned > 1:
                # ALWAYS LOG: Multiple items removed - significant activity worth noting
                pressure_info = f", pressure: {memory_pressure:.1f}" if memory_pressure > 0.8 else ""
                logger.info(f"🧹 Memory cleanup: removed {cleaned} items (expired: {len(expired_keys)}, evicted: {cleaned - len(expired_keys)}){pressure_info}")
                
            elif cleaned == 1:
                # THROTTLED LOGGING: Single item cleanup - time-based only for guaranteed visibility
                # Log at most once per minute, guaranteeing visibility if any activity occurs
                time_since_last_log = current_time - self._last_routine_cleanup_log
                
                if time_since_last_log >= self._routine_log_interval:
                    # Include pressure info if elevated to show operational context
                    pressure_info = f", pressure: {memory_pressure:.1f}" if memory_pressure > 0.8 else ""
                    logger.info(f"🧹 Cache churn: removed {cleaned} item (expired: {len(expired_keys)}, evicted: {cleaned - len(expired_keys)}) [cache: {len(self.cache)}/{self.max_size}]{pressure_info}")
                    self._last_routine_cleanup_log = current_time
                    
            elif cleaned == 0:
                # DEBUG LOGGING: No cleanup needed - periodic summary only
                if current_time - self._last_zero_cleanup_log > 300:
                    logger.debug(f"🧹 Memory cleanup: removed 0 items (cache size: {len(self.cache)}/{self.max_size})")
                    self._last_zero_cleanup_log = current_time
    
    def _count_expired_items(self) -> int:
        """Count expired items in cache"""
        current_time = time.time()
        expired = 0
        
        for metadata in self.metadata.values():
            if current_time > metadata.get('expires_at', 0):
                expired += 1
        
        return expired
    
    def _get_memory_pressure(self) -> float:
        """Calculate current memory pressure as ratio (0.0 to 1.0+)"""
        try:
            process = psutil.Process(os.getpid())
            current_memory_mb = process.memory_info().rss / 1024 / 1024
            return min(2.0, current_memory_mb / self.max_memory_mb)
        except Exception as e:
            logger.debug(f"Could not calculate memory pressure: {e}")
            return 0.0

# Global production cache instance
_production_cache = ProductionCache()

def get_cached(key: str) -> Optional[Any]:
    """Get item from production cache"""
    return _production_cache.get(key)

def set_cached(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Set item in production cache"""
    return _production_cache.set(key, value, ttl)

def delete_cached(key: str) -> bool:
    """Delete item from production cache"""
    return _production_cache.delete(key)

def get_cache_stats() -> Dict[str, Any]:
    """Get production cache statistics"""
    return _production_cache.get_stats()

def clear_cache():
    """Clear production cache"""
    _production_cache.clear()

class UserCacheOptimized:
    """Optimized user caching for production"""
    
    @staticmethod
    def get_user_cache_key(telegram_id: Union[str, int]) -> str:
        """Generate standardized user cache key"""
        return f"user:{telegram_id}"
    
    @staticmethod
    def cache_user_data(user, ttl: int = 300) -> bool:
        """Cache user data with optimized serialization"""
        if not user:
            return False
        
        try:
            cache_key = UserCacheOptimized.get_user_cache_key(user.telegram_id)
            
            # Lightweight user data for caching
            user_data = {
                'id': user.id,
                'telegram_id': user.telegram_id,
                'username': getattr(user, 'username', None),
                'first_name': getattr(user, 'first_name', None),
                'email': getattr(user, 'email', None),
                'email_verified': getattr(user, 'email_verified', False),
                'is_admin': getattr(user, 'is_admin', False),
                'total_trades': getattr(user, 'total_trades', 0),
                'reputation_score': str(getattr(user, 'reputation_score', 0)),
                'cached_at': time.time()
            }
            
            return set_cached(cache_key, user_data, ttl)
            
        except Exception as e:
            logger.error(f"Failed to cache user data: {e}")
            return False
    
    @staticmethod
    def get_cached_user(telegram_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """Get cached user data"""
        try:
            cache_key = UserCacheOptimized.get_user_cache_key(telegram_id)
            return get_cached(cache_key)
        except Exception as e:
            logger.error(f"Failed to get cached user: {e}")
            return None

def setup_production_cache():
    """Setup and configure production cache monitoring"""
    try:
        # Initialize cache statistics monitoring
        stats = get_cache_stats()
        logger.info(f"🔧 Production cache configured: {stats['size']}/{stats['max_size']} items, {stats['hit_rate']} hit rate")
        
        # Perform initial cleanup if needed
        if stats['expired_items'] > 0:
            _production_cache._cleanup_memory()
            logger.info(f"🧹 Cleaned up {stats['expired_items']} expired cache items")
        
        return True
    except Exception as e:
        logger.error(f"Failed to setup production cache: {e}")
        return False

# Initialize production cache on import
logger.info("🚀 Production cache system initialized")