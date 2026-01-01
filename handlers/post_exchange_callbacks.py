"""
Post Exchange Engagement Callback Handlers
Handles user interactions for post-exchange engagement features
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database import SessionLocal
from models import ExchangeOrder, User
from utils.callback_utils import safe_edit_message_text, safe_answer_callback_query
from services.post_exchange_engagement import PostExchangeEngagementService
from config import Config
from services.auto_refresh_service import auto_refresh_service

logger = logging.getLogger(__name__)


async def handle_exchange_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle exchange experience rating"""
    query = update.callback_query
    if not query or not query.data:
        return

    await safe_answer_callback_query(query, "⭐")

    try:
        # Extract exchange_id and rating from callback data
        # Format: rate_exchange_{exchange_id}_{rating}
        data_parts = query.data.split("_")
        if len(data_parts) < 4:
            return

        exchange_id = "_".join(data_parts[2:-1])  # Handle exchange_ids with underscores
        rating = int(data_parts[-1])

        # Store rating (you might want to add a rating field to ExchangeOrder model)
        session = SessionLocal()
        try:
            exchange = (
                session.query(ExchangeOrder)
                .filter(ExchangeOrder.id == exchange_id)  # Using id, not exchange_id
                .first()
            )
            
            if exchange:
                # For now, log the rating. You could add a rating field to the model later
                logger.info(f"User rated exchange {exchange_id} with {rating} stars")

                # Show thank you message
                thank_you_text = f"""⭐ Thank you for your {rating}-star rating!

Your feedback helps us improve {Config.PLATFORM_NAME}.

{"🎉 We're thrilled you had a great experience!" if rating >= 4 else "💪 We're working hard to improve your experience!"}

What would you like to do next?"""

                keyboard = []
                
                # First row - conditionally add exchange button
                first_row = []
                if Config.ENABLE_EXCHANGE_FEATURES:
                    first_row.append(
                        InlineKeyboardButton(
                            "🔄 Quick Exchange", callback_data="start_exchange"
                        )
                    )
                first_row.append(
                    InlineKeyboardButton(
                        "📊 View Stats", callback_data=f"view_exchange_stats_{exchange.user_id}"
                    )
                )
                keyboard.append(first_row)
                
                keyboard.append([
                    InlineKeyboardButton(
                        "🏆 Achievements", callback_data=f"view_achievements_{exchange.user_id}"
                    )
                ])

                await safe_edit_message_text(
                    query, thank_you_text, reply_markup=InlineKeyboardMarkup(keyboard)
                )

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Error handling exchange rating: {e}")
        await safe_edit_message_text(
            query, "❌ Error processing rating. Thank you for your feedback!"
        )


async def handle_view_savings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle view savings details"""
    query = update.callback_query
    if not query or not query.data:
        return

    await safe_answer_callback_query(query, "💰")

    try:
        # Extract exchange_id from callback data
        exchange_id = query.data.replace("view_savings_", "")

        session = SessionLocal()
        try:
            exchange = (
                session.query(ExchangeOrder)
                .filter(ExchangeOrder.id == exchange_id)
                .first()
            )
            
            if not exchange:
                await safe_edit_message_text(query, "❌ Exchange not found.")
                return

            # Calculate detailed savings
            source_amount = float(getattr(exchange, "from_amount", 0))
            target_amount = float(getattr(exchange, "to_amount", 0))
            exchange_type = getattr(exchange, "exchange_type", "")
            
            savings_info = PostExchangeEngagementService._calculate_savings(
                source_amount, target_amount, exchange_type
            )

            # Calculate competitor comparison
            if exchange_type == "crypto_to_ngn":
                competitor_fee = max(2.0, target_amount * 0.08)  # 8% typical competitor
                our_fee = target_amount * (float(Config.EXCHANGE_MARKUP_PERCENTAGE) / 100)
                amount_display = f"₦{target_amount:,.0f}"
            else:
                competitor_fee = max(2.0, source_amount * 0.05)  # 5% typical competitor
                our_fee = source_amount * (float(Config.EXCHANGE_MARKUP_PERCENTAGE) / 100)
                amount_display = f"₦{source_amount:,.0f}"

            savings_text = f"""💰 Your Savings Breakdown

Exchange: {amount_display}
Type: {exchange_type.replace('_', ' ').title()}

Fee Comparison:
• {Config.PLATFORM_NAME}: {savings_info['currency']}{our_fee:,.2f} ({Config.EXCHANGE_MARKUP_PERCENTAGE}%)
• Typical Competitor: {savings_info['currency']}{competitor_fee:,.2f} (8%+)

🎉 You saved: {savings_info['currency']}{savings_info['amount']:,.0f}

Why choose {Config.PLATFORM_NAME}?
• Transparent, low fees
• Real-time rate locking
• Fast processing (5-10 minutes)
• Secure & regulated

