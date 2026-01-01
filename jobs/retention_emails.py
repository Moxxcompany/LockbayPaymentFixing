"""Background job for sending retention follow-up emails"""

import logging
from datetime import datetime, timedelta
from sqlalchemy import and_
from database import SessionLocal
from models import User, Escrow
from services.welcome_email import WelcomeEmailService

logger = logging.getLogger(__name__)


async def send_followup_emails():
    """Send follow-up emails to users who haven't started trading yet"""
    session = SessionLocal()

    try:
        # Find users who signed up 3 days ago but haven't created any escrows
        three_days_ago = datetime.utcnow() - timedelta(days=3)

        users_to_follow_up = (
            session.query(User)
            .filter(
                and_(
                    User.created_at
                    >= three_days_ago
                    - timedelta(hours=1),  # Signed up around 3 days ago
                    User.created_at <= three_days_ago + timedelta(hours=1),
                    User.email.isnot(None),  # Has email address
                    ~User.id.in_(
                        session.query(Escrow.buyer_id).filter(
                            Escrow.buyer_id.isnot(None)
                        )
                    ),  # Hasn't created any escrows as buyer
                )
            )
            .all()
        )

        if not users_to_follow_up:
            logger.info("No users found for 3-day follow-up emails")
            return

        welcome_service = WelcomeEmailService()
        sent_count = 0

        for user in users_to_follow_up:
            try:
                success = await welcome_service.send_followup_email(
                    user.email, user.first_name or user.username or "there", 3
                )

                if success:
                    sent_count += 1
                    logger.info(
                        f"Follow-up email sent to user {user.id} ({user.email})"
                    )
                else:
                    logger.warning(
                        f"Failed to send follow-up email to user {user.id} ({user.email})"
                    )

            except Exception as e:
                logger.error(f"Error sending follow-up email to user {user.id}: {e}")

        logger.info(f"Follow-up emails sent: {sent_count}/{len(users_to_follow_up)}")

    except Exception as e:
        logger.error(f"Error in send_followup_emails job: {e}")
    finally:
        session.close()


async def send_weekly_retention_emails():
    """Send weekly retention emails to inactive users"""
    session = SessionLocal()

    try:
        # Find users who signed up 7 days ago but haven't been active
        one_week_ago = datetime.utcnow() - timedelta(days=7)

        inactive_users = (
            session.query(User)
            .filter(
                and_(
                    User.created_at >= one_week_ago - timedelta(hours=1),
                    User.created_at <= one_week_ago + timedelta(hours=1),
                    User.email.isnot(None),
                    User.completed_trades == 0,  # No completed trades
                )
            )
            .all()
        )

        if not inactive_users:
            logger.info("No users found for 7-day retention emails")
            return

        welcome_service = WelcomeEmailService()
        sent_count = 0

        for user in inactive_users:
            try:
                success = await welcome_service.send_followup_email(
                    user.email, user.first_name or user.username or "there", 7
                )

                if success:
                    sent_count += 1
                    logger.info(
                        f"7-day retention email sent to user {user.id} ({user.email})"
                    )

            except Exception as e:
                logger.error(
                    f"Error sending 7-day retention email to user {user.id}: {e}"
                )

        logger.info(f"7-day retention emails sent: {sent_count}/{len(inactive_users)}")

    except Exception as e:
        logger.error(f"Error in send_weekly_retention_emails job: {e}")
    finally:
        session.close()
