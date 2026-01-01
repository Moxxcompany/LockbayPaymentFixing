"""
Database Keep-Alive Job - Prevents Neon Database Suspension

This job runs every 4 minutes to prevent Neon serverless database from 
suspending due to inactivity. Neon suspends after 5 minutes of idle time,
causing 2-5 second cold start delays on next request.

Critical for production performance:
- Prevents database suspension (runs every 4min < 5min idle timeout)
- Keeps connection pool warm
- Eliminates cold start delays on button clicks and webhooks
- Improves response times from 2-5s to <200ms
"""

import logging
from datetime import datetime
from typing import Dict, Any
from sqlalchemy import text
from database import async_managed_session

logger = logging.getLogger(__name__)


class DatabaseKeepalive:
    """Database keep-alive engine to prevent Neon suspension"""

    def __init__(self):
        self.execution_count = 0
        
    async def run_database_keepalive(self) -> Dict[str, Any]:
        """
        Execute simple query to keep database warm
        Prevents Neon serverless from suspending (5min idle timeout)
        """
        start_time = datetime.utcnow()
        results = {
            "keepalive_executed": False,
            "execution_time_ms": 0,
            "status": "success",
            "execution_count": self.execution_count
        }
        
        try:
            # Execute simple SELECT 1 query to keep database active
            async with async_managed_session() as session:
                result = await session.execute(text("SELECT 1"))
                await session.commit()
                
                # Verify query executed successfully
                row = result.scalar()
                if row == 1:
                    results["keepalive_executed"] = True
                    self.execution_count += 1
                    results["execution_count"] = self.execution_count
                    
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            results["execution_time_ms"] = execution_time
            
            # Log success with execution count for monitoring
            if self.execution_count % 10 == 0:  # Log every 10th execution (every 40 minutes)
                logger.info(
                    f"💓 DATABASE_KEEPALIVE: Executed #{self.execution_count} "
                    f"(database warm, no suspension) in {execution_time:.0f}ms"
                )
            else:
                logger.debug(
                    f"💓 DATABASE_KEEPALIVE: Executed #{self.execution_count} "
                    f"in {execution_time:.0f}ms"
                )
            
            return results
            
        except Exception as e:
            logger.error(f"❌ DATABASE_KEEPALIVE_ERROR: Keep-alive failed: {e}")
            results["status"] = "error"
            results["error"] = str(e)
            # Calculate execution time even on error
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            results["execution_time_ms"] = execution_time
            return results


# Global keepalive instance
database_keepalive = DatabaseKeepalive()


# Exported function for scheduler integration
async def run_database_keepalive():
    """Main entry point for scheduler - prevents database suspension"""
    return await database_keepalive.run_database_keepalive()


# Export for scheduler
__all__ = [
    "DatabaseKeepalive",
    "database_keepalive",
    "run_database_keepalive"
]
