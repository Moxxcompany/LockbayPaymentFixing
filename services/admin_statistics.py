"""Real admin dashboard statistics service"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from database import SessionLocal
from models import User, Escrow, Cashout, Dispute, CashoutStatus, EscrowStatus
from sqlalchemy import func, and_, desc

logger = logging.getLogger(__name__)


class AdminStatisticsService:
    """Real-time admin dashboard statistics and analytics"""

    @classmethod
    def get_comprehensive_statistics(cls) -> Dict[str, Any]:
        """Get comprehensive real-time platform statistics"""
        session = SessionLocal()
        try:
            now = datetime.utcnow()

            # Time periods for analysis
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)

            stats = {
                "overview": cls._get_platform_overview(session, now),
                "user_analytics": cls._get_user_analytics(
                    session, today, week_ago, month_ago
                ),
                "escrow_analytics": cls._get_escrow_analytics(
                    session, today, week_ago, month_ago
                ),
                "financial_analytics": cls._get_financial_analytics(
                    session, today, week_ago, month_ago
                ),
                "performance_metrics": cls._get_performance_metrics(session, now),
                "security_insights": cls._get_security_insights(session, week_ago),
                "growth_trends": cls._get_growth_trends(session, now),
            }

            return stats

        except Exception as e:
            logger.error(f"Error generating admin statistics: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    @classmethod
    def _get_platform_overview(cls, session, now) -> Dict[str, Any]:
        """Get high-level platform overview"""
        # User statistics
        total_users = session.query(User).count()
        active_users_today = (
            session.query(User)
            .filter(
                User.last_activity
                >= now.replace(hour=0, minute=0, second=0, microsecond=0)
            )
            .count()
        )

        # Escrow statistics
        total_escrows = session.query(Escrow).count()
        active_escrows = (
            session.query(Escrow)
            .filter(Escrow.status.in_(["ACTIVE", "PENDING_DEPOSIT", "PENDING_SELLER"]))
            .count()
        )
        completed_escrows = (
            session.query(Escrow).filter(Escrow.status == "completed").count()
        )

        # Financial overview
        total_volume = (
            session.query(func.sum(Escrow.amount))
            .filter(Escrow.status == "completed")
            .scalar()
            or 0.0
        )

        # Current status - use correct lowercase enum values
        pending_cashouts = (
            session.query(Cashout).filter(Cashout.status == CashoutStatus.PENDING.value).count()
        )

        open_disputes = session.query(Dispute).filter(Dispute.status == "OPEN").count()

        return {
            "total_users": total_users,
            "active_users_today": active_users_today,
            "total_escrows": total_escrows,
            "active_escrows": active_escrows,
            "completed_escrows": completed_escrows,
            "completion_rate": (completed_escrows / max(total_escrows, 1)) * 100,
            "total_volume_usd": total_volume,
            "pending_cashouts": pending_cashouts,
            "open_disputes": open_disputes,
            "platform_health": (
                "excellent"
                if open_disputes == 0 and pending_cashouts < 10
                else "good" if open_disputes < 3 else "needs_attention"
            ),
        }

    @classmethod
    def _get_user_analytics(cls, session, today, week_ago, month_ago) -> Dict[str, Any]:
        """Get detailed user analytics"""
        # Registration trends
        new_users_today = session.query(User).filter(User.created_at >= today).count()
        new_users_week = session.query(User).filter(User.created_at >= week_ago).count()
        new_users_month = (
            session.query(User).filter(User.created_at >= month_ago).count()
        )

        # User activity analysis
        active_users_week = (
            session.query(User).filter(User.last_activity >= week_ago).count()
        )
        verified_users = session.query(User).filter(User.email_verified).count()

        # User distribution by trade volume
        high_volume_users = (
            session.query(User).filter(User.total_volume_usd >= 1000).count()
        )
        medium_volume_users = (
            session.query(User)
            .filter(and_(User.total_volume_usd >= 100, User.total_volume_usd < 1000))
            .count()
        )

        # User reputation analysis
        avg_reputation = session.query(func.avg(User.reputation_score)).scalar() or 0.0
        elite_users = session.query(User).filter(User.reputation_score >= 4.8).count()

        return {
            "registration_trends": {
                "today": new_users_today,
                "this_week": new_users_week,
                "this_month": new_users_month,
            },
            "activity_metrics": {
                "active_this_week": active_users_week,
                "verified_users": verified_users,
                "verification_rate": (
                    verified_users / max(session.query(User).count(), 1)
                )
                * 100,
            },
            "user_segments": {
                "high_volume": high_volume_users,
                "medium_volume": medium_volume_users,
                "elite_traders": elite_users,
            },
            "reputation_metrics": {
                "average_reputation": round(avg_reputation, 2),
                "elite_percentage": (elite_users / max(session.query(User).count(), 1))
                * 100,
            },
        }

    @classmethod
    def _get_escrow_analytics(
        cls, session, today, week_ago, month_ago
    ) -> Dict[str, Any]:
        """Get comprehensive escrow analytics"""
        # Escrow creation trends
        escrows_today = session.query(Escrow).filter(Escrow.created_at >= today).count()
        escrows_week = (
            session.query(Escrow).filter(Escrow.created_at >= week_ago).count()
        )
        escrows_month = (
            session.query(Escrow).filter(Escrow.created_at >= month_ago).count()
        )

        # Completion analysis
        completed_week = (
            session.query(Escrow)
            .filter(and_(Escrow.status == EscrowStatus.COMPLETED.value, Escrow.completed_at >= week_ago))
            .count()
        )

        # Status distribution
        status_distribution = {}
        for status in [
            "PENDING_SELLER",
            "PENDING_DEPOSIT",
            "ACTIVE",
            "COMPLETED",
            "DISPUTED",
            "CANCELLED",
            "EXPIRED",
        ]:
            count = session.query(Escrow).filter(Escrow.status == status).count()
            status_distribution[status.lower()] = count

        # Currency analysis
        currency_usage = (
            session.query(Escrow.currency, func.count(Escrow.currency).label("count"))
            .group_by(Escrow.currency)
            .order_by(desc("count"))
            .limit(5)
            .all()
        )

        # Average completion time
        completed_escrows = (
            session.query(Escrow)
            .filter(and_(Escrow.status == EscrowStatus.COMPLETED.value, Escrow.completed_at.isnot(None)))
            .all()
        )

        avg_completion_hours = 0
        if completed_escrows:
            total_hours = sum(
                [
                    (e.completed_at - e.created_at).total_seconds() / 3600
                    for e in completed_escrows
                    if e.completed_at and e.created_at
                ]
            )
            avg_completion_hours = total_hours / len(completed_escrows)

        return {
            "creation_trends": {
                "today": escrows_today,
                "this_week": escrows_week,
                "this_month": escrows_month,
            },
            "completion_metrics": {
                "completed_this_week": completed_week,
                "average_completion_hours": round(avg_completion_hours, 1),
            },
            "status_distribution": status_distribution,
            "popular_currencies": [
                {"currency": c[0], "count": c[1]} for c in currency_usage
            ],
            "performance_indicators": {
                "weekly_success_rate": (completed_week / max(escrows_week, 1)) * 100,
                "dispute_rate": (
                    status_distribution.get("disputed", 0)
                    / max(sum(status_distribution.values()), 1)
                )
                * 100,
            },
        }

    @classmethod
    def _get_financial_analytics(
        cls, session, today, week_ago, month_ago
    ) -> Dict[str, Any]:
        """Get comprehensive financial analytics"""
        # Volume analysis
        volume_today = (
            session.query(func.sum(Escrow.amount))
            .filter(and_(Escrow.status == EscrowStatus.COMPLETED.value, Escrow.completed_at >= today))
            .scalar()
            or 0.0
        )

        volume_week = (
            session.query(func.sum(Escrow.amount))
            .filter(and_(Escrow.status == EscrowStatus.COMPLETED.value, Escrow.completed_at >= week_ago))
            .scalar()
            or 0.0
        )

        volume_month = (
            session.query(func.sum(Escrow.amount))
            .filter(
                and_(Escrow.status == EscrowStatus.COMPLETED.value, Escrow.completed_at >= month_ago)
            )
            .scalar()
            or 0.0
        )

        # Fee analysis
        fee_week = (
            session.query(func.sum(Escrow.fee_amount))
            .filter(and_(Escrow.status == EscrowStatus.COMPLETED.value, Escrow.completed_at >= week_ago))
            .scalar()
            or 0.0
        )

        # Average transaction value
        avg_transaction = (
            session.query(func.avg(Escrow.amount))
            .filter(Escrow.status == "completed")
            .scalar()
            or 0.0
        )

        # Cashout analysis
        total_cashouts = (
            session.query(func.sum(Cashout.amount))
            .filter(Cashout.status == "APPROVED")
            .scalar()
            or 0.0
        )

        pending_cashout_amount = (
            session.query(func.sum(Cashout.amount))
            .filter(Cashout.status == CashoutStatus.PENDING.value)
            .scalar()
            or 0.0
        )

        return {
            "volume_trends": {
                "today_usd": volume_today,
                "week_usd": volume_week,
                "month_usd": volume_month,
            },
            "revenue_metrics": {
                "fees_this_week": fee_week,
                "average_transaction": avg_transaction,
                "projected_monthly_revenue": fee_week * 4.33,  # weeks per month
            },
            "cashout_analysis": {
                "total_withdrawn": total_cashouts,
                "pending_amount": pending_cashout_amount,
                "cashout_ratio": (total_cashouts / max(volume_month, 1)) * 100,
            },
            "financial_health": {
                "growth_rate_week": ((volume_week / max(volume_month / 4.33, 1)) - 1)
                * 100,
                "liquidity_status": (
                    "healthy"
                    if pending_cashout_amount < volume_week * 0.1
                    else "monitor"
                ),
            },
        }

    @classmethod
    def _get_performance_metrics(cls, session, now) -> Dict[str, Any]:
        """Get platform performance metrics"""
        # Response time simulation (in real implementation, this would come from monitoring)
        recent_escrows = (
            session.query(Escrow)
            .filter(Escrow.created_at >= now - timedelta(hours=24))
            .count()
        )

        # System load indicators
        active_transactions = (
            session.query(Escrow)
            .filter(Escrow.status.in_(["ACTIVE", "PENDING_DEPOSIT"]))
            .count()
        )

        # Error rate simulation
        failed_escrows = (
            session.query(Escrow)
            .filter(
                and_(
                    Escrow.status == "CANCELLED",
                    Escrow.created_at >= now - timedelta(days=7),
                )
            )
            .count()
        )

        total_recent = (
            session.query(Escrow)
            .filter(Escrow.created_at >= now - timedelta(days=7))
            .count()
        )

        return {
            "system_metrics": {
                "transactions_24h": recent_escrows,
                "active_transactions": active_transactions,
                "system_load": "normal" if active_transactions < 100 else "high",
            },
            "reliability_metrics": {
                "error_rate_week": (failed_escrows / max(total_recent, 1)) * 100,
                "uptime_status": "operational",
                "success_rate": ((total_recent - failed_escrows) / max(total_recent, 1))
                * 100,
            },
        }

    @classmethod
    def _get_security_insights(cls, session, week_ago) -> Dict[str, Any]:
        """Get security and risk analytics"""
        # Dispute analysis
        recent_disputes = (
            session.query(Dispute).filter(Dispute.created_at >= week_ago).count()
        )

        # High-value transaction monitoring
        high_value_escrows = (
            session.query(Escrow)
            .filter(and_(Escrow.amount >= 1000, Escrow.created_at >= week_ago))
            .count()
        )

        # User risk assessment
        suspicious_users = (
            session.query(User)
            .filter(and_(User.reputation_score < 3.0, User.completed_trades > 0))
            .count()
        )

        return {
            "dispute_monitoring": {
                "disputes_this_week": recent_disputes,
                "dispute_trend": "stable" if recent_disputes < 5 else "increasing",
            },
            "transaction_monitoring": {
                "high_value_transactions": high_value_escrows,
                "flagged_users": suspicious_users,
            },
            "security_score": max(
                0, 100 - (recent_disputes * 5) - (suspicious_users * 2)
            ),
            "recommendations": cls._get_security_recommendations(
                recent_disputes, suspicious_users
            ),
        }

    @classmethod
    def _get_growth_trends(cls, session, now) -> Dict[str, Any]:
        """Calculate growth trends and projections"""
        # Calculate monthly growth
        this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month = (this_month - timedelta(days=1)).replace(day=1)

        users_this_month = (
            session.query(User).filter(User.created_at >= this_month).count()
        )
        users_last_month = (
            session.query(User)
            .filter(and_(User.created_at >= last_month, User.created_at < this_month))
            .count()
        )

        escrows_this_month = (
            session.query(Escrow).filter(Escrow.created_at >= this_month).count()
        )
        escrows_last_month = (
            session.query(Escrow)
            .filter(
                and_(Escrow.created_at >= last_month, Escrow.created_at < this_month)
            )
            .count()
        )

        # Growth calculations
        user_growth = ((users_this_month / max(users_last_month, 1)) - 1) * 100
        escrow_growth = ((escrows_this_month / max(escrows_last_month, 1)) - 1) * 100

        return {
            "monthly_growth": {
                "user_growth_percent": round(user_growth, 1),
                "transaction_growth_percent": round(escrow_growth, 1),
                "growth_status": (
                    "excellent"
                    if user_growth > 20
                    else "good" if user_growth > 10 else "stable"
                ),
            },
            "projections": {
                "estimated_users_next_month": users_this_month
                * (1 + user_growth / 100),
                "estimated_transactions_next_month": escrows_this_month
                * (1 + escrow_growth / 100),
            },
        }

    @classmethod
    def _get_security_recommendations(
        cls, disputes: int, suspicious_users: int
    ) -> List[str]:
        """Generate security recommendations"""
        recommendations = []

        if disputes > 5:
            recommendations.append(
                "High dispute volume detected - review dispute resolution process"
            )

        if suspicious_users > 10:
            recommendations.append(
                "Multiple low-reputation users - consider enhanced verification"
            )

        if not recommendations:
            recommendations.append("Security metrics are within normal parameters")

        return recommendations

    @classmethod
    def get_real_time_dashboard(cls) -> Dict[str, Any]:
        """Get real-time dashboard data for admin interface"""
        try:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "statistics": cls.get_comprehensive_statistics(),
                "alerts": cls._get_active_alerts(),
                "quick_stats": cls._get_quick_stats(),
            }
        except Exception as e:
            logger.error(f"Error generating real-time dashboard: {e}")
            return {"error": str(e)}

    @classmethod
    def _get_active_alerts(cls) -> List[Dict[str, Any]]:
        """Get active system alerts"""
        session = SessionLocal()
        try:
            alerts = []

            # Check pending cashouts
            pending_count = (
                session.query(Cashout).filter(Cashout.status == CashoutStatus.PENDING.value).count()
            )

            if pending_count > 5:
                alerts.append(
                    {
                        "type": "warning",
                        "message": f"{pending_count} cashout requests pending review",
                        "action": "Review pending cashouts",
                    }
                )

            # Check open disputes
            dispute_count = (
                session.query(Dispute).filter(Dispute.status == "OPEN").count()
            )

            if dispute_count > 0:
                alerts.append(
                    {
                        "type": "info",
                        "message": f"{dispute_count} open disputes require attention",
                        "action": "Review dispute cases",
                    }
                )

            return alerts

        finally:
            session.close()

    @classmethod
    def _get_quick_stats(cls) -> Dict[str, Any]:
        """Get quick stats for dashboard header"""
        session = SessionLocal()
        try:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            return {
                "users_today": session.query(User)
                .filter(User.created_at >= today)
                .count(),
                "escrows_today": session.query(Escrow)
                .filter(Escrow.created_at >= today)
                .count(),
                "volume_today": session.query(func.sum(Escrow.amount))
                .filter(
                    and_(Escrow.status == "COMPLETED", Escrow.completed_at >= today)
                )
                .scalar()
                or 0.0,
                "active_escrows": session.query(Escrow)
                .filter(Escrow.status.in_(["ACTIVE", "PENDING_DEPOSIT"]))
                .count(),
            }

        finally:
            session.close()