Ready for another exchange?"""

            keyboard = []
            
            # First row - conditionally add exchange button
            first_row = []
            if Config.ENABLE_EXCHANGE_FEATURES:
                first_row.append(
                    InlineKeyboardButton(
                        "💱 New Exchange", callback_data="direct_exchange"
                    )
                )
            first_row.append(
                InlineKeyboardButton(
                    "📈 Rate Comparison", callback_data="exchange_help"
                )
            )
            keyboard.append(first_row)
            
            keyboard.append([
                InlineKeyboardButton(
                    "🏆 View Achievements", callback_data=f"view_achievements_{exchange.user_id}"
                )
            ])

            await safe_edit_message_text(
                query, savings_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML"
            )

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Error handling view savings: {e}")
        await safe_edit_message_text(query, "❌ Error loading savings details.")


async def handle_view_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle view achievements"""
    query = update.callback_query
    if not query or not query.data:
        return

    await safe_answer_callback_query(query, "🏆")

    try:
        # Extract user_id from callback data
        user_id = int(query.data.replace("view_achievements_", ""))

        session = SessionLocal()
        try:
            # Count user's completed exchanges
            exchange_count = (
                session.query(ExchangeOrder)
                .filter(
                    ExchangeOrder.user_id == user_id,
                    ExchangeOrder.status == "completed"
                )
                .count()
            )

            # Calculate total savings
            exchanges = (
                session.query(ExchangeOrder)
                .filter(
                    ExchangeOrder.user_id == user_id,
                    ExchangeOrder.status == "completed"
                )
                .all()
            )

            total_savings = 0
            for ex in exchanges:
                source_amount = float(getattr(ex, "from_amount", 0))
                target_amount = float(getattr(ex, "to_amount", 0))
                exchange_type = getattr(ex, "exchange_type", "")
                savings = PostExchangeEngagementService._calculate_savings(
                    source_amount, target_amount, exchange_type
                )
                total_savings += savings["amount"]

            # Get achievement info
            achievement_info = PostExchangeEngagementService._get_achievement_level(exchange_count)
            next_achievements = PostExchangeEngagementService._get_next_achievements(exchange_count)

            achievements_text = f"""🏆 Your Achievements

Current Status:
{achievement_info['emoji']} {achievement_info['title']}
{achievement_info['message']}

Your Stats:
💱 {exchange_count} successful exchange{"s" if exchange_count != 1 else ""}**
💰 ₦{total_savings:,.0f} total savings

Next Milestones:
{next_achievements}

Achievement Levels:
🥉 Bronze Exchanger (1+ exchanges)
🥈 Silver Exchanger (5+ exchanges)  
🥇 Gold Exchanger (20+ exchanges)
💎 Diamond Exchanger (50+ exchanges)

Keep trading to unlock more achievements!"""

            keyboard = []
            
            # First row - conditionally add exchange button
            first_row = []
            if Config.ENABLE_EXCHANGE_FEATURES:
                first_row.append(
                    InlineKeyboardButton(
                        "💱 New Exchange", callback_data="direct_exchange"
                    )
                )
            first_row.append(
                InlineKeyboardButton(
                    "📊 Full Stats", callback_data=f"view_exchange_stats_{user_id}"
                )
            )
            keyboard.append(first_row)
            
            keyboard.append([
                InlineKeyboardButton(
                    "🔙 Back", callback_data="main_menu"
                )
            ])

            await safe_edit_message_text(
                query, achievements_text, reply_markup=InlineKeyboardMarkup(keyboard)
            )

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Error handling view achievements: {e}")
        await safe_edit_message_text(query, "❌ Error loading achievements.")


async def handle_view_exchange_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle view detailed exchange statistics"""
    query = update.callback_query
    if not query or not query.data:
        return

    await safe_answer_callback_query(query, "📊")

    try:
        # Extract user_id from callback data
        user_id = int(query.data.replace("view_exchange_stats_", ""))

        session = SessionLocal()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                await safe_edit_message_text(query, "❌ User not found.")
                return

            # Get all completed exchanges
            exchanges = (
                session.query(ExchangeOrder)
                .filter(
                    ExchangeOrder.user_id == user_id,
                    ExchangeOrder.status == "completed"
                )
                .order_by(ExchangeOrder.completed_at.desc())
                .all()
            )

            if not exchanges:
                stats_text = f"""📊 Your Exchange Statistics

Welcome to {Config.PLATFORM_NAME}!

You haven't completed any exchanges yet.
Start your first exchange to unlock detailed statistics!

