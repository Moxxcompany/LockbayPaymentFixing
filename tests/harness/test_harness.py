"""
Comprehensive Test Harness
Integrates all Phase 1 testing infrastructure components
"""

import pytest
import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from contextlib import contextmanager
from datetime import datetime

# Import all Phase 1 components
from tests.providers.provider_factory import provider_factory
from tests.fixtures.time_control import freeze_time
from tests.fixtures.randomness_control import seed_random
from tests.fixtures.network_blocker import block_network_calls

logger = logging.getLogger(__name__)


class TestHarness:
    """
    Comprehensive test harness that integrates all testing infrastructure
    
    Features:
    - Provider fakes management
    - Time control with freezing and advancement
    - Deterministic randomness
    - Network isolation
    - Scenario-based testing configurations
    - Telegram Update/Context factories
    - Database state management
    """
    
    def __init__(self,
                 scenario: str = "success",
                 frozen_time: Optional[Union[str, datetime]] = None,
                 random_seed: int = 42,
                 block_network: bool = True,
                 network_whitelist: Optional[List[str]] = None):
        """
        Initialize test harness with configuration
        
        Args:
            scenario: Test scenario ("success", "network_failures", "auth_failures", etc.)
            frozen_time: Time to freeze at (defaults to 2025-09-19T10:00:00Z)
            random_seed: Seed for deterministic randomness
            block_network: Whether to block external network calls
            network_whitelist: Domains to allow through network blocker
        """
        self.scenario = scenario
        self.frozen_time = frozen_time or "2025-09-19T10:00:00Z"
        self.random_seed = random_seed
        self.block_network = block_network
        self.network_whitelist = network_whitelist or ['localhost', 'test.lockbay.io']
        
        # Active contexts
        self._provider_context = None
        self._time_context = None
        self._random_context = None
        self._network_context = None
        
        # Provider factory
        self.provider_factory = provider_factory
        
    def __enter__(self):
        """Start comprehensive test harness"""
        logger.info(f"🧪 Starting Test Harness (scenario: {self.scenario})")
        
        try:
            # 1. Configure provider fakes scenario
            self.provider_factory.configure_scenario(self.scenario)
            
            # 2. Start provider patches
            self._provider_context = self.provider_factory.patch_all_providers()
            self._provider_context.__enter__()
            
            # 3. Start time freezing
            from tests.fixtures.time_control import freeze_time
            self._time_context = freeze_time(self.frozen_time)
            self.frozen_time_control = self._time_context.__enter__()
            
            # 4. Start deterministic randomness
            from tests.fixtures.randomness_control import seed_random
            self._random_context = seed_random(self.random_seed)
            self.random_control = self._random_context.__enter__()
            
            # 5. Start network blocking if enabled
            if self.block_network:
                from tests.fixtures.network_blocker import block_network_calls
                self._network_context = block_network_calls(
                    whitelist_domains=self.network_whitelist,
                    allow_localhost=True
                )
                self.network_blocker = self._network_context.__enter__()
            
            logger.info("✅ Test Harness fully initialized")
            return self
            
        except Exception as e:
            logger.error(f"❌ Test Harness initialization failed: {e}")
            self.__exit__(None, None, None)
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop comprehensive test harness"""
        logger.info("🧪 Stopping Test Harness")
        
        # Stop contexts in reverse order
        contexts = [
            (self._network_context, "network blocker"),
            (self._random_context, "randomness control"),
            (self._time_context, "time control"),
            (self._provider_context, "provider patches")
        ]
        
        for context, name in contexts:
            if context:
                try:
                    context.__exit__(exc_type, exc_val, exc_tb)
                except Exception as e:
                    logger.debug(f"Error stopping {name}: {e}")
        
        # Clear all contexts
        self._provider_context = None
        self._time_context = None
        self._random_context = None
        self._network_context = None
        
        logger.info("✅ Test Harness stopped")
    
    # Provider Management
    @property
    def fincra(self):
        """Access Fincra fake provider"""
        return self.provider_factory.fincra
    
    @property
    def kraken(self):
        """Access Kraken fake provider"""
        return self.provider_factory.kraken
    
    @property
    def fastforex(self):
        """Access FastForex fake provider"""
        return self.provider_factory.fastforex
    
    @property
    def telegram(self):
        """Access Telegram fake provider"""
        return self.provider_factory.telegram
    
    @property
    def email(self):
        """Access Email fake provider"""
        return self.provider_factory.email
    
    def reset_providers(self):
        """Reset all provider fakes to clean state"""
        self.provider_factory.reset_all_providers()
        logger.info("🔄 All providers reset")
    
    def configure_scenario(self, scenario_name: str):
        """Reconfigure test scenario during test execution"""
        self.provider_factory.configure_scenario(scenario_name)
        self.scenario = scenario_name
        logger.info(f"🎭 Scenario changed to: {scenario_name}")
    
    # Time Management
    def advance_time(self, seconds: Union[int, float]):
        """Advance frozen time by seconds"""
        if self.frozen_time_control:
            self.frozen_time_control.advance_time(seconds)
    
    def advance_time_by(self, **kwargs):
        """Advance frozen time by timedelta kwargs"""
        if self.frozen_time_control:
            self.frozen_time_control.advance_time_by(**kwargs)
    
    def set_time(self, new_time: Union[str, datetime]):
        """Jump to specific time"""
        if self.frozen_time_control:
            self.frozen_time_control.set_time(new_time)
    
    def get_current_time(self) -> datetime:
        """Get current frozen time"""
        if self.frozen_time_control:
            return self.frozen_time_control.get_current_time()
        return datetime.now()
    
    # Randomness Management
    def get_deterministic_otp(self) -> str:
        """Get next deterministic OTP"""
        if self.random_control:
            return self.random_control.get_deterministic_otp()
        return "123456"  # Fallback
    
    def get_deterministic_reference(self, prefix: str = "TEST") -> str:
        """Generate deterministic reference ID"""
        if self.random_control:
            return self.random_control.get_deterministic_reference(prefix)
        return f"{prefix}_42_001001"  # Fallback
    
    def reset_random(self):
        """Reset random counters"""
        if self.random_control:
            self.random_control.reset_counters()
    
    # Telegram Utilities
    def create_user_update(self,
                          user_id: int,
                          message_text: str,
                          first_name: str = "Test",
                          last_name: str = "User",
                          username: Optional[str] = None):
        """Create realistic Telegram Update for user message"""
        return self.telegram.create_update_object(
            user_id=user_id,
            message_text=message_text,
            first_name=first_name,
            last_name=last_name,
            username=username
        )
    
    def create_callback_update(self,
                              user_id: int,
                              callback_data: str,
                              message_id: Optional[int] = None,
                              first_name: str = "Test",
                              last_name: str = "User"):
        """Create realistic Telegram Update for callback query"""
        return self.telegram.create_update_object(
            user_id=user_id,
            callback_data=callback_data,
            message_id=message_id,
            first_name=first_name,
            last_name=last_name
        )
    
    def create_context(self,
                      user_data: Optional[Dict] = None,
                      chat_data: Optional[Dict] = None,
                      bot_data: Optional[Dict] = None):
        """Create realistic Telegram Context for handlers"""
        return self.telegram.create_context_object(
            user_data=user_data,
            chat_data=chat_data,
            bot_data=bot_data
        )
    
    # Network Management
    def get_blocked_calls(self) -> List[str]:
        """Get list of blocked network calls"""
        if self.network_blocker:
            return self.network_blocker.get_blocked_calls()
        return []
    
    def clear_blocked_calls(self):
        """Clear blocked network calls history"""
        if self.network_blocker:
            self.network_blocker.clear_blocked_calls()
    
    # Comprehensive State Management
    def reset_all_state(self):
        """Reset all harness state for clean test isolation"""
        self.reset_providers()
        self.reset_random()
        self.clear_blocked_calls()
        logger.info("🔄 All test harness state reset")
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all harness components"""
        status = {
            "scenario": self.scenario,
            "current_time": self.get_current_time().isoformat(),
            "random_seed": self.random_seed,
            "network_blocked": self.block_network,
            "providers_status": {
                "fincra": {
                    "failure_mode": self.fincra.failure_mode,
                    "balance_ngn": float(self.fincra.balance_ngn),
                    "request_count": len(self.fincra.get_request_history())
                },
                "kraken": {
                    "failure_mode": self.kraken.failure_mode,
                    "balances": {k: float(v) for k, v in self.kraken.balances.items()},
                    "request_count": len(self.kraken.get_request_history())
                },
                "fastforex": {
                    "failure_mode": self.fastforex.failure_mode,
                    "request_count": len(self.fastforex.get_request_history())
                },
                "telegram": {
                    "failure_mode": self.telegram.failure_mode,
                    "messages_sent": len(self.telegram.get_sent_messages())
                },
                "email": {
                    "failure_mode": self.email.failure_mode,
                    "emails_sent": len(self.email.get_sent_emails())
                }
            }
        }
        
        if self.block_network:
            status["network_status"] = {
                "blocked_calls": len(self.get_blocked_calls())
            }
        
        return status


