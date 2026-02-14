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
            from config import Config
            bot_username = Config.BOT_USERNAME
            bot_link = f"https://t.me/{bot_username}"
            
            welcome_message = (
                "<b>LockBay Escrow Bot is Live Here!</b>\n\n"
                "This group is now connected to <b>LockBay</b> \u2014 "
                "the safest way to trade crypto peer-to-peer on Telegram.\n\n"
                "<b>You'll see real-time updates for:</b>\n"
                "\u2022 New escrow trades opening\n"
                "\u2022 Payments confirmed & funded\n"
                "\u2022 Sellers accepting trades\n"
                "\u2022 Successful completions & payouts\n"
                "\u2022 Trader ratings & reviews\n"
                "\u2022 New community members joining\n\n"
                "<b>Every trade is protected by escrow.</b> "
                "No more trust issues \u2014 funds are held securely until both parties are satisfied.\n\n"
                f"\u27a1\ufe0f <b>Start trading now:</b> @{bot_username}\n"
                f"\u27a1\ufe0f <b>Open bot:</b> {bot_link}"
            )
            
            if Config.BOT_TOKEN:
                bot = Bot(Config.BOT_TOKEN)
                await bot.send_message(
                    chat_id=chat.id,
                    text=welcome_message,
                    parse_mode='HTML',
                    disable_web_page_preview=True
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
