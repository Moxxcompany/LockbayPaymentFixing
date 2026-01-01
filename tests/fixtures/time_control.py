"""
Time Control Fixtures
Comprehensive time manipulation for deterministic testing
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Union, Callable, Any
from unittest.mock import patch, MagicMock
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class FrozenTime:
    """
    Comprehensive time freezing utility for testing
    
    Features:
    - Freeze datetime.now(), time.time(), asyncio sleep functions
    - Support for time advancement and time travel
    - Timezone-aware time manipulation
    - Database timestamp consistency
    """
    
    def __init__(self, frozen_time: Union[datetime, str, float]):
        if isinstance(frozen_time, str):
            # Parse ISO string
            self.frozen_time = datetime.fromisoformat(frozen_time.replace('Z', '+00:00'))
        elif isinstance(frozen_time, float):
            # Unix timestamp
            self.frozen_time = datetime.fromtimestamp(frozen_time, tz=timezone.utc)
        elif isinstance(frozen_time, datetime):
            # Ensure timezone-aware
            if frozen_time.tzinfo is None:
                self.frozen_time = frozen_time.replace(tzinfo=timezone.utc)
            else:
                self.frozen_time = frozen_time
        else:
            raise ValueError(f"Unsupported frozen_time type: {type(frozen_time)}")
            
        self.original_datetime = datetime
        self.original_time = time
        self.start_time = self.frozen_time
        self.patches = []
        
    def __enter__(self):
        """Start time freezing with comprehensive patching"""
        
        # Create mock datetime class
        mock_datetime = MagicMock()
        mock_datetime.now = self._mock_datetime_now
        mock_datetime.utcnow = self._mock_datetime_utcnow
        mock_datetime.fromtimestamp = self._mock_datetime_fromtimestamp
        
        # Preserve other datetime methods
        for attr in ['date', 'time', 'timedelta', 'timezone', 'fromisoformat', 'strptime']:
            if hasattr(self.original_datetime, attr):
                setattr(mock_datetime, attr, getattr(self.original_datetime, attr))
        
        # Create mock time module
        mock_time = MagicMock()
        mock_time.time = self._mock_time_time
        mock_time.sleep = self._mock_time_sleep
        
        # Preserve other time functions
        for attr in ['gmtime', 'localtime', 'strftime', 'mktime']:
            if hasattr(self.original_time, attr):
                setattr(mock_time, attr, getattr(self.original_time, attr))
        
        # Start patches
        patches_config = [
            ('datetime.datetime', mock_datetime),
            ('time.time', self._mock_time_time),
            ('time.sleep', self._mock_time_sleep),
            ('asyncio.sleep', self._mock_asyncio_sleep),
            
            # Patch common imports in services
            ('services.onboarding_service.datetime', mock_datetime),
            ('services.fincra_service.datetime', mock_datetime),
            ('services.kraken_service.datetime', mock_datetime),
            ('services.unified_transaction_service.datetime', mock_datetime),
            ('handlers.onboarding_router.datetime', mock_datetime),
            ('handlers.escrow.datetime', mock_datetime),
            ('handlers.admin.datetime', mock_datetime),
            
            # Model timestamps
            ('models.datetime', mock_datetime),
            ('sqlalchemy.func.now', self._mock_sql_now)
        ]
        
        for target, replacement in patches_config:
            try:
                patch_obj = patch(target, new=replacement)
                self.patches.append(patch_obj)
                patch_obj.start()
            except (ImportError, AttributeError) as e:
                logger.debug(f"Could not patch {target}: {e}")
        
        logger.info(f"🕐 Time frozen at: {self.frozen_time.isoformat()}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop time freezing and restore original functions"""
        for patch_obj in self.patches:
            try:
                patch_obj.stop()
            except Exception as e:
                logger.debug(f"Error stopping patch: {e}")
        
        self.patches.clear()
        logger.info("🕐 Time unfrozen")
    
    def _mock_datetime_now(self, tz=None):
        """Mock datetime.now() to return frozen time"""
        if tz is None:
            tz = timezone.utc
        return self.frozen_time.astimezone(tz)
    
    def _mock_datetime_utcnow(self):
        """Mock datetime.utcnow() to return frozen UTC time"""
        return self.frozen_time.replace(tzinfo=None)
    
    def _mock_datetime_fromtimestamp(self, timestamp, tz=None):
        """Mock datetime.fromtimestamp() based on frozen time offset"""
        if tz is None:
            tz = timezone.utc
        # Calculate offset and apply to frozen time
        current_offset = timestamp - time.time()
        return (self.frozen_time + timedelta(seconds=current_offset)).astimezone(tz)
    
    def _mock_time_time(self):
        """Mock time.time() to return frozen timestamp"""
        return self.frozen_time.timestamp()
    
    def _mock_time_sleep(self, seconds):
        """Mock time.sleep() - advances frozen time instead of sleeping"""
        self.advance_time(seconds)
    
    async def _mock_asyncio_sleep(self, delay):
        """Mock asyncio.sleep() - advances frozen time instantly"""
        self.advance_time(delay)
        # No actual sleep, return immediately for fast tests
    
    def _mock_sql_now(self):
        """Mock SQLAlchemy func.now() for database timestamps"""
        return self.frozen_time
    
    def advance_time(self, seconds: Union[int, float]):
        """Advance frozen time by specified seconds"""
        self.frozen_time += timedelta(seconds=seconds)
        logger.debug(f"⏰ Time advanced by {seconds}s to: {self.frozen_time.isoformat()}")
    
    def advance_time_by(self, **kwargs):
        """Advance frozen time by timedelta kwargs"""
        delta = timedelta(**kwargs)
        self.frozen_time += delta
        logger.debug(f"⏰ Time advanced by {delta} to: {self.frozen_time.isoformat()}")
    
    def set_time(self, new_time: Union[datetime, str, float]):
        """Jump to a specific time"""
        if isinstance(new_time, str):
            self.frozen_time = datetime.fromisoformat(new_time.replace('Z', '+00:00'))
        elif isinstance(new_time, float):
            self.frozen_time = datetime.fromtimestamp(new_time, tz=timezone.utc)
        elif isinstance(new_time, datetime):
            if new_time.tzinfo is None:
                self.frozen_time = new_time.replace(tzinfo=timezone.utc)
            else:
                self.frozen_time = new_time
        logger.info(f"🕐 Time set to: {self.frozen_time.isoformat()}")
    
    def get_current_time(self) -> datetime:
        """Get the current frozen time"""
        return self.frozen_time


