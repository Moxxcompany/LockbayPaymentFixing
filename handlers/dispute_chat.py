"""
Comprehensive Dispute Chat and Admin Messaging System
Restoration of the full-featured dispute management interface
"""

import logging
import html
from typing import Optional, Dict, Set, TYPE_CHECKING
from datetime import datetime, timedelta
from decimal import Decimal
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.error import TelegramError
from sqlalchemy.orm import sessionmaker
from sqlalchemy import desc, func, or_

from database import SessionLocal, engine, async_managed_session
from models import (
    Dispute, DisputeMessage, DisputeStatus, Escrow, EscrowMessage,
    User, EscrowStatus
)
from utils.dispute_prefetch import (
    prefetch_dispute_context,
    get_cached_dispute_data,
    cache_dispute_data,
    invalidate_dispute_cache
)
from utils.admin_security import is_admin_secure, is_admin_silent
from utils.helpers import get_user_display_name
from utils.exception_handler import ValidationError
from handlers.multi_dispute_manager import dispute_manager
from utils.comprehensive_audit_logger import (
    ComprehensiveAuditLogger, AuditEventType, AuditLevel, RelatedIDs, PayloadMetadata
)
from utils.handler_decorators import audit_handler, audit_dispute_handler
from utils.callback_utils import safe_answer_callback_query

# Initialize communication audit logger
communication_audit = ComprehensiveAuditLogger("communication")


