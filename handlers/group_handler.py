"""
Group Management Handler - Handles bot being added/removed from Telegram groups
and sends welcome message with event broadcasting info
"""

import logging
from telegram import Update, Bot
from telegram.ext import ContextTypes, ChatMemberHandler
from services.group_event_service import group_event_service

logger = logging.getLogger(__name__)


async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle bot being added to or removed from a group/supergroup"""
    if not update.my_chat_member:
        return
    
    chat = update.my_chat_member.chat
    new_status = update.my_chat_member.new_chat_member.status
    old_status = update.my_chat_member.old_chat_member.status
    
    # Only handle group/supergroup chats
    if chat.type not in ('group', 'supergroup'):
        return
    
    logger.info(f"Chat member update: {chat.title} ({chat.id}) - {old_status} -> {new_status}")
    
    if new_status in ('member', 'administrator'):
        # Bot was added to the group
        group_event_service.register_group(
            chat_id=chat.id,
            chat_title=chat.title or "Unknown Group",
            chat_type=chat.type
        )
        
        # Send welcome message to the group
        try:
            welcome_message = (
                "<b>LockBay Escrow Bot Connected</b>\n\n"
                "This group will now receive trade event updates:\n\n"
                "- New trade created\n"
                "- Trade funded\n"
                "- Seller accepted\n"
                "- Trade completed\n"
                "- Trade rated\n"
                "- New users joined\n\n"
                "All trades on LockBay are secured with escrow protection."
            )
            
            from config import Config
            if Config.BOT_TOKEN:
                bot = Bot(Config.BOT_TOKEN)
                await bot.send_message(
                    chat_id=chat.id,
                    text=welcome_message,
                    parse_mode='HTML'
                )
                logger.info(f"Sent welcome message to group: {chat.title} ({chat.id})")
        except Exception as e:
            logger.error(f"Error sending welcome message to group {chat.id}: {e}")
    
    elif new_status in ('left', 'kicked'):
        # Bot was removed from the group
        group_event_service.unregister_group(chat_id=chat.id)
        logger.info(f"Bot removed from group: {chat.title} ({chat.id})")


def register_group_handlers(application) -> None:
    """Register group management handlers with the Telegram application"""
    application.add_handler(
        ChatMemberHandler(handle_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER)
    )
    logger.info("Registered group management handlers")
