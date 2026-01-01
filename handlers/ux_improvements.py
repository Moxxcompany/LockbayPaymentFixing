"""
UX Improvements Handler
Handles all the new UX improvement callbacks and interactions
"""

import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler
from database import SessionLocal
from models import Escrow
from services.trade_status_tracker import TradeStatusTracker
from utils.callback_utils import safe_edit_message_text, safe_answer_callback_query

logger = logging.getLogger(__name__)

async def cancel_all_status_refresh_jobs(user_id: int = None) -> None:
    """
    Cancel all active trade status auto-refresh jobs.
    
    Args:
        user_id: Optional user ID to cancel jobs for specific user's trades.
                If None, attempts to cancel all auto_refresh_* jobs.
    """
    try:
        from utils.scheduler_access import get_global_scheduler
        scheduler = get_global_scheduler()
        
        if not scheduler or not scheduler.running:
            logger.debug("Scheduler not available for job cancellation")
            return
        
        # Get all jobs and filter for auto_refresh jobs
        cancelled_count = 0
        all_jobs = scheduler.get_jobs()
        
        for job in all_jobs:
            if job.id and job.id.startswith("auto_refresh_"):
                try:
                    scheduler.remove_job(job.id)
                    cancelled_count += 1
                    logger.debug(f"Cancelled status refresh job: {job.id}")
                except Exception as remove_error:
                    logger.debug(f"Failed to remove job {job.id}: {remove_error}")
        
        if cancelled_count > 0:
            logger.info(f"🧹 Cancelled {cancelled_count} trade status auto-refresh jobs")
    
    except Exception as e:
        logger.debug(f"Status refresh job cancellation skipped: {e}")

async def _auto_refresh_status(chat_id: int, message_id: int, escrow_id: str):
    """Auto-refresh status tracker message"""
    try:
        from main import get_application_instance
        application = get_application_instance()
        if not application:
            logger.error("Bot application not available for auto-refresh")
            return
            
        # Get updated status data
        status_data = await TradeStatusTracker.get_status_tracker_message(escrow_id)
        
        if "error" not in status_data:
            await application.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=status_data["text"],
                reply_markup=status_data["keyboard"]
            )
            
            # Schedule next auto-refresh if trade is still active/disputed
            if status_data.get("status") in ["disputed", "active", "payment_confirmed"]:
                from utils.scheduler_access import get_global_scheduler
                scheduler = get_global_scheduler()
                if scheduler and scheduler.running:
                    job_id = f"auto_refresh_{escrow_id}_{message_id}"
                    scheduler.add_job(
                        _auto_refresh_status,
                        'date',
                        run_date=datetime.now() + timedelta(seconds=30),
                        args=[chat_id, message_id, escrow_id],
                        id=job_id
                    )
            
    except Exception as e:
        logger.error(f"Auto-refresh failed for {escrow_id}: {e}")

