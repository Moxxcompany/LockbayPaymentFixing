"""
Unified message handling utilities to prevent UI duplication
Supports both Update objects and direct user_id parameters for flexibility
"""
from telegram import Update, InlineKeyboardMarkup, Bot
from typing import Optional, Union
import logging
import os

from utils.callback_utils import safe_edit_message_text

logger = logging.getLogger(__name__)

# Global bot instance for direct user messaging
_bot_instance = None

def get_bot_instance() -> Bot:
    """Get or create the global bot instance"""
    global _bot_instance
    if _bot_instance is None:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
        _bot_instance = Bot(token=bot_token)
    return _bot_instance

async def send_unified_message(
    update_or_user_id: Union[Update, int], 
    text: str, 
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = None,
    **kwargs
) -> None:
    """
    Send message using the appropriate method based on input type.
    This prevents UI duplication by ensuring only one message is sent.
    
    Args:
        update_or_user_id: Either a Telegram Update object or user_id integer
        text: Message text to send
        reply_markup: Optional keyboard markup
        parse_mode: Optional parse mode (HTML, Markdown)
        **kwargs: Additional arguments for compatibility
    """
    try:
        # Handle Update object (legacy/existing usage)
        if isinstance(update_or_user_id, Update):
            update = update_or_user_id
            if update.callback_query:
                # Edit existing message
                await safe_edit_message_text(
                    update.callback_query, 
                    text, 
                    reply_markup=reply_markup, 
                    parse_mode=parse_mode
                )
            elif update.message:
                # Send new message
                await update.message.reply_text(
                    text, 
                    reply_markup=reply_markup, 
                    parse_mode=parse_mode
                )
            else:
                logger.warning("send_unified_message called with Update but no message or callback_query")
        
        # Handle direct user_id (Scene Engine usage)
        elif isinstance(update_or_user_id, int):
            user_id = update_or_user_id
            bot = get_bot_instance()
            await bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        
        else:
            logger.error(f"send_unified_message called with invalid type: {type(update_or_user_id)}")
    
    except Exception as e:
        logger.error(f"Error in send_unified_message: {e}")
        # Fallback handling
        try:
            if isinstance(update_or_user_id, Update) and update_or_user_id.message:
                await update_or_user_id.message.reply_text(text, parse_mode=None)
            elif isinstance(update_or_user_id, int):
                bot = get_bot_instance()
                await bot.send_message(chat_id=update_or_user_id, text=text)
        except Exception as fallback_error:
            logger.error(f"Fallback message send failed: {fallback_error}")

# Backward compatibility alias
async def send_message_unified(update: Update, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None, parse_mode: Optional[str] = None) -> None:
    """Backward compatibility function for existing code"""
    await send_unified_message(update, text, reply_markup, parse_mode)