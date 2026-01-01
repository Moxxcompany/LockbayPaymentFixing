"""
Admin Authentication Service - Compatibility shim for testing infrastructure
"""

from typing import Optional
from models import AdminUser


class AdminAuthService:
    """Admin authentication service"""
    
    async def authenticate_admin(self, telegram_id: int) -> Optional[AdminUser]:
        """Authenticate admin user"""
        return None
    
    async def create_admin_session(self, admin_id: str) -> str:
        """Create admin session"""
        return "test_session_id"
    
    async def validate_admin_session(self, session_id: str) -> Optional[AdminUser]:
        """Validate admin session"""
        return None