"""
Admin Configuration Module
Centralized admin user management and configuration
"""

from typing import Set


class AdminConfig:
    """Centralized admin configuration"""

    @classmethod
    def get_admin_ids(cls) -> Set[int]:
        """Get list of admin user IDs from environment - SECURE VERSION"""
        # SECURITY FIX: Use secure admin manager instead of unsafe fallbacks
        from utils.admin_security import admin_security

        return admin_security.get_admin_ids()

    @classmethod
    def is_admin(cls, user_id: int) -> bool:
        """Check if user ID is an admin - SECURE VERSION"""
        # SECURITY FIX: Use admin list lookup instead of security-alert-triggering check
        admin_ids = cls.get_admin_ids()
        return user_id in admin_ids

    @classmethod
    def get_primary_admin_id(cls) -> int:
        """Get primary admin ID for notifications"""
        admin_ids = cls.get_admin_ids()
        return min(admin_ids) if admin_ids else 1531772316


# Legacy support - gradually replace usage of hardcoded admin checks
ADMIN_IDS = AdminConfig.get_admin_ids()
PRIMARY_ADMIN_ID = AdminConfig.get_primary_admin_id()


def is_admin(user_id: int) -> bool:
    """Legacy function for backward compatibility - SECURE VERSION"""
    # SECURITY FIX: Use admin list lookup instead of security-alert-triggering check
    return AdminConfig.is_admin(user_id)
