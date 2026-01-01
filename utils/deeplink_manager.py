"""Enhanced Deep Link Conflict Resolution for Active Conversations"""

import logging
from typing import Dict, Optional, Tuple
from enum import Enum
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from utils.conversation_protection import ConversationTimeout

logger = logging.getLogger(__name__)


class ConversationState(Enum):
    """Possible conversation states"""

    NONE = "none"
    ESCROW_CREATION = "escrow_creation"
    WALLET_OPERATION = "wallet_operation"
    CASHOUT = "cashout"
    SETTINGS = "settings"
    EMAIL_VERIFICATION = "email_verification"
    DIRECT_EXCHANGE = "direct_exchange"
    AUTO_CASHOUT = "auto_cashout"


class DeepLinkType(Enum):
    """Types of deep links"""

    ESCROW_INVITATION = "escrow"
    TRADE_INVITATION = "invite"
    EMAIL_VERIFICATION = "verify"
    SUPPORT_TICKET = "support"
    REFERRAL = "ref"
    PAYMENT_LINK = "pay"


class DeepLinkConflictResolver:
    """Manages deep link conflicts with active conversations"""

    # Track active conversations by user
    _active_conversations: Dict[int, ConversationState] = {}

    @classmethod
    def set_conversation_state(cls, user_id: int, state: ConversationState) -> None:
        """Set active conversation state for user"""
        cls._active_conversations[user_id] = state
        logger.info(f"Set conversation state for user {user_id}: {state.value}")

    @classmethod
    def get_conversation_state(cls, user_id: int) -> ConversationState:
        """Get current conversation state for user"""
        return cls._active_conversations.get(user_id, ConversationState.NONE)

    @classmethod
    async def handle_deeplink_callback(
        cls, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle deeplink callback conflicts during active conversations

        Args:
            update: Telegram update object
            context: Bot context
        """
        query = update.callback_query
        if not query or not query.data:
            return

        user_id = update.effective_user.id if update.effective_user else 0
        callback_data = query.data

        # Parse callback for deeplink conflicts
        if callback_data.startswith("deeplink_"):
            action = callback_data.replace("deeplink_", "")

            if action == "accept":
                # User accepted deeplink during conversation
                stored_link = cls._stored_deeplinks.get(user_id)
                if stored_link:
                    link_type, link_data = stored_link
                    await query.answer("Switching to new link...")

                    # Clear current state and process deeplink
                    cls.clear_conversation_state(user_id)

                    # Process the stored deeplink
                    from handlers.start import handle_deep_link

                    await handle_deep_link(update, context, link_data, None)

            elif action == "reject":
                # User rejected deeplink, continue current conversation
                await query.answer("Continuing current session...")
                cls._stored_deeplinks.pop(user_id, None)

        logger.info(f"Processed deeplink callback: {callback_data} for user {user_id}")

    @classmethod
    def clear_conversation_state(cls, user_id: int) -> None:
        """Clear conversation state for user"""
        cls._active_conversations.pop(user_id, None)
        logger.info(f"Cleared conversation state for user {user_id}")

    @classmethod
    def parse_deep_link(cls, start_param: str) -> Tuple[DeepLinkType, str]:
        """
        Parse deep link parameter and extract type and data

        Args:
            start_param: The parameter from /start command

        Returns:
            Tuple of (link_type, link_data)
        """
        if not start_param:
            return None, None

        # Parse different link formats
        if start_param.startswith("escrow_"):
            return DeepLinkType.ESCROW_INVITATION, start_param.replace("escrow_", "")
        elif start_param.startswith("invite_"):
            return DeepLinkType.TRADE_INVITATION, start_param.replace("invite_", "")
        elif start_param.startswith("verify_"):
            return DeepLinkType.EMAIL_VERIFICATION, start_param.replace("verify_", "")
        elif start_param.startswith("support_"):
            return DeepLinkType.SUPPORT_TICKET, start_param.replace("support_", "")
        elif start_param.startswith("ref_"):
            return DeepLinkType.REFERRAL, start_param.replace("ref_", "")
        elif start_param.startswith("pay_"):
            return DeepLinkType.PAYMENT_LINK, start_param.replace("pay_", "")

        # Default to escrow invitation for backward compatibility
        return DeepLinkType.ESCROW_INVITATION, start_param

    @classmethod
    async def handle_conflict(
        cls,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        deep_link_type: DeepLinkType,
        deep_link_data: str,
        current_state: ConversationState,
    ) -> Tuple[bool, Optional[int]]:
        """
        Handle conflict between deep link and active conversation

        Args:
            update: Telegram update object
            context: Bot context
            deep_link_type: Type of incoming deep link
            deep_link_data: Data from deep link
            current_state: Current conversation state

        Returns:
            Tuple of (should_proceed, conversation_end_result)
        """
        user_id = update.effective_user.id if update.effective_user else 0

        logger.info(
            f"Handling deep link conflict for user {user_id}: {deep_link_type.value} vs {current_state.value}"
        )

        # High priority links that should interrupt conversations
        high_priority = [
            DeepLinkType.ESCROW_INVITATION,
            DeepLinkType.TRADE_INVITATION,
            DeepLinkType.EMAIL_VERIFICATION,
        ]

        # Low priority links that should wait
        low_priority = [DeepLinkType.SUPPORT_TICKET, DeepLinkType.REFERRAL]

        if deep_link_type in high_priority:
            # Interrupt current conversation for high priority links
            return await cls._interrupt_conversation(
                update, context, deep_link_type, deep_link_data, current_state
            )
        elif deep_link_type in low_priority:
            # Queue low priority links for later
            return await cls._queue_deep_link(
                update, context, deep_link_type, deep_link_data, current_state
            )
        else:
            # Default: ask user what to do
            return await cls._ask_user_preference(
                update, context, deep_link_type, deep_link_data, current_state
            )

    @classmethod
    async def _interrupt_conversation(
        cls,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        deep_link_type: DeepLinkType,
        deep_link_data: str,
        current_state: ConversationState,
    ) -> Tuple[bool, int]:
        """Interrupt current conversation for high priority deep link"""
        user_id = update.effective_user.id if update.effective_user else 0

        # Save current conversation state for potential restoration
        if context.user_data:
            context.user_data["interrupted_conversation"] = {
                "state": current_state.value,
                "data": dict(context.user_data),
                "timestamp": ConversationTimeout.CONVERSATION_TIMEOUTS.get(user_id),
            }

        # Clear current conversation
        cls.clear_conversation_state(user_id)
        ConversationTimeout.clear_timeout(user_id)

        # Show interruption message
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton

        interrupt_message = f"""🔔 New {deep_link_type.value.replace('_', ' ').title()}
        
Your current session has been saved and you'll be redirected to handle this new request.

You can return to your previous session later if needed."""

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Continue",
                        callback_data=f"deeplink_proceed:{deep_link_type.value}:{deep_link_data}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔄 Restore Previous Session",
                        callback_data="restore_interrupted",
                    )
                ],
            ]
        )

        if update.message:
            await update.message.reply_text(
                interrupt_message, reply_markup=keyboard
            )

        logger.info(
            f"Interrupted conversation for user {user_id}: {current_state.value} -> {deep_link_type.value}"
        )

        return True, ConversationHandler.END

    @classmethod
    async def _queue_deep_link(
        cls,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        deep_link_type: DeepLinkType,
        deep_link_data: str,
        current_state: ConversationState,
    ) -> Tuple[bool, None]:
        """Queue deep link for after current conversation"""
        user_id = update.effective_user.id if update.effective_user else 0

        # Store queued deep link
        if not context.user_data:
            # Fix: Cannot assign new value to user_data
            if hasattr(context, 'user_data') and context.user_data is not None:
                context.user_data.clear()
            # Initialize with setdefault
            if hasattr(context, 'user_data'):
                context.user_data.setdefault('_init', True)

        context.user_data["queued_deeplink"] = {
            "type": deep_link_type.value,
            "data": deep_link_data,
        }

        # Notify user
        queue_message = f"""📋 **Link Queued**
        
You have a new {deep_link_type.value.replace('_', ' ')} waiting, but you're currently in an active session.

We'll handle it automatically when you finish your current task."""

        if update.message:
            await update.message.reply_text(queue_message, parse_mode="Markdown")

        logger.info(f"Queued deep link for user {user_id}: {deep_link_type.value}")

        return False, None

    @classmethod
    async def _ask_user_preference(
        cls,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        deep_link_type: DeepLinkType,
        deep_link_data: str,
        current_state: ConversationState,
    ) -> Tuple[bool, None]:
        """Ask user how to handle the conflict"""
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton

        choice_message = f"""🤔 **Action Required**
        
You clicked a {deep_link_type.value.replace('_', ' ')} link, but you're currently in an active {current_state.value.replace('_', ' ')} session.

What would you like to do?"""

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔄 Handle New Request",
                        callback_data=f"deeplink_proceed:{deep_link_type.value}:{deep_link_data}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📋 Continue Current Session",
                        callback_data="deeplink_continue_current",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⏯️ Queue for Later",
                        callback_data=f"deeplink_queue:{deep_link_type.value}:{deep_link_data}",
                    )
                ],
            ]
        )

        if update.message:
            await update.message.reply_text(
                choice_message, reply_markup=keyboard, parse_mode="Markdown"
            )

        return False, None

    @classmethod
    async def check_queued_deeplinks(
        cls, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> bool:
        """
        Check and process any queued deep links after conversation ends

        Args:
            update: Telegram update object
            context: Bot context

        Returns:
            True if a queued deep link was processed
        """
        if not context.user_data or "queued_deeplink" not in context.user_data:
            return False

        queued = context.user_data.pop("queued_deeplink")
        link_type = DeepLinkType(queued["type"])
        link_data = queued["data"]

        user_id = update.effective_user.id if update.effective_user else 0
        logger.info(
            f"Processing queued deep link for user {user_id}: {link_type.value}"
        )

        # Process the queued deep link
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton

        process_message = f"""🔔 **Processing Queued Request**
        
Your {link_type.value.replace('_', ' ')} is now ready to be processed."""

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Continue",
                        callback_data=f"deeplink_proceed:{link_type.value}:{link_data}",
                    )
                ],
                [InlineKeyboardButton("❌ Dismiss", callback_data="deeplink_dismiss")],
            ]
        )

        if update.callback_query:
            await update.callback_query.edit_message_text(
                process_message, reply_markup=keyboard, parse_mode="Markdown"
            )
        elif update.message:
            await update.message.reply_text(
                process_message, reply_markup=keyboard, parse_mode="Markdown"
            )

        return True

    @classmethod
    async def restore_interrupted_conversation(
        cls, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> bool:
        """
        Restore previously interrupted conversation

        Args:
            update: Telegram update object
            context: Bot context

        Returns:
            True if restoration was successful
        """
        if not context.user_data or "interrupted_conversation" not in context.user_data:
            return False

        interrupted = context.user_data.pop("interrupted_conversation")
        user_id = update.effective_user.id if update.effective_user else 0

        # Restore conversation state
        restored_state = ConversationState(interrupted["state"])
        cls.set_conversation_state(user_id, restored_state)

        # Restore context data
        context.user_data.clear()
        context.user_data.update(interrupted["data"])

        # Restore timeout if it was active
        if interrupted.get("timestamp"):
            ConversationTimeout.CONVERSATION_TIMEOUTS[user_id] = interrupted[
                "timestamp"
            ]

        logger.info(
            f"Restored interrupted conversation for user {user_id}: {restored_state.value}"
        )

        # Notify user
        restore_message = f"""🔄 **Session Restored**
        
Your {restored_state.value.replace('_', ' ')} session has been restored.

You can continue where you left off."""

        if update.callback_query:
            await update.callback_query.edit_message_text(
                restore_message, parse_mode="Markdown"
            )

        return True


async def handle_deeplink_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle deep link related callbacks"""
    query = update.callback_query
    if not query or not query.data:
        return

    user_id = update.effective_user.id if update.effective_user else 0

    if query.data.startswith("deeplink_proceed:"):
        # Process deep link
        parts = query.data.split(":", 2)
        if len(parts) >= 3:
            link_type = DeepLinkType(parts[1])
            link_data = parts[2]

            logger.info(f"Processing deep link for user {user_id}: {link_type.value}")

            # Clear any existing conversation
            DeepLinkConflictResolver.clear_conversation_state(user_id)

            # Handle specific deep link types
            if link_type == DeepLinkType.ESCROW_INVITATION:
                from handlers.start import handle_deep_link

                await handle_deep_link(update, context, f"escrow_{link_data}", None)
            # Add other deep link handlers as needed

    elif query.data == "deeplink_continue_current":
        # Continue current conversation
        await query.edit_message_text("▶️ Continuing your current session...")

    elif query.data.startswith("deeplink_queue:"):
        # Queue the deep link
        parts = query.data.split(":", 2)
        if len(parts) >= 3:
            link_type = DeepLinkType(parts[1])
            link_data = parts[2]

            if not context.user_data:
                # Fix: Cannot assign new value to user_data
                if hasattr(context, 'user_data') and context.user_data is not None:
                    context.user_data.clear()
                else:
                    # Use setdefault to initialize if possible
                    if hasattr(context, 'user_data'):
                        context.user_data.setdefault('_init', True)

            context.user_data["queued_deeplink"] = {
                "type": link_type.value,
                "data": link_data,
            }

            await query.edit_message_text(
                "📋 Request queued. We'll handle it when you finish your current session."
            )

    elif query.data == "restore_interrupted":
        # Restore interrupted conversation
        success = await DeepLinkConflictResolver.restore_interrupted_conversation(
            update, context
        )
        if not success:
            await query.edit_message_text("❌ No interrupted session found to restore.")

    elif query.data == "deeplink_dismiss":
        # Dismiss queued deep link
        await query.edit_message_text("✅ Request dismissed.")
