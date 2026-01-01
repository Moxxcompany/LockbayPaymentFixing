"""
Comprehensive Admin Transaction Management System
Detailed transaction oversight, monitoring, and control interface
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from decimal import Decimal
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy.orm import sessionmaker
from sqlalchemy import desc, func, or_, and_

from database import SessionLocal
from models import (
    User, Escrow, EscrowStatus, ExchangeOrder, ExchangeStatus,
    Cashout, CashoutStatus, Transaction, TransactionType, Rating
)
from utils.admin_security import is_admin_secure
from utils.financial import FinancialCalculator
from utils.callback_utils import safe_edit_message_text, safe_answer_callback_query
from utils.cashout_state_validator import CashoutStateValidator

logger = logging.getLogger(__name__)

# Conversation states
TRANSACTION_DETAIL, TRANSACTION_ACTION = range(2)

def escape_markdown(text: str) -> str:
    """Safely escape markdown characters to prevent parsing errors"""
    if not text:
        return ""
    # Escape ALL markdown characters that cause parsing issues in Telegram
    return (str(text)
        .replace('\\', '\\\\')  # Escape backslashes first
        .replace('_', '\\_')
        .replace('*', '\\*')
        .replace('[', '\\[')
        .replace(']', '\\]')
        .replace('`', '\\`')
        .replace('(', '\\(')
        .replace(')', '\\)')
        .replace('~', '\\~')
        .replace('>', '\\>')
        .replace('#', '\\#')
        .replace('+', '\\+')
        .replace('-', '\\-')
        .replace('=', '\\=')
        .replace('|', '\\|')
        .replace('{', '\\{')
        .replace('}', '\\}')
        .replace('.', '\\.')
        .replace('!', '\\!')
        .replace(':', '\\:'))



async def handle_admin_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Comprehensive transaction management dashboard"""
    logger.info(f"🔥 handle_admin_transactions called by user {update.effective_user.id if update.effective_user else 'None'}")
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        elif update.message:
            await update.message.reply_text("❌ Access denied. Admin access required.")
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query, "💰")

    try:
        session = SessionLocal()
        try:
            from datetime import timezone
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # === COMPREHENSIVE TRANSACTION METRICS ===
            
            # Escrow transactions
            total_escrows = session.query(Escrow).count()
            active_escrows = session.query(Escrow).filter(
                Escrow.status.in_([EscrowStatus.PAYMENT_PENDING.value, EscrowStatus.ACTIVE.value, EscrowStatus.DISPUTED.value])
            ).count()
            escrow_volume_today = session.query(func.sum(Escrow.amount)).filter(
                Escrow.created_at >= today_start
            ).scalar() or 0
            
            # Exchange transactions
            total_exchanges = session.query(ExchangeOrder).count()
            active_exchanges = session.query(ExchangeOrder).filter(
                ExchangeOrder.status.in_([ExchangeStatus.PENDING_APPROVAL.value, ExchangeStatus.PROCESSING.value])
            ).count()
            exchange_volume_today = session.query(func.sum(ExchangeOrder.source_amount)).filter(
                ExchangeOrder.created_at >= today_start
            ).scalar() or 0
            
            # CashOut transactions
            total_cashouts = session.query(Cashout).count()
            pending_cashouts_query = session.query(Cashout).filter(
                or_(
                    Cashout.status == CashoutStatus.PENDING.value,
                    Cashout.status == CashoutStatus.OTP_PENDING.value,  # CRITICAL FIX: Include deferred records
                    and_(Cashout.status == "admin_pending", Cashout.admin_approved == False)
                )
            ).order_by(desc(Cashout.created_at))
            pending_cashouts_list = pending_cashouts_query.limit(3).all()
            pending_cashouts = pending_cashouts_query.count()
            cashout_volume_today = session.query(func.sum(Cashout.amount)).filter(
                Cashout.created_at >= today_start
            ).scalar() or 0
            
            # Recent high-value transactions
            high_value_escrows = session.query(Escrow).filter(
                Escrow.amount >= 1000,
                Escrow.created_at >= now - timedelta(days=7)
            ).order_by(desc(Escrow.created_at)).limit(3).all()
            
            # Total volume metrics
            total_volume_today = float(escrow_volume_today) + float(exchange_volume_today) + float(cashout_volume_today)
            
            message = f"""💰 Admin Transactions

📊 Today: ${total_volume_today:,.0f}
Escrows: ${escrow_volume_today:,.0f} • Exchanges: ${exchange_volume_today:,.0f} • CashOuts: ${cashout_volume_today:,.0f}

🔄 Active: {active_escrows}/{total_escrows} Escrows • {active_exchanges}/{total_exchanges} Exchanges • {pending_cashouts} Pending

💎 High-Value (7d)"""
            
            if high_value_escrows:
                for escrow in high_value_escrows:
                    buyer = session.query(User).filter(User.id == escrow.buyer_id).first()
                    age = (now - escrow.created_at).days
                    status_emoji = "🟢" if escrow.status == EscrowStatus.COMPLETED.value else "🟡"
                    message += f"\n{status_emoji} ${escrow.amount:,.0f} • {buyer.first_name if buyer else 'User'} • {age}d ago"
            else:
                message += "\n📝 No high-value transactions this week"
            
            # Add pending cashouts section if any exist
            if pending_cashouts_list:
                message += f"\n\n⚠️ Pending CashOuts ({pending_cashouts})"
                for cashout in pending_cashouts_list:
                    user_obj = session.query(User).filter(User.id == cashout.user_id).first()
                    user_name = escape_markdown(user_obj.first_name if user_obj else 'Unknown')
                    age_hours = int((now - cashout.created_at).total_seconds() / 3600)
                    age_display = f"{age_hours}h" if age_hours < 48 else f"{age_hours//24}d"
                    risk_emoji = "🔴" if cashout.risk_score > 0.7 else "🟡" if cashout.risk_score > 0.3 else "🟢"
                    message += f"\n{risk_emoji} `{escape_markdown(cashout.cashout_id)}` • ${cashout.amount:.2f} {escape_markdown(cashout.currency)} • {user_name} • {age_display} ago"
            
            message += f"\n\n⏰ Updated: {now.strftime('%H:%M:%S UTC')}"
            
        finally:
            session.close()
        
        # Build dynamic keyboard based on pending cashouts
        keyboard = [
            [
                InlineKeyboardButton("🔍 View All Escrows", callback_data="admin_trans_escrows"),
                InlineKeyboardButton("💱 View Exchanges", callback_data="admin_trans_exchanges"),
            ],
            [
                InlineKeyboardButton("💸 CashOuts", callback_data="admin_trans_cashouts"),
                InlineKeyboardButton("📈 Analytics", callback_data="admin_trans_analytics"),
            ]
        ]
        
        # Add pending cashouts button if any exist
        if pending_cashouts > 0:
            keyboard.append([
                InlineKeyboardButton(f"⚠️ Review Pending ({pending_cashouts})", callback_data="admin_cashout_pending"),
                InlineKeyboardButton("⚡ Quick Actions", callback_data="admin_trans_actions"),
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("⚡ Quick Actions", callback_data="admin_trans_actions"),
            ])
        
        keyboard.append([
            InlineKeyboardButton("🏠 Admin", callback_data="admin_main"),
        ])
        
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
        logger.error(f"Admin transactions dashboard failed: {e}")
        if query:
            await safe_answer_callback_query(query, f"❌ Transactions dashboard failed: {str(e)}", show_alert=True)
        elif update.message:
            await update.message.reply_text(f"❌ Transactions dashboard failed: {str(e)}")
        return ConversationHandler.END

    return ConversationHandler.END