💡 **Benefits of exchanging with us:**
• Lowest fees in the market
• Real-time rate protection
• Lightning-fast processing
• 24/7 support"""
            else:
                # Calculate comprehensive stats
                total_exchanges = len(exchanges)
                total_volume = sum(float(getattr(ex, "from_amount", 0)) for ex in exchanges)
                total_savings = 0
                crypto_to_ngn_count = 0
                ngn_to_crypto_count = 0

                for ex in exchanges:
                    exchange_type = getattr(ex, "exchange_type", "")
                    if exchange_type == "crypto_to_ngn":
                        crypto_to_ngn_count += 1
                    else:
                        ngn_to_crypto_count += 1

                    source_amount = float(getattr(ex, "from_amount", 0))
                    target_amount = float(getattr(ex, "to_amount", 0))
                    savings = PostExchangeEngagementService._calculate_savings(
                        source_amount, target_amount, exchange_type
                    )
                    total_savings += savings["amount"]

                # Get achievement info
                achievement_info = PostExchangeEngagementService._get_achievement_level(total_exchanges)
                
                # Calculate average completion time (if available)
                avg_completion = "5-10 minutes"  # Default estimate

                stats_text = f"""📊 Your Exchange Statistics

**Overall Performance:**
🏆 **Status:** {achievement_info['emoji']} {achievement_info['title']}
💱 **Total Exchanges:** {total_exchanges}
💰 **Total Volume:** ${total_volume:,.2f}
💸 **Total Savings:** ₦{total_savings:,.0f}

**Exchange Breakdown:**
📈 **Crypto → NGN:** {crypto_to_ngn_count} exchanges
📉 **NGN → Crypto:** {ngn_to_crypto_count} exchanges

**Performance:**
⚡ **Avg Completion:** {avg_completion}
🎯 **Success Rate:** 100%

**Recent Activity:**
📅 **Last Exchange:** {exchanges[0].completed_at.strftime('%Y-%m-%d') if exchanges else 'N/A'}

You're doing great! Keep trading to unlock more achievements."""

            keyboard = []
            
            # First row - conditionally add exchange button
            first_row = []
            if Config.ENABLE_EXCHANGE_FEATURES:
                first_row.append(
                    InlineKeyboardButton(
                        "💱 New Exchange", callback_data="direct_exchange"
                    )
                )
            first_row.append(
                InlineKeyboardButton(
                    "🏆 Achievements", callback_data=f"view_achievements_{user_id}"
                )
            )
            keyboard.append(first_row)
            
            keyboard.append([
                InlineKeyboardButton(
                    "🔙 Back", callback_data="main_menu"
                )
            ])

            await safe_edit_message_text(
                query, stats_text, reply_markup=InlineKeyboardMarkup(keyboard)
            )

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Error handling view exchange stats: {e}")
        await safe_edit_message_text(query, "❌ Error loading statistics.")