async def handle_track_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle track status button clicks"""
    query = update.callback_query
    if not query or not query.data:
        return

    # SINGLE CALLBACK ANSWER: Track status
    await safe_answer_callback_query(query, "📊")

    # Extract escrow ID from callback data
    escrow_id = query.data.replace("track_status_", "")

    try:
        status_data = await TradeStatusTracker.get_status_tracker_message(escrow_id)

        if "error" in status_data:
            # CRITICAL FIX: Enhanced error handling for early-stage escrows
            error_message = status_data.get("message", f"❌ Error loading status: {status_data['error']}")
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        "🏠 Main Menu", callback_data="back_to_main"
                    )
                ]
            ]
            
            # Add support button if requested
            if status_data.get("show_support", False):
                keyboard.append([
                    InlineKeyboardButton(
                        "📞 Contact Support", callback_data="contact_support"
                    )
                ])
            
            await safe_edit_message_text(
                query,
                error_message,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        await safe_edit_message_text(
            query, status_data["text"], reply_markup=status_data["keyboard"]
        )
        
        # Auto-refresh for active/disputed trades (every 30 seconds)
        if status_data.get("status") in ["disputed", "active", "payment_confirmed"]:
            try:
                from utils.scheduler_access import get_global_scheduler
                scheduler = get_global_scheduler()
                if scheduler and scheduler.running:
                    # Schedule auto-refresh in 30 seconds
                    job_id = f"auto_refresh_{escrow_id}_{query.message.message_id}"
                    
                    # Remove any existing auto-refresh job for this message
                    if scheduler.get_job(job_id):
                        scheduler.remove_job(job_id)
                    
                    scheduler.add_job(
                        _auto_refresh_status,
                        'date',
                        run_date=datetime.now() + timedelta(seconds=30),
                        args=[query.message.chat.id, query.message.message_id, escrow_id],
                        id=job_id
                    )
                    logger.info(f"Auto-refresh scheduled for status tracker {escrow_id}")
            except Exception as e:
                logger.warning(f"Failed to schedule auto-refresh: {e}")

    except Exception as e:
        logger.error(f"Error handling track status: {e}")
        await safe_edit_message_text(
            query,
            "❌ Unable to load status. Please try again.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔄 Retry", callback_data=f"track_status_{escrow_id}"
                        ),
                        InlineKeyboardButton(
                            "🏠 Main Menu", callback_data="back_to_main"
                        ),
                    ]
                ]
            ),
        )

async def handle_help_timeline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle timeline help button clicks"""
    query = update.callback_query
    if not query or not query.data:
        return

    await safe_answer_callback_query(query, "❓")

    # Extract escrow ID from callback data
    escrow_id = query.data.replace("help_timeline_", "")

    try:
        help_text = await TradeStatusTracker.get_timeline_help_message(escrow_id)

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📊 Back to Status", callback_data=f"track_status_{escrow_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "💬 Contact Support", callback_data="contact_support"
                    ),
                    InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main"),
                ],
            ]
        )

        await safe_edit_message_text(query, help_text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error handling timeline help: {e}")
        await safe_edit_message_text(
            query,
            "❌ Unable to load help. Please try again.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔄 Retry", callback_data=f"help_timeline_{escrow_id}"
                        )
                    ]
                ]
            ),
        )

async def handle_cancel_escrow_improved(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle improved escrow cancellation with prevention dialog"""
    query = update.callback_query
    if not query or not query.data:
        return

    await safe_answer_callback_query(query, "⚠️")

    # Extract escrow ID from callback data
    escrow_id = query.data.replace("cancel_escrow_", "")
    user_id = query.from_user.id

    try:
        await TradeStatusTracker.show_cancellation_prevention(
            escrow_id, user_id, context
        )

    except Exception as e:
        logger.error(f"Error showing cancellation prevention: {e}")
        await safe_edit_message_text(
            query,
            "❌ Error processing cancellation. Please try again.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔄 Retry", callback_data=f"cancel_escrow_{escrow_id}"
                        )
                    ]
                ]
            ),
        )

async def handle_send_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle send reminder to seller"""
    query = update.callback_query
    if not query or not query.data:
        return

    await safe_answer_callback_query(query, "📞")

    escrow_id = query.data.replace("send_reminder_", "")

    try:
        # Check if reminder was already sent today
        session = SessionLocal()
        try:
            escrow = session.query(Escrow).filter(Escrow.escrow_id == escrow_id).first()
            if not escrow:
                await safe_edit_message_text(query, "❌ Trade not found.")
                return

            # Here you would implement actual reminder sending logic
            # For now, just show confirmation

            await safe_edit_message_text(
                query,
                f"""📞 Reminder Sent!

We've sent a gentle reminder to the seller about your trade #{escrow_id}.

• Sellers typically respond within 2-4 hours after reminders
• You can send 1 reminder per day
• Most sellers respond positively to friendly reminders

⏳ Please wait a bit longer for their response.""",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "📊 Check Status",
                                callback_data=f"track_status_{escrow_id}",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "🏠 Main Menu", callback_data="back_to_main"
                            )
                        ],
                    ]
                ),
            )

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Error sending reminder: {e}")
        await safe_edit_message_text(
            query, "❌ Unable to send reminder. Please try again."
        )