async def handle_admin_trans_escrows(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Detailed escrow transaction management"""
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query, "🔍")

    try:
        session = SessionLocal()
        try:
            # Get recent escrows with details
            recent_escrows = session.query(Escrow).order_by(
                desc(Escrow.created_at)
            ).limit(10).all()
            
            # Summary metrics
            total_escrows = session.query(Escrow).count()
            completed_escrows = session.query(Escrow).filter(
                Escrow.status == EscrowStatus.COMPLETED.value
            ).count()
            success_rate = (completed_escrows / max(total_escrows, 1)) * 100
            
            message = f"""🔍 Escrow Transaction Details

📊 Summary"
• Total Escrows: {total_escrows:,}
• Success Rate: {success_rate:.1f}%
• Completed: {completed_escrows:,}

🕒 Recent Escrows"""
            
            if recent_escrows:
                for escrow in recent_escrows[:5]:
                    buyer = session.query(User).filter(User.id == escrow.buyer_id).first()
                    seller = session.query(User).filter(User.id == escrow.seller_id).first()
                    
                    status_icons = {
                        EscrowStatus.PAYMENT_PENDING.value: "🟡",
                        EscrowStatus.ACTIVE.value: "🔵",
                        EscrowStatus.COMPLETED.value: "🟢",
                        EscrowStatus.DISPUTED.value: "🔴",
                        EscrowStatus.CANCELLED.value: "⚫"
                    }
                    
                    icon = status_icons.get(escrow.status, "❓")
                    # Ensure escrow.created_at is timezone-aware for subtraction
                    created_at = escrow.created_at.replace(tzinfo=timezone.utc) if escrow.created_at.tzinfo is None else escrow.created_at
                    age = (datetime.now(timezone.utc) - created_at).days
                    
                    message += f"""
{icon} #{escrow.escrow_id} - ${escrow.amount:.2f}
   Buyer: {buyer.first_name if buyer else 'Unknown'}
   Seller: {seller.first_name if seller else 'Unknown'}
   Status: {escrow.status.upper()} • {age}d ago"""
            else:
                message += "\n📝 No escrows found"
            
        finally:
            session.close()
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Active Only", callback_data="admin_trans_escrows_active"),
                InlineKeyboardButton("📋 All Status", callback_data="admin_trans_escrows_all"),
            ],
            [
                InlineKeyboardButton("💰 Transactions", callback_data="admin_transactions"),
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
        
    except Exception as e:
        logger.error(f"Admin escrow transactions failed: {e}")
        if query:
            await safe_answer_callback_query(query, f"❌ Escrow details failed: {str(e)}", show_alert=True)
        return ConversationHandler.END

    return ConversationHandler.END


async def handle_admin_trans_cashouts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Detailed cashout transaction management"""
    logger.info(f"🔥 handle_admin_trans_cashouts called by user {update.effective_user.id if update.effective_user else 'None'}")
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query, "💸")

    try:
        session = SessionLocal()
        try:
            # Get recent cashouts
            recent_cashouts = session.query(Cashout).order_by(
                desc(Cashout.created_at)
            ).limit(10).all()
            
            # Pending cashouts needing attention
            pending_cashouts = session.query(Cashout).filter(
                Cashout.status == CashoutStatus.PENDING.value
            ).order_by(desc(Cashout.created_at)).limit(5).all()
            
            # Enhanced summary metrics
            total_cashouts = session.query(Cashout).count()
            crypto_cashouts = session.query(Cashout).filter(Cashout.cashout_type == 'crypto').count()
            ngn_cashouts = session.query(Cashout).filter(Cashout.cashout_type == 'NGN_BANK').count()
            # Count both SUCCESS and COMPLETED status for backward compatibility
            completed_cashouts = session.query(Cashout).filter(
                or_(Cashout.status == CashoutStatus.SUCCESS.value, Cashout.status == CashoutStatus.COMPLETED.value)
            ).count()
            failed_cashouts = session.query(Cashout).filter(Cashout.status == CashoutStatus.FAILED.value).count()
            total_pending = len(pending_cashouts)
            total_volume = session.query(func.sum(Cashout.amount)).scalar() or 0
            
            message = f"""💸 CashOut Management Dashboard

📊 Complete Overview
• Total: {total_cashouts} ({completed_cashouts} ✅, {failed_cashouts} ❌, {total_pending} ⏳)
• Types: {crypto_cashouts} Crypto • {ngn_cashouts} NGN Bank
• Volume: ${float(total_volume):,.2f}

⚠️ Pending Admin Action"""
            
            if pending_cashouts:
                for cashout in pending_cashouts:
                    user_obj = session.query(User).filter(User.id == cashout.user_id).first()
                    # Ensure cashout.created_at is timezone-aware for subtraction
                    created_at = cashout.created_at.replace(tzinfo=timezone.utc) if cashout.created_at.tzinfo is None else cashout.created_at
                    age_hours = int((datetime.now(timezone.utc) - created_at).total_seconds() / 3600)
                    
                    # Safely escape all pending cashout data
                    safe_currency = escape_markdown(cashout.currency)
                    safe_user_name = escape_markdown(user_obj.first_name if user_obj else 'Unknown')
                    safe_cashout_type = escape_markdown(cashout.cashout_type)
                    
                    message += f"""
🔸 ${cashout.amount:.2f} to {safe_currency}
   User: {safe_user_name}
   Waiting: {age_hours}h • Type: {safe_cashout_type}"""
            else:
                message += "\n✅ No pending cashouts"
            
            message += "\n\n🕒 Recent Transactions (Detailed View)"
            if recent_cashouts:
                for cashout in recent_cashouts[:6]:  # Show first 6 (most recent)
                    status_icons = {
                        CashoutStatus.SUCCESS.value: "✅",  # New success status
                        CashoutStatus.COMPLETED.value: "✅",  # Legacy completed status (backward compatibility)
                        CashoutStatus.PENDING.value: "⏳", 
                        CashoutStatus.OTP_PENDING.value: "🔐",  # CRITICAL FIX: Add OTP_PENDING status icon
                        CashoutStatus.FAILED.value: "❌",
                        CashoutStatus.EXECUTING.value: "🔄",
                        CashoutStatus.APPROVED.value: "👍"
                    }
                    status_icon = status_icons.get(cashout.status, "❓")
                    user_obj = session.query(User).filter(User.id == cashout.user_id).first()
                    # Ensure cashout.created_at is timezone-aware for subtraction
                    created_at = cashout.created_at.replace(tzinfo=timezone.utc) if cashout.created_at.tzinfo is None else cashout.created_at
                    age = (datetime.now(timezone.utc) - created_at).days
                    hours = int((datetime.now(timezone.utc) - created_at).total_seconds() / 3600) if age == 0 else None
                    time_str = f"{hours}h ago" if hours and hours < 24 else f"{age}d ago"
                    
                    # Enhanced details with admin-relevant info - ESCAPE MARKDOWN CHARACTERS
                    tx_ref = cashout.external_tx_id or cashout.blockchain_tx_id or "No-Ref"
                    # Safely escape markdown characters in destination and transaction data
                    destination_raw = cashout.destination[:20] + "..." if len(cashout.destination) > 20 else cashout.destination
                    destination_safe = escape_markdown(destination_raw)
                    
                    cashout_id_safe = escape_markdown(str(cashout.cashout_id))
                    tx_ref_truncated = tx_ref[:15] + ('...' if len(tx_ref) > 15 else '')
                    tx_ref_safe = escape_markdown(tx_ref_truncated)
                    
                    user_name_safe = escape_markdown(user_obj.first_name if user_obj else 'Unknown')
                    
                    # Build message parts safely without f-string complications
                    message_part = f"\n\n{status_icon} "
                    message_part += f"`{cashout_id_safe}`"  # Use code formatting instead of italics
                    message_part += f"\n💰 ${cashout.amount:.2f} {escape_markdown(cashout.currency)} → {escape_markdown(cashout.cashout_type)}"
                    message_part += f"\n👤 {user_name_safe} • {time_str}"
                    message_part += f"\n📍 {destination_safe}"
                    message_part += f"\n🔗 {tx_ref_safe}"
                    message += message_part
            else:
                message += "\n📝 No cashout transactions found\n⚠️ This may indicate a database sync issue"
            
        finally:
            session.close()
        
        keyboard = [
            [
                InlineKeyboardButton("🔍 Search Cashout", callback_data="admin_cashout_search"),
            ],
            [
                InlineKeyboardButton("⚠️ Review Pending", callback_data="admin_cashout_pending"),
                InlineKeyboardButton("📊 Analytics", callback_data="admin_cashout_analytics"),
            ],
            [
                InlineKeyboardButton("🐛 Debug Missing TX", callback_data="admin_debug_cashouts"),
                InlineKeyboardButton("💰 Back to Transactions", callback_data="admin_transactions"),
            ],
            [
                InlineKeyboardButton("🏠 Admin Main", callback_data="admin_main")
            ]
        ]
        
        if query:
            await safe_edit_message_text(
                query,
                message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        
    except Exception as e:
        logger.error(f"Admin cashout management failed: {e}")
        if query:
            await safe_answer_callback_query(query, f"❌ Cashout management failed: {str(e)}", show_alert=True)
        return ConversationHandler.END

    return ConversationHandler.END


async def handle_admin_cashout_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle pending cashouts requiring admin approval"""
    logger.info(f"🔥 handle_admin_cashout_pending called by user {update.effective_user.id if update.effective_user else 'None'}")
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query, "⚠️")

    try:
        session = SessionLocal()
        try:
            # Get pending cashouts requiring admin approval (including failed ones for retry)
            pending_cashouts = session.query(Cashout).filter(
                or_(
                    Cashout.status == CashoutStatus.PENDING.value,
                    Cashout.status == CashoutStatus.OTP_PENDING.value,  # CRITICAL FIX: Include deferred records
                    and_(Cashout.status == "admin_pending", Cashout.admin_approved == False),
                    Cashout.status == "failed"  # Include failed cashouts for admin retry
                )
            ).order_by(desc(Cashout.created_at)).limit(20).all()
            
            if not pending_cashouts:
                message = """⚠️ Pending Cashout Review
                
✅ No pending cashouts requiring approval

All cashout requests have been processed or are in automated processing queues."""
                
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Refresh", callback_data="admin_cashout_pending"),
                        InlineKeyboardButton("💰 Back to CashOuts", callback_data="admin_trans_cashouts"),
                    ],
                    [
                        InlineKeyboardButton("🏠 Admin Main", callback_data="admin_main")
                    ]
                ]
            else:
                message = f"""⚠️ Pending Cashout Review ({len(pending_cashouts)} items)

🔍 Requires Admin Action"""
                
                for i, cashout in enumerate(pending_cashouts, 1):
                    user_obj = session.query(User).filter(User.id == cashout.user_id).first()
                    user_name_safe = escape_markdown(user_obj.first_name if user_obj else 'Unknown')
                    cashout_id_safe = escape_markdown(str(cashout.cashout_id))
                    destination_safe = escape_markdown(cashout.destination)
                    
                    # Ensure cashout.created_at is timezone-aware for subtraction
                    created_at = cashout.created_at.replace(tzinfo=timezone.utc) if cashout.created_at.tzinfo is None else cashout.created_at
                    age_hours = int((datetime.now(timezone.utc) - created_at).total_seconds() / 3600)
                    age_display = f"{age_hours}h" if age_hours < 48 else f"{age_hours//24}d"
                    
                    # Different indicators for failed vs pending cashouts
                    if cashout.status == "failed":
                        status_indicator = "❌ FAILED"
                        risk_indicator = "🔄"  # Retry indicator
                    else:
                        status_indicator = "⏳ PENDING"
                        risk_indicator = "🔴" if cashout.risk_score > 0.7 else "🟡" if cashout.risk_score > 0.3 else "🟢"
                    
                    message += f"""
                    
{i}. {risk_indicator} #{cashout_id_safe} • {status_indicator}
👤 {user_name_safe} • ${cashout.amount:.2f} {escape_markdown(cashout.currency)} via {escape_markdown(cashout.cashout_type)}
⏰ {age_display} ago
📍 {destination_safe}
💸 Total: ${cashout.net_amount + cashout.total_fee:.2f} (Fee: ${cashout.total_fee:.2f})"""
                
                # Simplified keyboard with essential actions only
                keyboard = []
                
                # Add clear action header and buttons for the first cashout
                if pending_cashouts:
                    first_cashout = pending_cashouts[0]
                    first_user = session.query(User).filter(User.id == first_cashout.user_id).first()
                    first_user_name = first_user.first_name if first_user else 'Unknown'
                    
                    # Add clear header showing which cashout the buttons control
                    message += f"""

⚡ QUICK ACTIONS FOR #{first_cashout.cashout_id}
👤 {first_user_name} • ${first_cashout.amount:.2f} {first_cashout.currency}"""
                    
                    if first_cashout.status == "failed":
                        # For failed cashouts, offer retry or permanent failure - simplified text
                        keyboard.append([
                            InlineKeyboardButton("🔄 Retry", callback_data=f"admin_retry_processing_{first_cashout.cashout_id}"),
                            InlineKeyboardButton("❌ Fail", callback_data=f"admin_mark_failed_{first_cashout.cashout_id}"),
                        ])
                    else:
                        # For pending cashouts, offer approve or decline - simplified text
                        keyboard.append([
                            InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_single_{first_cashout.cashout_id}"),
                            InlineKeyboardButton("❌ Decline", callback_data=f"admin_decline_single_{first_cashout.cashout_id}"),
                        ])
                
                # Essential navigation buttons - mobile-friendly
                keyboard.extend([
                    [
                        InlineKeyboardButton("🔄 Refresh", callback_data="admin_cashout_pending"),
                        InlineKeyboardButton("💰 CashOuts", callback_data="admin_trans_cashouts"),
                    ],
                    [
                        InlineKeyboardButton("🏠 Main", callback_data="admin_main")
                    ]
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
        
    except Exception as e:
        logger.error(f"Admin pending cashout review failed: {e}")
        if query:
            await safe_answer_callback_query(query, f"❌ Pending review failed: {str(e)}", show_alert=True)
        return ConversationHandler.END

    return ConversationHandler.END


async def handle_admin_approve_low_risk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Approve all low-risk cashouts automatically"""
    logger.info(f"🔥 handle_admin_approve_low_risk called by user {update.effective_user.id if update.effective_user else 'None'}")
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query, "✅")

    try:
        session = SessionLocal()
        try:
            # Get low-risk pending cashouts (risk_score < 0.3)
            low_risk_cashouts = session.query(Cashout).filter(
                or_(
                    Cashout.status == CashoutStatus.PENDING.value,
                    Cashout.status == CashoutStatus.OTP_PENDING.value,  # CRITICAL FIX: Include deferred records
                    and_(Cashout.status == "admin_pending", Cashout.admin_approved == False)
                ),
                Cashout.risk_score < 0.3
            ).all()
            
            if not low_risk_cashouts:
                message = """✅ Low Risk Approval
                
⚠️ No low-risk cashouts found for approval

All pending cashouts require manual review due to elevated risk scores."""
                
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Refresh", callback_data="admin_cashout_pending"),
                        InlineKeyboardButton("❌ Review High Risk", callback_data="admin_review_high_risk"),
                    ],
                    [
                        InlineKeyboardButton("💰 Back to CashOuts", callback_data="admin_trans_cashouts"),
                        InlineKeyboardButton("🏠 Admin Main", callback_data="admin_main"),
                    ]
                ]
            else:
                approved_count = 0
                total_amount = 0
                
                for cashout in low_risk_cashouts:
                    # Update cashout status to approved
                    cashout.status = CashoutStatus.APPROVED.value
                    cashout.admin_approved = True
                    cashout.admin_id = user.id
                    cashout.admin_approved_at = datetime.now(timezone.utc)
                    approved_count += 1
                    total_amount += float(cashout.amount)
                
                session.commit()
                
                message = f"""✅ Low Risk Approval Complete
                
🎯 Approved {approved_count} low-risk cashouts
💰 Total approved amount: ${total_amount:.2f}
⚡ Processing will begin automatically

✅ All approved cashouts will be processed within 24 hours."""
                
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Refresh Pending", callback_data="admin_cashout_pending"),
                        InlineKeyboardButton("❌ Review High Risk", callback_data="admin_review_high_risk"),
                    ],
                    [
                        InlineKeyboardButton("💰 Back to CashOuts", callback_data="admin_trans_cashouts"),
                        InlineKeyboardButton("🏠 Admin Main", callback_data="admin_main"),
                    ]
                ]
        finally:
            session.close()
        
        if query:
            await safe_edit_message_text(
                query,
                message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        
    except Exception as e:
        logger.error(f"Admin low-risk approval failed: {e}")
        if query:
            await safe_answer_callback_query(query, f"❌ Approval failed: {str(e)}", show_alert=True)
        return ConversationHandler.END

    return ConversationHandler.END


async def handle_admin_review_high_risk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Review high-risk cashouts requiring manual approval"""
    logger.info(f"🔥 handle_admin_review_high_risk called by user {update.effective_user.id if update.effective_user else 'None'}")
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query, "❌")

    try:
        session = SessionLocal()
        try:
            # Get high-risk pending cashouts (risk_score >= 0.3)
            high_risk_cashouts = session.query(Cashout).filter(
                or_(
                    Cashout.status == CashoutStatus.PENDING.value,
                    Cashout.status == CashoutStatus.OTP_PENDING.value,  # CRITICAL FIX: Include deferred records
                    and_(Cashout.status == "admin_pending", Cashout.admin_approved == False)
                ),
                Cashout.risk_score >= 0.3
            ).order_by(desc(Cashout.risk_score)).limit(10).all()
            
            if not high_risk_cashouts:
                message = """❌ High Risk Review
                
✅ No high-risk cashouts requiring review

All pending cashouts are low-risk and can be auto-approved."""
                
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Approve Low Risk", callback_data="admin_approve_low_risk"),
                        InlineKeyboardButton("🔄 Refresh", callback_data="admin_cashout_pending"),
                    ],
                    [
                        InlineKeyboardButton("💰 Back to CashOuts", callback_data="admin_trans_cashouts"),
                        InlineKeyboardButton("🏠 Admin Main", callback_data="admin_main"),
                    ]
                ]
            else:
                message = f"""❌ High Risk Cashouts ({len(high_risk_cashouts)} items)

🚨 Requires Manual Review"""
                
                for i, cashout in enumerate(high_risk_cashouts, 1):
                    user_obj = session.query(User).filter(User.id == cashout.user_id).first()
                    user_name_safe = escape_markdown(user_obj.first_name if user_obj else 'Unknown')
                    cashout_id_safe = escape_markdown(str(cashout.cashout_id))
                    
                    # Display FULL crypto address without truncation
                    destination_full = escape_markdown(cashout.destination)
                    
                    # Ensure cashout.created_at is timezone-aware for subtraction
                    created_at = cashout.created_at.replace(tzinfo=timezone.utc) if cashout.created_at.tzinfo is None else cashout.created_at
                    age_hours = int((datetime.now(timezone.utc) - created_at).total_seconds() / 3600)
                    age_display = f"{age_hours}h" if age_hours < 48 else f"{age_hours//24}d"
                    
                    risk_level = "🔴 HIGH" if cashout.risk_score > 0.7 else "🟡 MEDIUM"
                    risk_score_safe = escape_markdown(f"{cashout.risk_score:.2f}")
                    
                    message += f"""
                    
{i}. {risk_level} Risk ({risk_score_safe}) • `{cashout_id_safe}`
💰 ${cashout.amount:.2f} {escape_markdown(cashout.currency)} via {escape_markdown(cashout.cashout_type)}
👤 {user_name_safe} • {age_display} ago
📍 Full Address:
`{destination_full}`
💸 Total: ${cashout.net_amount + cashout.total_fee:.2f} (Fee: ${cashout.total_fee:.2f})"""
                
                keyboard = [
                    [
                        InlineKeyboardButton("🔍 Detailed Review", callback_data="admin_detailed_review"),
                        InlineKeyboardButton("✅ Approve Selected", callback_data="admin_approve_selected"),
                    ],
                    [
                        InlineKeyboardButton("❌ Reject Selected", callback_data="admin_reject_selected"),
                        InlineKeyboardButton("🔄 Refresh", callback_data="admin_cashout_pending"),
                    ],
                    [
                        InlineKeyboardButton("💰 Back to CashOuts", callback_data="admin_trans_cashouts"),
                        InlineKeyboardButton("🏠 Admin Main", callback_data="admin_main"),
                    ]
                ]
        finally:
            session.close()
        
        if query:
            await safe_edit_message_text(
                query,
                message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        
    except Exception as e:
        logger.error(f"Admin high-risk review failed: {e}")
        if query:
            await safe_answer_callback_query(query, f"❌ High-risk review failed: {str(e)}", show_alert=True)
        return ConversationHandler.END

    return ConversationHandler.END


async def handle_admin_detailed_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Detailed individual cashout review interface"""
    logger.info(f"🔥 handle_admin_detailed_review called by user {update.effective_user.id if update.effective_user else 'None'}")
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query, "🔍")

    try:
        session = SessionLocal()
        try:
            # Get all pending cashouts for detailed review
            pending_cashouts = session.query(Cashout).filter(
                or_(
                    Cashout.status == CashoutStatus.PENDING.value,
                    Cashout.status == CashoutStatus.OTP_PENDING.value,  # CRITICAL FIX: Include deferred records
                    and_(Cashout.status == "admin_pending", Cashout.admin_approved == False)
                )
            ).order_by(desc(Cashout.risk_score)).limit(5).all()
            
            if not pending_cashouts:
                message = """🔍 Detailed Review
                
✅ No cashouts requiring detailed review

All pending requests have been processed."""
                
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Refresh", callback_data="admin_cashout_pending"),
                        InlineKeyboardButton("💰 Back to CashOuts", callback_data="admin_trans_cashouts"),
                    ],
                    [
                        InlineKeyboardButton("🏠 Admin Main", callback_data="admin_main")
                    ]
                ]
            else:
                message = f"""🔍 Detailed Cashout Review

📋 Individual Review Required ({len(pending_cashouts)} items)"""
                
                for i, cashout in enumerate(pending_cashouts, 1):
                    user_obj = session.query(User).filter(User.id == cashout.user_id).first()
                    user_name_safe = escape_markdown(user_obj.first_name if user_obj else 'Unknown')
                    cashout_id_safe = escape_markdown(str(cashout.cashout_id))
                    
                    # Display COMPLETE crypto address
                    destination_full = escape_markdown(cashout.destination)
                    
                    created_time = cashout.created_at.strftime("%Y-%m-%d %H:%M UTC")
                    risk_score_safe = escape_markdown(f"{cashout.risk_score:.3f}")
                    
                    risk_indicator = "🔴" if cashout.risk_score > 0.7 else "🟡" if cashout.risk_score > 0.3 else "🟢"
                    
                    message += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{i}. {risk_indicator} Cashout ID: `{cashout_id_safe}`
