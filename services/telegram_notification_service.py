"""
Direct Telegram Notification Service - Simplified Architecture

Provides immediate Telegram messaging for wallet credits and deposits.
Part of the architect-approved direct notification flow.
"""

import logging
from telegram import Bot
from telegram.error import TelegramError
from config import Config

logger = logging.getLogger(__name__)

# Initialize bot instance
bot = Bot(token=Config.BOT_TOKEN)


def send_telegram_notification(user_id: int, message: str) -> bool:
    """
    Send immediate Telegram notification to user.
    
    Args:
        user_id: Database user ID  
        message: Text message to send
        
    Returns:
        True if sent successfully, False otherwise
    """
    try:
        # Get Telegram chat ID from user_id
        # For now, assume user_id is the telegram_id (this may need adjustment)
        telegram_id = user_id
        
        # Send message directly
        bot.send_message(chat_id=telegram_id, text=message)
        
        logger.info(f"✅ TELEGRAM_SENT: user={user_id}")
        return True
        
    except TelegramError as e:
        logger.error(f"❌ TELEGRAM_ERROR: user={user_id}, error={e}")
        return False
    except Exception as e:
        logger.error(f"❌ TELEGRAM_UNEXPECTED: user={user_id}, error={e}")
        return False


async def send_telegram_notification_async(user_id: int, message: str) -> bool:
    """
    Async version of send_telegram_notification.
    
    Args:
        user_id: Database user ID
        message: Text message to send
        
    Returns:
        True if sent successfully, False otherwise
    """
    try:
        # Get Telegram chat ID from user_id  
        telegram_id = user_id
        
        # Send message directly
        await bot.send_message(chat_id=telegram_id, text=message)
        
        logger.info(f"✅ TELEGRAM_SENT_ASYNC: user={user_id}")
        return True
        
    except TelegramError as e:
        logger.error(f"❌ TELEGRAM_ERROR_ASYNC: user={user_id}, error={e}")
        return False
    except Exception as e:
        logger.error(f"❌ TELEGRAM_UNEXPECTED_ASYNC: user={user_id}, error={e}")
        return False