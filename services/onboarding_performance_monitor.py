"""
Onboarding Performance Monitor
Comprehensive performance tracking for the onboarding flow to ensure <60s completion
"""

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
from functools import wraps
from caching.enhanced_cache import EnhancedCache

logger = logging.getLogger(__name__)

# Performance cache for tracking metrics
_perf_cache = EnhancedCache(default_ttl=3600, max_size=1000)

class OnboardingPerformanceMonitor:
    """Monitor and track onboarding performance metrics"""
    
    # Performance targets in seconds
    TARGETS = {
        "total_onboarding": 60.0,      # Total onboarding must complete in <60s
        "step_transition": 15.0,       # Each step should complete in <15s
        "email_otp_delivery": 10.0,    # Email OTP delivery in <10s
        "database_operation": 2.0,     # Database ops in <2s
        "user_creation": 5.0,          # User creation in <5s
        "email_verification": 8.0      # Email verification in <8s
    }
    
    def __init__(self):
        self.step_timers = {}
        self.total_start_time = None
    
    def start_total_timing(self, user_id: int) -> None:
        """Start timing total onboarding process"""
        self.total_start_time = time.perf_counter()
        cache_key = f"onboarding_start_{user_id}"
        _perf_cache.set(cache_key, self.total_start_time, ttl=7200)
        logger.info(f"🚀 ONBOARDING_START: User {user_id} onboarding timer started")
    
    def start_step_timing(self, user_id: int, step: str) -> None:
        """Start timing individual onboarding step"""
        step_start = time.perf_counter()
        self.step_timers[f"{user_id}_{step}"] = step_start
        cache_key = f"step_start_{user_id}_{step}"
        _perf_cache.set(cache_key, step_start, ttl=3600)
        logger.info(f"📊 STEP_START: User {user_id} step '{step}' timer started")
    
    def end_step_timing(self, user_id: int, step: str) -> float:
        """End timing individual onboarding step and return duration"""
        step_end = time.perf_counter()
        step_key = f"{user_id}_{step}"
        cache_key = f"step_start_{user_id}_{step}"
        
        # Try to get start time from instance or cache
        step_start = self.step_timers.get(step_key) or _perf_cache.get(cache_key)
        
        if step_start:
            duration = step_end - step_start
            target = self.TARGETS.get(f"step_{step}", self.TARGETS["step_transition"])
            
            # Performance analysis
            performance_status = "✅ FAST" if duration <= target else "⚠️ SLOW"
            over_target = max(0, duration - target)
            
            logger.info(
                f"📊 STEP_COMPLETE: User {user_id} step '{step}' completed in {duration:.3f}s "
                f"(target: {target}s) {performance_status}"
            )
            
            if over_target > 0:
                logger.warning(
                    f"⚠️ PERFORMANCE_WARNING: Step '{step}' exceeded target by {over_target:.3f}s"
                )
            
            # Cache step performance for analytics
            perf_data = {
                "duration": duration,
                "target": target,
                "timestamp": datetime.utcnow().isoformat(),
                "over_target": over_target
            }
            _perf_cache.set(f"step_perf_{user_id}_{step}", perf_data, ttl=3600)
            
            return duration
        else:
            logger.warning(f"⚠️ No start time found for step '{step}' user {user_id}")
            return 0.0
    
    def end_total_timing(self, user_id: int, completed: bool = True) -> Dict[str, Any]:
        """End total timing and provide performance summary"""
        total_end = time.perf_counter()
        cache_key = f"onboarding_start_{user_id}"
        
        # Get start time from instance or cache
        total_start = self.total_start_time or _perf_cache.get(cache_key)
        
        if not total_start:
            logger.warning(f"⚠️ No total start time found for user {user_id}")
            return {"duration": 0.0, "status": "TIMING_ERROR"}
        
        total_duration = total_end - total_start
        target = self.TARGETS["total_onboarding"]
        
        # Comprehensive performance analysis
        status = "✅ EXCELLENT" if total_duration <= target else "❌ SLOW"
        over_target = max(0, total_duration - target)
        
        # Performance grade
        if total_duration <= 30:
            grade = "A+"
        elif total_duration <= 45:
            grade = "A"
        elif total_duration <= target:
            grade = "B"
        elif total_duration <= 90:
            grade = "C"
        else:
            grade = "F"
        
        result = {
            "user_id": user_id,
            "total_duration": round(total_duration, 3),
            "target": target,
            "status": status,
            "grade": grade,
            "over_target": round(over_target, 3) if over_target > 0 else 0,
            "completed": completed,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Log comprehensive results
        logger.info(
            f"🏁 ONBOARDING_COMPLETE: User {user_id} onboarding completed in {total_duration:.3f}s "
            f"(target: {target}s) Grade: {grade} {status}"
        )
        
        if over_target > 0:
            logger.warning(
                f"🚨 PERFORMANCE_ALERT: Onboarding exceeded target by {over_target:.3f}s "
                f"({((over_target/target)*100):.1f}% over target)"
            )
        
        # Cache performance data for analytics
        _perf_cache.set(f"total_perf_{user_id}", result, ttl=7200)
        
        return result
    
    def get_performance_summary(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive performance summary for user onboarding"""
        total_perf = _perf_cache.get(f"total_perf_{user_id}")
        
        # Get step performances
        step_perfs = {}
        for step in ["capture_email", "verify_otp", "accept_tos"]:
            step_data = _perf_cache.get(f"step_perf_{user_id}_{step}")
            if step_data:
                step_perfs[step] = step_data
        
        return {
            "user_id": user_id,
            "total_performance": total_perf,
            "step_performances": step_perfs,
            "recommendations": self._get_performance_recommendations(total_perf, step_perfs)
        }
    
    def _get_performance_recommendations(self, total_perf: Optional[Dict], step_perfs: Dict) -> list:
        """Generate performance improvement recommendations"""
        recommendations = []
        
        if not total_perf:
            return ["No performance data available"]
        
        total_duration = total_perf.get("total_duration", 0)
        
        if total_duration > self.TARGETS["total_onboarding"]:
            recommendations.append("⚠️ Overall onboarding time exceeds 60s target")
        
        # Analyze individual steps
        for step, perf in step_perfs.items():
            duration = perf.get("duration", 0)
            target = perf.get("target", 15)
            
            if duration > target:
                recommendations.append(f"🔧 Optimize '{step}' step (took {duration:.1f}s, target: {target}s)")
        
        # Specific recommendations based on step analysis
        email_perf = step_perfs.get("verify_otp", {})
        if email_perf.get("duration", 0) > self.TARGETS["email_otp_delivery"]:
            recommendations.append("📧 Consider async email processing or faster email service")
        
        if not recommendations:
            recommendations.append("✅ Performance within all targets")
        
        return recommendations

# Global performance monitor instance
onboarding_perf_monitor = OnboardingPerformanceMonitor()

def track_onboarding_performance(step: str):
    """Decorator to track performance of onboarding functions"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract user_id from function arguments
            user_id = None
            if args:
                user_id = args[0] if isinstance(args[0], int) else getattr(args[0], 'user_id', None)
            if not user_id and 'user_id' in kwargs:
                user_id = kwargs['user_id']
            
            if user_id:
                onboarding_perf_monitor.start_step_timing(user_id, step)
            
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.perf_counter() - start_time
                if user_id:
                    onboarding_perf_monitor.end_step_timing(user_id, step)
                
                # Log function performance
                target = OnboardingPerformanceMonitor.TARGETS.get(step, 15.0)
                status = "✅" if duration <= target else "⚠️"
                logger.debug(f"{status} {func.__name__} completed in {duration:.3f}s (target: {target}s)")
        
        @wraps(func) 
        def sync_wrapper(*args, **kwargs):
            # Extract user_id from function arguments
            user_id = None
            if args:
                user_id = args[0] if isinstance(args[0], int) else getattr(args[0], 'user_id', None)
            if not user_id and 'user_id' in kwargs:
                user_id = kwargs['user_id']
            
            if user_id:
                onboarding_perf_monitor.start_step_timing(user_id, step)
            
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.perf_counter() - start_time
                if user_id:
                    onboarding_perf_monitor.end_step_timing(user_id, step)
                
                # Log function performance
                target = OnboardingPerformanceMonitor.TARGETS.get(step, 15.0)
                status = "✅" if duration <= target else "⚠️"
                logger.debug(f"{status} {func.__name__} completed in {duration:.3f}s (target: {target}s)")
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator