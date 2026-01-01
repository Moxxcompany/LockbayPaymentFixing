"""
Universal Message Editor - Handles all Telegram message editing conflicts
Architectural solution for Issues #19-21: Message Type Detection & Error Recovery
"""

import logging
from typing import Optional
from telegram import Update, InlineKeyboardMarkup, Message
from telegram.error import BadRequest

logger = logging.getLogger(__name__)


class MessageEditor:
    """
    ARCHITECTURE: Universal message editor that handles all editing conflicts
    Replaces 4-layer error recovery with intelligent single-layer detection
    """

    @staticmethod
    async def safe_edit_message(
        update: Update,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        parse_mode: str = "HTML",
        fallback_send: bool = True,
    ) -> bool:
        """
        Universal message editor with intelligent type detection

        Args:
            update: Telegram update object
            text: New message text
            reply_markup: Keyboard markup
            parse_mode: Message parse mode
            fallback_send: Whether to send new message if editing fails

        Returns:
            True if successful, False if failed
        """
        if not update.effective_chat:
            logger.error("No effective chat found in update")
            return False

        try:
            # Priority 1: Try callback query editing (most common)
            if update.callback_query and update.callback_query.message:
                message = update.callback_query.message
                # Type safety: Ensure message is accessible and convert to proper Message type
                if hasattr(message, "text") or hasattr(message, "caption"):
                    # Safe cast to Message type for editing
                    from telegram import Message as TGMessage

                    if isinstance(message, TGMessage):
                        return await MessageEditor._edit_existing_message(
                            message, text, reply_markup, parse_mode
                        )

            # Priority 2: Try direct message editing
            if update.message:
                return await MessageEditor._edit_existing_message(
                    update.message, text, reply_markup, parse_mode
                )

            # Priority 3: Fallback to new message if editing not possible
            if fallback_send:
                await update.effective_chat.send_message(
                    text=text, reply_markup=reply_markup, parse_mode=parse_mode
                )
                logger.info("Sent new message as fallback")
                return True

        except Exception as e:
            logger.error(f"Message editing failed: {e}")

            # Final fallback: Send new message
            if fallback_send:
                try:
                    await update.effective_chat.send_message(
                        text=text, reply_markup=reply_markup, parse_mode=parse_mode
                    )
                    logger.info("Sent new message after editing failure")
                    return True
                except Exception as send_error:
                    logger.error(f"Even fallback send failed: {send_error}")
                    return False

        return False

    @staticmethod
    async def _edit_existing_message(
        message: Message,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup],
        parse_mode: str,
    ) -> bool:
        """
        Internal method to handle actual message editing with type detection
        """
        try:
            # Detect message type and use appropriate editing method
            if message.text:
                # Text message - use edit_text
                await message.edit_text(
                    text=text, reply_markup=reply_markup, parse_mode=parse_mode
                )
                logger.debug("Successfully edited text message")
                return True

            elif message.caption or message.photo or message.document:
                # Media message - use edit_caption
                await message.edit_caption(
                    caption=text, reply_markup=reply_markup, parse_mode=parse_mode
                )
                logger.debug("Successfully edited media caption")
                return True

            else:
                # Unknown message type - cannot edit
                logger.warning("Unknown message type - cannot edit")
                return False

        except BadRequest as e:
            error_msg = str(e).lower()
            if "message is not modified" in error_msg:
                logger.debug("Message content identical - skipping edit")
                return True  # Content is the same, consider it successful
            elif "there is no text in the message to edit" in error_msg:
                logger.debug("No text to edit - trying caption edit")
                # Try caption edit as fallback
                try:
                    await message.edit_caption(
                        caption=text, reply_markup=reply_markup, parse_mode=parse_mode
                    )
                    return True
                except Exception:
                    logger.warning("Caption edit also failed")
                    return False
            else:
                logger.error(f"BadRequest during editing: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error during message edit: {e}")
            return False


# Convenience function for quick usage
async def safe_edit(
    update: Update,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: str = "HTML",
) -> bool:
    """Quick access to universal message editor"""
    return await MessageEditor.safe_edit_message(update, text, reply_markup, parse_mode)