@contextmanager
def freeze_time(frozen_time: Union[datetime, str, float]):
    """
    Context manager for freezing time
    
    Usage:
        with freeze_time("2025-09-19T10:00:00Z") as frozen:
            # Time is frozen at 2025-09-19 10:00:00 UTC
            frozen.advance_time(3600)  # Advance by 1 hour
            # Now it's 2025-09-19 11:00:00 UTC
    """
    frozen = FrozenTime(frozen_time)
    with frozen:
        yield frozen


@pytest.fixture
def frozen_time():
    """
    Pytest fixture for time freezing
    
    Usage:
        def test_something(frozen_time):
            with frozen_time("2025-09-19T10:00:00Z") as ft:
                # Test with frozen time
                ft.advance_time(60)
    """
    return freeze_time


@pytest.fixture
def frozen_time_2025():
    """
    Pytest fixture with pre-configured time for 2025 testing
    """
    with freeze_time("2025-09-19T10:00:00Z") as ft:
        yield ft


# Specific time fixtures for common test scenarios
@pytest.fixture
def time_onboarding_start():
    """Time fixture for onboarding flow start"""
    with freeze_time("2025-09-19T09:00:00Z") as ft:
        yield ft


@pytest.fixture  
def time_escrow_creation():
    """Time fixture for escrow creation scenarios"""
    with freeze_time("2025-09-19T14:30:00Z") as ft:
        yield ft


@pytest.fixture
def time_crypto_withdrawal():
    """Time fixture for crypto withdrawal scenarios"""
    with freeze_time("2025-09-19T16:45:00Z") as ft:
        yield ft