async def safe_edit_message_text(query, text, parse_mode=None, reply_markup=None):
    """Safe message editing with error handling"""
    try:
        await query.edit_message_text(text=text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Failed to edit message: {e}")


from services.dispute_resolution import DisputeResolutionService

logger = logging.getLogger(__name__)

# Active chat sessions tracking - Using multi-dispute manager
active_dispute_chat: Dict[int, int] = {}  # Legacy support, will migrate to dispute_manager
active_escrow_messaging: Dict[int, int] = {}  # user_id -> escrow_id

DISPUTE_CHAT, ESCROW_MESSAGING = range(2)


def format_full_chat_history(messages, buyer_id: int, seller_id: int, for_telegram: bool = True) -> str:
    """
    Format all dispute messages in chronological order for admin viewing.
    
    Args:
        messages: List of DisputeMessage objects
        buyer_id: Database ID of the buyer
        seller_id: Database ID of the seller
        for_telegram: If True, format for Telegram. If False, format for email/other.
    
    Returns:
        Formatted string with all messages in chronological order
    """
    if not messages:
        return "📭 No messages yet."
    
    chat_lines = []
    for msg in messages:
        # Determine sender role - prioritize trade role over admin status
        if msg.sender_id == buyer_id:
            sender_emoji = "👤"
            sender_role = "Buyer"
        elif msg.sender_id == seller_id:
            sender_emoji = "🏪"
            sender_role = "Seller"
        elif is_admin_secure(msg.sender_id):
            # Only show as Admin if not a participant
            sender_emoji = "🛡️"
            sender_role = "Admin"
        else:
            sender_emoji = "👤"
            sender_role = "User"
        
        # Format timestamp
        timestamp = msg.created_at.strftime("%m/%d %H:%M")
        
        # Format message (escape for Telegram if needed)
        if for_telegram:
            message_text = html.escape(msg.message if msg.message else "")
        else:
            message_text = msg.message if msg.message else ""
        
        # Build line
        chat_lines.append(f"{timestamp} {sender_emoji} {sender_role}: {message_text}")
    
    return "\n".join(chat_lines)


@audit_dispute_handler("admin_disputes_dashboard")
async def show_admin_disputes_realtime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Enhanced admin dispute dashboard with real-time monitoring"""
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query, "⚖️")

    try:
        session = SessionLocal()
        try:
            # === REAL-TIME DISPUTE MONITORING ===
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Active disputes with full details
            active_disputes = session.query(Dispute).filter(
                Dispute.status.in_(["open", "under_review"])
            ).order_by(desc(Dispute.created_at)).all()
            
            # Enhanced metrics
            total_disputes = session.query(Dispute).count()
            resolved_disputes = session.query(Dispute).filter(
                Dispute.status == "resolved"
            ).count()
            disputes_today = session.query(Dispute).filter(
                Dispute.created_at >= today_start
            ).count()
            
            resolution_rate = (resolved_disputes / max(total_disputes, 1)) * 100
            
            message = f"""⚖️ Live Dispute Console

📊 Real-Time Status
• Active: {len(active_disputes)} • Total: {total_disputes:,}
• Resolution Rate: {resolution_rate:.1f}% • Today: {disputes_today}

🔥 Active Disputes"""

            if active_disputes:
                for i, dispute in enumerate(active_disputes[:5], 1):
                    escrow = dispute.escrow
                    initiator = session.query(User).filter(
                        User.id == dispute.initiator_id
                    ).first()
                    
                    age_days = (now - dispute.created_at).days
                    status_emoji = "🔴" if dispute.status == "open" else "🟠"
                    
                    # Recent activity check
                    recent_messages = session.query(DisputeMessage).filter(
                        DisputeMessage.dispute_id == dispute.id,
                        DisputeMessage.created_at >= now - timedelta(hours=24)
                    ).count()
                    
                    activity_indicator = f" ({recent_messages} msgs)" if recent_messages > 0 else ""
                    
                    message += f"""
{status_emoji} #{dispute.id} - {dispute.reason}
   💰 ${escrow.amount:.2f} • {initiator.first_name if initiator else 'Unknown'}
   📅 {age_days}d ago{activity_indicator}"""
            else:
                message += "\n✅ No active disputes - all resolved!"
            
            message += f"\n\n📱 Live Console • {now.strftime('%H:%M:%S UTC')}"
            
        finally:
            session.close()
        
        keyboard = [
            [
                InlineKeyboardButton("💬 Chat View", callback_data="admin_dispute_chat_live"),
                InlineKeyboardButton("⚡ Quick Actions", callback_data="admin_dispute_actions"),
            ],
            [
                InlineKeyboardButton("📊 Analytics", callback_data="admin_analytics"),
                InlineKeyboardButton("🏠 Admin", callback_data="admin_main"),
            ]
        ]
        
        if query:
            await safe_edit_message_text(
                query,
                message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        elif update.message:
            await update.message.reply_text(
                message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        
    except Exception as e:
        logger.error(f"Admin disputes realtime failed: {e}")
        if query:
            await safe_answer_callback_query(query, "❌ Error loading disputes. Returning to admin panel.", show_alert=True)
            # Graceful recovery - redirect to admin main
            from handlers.admin import show_admin_panel
            return await show_admin_panel(update, context)
        elif update.message:
            await update.message.reply_text("❌ Error loading disputes. Returning to admin panel.")
            from handlers.admin import show_admin_panel
            return await show_admin_panel(update, context)
        return ConversationHandler.END

    return ConversationHandler.END


@audit_dispute_handler("admin_dispute_chat_interface")
async def handle_admin_dispute_chat_live(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Enhanced admin chat interface for disputes"""
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query, "💬")

    try:
        session = SessionLocal()
        try:
            # Get active disputes for selection
            active_disputes = session.query(Dispute).filter(
                Dispute.status.in_(["open", "under_review"])
            ).order_by(desc(Dispute.created_at)).limit(10).all()
            
            if not active_disputes:
                message = """💬 Admin Dispute Chat

✅ No active disputes to manage!
All disputes have been resolved."""
                
                keyboard = [
                    [InlineKeyboardButton("🏠 Admin Panel", callback_data="admin_main")]
                ]
            else:
                message = """💬 Admin Dispute Chat Interface

Select dispute to access chat:"""
                
                keyboard = []
                for dispute in active_disputes:
                    escrow = dispute.escrow
                    button_text = f"#{dispute.id} - ${escrow.amount:.0f}"
                    callback_data = f"admin_chat_start:{dispute.id}"
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
                
                keyboard.append([
                    InlineKeyboardButton("⚖️ Disputes", callback_data="admin_disputes"),
                    InlineKeyboardButton("🏠 Admin", callback_data="admin_main")
                ])
            
        finally:
            session.close()
        
        if query:
            await safe_edit_message_text(
                query,
                message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        elif update.message:
            await update.message.reply_text(
                message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        
    except ConnectionError as e:
        logger.error(f"Database connection failed in admin dispute interface: {e}")
        if query:
            await safe_answer_callback_query(query, "❌ Database connection issue. Please try again.", show_alert=True)
            from handlers.admin import show_admin_panel
            return await show_admin_panel(update, context)
    except ValidationError as e:
        logger.error(f"Invalid data in admin dispute interface: {e}")
        if query:
            await safe_answer_callback_query(query, "❌ Invalid request. Please try again.", show_alert=True)
    except Exception as e:
        logger.error(f"Admin dispute chat interface failed: {e}")
        if query:
            await safe_answer_callback_query(query, "❌ Error loading chat interface. Returning to admin panel.", show_alert=True)
            from handlers.admin import show_admin_panel
            return await show_admin_panel(update, context)
        elif update.message:
            await update.message.reply_text("❌ Error loading chat interface. Returning to admin panel.")
            from handlers.admin import show_admin_panel
            return await show_admin_panel(update, context)
        return ConversationHandler.END

    return ConversationHandler.END


@audit_dispute_handler("admin_dispute_chat_start")
async def admin_chat_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start admin chat session for specific dispute"""
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if not query or not query.data:
        return ConversationHandler.END
    
    try:
        dispute_id = int(query.data.split(":")[1])
        await safe_answer_callback_query(query, "💬")
        
        # Set active chat session using multi-dispute manager
        dispute_manager.add_dispute_session(user.id, dispute_id)
        active_dispute_chat[user.id] = dispute_id  # Legacy support
        
        # OPTIMIZATION: Check cache first, then prefetch if needed (67 queries → 2 queries)
        cached = get_cached_dispute_data(context.user_data)
        
        if not cached:
            # Prefetch all dispute context in 2 batched queries
            async with async_managed_session() as session:
                prefetch_data = await prefetch_dispute_context(dispute_id, session)
                if prefetch_data:
                    cache_dispute_data(context.user_data, prefetch_data)
                    cached = prefetch_data.to_dict()
        
        if not cached:
            # Fallback to old method if prefetch failed
            logger.warning(f"⚠️ DISPUTE_PREFETCH_FALLBACK: Using legacy queries for dispute {dispute_id}")
            session = SessionLocal()
            try:
                dispute = session.query(Dispute).filter(Dispute.id == dispute_id).first()
                if not dispute:
                    await safe_answer_callback_query(query, "❌ Dispute not found", show_alert=True)
                    return ConversationHandler.END
                
                escrow = dispute.escrow
                buyer = session.query(User).filter(User.id == escrow.buyer_id).first()
                seller = session.query(User).filter(User.id == escrow.seller_id).first()
                
                # Get ALL messages in chronological order
                all_messages = session.query(DisputeMessage).filter(
                    DisputeMessage.dispute_id == dispute.id
                ).order_by(DisputeMessage.created_at).all()
                
                # Use plain text to avoid Markdown escaping issues
                reason_text = dispute.reason or 'No reason provided'
                buyer_name = buyer.first_name if buyer else 'Unknown'
                seller_name = seller.first_name if seller else 'Unknown'
                escrow_amount = float(escrow.amount)
                buyer_id = escrow.buyer_id
                seller_id = escrow.seller_id
                
            finally:
                session.close()
        else:
            # Use cached prefetch data for basic info (FAST: 0 additional queries for metadata)
            logger.info(f"✅ DISPUTE_CACHE_HIT: Using cached data for dispute {dispute_id} ({cached.get('prefetch_duration_ms', 0):.1f}ms)")
            reason_text = cached['reason'] or 'No reason provided'
            buyer_name = cached['buyer']['first_name'] if cached.get('buyer') else 'Unknown'
            seller_name = cached['seller']['first_name'] if cached.get('seller') else 'Unknown'
            escrow_amount = float(cached['escrow_amount'])
            buyer_id = cached['buyer']['id'] if cached.get('buyer') else 0
            seller_id = cached['seller']['id'] if cached.get('seller') else 0
            
            # CRITICAL FIX: Always fetch ALL messages from database for admin chat
            # Cache contains only recent 5 messages, but admin needs complete history
            session = SessionLocal()
            try:
                all_messages = session.query(DisputeMessage).filter(
                    DisputeMessage.dispute_id == dispute_id
                ).order_by(DisputeMessage.created_at).all()
            finally:
                session.close()
        
        # Build message display with FULL chat history
        # Format all messages in chronological order
        chat_history = format_full_chat_history(
            all_messages,
            buyer_id,
            seller_id,
            for_telegram=False  # Use plain text for admin view
        )
        
        message = f"""💬 Live Admin Chat: {dispute_id}

📋 Case Details:
• Escrow: ${escrow_amount:.2f} • Reason: {reason_text}
• Buyer: {buyer_name}
• Seller: {seller_name}

💬 Full Chat History ({len(all_messages)} messages):
{chat_history}

💬 Type your message or use quick actions below:"""
        
        # Telegram has 4096 character limit - truncate if needed
        if len(message) > 4000:
            # Keep header and truncate chat history
            header = f"""💬 Live Admin Chat: {dispute_id}

📋 Case Details:
• Escrow: ${escrow_amount:.2f} • Reason: {reason_text}
• Buyer: {buyer_name}
• Seller: {seller_name}

💬 Full Chat History ({len(all_messages)} messages):
"""
            footer = "\n\n💬 Type your message or use quick actions below:"
            max_chat_length = 4000 - len(header) - len(footer) - 50
            
            if len(chat_history) > max_chat_length:
                chat_history_truncated = chat_history[-max_chat_length:]
                message = header + "[...earlier messages truncated...]\n" + chat_history_truncated + footer
            else:
                message = header + chat_history + footer
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Release to Seller", callback_data=f"admin_resolve_seller:{dispute_id}"),
                InlineKeyboardButton("↩️ Refund to Buyer", callback_data=f"admin_resolve_buyer:{dispute_id}"),
            ],
            [
                InlineKeyboardButton("⚖️ Split Funds", callback_data=f"admin_split_funds:{dispute_id}"),
            ],
            [
                InlineKeyboardButton("📝 View Full Chat", callback_data=f"admin_full_chat:{dispute_id}"),
                InlineKeyboardButton("❌ Exit Chat", callback_data="admin_chat_exit"),
            ]
        ]
        
        await safe_edit_message_text(
            query,
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        
        return DISPUTE_CHAT
        
    except Exception as e:
        logger.error(f"Admin chat start failed: {e}")
        if query:
            await safe_answer_callback_query(query, f"❌ Chat start failed: {str(e)}", show_alert=True)
        return ConversationHandler.END


@audit_dispute_handler("user_dispute_chat_open")
async def show_dispute_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show dispute chat interface for users"""
    user = update.effective_user
    if not user:
        return ConversationHandler.END
    
    query = update.callback_query
    if not query or not query.data:
        return ConversationHandler.END
    
    try:
        dispute_id = int(query.data.split(":")[1])
        await safe_answer_callback_query(query, "💬")
        
        # OPTIMIZATION: Check cache first, then prefetch if needed (67 queries → 2 queries)
        cached = get_cached_dispute_data(context.user_data)
        
        if not cached:
            # Prefetch all dispute context in 2 batched queries
            async with async_managed_session() as session:
                prefetch_data = await prefetch_dispute_context(dispute_id, session)
                if prefetch_data:
                    cache_dispute_data(context.user_data, prefetch_data)
                    cached = prefetch_data.to_dict()
        
        if not cached:
            # Fallback to old method if prefetch failed
            logger.warning(f"⚠️ DISPUTE_PREFETCH_FALLBACK: Using legacy queries for dispute {dispute_id}")
            session = SessionLocal()
            try:
                dispute = session.query(Dispute).filter(Dispute.id == dispute_id).first()
                if not dispute:
                    await safe_answer_callback_query(query, "❌ Dispute not found", show_alert=True)
                    return ConversationHandler.END
                
                escrow = dispute.escrow
                
                # Verify user is involved in this dispute
                if not (user.id == escrow.buyer_id or user.id == escrow.seller_id):
                    await safe_answer_callback_query(query, "❌ Access denied - not your dispute", show_alert=True)
                    return ConversationHandler.END
                
                # Get user from DB to match telegram_id with db user_id
                db_user = session.query(User).filter(User.telegram_id == str(user.id)).first()
                if not db_user:
                    await safe_answer_callback_query(query, "❌ User not found", show_alert=True)
                    return ConversationHandler.END
                
                # Set active chat session
                dispute_manager.add_dispute_session(user.id, dispute_id)
                active_dispute_chat[user.id] = dispute_id
                
                # Get recent messages
                recent_messages = session.query(DisputeMessage).filter(
                    DisputeMessage.dispute_id == dispute.id
                ).order_by(desc(DisputeMessage.created_at)).limit(10).all()
                
                role = "buyer" if db_user.id == escrow.buyer_id else "seller"
                counterpart_id = escrow.seller_id if role == "buyer" else escrow.buyer_id
                counterpart = session.query(User).filter(User.id == counterpart_id).first()
                
                # Escape special characters for HTML
                import html
                reason_safe = html.escape(dispute.reason or 'No reason provided')
                counterpart_name = counterpart.first_name if counterpart else 'Other party'
                counterpart_name_safe = html.escape(counterpart_name)
                escrow_amount = float(escrow.amount)
                buyer_id = escrow.buyer_id
                seller_id = escrow.seller_id
                
            finally:
                session.close()
        else:
            # Use cached prefetch data (FAST: 0 additional queries)
            logger.info(f"✅ DISPUTE_CACHE_HIT: Using cached data for dispute {dispute_id} (user view)")
            
            # Get user from DB to verify access (need to map telegram_id to db user_id)
            session = SessionLocal()
            try:
                db_user = session.query(User).filter(User.telegram_id == str(user.id)).first()
                if not db_user:
                    await safe_answer_callback_query(query, "❌ User not found", show_alert=True)
                    return ConversationHandler.END
            finally:
                session.close()
            
            # Verify user is involved in this dispute
            buyer_id = cached['buyer']['user_id']
            seller_id = cached['seller']['user_id']
            
            if not (db_user.id == buyer_id or db_user.id == seller_id):
                await safe_answer_callback_query(query, "❌ Access denied - not your dispute", show_alert=True)
                return ConversationHandler.END
            
            # Set active chat session
            dispute_manager.add_dispute_session(user.id, dispute_id)
            active_dispute_chat[user.id] = dispute_id
            
            # Extract data from cache
            import html
            reason_safe = html.escape(cached['reason'] or 'No reason provided')
            escrow_amount = float(cached['escrow_amount'])
            
            role = "buyer" if db_user.id == buyer_id else "seller"
            counterpart_data = cached['seller'] if role == "buyer" else cached['buyer']
            counterpart_name = counterpart_data['first_name'] if counterpart_data else 'Other party'
            counterpart_name_safe = html.escape(counterpart_name)
            
            # Convert cached messages to displayable format
            recent_messages = []
            for msg_data in cached.get('recent_messages', [])[:10]:
                class MessageDisplay:
                    def __init__(self, data):
                        self.sender_id = data['sender_id']
                        self.message = data['message']
                        self.created_at = data['timestamp']
                recent_messages.append(MessageDisplay(msg_data))
        
        # Build message display (same for both cached and non-cached paths)
        message = f"""<b>💬 Dispute Chat: #{dispute_id}</b>

📋 Case: {reason_safe} (<b>${escrow_amount:.2f}</b>)
👥 With: {counterpart_name_safe}

<b>Recent Messages:</b>"""
        
        if recent_messages:
            # Telegram has 4096 char limit - reserve space for header and footer
            TELEGRAM_LIMIT = 4096
            RESERVED_SPACE = len(message) + 150  # Current message + footer buffer
            remaining_chars = TELEGRAM_LIMIT - RESERVED_SPACE
            
            messages_to_show = []
            total_chars_used = 0
            
            # Build messages from newest to oldest (last 5), tracking character count
            for msg in reversed(recent_messages[-5:]):
                # Get sender identity - prioritize trade role over admin status
                if msg.sender_id == buyer_id:
                    sender = "👤 Buyer"
                elif msg.sender_id == seller_id:
                    sender = "🏪 Seller"
                elif is_admin_secure(msg.sender_id):
                    # Only show as Admin if not a participant
                    sender = "🛡️ Admin (Support)"
                else:
                    sender = "👤 User"
                
                # Show full message text with HTML escaping
                import html
                msg_text = html.escape(msg.message if msg.message else "")
                msg_line = f"\n{sender}: {msg_text}"
                msg_line_length = len(msg_line)
                
                # Check if adding this message would exceed limit
                if total_chars_used + msg_line_length <= remaining_chars:
                    messages_to_show.insert(0, msg_line)  # Insert at start to maintain order
                    total_chars_used += msg_line_length
                else:
                    # Can't fit this message - add truncation notice only if it fits
                    if messages_to_show:  # Only if we're showing some messages
                        overflow_notice = "\n<i>[Earlier messages hidden]</i>"
                        if total_chars_used + len(overflow_notice) <= remaining_chars:
                            messages_to_show.insert(0, overflow_notice)
                    break
            
            # Add messages to main message
            message += ''.join(messages_to_show)
        else:
            message += "\n📝 No messages yet - start the conversation!"
        
        message += "\n\n💬 Type your message below:"
        
        keyboard = [
            [
                InlineKeyboardButton("📄 Full Chat", callback_data=f"dispute_full_chat:{dispute_id}"),
                InlineKeyboardButton("❌ Exit Chat", callback_data="exit_dispute_chat:main"),
            ]
        ]
        
        await safe_edit_message_text(
            query,
            message,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        
        return DISPUTE_CHAT
        
    except Exception as e:
        logger.error(f"Show dispute chat failed: {e}")
        if query:
            await safe_answer_callback_query(query, "❌ Error loading chat. Returning to main menu.", show_alert=True)
            # Graceful recovery - return to main menu for users
            from handlers.menu import show_main_menu
            return await show_main_menu(update, context)
        return ConversationHandler.END


@audit_dispute_handler("dispute_message_processing")
async def process_dispute_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process incoming dispute chat messages"""
    user = update.effective_user
    message = update.message
    
    if not user or not message or not message.text:
        return ConversationHandler.END
    
    # Auto-establish dispute chat session if not active (support multiple disputes)
    dispute_id = dispute_manager.get_current_dispute(user.id)
    if not dispute_id:
        # Legacy fallback
        dispute_id = active_dispute_chat.get(user.id)
    
    if not dispute_id:
        # Try to find user's most recent active dispute automatically
        session = SessionLocal()
        try:
            db_user = None  # Initialize to avoid unbound variable
            # For admins, get any active dispute - using silent check to avoid false security alerts
            if is_admin_silent(user.id):
                recent_dispute = session.query(Dispute).filter(
                    Dispute.status.in_(["open", "under_review"])
                ).order_by(desc(Dispute.created_at)).first()
            else:
                # For regular users, get their disputes
                db_user = session.query(User).filter(User.telegram_id == str(user.id)).first()
                if db_user:
                    logger.info(f"Looking for disputes for user {db_user.id} (telegram: {user.id})")
                    recent_dispute = session.query(Dispute).join(Escrow, Dispute.escrow_id == Escrow.id).filter(
                        or_(Escrow.buyer_id == db_user.id, Escrow.seller_id == db_user.id),
                        Dispute.status.in_(["open", "under_review"])
                    ).order_by(desc(Dispute.created_at)).first()
                    if recent_dispute:
                        logger.info(f"Found dispute {recent_dispute.id} for user {db_user.id}")
                    else:
                        logger.warning(f"No active disputes found for db_user {db_user.id}")
                else:
                    logger.error(f"User with telegram_id {user.id} not found in database")
                    recent_dispute = None
            
            if recent_dispute:
                # Auto-establish session using multi-dispute manager
                dispute_manager.add_dispute_session(user.id, recent_dispute.id)
                active_dispute_chat[user.id] = recent_dispute.id  # Legacy support
                dispute_id = recent_dispute.id
                logger.info(f"Auto-established dispute chat session for user {user.id} in dispute {dispute_id}")
            else:
                logger.warning(f"No active disputes found for user {user.id} (telegram_id)")
                # Try one more time - check for disputed escrows directly
                if db_user:
                    disputed_escrow = session.query(Escrow).filter(
                        or_(Escrow.buyer_id == db_user.id, Escrow.seller_id == db_user.id),
                        Escrow.status == EscrowStatus.DISPUTED.value
                    ).first()
                    if disputed_escrow:
                        # Create or find dispute for this escrow
                        dispute = session.query(Dispute).filter(
                            Dispute.escrow_id == disputed_escrow.id
                        ).first()
                        if dispute:
                            dispute_manager.add_dispute_session(user.id, dispute.id)
                            active_dispute_chat[user.id] = dispute.id  # Legacy support
                            dispute_id = dispute.id
                            logger.info(f"Found disputed escrow {disputed_escrow.id}, established dispute session {dispute_id}")
                        else:
                            await message.reply_text("❌ No active disputes found. Please contact support if you need help.")
                            return ConversationHandler.END
                    else:
                        await message.reply_text("❌ No active disputes found. Please contact support if you need help.")
                        return ConversationHandler.END
                else:
                    # ENHANCEMENT: Check for active escrows that can be disputed
                    active_escrow = session.query(Escrow).filter(
                        or_(Escrow.buyer_id == db_user.id, Escrow.seller_id == db_user.id),
                        Escrow.status == EscrowStatus.ACTIVE.value
                    ).first()
                    
                    if active_escrow:
                        # Offer to create a dispute for the active escrow
                        await message.reply_text(
                            f"🚨 Dispute Center\n\n"
                            f"You have an active escrow (#{active_escrow.escrow_id}) but no dispute has been filed yet.\n\n"
                            f"To start a dispute:\n"
                            f"1. Go to 📋 My Trades > Active Trades\n"
                            f"2. Select your escrow #{active_escrow.escrow_id}\n"
                            f"3. Click 🚨 Report Issue\n\n"
                            f"Or contact support directly using 💬 Support from the main menu.",
                            parse_mode="Markdown"
                        )
                        return ConversationHandler.END
                    else:
                        await message.reply_text("❌ No active disputes found. Please contact support if you need help.")
                        return ConversationHandler.END
                
        except Exception as e:
            logger.error(f"Failed to auto-establish dispute session for user {user.id}: {e}", exc_info=True)
            # Instead of failing, try to continue without session
            logger.info(f"Attempting to continue without session for user {user.id}")
            # Clear the cache and retry
            if user.id in active_dispute_chat:
                del active_dispute_chat[user.id]
            await message.reply_text("⚠️ Session issue detected. Please use the Reply button in the notification to continue the chat.")
            return ConversationHandler.END
        finally:
            session.close()
    
    try:
        session = SessionLocal()
        try:
            # Verify dispute exists and user has access
            dispute = session.query(Dispute).filter(Dispute.id == dispute_id).first()
            if not dispute:
                await message.reply_text("❌ Dispute not found.")
                del active_dispute_chat[user.id]
                return ConversationHandler.END
            
            escrow = dispute.escrow
            # Get the database user ID for proper access check
            db_user = session.query(User).filter(User.telegram_id == str(user.id)).first()
            if not db_user:
                await message.reply_text("❌ User not found in database.")
                del active_dispute_chat[user.id]
                return ConversationHandler.END
            
            # Check access using database user ID, not telegram ID - using silent check to avoid false security alerts
            if not is_admin_silent(user.id) and not (db_user.id == escrow.buyer_id or db_user.id == escrow.seller_id):
                await message.reply_text("❌ Access denied.")
                del active_dispute_chat[user.id]
                return ConversationHandler.END
            
            # Validate and sanitize message input
            from utils.enhanced_input_validation import SecurityInputValidator
            
            validation_result = SecurityInputValidator.validate_and_sanitize_input(
                message.text,
                "dispute_message",
                max_length=1000,
                required=True
            )
            
            if not validation_result["is_valid"]:
                await message.reply_text("❌ Invalid message content. Please check your input and try again.")
                return ConversationHandler.END
            
            sanitized_message = validation_result["sanitized_value"]
            
            # Check if sender is admin and handle accordingly - using silent check to avoid false security alerts
            sender_user_id = None
            if is_admin_silent(user.id):
                # For admin users, ensure they exist in users table
                admin_user = session.query(User).filter(User.telegram_id == str(user.id)).first()
                if not admin_user:
                    # Create admin user record if it doesn't exist
                    from utils.datetime_helpers import get_naive_utc_now
                    now = get_naive_utc_now()
                    admin_user = User(
                        telegram_id=str(user.id),
                        username=user.username or f"admin_{user.id}",
                        first_name=user.first_name or "Admin",
                        email=f"admin_{user.id}@internal.system",  # Required field
                        created_at=now,
                        updated_at=now
                    )
                    session.add(admin_user)
                    session.flush()  # Flush to get the ID
                    logger.info(f"Created admin user record for telegram_id: {user.id}")
                sender_user_id = admin_user.id
            else:
                # For regular users, get their database user ID
                regular_user = session.query(User).filter(User.telegram_id == str(user.id)).first()
                if not regular_user:
                    await message.reply_text("❌ User account not found. Please contact support.")
                    return ConversationHandler.END
                sender_user_id = regular_user.id
            
            # Save message to database using the database user ID
            dispute_message = DisputeMessage(
                dispute_id=dispute.id,
                sender_id=sender_user_id,  # Use database user ID, not Telegram ID
                message=sanitized_message,  # Use sanitized message
                created_at=datetime.utcnow()
            )
            session.add(dispute_message)
            session.commit()
            
            # CACHE INVALIDATION: New message added, invalidate cached dispute data
            invalidate_dispute_cache(context.user_data)
            logger.info(f"🗑️ DISPUTE_CACHE_INVALIDATED: Dispute {dispute.id} cache cleared after new message")
            
            # Log dispute message with detailed communication metadata
            message_metadata = PayloadMetadata(
                communication_type="dispute",
                message_thread_id=str(dispute.id),
                participant_count=3 if not is_admin_silent(user.id) else 2,  # buyer, seller, admin
                message_length=len(sanitized_message),
                is_admin_message=is_admin_silent(user.id),
                has_attachments=bool(message.photo or message.document),
                message_sequence_number=1  # Will be updated with actual sequence
            )
            
            related_ids = RelatedIDs(
                dispute_id=str(dispute.id),
                escrow_id=str(escrow.escrow_id),
                message_id=str(dispute_message.id),
                conversation_id=f"dispute_{dispute.id}",
                counterpart_user_id=str(escrow.seller_id if sender_user_id == escrow.buyer_id else escrow.buyer_id)
            )
            
            communication_audit.audit(
                event_type=AuditEventType.COMMUNICATION,
                action="dispute_message_sent",
                result="success",
                user_id=user.id,
                is_admin=is_admin_silent(user.id),
                related_ids=related_ids,
                payload_metadata=message_metadata
            )
            
            # Send confirmation using sanitized message
            # Prioritize trade role over admin status - if they're buyer/seller in this trade, show that role
            if sender_user_id == escrow.buyer_id:
                sender_role = "Buyer"
            elif sender_user_id == escrow.seller_id:
                sender_role = "Seller"
            else:
                # Only show as "Admin" if they're not a buyer or seller in this trade
                sender_role = "Admin"
            
            recipient_role = "Seller" if sender_role == "Buyer" else ("Buyer" if sender_role == "Seller" else "All Parties")
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            await message.reply_text(
                f"✅ Message sent successfully!\n\n"
                f"📋 Dispute: #{dispute.id} • Trade: #{escrow.escrow_id[:12]}\n"
                f"👤 From: {sender_role} → {recipient_role}\n"
                f"💬 Message: {sanitized_message[:50]}{'...' if len(sanitized_message) > 50 else ''}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💬 Continue Chat", callback_data=f"view_dispute:{dispute.id}")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                ]),
                parse_mode="Markdown"
            )
            
            # Deliver real messages to other parties using trade chat system
            logger.info(f"Dispute message from user {user.id} in dispute #{dispute.id}: {sanitized_message[:50]}...")
            
            try:
                # Get all parties involved in the dispute
                participants = []
                if escrow.buyer_id and escrow.buyer_id != sender_user_id:
                    buyer = session.query(User).filter(User.id == escrow.buyer_id).first()
                    if buyer:
                        participants.append(("Buyer", buyer))
                        
                if escrow.seller_id and escrow.seller_id != sender_user_id:
                    seller = session.query(User).filter(User.id == escrow.seller_id).first()
                    if seller:
                        participants.append(("Seller", seller))
                
                # Always notify admins about dispute messages (excluding sender if they're an admin)
                # === FIX 1: ADMIN TELEGRAM NOTIFICATIONS WITH DETAILED LOGGING ===
                logger.info(f"🔔 ADMIN_NOTIFICATION_START: Entering admin notification block for dispute #{dispute.id}")
                telegram_notification_success = False
                telegram_notification_count = 0
                
                try:
                    from utils.admin_security import AdminSecurityManager
                    admin_manager = AdminSecurityManager()
                    admin_ids = list(admin_manager.get_admin_ids())
                    
                    # FIX: Add logging after retrieving admin IDs
                    logger.info(f"📋 ADMIN_IDS_RETRIEVED: Retrieved {len(admin_ids)} admin IDs for dispute notification")
                    
                except Exception as admin_e:
                    logger.error(f"❌ ADMIN_IDS_FETCH_FAILED: Failed to get admin IDs for dispute notification: {admin_e}", exc_info=True)
                    admin_ids = []
                
                if admin_ids:
                    try:
                        from main import get_application_instance
                        application = get_application_instance()
                        
                        if application and application.bot:
                            # Get ALL messages in chronological order for complete context
                            all_messages = session.query(DisputeMessage).filter(
                                DisputeMessage.dispute_id == dispute.id
                            ).order_by(DisputeMessage.created_at).all()
                            
                            # Format full chat history
                            chat_history = format_full_chat_history(
                                all_messages,
                                escrow.buyer_id,
                                escrow.seller_id,
                                for_telegram=True
                            )
                            
                            # Build admin notification with full context
                            admin_text = f"⚖️ New Dispute Message\n\n"
                            admin_text += f"📋 Dispute: #{dispute.id}\n"
                            admin_text += f"💰 Trade: #{escrow.escrow_id[:12]} (${float(escrow.amount):.2f})\n"
                            admin_text += f"👤 Latest From: {sender_role}\n\n"
                            admin_text += f"💬 Full Chat History ({len(all_messages)} messages):\n"
                            admin_text += f"{chat_history}"
                            
                            # Notify all admins except the sender
                            for admin_id in admin_ids:
                                try:
                                    chat_id = int(admin_id.strip() if isinstance(admin_id, str) else admin_id)
                                    
                                    # Skip notifying the sender if they're also an admin
                                    if chat_id == user.id:
                                        logger.info(f"⏭️ ADMIN_SKIP_SENDER: Skipping notification to sender admin {chat_id}")
                                        continue
                                    
                                    await application.bot.send_message(
                                        chat_id=chat_id,
                                        text=admin_text,
                                        reply_markup=InlineKeyboardMarkup([
                                            [InlineKeyboardButton("💬 Open Dispute", callback_data=f"view_dispute:{dispute.id}")],
                                            [InlineKeyboardButton("📋 Trade Details", callback_data=f"track_status_{escrow.escrow_id}")]
                                        ]),
                                        parse_mode="Markdown"
                                    )
                                    # FIX: Log successful send per admin
                                    logger.info(f"✅ ADMIN_TELEGRAM_SUCCESS: Telegram dispute notification sent to admin {admin_id}")
                                    telegram_notification_success = True
                                    telegram_notification_count += 1
                                except Exception as admin_notify_error:
                                    # FIX: Log failure per admin with full details
                                    logger.error(f"❌ ADMIN_TELEGRAM_FAILED: Failed to notify admin {admin_id}: {admin_notify_error}", exc_info=True)
                            
                            # FIX: Log completion summary
                            logger.info(f"📊 ADMIN_TELEGRAM_COMPLETE: Sent {telegram_notification_count}/{len(admin_ids)} Telegram notifications successfully")
                        else:
                            logger.error(f"❌ TELEGRAM_BOT_UNAVAILABLE: Application or bot instance not available for admin notifications")
                    except Exception as e:
                        logger.error(f"❌ ADMIN_TELEGRAM_CRITICAL_ERROR: Failed to notify admins via Telegram: {e}", exc_info=True)
                    
                    # === FIX 2 & 3: OPTIMIZED BACKGROUND EMAIL QUEUE FOR ADMIN ===
                    logger.info(f"📧 ADMIN_EMAIL_START: Starting admin email notification for dispute #{dispute.id}")
                    email_queue_success = False
                    
                    try:
                        from services.background_email_queue import background_email_queue
                        from config import Config
                        from services.admin_email_actions import AdminEmailActionService
                        
                        if Config.ADMIN_EMAIL_ALERTS and Config.ADMIN_ALERT_EMAIL:
                            sender_user = session.query(User).filter(User.id == sender_user_id).first()
                            sender_info = f"@{sender_user.username}" if sender_user and sender_user.username else sender_role
                            
                            # === FIX 3: OPTIMIZED - Only use current message, not full history ===
                            # Generate action tokens (preserve security features)
                            release_token = AdminEmailActionService.generate_dispute_token(
                                dispute_id=dispute.id,
                                action="RELEASE_TO_SELLER",
                                admin_email=Config.ADMIN_ALERT_EMAIL
                            )
                            refund_token = AdminEmailActionService.generate_dispute_token(
                                dispute_id=dispute.id,
                                action="REFUND_TO_BUYER",
                                admin_email=Config.ADMIN_ALERT_EMAIL
                            )
                            split_token = AdminEmailActionService.generate_dispute_token(
                                dispute_id=dispute.id,
                                action="SPLIT_FUNDS",
                                admin_email=Config.ADMIN_ALERT_EMAIL
                            )
                            custom_split_token = AdminEmailActionService.generate_dispute_token(
                                dispute_id=dispute.id,
                                action="CUSTOM_SPLIT",
                                admin_email=Config.ADMIN_ALERT_EMAIL
                            )
                            
                            # Build action button URLs
                            base_url = Config.ADMIN_ACTION_BASE_URL
                            action_urls = {
                                'release_url': f"{base_url}/admin/dispute/{dispute.id}/resolve?token={release_token}&action=RELEASE_TO_SELLER",
                                'refund_url': f"{base_url}/admin/dispute/{dispute.id}/resolve?token={refund_token}&action=REFUND_TO_BUYER",
                                'split_url': f"{base_url}/admin/dispute/{dispute.id}/resolve?token={split_token}&action=SPLIT_FUNDS",
                                'custom_split_url': f"{base_url}/admin/resolve-dispute/split/{dispute.id}?token={custom_split_token}"
                            }
                            
                            # Build admin panel URL for full history
                            admin_panel_url = f"{base_url}/admin/disputes/{dispute.id}"
                            
                            # === FIX 2: Use background email queue instead of synchronous sending ===
                            queue_result = await background_email_queue.queue_dispute_notification_email(
                                recipient=Config.ADMIN_ALERT_EMAIL,
                                dispute_id=dispute.id,
                                escrow_id=escrow.escrow_id,
                                escrow_amount=float(escrow.amount),
                                sender_info=sender_info,
                                sender_role=sender_role,
                                current_message=sanitized_message,
                                dispute_status=dispute.status,
                                action_urls=action_urls,
                                admin_panel_url=admin_panel_url,
                                user_id=None  # Admin notification, no specific user
                            )
                            
                            if queue_result.get('success'):
                                email_queue_success = True
                                logger.info(f"✅ ADMIN_EMAIL_QUEUED: Admin email queued successfully - Job ID: {queue_result.get('job_id')}")
                            else:
                                logger.error(f"❌ ADMIN_EMAIL_QUEUE_FAILED: Failed to queue admin email: {queue_result.get('error')}")
                        else:
                            logger.info(f"ℹ️ ADMIN_EMAIL_DISABLED: Admin email alerts disabled in configuration")
                            
                    except Exception as email_error:
                        logger.error(f"❌ ADMIN_EMAIL_CRITICAL_ERROR: Failed to queue admin email notification: {email_error}", exc_info=True)
                    
                    # FIX 4: Log completion of admin notification
                    logger.info(f"📊 ADMIN_NOTIFICATION_COMPLETE: Telegram={telegram_notification_success}, Email={email_queue_success}")
                
                # Send email notification to buyer/seller with full message history (runs for ALL senders including admin)
                try:
                    from services.email import email_service
                    from config import Config
                    
                    # Fetch buyer and seller user objects
                    buyer = session.query(User).filter(User.id == escrow.buyer_id).first()
                    seller = session.query(User).filter(User.id == escrow.seller_id).first()
                    
                    # Determine recipients based on sender role
                    recipients = []
                    if sender_role == "Buyer":
                        # Buyer sent message -> notify seller
                        if seller and seller.email:
                            recipients.append(("Seller", seller))
                    elif sender_role == "Seller":
                        # Seller sent message -> notify buyer
                        if buyer and buyer.email:
                            recipients.append(("Buyer", buyer))
                    elif sender_role == "Admin":
                        # Admin sent message -> notify both buyer and seller
                        if buyer and buyer.email:
                            recipients.append(("Buyer", buyer))
                        if seller and seller.email:
                            recipients.append(("Seller", seller))
                    
                    # Only proceed if there are recipients with email addresses
                    if recipients:
                        # Fetch ALL dispute messages for full history
                        all_messages_bs = session.query(DisputeMessage).filter(
                            DisputeMessage.dispute_id == dispute.id
                        ).order_by(DisputeMessage.created_at.asc()).all()
                        
                        # Build message history HTML (same logic as admin email)
                        message_history_html_bs = ""
                        for msg in all_messages_bs:
                            msg_user = session.query(User).filter(User.id == msg.sender_id).first()
                            msg_role = "Buyer" if msg.sender_id == escrow.buyer_id else "Seller" if msg.sender_id == escrow.seller_id else "Admin"
                            msg_sender_info = f"@{msg_user.username}" if msg_user and msg_user.username else msg_role
                            msg_time = msg.created_at.strftime('%b %d, %I:%M %p')
                            
                            # SECURITY: Escape all user-generated content to prevent HTML injection
                            escaped_sender_info_bs = html.escape(msg_sender_info)
                            escaped_message_bs = html.escape(msg.message)
                            
                            message_history_html_bs += f"""
                            <div style="margin-bottom: 15px; padding: 10px; background-color: {'#e3f2fd' if msg_role == 'Buyer' else '#fff3e0' if msg_role == 'Seller' else '#f3e5f5'}; border-radius: 5px;">
                                <div style="font-weight: bold; color: #333; margin-bottom: 5px;">
                                    {escaped_sender_info_bs} ({msg_role}) - {msg_time}
                                </div>
                                <div style="color: #555; white-space: pre-wrap; font-family: monospace;">
                                    {escaped_message_bs}
                                </div>
                            </div>
                            """
                        
                        # Send email to each recipient
                        for recipient_role, recipient_user in recipients:
                            try:
                                # Build "Reply via Bot" button URL
                                bot_url = f"https://t.me/{Config.BOT_USERNAME}?start=dispute_{dispute.id}"
                                
                                # Create email content for buyer/seller (no action buttons)
                                email_content = f"""
                                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107;">
                                    <h3 style="color: #856404; margin-top: 0;">💬 New Dispute Message</h3>
                                    <p><strong>Dispute ID:</strong> #{dispute.id}</p>
                                    <p><strong>Trade ID:</strong> #{escrow.escrow_id}</p>
                                    <p><strong>Amount:</strong> ${escrow.amount:.2f} USD</p>
                                    <p><strong>From:</strong> {sender_role}</p>
                                    <p><strong>Status:</strong> {dispute.status}</p>
                                </div>
                                
                                <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
                                    <h4 style="margin-top: 0;">💬 Message History:</h4>
                                    {message_history_html_bs}
                                </div>
                                
                                <div style="margin-top: 20px; padding: 20px; background-color: #e7f3ff; border-radius: 5px; text-align: center;">
                                    <p style="margin-top: 0;"><strong>💬 Reply to this dispute:</strong></p>
                                    <div style="margin-top: 15px;">
                                        <a href="{bot_url}" style="display: inline-block; padding: 12px 24px; background-color: #0088cc; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">🤖 Open Dispute Chat</a>
                                    </div>
                                </div>
                                """
                                
                                # Create full HTML email template
                                html_content = f"""
                                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                                    <div style="background: #ffc107; color: #333; padding: 20px; text-align: center; border-radius: 10px 10px 0 0;">
                                        <h1>💬 Dispute Message</h1>
                                        <p style="margin: 0; opacity: 0.9;">{Config.PLATFORM_NAME} Notification</p>
                                    </div>
                                    <div style="background: #f8f9fa; padding: 25px; border-radius: 0 0 10px 10px; border: 1px solid #dee2e6;">
                                        {email_content}
                                    </div>
                                    <div style="text-align: center; margin-top: 20px; color: #6c757d; font-size: 12px;">
                                        <p>This is an automated notification from {Config.PLATFORM_NAME}</p>
                                        <p>{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                                    </div>
                                </div>
                                """
                                
                                success = email_service.send_email(
                                    to_email=recipient_user.email,
                                    subject=f"💬 New Dispute Message: #{dispute.id} | ${escrow.amount:.2f}",
                                    html_content=html_content
                                )
                                
                                if success:
                                    logger.info(f"📧 Email dispute notification sent to {recipient_role} ({recipient_user.email})")
                                else:
                                    logger.error(f"Failed to send email dispute notification to {recipient_role} ({recipient_user.email})")
                            except Exception as recipient_email_error:
                                logger.error(f"❌ Failed to send email to {recipient_role}: {recipient_email_error}")
                except Exception as buyer_seller_email_error:
                    logger.error(f"❌ Failed to send buyer/seller email notifications: {buyer_seller_email_error}")
                
                # Deliver actual messages to all participants using trade chat interface
                for participant_role, participant_user in participants:
                    try:
                        if participant_user.telegram_id:
                            # Get bot instance from the application
                            from main import get_application_instance
                            application = get_application_instance()
                            
                            if application and application.bot:
                                # Create message with trade chat integration
                                message_header = f"💬 New message in dispute #{dispute.id}\n"
                                message_body = f"{sender_role}: {sanitized_message}\n\n"
                                message_footer = f"💰 Trade: ${escrow.amount:.2f} USD"
                                
                                full_message = f"{message_header}{message_body}{message_footer}"
                                
                                # Send message with direct access to dispute chat
                                keyboard = InlineKeyboardMarkup([
                                    [InlineKeyboardButton("💬 Open Chat", callback_data=f"view_dispute:{dispute.id}")],
                                    [InlineKeyboardButton("📋 Trade Details", callback_data=f"track_status_{escrow.escrow_id}")]
                                ])
                                
                                await application.bot.send_message(
                                    chat_id=participant_user.telegram_id,
                                    text=full_message,
                                    reply_markup=keyboard,
                                    parse_mode="Markdown"
                                )
                                logger.info(f"Trade chat message delivered to {participant_role} (user {participant_user.telegram_id})")
                            else:
                                logger.error("Bot application instance not available for notifications")
                            
                    except Exception as notify_error:
                        logger.error(f"Failed to notify {participant_role}: {notify_error}")
                        
            except Exception as notification_error:
                logger.error(f"Trade chat message delivery failed: {notification_error}")
            
        finally:
            session.close()
            
        return DISPUTE_CHAT
        
    except Exception as e:
        logger.error(f"Process dispute message failed: {e}")
        await message.reply_text("❌ Failed to send message. You can try again or return to main menu.")
        # Don't terminate - let user try again
        return DISPUTE_CHAT


async def handle_escrow_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle escrow messaging system"""
    user = update.effective_user
    if not user:
        return ConversationHandler.END
    
    query = update.callback_query
    if not query or not query.data:
        return ConversationHandler.END
    
    try:
        escrow_id = int(query.data.split(":")[1])
        await safe_answer_callback_query(query, "💬")
        
        session = SessionLocal()
        try:
            escrow = session.query(Escrow).filter(Escrow.id == escrow_id).first()
            if not escrow:
                await safe_answer_callback_query(query, "❌ Escrow not found", show_alert=True)
                return ConversationHandler.END
            
            # Verify user is involved in this escrow
            if not (user.id == escrow.buyer_id or user.id == escrow.seller_id):
                await safe_answer_callback_query(query, "❌ Access denied", show_alert=True)
                return ConversationHandler.END
            
            # Set active messaging session
            active_escrow_messaging[user.id] = escrow_id
            
            # Get recent messages
            recent_messages = session.query(EscrowMessage).filter(
                EscrowMessage.escrow_id == escrow.id
            ).order_by(desc(EscrowMessage.created_at)).limit(10).all()
            
            role = "buyer" if user.id == escrow.buyer_id else "seller"
            counterpart_id = escrow.seller_id if role == "buyer" else escrow.buyer_id
            counterpart = session.query(User).filter(User.id == counterpart_id).first()
            
            message = f"""💬 Escrow Chat: #{escrow.escrow_id}

📋 Trade: ${escrow.amount:.2f}
👥 With: {counterpart.first_name if counterpart else 'Other party'}
📊 Status: {escrow.status.value.upper()}

🕒 Recent Messages:"""
            
            if recent_messages:
                for msg in reversed(recent_messages[-5:]):
                    is_mine = msg.sender_id == user.id
                    sender_name = "You" if is_mine else (counterpart.first_name if counterpart else "Other")
                    timestamp = msg.created_at.strftime("%m/%d %H:%M")
                    
                    prefix = "→" if is_mine else "←"
                    # Plain text - no escaping needed
                    msg_preview = msg.message[:60] + "..." if len(msg.message) > 60 else msg.message
                    message += f"\n{prefix} {timestamp} {sender_name}: {msg_preview}"
            else:
                message += "\n📝 No messages yet - start the conversation!"
            
            message += "\n\n💬 Type your message below:"
            
        finally:
            session.close()
        
        keyboard = [
            [
                InlineKeyboardButton("📋 Trade Details", callback_data=f"escrow_details:{escrow_id}"),
                InlineKeyboardButton("❌ Exit Chat", callback_data="back_to_main"),
            ]
        ]
        
        await safe_edit_message_text(
            query,
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        
        return ESCROW_MESSAGING
        
    except Exception as e:
        logger.error(f"Handle escrow message failed: {e}")
        if query:
            await safe_answer_callback_query(query, "❌ Error loading messages. Returning to main menu.", show_alert=True)
            # Graceful recovery for escrow messaging
            from handlers.menu import show_main_menu
            return await show_main_menu(update, context)
        return ConversationHandler.END


async def exit_dispute_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Exit dispute chat and return to main menu"""
    user = update.effective_user
    if not user:
        return ConversationHandler.END
    
    # Clear active chat sessions
    dispute_manager.clear_user_sessions(user.id)
    if user.id in active_dispute_chat:
        del active_dispute_chat[user.id]
    if user.id in active_escrow_messaging:
        del active_escrow_messaging[user.id]
    
    query = update.callback_query
    if query:
        await safe_answer_callback_query(query, "❌")
        
        # Return to main menu or admin panel
        if is_admin_secure(user.id):
            from handlers.admin import admin_command
            return await admin_command(update, context)
        else:
            # Return to main menu
            await query.edit_message_text(
                "🏠 Returning to main menu...",
                reply_markup=None
            )
            return ConversationHandler.END
    
    return ConversationHandler.END


# ===== ADMIN DISPUTE RESOLUTION HANDLERS =====

async def handle_admin_resolve_buyer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle admin_resolve_buyer callback - refund to buyer"""
    logger.info(f"🔥 handle_admin_resolve_buyer called by user {update.effective_user.id if update.effective_user else 'None'}")
    
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if not query or not query.data:
        return ConversationHandler.END
    
    session = SessionLocal()
    try:
        dispute_id = query.data.split(":")[-1]
        await safe_answer_callback_query(query, "💰 Processing refund to buyer...")
        
        # Get dispute information for display
        dispute = session.query(Dispute).filter(Dispute.id == dispute_id).first()
        if not dispute:
            await query.edit_message_text("❌ Dispute not found.")
            return ConversationHandler.END
        
        await query.edit_message_text(
            f"⚖️ Dispute Resolution: Refund to Buyer\n\n"
            f"🆔 ID: {dispute.id}\n"
            f"💰 Action: Refunding escrow amount to buyer\n"
            f"👤 Resolved by: Admin {user.first_name}\n\n"
            f"⚠️ This action is irreversible\n"
            f"Buyer will receive the full escrow amount.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Confirm Refund", callback_data=f"admin_confirm_refund:{dispute_id}"),
                    InlineKeyboardButton("❌ Cancel", callback_data=f"admin_dispute_chat_live")
                ]
            ])
        )
    
    except ValueError as e:
        logger.error(f"Invalid dispute ID format: {e}")
        await safe_answer_callback_query(query, "❌ Invalid dispute ID", show_alert=True)
    except TelegramError as e:
        logger.error(f"Telegram API error in admin resolve buyer: {e}")
        await safe_answer_callback_query(query, "❌ Message error", show_alert=True)
    except Exception as e:
        logger.error(f"Admin resolve buyer failed: {e}")
        await safe_answer_callback_query(query, "❌ Error occurred", show_alert=True)
    finally:
        session.close()
        
    return ConversationHandler.END


async def handle_admin_resolve_seller(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle admin_resolve_seller callback - release to seller"""
    logger.info(f"🔥 handle_admin_resolve_seller called by user {update.effective_user.id if update.effective_user else 'None'}")
    
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if not query or not query.data:
        return ConversationHandler.END
        
    try:
        dispute_id = query.data.split(":")[-1]
        await safe_answer_callback_query(query, "💰 Processing release to seller...")
        
        await query.edit_message_text(
            f"⚖️ Dispute Resolution: Release to Seller\n\n"
            f"🆔 ID: {dispute.id}\n"
            f"💰 Action: Releasing escrow amount to seller\n"
            f"👤 Resolved by: Admin {user.first_name}\n\n"
            f"⚠️ This action is irreversible\n"
            f"Seller will receive the escrow amount minus platform fees.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Confirm Release", callback_data=f"admin_confirm_release:{dispute_id}"),
                    InlineKeyboardButton("❌ Cancel", callback_data=f"admin_dispute_chat_live")
                ]
            ])
        )
        
    except Exception as e:
        logger.error(f"Admin resolve seller failed: {e}")
        await safe_answer_callback_query(query, "❌ Error occurred", show_alert=True)
        
    return ConversationHandler.END


async def handle_admin_full_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle admin_full_chat callback - show complete chat history"""
    logger.info(f"🔥 handle_admin_full_chat called by user {update.effective_user.id if update.effective_user else 'None'}")
    
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if not query or not query.data:
        return ConversationHandler.END
        
    try:
        dispute_id = query.data.split(":")[-1]
        await safe_answer_callback_query(query, "📝 Loading full chat history...")
        
        session = SessionLocal()
        try:
            # Get all messages for this dispute
            messages = session.query(DisputeMessage).filter(
                DisputeMessage.dispute_id == dispute_id
            ).order_by(DisputeMessage.created_at).all()
            
            if not messages:
                chat_display = "📭 No messages in this dispute yet."
            else:
                chat_lines = []
                for msg in messages:
                    timestamp = msg.created_at.strftime("%m/%d %H:%M")
                    role_emoji = "👤" if msg.sender_role == "user" else "🔧"
                    chat_lines.append(f"{timestamp} {role_emoji}{msg.sender_role.title()}: {msg.message}")
                
                chat_display = "\n".join(chat_lines[-20:])  # Show last 20 messages
                if len(messages) > 20:
                    chat_display = f"[Showing last 20 of {len(messages)} messages]\n" + chat_display
        finally:
            session.close()
        
        await query.edit_message_text(
            f"📝 Full Chat History: {dispute_id}\n\n"
            f"💬 Messages:\n"
            f"```\n{chat_display}\n```\n\n"
            f"📊 Total Messages: {len(messages) if messages else 0}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔙 Back to Chat", callback_data=f"admin_dispute_chat_live"),
                    InlineKeyboardButton("⚖️ Disputes", callback_data="admin_disputes")
                ]
            ])
        )
        
    except Exception as e:
        logger.error(f"Admin full chat failed: {e}")
        await safe_answer_callback_query(query, "❌ Error occurred", show_alert=True)
        
    return ConversationHandler.END


