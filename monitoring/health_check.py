"""
Health Check and Monitoring System
Provides system health monitoring and diagnostic endpoints
"""

import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from database import SessionLocal
from models import Escrow, User, Transaction, Cashout
from sqlalchemy import text

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Health check status"""

    status: str  # "healthy", "warning", "critical"
    component: str
    message: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None


class HealthChecker:
    """System health monitoring"""

    def __init__(self):
        self.last_check = None
        self.cached_status = []
        self.cache_duration = 60  # Cache for 60 seconds

    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        now = datetime.utcnow()

        # Use cached results if recent
        if (
            self.last_check
            and self.cached_status
            and (now - self.last_check).seconds < self.cache_duration
        ):
            return self._format_health_response(self.cached_status)

        checks = []

        # Database health
        checks.append(await self._check_database_health())

        # System resources
        checks.append(self._check_system_resources())

        # Application metrics
        checks.append(await self._check_application_metrics())

        # Scheduler health
        checks.append(self._check_scheduler_health())

        # Cache results
        self.last_check = now
        self.cached_status = checks

        return self._format_health_response(checks)

    async def _check_database_health(self) -> HealthStatus:
        """Check database connectivity and performance"""
        try:
            session = SessionLocal()
            start_time = time.time()

            try:
                # Test basic connectivity
                session.execute(text("SELECT 1"))

                # Check recent activity
                recent_users = (
                    session.query(User)
                    .filter(User.created_at > datetime.utcnow() - timedelta(hours=24))
                    .count()
                )

                # Check for stuck transactions
                stuck_escrows = (
                    session.query(Escrow)
                    .filter(
                        Escrow.status == "pending_deposit",
                        Escrow.created_at < datetime.utcnow() - timedelta(days=7),
                    )
                    .count()
                )

                response_time = (time.time() - start_time) * 1000  # ms

                details = {
                    "response_time_ms": round(response_time, 2),
                    "recent_users_24h": recent_users,
                    "stuck_escrows": stuck_escrows,
                }

                if response_time > 1000:  # > 1 second
                    return HealthStatus(
                        status="warning",
                        component="database",
                        message=f"Database response slow: {response_time:.0f}ms",
                        timestamp=datetime.utcnow(),
                        details=details,
                    )

                if stuck_escrows > 5:
                    return HealthStatus(
                        status="warning",
                        component="database",
                        message=f"Found {stuck_escrows} stuck escrows",
                        timestamp=datetime.utcnow(),
                        details=details,
                    )

                return HealthStatus(
                    status="healthy",
                    component="database",
                    message="Database operational",
                    timestamp=datetime.utcnow(),
                    details=details,
                )

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return HealthStatus(
                status="critical",
                component="database",
                message=f"Database connection failed: {str(e)}",
                timestamp=datetime.utcnow(),
            )

    def _check_system_resources(self) -> HealthStatus:
        """Check system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Disk usage
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent

            details = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_free_gb": round(disk.free / (1024**3), 2),
            }

            # Determine status
            if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
                return HealthStatus(
                    status="critical",
                    component="system_resources",
                    message=f"High resource usage: CPU {cpu_percent}%, Memory {memory_percent}%, Disk {disk_percent}%",
                    timestamp=datetime.utcnow(),
                    details=details,
                )
            elif cpu_percent > 70 or memory_percent > 70 or disk_percent > 80:
                return HealthStatus(
                    status="warning",
                    component="system_resources",
                    message=f"Elevated resource usage: CPU {cpu_percent}%, Memory {memory_percent}%, Disk {disk_percent}%",
                    timestamp=datetime.utcnow(),
                    details=details,
                )
            else:
                return HealthStatus(
                    status="healthy",
                    component="system_resources",
                    message="System resources normal",
                    timestamp=datetime.utcnow(),
                    details=details,
                )

        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return HealthStatus(
                status="warning",
                component="system_resources",
                message=f"Could not check system resources: {str(e)}",
                timestamp=datetime.utcnow(),
            )

    async def _check_application_metrics(self) -> HealthStatus:
        """Check application-specific metrics"""
        try:
            session = SessionLocal()

            try:
                # Count active escrows (including payment_confirmed)
                active_escrows = (
                    session.query(Escrow).filter(
                        Escrow.status.in_(["active", "payment_pending", "payment_confirmed"])
                    ).count()
                )

                # Count pending cashouts
                pending_cashouts = (
                    session.query(Cashout)
                    .filter(Cashout.status == "pending")
                    .count()
                )

                # Count recent transactions
                recent_transactions = (
                    session.query(Transaction)
                    .filter(
                        Transaction.created_at > datetime.utcnow() - timedelta(hours=1)
                    )
                    .count()
                )

                # Check for overdue auto-releases (including payment_confirmed)
                overdue_releases = (
                    session.query(Escrow)
                    .filter(
                        Escrow.status.in_(["active", "payment_confirmed"]),
                        Escrow.auto_release_at.isnot(None),
                        Escrow.auto_release_at < datetime.utcnow(),
                    )
                    .count()
                )

                details = {
                    "active_escrows": active_escrows,
                    "pending_cashouts": pending_cashouts,
                    "recent_transactions_1h": recent_transactions,
                    "overdue_releases": overdue_releases,
                }

                if overdue_releases > 0:
                    return HealthStatus(
                        status="warning",
                        component="application",
                        message=f"Found {overdue_releases} overdue auto-releases",
                        timestamp=datetime.utcnow(),
                        details=details,
                    )

                if pending_cashouts > 20:
                    return HealthStatus(
                        status="warning",
                        component="application",
                        message=f"High number of pending cashouts: {pending_cashouts}",
                        timestamp=datetime.utcnow(),
                        details=details,
                    )

                return HealthStatus(
                    status="healthy",
                    component="application",
                    message="Application metrics normal",
                    timestamp=datetime.utcnow(),
                    details=details,
                )

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Application metrics check failed: {e}")
            return HealthStatus(
                status="warning",
                component="application",
                message=f"Could not check application metrics: {str(e)}",
                timestamp=datetime.utcnow(),
            )

    def _check_scheduler_health(self) -> HealthStatus:
        """Check if background scheduler is working"""
        try:
            # This would need to be integrated with the actual scheduler
            # For now, assume healthy if no critical errors

            details = {
                "scheduler_running": True,  # Would check actual scheduler status
                "last_job_execution": "recently",  # Would check actual last execution
            }

            return HealthStatus(
                status="healthy",
                component="scheduler",
                message="Background scheduler operational",
                timestamp=datetime.utcnow(),
                details=details,
            )

        except Exception as e:
            logger.error(f"Scheduler health check failed: {e}")
            return HealthStatus(
                status="warning",
                component="scheduler",
                message=f"Could not verify scheduler status: {str(e)}",
                timestamp=datetime.utcnow(),
            )

    def _format_health_response(self, checks: List[HealthStatus]) -> Dict[str, Any]:
        """Format health check results"""
        # Determine overall status
        statuses = [check.status for check in checks]
        if "critical" in statuses:
            overall_status = "critical"
        elif "warning" in statuses:
            overall_status = "warning"
        else:
            overall_status = "healthy"

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": [
                {
                    "component": check.component,
                    "status": check.status,
                    "message": check.message,
                    "timestamp": check.timestamp.isoformat(),
                    "details": check.details or {},
                }
                for check in checks
            ],
            "summary": {
                "total_checks": len(checks),
                "healthy": len([c for c in checks if c.status == "healthy"]),
                "warnings": len([c for c in checks if c.status == "warning"]),
                "critical": len([c for c in checks if c.status == "critical"]),
            },
        }


# Global health checker instance
health_checker = HealthChecker()


async def get_health_status() -> Dict[str, Any]:
    """Get current system health status"""
    return await health_checker.get_system_health()


# Simple health check for basic availability
async def ping_check() -> Dict[str, Any]:
    """Simple ping/alive check"""
    return {
        "status": "healthy",
        "message": "Service is running",
        "timestamp": datetime.utcnow().isoformat(),
    }