💰 Amount: ${cashout.amount:.2f} {escape_markdown(cashout.currency)}
🏦 Method: {escape_markdown(cashout.cashout_type)}
👤 User: {user_name_safe} (ID: {cashout.user_id})
📅 Created: {escape_markdown(created_time)}
⚠️ Risk Score: {risk_score_safe}
💸 Net Amount: ${cashout.net_amount:.2f}
💰 Total Fee: ${cashout.total_fee:.2f}
📍 FULL DESTINATION ADDRESS:
`{destination_full}`"""
                
                keyboard = [
                    [
                        InlineKeyboardButton(f"✅ Approve #{pending_cashouts[0].cashout_id}", callback_data=f"admin_approve_single_{pending_cashouts[0].cashout_id}"),
                        InlineKeyboardButton(f"❌ Decline #{pending_cashouts[0].cashout_id}", callback_data=f"admin_decline_single_{pending_cashouts[0].cashout_id}"),
                    ],
                    [
                        InlineKeyboardButton("✅ Approve All Shown", callback_data="admin_approve_shown"),
                        InlineKeyboardButton("❌ Decline All Shown", callback_data="admin_decline_shown"),
                    ],
                    [
                        InlineKeyboardButton("🔄 Refresh", callback_data="admin_detailed_review"),
                        InlineKeyboardButton("⬅️ Back to Review", callback_data="admin_cashout_pending"),
                    ],
                    [
                        InlineKeyboardButton("💰 Back to CashOuts", callback_data="admin_trans_cashouts"),
                        InlineKeyboardButton("🏠 Admin Main", callback_data="admin_main"),
                    ]
                ]
        finally:
            session.close()
        
        if query:
            await safe_edit_message_text(
                query,
                message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        
    except Exception as e:
        logger.error(f"Admin detailed review failed: {e}")
        if query:
            await safe_answer_callback_query(query, f"❌ Detailed review failed: {str(e)}", show_alert=True)
        return ConversationHandler.END

    return ConversationHandler.END


async def handle_admin_approve_single(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle individual cashout approval with transaction hash input and double confirmation"""
    logger.info(f"🔥 handle_admin_approve_single called by user {update.effective_user.id if update.effective_user else 'None'}")
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query)  # Acknowledge click
        await query.edit_message_text("⏳ Loading approval details...")  # Instant visual feedback

    try:
        # Extract cashout_id from callback data
        callback_data = query.data
        if not callback_data.startswith("admin_approve_single_"):
            await safe_answer_callback_query(query, "❌ Invalid approval request", show_alert=True)
            return ConversationHandler.END
        
        cashout_id = callback_data.replace("admin_approve_single_", "")
        
        session = SessionLocal()
        try:
            # Get cashout details
            cashout = session.query(Cashout).filter(Cashout.cashout_id == cashout_id).first()
            
            if not cashout:
                await safe_answer_callback_query(query, "❌ Cashout not found", show_alert=True)
                return ConversationHandler.END
            
            user_obj = session.query(User).filter(User.id == cashout.user_id).first()
            user_name_safe = escape_markdown(user_obj.first_name if user_obj else 'Unknown')
            cashout_id_safe = escape_markdown(str(cashout.cashout_id))
            destination_full = escape_markdown(cashout.destination)
            
            # Get recent transactions (last 3)
            recent_transactions = session.query(Transaction).filter(
                Transaction.user_id == cashout.user_id
            ).order_by(Transaction.created_at.desc()).limit(3).all()
            
            # Get recent escrow ratings received by this user
            recent_ratings = session.query(Rating).filter(
                Rating.rated_id == cashout.user_id
            ).order_by(Rating.created_at.desc()).limit(3).all()
            
            # Build transaction history section
            transaction_history = ""
            if recent_transactions:
                transaction_history = "\n📊 Recent Transactions:\n"
                for tx in recent_transactions:
                    tx_type = tx.transaction_type.capitalize()
                    tx_amount = f"${tx.amount:.2f} {tx.currency}"
                    tx_date = tx.created_at.strftime("%m/%d")
                    tx_status = tx.status.upper()
                    transaction_history += f"• {tx_date}: {tx_type} {tx_amount} ({tx_status})\n"
            else:
                transaction_history = "\n📊 Recent Transactions: None\n"
            
            # Build ratings section
            ratings_info = ""
            if recent_ratings:
                avg_rating = sum(r.rating for r in recent_ratings) / len(recent_ratings)
                ratings_info = f"\n⭐ Escrow Ratings: {avg_rating:.1f}/5 ({len(recent_ratings)} recent)\n"
                for rating in recent_ratings:
                    stars = "⭐" * rating.rating
                    rater_name = session.query(User).filter(User.id == rating.rater_id).first()
                    rater_display = rater_name.first_name[:8] if rater_name else "Unknown"
                    ratings_info += f"• {stars} by {rater_display} ({rating.category})\n"
            else:
                ratings_info = "\n⭐ Escrow Ratings: No ratings yet\n"
            
            # Show detailed confirmation with OTP verification status
            otp_status = "✅ Verified" if cashout.otp_verified else "❌ Not Verified"
            message = f"""💳 CASHOUT #{cashout_id_safe} 
👤 {user_name_safe} • ${cashout.amount:.2f} {escape_markdown(cashout.currency)}

⚠️ ADMIN APPROVAL CONFIRMATION

🔍 Cashout Details:
• Method: {escape_markdown(cashout.cashout_type)}
• Destination: `{destination_full}`
• Risk Score: {cashout.risk_score:.3f}
• OTP Status: {otp_status}{transaction_history}{ratings_info}
💸 Financial Impact:
• Wallet Debit: ${cashout.amount:.2f}
• Total Fee: ${cashout.total_fee:.2f}
• Net to User: ${cashout.net_amount:.2f}

⚠️ DOUBLE CONFIRMATION REQUIRED:
1. This will IMMEDIATELY debit user's wallet
2. External transfer will be initiated automatically
3. Action CANNOT be undone

📝 Enter blockchain transaction hash (if manual processing):"""
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ CONFIRM APPROVE", callback_data=f"admin_confirm_approve_{cashout_id}"),
                    InlineKeyboardButton("❌ DECLINE", callback_data=f"admin_decline_single_{cashout_id}"),
                ],
                [
                    InlineKeyboardButton("📝 Enter TX Hash", callback_data=f"admin_enter_hash_{cashout_id}"),
                    InlineKeyboardButton("🔄 Auto Process", callback_data=f"admin_auto_process_{cashout_id}"),
                ],
                [
                    InlineKeyboardButton("⬅️ Back to Review", callback_data="admin_detailed_review"),
                    InlineKeyboardButton("🏠 Admin Main", callback_data="admin_main"),
                ]
            ]
        finally:
            session.close()
        
        if query:
            await safe_edit_message_text(
                query,
                message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        
    except Exception as e:
        logger.error(f"Admin single approval failed: {e}")
        if query:
            await safe_answer_callback_query(query, f"❌ Approval failed: {str(e)}", show_alert=True)
        return ConversationHandler.END

    return ConversationHandler.END


async def handle_admin_confirm_approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle final confirmation of cashout approval"""
    logger.info(f"🔥 handle_admin_confirm_approve called by user {update.effective_user.id if update.effective_user else 'None'}")
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query)  # Acknowledge click
        await query.edit_message_text("⏳ Processing approval...")  # Instant visual feedback

    try:
        # Extract cashout_id from callback data
        callback_data = query.data
        if not callback_data.startswith("admin_confirm_approve_"):
            await safe_answer_callback_query(query, "❌ Invalid confirmation request", show_alert=True)
            return ConversationHandler.END
        
        cashout_id = callback_data.replace("admin_confirm_approve_", "")
        
        # Process the cashout approval
        from services.auto_cashout import AutoCashoutService
        
        session = SessionLocal()
        try:
            # First approve the cashout
            cashout = session.query(Cashout).filter(Cashout.cashout_id == cashout_id).first()
            
            if not cashout:
                await safe_answer_callback_query(query, "❌ Cashout not found", show_alert=True)
                return ConversationHandler.END
            
            # Update cashout to approved status
            cashout.status = CashoutStatus.APPROVED.value
            cashout.admin_approved = True
            cashout.admin_id = user.id
            cashout.admin_approved_at = datetime.now(timezone.utc)
            session.commit()
            
            user_obj = session.query(User).filter(User.id == cashout.user_id).first()
            user_name_safe = escape_markdown(user_obj.first_name if user_obj else 'Unknown')
            
            # Process the approved cashout immediately
            result = await AutoCashoutService.process_approved_cashout(
                cashout_id=cashout_id,
                admin_approved=True
            )
            
            if result.get('success'):
                message = f"""✅ APPROVAL SUCCESSFUL

🎯 Cashout `{escape_markdown(cashout_id)}` approved and processed
👤 User: {user_name_safe}
💰 Amount: ${cashout.amount:.2f} {escape_markdown(cashout.currency)}
🔗 TX Hash: `{escape_markdown(result.get('tx_hash', 'Processing...'))}`

✅ Wallet balance debited successfully
✅ External transfer initiated
✅ User notified automatically"""
                
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Refresh Pending", callback_data="admin_cashout_pending"),
                        InlineKeyboardButton("📋 View Details", callback_data=f"admin_cashout_details_{cashout_id}"),
                    ],
                    [
                        InlineKeyboardButton("💰 Back to CashOuts", callback_data="admin_trans_cashouts"),
                        InlineKeyboardButton("🏠 Admin Main", callback_data="admin_main"),
                    ]
                ]
            else:
                error_msg = result.get('error', 'Unknown error')
                message = f"""❌ APPROVAL FAILED

🚨 Error processing cashout `{escape_markdown(cashout_id)}`
👤 User: {user_name_safe}
💰 Amount: ${cashout.amount:.2f} {escape_markdown(cashout.currency)}
❌ Error: {escape_markdown(error_msg)}

⚠️ Cashout marked as approved but processing failed
🔧 Manual intervention may be required"""
                
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Retry Processing", callback_data=f"admin_retry_processing_{cashout_id}"),
                        InlineKeyboardButton("❌ Mark Failed", callback_data=f"admin_mark_failed_{cashout_id}"),
                    ],
                    [
                        InlineKeyboardButton("💰 Back to CashOuts", callback_data="admin_trans_cashouts"),
                        InlineKeyboardButton("🏠 Admin Main", callback_data="admin_main"),
                    ]
                ]
        finally:
            session.close()
        
        if query:
            await safe_edit_message_text(
                query,
                message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        
    except Exception as e:
        logger.error(f"Admin confirm approval failed: {e}")
        if query:
            await safe_answer_callback_query(query, f"❌ Confirmation failed: {str(e)}", show_alert=True)
        return ConversationHandler.END

    return ConversationHandler.END


async def handle_admin_decline_single(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle declining a single cashout with reason"""
    logger.info(f"🔥 handle_admin_decline_single called by user {update.effective_user.id if update.effective_user else 'None'}")
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query)  # Acknowledge click
        await query.edit_message_text("⏳ Loading decline options...")  # Instant visual feedback

    try:
        # Extract cashout_id from callback data
        callback_data = query.data
        if not callback_data.startswith("admin_decline_single_"):
            await safe_answer_callback_query(query, "❌ Invalid decline request", show_alert=True)
            return ConversationHandler.END
        
        cashout_id = callback_data.replace("admin_decline_single_", "")
        
        session = SessionLocal()
        try:
            # Get cashout details
            cashout = session.query(Cashout).filter(Cashout.cashout_id == cashout_id).first()
            
            if not cashout:
                await safe_answer_callback_query(query, "❌ Cashout not found", show_alert=True)
                return ConversationHandler.END
            
            user_obj = session.query(User).filter(User.id == cashout.user_id).first()
            user_name_safe = escape_markdown(user_obj.first_name if user_obj else 'Unknown')
            cashout_id_safe = escape_markdown(str(cashout.cashout_id))
            
            message = f"""❌ DECLINE CASHOUT CONFIRMATION

🔍 Cashout to Decline:
• ID: `{cashout_id_safe}`
• User: {user_name_safe}
• Amount: ${cashout.amount:.2f} {escape_markdown(cashout.currency)}
• Destination: `{escape_markdown(cashout.destination[:50])}...`

⚠️ DECLINE ACTIONS:
1. Cashout will be marked as DECLINED
2. Locked funds will be released back to user wallet
3. User will be notified of decline
4. Action cannot be easily undone

📝 Select decline reason:"""
            
            keyboard = [
                [
                    InlineKeyboardButton("🚫 Insufficient Verification", callback_data=f"admin_decline_reason_{cashout_id}_verification"),
                    InlineKeyboardButton("⚠️ High Risk Transaction", callback_data=f"admin_decline_reason_{cashout_id}_risk"),
                ],
                [
                    InlineKeyboardButton("📍 Invalid Destination", callback_data=f"admin_decline_reason_{cashout_id}_destination"),
                    InlineKeyboardButton("💰 Suspicious Activity", callback_data=f"admin_decline_reason_{cashout_id}_suspicious"),
                ],
                [
                    InlineKeyboardButton("📝 Compliance Issue", callback_data=f"admin_decline_reason_{cashout_id}_compliance"),
                    InlineKeyboardButton("🔧 Technical Issue", callback_data=f"admin_decline_reason_{cashout_id}_technical"),
                ],
                [
                    InlineKeyboardButton("⬅️ Back to Approval", callback_data=f"admin_approve_single_{cashout_id}"),
                    InlineKeyboardButton("🏠 Admin Main", callback_data="admin_main"),
                ]
            ]
        finally:
            session.close()
        
        if query:
            await safe_edit_message_text(
                query,
                message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        
    except Exception as e:
        logger.error(f"Admin decline preparation failed: {e}")
        if query:
            await safe_answer_callback_query(query, f"❌ Decline failed: {str(e)}", show_alert=True)
        return ConversationHandler.END

    return ConversationHandler.END


async def handle_admin_decline_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cashout decline with specific reason"""
    logger.info(f"🔥 handle_admin_decline_reason called by user {update.effective_user.id if update.effective_user else 'None'}")
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query, "❌")

    try:
        # Parse callback data: admin_decline_reason_{cashout_id}_{reason}
        callback_data = query.data
        if not callback_data.startswith("admin_decline_reason_"):
            await safe_answer_callback_query(query, "❌ Invalid decline reason", show_alert=True)
            return ConversationHandler.END
        
        # Extract cashout_id and reason
        parts = callback_data.replace("admin_decline_reason_", "").rsplit("_", 1)
        if len(parts) != 2:
            await safe_answer_callback_query(query, "❌ Invalid decline format", show_alert=True)
            return ConversationHandler.END
        
        cashout_id, reason_code = parts
        
        # Map reason codes to human-readable reasons
        reason_map = {
            "verification": "Insufficient identity verification",
            "risk": "High-risk transaction detected",
            "destination": "Invalid or unverified destination address",
            "suspicious": "Suspicious account activity detected", 
            "compliance": "Compliance policy violation",
            "technical": "Technical processing issue"
        }
        
        decline_reason = reason_map.get(reason_code, "Administrative decision")
        
        session = SessionLocal()
        try:
            # Execute decline
            from services.auto_cashout import AutoCashoutService
            
            # Cancel the cashout and release funds
            result = await AutoCashoutService.cancel_cashout(
                cashout_id=cashout_id,
                reason=f"Admin declined: {decline_reason}"
            )
            
            cashout = session.query(Cashout).filter(Cashout.cashout_id == cashout_id).first()
            user_obj = session.query(User).filter(User.id == cashout.user_id).first() if cashout else None
            user_name_safe = escape_markdown(user_obj.first_name if user_obj else 'Unknown')
            
            if result.get('success'):
                message = f"""❌ CASHOUT DECLINED

✅ Successfully declined cashout `{escape_markdown(cashout_id)}`
👤 User: {user_name_safe}
💰 Amount: ${cashout.amount:.2f} released back to wallet
📝 Reason: {escape_markdown(decline_reason)}

✅ Locked funds released to user wallet
✅ User notified of decline
✅ Cashout marked as cancelled"""
                
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Refresh Pending", callback_data="admin_cashout_pending"),
                        InlineKeyboardButton("📋 View History", callback_data="admin_trans_cashouts"),
                    ],
                    [
                        InlineKeyboardButton("💰 Back to CashOuts", callback_data="admin_trans_cashouts"),
                        InlineKeyboardButton("🏠 Admin Main", callback_data="admin_main"),
                    ]
                ]
            else:
                error_msg = result.get('error', 'Unknown error')
                message = f"""❌ DECLINE FAILED

🚨 Error declining cashout `{escape_markdown(cashout_id)}`
👤 User: {user_name_safe}
❌ Error: {escape_markdown(error_msg)}

⚠️ Manual intervention required"""
                
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Retry Decline", callback_data=f"admin_decline_single_{cashout_id}"),
                        InlineKeyboardButton("🔧 Manual Review", callback_data=f"admin_approve_single_{cashout_id}"),
                    ],
                    [
                        InlineKeyboardButton("💰 Back to CashOuts", callback_data="admin_trans_cashouts"),
                        InlineKeyboardButton("🏠 Admin Main", callback_data="admin_main"),
                    ]
                ]
        finally:
            session.close()
        
        if query:
            await safe_edit_message_text(
                query,
                message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        
    except Exception as e:
        logger.error(f"Admin decline reason processing failed: {e}")
        if query:
            await safe_answer_callback_query(query, f"❌ Decline processing failed: {str(e)}", show_alert=True)
        return ConversationHandler.END

    return ConversationHandler.END


async def handle_admin_trans_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Advanced transaction analytics and insights"""
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query, "📈")

    try:
        session = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            
            # Volume analytics
            today_volume = session.query(func.sum(Escrow.amount)).filter(
                Escrow.created_at >= today
            ).scalar() or 0
            
            week_volume = session.query(func.sum(Escrow.amount)).filter(
                Escrow.created_at >= week_ago
            ).scalar() or 0
            
            month_volume = session.query(func.sum(Escrow.amount)).filter(
                Escrow.created_at >= month_ago
            ).scalar() or 0
            
            # Transaction count analytics
            today_count = session.query(Escrow).filter(Escrow.created_at >= today).count()
            week_count = session.query(Escrow).filter(Escrow.created_at >= week_ago).count()
            month_count = session.query(Escrow).filter(Escrow.created_at >= month_ago).count()
            
            # User activity
            active_users_today = session.query(func.count(func.distinct(Escrow.buyer_id))).filter(
                Escrow.created_at >= today
            ).scalar() or 0
            
            # Average transaction values
            avg_today = float(today_volume) / max(today_count, 1)
            avg_week = float(week_volume) / max(week_count, 1)
            
            message = f"""📈 Transaction Analytics

💰 Volume Analysis"
• Today: ${float(today_volume):,.2f} ({today_count} transactions)
• This Week: ${float(week_volume):,.2f} ({week_count} transactions)  
• This Month: ${float(month_volume):,.2f} ({month_count} transactions)

📊 Performance Metrics
• Average Today: ${avg_today:.2f}
• Average This Week: ${avg_week:.2f}
• Active Users Today: {active_users_today}

🎯 Key Insights"""
            
            # Growth calculations
            if week_count > 0 and month_count > week_count:
                weekly_growth = ((week_count - (month_count - week_count)) / max(month_count - week_count, 1)) * 100
                message += f"\n• Weekly Growth: {weekly_growth:+.1f}%"
            
            if today_count > 0 and week_count > today_count:
                daily_performance = (today_count / (week_count / 7)) * 100
                message += f"\n• Today vs Avg: {daily_performance:.0f}%"
            
            message += f"\n\n📅 Generated: {now.strftime('%H:%M UTC')}"
            
        finally:
            session.close()
        
        keyboard = [
            [
                InlineKeyboardButton("📊 Detailed Report", callback_data="admin_analytics_detailed"),
                InlineKeyboardButton("📈 Growth Trends", callback_data="admin_analytics_growth"),
            ],
            [
                InlineKeyboardButton("💰 Transactions", callback_data="admin_transactions"),
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
        
    except Exception as e:
        logger.error(f"Admin transaction analytics failed: {e}")
        if query:
            await safe_answer_callback_query(query, f"❌ Analytics failed: {str(e)}", show_alert=True)
        return ConversationHandler.END

    return ConversationHandler.END


async def handle_admin_trans_exchanges(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Exchange transaction management"""
    logger.info(f"🔥 handle_admin_trans_exchanges called by user {update.effective_user.id if update.effective_user else 'None'}")
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query, "💱")

    try:
        session = SessionLocal()
        try:
            # Get recent exchanges
            recent_exchanges = session.query(ExchangeOrder).order_by(
                desc(ExchangeOrder.created_at)
            ).limit(10).all()
            
            total_exchanges = session.query(ExchangeOrder).count()
            total_volume = session.query(func.sum(ExchangeOrder.source_amount)).scalar() or 0
            
            message = f"""💱 Exchange Management

📊 Overview
• Total Exchanges: {total_exchanges:,}
• Total Volume: ${float(total_volume):,.2f}

🔄 Recent Activity"""
            
            if recent_exchanges:
                for exchange in recent_exchanges[-5:]:
                    # Ensure exchange.created_at is timezone-aware for subtraction
                    created_at = exchange.created_at.replace(tzinfo=timezone.utc) if exchange.created_at.tzinfo is None else exchange.created_at
                    age = (datetime.now(timezone.utc) - created_at).days
                    message += f"\n• ${exchange.source_amount:.2f} {exchange.source_amount}→{exchange.target_currency} • {age}d ago"
            else:
                message += "\n📝 No recent exchanges"
                
        finally:
            session.close()
        
        keyboard = [
            [
                InlineKeyboardButton("💰 Transactions", callback_data="admin_transactions"),
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
        
    except Exception as e:
        logger.error(f"Admin exchange transactions failed: {e}")
        if query:
            await safe_answer_callback_query(query, f"❌ Exchange details failed: {str(e)}", show_alert=True)
        return ConversationHandler.END

    return ConversationHandler.END


async def handle_admin_retry_processing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle retrying failed cashout processing"""
    logger.info(f"🔥 handle_admin_retry_processing called by user {update.effective_user.id if update.effective_user else 'None'}")
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query, "🔄")

    try:
        # Extract cashout_id from callback data
        callback_data = query.data
        if not callback_data.startswith("admin_retry_processing_"):
            await safe_answer_callback_query(query, "❌ Invalid retry request", show_alert=True)
            return ConversationHandler.END
        
        cashout_id = callback_data.replace("admin_retry_processing_", "")
        
        session = SessionLocal()
        try:
            # Get cashout details
            cashout = session.query(Cashout).filter(Cashout.cashout_id == cashout_id).first()
            
            if not cashout:
                await safe_answer_callback_query(query, "❌ Cashout not found", show_alert=True)
                return ConversationHandler.END
            
            user_obj = session.query(User).filter(User.id == cashout.user_id).first()
            user_name_safe = escape_markdown(user_obj.first_name if user_obj else 'Unknown')
            
            # Reset cashout status to admin_pending for retry (required by process_approved_cashout)
            # SECURITY: Validate state transition to prevent overwriting terminal states
            try:
                current_status = CashoutStatus(cashout.status)
                CashoutStateValidator.validate_transition(
                    current_status, 
                    CashoutStatus.ADMIN_PENDING, 
                    str(cashout.cashout_id)
                )
                cashout.status = 'admin_pending'
                cashout.processed_at = None
                cashout.tx_hash = None
                session.commit()
            except Exception as validation_error:
                logger.error(
                    f"🚫 ADMIN_RETRY_BLOCKED: {current_status}→ADMIN_PENDING for {cashout_id}: {validation_error}"
                )
                await safe_answer_callback_query(
                    query, 
                    f"❌ Invalid state transition: {current_status.value}→ADMIN_PENDING. Cashout may already be completed.",
                    show_alert=True
                )
                return ConversationHandler.END
            
            logger.info(f"✅ Admin {user.id} reset cashout {cashout_id} for retry")
            
            # Import and retry the cashout processing
            from services.auto_cashout import AutoCashoutService
            
            logger.info(f"🔄 Starting retry processing for cashout {cashout_id}")
            # Create a retry processing request
            result = await AutoCashoutService.process_approved_cashout(
                cashout_id=cashout_id,
                admin_approved=True
            )
            logger.info(f"🔄 Retry processing result for {cashout_id}: {result}")
            
            if result.get('success'):
                message = f"""✅ RETRY SUCCESSFUL
            
🎯 Cashout `{escape_markdown(cashout_id)}` processed successfully
👤 User: {user_name_safe}
💰 Amount: ${cashout.amount:.2f} {escape_markdown(cashout.currency)}
🔗 TX Hash: `{escape_markdown(result.get('tx_hash', 'Processing...'))}`

✅ Processing completed on retry
✅ User notified automatically"""
                
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Refresh Pending", callback_data="admin_cashout_pending"),
                        InlineKeyboardButton("📋 View Details", callback_data=f"admin_cashout_details_{cashout_id}"),
                    ],
                    [
                        InlineKeyboardButton("💰 Back to CashOuts", callback_data="admin_trans_cashouts"),
                        InlineKeyboardButton("🏠 Admin Main", callback_data="admin_main"),
                    ]
                ]
            else:
                error_msg = result.get('error', 'Unknown error')
                message = f"""❌ RETRY FAILED
                
🚨 Cashout `{escape_markdown(cashout_id)}` failed again
👤 User: {user_name_safe}
💰 Amount: ${cashout.amount:.2f} {escape_markdown(cashout.currency)}
❌ Error: {escape_markdown(error_msg)}

⚠️ Multiple processing attempts failed
🔧 Consider marking as failed or manual processing"""
                
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Retry Again", callback_data=f"admin_retry_processing_{cashout_id}"),
                        InlineKeyboardButton("❌ Mark Failed", callback_data=f"admin_mark_failed_{cashout_id}"),
                    ],
                    [
                        InlineKeyboardButton("💰 Back to CashOuts", callback_data="admin_trans_cashouts"),
                        InlineKeyboardButton("🏠 Admin Main", callback_data="admin_main"),
                    ]
                ]
                
        finally:
            session.close()
        
        if query:
            await safe_edit_message_text(
                query,
                message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        
    except Exception as e:
        logger.error(f"Admin retry processing failed: {e}")
        if query:
            await safe_answer_callback_query(query, f"❌ Retry failed: {str(e)}", show_alert=True)
        return ConversationHandler.END

    return ConversationHandler.END


async def handle_admin_mark_failed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle marking a cashout as permanently failed"""
    logger.info(f"🔥 handle_admin_mark_failed called by user {update.effective_user.id if update.effective_user else 'None'}")
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query, "❌")

    try:
        # Extract cashout_id from callback data
        callback_data = query.data
        if not callback_data.startswith("admin_mark_failed_"):
            await safe_answer_callback_query(query, "❌ Invalid request", show_alert=True)
            return ConversationHandler.END
        
        cashout_id = callback_data.replace("admin_mark_failed_", "")
        
        session = SessionLocal()
        try:
            # Get cashout details
            cashout = session.query(Cashout).filter(Cashout.cashout_id == cashout_id).first()
            
            if not cashout:
                await safe_answer_callback_query(query, "❌ Cashout not found", show_alert=True)
                return ConversationHandler.END
            
            user_obj = session.query(User).filter(User.id == cashout.user_id).first()
            user_name_safe = escape_markdown(user_obj.first_name if user_obj else 'Unknown')
            
            # Mark cashout as failed and refund user
            # SECURITY: Validate state transition to prevent overwriting terminal states
            try:
                current_status = CashoutStatus(cashout.status)
                CashoutStateValidator.validate_transition(
                    current_status, 
                    CashoutStatus.FAILED, 
                    str(cashout.cashout_id)
                )
                cashout.status = 'failed'
                cashout.processed_at = datetime.now(timezone.utc)
                session.commit()
            except Exception as validation_error:
                logger.error(
                    f"🚫 ADMIN_FAIL_BLOCKED: {current_status}→FAILED for {cashout_id}: {validation_error}"
                )
                await safe_answer_callback_query(
                    query, 
                    f"❌ Invalid state transition: {current_status.value}→FAILED. Cashout may already be in a terminal state.",
                    show_alert=True
                )
                return ConversationHandler.END
            
            # Refund the user's wallet
            from services.idempotent_refund_service import IdempotentRefundService
            refund_result = await IdempotentRefundService.process_cashout_refund(
                cashout_id=cashout_id,
                admin_initiated=True
            )
            
            logger.info(f"✅ Admin {user.id} marked cashout {cashout_id} as failed and initiated refund")
            
            if refund_result.get('success'):
                message = f"""✅ CASHOUT MARKED AS FAILED
                
🚨 Cashout `{escape_markdown(cashout_id)}` marked as failed
👤 User: {user_name_safe}
💰 Amount: ${cashout.amount:.2f} {escape_markdown(cashout.currency)}

✅ User wallet refunded: ${cashout.amount:.2f}
✅ User notified of refund
✅ Transaction closed"""
            else:
                message = f"""⚠️ CASHOUT FAILED - REFUND ISSUE
                
🚨 Cashout `{escape_markdown(cashout_id)}` marked as failed
👤 User: {user_name_safe}
💰 Amount: ${cashout.amount:.2f} {escape_markdown(cashout.currency)}

❌ Refund failed: {escape_markdown(refund_result.get('error', 'Unknown error'))}
🔧 Manual refund may be required"""
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh Pending", callback_data="admin_cashout_pending"),
                    InlineKeyboardButton("📋 View Failed", callback_data="admin_cashout_failed"),
                ],
                [
                    InlineKeyboardButton("💰 Back to CashOuts", callback_data="admin_trans_cashouts"),
                    InlineKeyboardButton("🏠 Admin Main", callback_data="admin_main"),
                ]
            ]
                
        finally:
            session.close()
        
        if query:
            await safe_edit_message_text(
                query,
                message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        
    except Exception as e:
        logger.error(f"Admin mark failed operation failed: {e}")
        if query:
            await safe_answer_callback_query(query, f"❌ Operation failed: {str(e)}", show_alert=True)
        return ConversationHandler.END

    return ConversationHandler.END


async def handle_admin_trans_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Quick admin transaction actions"""
    logger.info(f"🔥 handle_admin_trans_actions called by user {update.effective_user.id if update.effective_user else 'None'}")
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query, "⚡")

    message = f"""⚡ Quick Actions

🔧 Transaction Operations
• Bulk transaction management
• Emergency controls
• System maintenance

📊 Quick Stats
• Real-time monitoring
• Alert management
• Performance tools"""
        
    keyboard = [
        [
            InlineKeyboardButton("🔍 Bulk Review", callback_data="admin_bulk_review"),
            InlineKeyboardButton("⚠️ Emergency Stop", callback_data="admin_emergency"),
        ],
        [
            InlineKeyboardButton("💰 Transactions", callback_data="admin_transactions"),
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

    return ConversationHandler.END