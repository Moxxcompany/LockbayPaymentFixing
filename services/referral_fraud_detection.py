"""Comprehensive referral fraud detection system"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import and_
from database import SessionLocal
from models import User, Transaction, ReferralFraudAlert

logger = logging.getLogger(__name__)


class ReferralFraudDetector:
    """Detect and flag suspicious referral activity"""

    @staticmethod
    def analyze_user_behavior(user_id: int, session=None) -> Dict[str, Any]:
        """Analyze user's referral behavior for fraud patterns"""
        close_session = False
        if not session:
            session = SessionLocal()
            close_session = True

        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return {"error": "User not found"}

            # Get all referrals made by this user
            referrals = session.query(User).filter(User.referred_by == user_id).all()

            analysis = {
                "user_id": user_id,
                "total_referrals": len(referrals),
                "risk_score": 0,
                "risk_factors": [],
                "suspicious_patterns": [],
            }

            if not referrals:
                return analysis

            # Pattern 1: Rapid referral creation
            ReferralFraudDetector._check_rapid_referrals(
                referrals, analysis
            )

            # Pattern 2: Suspicious user attributes
            ReferralFraudDetector._check_suspicious_referrals(
                referrals, analysis
            )

            # Pattern 3: Geographic clustering (if available)
            ReferralFraudDetector._check_geographic_patterns(
                referrals, analysis
            )

            # Pattern 4: Activity patterns
            ReferralFraudDetector._check_activity_patterns(
                user_id, referrals, session, analysis
            )

            # Pattern 5: Account age vs referral timing
            ReferralFraudDetector._check_timing_patterns(
                user, referrals, analysis
            )

            # Calculate final risk score
            analysis["risk_level"] = ReferralFraudDetector._calculate_risk_level(
                analysis["risk_score"]
            )

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing user behavior: {e}")
            return {"error": str(e)}
        finally:
            if close_session:
                session.close()

    @staticmethod
    def _check_rapid_referrals(referrals: List[User], analysis: Dict[str, Any]) -> bool:
        """Check for unusually rapid referral creation"""
        if len(referrals) < 3:
            return False

        # Sort by creation time
        sorted_referrals = sorted(referrals, key=lambda x: getattr(x, 'created_at', None) or datetime.min)

        # Check for multiple referrals in short time windows
        rapid_count = 0
        for i in range(len(sorted_referrals) - 2):
            time_diff = (
                sorted_referrals[i + 2].created_at - sorted_referrals[i].created_at
            ).total_seconds()
            if time_diff < 3600:  # 3 referrals within 1 hour
                rapid_count += 1

        if rapid_count > 0:
            analysis["risk_score"] += 25
            analysis["risk_factors"].append(f"Rapid referrals: {rapid_count} clusters")
            analysis["suspicious_patterns"].append(
                {
                    "type": "rapid_referrals",
                    "description": f"Created {rapid_count} referral clusters within 1 hour",
                    "severity": "high" if rapid_count > 2 else "medium",
                }
            )
            return True

        return False

    @staticmethod
    def _check_suspicious_referrals(
        referrals: List[User], analysis: Dict[str, Any]
    ) -> bool:
        """Check for suspicious patterns in referred users"""
        suspicious_count = 0
        patterns = []

        # Check for patterns in usernames/names
        usernames = [getattr(r, 'username', None) for r in referrals if getattr(r, 'username', None)]
        first_names = [getattr(r, 'first_name', None) for r in referrals if getattr(r, 'first_name', None)]

        # Pattern: Similar usernames
        if len(usernames) > 1:
            similar_usernames = 0
            for i, username1 in enumerate(usernames):
                for username2 in usernames[i + 1 :]:
                    if username1 and username2:
                        # Simple similarity check
                        if abs(len(username1) - len(username2)) <= 2:
                            common_chars = sum(
                                1 for a, b in zip(username1, username2) if a == b
                            )
                            similarity = common_chars / max(
                                len(username1), len(username2)
                            )
                            if similarity > 0.7:
                                similar_usernames += 1

            if similar_usernames > 2:
                suspicious_count += similar_usernames
                patterns.append(f"Similar usernames: {similar_usernames} pairs")

        # Pattern: Sequential or pattern-based names
        sequential_names = 0
        if len(first_names) > 2:
            for i, name1 in enumerate(first_names):
                for name2 in first_names[i + 1 :]:
                    if name1 and name2 and len(name1) > 3 and len(name2) > 3:
                        if name1[:-1] == name2[:-1] or name1[:-2] == name2[:-2]:
                            sequential_names += 1

        if sequential_names > 1:
            suspicious_count += sequential_names
            patterns.append(f"Sequential names: {sequential_names} pairs")

        # Pattern: All users created within short timeframe
        creation_times = [r.created_at for r in referrals if r.created_at]
        if len(creation_times) > 2:
            time_span = (max(creation_times) - min(creation_times)).total_seconds()
            if time_span < 7200 and len(creation_times) > 5:  # 5+ users in 2 hours
                suspicious_count += 10
                patterns.append(
                    f"Mass creation: {len(creation_times)} users in {time_span/3600:.1f} hours"
                )

        if suspicious_count > 0:
            analysis["risk_score"] += min(suspicious_count * 5, 30)
            analysis["risk_factors"].extend(patterns)
            analysis["suspicious_patterns"].append(
                {
                    "type": "suspicious_referrals",
                    "description": f"Suspicious patterns in {suspicious_count} referred users",
                    "details": patterns,
                    "severity": "high" if suspicious_count > 5 else "medium",
                }
            )
            return True

        return False

    @staticmethod
    def _check_geographic_patterns(
        referrals: List[User], analysis: Dict[str, Any]
    ) -> bool:
        """Check for geographic clustering (placeholder for future implementation)"""
        # This would require IP/location data
        # For now, this is a placeholder for future geographic analysis
        return False

    @staticmethod
    def _check_activity_patterns(
        user_id: int, referrals: List[User], session, analysis: Dict[str, Any]
    ) -> bool:
        """Check activity patterns of referred users"""
        try:
            # Check how many referred users became active
            active_count = 0
            inactive_count = 0

            for referral in referrals:
                # Check if user has any transactions
                transaction_count = (
                    session.query(Transaction)
                    .filter(Transaction.user_id == referral.id)
                    .count()
                )

                if transaction_count > 0:
                    active_count += 1
                else:
                    inactive_count += 1

            total_referrals = len(referrals)
            if total_referrals > 5:
                activity_rate = active_count / total_referrals

                # Suspiciously low activity rate
                if activity_rate < 0.1 and total_referrals > 10:
                    analysis["risk_score"] += 20
                    analysis["risk_factors"].append(
                        f"Low activity rate: {activity_rate:.1%}"
                    )
                    analysis["suspicious_patterns"].append(
                        {
                            "type": "low_activity",
                            "description": f"Only {activity_rate:.1%} of referred users are active",
                            "severity": "medium",
                        }
                    )
                    return True

                # Suspiciously high activity rate (could indicate coordinated fake activity)
                elif activity_rate > 0.9 and total_referrals > 20:
                    analysis["risk_score"] += 15
                    analysis["risk_factors"].append(
                        f"Unusually high activity rate: {activity_rate:.1%}"
                    )
                    analysis["suspicious_patterns"].append(
                        {
                            "type": "high_activity",
                            "description": f"{activity_rate:.1%} activity rate may indicate coordinated activity",
                            "severity": "medium",
                        }
                    )
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking activity patterns: {e}")
            return False

    @staticmethod
    def _check_timing_patterns(
        user: User, referrals: List[User], analysis: Dict[str, Any]
    ) -> bool:
        """Check timing patterns between account creation and referrals"""
        if not user.created_at or not referrals:
            return False

        # Check if user started referring immediately after account creation
        first_referral = min(referrals, key=lambda x: x.created_at or datetime.max)
        if first_referral.created_at:
            time_to_first_referral = (
                first_referral.created_at - user.created_at
            ).total_seconds()

            # Started referring within 1 hour of account creation
            if time_to_first_referral < 3600 and len(referrals) > 3:
                analysis["risk_score"] += 15
                analysis["risk_factors"].append(
                    "Immediate referral activity after signup"
                )
                analysis["suspicious_patterns"].append(
                    {
                        "type": "immediate_referrals",
                        "description": f"Started referring {time_to_first_referral/60:.0f} minutes after account creation",
                        "severity": "medium",
                    }
                )
                return True

        return False

    @staticmethod
    def _calculate_risk_level(risk_score: int) -> str:
        """Calculate risk level based on score"""
        if risk_score >= 50:
            return "critical"
        elif risk_score >= 30:
            return "high"
        elif risk_score >= 15:
            return "medium"
        else:
            return "low"

    @staticmethod
    def create_fraud_alert(
        user_id: int, analysis: Dict[str, Any], session=None
    ) -> Optional[int]:
        """Create fraud alert if risk score is high enough"""
        close_session = False
        if not session:
            session = SessionLocal()
            close_session = True

        try:
            if analysis["risk_score"] < 15:  # Only create alerts for medium+ risk
                return None

            # Check if alert already exists for this user
            existing_alert = (
                session.query(ReferralFraudAlert)
                .filter(
                    and_(
                        ReferralFraudAlert.user_id == user_id,
                        ReferralFraudAlert.status == "pending",
                    )
                )
                .first()
            )

            if existing_alert:
                return existing_alert.id

            # Create new alert
            alert = ReferralFraudAlert(
                user_id=user_id,
                alert_type="automated_detection",
                severity=analysis["risk_level"],
                description=f"Automated fraud detection (Risk Score: {analysis['risk_score']})",
                evidence_data=json.dumps(analysis),
                status="pending",
            )

            session.add(alert)
            session.commit()

            logger.warning(
                f"Fraud alert created for user {user_id}: risk score {analysis['risk_score']}"
            )

            return alert.id

        except Exception as e:
            session.rollback()
            logger.error(f"Error creating fraud alert: {e}")
            return None
        finally:
            if close_session:
                session.close()

    @staticmethod
    def monitor_referral_activity():
        """Periodic monitoring job for referral fraud detection"""
        session = SessionLocal()
        try:
            # Get users with recent referral activity
            recent_date = datetime.utcnow() - timedelta(days=7)

            active_referrers = (
                session.query(User.referred_by)
                .filter(
                    and_(User.referred_by.isnot(None), User.created_at >= recent_date)
                )
                .distinct()
                .all()
            )

            alerts_created = 0
            for (referrer_id,) in active_referrers:
                try:
                    analysis = ReferralFraudDetector.analyze_user_behavior(
                        referrer_id, session
                    )
                    if analysis.get("risk_score", 0) >= 15:
                        alert_id = ReferralFraudDetector.create_fraud_alert(
                            referrer_id, analysis, session
                        )
                        if alert_id:
                            alerts_created += 1
                except Exception as e:
                    logger.error(f"Error analyzing user {referrer_id}: {e}")

            logger.info(
                f"Referral fraud monitoring completed: {alerts_created} new alerts created"
            )

        except Exception as e:
            logger.error(f"Error in referral fraud monitoring: {e}")
        finally:
            session.close()