async def handle_view_exchange(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle view exchange order details"""
    query = update.callback_query
    if not query or not query.data:
        return

    await safe_answer_callback_query(query, "🔄")

    try:
        # Extract exchange_id from callback data
        exchange_id = int(query.data.replace("view_exchange_", ""))
        
        session = SessionLocal()
        try:
            from models import ExchangeOrder
            
            exchange = session.query(ExchangeOrder).filter(ExchangeOrder.id == exchange_id).first()
            if not exchange:
                await query.edit_message_text("❌ Exchange order not found")
                return
            
            # Create exchange details view
            status_emoji = {
                'created': '📋',
                'awaiting_deposit': '⏳',
                'payment_received': '💰',
                'processing': '⚡',
                'completed': '✅',
                'failed': '❌',
                'cancelled': '🚫'
            }.get(exchange.status, '📋')
            
            # Format amounts
            source_amount = getattr(exchange, 'source_amount', 0)
            final_amount = getattr(exchange, 'final_amount', 0)
            source_currency = getattr(exchange, 'source_currency', 'USD')
            target_currency = getattr(exchange, 'target_currency', 'NGN')
            
            details_text = f"{status_emoji} *Exchange Order Details*\n\n"
            details_text += f"*Order:* #{getattr(exchange, 'utid', 'N/A')}\n"
            
            # Escape underscores in status to prevent Markdown conflicts
            status_display = exchange.status.replace('_', ' ').title()
            details_text += f"*Status:* {status_display}\n"
            details_text += f"*Amount:* {source_amount:.4f} {source_currency} → "
            
            if target_currency == 'NGN':
                details_text += f"₦{final_amount:,.2f}\n"
            else:
                details_text += f"{final_amount:.4f} {target_currency}\n"
                
            # Comprehensive timestamp formatting matching escrow implementation
            def format_timestamp(timestamp, default="Unknown"):
                """Format timestamp in user-friendly format matching escrow display"""
                if timestamp:
                    try:
                        return timestamp.strftime("%b %d, %Y %I:%M %p")
                    except (AttributeError, ValueError):
                        return default
                return default
            
            # Build comprehensive timestamp information based on exchange status
            timestamp_info = ""
            
            # 1. Always show creation time
            created_at = getattr(exchange, 'created_at', None)
            created_display = format_timestamp(created_at, "Unknown")
            timestamp_info += f"\n🕐 *Created:* {created_display}"
            
            # 2. Add status-specific timestamps
            if exchange.status == 'completed':
                completed_at = getattr(exchange, 'completed_at', None)
                if completed_at:
                    completed_display = format_timestamp(completed_at)
                    timestamp_info += f"\n✅ *Completed:* {completed_display}"
                    
            elif exchange.status in ['failed', 'cancelled']:
                # For failed/cancelled exchanges, show when failure/cancellation occurred
                failed_at = getattr(exchange, 'completed_at', None) or getattr(exchange, 'updated_at', None)
                if failed_at:
                    failed_display = format_timestamp(failed_at)
                    emoji = "❌" if exchange.status == 'failed' else "🚫"
                    status_label = "Failed" if exchange.status == 'failed' else "Cancelled"
                    timestamp_info += f"\n{emoji} *{status_label}:* {failed_display}"
                    
            elif exchange.status == 'processing':
                # Show when processing started (rate locked time)
                rate_locked_at = getattr(exchange, 'rate_locked_at', None)
                if rate_locked_at:
                    processing_display = format_timestamp(rate_locked_at)
                    timestamp_info += f"\n⚡ *Processing Started:* {processing_display}"
                    
            # 3. Add rate lock information for relevant statuses
            if exchange.status in ['created', 'awaiting_deposit', 'processing']:
                rate_locked_at = getattr(exchange, 'rate_locked_at', None)
                rate_lock_expires_at = getattr(exchange, 'rate_lock_expires_at', None)
                
                if rate_locked_at and exchange.status != 'processing':  # Don't duplicate for processing
                    locked_display = format_timestamp(rate_locked_at)
                    timestamp_info += f"\n🔒 *Rate Locked:* {locked_display}"
                    
                if rate_lock_expires_at:
                    expiry_display = format_timestamp(rate_lock_expires_at)
                    # Check if rate lock is still valid
                    from datetime import datetime, timezone
                    current_time = datetime.now(timezone.utc)
                    if rate_lock_expires_at > current_time:
                        timestamp_info += f"\n⏰ *Rate Valid Until:* {expiry_display}"
                    else:
                        timestamp_info += f"\n⏰ *Rate Expired:* {expiry_display}"
                        
            # 4. Add order expiry information for active orders
            if exchange.status in ['created', 'awaiting_deposit', 'processing']:
                expires_at = getattr(exchange, 'expires_at', None)
                if expires_at:
                    expiry_display = format_timestamp(expires_at)
                    # Check if order is still valid
                    from datetime import datetime, timezone
                    current_time = datetime.now(timezone.utc)
                    if expires_at > current_time:
                        timestamp_info += f"\n⏳ *Order Expires:* {expiry_display}"
                    else:
                        timestamp_info += f"\n⏳ *Order Expired:* {expiry_display}"
                        
            # 5. Always show last updated time
            updated_at = getattr(exchange, 'updated_at', None)
            if updated_at:
                updated_display = format_timestamp(updated_at)
                timestamp_info += f"\n🔄 *Last Updated:* {updated_display}"
                
            # Add comprehensive timestamp information to details
            details_text += timestamp_info
            
            # Add bank reference if available
            if hasattr(exchange, 'bank_reference') and exchange.bank_reference:
                details_text += f"*Bank Ref:* {exchange.bank_reference}\n"
            
            # Create keyboard
            keyboard = []
            
            # Removed refresh button - auto-refresh implemented instead
            
            # Always add back button
            keyboard.append([
                InlineKeyboardButton("⬅️ Back to Messages", callback_data="trades_messages_hub")
            ])
            keyboard.append([
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
            ])
            
            message = await query.edit_message_text(
                details_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            
            # Register for auto-refresh if exchange is still active
            if exchange.status not in ['completed', 'failed', 'cancelled', 'expired']:
                auto_refresh_service.register_auto_refresh(
                    chat_id=query.message.chat_id,
                    message_id=message.message_id,
                    content_type='exchange_order',
                    content_id=str(exchange.id),
                    user_id=query.from_user.id
                )
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error viewing exchange details: {e}")
        await query.edit_message_text(
            "❌ Error loading exchange details",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back", callback_data="trades_messages_hub")
            ]])
        )


# Handler list for registration
POST_EXCHANGE_CALLBACK_HANDLERS = [
    # Exchange rating handlers
    ("rate_exchange_", handle_exchange_rating),
    # Savings and achievements handlers  
    ("view_savings_", handle_view_savings),
    ("view_achievements_", handle_view_achievements),
    ("view_exchange_stats_", handle_view_exchange_stats),
    ("view_exchange_", handle_view_exchange),  # Basic exchange view handler
]