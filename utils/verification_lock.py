"""Thread-safe lock for bank verification to prevent duplicate processing"""

import asyncio
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Global locks per user to prevent duplicate verification
_user_verification_locks: Dict[int, asyncio.Lock] = {}


def get_verification_lock(user_id: int) -> asyncio.Lock:
    """Get or create a verification lock for a specific user"""
    if user_id not in _user_verification_locks:
        _user_verification_locks[user_id] = asyncio.Lock()
    return _user_verification_locks[user_id]


async def is_verification_running(user_id: int) -> bool:
    """Check if verification is currently running for a user"""
    lock = get_verification_lock(user_id)
    return lock.locked()


def cleanup_lock(user_id: int):
    """Clean up the lock for a user after verification completes"""
    if user_id in _user_verification_locks:
        del _user_verification_locks[user_id]
