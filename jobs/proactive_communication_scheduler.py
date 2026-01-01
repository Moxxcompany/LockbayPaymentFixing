"""
Proactive Communication Scheduler
Schedules follow-up notifications and user engagement during trade wait periods
Extended to support DirectExchange post-completion engagement
"""

import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.proactive_communication import ProactiveCommunicationService
from models import Escrow
from database import SessionLocal

logger = logging.getLogger(__name__)


class ProactiveCommunicationScheduler:
    """Scheduler for proactive communication tasks"""

    @staticmethod
    def schedule_trade_followups(
        escrow_id: str, user_id: int, scheduler: AsyncIOScheduler
    ):
        """Schedule all follow-up communications for a trade"""
        try:
            # Schedule 15-minute follow-up
            run_time_15min = datetime.utcnow() + timedelta(minutes=15)
            scheduler.add_job(
                ProactiveCommunicationScheduler._send_15min_with_context,
                "date",
                run_date=run_time_15min,
                args=[escrow_id, user_id],
                id=f"followup_15min_{escrow_id}",
                replace_existing=True,
            )

            # Schedule 2-hour follow-up
            run_time_2hour = datetime.utcnow() + timedelta(hours=2)
            scheduler.add_job(
                ProactiveCommunicationScheduler._send_2hour_with_context,
                "date",
                run_date=run_time_2hour,
                args=[escrow_id, user_id],
                id=f"followup_2hour_{escrow_id}",
                replace_existing=True,
            )

            # Schedule daily check-ins for first 3 days
            for day in range(1, 4):
                run_time_daily = datetime.utcnow() + timedelta(days=day)
                scheduler.add_job(
                    ProactiveCommunicationScheduler._send_daily_with_context,
                    "date",
                    run_date=run_time_daily,
                    args=[escrow_id, user_id],
                    id=f"daily_checkin_{escrow_id}_day{day}",
                    replace_existing=True,
                )

            logger.info(f"Scheduled proactive communications for trade {escrow_id}")

        except Exception as e:
            logger.error(f"Error scheduling trade follow-ups: {e}")

    @staticmethod
    def schedule_exchange_followups(
        exchange_id: str, user_id: int, scheduler: AsyncIOScheduler
    ):
        """Schedule all post-completion follow-ups for a DirectExchange"""
        try:
            # Schedule immediate completion follow-up (5 minutes after completion)
            run_time_immediate = datetime.utcnow() + timedelta(minutes=5)
            scheduler.add_job(
                ProactiveCommunicationScheduler._send_exchange_immediate_with_context,
                "date",
                run_date=run_time_immediate,
                args=[exchange_id, user_id],
                id=f"exchange_immediate_{exchange_id}",
                replace_existing=True,
            )

            # Schedule achievement follow-up (30 minutes after completion)
            run_time_achievement = datetime.utcnow() + timedelta(minutes=30)
            scheduler.add_job(
                ProactiveCommunicationScheduler._send_exchange_achievement_with_context,
                "date",
                run_date=run_time_achievement,
                args=[exchange_id, user_id],
                id=f"exchange_achievement_{exchange_id}",
                replace_existing=True,
            )

            # Schedule educational follow-up (24 hours after completion)
            run_time_educational = datetime.utcnow() + timedelta(hours=24)
            scheduler.add_job(
                ProactiveCommunicationScheduler._send_exchange_educational_with_context,
                "date",
                run_date=run_time_educational,
                args=[exchange_id, user_id],
                id=f"exchange_educational_{exchange_id}",
                replace_existing=True,
            )

            logger.info(f"Scheduled post-exchange engagement for exchange {exchange_id}")

        except Exception as e:
            logger.error(f"Error scheduling exchange follow-ups: {e}")

    @staticmethod
    def cancel_trade_followups(escrow_id: str, scheduler: AsyncIOScheduler):
        """Cancel all scheduled follow-ups for a trade (when trade is completed/cancelled)"""
        try:
            jobs_to_remove = [
                f"followup_15min_{escrow_id}",
                f"followup_2hour_{escrow_id}",
                f"daily_checkin_{escrow_id}_day1",
                f"daily_checkin_{escrow_id}_day2",
                f"daily_checkin_{escrow_id}_day3",
            ]

            for job_id in jobs_to_remove:
                try:
                    scheduler.remove_job(job_id)
                    logger.info(f"Cancelled scheduled job: {job_id}")
                except Exception as e:
                    # Job might not exist or already executed
                    logger.debug(f"Job {job_id} not found or already executed: {e}")
                    pass

        except Exception as e:
            logger.error(f"Error cancelling trade follow-ups: {e}")

    @staticmethod
    def cancel_exchange_followups(exchange_id: str, scheduler: AsyncIOScheduler):
        """Cancel all scheduled follow-ups for an exchange (if needed)"""
        try:
            jobs_to_remove = [
                f"exchange_immediate_{exchange_id}",
                f"exchange_achievement_{exchange_id}",
                f"exchange_educational_{exchange_id}",
            ]

            for job_id in jobs_to_remove:
                try:
                    scheduler.remove_job(job_id)
                    logger.info(f"Removed scheduled job: {job_id}")
                except Exception:
                    pass  # Job might not exist

            logger.info(f"Cancelled all exchange follow-ups for {exchange_id}")

        except Exception as e:
            logger.error(f"Error cancelling exchange follow-ups: {e}")

    @staticmethod
    def schedule_weekly_milestone_report(user_id: int, scheduler: AsyncIOScheduler):
        """Schedule weekly milestone report for active exchange users"""
        try:
            # Schedule for next Monday at 9 AM UTC
            now = datetime.utcnow()
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:  # If today is Monday, schedule for next Monday
                days_until_monday = 7
            
            next_monday = now + timedelta(days=days_until_monday)
            run_time = next_monday.replace(hour=9, minute=0, second=0, microsecond=0)

            scheduler.add_job(
                ProactiveCommunicationScheduler._send_weekly_milestone_with_context,
                "date",
                run_date=run_time,
                args=[user_id],
                id=f"weekly_milestone_{user_id}",
                replace_existing=True,
            )

            logger.info(f"Scheduled weekly milestone report for user {user_id} at {run_time}")

        except Exception as e:
            logger.error(f"Error scheduling weekly milestone report: {e}")

    @staticmethod
    async def check_pending_trades_for_updates():
        """Check all pending trades for status updates"""
        try:
            session = SessionLocal()
            try:
                # Find all trades waiting for seller response
                pending_trades = (
                    session.query(Escrow)
                    .filter(
                        Escrow.status.in_(["payment_pending", "payment_confirmed", "awaiting_seller"]),
                        Escrow.created_at
                        >= datetime.utcnow() - timedelta(days=7),  # Only recent trades
                    )
                    .all()
                )

                for escrow in pending_trades:
                    # Check if seller has responded (this would be implemented based on your seller response logic)
                    # For now, this is a placeholder for the actual seller response detection
                    pass

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error checking pending trades: {e}")

    @staticmethod
    async def _send_15min_with_context(escrow_id: str, user_id: int):
        """Send 15-minute follow-up with proper context"""
        try:
            from main import get_application_instance
            from telegram.ext import ContextTypes
            
            # Get application context
            app = get_application_instance()
            if app and app.bot:
                # Create minimal context for job execution
                context = ContextTypes.DEFAULT_TYPE(application=app)
                await ProactiveCommunicationService.send_15_minute_followup(
                    escrow_id, user_id, context
                )
            else:
                logger.error("Application not available for 15-min follow-up")
        except Exception as e:
            logger.error(f"Error in 15-min follow-up job: {e}")

    @staticmethod
    async def _send_2hour_with_context(escrow_id: str, user_id: int):
        """Send 2-hour follow-up with proper context"""
        try:
            from main import get_application_instance
            from telegram.ext import ContextTypes
            
            # Get application context
            app = get_application_instance()
            if app and app.bot:
                # Create minimal context for job execution
                context = ContextTypes.DEFAULT_TYPE(application=app)
                await ProactiveCommunicationService.send_2_hour_followup(
                    escrow_id, user_id, context
                )
            else:
                logger.error("Application not available for 2-hour follow-up")
        except Exception as e:
            logger.error(f"Error in 2-hour follow-up job: {e}")

    @staticmethod
    async def _send_daily_with_context(escrow_id: str, user_id: int):
        """Send daily check-in with proper context"""
        try:
            from main import get_application_instance
            from telegram.ext import ContextTypes
            
            # Get application context
            app = get_application_instance()
            if app and app.bot:
                # Create minimal context for job execution
                context = ContextTypes.DEFAULT_TYPE(application=app)
                await ProactiveCommunicationService.send_daily_check_in(
                    escrow_id, user_id, context
                )
            else:
                logger.error("Application not available for daily check-in")
        except Exception as e:
            logger.error(f"Error in daily check-in job: {e}")

    @staticmethod
    async def _send_exchange_immediate_with_context(exchange_id: str, user_id: int):
        """Send immediate post-exchange follow-up with proper context"""
        try:
            from main import get_application_instance
            from telegram.ext import ContextTypes
            from services.post_exchange_engagement import PostExchangeEngagementService
            
            # Get application context
            app = get_application_instance()
            if app and app.bot:
                # Create minimal context for job execution
                context = ContextTypes.DEFAULT_TYPE(application=app)
                await PostExchangeEngagementService.send_immediate_completion_followup(
                    exchange_id, user_id, context
                )
            else:
                logger.error("Application not available for immediate exchange follow-up")
        except Exception as e:
            logger.error(f"Error in immediate exchange follow-up job: {e}")

    @staticmethod
    async def _send_exchange_achievement_with_context(exchange_id: str, user_id: int):
        """Send achievement post-exchange follow-up with proper context"""
        try:
            from main import get_application_instance
            from telegram.ext import ContextTypes
            from services.post_exchange_engagement import PostExchangeEngagementService
            
            # Get application context
            app = get_application_instance()
            if app and app.bot:
                # Create minimal context for job execution
                context = ContextTypes.DEFAULT_TYPE(application=app)
                await PostExchangeEngagementService.send_achievement_followup(
                    exchange_id, user_id, context
                )
            else:
                logger.error("Application not available for achievement exchange follow-up")
        except Exception as e:
            logger.error(f"Error in achievement exchange follow-up job: {e}")

    @staticmethod
    async def _send_exchange_educational_with_context(exchange_id: str, user_id: int):
        """Send educational post-exchange follow-up with proper context"""
        try:
            from main import get_application_instance
            from telegram.ext import ContextTypes
            from services.post_exchange_engagement import PostExchangeEngagementService
            
            # Get application context
            app = get_application_instance()
            if app and app.bot:
                # Create minimal context for job execution
                context = ContextTypes.DEFAULT_TYPE(application=app)
                await PostExchangeEngagementService.send_educational_followup(
                    exchange_id, user_id, context
                )
            else:
                logger.error("Application not available for educational exchange follow-up")
        except Exception as e:
            logger.error(f"Error in educational exchange follow-up job: {e}")

    @staticmethod
    async def _send_weekly_milestone_with_context(user_id: int):
        """Send weekly milestone report with proper context"""
        try:
            from main import get_application_instance
            from telegram.ext import ContextTypes
            from services.post_exchange_engagement import PostExchangeEngagementService
            
            # Get application context
            app = get_application_instance()
            if app and app.bot:
                # Create minimal context for job execution
                context = ContextTypes.DEFAULT_TYPE(application=app)
                await PostExchangeEngagementService.send_weekly_milestone_report(
                    user_id, context
                )
            else:
                logger.error("Application not available for weekly milestone report")
        except Exception as e:
            logger.error(f"Error in weekly milestone report job: {e}")
