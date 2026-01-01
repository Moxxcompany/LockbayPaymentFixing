"""
Cache Invalidation System
Ensures cache consistency when user data changes
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


class CacheInvalidator:
    """Manages cache invalidation for user data changes"""
    
    @staticmethod
    def invalidate_user_caches(user_id: int, reason: str = "user_data_change"):
        """
        Invalidate all caches for a specific user
        Called when user balance or status changes
        """
        from utils.performance_cache import PerformanceCache
        
        # Invalidate user-specific caches
        PerformanceCache.invalidate_user_cache(user_id)
        
        logger.debug(f"Cache invalidated for user {user_id}: {reason}")
    
    @staticmethod
    def invalidate_on_transaction(user_ids: List[int], transaction_type: str = "generic"):
        """
        Invalidate caches for multiple users involved in a transaction
        """
        for user_id in user_ids:
            CacheInvalidator.invalidate_user_caches(
                user_id, f"transaction_{transaction_type}"
            )
    
    @staticmethod
    def invalidate_on_escrow_change(escrow_id: str, buyer_id: int, seller_id: int | None = None):
        """
        Invalidate caches when escrow status changes
        """
        users_to_invalidate = [buyer_id]
        if seller_id:
            users_to_invalidate.append(seller_id)
        
        CacheInvalidator.invalidate_on_transaction(
            users_to_invalidate, f"escrow_{escrow_id}"
        )
    
    @staticmethod
    def invalidate_on_cashout(user_id: int, amount: float):
        """
        Invalidate caches after cashout processing
        """
        CacheInvalidator.invalidate_user_caches(
            user_id, f"cashout_{amount}"
        )