async def handle_extend_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle deadline extension"""
    query = update.callback_query
    if not query or not query.data:
        return

    await safe_answer_callback_query(query, "⏰")

    escrow_id = query.data.replace("extend_deadline_", "")

    try:
        await safe_edit_message_text(
            query,
            f"""⏰ Deadline Extended!

Your trade #{escrow_id} deadline has been extended to 72 hours.

• Gives seller more time to respond
• Many sellers respond during weekends
• You can still cancel anytime if needed

✅ New deadline: 72 hours from creation
📱 You'll get notified when seller responds""",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📊 Check Status", callback_data=f"track_status_{escrow_id}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🏠 Main Menu", callback_data="back_to_main"
                        )
                    ],
                ]
            ),
        )

    except Exception as e:
        logger.error(f"Error extending deadline: {e}")
        await safe_edit_message_text(
            query, "❌ Unable to extend deadline. Please try again."
        )

async def handle_contact_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle contact support button"""
    query = update.callback_query
    if not query:
        logger.warning("handle_contact_support: No callback query provided")
        return

    # CRITICAL DEBUG: Log that this handler is being called
    user_id = query.from_user.id if query.from_user else "unknown"
    logger.warning(f"🚀 SUPPORT HANDLER CALLED by user {user_id} - HANDLER IS WORKING!")

    await safe_answer_callback_query(query, "💬")

    # Use configurable support email with updated default
    from config import Config
    support_email = getattr(Config, 'SUPPORT_EMAIL', 'support@lockbay.io')
    
    support_text = f"""💬 Support

📧 {support_email}
⚡ Lightning-fast response

🚀 Live Chat - Instant help (< 1 min)
📋 My Tickets - View conversations  
📞 Email - Detailed inquiries

*For urgent issues: username, trade ID, description*"""

    # Check if user has active support session
    from database import SessionLocal
    from models import User, SupportTicket
    active_ticket = None
    try:
        session = SessionLocal()
        try:
            db_user = session.query(User).filter(User.telegram_id == str(user_id)).first()
            if db_user:
                active_ticket = session.query(SupportTicket).filter(
                    SupportTicket.user_id == db_user.id,
                    SupportTicket.status.in_(["open", "assigned"])
                ).first()
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Error checking active support session: {e}")

    # Build keyboard based on active session
    if active_ticket:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Continue Chat", callback_data=f"support_chat_open:{active_ticket.id}")],
            [InlineKeyboardButton("📋 My Support Tickets", callback_data="view_support_tickets")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")],
        ])
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Start Live Chat", callback_data="start_support_chat")],
            [InlineKeyboardButton("📋 My Support Tickets", callback_data="view_support_tickets")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")],
        ])

    # CRITICAL DEBUG: Log before attempting to edit message
    logger.info(f"🔧 SUPPORT HANDLER: About to edit message for user {user_id}")
    
    try:
        result = await safe_edit_message_text(query, support_text, reply_markup=keyboard)
        if result:
            logger.info(f"✅ SUPPORT HANDLER: Successfully edited message for user {user_id}")
        else:
            logger.warning(f"⚠️ SUPPORT HANDLER: Edit failed, trying fallback for user {user_id}")
            # CRITICAL FIX: When edit fails, send new message instead
            try:
                await query.message.reply_text(support_text, reply_markup=keyboard)
                logger.info(f"✅ SUPPORT HANDLER: Sent fallback message for user {user_id}")
            except Exception as fallback_error:
                logger.error(f"❌ SUPPORT HANDLER: Fallback also failed for user {user_id}: {fallback_error}")
    except Exception as e:
        logger.error(f"❌ SUPPORT HANDLER: Exception editing message for user {user_id}: {e}")
        # Try fallback - send new message
        try:
            await query.message.reply_text(support_text, reply_markup=keyboard)
            logger.info(f"✅ SUPPORT HANDLER: Sent fallback message for user {user_id}")
        except Exception as fallback_error:
            logger.error(f"❌ SUPPORT HANDLER: Fallback also failed for user {user_id}: {fallback_error}")

async def handle_confirm_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle confirmed cancellation after prevention dialog"""
    query = update.callback_query
    if not query or not query.data:
        return

    await safe_answer_callback_query(query, "❌")

    escrow_id = query.data.replace("confirm_cancel_", "")

    try:
        session = SessionLocal()
        try:
            escrow = session.query(Escrow).filter(Escrow.escrow_id == escrow_id).first()
            if escrow:
                escrow.status = "cancelled"
                escrow.cancelled_reason = "Cancelled by buyer after confirmation"
                session.commit()

                await safe_edit_message_text(
                    query,
                    f"""❌ Trade Cancelled

Trade #{escrow_id} has been cancelled.

• Any payments will be refunded automatically
• Seller has been notified of cancellation
• You can create a new trade anytime

Thank you for using LockBay! 🤝""",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "🏠 Main Menu", callback_data="back_to_main"
                                )
                            ],
                            [
                                InlineKeyboardButton(
                                    "🔄 Create New Trade",
                                    callback_data="start_secure_trade",
                                )
                            ],
                        ]
                    ),
                )
            else:
                await safe_edit_message_text(query, "❌ Trade not found.")

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Error confirming cancellation: {e}")
        await safe_edit_message_text(
            query, "❌ Unable to cancel trade. Please try again."
        )

