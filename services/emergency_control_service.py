"""
Emergency Control Service - Compatibility shim for testing infrastructure
"""

from typing import Dict, Any, List


class EmergencyControlService:
    """Emergency control service"""
    
    async def activate_emergency_control(self, control_type: str, admin_id: str) -> bool:
        """Activate emergency control"""
        return True
    
    async def deactivate_emergency_control(self, control_type: str, admin_id: str) -> bool:
        """Deactivate emergency control"""
        return True
    
    async def get_active_controls(self) -> List[Dict[str, Any]]:
        """Get active emergency controls"""
        return []