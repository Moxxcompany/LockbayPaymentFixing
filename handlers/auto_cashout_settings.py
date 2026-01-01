"""
Auto Cashout Settings Handler
Handles automatic cashout configuration for users
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def complete_auto_cashout_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Complete auto cashout setup for a user
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    try:
        user = update.effective_user
        if not user:
            logger.warning("No effective user found for auto cashout setup")
            return
        
        logger.info(f"Completing auto cashout setup for user {user.id}")
        
        # Send confirmation message
        message = (
            "✅ **Auto Cashout Setup Complete!**\n\n"
            "Your automatic cashout preferences have been saved.\n"
            "You can modify these settings anytime from the main menu."
        )
        
        if update.callback_query:
            await update.callback_query.edit_message_text(message, parse_mode="Markdown")
        elif update.message:
            await update.message.reply_text(message, parse_mode="Markdown")
        
        # Return to main menu
        from handlers.start import show_main_menu
        await show_main_menu(update, context)
        
    except Exception as e:
        logger.error(f"Error completing auto cashout setup: {e}")
        
        error_message = "❌ Error completing auto cashout setup. Please try again later."
        
        if update.callback_query:
            await update.callback_query.edit_message_text(error_message)
        elif update.message:
            await update.message.reply_text(error_message)