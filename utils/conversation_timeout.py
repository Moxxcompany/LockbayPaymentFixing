"""
Universal Conversation Timeout Handler

Provides automatic cleanup for abandoned conversations after inactivity.
This prevents stale state by clearing all conversation data when users
leave conversations idle for too long.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

logger = logging.getLogger(__name__)

async def conversation_timeout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Universal timeout handler for all ConversationHandlers.
    
    This is called automatically when a conversation times out (user inactive).
    It clears all conversation state and gracefully returns the user to a clean state.
    
    Args:
        update: Telegram update object
        context: Telegram context object
        
    Returns:
        ConversationHandler.END: Ends the conversation
        
    Usage:
        ConversationHandler(
            conversation_timeout=600,  # 10 minutes
            fallbacks=[
                CommandHandler("cancel", cancel_handler)
            ],
            name="escrow_conversation",
            persistent=True,
            # This handler is called on timeout
            on_timeout=conversation_timeout_handler
        )
    """
    user = update.effective_user
    
    if not user:
        logger.warning("⏰ TIMEOUT: No user found in timeout handler")
        return ConversationHandler.END
    
    try:
        # Use unified cleanup function for consistent state clearing
        from utils.conversation_cleanup import clear_user_conversation_state
        
        cleanup_success = await clear_user_conversation_state(
            user_id=user.id,
            context=context,
            trigger="conversation_timeout"
        )
        
        if cleanup_success:
            logger.info(f"⏰ TIMEOUT: Cleaned up abandoned conversation for user {user.id}")
        else:
            logger.warning(f"⏰ TIMEOUT: Partial cleanup for user {user.id}")
        
        # Optionally notify user that their session timed out
        # (Only if update has a message or callback_query to reply to)
        try:
            if update.message:
                await update.message.reply_text(
                    "⏰ **Session Timeout**\n\n"
                    "Your conversation was inactive for too long and has been reset.\n\n"
                    "Use /start to return to the main menu.",
                    parse_mode="Markdown"
                )
            elif update.callback_query:
                await update.callback_query.message.reply_text(
                    "⏰ **Session Timeout**\n\n"
                    "Your conversation was inactive for too long and has been reset.\n\n"
                    "Use /start to return to the main menu.",
                    parse_mode="Markdown"
                )
        except Exception as notify_error:
            # Don't fail if notification fails - cleanup is more important
            logger.debug(f"Could not notify user of timeout: {notify_error}")
        
    except Exception as e:
        logger.error(f"❌ TIMEOUT: Cleanup failed for user {user.id}: {e}")
    
    return ConversationHandler.END


# Recommended timeout duration (in seconds)
CONVERSATION_TIMEOUT_DURATION = 600  # 10 minutes
CONVERSATION_TIMEOUT_DURATION_SHORT = 300  # 5 minutes (for sensitive operations)
CONVERSATION_TIMEOUT_DURATION_LONG = 1800  # 30 minutes (for complex flows)
