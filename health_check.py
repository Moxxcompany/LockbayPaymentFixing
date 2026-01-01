"""
Health check endpoint for production monitoring
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import logging
from utils.performance_monitoring import performance_monitor
from database_config import check_database_health

logger = logging.getLogger(__name__)

def setup_health_routes(app: FastAPI):
    """Add health check routes to FastAPI app"""
    
    @app.get("/health")
    async def health_check():
        """Basic health check"""
        try:
            health_data = performance_monitor.get_system_health()
            
            # Determine overall health status
            is_healthy = (
                health_data.get("database", {}).get("status") == "healthy" and
                len([alert for alert in health_data.get("alerts", []) if alert.get("level") == "critical"]) == 0
            )
            
            status_code = 200 if is_healthy else 503
            
            return JSONResponse(
                content={
                    "status": "healthy" if is_healthy else "unhealthy",
                    "timestamp": health_data.get("timestamp"),
                    "uptime_seconds": health_data.get("uptime_seconds"),
                    "alerts": health_data.get("alerts", [])
                },
                status_code=status_code
            )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return JSONResponse(
                content={"status": "error", "error": str(e)},
                status_code=500
            )
    
    @app.get("/health/detailed")
    async def detailed_health_check():
        """Detailed health check for monitoring systems"""
        try:
            return performance_monitor.get_system_health()
        except Exception as e:
            logger.error(f"Detailed health check failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/health/database")
    async def database_health_check():
        """Database-specific health check"""
        try:
            return check_database_health()
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))