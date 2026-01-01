"""Security audit utilities for monitoring and logging security events"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Cashout, User

logger = logging.getLogger(__name__)


class SecurityAudit:
    """Security auditing and monitoring utilities"""

    @classmethod
    def generate_security_report(
        cls, session: Session, hours: int = 24
    ) -> Dict[str, Any]:
        """Generate comprehensive security report for recent activity"""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)

            # Cashout statistics
            total_cashouts = (
                session.query(Cashout).filter(Cashout.created_at >= since).count()
            )

            approved_cashouts = (
                session.query(Cashout)
                .filter(
                    Cashout.created_at >= since, Cashout.status == "completed"
                )
                .count()
            )

            rejected_cashouts = (
                session.query(Cashout)
                .filter(Cashout.created_at >= since, Cashout.status == "failed")
                .count()
            )

            pending_cashouts = (
                session.query(Cashout)
                .filter(Cashout.created_at >= since, Cashout.status == "pending")
                .count()
            )

            # High value cashouts (>$500)
            high_value_cashouts = (
                session.query(Cashout)
                .filter(Cashout.created_at >= since, Cashout.amount > 500)
                .count()
            )

            # Users with multiple cashout requests
            multiple_cashout_users = (
                session.query(
                    Cashout.user_id,
                    func.count(Cashout.id).label("cashout_count"),
                )
                .filter(Cashout.created_at >= since)
                .group_by(Cashout.user_id)
                .having(func.count(Cashout.id) > 2)
                .all()
            )

            # Total amounts
            total_requested_amount = (
                session.query(func.sum(Cashout.amount))
                .filter(Cashout.created_at >= since)
                .scalar()
                or 0
            )

            total_approved_amount = (
                session.query(func.sum(Cashout.amount))
                .filter(
                    Cashout.created_at >= since, Cashout.status == "completed"
                )
                .scalar()
                or 0
            )

            return {
                "period_hours": hours,
                "timestamp": datetime.utcnow().isoformat(),
                "cashout_stats": {
                    "total_requests": total_cashouts,
                    "approved": approved_cashouts,
                    "rejected": rejected_cashouts,
                    "pending": pending_cashouts,
                    "high_value_count": high_value_cashouts,
                    "approval_rate": (
                        (approved_cashouts / total_cashouts * 100)
                        if total_cashouts > 0
                        else 0
                    ),
                },
                "amounts": {
                    "total_requested": float(total_requested_amount),
                    "total_approved": float(total_approved_amount),
                    "average_request": (
                        float(total_requested_amount / total_cashouts)
                        if total_cashouts > 0
                        else 0
                    ),
                },
                "risk_indicators": {
                    "multiple_cashout_users": len(multiple_cashout_users),
                    "user_details": [
                        {"user_id": user_id, "cashout_count": count}
                        for user_id, count in multiple_cashout_users
                    ],
                },
            }

        except Exception as e:
            logger.error(f"Error generating security report: {e}")
            return {"error": str(e)}

    @classmethod
    def get_user_risk_profile(cls, session: Session, user_id: int) -> Dict[str, Any]:
        """Get comprehensive risk profile for a specific user"""
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return {"error": "User not found"}

            # Account age
            account_age_days = (
                (datetime.utcnow() - user.created_at).days if user.created_at else 0
            )

            # Cashout history
            total_cashouts = (
                session.query(Cashout).filter(Cashout.user_id == user_id).count()
            )

            completed_cashouts = (
                session.query(Cashout)
                .filter(Cashout.user_id == user_id, Cashout.status == "completed")
                .count()
            )

            failed_cashouts = (
                session.query(Cashout)
                .filter(Cashout.user_id == user_id, Cashout.status == "failed")
                .count()
            )

            # Recent activity (last 7 days)
            recent_cashouts = (
                session.query(Cashout)
                .filter(
                    Cashout.user_id == user_id,
                    Cashout.created_at >= datetime.utcnow() - timedelta(days=7),
                )
                .count()
            )

            # Total cashout amounts
            total_cashout_amount = (
                session.query(func.sum(Cashout.amount))
                .filter(Cashout.user_id == user_id, Cashout.status == "completed")
                .scalar()
                or 0
            )

            # Risk factors
            risk_factors = []
            risk_score = 0

            if account_age_days < 7:
                risk_factors.append("New account (< 7 days)")
                risk_score += 3
            elif account_age_days < 30:
                risk_factors.append("Recent account (< 30 days)")
                risk_score += 1

            if recent_cashouts > 3:
                risk_factors.append(
                    f"High recent activity ({recent_cashouts} cashouts in 7 days)"
                )
                risk_score += 2

            if failed_cashouts > completed_cashouts and total_cashouts > 0:
                risk_factors.append("More failed than successful cashouts")
                risk_score += 2

            failure_rate = (
                (failed_cashouts / total_cashouts * 100)
                if total_cashouts > 0
                else 0
            )
            if failure_rate > 50:
                risk_factors.append(f"High failure rate ({failure_rate:.1f}%)")
                risk_score += 1

            return {
                "user_id": user_id,
                "username": user.username,
                "account_age_days": account_age_days,
                "cashout_history": {
                    "total": total_cashouts,
                    "completed": completed_cashouts,
                    "failed": failed_cashouts,
                    "failure_rate": failure_rate,
                    "recent_activity": recent_cashouts,
                    "total_amount": float(total_cashout_amount),
                },
                "risk_assessment": {
                    "risk_score": risk_score,
                    "risk_level": (
                        "HIGH"
                        if risk_score >= 6
                        else "MEDIUM" if risk_score >= 3 else "LOW"
                    ),
                    "risk_factors": risk_factors,
                },
            }

        except Exception as e:
            logger.error(f"Error generating user risk profile: {e}")
            return {"error": str(e)}

    @classmethod
    def get_suspicious_patterns(
        cls, session: Session, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Identify suspicious cashout patterns"""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            patterns = []

            # Pattern 1: Multiple cashouts from same IP (simulated - would need IP tracking)
            # Pattern 2: Rapid successive cashouts
            rapid_cashouts = (
                session.query(
                    Cashout.user_id,
                    func.count(Cashout.id).label("count"),
                    func.min(Cashout.created_at).label("first_cashout"),
                    func.max(Cashout.created_at).label("last_cashout"),
                )
                .filter(Cashout.created_at >= since)
                .group_by(Cashout.user_id)
                .having(func.count(Cashout.id) >= 3)
                .all()
            )

            for user_id, count, first, last in rapid_cashouts:
                time_span = (last - first).total_seconds() / 3600  # hours
                if time_span < 2:  # 3+ cashouts in less than 2 hours
                    patterns.append(
                        {
                            "type": "RAPID_CASHOUTS",
                            "user_id": user_id,
                            "cashout_count": count,
                            "time_span_hours": time_span,
                            "severity": "HIGH",
                        }
                    )

            # Pattern 3: Large percentage of balance cashouts
            # This would require balance tracking integration

            return patterns

        except Exception as e:
            logger.error(f"Error identifying suspicious patterns: {e}")
            return []
