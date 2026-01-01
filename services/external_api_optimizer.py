"""
External API Optimization Service
Provides centralized connection pooling, caching, and performance optimizations for all external API calls
"""

import asyncio
import aiohttp
import logging
import time
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from contextlib import asynccontextmanager
from utils.production_cache import get_cached, set_cached

logger = logging.getLogger(__name__)


@dataclass
class APIOptimizationConfig:
    """Configuration for API optimization settings"""
    # Connection pooling settings
    max_connections: int = 100
    max_connections_per_host: int = 30
    
    # Timeout configurations
    total_timeout: int = 30
    connect_timeout: int = 10
    
    # Cache settings
    default_cache_ttl: int = 300  # 5 minutes
    short_cache_ttl: int = 60     # 1 minute for frequently changing data
    long_cache_ttl: int = 1800    # 30 minutes for stable data
    
    # Retry settings
    max_retries: int = 3
    retry_delay_base: float = 1.0
    retry_backoff_factor: float = 2.0


class ExternalAPIOptimizer:
    """
    Centralized optimization service for all external API calls
    Provides connection pooling, intelligent caching, and performance monitoring
    """
    
    def __init__(self, config: Optional[APIOptimizationConfig] = None):
        self.config = config or APIOptimizationConfig()
        self._sessions: Dict[int, aiohttp.ClientSession] = {}  # Per-loop sessions
        self._session_locks: Dict[int, asyncio.Lock] = {}     # Per-loop locks
        
        # Performance tracking
        self._api_call_count = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._start_time = time.time()
        
        logger.info("🚀 External API Optimizer initialized with per-loop session management")
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get optimized HTTP session with connection pooling (per event loop)"""
        # Get current event loop ID to create per-loop sessions
        try:
            loop = asyncio.get_running_loop()
            loop_id = id(loop)
        except RuntimeError:
            # No running loop, create a temporary session for sync context
            logger.debug("🔄 Creating temporary session for non-async context")
            return await self._create_temporary_session()
        
        # Ensure we have a lock for this loop
        if loop_id not in self._session_locks:
            self._session_locks[loop_id] = asyncio.Lock()
        
        async with self._session_locks[loop_id]:
            # Check if we have a valid session for this loop
            if loop_id not in self._sessions or self._sessions[loop_id].closed:
                # Create optimized session for this specific event loop
                self._sessions[loop_id] = await self._create_optimized_session()
                logger.info(f"✅ Created optimized HTTP session for loop {loop_id}")
            
            return self._sessions[loop_id]
    
    async def _create_optimized_session(self) -> aiohttp.ClientSession:
        """Create an optimized aiohttp session with connection pooling"""
        # Create optimized connector with connection pooling
        connector = aiohttp.TCPConnector(
            limit=self.config.max_connections,
            limit_per_host=self.config.max_connections_per_host,
            ttl_dns_cache=300,  # DNS cache for 5 minutes
            use_dns_cache=True,
            keepalive_timeout=60,  # Keep connections alive for 1 minute
            enable_cleanup_closed=True
        )
        
        # Optimized timeout configuration
        timeout = aiohttp.ClientTimeout(
            total=self.config.total_timeout,
            connect=self.config.connect_timeout
        )
        
        return aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'LockBay-Escrow-Bot/2.0 (Optimized)'}
        )
    
    async def _create_temporary_session(self) -> aiohttp.ClientSession:
        """Create a temporary session for sync/non-loop contexts"""
        return await self._create_optimized_session()
    
    async def close_session(self):
        """Clean up all HTTP sessions"""
        closed_count = 0
        for loop_id, session in list(self._sessions.items()):
            if not session.closed:
                await session.close()
                closed_count += 1
        
        self._sessions.clear()
        self._session_locks.clear()
        logger.info(f"🔒 {closed_count} HTTP sessions closed")
    
    async def cached_api_call(
        self,
        service_name: str,
        cache_key: str,
        api_call_func,
        cache_ttl: Optional[int] = None,
        force_refresh: bool = False
    ) -> Any:
        """
        Execute API call with intelligent caching
        
        Args:
            service_name: Name of the service making the call
            cache_key: Unique cache key for this API call
            api_call_func: Async function that makes the actual API call
            cache_ttl: Cache time-to-live in seconds
            force_refresh: Force cache refresh if True
            
        Returns:
            API response data (cached or fresh)
        """
        self._api_call_count += 1
        
        # Check cache first (unless forced refresh)
        if not force_refresh:
            cached_result = get_cached(cache_key)
            if cached_result is not None:
                self._cache_hits += 1
                logger.debug(f"💾 Cache HIT for {service_name}: {cache_key}")
                return cached_result
        
        # Cache miss - make API call
        self._cache_misses += 1
        logger.debug(f"🌐 Cache MISS for {service_name}: {cache_key}")
        
        try:
            # Execute the API call
            result = await api_call_func()
            
            # Cache the result
            ttl = cache_ttl or self.config.default_cache_ttl
            set_cached(cache_key, result, ttl=ttl)
            
            logger.debug(f"✅ {service_name} API call successful, cached for {ttl}s")
            return result
            
        except Exception as e:
            logger.error(f"❌ {service_name} API call failed: {e}")
            raise
    
    async def batch_api_calls(
        self,
        service_name: str,
        calls: List[Dict[str, Any]],
        max_concurrent: int = 10
    ) -> List[Any]:
        """
        Execute multiple API calls concurrently with controlled concurrency
        
        Args:
            service_name: Name of the service making the calls
            calls: List of call dictionaries with 'func' and optional 'cache_key', 'cache_ttl'
            max_concurrent: Maximum number of concurrent calls
            
        Returns:
            List of results in the same order as input calls
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_call(call_info: Dict[str, Any]) -> Any:
            async with semaphore:
                func = call_info['func']
                cache_key = call_info.get('cache_key')
                cache_ttl = call_info.get('cache_ttl')
                
                if cache_key:
                    return await self.cached_api_call(
                        service_name, cache_key, func, cache_ttl
                    )
                else:
                    return await func()
        
        # Execute all calls concurrently
        start_time = time.time()
        tasks = [execute_call(call) for call in calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Count successful vs failed calls
        successful = sum(1 for r in results if not isinstance(r, Exception))
        failed = len(results) - successful
        
        logger.info(
            f"🔄 {service_name} batch execution: {successful}/{len(calls)} successful, "
            f"{failed} failed in {execution_time:.2f}s"
        )
        
        return results
    
    async def rate_limited_call(
        self,
        service_name: str,
        api_call_func,
        calls_per_second: float = 10.0
    ) -> Any:
        """
        Execute API call with rate limiting
        
        Args:
            service_name: Name of the service
            api_call_func: Function to execute
            calls_per_second: Maximum calls per second
            
        Returns:
            API response
        """
        # Simple rate limiting using sleep
        delay = 1.0 / calls_per_second
        await asyncio.sleep(delay)
        
        logger.debug(f"⏰ Rate limited {service_name} call (max {calls_per_second}/s)")
        return await api_call_func()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for monitoring"""
        uptime = time.time() - self._start_time
        cache_hit_rate = (
            self._cache_hits / (self._cache_hits + self._cache_misses)
            if (self._cache_hits + self._cache_misses) > 0
            else 0.0
        )
        
        return {
            'uptime_seconds': uptime,
            'total_api_calls': self._api_call_count,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_hit_rate': cache_hit_rate,
            'calls_per_minute': (self._api_call_count / uptime * 60) if uptime > 0 else 0
        }
    
    def log_performance_summary(self):
        """Log performance summary for monitoring"""
        stats = self.get_performance_stats()
        logger.info(
            f"📊 API Performance: {stats['total_api_calls']} calls, "
            f"{stats['cache_hit_rate']:.1%} cache hit rate, "
            f"{stats['calls_per_minute']:.1f} calls/min"
        )


# Global optimizer instance
_api_optimizer = None


async def get_api_optimizer() -> ExternalAPIOptimizer:
    """Get the global API optimizer instance"""
    global _api_optimizer
    if _api_optimizer is None:
        _api_optimizer = ExternalAPIOptimizer()
    return _api_optimizer


@asynccontextmanager
async def optimized_http_session():
    """Context manager for optimized HTTP session"""
    optimizer = await get_api_optimizer()
    session = await optimizer.get_session()
    try:
        yield session
    finally:
        # Session is managed globally, don't close here
        pass


async def cleanup_api_optimizer():
    """Clean up global API optimizer"""
    global _api_optimizer
    if _api_optimizer:
        await _api_optimizer.close_session()
        _api_optimizer.log_performance_summary()
        _api_optimizer = None
        logger.info("🧹 API optimizer cleaned up")