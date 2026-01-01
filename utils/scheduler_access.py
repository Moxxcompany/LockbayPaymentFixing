"""
Global Scheduler Access Utility
Provides access to the main scheduler instance across the application
"""

import logging
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

# Global scheduler instance reference
_global_scheduler: Optional[AsyncIOScheduler] = None


def set_global_scheduler(scheduler: AsyncIOScheduler):
    """Set the global scheduler instance"""
    global _global_scheduler
    _global_scheduler = scheduler
    logger.info("Global scheduler instance registered")


def get_global_scheduler() -> Optional[AsyncIOScheduler]:
    """Get the global scheduler instance"""
    return _global_scheduler


def is_scheduler_available() -> bool:
    """Check if scheduler is available"""
    return _global_scheduler is not None and _global_scheduler.running