async def handle_admin_chat_exit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle admin_chat_exit callback - exit dispute chat"""
    logger.info(f"🔥 handle_admin_chat_exit called by user {update.effective_user.id if update.effective_user else 'None'}")
    
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    await safe_answer_callback_query(query, "👋 Exiting chat...")
    
    try:
        # Clear any active chat sessions and dispute manager
        if context.user_data:
            context.user_data.pop('active_dispute_chat', None)
            context.user_data.pop('chat_mode', None)
            context.user_data.pop('current_dispute_id', None)
        
        # Clear from dispute manager
        if hasattr(dispute_manager, 'remove_all_sessions'):
            dispute_manager.remove_all_sessions(user.id)
        elif hasattr(dispute_manager, 'active_disputes') and user.id in dispute_manager.active_disputes:
            del dispute_manager.active_disputes[user.id]
            if user.id in dispute_manager.current_dispute:
                del dispute_manager.current_dispute[user.id]
        
        # Directly edit message to dispute dashboard - avoid callback conflict
        from database import SessionLocal
        from models import Dispute
        
        session = SessionLocal()
        try:
            total_disputes = session.query(Dispute).count()
            open_disputes = session.query(Dispute).filter(Dispute.status == "open").count()
            
            await query.edit_message_text(
                f"⚖️ Dispute Management Dashboard\n\n"
                f"📊 Summary:\n"
                f"• Total Disputes: {total_disputes}\n"
                f"• Open/Active: {open_disputes}\n",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 Live Disputes", callback_data="admin_dispute_chat_live")],
                    [InlineKeyboardButton("🏠 Admin Panel", callback_data="admin_main")]
                ])
            )
        finally:
            session.close()
        
    except Exception as e:
        logger.error(f"Admin chat exit failed: {e}")
        await query.edit_message_text(
            "❌ Error exiting chat. Returning to admin panel.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Admin Panel", callback_data="admin_main")]
            ])
        )
        
    return ConversationHandler.END


async def handle_admin_confirm_refund(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle admin_confirm_refund callback - execute refund to buyer"""
    logger.info(f"🔥 handle_admin_confirm_refund called by user {update.effective_user.id if update.effective_user else 'None'}")
    
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if not query or not query.data:
        return ConversationHandler.END
        
    try:
        dispute_id = query.data.split(":")[-1]
        await safe_answer_callback_query(query, "⚡ Executing refund...")
        
        from database import SessionLocal
        from models import Dispute, Escrow, EscrowStatus
        
        session = SessionLocal()
        try:
            # Get dispute and escrow
            dispute = session.query(Dispute).filter(Dispute.id == dispute_id).first()
            if not dispute:
                await query.edit_message_text("❌ Dispute not found.")
                return ConversationHandler.END
                
            escrow = dispute.escrow
            if not escrow:
                await query.edit_message_text("❌ Associated escrow not found.")
                return ConversationHandler.END
            
            # Close the session before using DisputeResolutionService
            session.close()
            
            # Use the proper dispute resolution service that handles platform fees correctly
            from services.dispute_resolution import DisputeResolutionService
            result = await DisputeResolutionService.resolve_refund_to_buyer(
                dispute_id=int(dispute_id),
                admin_user_id=user.id
            )
            
            if not result.success:
                await query.edit_message_text(f"❌ Refund failed: {result.error_message}")
                return ConversationHandler.END
            
            # CACHE INVALIDATION: Dispute resolved, invalidate cached data
            invalidate_dispute_cache(context.user_data)
            logger.info(f"🗑️ DISPUTE_CACHE_INVALIDATED: Dispute {dispute_id} cache cleared after refund to buyer")
            
            # Send outcome-aware dispute resolution notifications  
            try:
                from services.post_completion_notification_service import PostCompletionNotificationService
                notification_service = PostCompletionNotificationService()
                await notification_service.notify_escrow_completion(
                    escrow_id=result.escrow_id,
                    completion_type='dispute_resolved',
                    amount=float(result.amount),
                    buyer_id=result.buyer_id,
                    seller_id=result.seller_id,
                    dispute_winner_id=result.dispute_winner_id,
                    dispute_loser_id=result.dispute_loser_id,
                    resolution_type=result.resolution_type
                )
                logger.info(f"Dispute resolution notifications sent for {result.escrow_id} (refund to buyer)")
            except Exception as notify_error:
                logger.error(f"Failed to send dispute resolution notifications: {notify_error}")
            
            # Get updated escrow info from a new session for display
            session = SessionLocal()
            try:
                escrow = session.query(Escrow).filter(Escrow.escrow_id == result.escrow_id).first()
                platform_fee = Decimal(str(escrow.amount)) * Decimal("0.05")  # 5% platform fee
            finally:
                session.close()
            
            await query.edit_message_text(
                f"✅ Refund Executed Successfully\n\n"
                f"🆔 ID: {dispute.id}\n"
                f"💰 Refunded Amount: ${result.amount:.2f}\n"
                f"🏦 Platform Fee Retained: ${platform_fee:.2f}\n"
                f"👤 Resolved by: Admin {user.first_name}\n"
                f"⏰ Completed: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
                f"📧 Buyer refunded (trade amount only, platform fee retained).",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("⚖️ Back to Disputes", callback_data="admin_disputes"),
                        InlineKeyboardButton("🏠 Admin Panel", callback_data="admin_main")
                    ]
                ])
            )
            
        finally:
            session.close()
        
    except Exception as e:
        logger.error(f"Admin confirm refund failed: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        try:
            if query:
                await safe_answer_callback_query(query, f"❌ Refund failed: {str(e)}", show_alert=True)
                # Try to edit message to show error
                await query.edit_message_text(
                    f"❌ Refund Failed\n\n"
                    f"Error: {str(e)}\n\n"
                    f"Please try again or contact support.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("⚖️ Back to Disputes", callback_data="admin_disputes"),
                            InlineKeyboardButton("🏠 Admin Panel", callback_data="admin_main")
                        ]
                    ])
                )
        except Exception as edit_error:
            logger.error(f"Failed to show error message: {edit_error}")
        
    return ConversationHandler.END


