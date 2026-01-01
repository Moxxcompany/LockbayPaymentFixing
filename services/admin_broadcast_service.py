"""
Admin Broadcast Service - Compatibility shim for testing infrastructure
"""

from typing import Dict, Any


class AdminBroadcastService:
    """Admin broadcast service"""
    
    async def create_broadcast(self, data: Dict[str, Any]) -> str:
        """Create broadcast message"""
        return "test_broadcast_id"
    
    async def send_broadcast(self, broadcast_id: str) -> Dict[str, Any]:
        """Send broadcast message"""
        return {"status": "sent", "delivered": 0, "failed": 0}
    
    async def get_broadcast_stats(self, broadcast_id: str) -> Dict[str, Any]:
        """Get broadcast statistics"""
        return {"delivered": 0, "failed": 0, "pending": 0}