"""
Transaction Command Handlers
Handles commands like /tx_<transaction_id> for viewing transaction details
"""

import logging
import re
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from handlers.transaction_history import show_transaction_detail

logger = logging.getLogger(__name__)


async def handle_transaction_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /tx_<transaction_id> commands"""
    message = update.message
    if not message or not message.text:
        return ConversationHandler.END
    
    # Extract transaction ID from command
    command_text = message.text.strip()
    match = re.match(r'^/tx_([A-Za-z0-9\-_]+)$', command_text)
    
    if not match:
        await message.reply_text("❌ Invalid transaction command format. Use: /tx_<transaction_id>")
        return ConversationHandler.END
    
    transaction_id = match.group(1)
    logger.info(f"User {update.effective_user.id if update.effective_user else 'unknown'} requested transaction details for {transaction_id}")
    
    # Show transaction detail
    return await show_transaction_detail(update, context, transaction_id)