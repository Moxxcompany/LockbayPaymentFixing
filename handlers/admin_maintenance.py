"""
Admin Maintenance Mode Control
Allows admins to enable/disable maintenance mode for the bot
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from config import Config
from utils.admin_security import is_admin_secure
from utils.callback_utils import safe_answer_callback_query

logger = logging.getLogger(__name__)


async def handle_admin_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to view/toggle maintenance mode"""
    if not update.effective_user:
        return
    user_id = update.effective_user.id
    
    if not update.message:
        return
    
    # DEBUG: Log admin check
    import os
    logger.info(f"🔍 ADMIN CHECK: User {user_id} attempting /maintenance")
    logger.info(f"🔍 ADMIN_IDS env: {repr(os.getenv('ADMIN_IDS', ''))}")
    
    is_admin = is_admin_secure(user_id)
    logger.info(f"🔍 is_admin_secure({user_id}) returned: {is_admin}")
    
    if not is_admin:
        logger.warning(f"⛔ ADMIN DENIED: User {user_id} was denied admin access")
        await update.message.reply_text("❌ Unauthorized. Admin access required.")
        return
    
    logger.info(f"✅ ADMIN GRANTED: User {user_id} has admin access")
    
    # Get current maintenance status
    is_maintenance = Config.get_maintenance_mode()
    current_status = "🔴 ENABLED" if is_maintenance else "🟢 DISABLED"
    
    keyboard = [
        [
            InlineKeyboardButton(
                "🔴 Enable Maintenance", 
                callback_data="maintenance_enable"
            ) if not is_maintenance else InlineKeyboardButton(
                "🟢 Disable Maintenance", 
                callback_data="maintenance_disable"
            )
        ],
        [InlineKeyboardButton("🔄 Refresh Status", callback_data="maintenance_status")]
    ]
    
    message = f"""
🛠️ **Maintenance Mode Control**

**Current Status:** {current_status}

**When ENABLED:**
✅ Admins have full access
❌ Regular users are blocked
📢 Users see maintenance message

**When DISABLED:**
✅ All users have access
✅ Normal bot operation
    """.strip()
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_maintenance_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle maintenance mode toggle buttons"""
    if not update.callback_query:
        return
    query = update.callback_query
    
    if not update.effective_user:
        return
    user_id = update.effective_user.id
    
    if not is_admin_secure(user_id):
        await safe_answer_callback_query(query, "❌ Unauthorized", show_alert=True)
        return
    
    await safe_answer_callback_query(query, "⏳ Processing...")
    
    action = query.data
    if not action:
        return
    
    if action == "maintenance_enable":
        # Show duration selection menu
        keyboard = [
            [
                InlineKeyboardButton("⏱️ 15 minutes", callback_data="maintenance_duration_15"),
                InlineKeyboardButton("⏱️ 30 minutes", callback_data="maintenance_duration_30")
            ],
            [
                InlineKeyboardButton("⏱️ 1 hour", callback_data="maintenance_duration_60"),
                InlineKeyboardButton("⏱️ 2 hours", callback_data="maintenance_duration_120")
            ],
            [
                InlineKeyboardButton("⏱️ 4 hours", callback_data="maintenance_duration_240"),
                InlineKeyboardButton("❓ Unspecified", callback_data="maintenance_duration_unspecified")
            ],
            [InlineKeyboardButton("« Back", callback_data="maintenance_status")]
        ]
        
        message = """
🛠️ **Enable Maintenance Mode**

⏱️ **Select estimated downtime:**

Choose how long you expect the maintenance to take. Users will see a countdown timer.

