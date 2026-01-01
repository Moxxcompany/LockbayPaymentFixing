"""
Rate Limiting Middleware
Prevents abuse and spam by limiting requests per user
"""

import time
from typing import Dict, Optional, Tuple
from functools import wraps
import logging
from utils.callback_utils import safe_answer_callback_query

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self):
        self._user_requests: Dict[int, list] = {}  # user_id -> [timestamp, ...]
        self._command_requests: Dict[Tuple[int, str], list] = (
            {}
        )  # (user_id, command) -> [timestamp, ...]

    def is_rate_limited(
        self,
        user_id: int,
        command: str = "general",
        max_requests: int = 10,
        window_seconds: int = 60,
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if user is rate limited

        Args:
            user_id: Telegram user ID
            command: Command or action being performed
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_limited, seconds_until_reset)
        """
        now = time.time()
        cutoff = now - window_seconds

        # Clean old requests
        key = (user_id, command)
        if key not in self._command_requests:
            self._command_requests[key] = []

        # Remove expired requests
        self._command_requests[key] = [
            req_time for req_time in self._command_requests[key] if req_time > cutoff
        ]

        # Check if limit exceeded
        if len(self._command_requests[key]) >= max_requests:
            oldest_request = min(self._command_requests[key])
            reset_time = int(oldest_request + window_seconds - now)
            return True, max(1, reset_time)

        # Add current request
        self._command_requests[key].append(now)
        return False, None

    def reset_user_limits(self, user_id: int):
        """Reset all limits for a user (admin function)"""
        keys_to_remove = [
            key for key in self._command_requests.keys() if key[0] == user_id
        ]
        for key in keys_to_remove:
            del self._command_requests[key]

        if user_id in self._user_requests:
            del self._user_requests[user_id]


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(
    max_requests: int = 10, window_seconds: int = 60, command: str = "general"
):
    """
    Decorator for rate limiting telegram handlers

    Usage:
        @rate_limit(max_requests=5, window_seconds=60, command="create_escrow")
        async def create_escrow_handler(update, context):
            ...
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(update, context):
            if not update.effective_user:
                return await func(update, context)

            user_id = update.effective_user.id

            # Skip rate limiting for admins
            from config_admin import AdminConfig

            if AdminConfig.is_admin(user_id):
                return await func(update, context)

            # Check rate limit
            is_limited, reset_time = rate_limiter.is_rate_limited(
                user_id, command, max_requests, window_seconds
            )

            if is_limited:
                logger.warning(
                    f"Rate limit exceeded for user {user_id} on command {command}"
                )

                # Send rate limit message
                message = f"⏱️ Rate limit exceeded\n\nToo many {command} requests. Please wait {reset_time} seconds and try again."

                if update.message:
                    await update.message.reply_text(message, parse_mode="Markdown")
                elif update.callback_query:
                    await safe_answer_callback_query(
                        update.callback_query,
                        f"Rate limited. Wait {reset_time}s",
                        show_alert=True
                    )

                return None

            return await func(update, context)

        return wrapper

    return decorator


# Rate limiting configurations for different actions
RATE_LIMITS = {
    # CRITICAL - Payment and cashout endpoints
    "payment": {
        "max_requests": 5,
        "window_seconds": 60,
    },  # 5 payment requests per minute
    "cashout": {
        "max_requests": 3,
        "window_seconds": 60,
    },  # 3 cashout requests per minute
    "exchange": {
        "max_requests": 10,
        "window_seconds": 60,
    },  # 10 exchange requests per minute
    
    # Standard endpoints
    "create_escrow": {
        "max_requests": 3,
        "window_seconds": 300,
    },  # 3 escrows per 5 minutes
    "send_message": {
        "max_requests": 20,
        "window_seconds": 60,
    },  # 20 messages per minute
    "wallet_action": {
        "max_requests": 10,
        "window_seconds": 60,
    },  # 10 wallet actions per minute
    "dispute_action": {
        "max_requests": 5,
        "window_seconds": 300,
    },  # 5 dispute actions per 5 minutes
    
    # Admin endpoints
    "admin": {
        "max_requests": 50,
        "window_seconds": 60,
    },  # 50 admin actions per minute
    
    # Default
    "general": {
        "max_requests": 30,
        "window_seconds": 60,
    },  # 30 general actions per minute
}


def get_rate_limit_config(command: str) -> dict:
    """Get rate limit configuration for a command"""
    return RATE_LIMITS.get(command, RATE_LIMITS["general"])
