"""
Exception Handler Module
Provides custom exceptions and error handling decorators
"""

import logging
import functools
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom validation error for input validation failures"""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def safe_telegram_handler(func: Callable) -> Callable:
    """
    Decorator to safely handle telegram handler functions
    Catches exceptions and logs them without crashing the bot
    """
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in telegram handler {func.__name__}: {e}")
            logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
            # Don't re-raise to prevent bot crashes
            return None
    
    return wrapper