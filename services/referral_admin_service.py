"""Comprehensive admin service for referral system management"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_
from database import SessionLocal
from models import (
    User,
    Transaction,
    ReferralConfig,
    ReferralFraudAlert,
)
from utils.referral import ReferralSystem

logger = logging.getLogger(__name__)


class ReferralAdminService:
    """Administrative service for comprehensive referral system management"""

    @staticmethod
    def get_current_config(session=None) -> Dict[str, Any]:
        """Get current referral system configuration"""
        close_session = False
        if not session:
            session = SessionLocal()
            close_session = True

        try:
            config = (
                session.query(ReferralConfig)
                .order_by(desc(ReferralConfig.created_at))
                .first()
            )

            if not config:
                # Create default configuration
                config = ReferralConfig()
                session.add(config)
                session.commit()
                logger.info("Created default referral configuration")

            return {
                "id": config.id,
                # Core rewards
                "referrer_reward_usd": float(getattr(config, 'referrer_reward_usd', 5.0)),
                "referee_reward_usd": float(getattr(config, 'referee_reward_usd', 3.0)),
                "min_activity_for_reward": float(getattr(config, 'min_activity_for_reward', 50.0)),
                
                # Regional adjustments
                "enable_regional_adjustments": getattr(config, 'enable_regional_adjustments', True),
                "regional_adjustment_multiplier": float(getattr(config, 'regional_adjustment_multiplier', 0.8)),
                "minimum_threshold_floor_usd": float(getattr(config, 'minimum_threshold_floor_usd', 5.0)),
                "developing_tier_multiplier": float(getattr(config, 'developing_tier_multiplier', 0.4)),
                "emerging_tier_multiplier": float(getattr(config, 'emerging_tier_multiplier', 0.6)),
                "developed_tier_multiplier": float(getattr(config, 'developed_tier_multiplier', 1.0)),
                
                # System settings
                "system_enabled": config.system_enabled,
                "max_referrals_per_user": config.max_referrals_per_user,
                "reward_cap_per_user": (
                    float(config.reward_cap_per_user)
                    if config.reward_cap_per_user
                    else None
                ),
                
                # Fraud protection
                "enable_fraud_detection": config.enable_fraud_detection,
                "min_account_age_hours": config.min_account_age_hours,
                "max_referrals_per_day": config.max_referrals_per_day,
                "fraud_risk_threshold": float(getattr(config, 'fraud_risk_threshold', 70.0)),
                "auto_block_high_risk": getattr(config, 'auto_block_high_risk', False),
                
                # Performance optimization
                "batch_reward_processing": getattr(config, 'batch_reward_processing', True),
                "reward_processing_delay_hours": getattr(config, 'reward_processing_delay_hours', 24),
                "auto_expire_inactive_codes": getattr(config, 'auto_expire_inactive_codes', True),
                "inactive_code_expiry_days": getattr(config, 'inactive_code_expiry_days', 90),
                
                # Analytics and monitoring
                "track_conversion_funnel": getattr(config, 'track_conversion_funnel', True),
                "enable_a_b_testing": getattr(config, 'enable_a_b_testing', False),
                "send_performance_alerts": getattr(config, 'send_performance_alerts', True),
                
                # Metadata
                "updated_at": (
                    config.updated_at.isoformat() if config.updated_at else None
                ),
                "updated_by_admin_id": config.updated_by_admin_id,
            }

        except Exception as e:
            logger.error(f"Error getting referral config: {e}")
            return ReferralAdminService._get_default_config()
        finally:
            if close_session:
                session.close()

    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """Get default configuration values"""
        return {
            # Core rewards
            "referrer_reward_usd": 5.0,
            "referee_reward_usd": 3.0,
            "min_activity_for_reward": 50.0,
            
            # Regional adjustments
            "enable_regional_adjustments": True,
            "regional_adjustment_multiplier": 0.8,
            "minimum_threshold_floor_usd": 5.0,
            "developing_tier_multiplier": 0.4,
            "emerging_tier_multiplier": 0.6,
            "developed_tier_multiplier": 1.0,
            
            # System settings
            "system_enabled": True,
            "max_referrals_per_user": None,
            "reward_cap_per_user": None,
            
            # Fraud protection
            "enable_fraud_detection": True,
            "min_account_age_hours": 24,
            "max_referrals_per_day": 10,
            "fraud_risk_threshold": 70.0,
            "auto_block_high_risk": False,
            
            # Performance optimization
            "batch_reward_processing": True,
            "reward_processing_delay_hours": 24,
            "auto_expire_inactive_codes": True,
            "inactive_code_expiry_days": 90,
            
            # Analytics and monitoring
            "track_conversion_funnel": True,
            "enable_a_b_testing": False,
            "send_performance_alerts": True,
        }

    @staticmethod
    def update_config(
        admin_user_id: int, updates: Dict[str, Any], reason: str = ""
    ) -> Dict[str, Any]:
        """Update referral system configuration"""
        session = SessionLocal()
        try:
            # Get current config
            current_config = (
                session.query(ReferralConfig)
                .order_by(desc(ReferralConfig.created_at))
                .first()
            )

            # Create new config entry (audit trail)
            new_config = ReferralConfig(
                referrer_reward_usd=updates.get(
                    "referrer_reward_usd",
                    current_config.referrer_reward_usd if current_config else 5.0,
                ),
                referee_reward_usd=updates.get(
                    "referee_reward_usd",
                    current_config.referee_reward_usd if current_config else 3.0,
                ),
                min_activity_for_reward=updates.get(
                    "min_activity_for_reward",
                    current_config.min_activity_for_reward if current_config else 50.0,
                ),
                system_enabled=updates.get(
                    "system_enabled",
                    current_config.system_enabled if current_config else True,
                ),
                max_referrals_per_user=updates.get(
                    "max_referrals_per_user",
                    current_config.max_referrals_per_user if current_config else None,
                ),
                reward_cap_per_user=updates.get(
                    "reward_cap_per_user",
                    current_config.reward_cap_per_user if current_config else None,
                ),
                enable_fraud_detection=updates.get(
                    "enable_fraud_detection",
                    current_config.enable_fraud_detection if current_config else True,
                ),
                min_account_age_hours=updates.get(
                    "min_account_age_hours",
                    current_config.min_account_age_hours if current_config else 24,
                ),
                max_referrals_per_day=updates.get(
                    "max_referrals_per_day",
                    current_config.max_referrals_per_day if current_config else 10,
                ),
                updated_by_admin_id=admin_user_id,
                update_reason=reason,
            )

            session.add(new_config)
            session.commit()

            # Update ReferralSystem class constants (for backward compatibility)
            ReferralSystem.REFERRER_REWARD_USD = new_config.referrer_reward_usd
            ReferralSystem.REFEREE_REWARD_USD = new_config.referee_reward_usd
            ReferralSystem.MIN_ACTIVITY_FOR_REWARD = new_config.min_activity_for_reward

            logger.info(f"Referral config updated by admin {admin_user_id}: {updates}")

            return {
                "success": True,
                "config_id": new_config.id,
                "message": "Configuration updated successfully",
            }

        except Exception as e:
            session.rollback()
            logger.error(f"Error updating referral config: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    @staticmethod
    def get_system_analytics(days: int = 30, session=None) -> Dict[str, Any]:
        """Get comprehensive referral system analytics"""
        close_session = False
        if not session:
            session = SessionLocal()
            close_session = True

        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            # Overall system stats
            total_users_with_referrals = (
                session.query(User).filter(User.referred_by.isnot(None)).count()
            )
            total_active_referrers = (
                session.query(User.referred_by)
                .filter(User.referred_by.isnot(None))
                .distinct()
                .count()
            )

            # Recent activity
            recent_referrals = (
                session.query(User)
                .filter(
                    and_(User.referred_by.isnot(None), User.created_at >= start_date)
                )
                .count()
            )

            # Reward distribution
            total_rewards_query = session.query(func.sum(Transaction.amount)).filter(
                and_(
                    Transaction.transaction_type.in_(
                        ["referral_bonus", "referral_reward"]
                    ),
                    Transaction.created_at >= start_date,
                )
            )
            total_rewards = float(total_rewards_query.scalar() or 0)

            # Top referrers
            top_referrers = (
                session.query(
                    User.referred_by,
                    func.count(User.id).label("referral_count"),
                    func.max(User.first_name).label("referrer_name"),
                )
                .filter(User.referred_by.isnot(None))
                .group_by(User.referred_by)
                .order_by(desc("referral_count"))
                .limit(10)
                .all()
            )

            # Conversion rates
            total_referred = (
                session.query(User).filter(User.referred_by.isnot(None)).count()
            )
            active_referred = 0
            if total_referred > 0:
                for user in (
                    session.query(User).filter(User.referred_by.isnot(None)).all()
                ):
                    volume = ReferralSystem._get_user_trading_volume(user.id, session)
                    if volume >= ReferralSystem.MIN_ACTIVITY_FOR_REWARD:
                        active_referred += 1

            conversion_rate = (
                (active_referred / total_referred * 100) if total_referred > 0 else 0
            )

            # Fraud alerts
            pending_alerts = (
                session.query(ReferralFraudAlert)
                .filter(ReferralFraudAlert.status == "pending")
                .count()
            )

            critical_alerts = (
                session.query(ReferralFraudAlert)
                .filter(
                    and_(
                        ReferralFraudAlert.status == "pending",
                        ReferralFraudAlert.severity == "critical",
                    )
                )
                .count()
            )

            return {
                "period_days": days,
                "total_stats": {
                    "total_users_referred": total_users_with_referrals,
                    "total_active_referrers": total_active_referrers,
                    "recent_referrals": recent_referrals,
                    "total_rewards_paid": total_rewards,
                    "conversion_rate": round(conversion_rate, 2),
                },
                "top_referrers": [
                    {
                        "user_id": row.referred_by,
                        "referral_count": row.referral_count,
                        "display_name": row.referrer_name or f"User {row.referred_by}",
                    }
                    for row in top_referrers
                ],
                "fraud_alerts": {
                    "pending_total": pending_alerts,
                    "critical_count": critical_alerts,
                },
                "system_health": {
                    "fraud_rate": round(
                        (
                            (critical_alerts / total_referred * 100)
                            if total_referred > 0
                            else 0
                        ),
                        2,
                    ),
                    "growth_trend": "positive" if recent_referrals > 0 else "stable",
                },
            }

        except Exception as e:
            logger.error(f"Error getting referral analytics: {e}")
            return {
                "error": str(e),
                "total_stats": {
                    "total_users_referred": 0,
                    "total_active_referrers": 0,
                    "recent_referrals": 0,
                    "total_rewards_paid": 0.0,
                    "conversion_rate": 0.0,
                },
            }
        finally:
            if close_session:
                session.close()

    @staticmethod
    def get_user_referral_details(user_id: int, session=None) -> Dict[str, Any]:
        """Get detailed referral information for specific user"""
        close_session = False
        if not session:
            session = SessionLocal()
            close_session = True

        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return {"error": "User not found"}

            # Get user's referral stats
            stats = ReferralSystem.get_referral_stats(user, session)

            # Get referrals made by user
            referrals = session.query(User).filter(User.referred_by == user.id).all()

            # Get fraud alerts for this user
            fraud_alerts = (
                session.query(ReferralFraudAlert)
                .filter(ReferralFraudAlert.user_id == user_id)
                .order_by(desc(ReferralFraudAlert.created_at))
                .all()
            )

            # Get reward transactions
            reward_transactions = (
                session.query(Transaction)
                .filter(
                    and_(
                        Transaction.user_id == user_id,
                        Transaction.transaction_type.in_(
                            ["referral_bonus", "referral_reward"]
                        ),
                    )
                )
                .order_by(desc(Transaction.created_at))
                .all()
            )

            return {
                "user_info": {
                    "id": user.id,
                    "telegram_id": user.telegram_id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "created_at": (
                        user.created_at.isoformat() if user.created_at else None
                    ),
                },
                "referral_stats": stats,
                "referrals_detail": [
                    {
                        "id": ref.id,
                        "telegram_id": ref.telegram_id,
                        "username": ref.username,
                        "first_name": ref.first_name,
                        "created_at": (
                            ref.created_at.isoformat() if ref.created_at else None
                        ),
                        "trading_volume": ReferralSystem._get_user_trading_volume(
                            ref.id, session
                        ),
                    }
                    for ref in referrals
                ],
                "fraud_alerts": [
                    {
                        "id": alert.id,
                        "alert_type": alert.alert_type,
                        "severity": alert.severity,
                        "description": alert.description,
                        "status": alert.status,
                        "created_at": (
                            alert.created_at.isoformat() if alert.created_at else None
                        ),
                    }
                    for alert in fraud_alerts
                ],
                "reward_history": [
                    {
                        "id": tx.id,
                        "amount": float(tx.amount),
                        "type": tx.transaction_type,
                        "description": tx.description,
                        "created_at": (
                            tx.created_at.isoformat() if tx.created_at else None
                        ),
                    }
                    for tx in reward_transactions
                ],
            }

        except Exception as e:
            logger.error(f"Error getting user referral details: {e}")
            return {"error": str(e)}
        finally:
            if close_session:
                session.close()

    @staticmethod
    def get_pending_fraud_alerts(session=None) -> List[Dict[str, Any]]:
        """Get all pending fraud alerts requiring admin review"""
        close_session = False
        if not session:
            session = SessionLocal()
            close_session = True

        try:
            alerts = (
                session.query(ReferralFraudAlert)
                .filter(ReferralFraudAlert.status == "pending")
                .order_by(
                    desc(ReferralFraudAlert.severity),
                    desc(ReferralFraudAlert.created_at),
                )
                .all()
            )

            result = []
            for alert in alerts:
                user = session.query(User).filter(User.id == alert.user_id).first()

                result.append(
                    {
                        "alert_id": alert.id,
                        "user_id": alert.user_id,
                        "user_info": {
                            "username": user.username if user else "Unknown",
                            "first_name": user.first_name if user else "Unknown",
                            "telegram_id": user.telegram_id if user else "Unknown",
                        },
                        "alert_type": alert.alert_type,
                        "severity": alert.severity,
                        "description": alert.description,
                        "evidence_data": alert.evidence_data,
                        "created_at": (
                            alert.created_at.isoformat() if alert.created_at else None
                        ),
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Error getting fraud alerts: {e}")
            return []
        finally:
            if close_session:
                session.close()

    @staticmethod
    def resolve_fraud_alert(
        alert_id: int, admin_user_id: int, action: str, notes: str = ""
    ) -> Dict[str, Any]:
        """Resolve a fraud alert with admin action"""
        session = SessionLocal()
        try:
            alert = (
                session.query(ReferralFraudAlert)
                .filter(ReferralFraudAlert.id == alert_id)
                .first()
            )
            if not alert:
                return {"success": False, "error": "Alert not found"}

            setattr(alert, 'status', "reviewed")
            setattr(alert, 'reviewed_by_admin_id', admin_user_id)
            setattr(alert, 'admin_notes', notes)
            setattr(alert, 'action_taken', action)
            setattr(alert, 'reviewed_at', datetime.utcnow())

            if action in ["resolved", "false_positive"]:
                setattr(alert, 'resolved_at', datetime.utcnow())
                setattr(alert, 'status', action)

            session.commit()

            logger.info(
                f"Fraud alert {alert_id} resolved by admin {admin_user_id}: {action}"
            )

            return {"success": True, "message": f"Alert {action} successfully"}

        except Exception as e:
            session.rollback()
            logger.error(f"Error resolving fraud alert: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    @staticmethod
    def block_user_referrals(
        user_id: int, admin_user_id: int, reason: str, permanent: bool = False
    ) -> Dict[str, Any]:
        """Block user from referral system"""
        session = SessionLocal()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}

            # Create fraud alert record
            alert = ReferralFraudAlert(
                user_id=user_id,
                alert_type="admin_block",
                severity="high",
                description=f"User blocked from referral system by admin. Reason: {reason}",
                status="resolved",
                reviewed_by_admin_id=admin_user_id,
                admin_notes=f'{"Permanent" if permanent else "Temporary"} block: {reason}',
                action_taken="blocked",
                reviewed_at=datetime.utcnow(),
                resolved_at=datetime.utcnow(),
            )

            session.add(alert)
            session.commit()

            logger.warning(
                f"User {user_id} blocked from referrals by admin {admin_user_id}: {reason}"
            )

            return {
                "success": True,
                "message": "User blocked from referral system",
                "alert_id": alert.id,
            }

        except Exception as e:
            session.rollback()
            logger.error(f"Error blocking user referrals: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    @staticmethod
    def bulk_manage_referrals(
        admin_user_id: int, action: str, user_ids: List[int], reason: str = ""
    ) -> Dict[str, Any]:
        """Bulk management operations for referral users"""
        session = SessionLocal()
        try:
            results = {"successful": [], "failed": [], "total_processed": len(user_ids)}

            for user_id in user_ids:
                try:
                    if action == "block":
                        result = ReferralAdminService.block_user_referrals(
                            user_id, admin_user_id, reason
                        )
                        if result["success"]:
                            results["successful"].append(user_id)
                        else:
                            results["failed"].append(
                                {"user_id": user_id, "error": result["error"]}
                            )

                    # Add more bulk actions as needed

                except Exception as e:
                    results["failed"].append({"user_id": user_id, "error": str(e)})

            logger.info(
                f"Bulk referral action '{action}' by admin {admin_user_id}: {len(results['successful'])} successful, {len(results['failed'])} failed"
            )

            return {"success": True, "results": results}

        except Exception as e:
            logger.error(f"Error in bulk referral management: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()