Select **Unspecified** if you don't know how long it will take.
        """.strip()
        
        try:
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to show duration menu: {e}")
            await safe_answer_callback_query(query, "❌ Failed to show duration menu", show_alert=True)
        return
        
    elif action.startswith("maintenance_duration_"):
        # Extract duration from callback data
        duration_str = action.replace("maintenance_duration_", "")
        
        if duration_str == "unspecified":
            duration_minutes = None
            duration_text = "Unspecified"
        else:
            duration_minutes = int(duration_str)
            if duration_minutes < 60:
                duration_text = f"{duration_minutes} minutes"
            else:
                hours = duration_minutes // 60
                duration_text = f"{hours} hour{'s' if hours > 1 else ''}"
        
        # Set duration and enable maintenance mode
        duration_success = Config.set_maintenance_duration(duration_minutes, admin_user_id=user_id)
        mode_success = Config.set_maintenance_mode(True, admin_user_id=user_id)
        
        if duration_success and mode_success:
            status_emoji = "🔴"
            status_text = "ENABLED"
            action_text = f"enabled with {duration_text} duration"
            logger.warning(f"🔴 MAINTENANCE MODE ENABLED ({duration_text}) by admin {user_id}")
        else:
            await query.edit_message_text("❌ Failed to enable maintenance mode. Check logs.")
            return
        
    elif action == "maintenance_disable":
        # Disable maintenance mode and clear duration
        mode_success = Config.set_maintenance_mode(False, admin_user_id=user_id)
        duration_success = Config.clear_maintenance_duration()
        
        if mode_success:
            status_emoji = "🟢"
            status_text = "DISABLED"
            action_text = "disabled"
            logger.warning(f"🟢 MAINTENANCE MODE DISABLED by admin {user_id}")
        else:
            await query.edit_message_text("❌ Failed to disable maintenance mode. Check logs.")
            return
    
    else:  # maintenance_status (refresh)
        is_maintenance = Config.get_maintenance_mode()
        status_emoji = "🔴" if is_maintenance else "🟢"
        status_text = "ENABLED" if is_maintenance else "DISABLED"
        action_text = "refreshed"
    
    # Update keyboard
    is_maintenance = Config.get_maintenance_mode()
    keyboard = [
        [
            InlineKeyboardButton(
                "🔴 Enable Maintenance", 
                callback_data="maintenance_enable"
            ) if not is_maintenance else InlineKeyboardButton(
                "🟢 Disable Maintenance", 
                callback_data="maintenance_disable"
            )
        ],
        [InlineKeyboardButton("🔄 Refresh Status", callback_data="maintenance_status")]
    ]
    
    message = f"""
🛠️ **Maintenance Mode Control**

**Status {action_text}:** {status_emoji} **{status_text}**

**When ENABLED:**
✅ Admins have full access
❌ Regular users are blocked
📢 Users see maintenance message

**When DISABLED:**
✅ All users have access
✅ Normal bot operation
    """.strip()
    
    try:
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Failed to update maintenance message: {e}")
        await safe_answer_callback_query(query, f"{status_emoji} Maintenance mode {action_text}!", show_alert=True)


async def handle_maintenance_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick status check command"""
    if not update.effective_user:
        return
    user_id = update.effective_user.id
    
    if not update.message:
        return
    
    if not is_admin_secure(user_id):
        await update.message.reply_text("❌ Unauthorized. Admin access required.")
        return
    
    is_maintenance = Config.get_maintenance_mode()
    status_emoji = "🔴" if is_maintenance else "🟢"
    status_text = "ENABLED" if is_maintenance else "DISABLED"
    
    message = f"{status_emoji} **Maintenance Mode:** {status_text}"
    
    await update.message.reply_text(message, parse_mode='Markdown')


def register_maintenance_handlers(application):
    """Register maintenance mode admin handlers"""
    application.add_handler(
        CommandHandler("maintenance", handle_admin_maintenance)
    )
    application.add_handler(
        CommandHandler("maintenance_status", handle_maintenance_status)
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_maintenance_toggle,
            pattern="^maintenance_(enable|disable|status|duration_.+)$"
        )
    )
    
    logger.info("✅ Maintenance mode handlers registered")
