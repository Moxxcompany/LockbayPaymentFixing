"""
Centralized notification preferences handling
Eliminates JSON handling duplication and type inconsistencies
"""

import json
import logging
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Default notification preferences
DEFAULT_PREFERENCES = {
    "escrow_updates": {"telegram": True, "email": True},
    "payments": {"telegram": True, "email": True},
    "exchanges": {"telegram": True, "email": True},
    "disputes": {"telegram": True, "email": True},
    "marketing": {"telegram": False, "email": False},
    "maintenance": {"telegram": True, "email": True},
    "daily_rates": {"telegram": True, "email": False},
}


def get_user_preferences(user) -> Dict[str, Any]:
    """
    Get user notification preferences as a dict, with defaults merged

    Args:
        user: User model instance

    Returns:
        Dict with merged preferences and defaults
    """
    try:
        # Handle both str and dict types from database
        if isinstance(user.notification_preferences, str):
            preferences = json.loads(user.notification_preferences)
        elif isinstance(user.notification_preferences, dict):
            preferences = user.notification_preferences.copy()
        else:
            preferences = {}
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        logger.warning(f"Invalid preferences format for user {user.telegram_id}: {e}")
        preferences = {}

    # Merge with defaults - ensure all categories exist
    merged = DEFAULT_PREFERENCES.copy()
    for category, settings in preferences.items():
        if category in merged and isinstance(settings, dict):
            merged[category].update(settings)

    return merged


def set_user_preferences(user, preferences: Dict[str, Any], session) -> None:
    """
    Set user notification preferences with proper JSON serialization

    Args:
        user: User model instance
        preferences: Preferences dict to save
        session: Database session for commit
    """
    try:
        # Always store as JSON string for consistency
        # Use SQLAlchemy update to avoid type issues
        from sqlalchemy import text

        session.execute(
            text(
                "UPDATE users SET notification_preferences = :prefs WHERE telegram_id = :telegram_id"
            ),
            {"prefs": json.dumps(preferences), "telegram_id": str(user.telegram_id)},
        )
        session.commit()
        logger.info(f"Updated preferences for user {user.telegram_id}")
    except Exception as e:
        logger.error(f"Error saving preferences for user {user.telegram_id}: {e}")
        session.rollback()
        raise


def toggle_preference(user, category: str, channel: str, session) -> bool:
    """
    Toggle a specific notification preference

    Args:
        user: User model instance
        category: Preference category (escrow_updates, payments, etc.)
        channel: Notification channel (telegram, email)
        session: Database session

    Returns:
        New state (True/False) after toggle
    """
    preferences = get_user_preferences(user)

    if category not in preferences:
        logger.warning(f"Unknown preference category: {category}")
        return False

    if channel not in preferences[category]:
        logger.warning(f"Unknown channel {channel} for category {category}")
        return False

    # Toggle the preference
    current_state = preferences[category][channel]
    new_state = not current_state
    preferences[category][channel] = new_state

    # Save the updated preferences
    set_user_preferences(user, preferences, session)

    return new_state


def is_enabled(user, category: str, channel: str) -> bool:
    """
    Check if a specific notification is enabled

    Args:
        user: User model instance
        category: Preference category
        channel: Notification channel

    Returns:
        True if enabled, False otherwise
    """
    preferences = get_user_preferences(user)
    return preferences.get(category, {}).get(channel, False)


def reset_to_defaults(user, session) -> None:
    """
    Reset all preferences to defaults

    Args:
        user: User model instance
        session: Database session
    """
    set_user_preferences(user, DEFAULT_PREFERENCES.copy(), session)
    logger.info(f"Reset preferences to defaults for user {user.telegram_id}")


def format_preference_status(telegram_enabled: bool, email_enabled: bool) -> str:
    """
    Format preference status for UI display

    Args:
        telegram_enabled: Telegram notification enabled
        email_enabled: Email notification enabled

    Returns:
        Formatted status string
    """
    if telegram_enabled and email_enabled:
        return "📱📧 Both"
    elif telegram_enabled:
        return "📱 Telegram only"
    elif email_enabled:
        return "📧 Email only"
    else:
        return "❌ Disabled"
