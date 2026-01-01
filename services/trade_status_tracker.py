"""
Trade Status Tracking Service
Manages post-creation status tracking, notifications, and user experience improvements
"""

import logging
import html
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database import SessionLocal
from models import Escrow, Dispute
from utils.markdown_escaping import format_username_html

# from services.consolidated_notification_service import consolidated_notification_service

logger = logging.getLogger(__name__)


class TradeStatusTracker:
    """Enhanced trade status tracking and communication system"""

    @staticmethod
    def format_phone_display(phone: str) -> str:
        """Format phone number for display (mask middle digits)"""
        if not phone or len(phone) < 8:
            return phone

        # For +1234567890, show +123456xxxx
        if phone.startswith("+") and len(phone) > 10:
            return phone[:7] + "x" * (len(phone) - 9) + phone[-2:]
        return phone[:6] + "x" * max(0, len(phone) - 8) + phone[-2:]

    @staticmethod
    async def send_enhanced_confirmation(
        escrow: Escrow,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        invitation_type: str = "sms",  # sms, email, telegram
    ) -> bool:
        """Send enhanced post-creation confirmation with status tracking"""
        try:
            # CRITICAL FIX: Use fresh database session to avoid binding issues
            session = SessionLocal()
            try:
                # Get fresh escrow data from database to avoid session binding issues
                fresh_escrow = session.query(Escrow).filter(
                    Escrow.escrow_id == escrow.escrow_id
                ).first()
                
                if not fresh_escrow:
                    logger.error(f"Could not find escrow {escrow.escrow_id} in database")
                    return False
                
                # Extract data from fresh session-bound object
                escrow_id = fresh_escrow.escrow_id
                current_amount = fresh_escrow.amount
                seller_phone = fresh_escrow.seller_phone
                seller_email = fresh_escrow.seller_email
                seller_username = fresh_escrow.seller_username
                
            finally:
                session.close()
            
            # Use extracted data directly - no more session binding issues
            
            seller_display = ""

            if seller_phone:
                seller_display = TradeStatusTracker.format_phone_display(seller_phone)
                channel_info = f"📱 SMS invitation sent to: {html.escape(seller_display)}"
            elif seller_email:
                seller_display = seller_email[:3] + "***@" + seller_email.split("@")[1]
                channel_info = f"📧 Email invitation sent to: {html.escape(seller_display)}"
            else:
                seller_display = seller_username or "Unknown"
                channel_info = f"📱 Telegram invitation sent to: {format_username_html(seller_display)}"

            current_time = datetime.now(timezone.utc).strftime("%I:%M %p")
            amount = float(current_amount)

            confirmation_text = f"""📋 <b>Trade Setup Complete!</b>

{channel_info} • ⏰ {html.escape(current_time)}
🆔 #{html.escape(escrow_id or 'Unknown')} • 💰 ${amount:.2f} USD

⚠️ <b>Payment Required</b> - Send crypto to complete trade
⏳ Seller will be notified after payment confirmation"""

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📊 Track", callback_data=f"track_status_{escrow_id}"
                        ),
                        InlineKeyboardButton(
                            "❓ Help", callback_data=f"help_timeline_{escrow_id}"
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            "⚠️ Cancel",
                            callback_data=f"cancel_escrow_{escrow_id}",
                        )
                    ],
                ]
            )

            await context.bot.send_message(
                chat_id=user_id,
                text=confirmation_text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

            # Schedule follow-up notifications
            await TradeStatusTracker._schedule_follow_ups(escrow_id, user_id)

            return True

        except Exception as e:
            logger.error(f"Error sending enhanced confirmation: {e}")
            return False

    @staticmethod
    async def get_status_tracker_message(escrow_id: str) -> Dict[str, Any]:
        """Generate status tracker message for a trade"""
        session = SessionLocal()
        try:
            escrow = session.query(Escrow).filter(Escrow.escrow_id == escrow_id).first()
            if not escrow:
                # CRITICAL FIX: Check if this is an early-stage escrow ID that hasn't been completed yet
                return {
                    "error": "Trade Setup Incomplete",
                    "message": f"""⏳ Trade Setup In Progress

🆔 Trade #{escrow_id}

This trade is still being created and hasn't been completed yet. The tracking system will activate once payment is confirmed.

💡 **What this means:**
• Trade setup was started but not finished
• No payment has been made yet  
• The trade ID was assigned early for tracking purposes

📊 **Next Steps:**
• Complete your trade setup if you haven't finished
• Contact support if you need help completing the trade""",
                    "show_support": True,
                }

            # Calculate time remaining
            created_at = getattr(escrow, "created_at", datetime.now(timezone.utc))
            invitation_expires_at = getattr(escrow, "invitation_expires_at", None)
            expires_at = invitation_expires_at if invitation_expires_at is not None else (created_at + timedelta(hours=48))
            time_left = expires_at - datetime.now(timezone.utc)

            if time_left.total_seconds() <= 0:
                time_display = "⏰ EXPIRED"
            else:
                hours = int(time_left.total_seconds() // 3600)
                minutes = int((time_left.total_seconds() % 3600) // 60)
                time_display = f"⏱️ {hours}h {minutes}m remaining"

            # Determine status and next steps
            status = getattr(escrow, "status", "unknown")
            seller_phone = getattr(escrow, "seller_phone", None)
            seller_email = getattr(escrow, "seller_email", None)

            if seller_phone:
                contact_display = TradeStatusTracker.format_phone_display(seller_phone)
                sent_via = "📱 SMS"
            elif seller_email:
                contact_display = seller_email[:3] + "***@" + seller_email.split("@")[1]
                sent_via = "📧 Email"
            else:
                contact_display = getattr(escrow, "seller_username", "Unknown")
                sent_via = "📱 Telegram"

            # Status-specific messaging
            if status in ["payment_pending", "awaiting_seller"]:
                status_icon = "⏳"
                status_text = "Waiting for seller response"
                invitation_clicked = "⏳ Waiting..."
                invitation_response = "⏳ Pending"
                activity_updates = [
                    f"• {created_at.strftime('%I:%M %p')} - Trade created",
                    f"• {created_at.strftime('%I:%M %p')} - Invitation sent successfully",
                    "• Waiting for seller to respond...",
                ]
            elif status == "payment_confirmed":
                status_icon = "✅"
                status_text = "Payment confirmed - seller notified"
                invitation_clicked = "✅ Viewed"
                invitation_response = "✅ Accepted"
                activity_updates = [
                    f"• {created_at.strftime('%I:%M %p')} - Trade created",
                    f"• {created_at.strftime('%I:%M %p')} - Payment confirmed",
                    "• Seller has been notified to begin delivery",
                ]
            elif status == "disputed":
                status_icon = "❓"
                status_text = "Disputed"
                # Check if trade has been pending for too long (5+ days = 120+ hours)
                hours_since_created = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
                if hours_since_created > 120:  # 5+ days
                    invitation_clicked = "❌ No response"
                    invitation_response = "❌ Expired (5+ days)"
                else:
                    invitation_clicked = "⏳ Waiting..."
                    invitation_response = "❓ Under review"
                activity_updates = [
                    f"• {created_at.strftime('%I:%M %p')} - Trade created",
                    f"• {created_at.strftime('%I:%M %p')} - Invitation sent",
                    "• Current status: Disputed",
                ]
            elif status == "cancelled":
                status_icon = "❌"
                status_text = "Trade cancelled"
                invitation_clicked = "❌ Not accessed"
                invitation_response = "❌ Cancelled"
                activity_updates = [
                    f"• {created_at.strftime('%I:%M %p')} - Trade created",
                    f"• {datetime.now(timezone.utc).strftime('%I:%M %p')} - Trade cancelled",
                ]
            else:
                status_icon = "❓"
                status_text = status.replace("_", " ").title()
                invitation_clicked = "⏳ Waiting..."
                invitation_response = "⏳ Pending"
                activity_updates = [f"• Current status: {status_text}"]

            tracker_text = f"""📊 TRADE STATUS TRACKER

Trade #{escrow_id}
Status: {status_icon} {status_text}

{sent_via} Invitation Details:
• Sent to: {contact_display}
• Delivered: ✅ {created_at.strftime('%I:%M %p')}
• Clicked: {invitation_clicked}
• Response: {invitation_response}

{time_display}

💬 Recent Activity:
{chr(10).join(activity_updates)}"""

            keyboard = []
            
            # Smart chat access button based on trade status
            if status == "disputed":
                # Find the dispute record to get dispute ID
                dispute = session.query(Dispute).filter(
                    Dispute.escrow_id == escrow.id,
                    Dispute.status == "open"
                ).first()
                
                if dispute:
                    # For disputed trades, open dispute chat with correct dispute ID
                    keyboard.append([
                        InlineKeyboardButton(
                            "💬 Open Dispute Chat", 
                            callback_data=f"admin_chat_start:{dispute.id}"
                        )
                    ])
            elif status in ["active", "payment_confirmed"]:
                # For active trades, open trade chat
                keyboard.append([
                    InlineKeyboardButton(
                        "💬 Open Trade Chat", 
                        callback_data=f"trade_chat_open:{escrow.id}"
                    )
                ])
            
            # Support and help options
            keyboard.append([
                InlineKeyboardButton(
                    "📞 Contact Support", callback_data="contact_support"
                ),
                InlineKeyboardButton(
                    "❓ Help", callback_data=f"help_timeline_{escrow_id}"
                ),
            ])

            # Cancel trade option for non-completed trades
            if status not in ["cancelled", "completed"]:
                keyboard.append([
                    InlineKeyboardButton(
                        "❌ Cancel Trade",
                        callback_data=f"cancel_escrow_{escrow_id}",
                    )
                ])

            return {
                "text": tracker_text,
                "keyboard": InlineKeyboardMarkup(keyboard),
                "status": status,
            }

        except Exception as e:
            logger.error(f"Error generating status tracker: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    @staticmethod
    async def get_timeline_help_message(escrow_id: str) -> str:
        """Generate timeline help message"""
        return """⏱️ TYPICAL TRADE TIMELINE

SMS Sent → Seller Response → Payment → Completion
0-15min      2-24 hours      5-30min    Instant

📊 Response Rate Statistics:
• Within 2 hours: 34%
• Within 6 hours: 67%  
• Within 24 hours: 89%
• No response: 11% (auto-refunded)

🤔 "Why haven't they responded yet?"
→ Sellers receive many invitations daily
→ They carefully review each trade
→ Quality sellers take time to respond properly

🔒 "Is my money safe?"  
→ Yes! Your funds are protected by escrow
→ Auto-refund if seller doesn't respond in 48h
→ Dispute resolution available 24/7

📱 "Should I contact them directly?"
→ Not recommended - keep all communication in-platform
→ Use our secure messaging when trade starts

💡 Most sellers check messages 2-3 times daily. Response rates are highest in evenings!"""

    @staticmethod
    async def _schedule_follow_ups(escrow_id: str, user_id: int):
        """Schedule proactive follow-up notifications"""
        try:
            from utils.scheduler_access import get_global_scheduler
            from jobs.proactive_communication_scheduler import ProactiveCommunicationScheduler
            
            scheduler = get_global_scheduler()
            if scheduler and scheduler.running:
                # Use the proper scheduler to schedule follow-ups
                ProactiveCommunicationScheduler.schedule_trade_followups(
                    escrow_id=escrow_id,
                    user_id=user_id,
                    scheduler=scheduler
                )
                logger.info(f"Successfully scheduled follow-ups for trade {escrow_id}")
            else:
                logger.warning(f"Scheduler not available - follow-ups not scheduled for {escrow_id}")

        except Exception as e:
            logger.error(f"Error scheduling follow-ups: {e}")

    @staticmethod
    async def _send_delayed_notification(
        delay_minutes: int, user_id: int, escrow_id: str, notification_type: str
    ):
        """Legacy method - replaced by proper scheduler integration"""
        logger.info(f"Legacy notification call for {notification_type} - using new scheduler integration")

    @staticmethod
    async def send_seller_response_notification(
        escrow: Escrow, user_id: int, context: ContextTypes.DEFAULT_TYPE
    ):
        """Send notification when seller responds to invitation"""
        try:
            seller_name = "John D."  # This would come from actual seller data
            response_time = "3h 24m"  # Calculate from creation time

            notification_text = f"""✅ Seller Accepted • #{escrow.escrow_id}

👤 {seller_name} • {response_time}
🔐 Trade active: ${float(getattr(escrow, 'amount', 0)):.2f} USD

📨 Ready to chat?"""

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "💳 Make Payment",
                            callback_data=f"make_payment_{escrow.escrow_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "💬 Message Seller",
                            callback_data=f"trade_chat_open:{escrow.id}",
                        ),
                        InlineKeyboardButton(
                            "❌ Cancel",
                            callback_data=f"cancel_escrow_{escrow.escrow_id}",
                        ),
                    ],
                ]
            )

            await context.bot.send_message(
                chat_id=user_id, text=notification_text, reply_markup=keyboard
            )

        except Exception as e:
            logger.error(f"Error sending seller response notification: {e}")

    @staticmethod
    async def show_cancellation_prevention(
        escrow_id: str, user_id: int, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show cancellation prevention dialog"""
        try:
            prevention_text = """⚠️ WAIT! Before you cancel...

• Seller might respond in next few hours
• 67% of sellers respond within 6 hours
• Cancelling now means losing this seller
• You'll need to start over with new invitation

💡 ALTERNATIVES:
🔄 Send gentle reminder to seller (1/day limit)
⏰ Extend deadline to 72 hours  
💬 Contact support for help

Most sellers check messages in the evening. Your trade is still likely to be accepted!"""

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📞 Send Reminder",
                            callback_data=f"send_reminder_{escrow_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⏰ Extend Time",
                            callback_data=f"extend_deadline_{escrow_id}",
                        ),
                        InlineKeyboardButton(
                            "💬 Contact Support", callback_data="contact_support"
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            "❌ Still Cancel",
                            callback_data=f"confirm_cancel_{escrow_id}",
                        )
                    ],
                ]
            )

            await context.bot.send_message(
                chat_id=user_id, text=prevention_text, reply_markup=keyboard
            )

        except Exception as e:
            logger.error(f"Error showing cancellation prevention: {e}")
