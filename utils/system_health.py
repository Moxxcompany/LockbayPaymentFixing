# Fixed System Health and Analytics Module

from datetime import datetime, timedelta
from sqlalchemy import and_
from database import SessionLocal
from models import User, Escrow, Cashout
import logging

logger = logging.getLogger(__name__)


class SystemHealthMonitor:
    """Properly typed system health monitoring functions"""

    @staticmethod
    def get_recent_activity_stats(hours: int = 24) -> dict:
        """Get system activity statistics for the last N hours"""
        session = SessionLocal()
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            # Get user stats using proper created_at field
            try:
                new_users = (
                    session.query(User).filter(User.created_at >= cutoff_time).count()
                    if hasattr(User, "created_at")
                    else 0
                )
            except Exception:
                new_users = 0

            # Get escrow stats
            try:
                recent_escrows = (
                    session.query(Escrow).filter(Escrow.created_at >= cutoff_time).all()
                )

                # Safe status breakdown
                status_counts = {}
                for escrow in recent_escrows:
                    status = getattr(escrow, "status", "unknown")
                    status_counts[status] = status_counts.get(status, 0) + 1

            except Exception as e:
                logger.error(f"Error getting escrow stats: {e}")
                recent_escrows = []
                status_counts = {}

            return {
                "new_users": new_users,
                "new_escrows": len(recent_escrows),
                "escrow_status_breakdown": status_counts,
                "time_window": f"{hours}h",
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error in activity stats: {e}")
            return {
                "error": str(e),
                "new_users": 0,
                "new_escrows": 0,
                "escrow_status_breakdown": {},
                "time_window": f"{hours}h",
            }
        finally:
            session.close()

    @staticmethod
    def check_system_health() -> dict:
        """Comprehensive system health check"""
        session = SessionLocal()
        try:
            health_issues = []
            warnings = []

            # Check for missing invitation tokens
            try:
                active_no_tokens = (
                    session.query(Escrow)
                    .filter(
                        and_(
                            Escrow.status.in_(["awaiting_seller", "pending"]),
                            Escrow.invitation_token.is_(None),
                        )
                    )
                    .count()
                )

                if active_no_tokens > 0:
                    health_issues.append(
                        f"{active_no_tokens} active escrows missing invitation tokens"
                    )
            except Exception as e:
                warnings.append(f"Could not check invitation tokens: {e}")

            # Check for orphaned escrows
            try:
                orphaned_escrows = (
                    session.query(Escrow).filter(Escrow.buyer_id.is_(None)).count()
                )

                if orphaned_escrows > 0:
                    health_issues.append(
                        f"{orphaned_escrows} orphaned escrows without buyers"
                    )
            except Exception as e:
                warnings.append(f"Could not check orphaned escrows: {e}")

            # Check for stuck cashouts
            try:
                one_hour_ago = datetime.utcnow() - timedelta(hours=1)
                stuck_cashouts = (
                    session.query(Cashout)
                    .filter(
                        and_(
                            Cashout.status.in_(["pending", "processing"]),
                            Cashout.created_at < one_hour_ago,
                        )
                    )
                    .count()
                )

                if stuck_cashouts > 0:
                    warnings.append(
                        f"{stuck_cashouts} cashouts stuck for >1 hour"
                    )
            except Exception as e:
                warnings.append(f"Could not check stuck cashouts: {e}")

            # Get basic system stats
            try:
                total_users = session.query(User).count()
                total_escrows = session.query(Escrow).count()
            except Exception as e:
                total_users = 0
                total_escrows = 0
                warnings.append(f"Could not get basic stats: {e}")

            # Calculate health score
            health_score = 100
            health_score -= len(health_issues) * 20  # Major issues
            health_score -= len(warnings) * 10  # Warnings
            health_score = max(0, health_score)

            return {
                "health_score": health_score,
                "status": (
                    "healthy"
                    if health_score >= 80
                    else "degraded" if health_score >= 60 else "unhealthy"
                ),
                "total_users": total_users,
                "total_escrows": total_escrows,
                "health_issues": health_issues,
                "warnings": warnings,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Critical error in health check: {e}")
            return {
                "health_score": 0,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
        finally:
            session.close()

    @staticmethod
    def analyze_recent_anomalies(hours: int = 24) -> dict:
        """Analyze system for anomalies and unusual patterns"""
        session = SessionLocal()
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            anomalies = []

            # Check high cancellation rates
            try:
                recent_cancellations = (
                    session.query(Escrow)
                    .filter(
                        and_(
                            Escrow.status == "cancelled",
                            Escrow.created_at >= cutoff_time,
                        )
                    )
                    .count()
                )

                if recent_cancellations > 10:
                    anomalies.append(
                        f"High cancellation rate: {recent_cancellations} in {hours}h"
                    )

                # Check cancellation patterns
                cancelled_escrows = (
                    session.query(Escrow)
                    .filter(
                        and_(
                            Escrow.status == "cancelled",
                            Escrow.created_at >= cutoff_time,
                        )
                    )
                    .all()
                )

                phone_cancellations = sum(
                    1 for e in cancelled_escrows if getattr(e, "seller_phone", None)
                )
                email_cancellations = sum(
                    1
                    for e in cancelled_escrows
                    if getattr(e, "seller_email", None)
                    and not getattr(e, "seller_phone", None)
                )

                if phone_cancellations > email_cancellations * 2:
                    anomalies.append(
                        f"Phone invitations failing more than email ({phone_cancellations} vs {email_cancellations})"
                    )

            except Exception as e:
                anomalies.append(f"Could not analyze cancellations: {e}")

            # Check for rapid user creation (potential spam)
            try:
                if hasattr(User, "created_at"):
                    recent_users = (
                        session.query(User)
                        .filter(User.created_at >= cutoff_time)
                        .count()
                    )
                else:
                    recent_users = 0

                if recent_users > 50:  # Threshold for spam detection
                    anomalies.append(
                        f"Unusual user creation rate: {recent_users} in {hours}h"
                    )
            except Exception as e:
                anomalies.append(f"Could not check user creation: {e}")

            return {
                "anomalies_detected": len(anomalies),
                "anomalies": anomalies,
                "analysis_period": f"{hours}h",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error in anomaly analysis: {e}")
            return {"error": str(e), "anomalies_detected": 0, "anomalies": []}
        finally:
            session.close()
