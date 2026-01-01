"""
Proactive Communication Service
Handles follow-up notifications and user engagement during wait periods
"""

import logging
from datetime import datetime
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from models import Escrow
from database import SessionLocal
from services.trade_status_tracker import TradeStatusTracker

logger = logging.getLogger(__name__)


class ProactiveCommunicationService:
    """Service for sending proactive communications to users"""

    @staticmethod
    async def send_15_minute_followup(
        escrow_id: str, user_id: int, context: ContextTypes.DEFAULT_TYPE
    ):
        """Send 15-minute follow-up notification"""
        try:
            session = SessionLocal()
            try:
                escrow = (
                    session.query(Escrow).filter(Escrow.escrow_id == escrow_id).first()
                )
                if not escrow or getattr(escrow, "status", "") == "cancelled":
                    return  # Trade was cancelled, skip notification

                seller_phone = getattr(escrow, "seller_phone", None)
                seller_email = getattr(escrow, "seller_email", None)

                if seller_phone:
                    contact_display = TradeStatusTracker.format_phone_display(
                        seller_phone
                    )
                    channel = "SMS"
                elif seller_email:
                    contact_display = (
                        seller_email[:3] + "***@" + seller_email.split("@")[1]
                    )
                    channel = "Email"
                else:
                    contact_display = getattr(escrow, "seller_username", "seller")
                    channel = "Telegram"

                followup_text = f"""📱 Update on your trade #{escrow_id}

{channel} successfully delivered to {contact_display} ✅
No response yet (this is normal!)

Most sellers respond within 2-6 hours.
We'll notify you the moment they respond.

📊 [Check Status](track_status_{escrow_id}) | ❓ [Why the wait?](help_timeline_{escrow_id})"""

                keyboard = [
                    [
                        InlineKeyboardButton(
                            "📊 Check Status", callback_data=f"track_status_{escrow_id}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "❓ Why the wait?",
                            callback_data=f"help_timeline_{escrow_id}",
                        )
                    ],
                ]

                await context.bot.send_message(
                    chat_id=user_id,
                    text=followup_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error sending 15-minute follow-up: {e}")

    @staticmethod
    async def send_2_hour_followup(
        escrow_id: str, user_id: int, context: ContextTypes.DEFAULT_TYPE
    ):
        """Send 2-hour follow-up notification"""
        try:
            session = SessionLocal()
            try:
                escrow = (
                    session.query(Escrow).filter(Escrow.escrow_id == escrow_id).first()
                )
                if not escrow or getattr(escrow, "status", "") == "cancelled":
                    return  # Trade was cancelled, skip notification

                followup_text = f"""⏰ Still waiting • Trade #{escrow_id}
89% respond in 24h • Secure ✅

📊 Options:"""

                keyboard = [
                    [
                        InlineKeyboardButton(
                            "📊 Check Status", callback_data=f"track_status_{escrow_id}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "📞 Send Reminder",
                            callback_data=f"send_reminder_{escrow_id}",
                        ),
                        InlineKeyboardButton(
                            "❓ FAQ", callback_data=f"help_timeline_{escrow_id}"
                        ),
                    ],
                ]

                await context.bot.send_message(
                    chat_id=user_id,
                    text=followup_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error sending 2-hour follow-up: {e}")

    @staticmethod
    async def send_seller_response_notification(
        escrow_id: str, user_id: int, context: ContextTypes.DEFAULT_TYPE
    ):
        """Send notification when seller responds"""
        try:
            session = SessionLocal()
            try:
                escrow = (
                    session.query(Escrow).filter(Escrow.escrow_id == escrow_id).first()
                )
                if not escrow:
                    return

                created_at = getattr(escrow, "created_at", datetime.utcnow())
                response_time = datetime.utcnow() - created_at

                hours = int(response_time.total_seconds() // 3600)
                minutes = int((response_time.total_seconds() % 3600) // 60)

                if hours > 0:
                    time_display = f"{hours}h {minutes}m"
                else:
                    time_display = f"{minutes}m"

                amount = float(getattr(escrow, "amount", 0))

                notification_text = f"""✅ Trade Started • #{escrow_id}

👤 Professional Trader • {time_display}
🔐 Funds secured: ${amount:.2f}

📨 Chat with seller?"""

                keyboard = [
                    [
                        InlineKeyboardButton(
                            "💳 Make Payment", callback_data=f"make_payment_{escrow_id}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "💬 Message Seller",
                            callback_data=f"trade_chat_open:{escrow.id}",
                        ),
                        InlineKeyboardButton(
                            "❌ Cancel", callback_data=f"cancel_escrow_{escrow_id}"
                        ),
                    ],
                ]

                await context.bot.send_message(
                    chat_id=user_id,
                    text=notification_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error sending seller response notification: {e}")

    @staticmethod
    async def send_daily_check_in(
        escrow_id: str, user_id: int, context: ContextTypes.DEFAULT_TYPE
    ):
        """Send daily check-in for long-running trades"""
        try:
            session = SessionLocal()
            try:
                escrow = (
                    session.query(Escrow).filter(Escrow.escrow_id == escrow_id).first()
                )
                if not escrow or getattr(escrow, "status", "") == "cancelled":
                    return

                created_at = getattr(escrow, "created_at", datetime.utcnow())
                days_passed = (datetime.utcnow() - created_at).days

                checkin_text = f"""📅 Day {days_passed} • Trade #{escrow_id}
⏰ {48 - (days_passed * 24)}h left • Secure ✅

💡 Options:"""

                keyboard = [
                    [
                        InlineKeyboardButton(
                            "📊 Check Status", callback_data=f"track_status_{escrow_id}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "📞 Send Reminder",
                            callback_data=f"send_reminder_{escrow_id}",
                        ),
                        InlineKeyboardButton(
                            "⏰ Extend Time",
                            callback_data=f"extend_deadline_{escrow_id}",
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            "💬 Contact Support", callback_data="contact_support"
                        )
                    ],
                ]

                await context.bot.send_message(
                    chat_id=user_id,
                    text=checkin_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error sending daily check-in: {e}")
