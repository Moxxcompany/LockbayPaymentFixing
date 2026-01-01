"""
Provider Fake Factory
Central factory for creating and managing test double providers
"""

import logging
from typing import Dict, Any, Optional, List, Type, Union
from unittest.mock import patch, MagicMock
from contextlib import contextmanager
from .fincra_fake import FincraFakeProvider, fincra_fake
from .kraken_fake import KrakenFakeProvider, kraken_fake
from .fastforex_fake import FastForexFakeProvider, fastforex_fake
from .telegram_fake import TelegramFakeProvider, telegram_fake
from .email_fake import EmailFakeProvider, email_fake

logger = logging.getLogger(__name__)


class ProviderFakeFactory:
    """
    Central factory for creating and managing provider fakes
    
    Features:
    - Centralized provider fake management
    - Cross-provider state management
    - Scenario-based testing configurations
    - Comprehensive patching context managers
    """
    
    def __init__(self):
        # Provider instances
        self.fincra = fincra_fake
        self.kraken = kraken_fake
        self.fastforex = fastforex_fake
        self.telegram = telegram_fake
        self.email = email_fake
        
        # Patch configurations
        self.patch_targets = {
            'fincra': [
                'services.fincra_service.FincraService',
                'services.fincra_service.fincra_service',
                'handlers.wallet_direct.fincra_service',
                'services.core.payment_provider_interface.FincraService'
            ],
            'kraken': [
                'services.kraken_service.KrakenService', 
                'services.kraken_service.kraken_service',
                'handlers.wallet_direct.kraken_service',
                'services.core.payment_provider_interface.KrakenService'
            ],
            'fastforex': [
                'services.fastforex_service.FastForexService',
                'services.fastforex_service.fastforex_service',
                'services.exchange_service.fastforex_service',
                'services.crypto.fastforex_service'
            ],
            'telegram': [
                'telegram.Bot',
                'services.notification_service.Bot',
                'handlers.admin.Bot'
            ],
            'email': [
                'services.email.EmailService',
                'services.async_email_service.AsyncEmailService',
                'services.async_email_service.async_email_service',
                'services.email_verification_service.EmailService'
            ]
        }
    
    def reset_all_providers(self):
        """Reset state for all provider fakes"""
        self.fincra.reset_state()
        self.kraken.reset_state()
        self.fastforex.reset_state()
        self.telegram.reset_state()
        self.email.reset_state()
        logger.info("🔄 All provider fakes reset for test isolation")
    
    def configure_scenario(self, scenario_name: str, **kwargs):
        """
        Configure providers for specific test scenarios
        
        Available scenarios:
        - 'success': All operations succeed
        - 'network_failures': Network connectivity issues
        - 'auth_failures': Authentication/authorization failures  
        - 'insufficient_funds': Balance/funding issues
        - 'rate_limits': API rate limiting scenarios
        - 'mixed_failures': Mixed success/failure patterns
        """
        self.reset_all_providers()
        
        if scenario_name == "success":
            # All providers in success mode (default)
            logger.info("✅ Configured SUCCESS scenario")
            
        elif scenario_name == "network_failures":
            # Simulate network connectivity issues
            self.fincra.set_failure_mode("api_timeout")
            self.kraken.set_failure_mode("api_timeout")
            self.fastforex.set_failure_mode("api_timeout")
            self.telegram.set_failure_mode("network_error")
            self.email.set_failure_mode("network_error")
            logger.info("🔌 Configured NETWORK_FAILURES scenario")
            
        elif scenario_name == "auth_failures":
            # Simulate authentication/authorization failures
            self.fincra.set_failure_mode("auth_failed")
            self.kraken.set_failure_mode("auth_failed")
            self.fastforex.set_failure_mode("auth_failed")
            self.email.set_failure_mode("auth_failed")
            logger.info("🔐 Configured AUTH_FAILURES scenario")
            
        elif scenario_name == "insufficient_funds":
            # Simulate balance/funding issues
            self.fincra.set_failure_mode("insufficient_funds")
            self.fincra.set_balance(0)  # Zero NGN balance
            self.kraken.set_failure_mode("insufficient_funds")
            self.kraken.set_balance("USD", 0)  # Zero USD balance
            self.kraken.set_balance("BTC", 0)  # Zero BTC balance
            logger.info("💰 Configured INSUFFICIENT_FUNDS scenario")
            
        elif scenario_name == "rate_limits":
            # Simulate API rate limiting
            self.fincra.set_failure_mode("rate_limit")  # Not implemented in FincraFake yet, but structure ready
            self.fastforex.set_failure_mode("rate_limit")
            self.telegram.set_failure_mode("rate_limit")
            self.email.set_failure_mode("rate_limit")
            logger.info("⏱️ Configured RATE_LIMITS scenario")
            
        elif scenario_name == "mixed_failures":
            # Mixed success/failure patterns for chaos testing
            self.fincra.set_failure_mode(None)  # Success
            self.kraken.set_failure_mode("api_timeout")  # Failure
            self.fastforex.set_failure_mode(None)  # Success
            self.telegram.set_failure_mode("network_error")  # Failure  
            self.email.set_failure_mode(None)  # Success
            logger.info("🎭 Configured MIXED_FAILURES scenario")
            
        else:
            logger.warning(f"❓ Unknown scenario: {scenario_name}")
    
    @contextmanager
    def patch_all_providers(self):
        """
        Context manager to patch all external service providers
        Uses comprehensive patching to catch all import variations
        """
        patches = []
        
        try:
            # Patch Fincra service
            for target in self.patch_targets['fincra']:
                try:
                    patches.append(patch(target, new=self.fincra))
                except ImportError:
                    pass  # Skip if module not available
            
            # Patch Kraken service  
            for target in self.patch_targets['kraken']:
                try:
                    patches.append(patch(target, new=self.kraken))
                except ImportError:
                    pass
            
            # Patch FastForex service
            for target in self.patch_targets['fastforex']:
                try:
                    patches.append(patch(target, new=self.fastforex))
                except ImportError:
                    pass
            
            # Patch Email services
            for target in self.patch_targets['email']:
                try:
                    patches.append(patch(target, new=self.email))
                except ImportError:
                    pass
                    
            # Patch Telegram Bot (special handling for Bot class)
            for target in self.patch_targets['telegram']:
                try:
                    # Create a mock Bot that delegates to our fake
                    mock_bot = MagicMock()
                    mock_bot.send_message = self.telegram.send_message
                    mock_bot.edit_message_text = self.telegram.edit_message_text
                    mock_bot.answer_callback_query = self.telegram.answer_callback_query
                    mock_bot.delete_message = self.telegram.delete_message
                    patches.append(patch(target, return_value=mock_bot))
                except ImportError:
                    pass
            
            # Start all patches
            active_patches = []
            for p in patches:
                try:
                    active_patches.append(p.start())
                except Exception as e:
                    logger.debug(f"Failed to start patch: {e}")
            
            logger.info(f"🔧 Started {len(active_patches)} provider patches")
            yield self
            
        finally:
            # Stop all patches
            for p in patches:
                try:
                    p.stop()
                except Exception as e:
                    logger.debug(f"Failed to stop patch: {e}")
            
            logger.info("🔧 Stopped all provider patches")
    
    @contextmanager 
    def patch_specific_providers(self, provider_names: List[str]):
        """
        Context manager to patch only specific providers
        
        Args:
            provider_names: List of provider names to patch ('fincra', 'kraken', etc.)
        """
        patches = []
        
        try:
            for provider_name in provider_names:
                if provider_name not in self.patch_targets:
                    logger.warning(f"Unknown provider: {provider_name}")
                    continue
                    
                provider_fake = getattr(self, provider_name)
                for target in self.patch_targets[provider_name]:
                    try:
                        if provider_name == 'telegram':
                            # Special handling for Telegram Bot
                            mock_bot = MagicMock()
                            mock_bot.send_message = provider_fake.send_message
                            mock_bot.edit_message_text = provider_fake.edit_message_text
                            mock_bot.answer_callback_query = provider_fake.answer_callback_query
                            mock_bot.delete_message = provider_fake.delete_message
                            patches.append(patch(target, return_value=mock_bot))
                        else:
                            patches.append(patch(target, new=provider_fake))
                    except ImportError:
                        pass
            
            # Start patches
            for p in patches:
                try:
                    p.start()
                except Exception as e:
                    logger.debug(f"Failed to start patch: {e}")
            
            logger.info(f"🔧 Patched providers: {', '.join(provider_names)}")
            yield self
            
        finally:
            for p in patches:
                try:
                    p.stop()
                except Exception as e:
                    logger.debug(f"Failed to stop patch: {e}")
    
    def get_all_request_histories(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get request histories from all providers"""
        return {
            'fincra': self.fincra.get_request_history(),
            'kraken': self.kraken.get_request_history(),
            'fastforex': self.fastforex.get_request_history(),
            'telegram': self.telegram.get_sent_messages(),
            'email': self.email.get_sent_emails()
        }
    
    def clear_all_histories(self):
        """Clear request histories from all providers"""
        self.fincra.clear_history()
        self.kraken.clear_history()
        self.fastforex.clear_history()
        self.telegram.clear_history()
        self.email.clear_history()
        logger.info("🧹 Cleared all provider histories")


# Global factory instance
provider_factory = ProviderFakeFactory()