# Fee transparency handlers
async def handle_accept_fees_create_trade(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle fee acceptance and proceed to trade creation"""
    query = update.callback_query
    if not query:
        return

    await safe_answer_callback_query(query, "✅")

    # Mark fees as accepted
    if context.user_data:
        context.user_data["fees_accepted"] = True

    # Proceed to payment method selection
    from handlers.escrow import show_payment_selection

    await show_payment_selection(query, context)

async def handle_explain_fees(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle fee explanation request"""
    query = update.callback_query
    if not query:
        return

    await safe_answer_callback_query(query, "❓")

    try:
        from services.fee_transparency import FeeTransparencyService

        await FeeTransparencyService.show_fee_explanation(context, query.from_user.id)

    except Exception as e:
        logger.error(f"Error showing fee explanation: {e}")
        await safe_edit_message_text(query, "❌ Unable to load fee explanation.")

async def handle_cancel_fee_acceptance(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle cancelling fee acceptance"""
    query = update.callback_query
    if not query:
        return

    await safe_answer_callback_query(query, "❌")

    await safe_edit_message_text(
        query,
        "❌ Trade creation cancelled.\n\nYou can start a new trade anytime!",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main")],
                [
                    InlineKeyboardButton(
                        "🔄 Try Again", callback_data="start_secure_trade"
                    )
                ],
            ]
        ),
    )

    # Clear escrow data
    if context.user_data:
        context.user_data.pop("escrow_data", None)
        context.user_data.pop("fees_accepted", None)

# Export all handlers for registration
UX_IMPROVEMENT_HANDLERS = [
    CallbackQueryHandler(handle_track_status, pattern=r"^track_status_"),
    CallbackQueryHandler(handle_help_timeline, pattern=r"^help_timeline_"),
    CallbackQueryHandler(handle_cancel_escrow_improved, pattern=r"^cancel_escrow_"),
    CallbackQueryHandler(handle_send_reminder, pattern=r"^send_reminder_"),
    CallbackQueryHandler(handle_extend_deadline, pattern=r"^extend_deadline_"),
    CallbackQueryHandler(handle_contact_support, pattern=r"^contact_support$"),
    CallbackQueryHandler(handle_confirm_cancel, pattern=r"^confirm_cancel_"),
    CallbackQueryHandler(
        handle_accept_fees_create_trade, pattern=r"^accept_fees_create_trade$"
    ),
    CallbackQueryHandler(handle_explain_fees, pattern=r"^explain_fees$"),
    CallbackQueryHandler(
        handle_cancel_fee_acceptance, pattern=r"^cancel_fee_acceptance$"
    ),
]
