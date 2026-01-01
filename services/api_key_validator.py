"""
API Key Validation Service
Centralized validation for all API keys and secrets
"""

import os
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class APIKeyValidator:
    """Validates and manages API keys for all services"""

    @staticmethod
    def validate_required_keys() -> Dict[str, bool]:
        """Validate all required API keys are present"""
        required_keys = {
            "BOT_TOKEN": "Telegram Bot Token",
            "DATABASE_URL": "PostgreSQL Database URL",
        }

        optional_keys = {
            "BREVO_API_KEY": "Email Service (Brevo)",
            "FASTFOREX_API_KEY": "Exchange Rate Service",
            "BLOCKBEE_API_KEY": "Blockchain Service",
            "FINCRA_API_KEY": "Nigerian Payment Service",
            "BINANCE_API_KEY": "Binance Exchange",
            "BINANCE_SECRET_KEY": "Binance Secret",
            "TWILIO_ACCOUNT_SID": "SMS Service Account",
            "TWILIO_AUTH_TOKEN": "SMS Service Auth",
            "WEBHOOK_SECRET_TOKEN": "Webhook Security",
        }

        validation_results = {}
        missing_required = []
        missing_optional = []

        # Check required keys
        for key, description in required_keys.items():
            value = os.getenv(key)
            if value and value.strip():
                validation_results[key] = True
                logger.debug(f"✅ {description} configured")
            else:
                validation_results[key] = False
                missing_required.append(f"{description} ({key})")
                logger.error(f"❌ REQUIRED: {description} ({key}) is missing")

        # Check optional keys
        for key, description in optional_keys.items():
            value = os.getenv(key)
            if value and value.strip():
                validation_results[key] = True
                logger.info(f"✅ {description} configured")
            else:
                validation_results[key] = False
                missing_optional.append(f"{description} ({key})")
                logger.warning(
                    f"⚠️  Optional: {description} ({key}) not configured - feature disabled"
                )

        # Log summary
        if missing_required:
            logger.critical(f"MISSING REQUIRED KEYS: {', '.join(missing_required)}")
            raise EnvironmentError(
                f"Required API keys missing: {', '.join(missing_required)}"
            )

        if missing_optional:
            logger.info(f"Optional services disabled: {', '.join(missing_optional)}")

        return validation_results

    @staticmethod
    def get_api_key(key_name: str, required: bool = False) -> Optional[str]:
        """
        Get API key with validation

        Args:
            key_name: Environment variable name
            required: If True, raises error if not found

        Returns:
            API key value or None if not found
        """
        value = os.getenv(key_name)

        if not value or not value.strip():
            if required:
                raise EnvironmentError(f"Required API key {key_name} not configured")
            return None

        return value.strip()

    @staticmethod
    def mask_key(key: str, visible_chars: int = 4) -> str:
        """Mask API key for logging"""
        if not key:
            return "NOT_SET"
        if len(key) <= visible_chars * 2:
            return "***"
        return f"{key[:visible_chars]}...{key[-visible_chars:]}"

    @staticmethod
    def validate_service_availability(
        service_name: str, required_keys: List[str]
    ) -> bool:
        """
        Check if a service has all required keys configured

        Args:
            service_name: Name of the service
            required_keys: List of required environment variable names

        Returns:
            True if all keys are present, False otherwise
        """
        missing_keys = []

        for key in required_keys:
            if not os.getenv(key):
                missing_keys.append(key)

        if missing_keys:
            logger.warning(
                f"{service_name} disabled - missing keys: {', '.join(missing_keys)}"
            )
            return False

        logger.info(f"{service_name} available - all keys configured")
        return True


# Initialize validator on module import
api_validator = APIKeyValidator()
