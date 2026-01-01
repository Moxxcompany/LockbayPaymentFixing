"""
Webhook Rate Limiter Service - Controls webhook request rates
Provides rate limiting functionality for webhook endpoints
"""

import time
from typing import Dict, Any
from collections import defaultdict, deque

class WebhookRateLimiter:
    """Rate limiter for webhook endpoints"""
    
    def __init__(self, max_requests: int = None, time_window: int = None):
        """
        Initialize rate limiter with configurable limits
        
        Args:
            max_requests: Maximum requests per time window (default from config)
            time_window: Time window in seconds (default from config)
        """
        # Import Config here to avoid circular imports
        from config import Config
        
        self.max_requests = max_requests or getattr(Config, 'WEBHOOK_RATE_LIMIT_REQUESTS', 5)
        self.time_window = time_window or getattr(Config, 'WEBHOOK_RATE_LIMIT_WINDOW', 60)
        self.request_history = defaultdict(deque)
    
    def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed based on rate limits
        
        Args:
            identifier: Unique identifier for the requester (IP, user ID, etc.)
            
        Returns:
            True if request is allowed, False if rate limited
        """
        current_time = time.time()
        history = self.request_history[identifier]
        
        # Remove old requests outside the time window
        while history and history[0] <= current_time - self.time_window:
            history.popleft()
        
        # Check if under rate limit
        if len(history) < self.max_requests:
            history.append(current_time)
            return True
        
        return False
    
    def get_remaining_requests(self, identifier: str) -> int:
        """Get remaining requests for identifier"""
        current_time = time.time()
        history = self.request_history[identifier]
        
        # Remove old requests
        while history and history[0] <= current_time - self.time_window:
            history.popleft()
        
        return max(0, self.max_requests - len(history))

# Global rate limiter instance
webhook_rate_limiter = WebhookRateLimiter()

async def check_rate_limit(identifier: str) -> bool:
    """
    Check rate limit for webhook requests - returns boolean as expected by tests
    
    Args:
        identifier: Unique identifier for the requester
        
    Returns:
        True if request is allowed, False if rate limited
    """
    return webhook_rate_limiter.is_allowed(identifier)

async def get_rate_limit_status(identifier: str) -> Dict[str, Any]:
    """
    Get detailed rate limit status for diagnostic purposes
    
    Args:
        identifier: Unique identifier for the requester
        
    Returns:
        Dictionary with detailed rate limit status
    """
    is_allowed = webhook_rate_limiter.is_allowed(identifier)
    remaining = webhook_rate_limiter.get_remaining_requests(identifier)
    
    return {
        "allowed": is_allowed,
        "remaining_requests": remaining,
        "max_requests": webhook_rate_limiter.max_requests,
        "time_window": webhook_rate_limiter.time_window,
        "message": "Request allowed" if is_allowed else "Rate limit exceeded"
    }

def check_rate_limit_sync(identifier: str) -> Dict[str, Any]:
    """
    Synchronous version of rate limit check
    
    Args:
        identifier: Unique identifier for the requester
        
    Returns:
        Dictionary with rate limit status
    """
    is_allowed = webhook_rate_limiter.is_allowed(identifier)
    remaining = webhook_rate_limiter.get_remaining_requests(identifier)
    
    return {
        "allowed": is_allowed,
        "remaining_requests": remaining,
        "max_requests": webhook_rate_limiter.max_requests,
        "time_window": webhook_rate_limiter.time_window,
        "message": "Request allowed" if is_allowed else "Rate limit exceeded"
    }

def reset_rate_limits():
    """Reset all rate limits - for testing purposes"""
    webhook_rate_limiter.request_history.clear()