async def handle_admin_confirm_release(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle admin_confirm_release callback - execute release to seller"""
    logger.info(f"🔥 handle_admin_confirm_release called by user {update.effective_user.id if update.effective_user else 'None'}")
    
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if not query or not query.data:
        return ConversationHandler.END
        
    try:
        dispute_id = query.data.split(":")[-1]
        await safe_answer_callback_query(query, "⚡ Executing release...")
        
        from database import SessionLocal
        from models import Dispute, Escrow, EscrowStatus
        
        session = SessionLocal()
        try:
            # Get dispute and escrow
            dispute = session.query(Dispute).filter(Dispute.id == dispute_id).first()
            if not dispute:
                await query.edit_message_text("❌ Dispute not found.")
                return ConversationHandler.END
                
            escrow = dispute.escrow
            if not escrow:
                await query.edit_message_text("❌ Associated escrow not found.")
                return ConversationHandler.END
            
            # Close the session before using DisputeResolutionService  
            session.close()
            
            # Use the proper dispute resolution service that handles fund transfers and platform fees correctly
            from services.dispute_resolution import DisputeResolutionService
            result = await DisputeResolutionService.resolve_release_to_seller(
                dispute_id=int(dispute_id),
                admin_user_id=user.id
            )
            
            if not result.success:
                await query.edit_message_text(f"❌ Release failed: {result.error_message}")
                return ConversationHandler.END
            
            # CACHE INVALIDATION: Dispute resolved, invalidate cached data
            invalidate_dispute_cache(context.user_data)
            logger.info(f"🗑️ DISPUTE_CACHE_INVALIDATED: Dispute {dispute_id} cache cleared after release to seller")
            
            # Send outcome-aware dispute resolution notifications
            try:
                from services.post_completion_notification_service import PostCompletionNotificationService
                notification_service = PostCompletionNotificationService()
                await notification_service.notify_escrow_completion(
                    escrow_id=result.escrow_id,
                    completion_type='dispute_resolved',
                    amount=float(result.amount),
                    buyer_id=result.buyer_id,
                    seller_id=result.seller_id,
                    dispute_winner_id=result.dispute_winner_id,
                    dispute_loser_id=result.dispute_loser_id,
                    resolution_type=result.resolution_type
                )
                logger.info(f"Dispute resolution notifications sent for {result.escrow_id} (release to seller)")
            except Exception as notify_error:
                logger.error(f"Failed to send dispute resolution notifications: {notify_error}")
            
            # Get updated escrow info from a new session for display
            session = SessionLocal()
            try:
                escrow = session.query(Escrow).filter(Escrow.escrow_id == result.escrow_id).first()
                platform_fee = Decimal(str(escrow.amount)) * Decimal("0.05")  # 5% platform fee
            finally:
                session.close()
            
            await query.edit_message_text(
                f"✅ Release Executed Successfully\n\n"
                f"🆔 ID: {dispute.id}\n"
                f"💰 Released Amount: ${result.amount:.2f}\n"
                f"🏦 Platform Fee Retained: ${platform_fee:.2f}\n"
                f"👤 Resolved by: Admin {user.first_name}\n"
                f"⏰ Completed: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
                f"📧 Both parties have been notified of the resolution.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("⚖️ Back to Disputes", callback_data="admin_disputes"),
                        InlineKeyboardButton("🏠 Admin Panel", callback_data="admin_main")
                    ]
                ])
            )
            
        except Exception as e:
            # Handle any session cleanup if needed
            pass
        
    except Exception as e:
        logger.error(f"Admin confirm release failed: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        try:
            if query:
                await safe_answer_callback_query(query, f"❌ Release failed: {str(e)}", show_alert=True)
                # Try to edit message to show error
                await query.edit_message_text(
                    f"❌ Release Failed\n\n"
                    f"Error: {str(e)}\n\n"
                    f"Please try again or contact support.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("⚖️ Back to Disputes", callback_data="admin_disputes"),
                            InlineKeyboardButton("🏠 Admin Panel", callback_data="admin_main")
                        ]
                    ])
                )
        except Exception as edit_error:
            logger.error(f"Failed to show error message: {edit_error}")
        
    return ConversationHandler.END


async def handle_admin_split_funds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle admin_split_funds callback - show split configuration screen"""
    logger.info(f"🔥 handle_admin_split_funds called by user {update.effective_user.id if update.effective_user else 'None'}")
    
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if not query or not query.data:
        return ConversationHandler.END
        
    try:
        dispute_internal_id = int(query.data.split(":")[-1])
        await safe_answer_callback_query(query, "⚖️ Loading split configuration...")
        
        # Get dispute and escrow details
        session = SessionLocal()
        try:
            dispute = session.query(Dispute).filter(Dispute.id == dispute_internal_id).first()
            if not dispute:
                await query.edit_message_text("❌ Dispute not found.")
                return ConversationHandler.END
                
            escrow = dispute.escrow
            if not escrow:
                await query.edit_message_text("❌ Associated escrow not found.")
                return ConversationHandler.END
            
            # Calculate available amount (after platform fee)
            platform_fee = Decimal(str(escrow.amount)) * Decimal("0.05")  # 5% platform fee
            available_amount = Decimal(str(escrow.amount)) - platform_fee
            
            # Default to 50/50 split
            buyer_percent = 50
            seller_percent = 50
            buyer_amount = available_amount * (Decimal(buyer_percent) / Decimal(100))
            seller_amount = available_amount * (Decimal(seller_percent) / Decimal(100))
            
        finally:
            session.close()
        
        message = f"""⚖️ Split Funds

🆔 ID: {dispute.id}
💰 Escrow: ${escrow.amount:.2f}
💰 Fee: ${platform_fee:.2f}
💰 Split: ${available_amount:.2f}

📊 Distribution:
👤 Buyer: {buyer_percent}% = ${buyer_amount:.2f}
🛍️ Seller: {seller_percent}% = ${seller_amount:.2f}

🎯 Choose Split Percentage:
B = Buyer | S = Seller"""

        keyboard = [
            [
                InlineKeyboardButton("B50/S50", callback_data=f"admin_split_set:50:{dispute_internal_id}"),
                InlineKeyboardButton("B60/S40", callback_data=f"admin_split_set:60:{dispute_internal_id}"),
                InlineKeyboardButton("B70/S30", callback_data=f"admin_split_set:70:{dispute_internal_id}"),
            ],
            [
                InlineKeyboardButton("B40/S60", callback_data=f"admin_split_set:40:{dispute_internal_id}"),
                InlineKeyboardButton("B30/S70", callback_data=f"admin_split_set:30:{dispute_internal_id}"),
                InlineKeyboardButton("B20/S80", callback_data=f"admin_split_set:20:{dispute_internal_id}"),
            ],
            [
                InlineKeyboardButton("B80/S20", callback_data=f"admin_split_set:80:{dispute_internal_id}"),
                InlineKeyboardButton("B90/S10", callback_data=f"admin_split_set:90:{dispute_internal_id}"),
                InlineKeyboardButton("B10/S90", callback_data=f"admin_split_set:10:{dispute_internal_id}"),
            ],
            [
                InlineKeyboardButton("✅ Continue with B50/S50", callback_data=f"admin_split_confirm:50:{dispute_internal_id}"),
            ],
            [
                InlineKeyboardButton("❌ Cancel", callback_data=f"admin_chat_start:{dispute_internal_id}"),
            ]
        ]
        
        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Admin split funds failed: {e}")
        await safe_answer_callback_query(query, "❌ Split funds error", show_alert=True)
        
    return ConversationHandler.END


async def handle_admin_split_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle admin_split_set callback - update percentage and show confirmation option"""
    logger.info(f"🔥 handle_admin_split_set called by user {update.effective_user.id if update.effective_user else 'None'}")
    
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if not query or not query.data:
        return ConversationHandler.END
        
    try:
        parts = query.data.split(":")
        buyer_percent = int(parts[1])
        dispute_internal_id = int(parts[2])
        seller_percent = 100 - buyer_percent
        
        await safe_answer_callback_query(query, f"📊 Updated: {buyer_percent}% buyer, {seller_percent}% seller")
        
        # Get dispute and escrow details
        session = SessionLocal()
        try:
            dispute = session.query(Dispute).filter(Dispute.id == dispute_internal_id).first()
            if not dispute:
                await query.edit_message_text("❌ Dispute not found.")
                return ConversationHandler.END
                
            escrow = dispute.escrow
            if not escrow:
                await query.edit_message_text("❌ Associated escrow not found.")
                return ConversationHandler.END
            
            # Calculate amounts
            platform_fee = Decimal(str(escrow.amount)) * Decimal("0.05")  # 5% platform fee
            available_amount = Decimal(str(escrow.amount)) - platform_fee
            buyer_amount = available_amount * (Decimal(buyer_percent) / Decimal(100))
            seller_amount = available_amount * (Decimal(seller_percent) / Decimal(100))
            
        finally:
            session.close()
        
        message = f"""⚖️ Split Funds

🆔 ID: {dispute.id}
💰 Escrow: ${escrow.amount:.2f}
💰 Fee: ${platform_fee:.2f}
💰 Split: ${available_amount:.2f}

📊 Distribution:
👤 Buyer: {buyer_percent}% = ${buyer_amount:.2f}
🛍️ Seller: {seller_percent}% = ${seller_amount:.2f}

🎯 Choose Split Percentage:
B = Buyer | S = Seller"""

        keyboard = [
            [
                InlineKeyboardButton("B50/S50", callback_data=f"admin_split_set:50:{dispute_internal_id}"),
                InlineKeyboardButton("B60/S40", callback_data=f"admin_split_set:60:{dispute_internal_id}"),
                InlineKeyboardButton("B70/S30", callback_data=f"admin_split_set:70:{dispute_internal_id}"),
            ],
            [
                InlineKeyboardButton("B40/S60", callback_data=f"admin_split_set:40:{dispute_internal_id}"),
                InlineKeyboardButton("B30/S70", callback_data=f"admin_split_set:30:{dispute_internal_id}"),
                InlineKeyboardButton("B20/S80", callback_data=f"admin_split_set:20:{dispute_internal_id}"),
            ],
            [
                InlineKeyboardButton("B80/S20", callback_data=f"admin_split_set:80:{dispute_internal_id}"),
                InlineKeyboardButton("B90/S10", callback_data=f"admin_split_set:90:{dispute_internal_id}"),
                InlineKeyboardButton("B10/S90", callback_data=f"admin_split_set:10:{dispute_internal_id}"),
            ],
            [
                InlineKeyboardButton(f"✅ Continue with B{buyer_percent}/S{seller_percent}", callback_data=f"admin_split_confirm:{buyer_percent}:{dispute_internal_id}"),
            ],
            [
                InlineKeyboardButton("❌ Cancel", callback_data=f"admin_chat_start:{dispute_internal_id}"),
            ]
        ]
        
        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Admin split set failed: {e}")
        await safe_answer_callback_query(query, "❌ Error occurred", show_alert=True)
        
    return ConversationHandler.END


async def handle_admin_split_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle admin_split_confirm callback - show final confirmation"""
    logger.info(f"🔥 handle_admin_split_confirm called by user {update.effective_user.id if update.effective_user else 'None'}")
    
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if not query or not query.data:
        return ConversationHandler.END
        
    try:
        parts = query.data.split(":")
        buyer_percent = int(parts[1])
        dispute_internal_id = int(parts[2])
        seller_percent = 100 - buyer_percent
        
        await safe_answer_callback_query(query, f"⚖️ Preparing split confirmation...")
        
        # Get dispute and escrow details
        session = SessionLocal()
        try:
            dispute = session.query(Dispute).filter(Dispute.id == dispute_internal_id).first()
            if not dispute:
                await query.edit_message_text("❌ Dispute not found.")
                return ConversationHandler.END
                
            escrow = dispute.escrow
            if not escrow:
                await query.edit_message_text("❌ Associated escrow not found.")
                return ConversationHandler.END
            
            # Calculate amounts
            platform_fee = Decimal(str(escrow.amount)) * Decimal("0.05")  # 5% platform fee
            available_amount = Decimal(str(escrow.amount)) - platform_fee
            buyer_amount = available_amount * (Decimal(buyer_percent) / Decimal(100))
            seller_amount = available_amount * (Decimal(seller_percent) / Decimal(100))
            
        finally:
            session.close()
        
        message = f"""⚖️ Final Split Confirmation

🆔 ID: {dispute.id}
💰 Escrow: ${escrow.amount:.2f}

📊 Final Distribution:
• Buyer: ${buyer_amount:.2f} ({buyer_percent}%)
• Seller: ${seller_amount:.2f} ({seller_percent}%)
• Platform Fee: ${platform_fee:.2f}
────────────────────
• Total: ${escrow.amount:.2f}

👤 Resolved by: Admin {user.first_name}
⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

⚠️ This action is irreversible
Both parties will be notified immediately."""

        keyboard = [
            [
                InlineKeyboardButton("✅ Execute Split", callback_data=f"admin_split_execute:{buyer_percent}:{dispute_internal_id}"),
            ],
            [
                InlineKeyboardButton("⬅️ Adjust Split", callback_data=f"admin_split_funds:{dispute_internal_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"admin_chat_start:{dispute_internal_id}"),
            ]
        ]
        
        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Admin split confirm failed: {e}")
        await safe_answer_callback_query(query, "❌ Error occurred", show_alert=True)
        
    return ConversationHandler.END


async def handle_admin_split_execute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle admin_split_execute callback - execute the split using backend service"""
    logger.info(f"🔥 handle_admin_split_execute called by user {update.effective_user.id if update.effective_user else 'None'}")
    
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if not query or not query.data:
        return ConversationHandler.END

    session = SessionLocal()
    try:
        parts = query.data.split(":")
        buyer_percent = int(parts[1])
        dispute_internal_id = int(parts[2])
        seller_percent = 100 - buyer_percent
        
        await safe_answer_callback_query(query, "💰 Executing split resolution...")
        
        # Get dispute details
        dispute = session.query(Dispute).filter(Dispute.id == dispute_internal_id).first()
        if not dispute:
            await query.edit_message_text("❌ Dispute not found.")
            return ConversationHandler.END
            
        escrow = dispute.escrow
        if not escrow:
            await query.edit_message_text("❌ Associated escrow not found.")
            return ConversationHandler.END
        
        # Close the session before using atomic resolution service
        session.close()
        
        # Use the dispute resolution service for custom split
        from services.dispute_resolution import DisputeResolutionService
        
        result = await DisputeResolutionService.resolve_custom_split(
            dispute_id=dispute_internal_id,
            buyer_percent=buyer_percent,
            seller_percent=seller_percent,
            admin_user_id=user.id
        )
        
        if not result.success:
            await query.edit_message_text(f"❌ Split failed: {result.error_message}")
            return ConversationHandler.END
        
        # CACHE INVALIDATION: Dispute resolved, invalidate cached data
        invalidate_dispute_cache(context.user_data)
        logger.info(f"🗑️ DISPUTE_CACHE_INVALIDATED: Dispute {dispute_internal_id} cache cleared after custom split resolution")
        
        # Send admin notification for dispute resolution
        import asyncio
        from services.admin_trade_notifications import admin_trade_notifications
        
        # Re-fetch data for notification (session was closed)
        notification_session = SessionLocal()
        try:
            notification_dispute = notification_session.query(Dispute).filter(Dispute.id == dispute_internal_id).first()
            if notification_dispute and notification_dispute.escrow:
                notification_escrow = notification_dispute.escrow
                buyer = notification_session.query(User).filter(User.id == notification_escrow.buyer_id).first()
                seller = notification_session.query(User).filter(User.id == notification_escrow.seller_id).first()
                
                buyer_info = f"{buyer.first_name} (@{buyer.username})" if buyer and buyer.username else (f"{buyer.first_name}" if buyer else "Unknown")
                seller_info = f"{seller.first_name} (@{seller.username})" if seller and seller.username else (f"{seller.first_name}" if seller else "Unknown")
                
                asyncio.create_task(
                    admin_trade_notifications.notify_dispute_resolved({
                        'dispute_id': notification_dispute.id,
                        'escrow_id': notification_escrow.escrow_id,
                        'amount': float(str(notification_escrow.amount)) if notification_escrow.amount is not None else 0.0,
                        'buyer_info': buyer_info,
                        'seller_info': seller_info,
                        'currency': notification_escrow.currency,
                        'resolution_type': 'custom_split',
                        'buyer_percent': buyer_percent,
                        'seller_percent': seller_percent,
                        'resolved_at': datetime.utcnow(),
                        'resolved_by': f"Admin {user.first_name}"
                    })
                )
        except Exception as notification_error:
            logger.error(f"Failed to send admin dispute resolution notification: {notification_error}")
        finally:
            notification_session.close()
        
        # Calculate final amounts for display
        platform_fee = Decimal(str(escrow.amount)) * Decimal("0.05")
        available_amount = Decimal(str(escrow.amount)) - platform_fee
        buyer_amount = available_amount * (Decimal(buyer_percent) / Decimal(100))
        seller_amount = available_amount * (Decimal(seller_percent) / Decimal(100))
        
        # Send notifications to both parties
        try:
            from services.notification_service import notification_service as NotificationService
            # Send split notifications (this may need to be implemented)
            await NotificationService.send_escrow_split_notification(escrow, buyer_amount, seller_amount, buyer_percent, seller_percent)
            logger.info(f"Notifications sent for split resolution - escrow {escrow.escrow_id}")
        except Exception as notify_error:
            logger.error(f"Failed to send split notifications: {notify_error}")
        
        await query.edit_message_text(
            f"✅ Split Resolution Executed Successfully\n\n"
            f"🆔 ID: {dispute.id}\n"
            f"💰 Fund Distribution:\n"
            f"   • Buyer: ${buyer_amount:.2f} ({buyer_percent}%)\n"
            f"   • Seller: ${seller_amount:.2f} ({seller_percent}%)\n"
            f"   • Platform Fee Retained: ${platform_fee:.2f}\n\n"
            f"👤 Resolved by: Admin {user.first_name}\n"
            f"⏰ Completed: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"📧 Both parties have been notified of the resolution.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("⚖️ Back to Disputes", callback_data="admin_disputes"),
                    InlineKeyboardButton("🏠 Admin Panel", callback_data="admin_main")
                ]
            ])
        )
        
    except Exception as e:
        logger.error(f"Admin split execute failed: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        try:
            if query:
                await safe_answer_callback_query(query, f"❌ Split failed: {str(e)}", show_alert=True)
                await query.edit_message_text(
                    f"❌ Split Failed\n\n"
                    f"Error: {str(e)}\n\n"
                    f"Please try again or contact support.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("⚖️ Back to Disputes", callback_data="admin_disputes"),
                            InlineKeyboardButton("🏠 Admin Panel", callback_data="admin_main")
                        ]
                    ])
                )
        except Exception as edit_error:
            logger.error(f"Failed to show error message: {edit_error}")
    finally:
        if session:
            session.close()
        
    return ConversationHandler.END
