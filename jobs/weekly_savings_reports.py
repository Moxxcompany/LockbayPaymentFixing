"""
Weekly Savings Reports Job - Phase 2 Retention Strategy
Send weekly savings reports to engaged users
"""

import logging
import asyncio
from telegram import Bot
from telegram.error import TelegramError
from services.savings_service import savings_service
from database import SessionLocal
from models import User
from config import Config

logger = logging.getLogger(__name__)


async def send_weekly_savings_reports():
    """Send weekly savings reports to eligible users"""
    try:
        logger.info("Starting weekly savings reports job...")

        # Get users who need weekly reports
        user_ids = await savings_service.get_users_needing_weekly_reports()

        if not user_ids:
            logger.info("No users need weekly reports")
            return

        logger.info(f"Sending weekly reports to {len(user_ids)} users")

        # Initialize bot
        bot_token = Config.BOT_TOKEN
        if not bot_token:
            logger.error("BOT_TOKEN not configured - cannot send weekly reports")
            return
        bot = Bot(token=bot_token)

        sent_count = 0
        error_count = 0

        session = SessionLocal()
        try:
            for user_id in user_ids:
                try:
                    # Get user telegram ID
                    user = session.query(User).filter(User.id == user_id).first()
                    if not user:
                        continue

                    # Get savings summary
                    savings_summary = await savings_service.get_user_savings_summary(
                        user_id
                    )

                    if savings_summary.get("weekly_savings", 0) <= 0:
                        continue  # Skip users with no weekly savings

                    # Generate weekly report message
                    report_message = savings_service.get_weekly_report_message(
                        savings_summary
                    )

                    # Send report
                    await bot.send_message(
                        chat_id=int(user.telegram_id),
                        text=report_message,
                        parse_mode="Markdown",
                    )

                    # Mark report as sent
                    await savings_service.mark_weekly_report_sent(user_id)

                    sent_count += 1
                    logger.info(f"Weekly report sent to user {user_id}")

                    # Small delay to avoid rate limits
                    await asyncio.sleep(0.1)

                except TelegramError as e:
                    if "blocked" in str(e).lower() or "deactivated" in str(e).lower():
                        logger.info(
                            f"User {user_id} blocked bot or deactivated account"
                        )
                    else:
                        logger.error(
                            f"Telegram error sending report to user {user_id}: {e}"
                        )
                    error_count += 1
                    continue

                except Exception as e:
                    logger.error(f"Error sending weekly report to user {user_id}: {e}")
                    error_count += 1
                    continue

        finally:
            session.close()

        logger.info(
            f"Weekly savings reports completed: {sent_count} sent, {error_count} errors"
        )

    except Exception as e:
        logger.error(f"Error in weekly savings reports job: {e}")
        import traceback

        logger.error(f"Full traceback: {traceback.format_exc()}")


# Export for scheduler
weekly_savings_reports_job = send_weekly_savings_reports
