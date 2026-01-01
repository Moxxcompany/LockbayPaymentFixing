"""Admin utility functions for authorization checks"""

import logging

logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    """
    SECURITY-HARDENED admin check function

    Args:
        user_id: Telegram user ID (integer)

    Returns:
        bool: True if user is admin, False otherwise
    """
    # SECURITY FIX: Use non-alerting admin check for normal operations
    from utils.admin_security import is_admin_silent

    return is_admin_silent(user_id)


def require_admin(user_id: int) -> tuple[bool, str]:
    """
    SECURITY-HARDENED admin requirement check

    Args:
        user_id: Telegram user ID

    Returns:
        tuple: (is_admin, error_message)
    """
    # SECURITY FIX: Use non-alerting admin check for requirement validation
    from utils.admin_security import is_admin_silent

    if is_admin_silent(user_id):
        return True, ""
    else:
        return False, "❌ Access denied. Administrative privileges required."


def get_admin_user_ids() -> list[int]:
    """
    SECURITY-HARDENED admin ID retrieval for notifications

    Returns:
        list[int]: List of admin Telegram user IDs
    """
    try:
        # SECURITY FIX: Get admin IDs securely without exposing in logs
        from utils.admin_security import admin_security

        admin_set = admin_security.get_admin_ids()
        logger.info(f"Retrieved {len(admin_set)} admin user IDs for notifications")
        return list(admin_set)
    except Exception as e:
        logger.error(f"Error retrieving admin user IDs: {e}")
        return []
        return []