@contextmanager
def comprehensive_test_harness(
    scenario: str = "success",
    frozen_time: Optional[Union[str, datetime]] = None,
    random_seed: int = 42,
    block_network: bool = True,
    network_whitelist: Optional[List[str]] = None
):
    """
    Context manager for comprehensive test harness
    
    Usage:
        with comprehensive_test_harness(scenario="success") as harness:
            # All external services are mocked
            # Time is frozen at 2025-09-19T10:00:00Z
            # Random values are deterministic
            # Network calls are blocked
            
            update = harness.create_user_update(user_id=123, message_text="/start")
            context = harness.create_context()
            
            # Test handler
            result = await handler(update, context)
            
            # Verify interactions
            assert len(harness.telegram.get_sent_messages()) == 1
    """
    harness = TestHarness(
        scenario=scenario,
        frozen_time=frozen_time,
        random_seed=random_seed,
        block_network=block_network,
        network_whitelist=network_whitelist
    )
    
    with harness:
        yield harness


# Pytest fixtures for easy integration
@pytest.fixture
def test_harness():
    """Basic test harness fixture"""
    with comprehensive_test_harness() as harness:
        yield harness


@pytest.fixture
def success_harness():
    """Test harness configured for success scenario"""
    with comprehensive_test_harness(scenario="success") as harness:
        yield harness


@pytest.fixture  
def network_failure_harness():
    """Test harness configured for network failure scenario"""
    with comprehensive_test_harness(scenario="network_failures") as harness:
        yield harness


@pytest.fixture
def auth_failure_harness():
    """Test harness configured for authentication failure scenario"""  
    with comprehensive_test_harness(scenario="auth_failures") as harness:
        yield harness


@pytest.fixture
def insufficient_funds_harness():
    """Test harness configured for insufficient funds scenario"""
    with comprehensive_test_harness(scenario="insufficient_funds") as harness:
        yield harness


@pytest.fixture
def mixed_failure_harness():
    """Test harness configured for mixed failure scenario"""
    with comprehensive_test_harness(scenario="mixed_failures") as harness:
        yield harness