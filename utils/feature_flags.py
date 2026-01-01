"""Feature flags system for dynamic feature toggling"""

import os
import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)


class FeatureState(Enum):
    """Feature flag states"""

    ENABLED = "enabled"
    DISABLED = "disabled"
    TESTING = "testing"
    ROLLOUT = "rollout"
    DEPRECATED = "deprecated"


@dataclass
class FeatureFlag:
    """Feature flag configuration"""

    name: str
    state: FeatureState
    description: str
    default_value: bool = False
    rollout_percentage: float = 0.0
    user_whitelist: Optional[list] = None
    user_blacklist: Optional[list] = None
    environment_restrictions: Optional[list] = None
    expiry_date: Optional[datetime] = None
    conditions: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class FeatureFlagManager:
    """Comprehensive feature flag management system"""

    def __init__(self):
        self.flags = self._initialize_flags()
        self.cache = {}
        self.environment = os.getenv("ENVIRONMENT", "production")

    def _initialize_flags(self) -> Dict[str, FeatureFlag]:
        """Initialize all feature flags"""
        return {
            # Core Features
            "auto_cashout": FeatureFlag(
                name="auto_cashout",
                state=FeatureState.ENABLED,
                description="Automatic cashout processing",
                default_value=True,
                environment_restrictions=["production", "staging"],
            ),
            "manual_approval": FeatureFlag(
                name="manual_approval",
                state=FeatureState.ENABLED,
                description="Manual approval for cashouts",
                default_value=True,
            ),
            "email_verification": FeatureFlag(
                name="email_verification",
                state=FeatureState.ENABLED,
                description="Email verification for new users",
                default_value=True,
            ),
            "phone_verification": FeatureFlag(
                name="phone_verification",
                state=FeatureState.TESTING,
                description="Phone number verification",
                default_value=False,
                rollout_percentage=25.0,
            ),
            # Payment Features
            "ngn_payments": FeatureFlag(
                name="ngn_payments",
                state=FeatureState.ENABLED,
                description="Nigerian Naira payment processing",
                default_value=True,
            ),
            "crypto_cashouts": FeatureFlag(
                name="crypto_cashouts",
                state=FeatureState.ENABLED,
                description="Cryptocurrency cashout support",
                default_value=True,
            ),
            "rate_locking": FeatureFlag(
                name="rate_locking",
                state=FeatureState.ENABLED,
                description="Exchange rate locking for trades",
                default_value=True,
            ),
            # Security Features
            "two_factor_auth": FeatureFlag(
                name="two_factor_auth",
                state=FeatureState.ROLLOUT,
                description="Two-factor authentication",
                default_value=False,
                rollout_percentage=10.0,
            ),
            "advanced_kyc": FeatureFlag(
                name="advanced_kyc",
                state=FeatureState.TESTING,
                description="Advanced KYC verification",
                default_value=False,
                rollout_percentage=5.0,
                conditions={"min_transaction_amount": 1000.0},
            ),
            "ip_geoblocking": FeatureFlag(
                name="ip_geoblocking",
                state=FeatureState.ENABLED,
                description="IP-based geographic blocking",
                default_value=True,
            ),
            # UI/UX Features
            "new_dashboard": FeatureFlag(
                name="new_dashboard",
                state=FeatureState.TESTING,
                description="New user dashboard interface",
                default_value=False,
                rollout_percentage=15.0,
            ),
            "dark_mode": FeatureFlag(
                name="dark_mode",
                state=FeatureState.DISABLED,
                description="Dark mode interface",
                default_value=False,
            ),
            "mobile_app_integration": FeatureFlag(
                name="mobile_app_integration",
                state=FeatureState.DISABLED,
                description="Mobile app integration features",
                default_value=False,
                environment_restrictions=["development"],
            ),
            # Analytics Features
            "advanced_analytics": FeatureFlag(
                name="advanced_analytics",
                state=FeatureState.ENABLED,
                description="Advanced user analytics tracking",
                default_value=True,
            ),
            "real_time_metrics": FeatureFlag(
                name="real_time_metrics",
                state=FeatureState.ROLLOUT,
                description="Real-time metrics dashboard",
                default_value=False,
                rollout_percentage=30.0,
            ),
            # Experimental Features
            "ai_fraud_detection": FeatureFlag(
                name="ai_fraud_detection",
                state=FeatureState.TESTING,
                description="AI-powered fraud detection",
                default_value=False,
                rollout_percentage=5.0,
                user_whitelist=["admin_users"],
            ),
            "smart_contracts": FeatureFlag(
                name="smart_contracts",
                state=FeatureState.DISABLED,
                description="Smart contract integration",
                default_value=False,
                environment_restrictions=["development"],
            ),
            # Business Features
            "referral_program": FeatureFlag(
                name="referral_program",
                state=FeatureState.ENABLED,
                description="User referral program",
                default_value=True,
            ),
            "loyalty_rewards": FeatureFlag(
                name="loyalty_rewards",
                state=FeatureState.ROLLOUT,
                description="Loyalty rewards system",
                default_value=False,
                rollout_percentage=20.0,
            ),
            "premium_features": FeatureFlag(
                name="premium_features",
                state=FeatureState.TESTING,
                description="Premium subscription features",
                default_value=False,
                rollout_percentage=10.0,
            ),
        }

    def is_enabled(
        self, flag_name: str, user_id: Optional[int] = None, **context
    ) -> bool:
        """Check if a feature flag is enabled for a user/context"""
        try:
            # Check cache first
            cache_key = f"{flag_name}_{user_id}_{hash(str(context))}"
            if cache_key in self.cache:
                return self.cache[cache_key]

            flag = self.flags.get(flag_name)
            if not flag:
                logger.warning(f"Unknown feature flag: {flag_name}")
                return False

            # Check environment restrictions
            if (
                flag.environment_restrictions
                and self.environment not in flag.environment_restrictions
            ):
                result = False
            # Check expiry
            elif flag.expiry_date and datetime.now(timezone.utc) > flag.expiry_date:
                result = False
            # Check state
            elif flag.state == FeatureState.DISABLED:
                result = False
            elif flag.state == FeatureState.ENABLED:
                result = True
            elif flag.state == FeatureState.DEPRECATED:
                logger.warning(f"Using deprecated feature flag: {flag_name}")
                result = flag.default_value
            else:
                # Handle testing/rollout states
                result = self._evaluate_conditional_flag(flag, user_id, context)

            # Cache result
            self.cache[cache_key] = result

            # Log flag usage for analytics
            self._log_flag_usage(flag_name, result, user_id)

            return result

        except Exception as e:
            logger.error(f"Error evaluating feature flag {flag_name}: {e}")
            return self.flags.get(
                flag_name, FeatureFlag("", FeatureState.DISABLED, "")
            ).default_value

    def _evaluate_conditional_flag(
        self, flag: FeatureFlag, user_id: Optional[int], context: Dict[str, Any]
    ) -> bool:
        """Evaluate conditional feature flags (testing/rollout)"""
        # Check user whitelist
        if flag.user_whitelist and user_id:
            if (
                str(user_id) in flag.user_whitelist
                or "admin_users" in flag.user_whitelist
            ):
                return True

        # Check user blacklist
        if flag.user_blacklist and user_id:
            if str(user_id) in flag.user_blacklist:
                return False

        # Check conditions
        if flag.conditions:
            for condition_key, condition_value in flag.conditions.items():
                context_value = context.get(condition_key)
                if context_value is None:
                    continue

                # Handle different condition types
                if isinstance(condition_value, (int, float)):
                    if float(context_value) < condition_value:
                        return False
                elif isinstance(condition_value, str):
                    if str(context_value) != condition_value:
                        return False
                elif isinstance(condition_value, list):
                    if context_value not in condition_value:
                        return False

        # Rollout percentage check
        if flag.rollout_percentage > 0:
            if user_id:
                # Deterministic rollout based on user ID
                user_hash = hash(str(user_id) + flag.name) % 100
                return user_hash < flag.rollout_percentage
            else:
                # Random rollout for anonymous users
                import random

                return random.random() * 100 < flag.rollout_percentage

        return flag.default_value

    def _log_flag_usage(self, flag_name: str, result: bool, user_id: Optional[int]):
        """Log feature flag usage for analytics"""
        try:
            # This could be sent to analytics service
            log_data = {
                "flag_name": flag_name,
                "enabled": result,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "environment": self.environment,
            }

            # For now, just debug log
            logger.debug(f"Feature flag usage: {json.dumps(log_data)}")

        except Exception as e:
            logger.error(f"Error logging flag usage: {e}")

    def get_flag_config(self, flag_name: str) -> Optional[FeatureFlag]:
        """Get feature flag configuration"""
        return self.flags.get(flag_name)

    def list_flags(
        self, state_filter: Optional[FeatureState] = None
    ) -> Dict[str, FeatureFlag]:
        """List all feature flags, optionally filtered by state"""
        if state_filter:
            return {
                name: flag
                for name, flag in self.flags.items()
                if flag.state == state_filter
            }
        return self.flags.copy()

    def update_flag(self, flag_name: str, **updates):
        """Update feature flag configuration"""
        if flag_name in self.flags:
            flag = self.flags[flag_name]
            for key, value in updates.items():
                if hasattr(flag, key):
                    setattr(flag, key, value)

            # Clear cache for this flag
            self.cache = {
                k: v for k, v in self.cache.items() if not k.startswith(flag_name)
            }

            logger.info(f"Updated feature flag {flag_name}: {updates}")
        else:
            logger.error(f"Cannot update unknown feature flag: {flag_name}")

    def clear_cache(self):
        """Clear feature flag cache"""
        self.cache.clear()
        logger.info("Feature flag cache cleared")

    def get_enabled_flags(self, user_id: Optional[int] = None, **context) -> List[str]:
        """Get list of enabled flags for a user/context"""
        enabled = []
        for flag_name in self.flags:
            if self.is_enabled(flag_name, user_id, **context):
                enabled.append(flag_name)
        return enabled

    def flag_status_report(self) -> Dict[str, Any]:
        """Generate comprehensive flag status report"""
        report = {
            "total_flags": len(self.flags),
            "by_state": {},
            "environment": self.environment,
            "cache_size": len(self.cache),
            "flags": {},
        }

        # Count by state
        for state in FeatureState:
            count = len([f for f in self.flags.values() if f.state == state])
            report["by_state"][state.value] = count

        # Flag details
        for name, flag in self.flags.items():
            report["flags"][name] = {
                "state": flag.state.value,
                "description": flag.description,
                "default_value": flag.default_value,
                "rollout_percentage": flag.rollout_percentage,
            }

        return report


# Global feature flag manager
feature_flags = FeatureFlagManager()


def is_feature_enabled(
    flag_name: str, user_id: Optional[int] = None, **context
) -> bool:
    """Convenience function to check if feature is enabled"""
    return feature_flags.is_enabled(flag_name, user_id, **context)


def require_feature(flag_name: str):
    """Decorator to require a feature flag to be enabled"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Try to extract user_id from args/kwargs
            user_id = kwargs.get("user_id")
            if not user_id and args:
                # Look for user_id in common positions
                for arg in args[:3]:  # Check first 3 args
                    if hasattr(arg, "effective_user") and hasattr(
                        arg.effective_user, "id"
                    ):
                        user_id = arg.effective_user.id
                        break

            if not is_feature_enabled(flag_name, user_id):
                raise PermissionError(f"Feature '{flag_name}' is not enabled")

            return func(*args, **kwargs)

        return wrapper

    return decorator
