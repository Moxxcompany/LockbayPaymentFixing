"""
Achievement Tracking Service
Automatically tracks and awards achievements to users
"""

import logging
from models import User, Escrow, Rating
from utils.trusted_trader import TrustedTraderSystem
from services.consolidated_notification_service import (
    consolidated_notification_service as NotificationService,
)
from utils.markdown_escaping import escape_markdown

logger = logging.getLogger(__name__)


class AchievementTracker:
    """Tracks and awards achievements automatically"""

    @staticmethod
    async def check_and_award_achievements(session, user_id, trigger_event="general"):
        """Check for new achievements and notify user"""
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return

            # Get previous achievements (stored in user preferences or separate table)
            previous_achievements = user.notification_preferences.get(
                "earned_achievements", []
            )

            # Get current achievements
            current_achievements = TrustedTraderSystem.get_achievement_status(
                user, session
            )

            # Find new achievements
            new_achievements = [
                a for a in current_achievements if a not in previous_achievements
            ]

            if new_achievements:
                # Update user's earned achievements
                if not user.notification_preferences:
                    user.notification_preferences = {}
                user.notification_preferences["earned_achievements"] = (
                    current_achievements
                )
                session.commit()

                # Send achievement notifications
                await AchievementTracker._notify_achievements(user, new_achievements)

                logger.info(
                    f"Awarded {len(new_achievements)} new achievements to user {user_id}"
                )

            return new_achievements

        except Exception as e:
            logger.error(f"Error checking achievements for user {user_id}: {e}")
            return []

    @staticmethod
    async def _notify_achievements(user, achievements):
        """Send achievement notifications to user"""
        try:
            notification_service = NotificationService()

            for achievement_key in achievements:
                achievement = TrustedTraderSystem.ACHIEVEMENTS.get(achievement_key)
                if achievement:
                    # Safely escape all user-displayed content
                    safe_name = escape_markdown(achievement["name"])
                    safe_description = escape_markdown(achievement["description"])
                    safe_reward = escape_markdown(achievement["reward"])
                    safe_icon = escape_markdown(achievement["icon"])

                    message = f"""🎉 Achievement Unlocked!

{safe_icon} {safe_name}

{safe_description}

Reward: {safe_reward}

Keep up the excellent work!"""

                    # Send Telegram notification
                    await notification_service.send_telegram_notification(
                        user.telegram_id, message, parse_mode="Markdown"
                    )

        except Exception as e:
            logger.error(f"Error sending achievement notifications: {e}")

    @staticmethod
    async def check_level_promotion(session, user_id):
        """Check if user has been promoted to a new trader level"""
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return

            # Get current level
            current_level = TrustedTraderSystem.get_trader_level(user, session)

            # Check if this is a promotion (stored in user preferences)
            last_known_level = user.notification_preferences.get("last_trader_level", 0)
            current_threshold = current_level.get("threshold", 0)

            if current_threshold > last_known_level:
                # User has been promoted!
                if not user.notification_preferences:
                    user.notification_preferences = {}
                user.notification_preferences["last_trader_level"] = current_threshold
                session.commit()

                # Send promotion notification
                await AchievementTracker._notify_level_promotion(user, current_level)

                logger.info(f"User {user_id} promoted to {current_level['name']}")

        except Exception as e:
            logger.error(f"Error checking level promotion for user {user_id}: {e}")

    @staticmethod
    async def _notify_level_promotion(user, level_info):
        """Send level promotion notification"""
        try:
            notification_service = NotificationService()

            # Safely escape level information
            safe_badge = escape_markdown(level_info["badge"])
            safe_level_name = escape_markdown(level_info["name"])

            message = f"""🎖️ Level Promotion!

Congratulations! You've been promoted to:

{safe_badge} {safe_level_name}

New Benefits:
"""

            for benefit in level_info.get("benefits", []):
                safe_benefit = escape_markdown(benefit)
                message += f"• {safe_benefit}\n"

            message += "\nThank you for being a valued member of our trading community!"

            # Send Telegram notification
            await notification_service.send_telegram_notification(
                user.telegram_id, message, parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Error sending level promotion notification: {e}")

    @staticmethod
    async def process_trade_completion(session, escrow_id):
        """Process achievements when a trade is completed"""
        try:
            escrow = session.query(Escrow).filter(Escrow.id == escrow_id).first()
            if not escrow:
                return

            # Check achievements for both buyer and seller
            for user_id in [escrow.buyer_id, escrow.seller_id]:
                if user_id:
                    await AchievementTracker.check_and_award_achievements(
                        session, user_id, "trade_completion"
                    )
                    await AchievementTracker.check_level_promotion(session, user_id)

        except Exception as e:
            logger.error(f"Error processing trade completion achievements: {e}")

    @staticmethod
    async def process_rating_received(session, rating_id):
        """Process achievements when a rating is received"""
        try:
            rating = session.query(Rating).filter(Rating.id == rating_id).first()
            if not rating:
                return

            # Check achievements for the rated user
            await AchievementTracker.check_and_award_achievements(
                session, rating.rated_id, "rating_received"
            )
            await AchievementTracker.check_level_promotion(session, rating.rated_id)

        except Exception as e:
            logger.error(f"Error processing rating achievements: {e}")

    @staticmethod
    def get_user_progress_summary(session, user_id):
        """Get a summary of user's progress towards next achievements"""
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return None

            # Get current level
            current_level = TrustedTraderSystem.get_trader_level(user, session)
            next_threshold, next_level = TrustedTraderSystem.get_next_level(
                current_level.get("threshold", 0)
            )

            # Get trade stats
            total_trades = (
                session.query(Escrow)
                .filter((Escrow.buyer_id == user.id) | (Escrow.seller_id == user.id))
                .count()
            )

            completed_trades = (
                session.query(Escrow)
                .filter(
                    ((Escrow.buyer_id == user.id) | (Escrow.seller_id == user.id)),
                    Escrow.status == "completed",
                )
                .count()
            )

            summary = {
                "current_level": current_level,
                "next_level": next_level,
                "next_threshold": next_threshold,
                "current_trades": total_trades,
                "completed_trades": completed_trades,
                "reputation": getattr(user, 'reputation_score', 0.0),
                "total_volume": user.total_volume_usd,
            }

            return summary

        except Exception as e:
            logger.error(f"Error getting progress summary for user {user_id}: {e}")
            return None
