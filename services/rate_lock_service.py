"""
Rate Lock Service for 10-minute price protection on wallet deposits
Ensures users get guaranteed exchange rates during deposit process
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass
from config import Config
from services.fastforex_service import fastforex_service
from services.crypto import CryptoServiceAtomic

logger = logging.getLogger(__name__)


@dataclass
class RateLock:
    """Data class for rate lock information"""

    lock_id: str
    currency: str
    usd_rate: float
    ngn_rate: float
    locked_at: datetime
    expires_at: datetime
    user_id: int
    is_expired: bool = False


class RateLockService:
    """Service for managing 10-minute rate locks on deposit quotes"""

    def __init__(self):
        self.rate_locks: Dict[str, RateLock] = {}
        self.lock_duration_minutes = 10
        self.cleanup_task = None

    async def start_cleanup_task(self):
        """Start background task to cleanup expired rate locks"""
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._cleanup_expired_locks())
            logger.info("Rate lock cleanup task started")

    async def _cleanup_expired_locks(self):
        """Background task to remove expired rate locks every minute"""
        while True:
            try:
                now = datetime.utcnow()
                expired_keys = []

                for lock_id, rate_lock in self.rate_locks.items():
                    if now > rate_lock.expires_at:
                        expired_keys.append(lock_id)

                for key in expired_keys:
                    del self.rate_locks[key]
                    logger.debug(f"Cleaned up expired rate lock: {key}")

                if expired_keys:
                    logger.info(f"Cleaned up {len(expired_keys)} expired rate locks")

            except Exception as e:
                logger.error(f"Error in rate lock cleanup task: {e}")

            # Wait 60 seconds before next cleanup
            await asyncio.sleep(60)

    async def create_rate_lock(self, currency: str, user_id: int) -> RateLock:
        """Create a new 10-minute rate lock for deposit protection"""
        try:
            # Get current real-time rates
            usd_rate = await CryptoServiceAtomic.get_real_time_exchange_rate(currency)
            ngn_rate = await fastforex_service.get_usd_to_ngn_rate_clean()

            if not ngn_rate:
                raise ValueError("Unable to get NGN exchange rate")

            # Generate unique lock ID
            lock_id = f"rate_lock_{user_id}_{currency}_{datetime.utcnow().timestamp()}"

            # Create rate lock with 10-minute protection
            now = datetime.utcnow()
            expires_at = now + timedelta(minutes=self.lock_duration_minutes)

            rate_lock = RateLock(
                lock_id=lock_id,
                currency=currency,
                usd_rate=usd_rate,
                ngn_rate=ngn_rate,
                locked_at=now,
                expires_at=expires_at,
                user_id=user_id,
            )

            # Store in memory (for high performance)
            self.rate_locks[lock_id] = rate_lock

            logger.info(
                f"Created rate lock {lock_id} for {currency} @ ${usd_rate:.2f} USD, ₦{ngn_rate:.2f}/USD"
            )
            return rate_lock

        except Exception as e:
            logger.error(f"Error creating rate lock for {currency}: {e}")
            raise

    def get_rate_lock(self, lock_id: str) -> Optional[RateLock]:
        """Get rate lock by ID, returns None if expired or not found"""
        rate_lock = self.rate_locks.get(lock_id)

        if not rate_lock:
            return None

        # Check if expired
        if datetime.utcnow() > rate_lock.expires_at:
            rate_lock.is_expired = True
            # Remove from memory
            del self.rate_locks[lock_id]
            return None

        return rate_lock

    def get_user_active_locks(self, user_id: int) -> List[RateLock]:
        """Get all active rate locks for a user"""
        active_locks = []
        now = datetime.utcnow()

        for rate_lock in self.rate_locks.values():
            if rate_lock.user_id == user_id and now <= rate_lock.expires_at:
                active_locks.append(rate_lock)

        return active_locks

    def calculate_locked_amounts(
        self, rate_lock: RateLock, usd_amount: float
    ) -> Dict[str, float]:
        """Calculate equivalent amounts using locked rates"""
        try:
            # Apply markup to locked rates
            markup_percentage = getattr(Config, "EXCHANGE_MARKUP_PERCENTAGE", 5) / 100

            # Calculate crypto amount using locked USD rate
            crypto_amount = usd_amount / rate_lock.usd_rate

            # Calculate NGN amount using locked NGN rate with markup
            ngn_rate_with_markup = rate_lock.ngn_rate * (1 + markup_percentage)
            ngn_amount = usd_amount * ngn_rate_with_markup

            return {
                "usd_amount": usd_amount,
                "crypto_amount": crypto_amount,
                "ngn_amount": ngn_amount,
                "usd_rate": rate_lock.usd_rate,
                "ngn_rate": ngn_rate_with_markup,
            }

        except Exception as e:
            logger.error(f"Error calculating locked amounts: {e}")
            raise

    def get_remaining_time(self, rate_lock: RateLock) -> int:
        """Get remaining time in seconds for rate lock"""
        now = datetime.utcnow()
        if now >= rate_lock.expires_at:
            return 0

        remaining = rate_lock.expires_at - now
        return int(remaining.total_seconds())

    def extend_rate_lock(self, lock_id: str, additional_minutes: int = 5) -> bool:
        """Extend rate lock by additional minutes (max 5 minutes)"""
        rate_lock = self.rate_locks.get(lock_id)

        if not rate_lock:
            return False

        # Only allow extension if not already expired
        if datetime.utcnow() > rate_lock.expires_at:
            return False

        # Extend by up to 5 additional minutes
        additional_minutes = min(additional_minutes, 5)
        rate_lock.expires_at += timedelta(minutes=additional_minutes)

        logger.info(f"Extended rate lock {lock_id} by {additional_minutes} minutes")
        return True


# Global instance
rate_lock_service = RateLockService()
