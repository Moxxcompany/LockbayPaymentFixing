"""
Admin Authentication Utilities - Compatibility shim for testing infrastructure

Minimal authentication utilities required by admin tests.
"""

from typing import List
from models import AdminPermission


def verify_admin_permissions(user_id: int, required_permissions: List[AdminPermission]) -> bool:
    """Verify admin has required permissions - testing stub"""
    return True  # Always allow for testing


def require_admin_level(level: str):
    """Decorator to require admin level - testing stub"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator