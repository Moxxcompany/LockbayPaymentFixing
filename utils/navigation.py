"""Universal Navigation Utilities for Telegram Escrow Bot"""

import logging
import time
from typing import List, Optional, Dict
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

logger = logging.getLogger(__name__)


def create_navigation_footer(
    show_back: bool = True,
    back_text: str = "⬅️ Back",
    back_data: str = "back",
    show_main_menu: bool = True,
    main_menu_text: str = "🏠 Main Menu",
    main_menu_data: str = "back_to_main",
    additional_buttons: Optional[List[List[InlineKeyboardButton]]] = None,
) -> List[List[InlineKeyboardButton]]:
    """
    Create standardized navigation footer for consistent user experience

    Args:
        show_back: Whether to show back button
        back_text: Text for back button
        back_data: Callback data for back button
        show_main_menu: Whether to show main menu button
        main_menu_text: Text for main menu button
        main_menu_data: Callback data for main menu button
        additional_buttons: Extra button rows to include

    Returns:
        List of button rows for InlineKeyboardMarkup
    """
    footer_buttons = []

    # Add additional buttons first if provided
    if additional_buttons:
        footer_buttons.extend(additional_buttons)

    # Create navigation row
    nav_row = []
    if show_back:
        nav_row.append(InlineKeyboardButton(back_text, callback_data=back_data))

    if show_main_menu:
        nav_row.append(
            InlineKeyboardButton(main_menu_text, callback_data=main_menu_data)
        )

    if nav_row:
        footer_buttons.append(nav_row)

    return footer_buttons


def create_standard_keyboard(
    main_buttons: List[List[InlineKeyboardButton]],
    show_back: bool = True,
    back_data: str = "back",
    show_main_menu: bool = True,
    additional_nav_buttons: Optional[List[List[InlineKeyboardButton]]] = None,
) -> InlineKeyboardMarkup:
    """
    Create keyboard with main buttons + standardized navigation footer

    Args:
        main_buttons: Main action buttons
        show_back: Whether to show back button
        back_data: Callback data for back button
        show_main_menu: Whether to show main menu
        additional_nav_buttons: Extra navigation buttons

    Returns:
        Complete InlineKeyboardMarkup
    """
    all_buttons = main_buttons.copy()

    # Add navigation footer
    nav_footer = create_navigation_footer(
        show_back=show_back,
        back_data=back_data,
        show_main_menu=show_main_menu,
        additional_buttons=additional_nav_buttons,
    )

    all_buttons.extend(nav_footer)
    return InlineKeyboardMarkup(all_buttons)


def create_error_recovery_keyboard(
    error_context: str = "general",
    show_retry: bool = True,
    retry_data: str = "retry",
    show_support: bool = True,
) -> InlineKeyboardMarkup:
    """
    Create standardized error recovery keyboard

    Args:
        error_context: Context of the error for analytics
        show_retry: Whether to show retry button
        retry_data: Callback data for retry
        show_support: Whether to show support button

    Returns:
        Error recovery keyboard with navigation options
    """
    buttons = []

    if show_retry:
        buttons.append([InlineKeyboardButton("🔄 Try Again", callback_data=retry_data)])

    if show_support:
        buttons.append(
            [
                InlineKeyboardButton(
                    "📞 Contact Support", callback_data="contact_support"
                )
            ]
        )

    # Always include main menu escape
    buttons.append([InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main")])

    return InlineKeyboardMarkup(buttons)


async def safe_navigation_fallback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message: str = "⚠️ Session expired. Returning to main menu...",
    cleanup_conversation: bool = True,
) -> int:
    """
    Safe fallback for navigation issues - always returns user to main menu

    Args:
        update: Telegram update object
        context: Bot context
        message: Message to show user
        cleanup_conversation: Whether to clean conversation state

    Returns:
        ConversationHandler.END
    """
    user_id = update.effective_user.id if update.effective_user else 0

    # Rate limiting to prevent over-triggering
    _rate_cache = getattr(safe_navigation_fallback, "_rate_cache", {})

    current_time = time.time()
    cache_key = f"nav_{user_id}"

    if cache_key in _rate_cache:
        last_time = _rate_cache[cache_key]
        if current_time - last_time < 10:  # 10 second cooldown
            logger.debug(f"Navigation fallback rate limited for user {user_id}")
            return ConversationHandler.END

    _rate_cache[cache_key] = current_time
    setattr(safe_navigation_fallback, "_rate_cache", _rate_cache)

    logger.warning(f"Navigation fallback triggered for user {user_id}")

    try:
        # Clean up conversation state if requested
        if cleanup_conversation and context.user_data:
            # Keep essential user data, clean conversation-specific data
            essential_keys = ["user_id", "telegram_id", "username"]
            conversation_keys = [
                k for k in context.user_data.keys() if k not in essential_keys
            ]
            for key in conversation_keys:
                context.user_data.pop(key, None)
            logger.info("Cleaned conversation state in navigation fallback")

        # Send user to main menu
        from utils.keyboards import main_menu_keyboard

        if update.callback_query:
            await update.callback_query.edit_message_text(
                message, reply_markup=main_menu_keyboard()  # Navigation fallback
            )
        elif update.message:
            await update.message.reply_text(
                message, reply_markup=main_menu_keyboard()  # Navigation fallback
            )

    except Exception as e:
        logger.error(f"Error in navigation fallback: {e}")
        # Last resort - send simple text message
        try:
            if update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="🏠 Returning to main menu... Type /start to continue.",
                )
        except Exception as final_error:
            logger.error(f"Final fallback failed: {final_error}")

    return ConversationHandler.END


async def universal_error_recovery(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    error_message: str = "❌ Something went wrong",
    return_state: Optional[str] = None,
    show_retry: bool = True,
    retry_callback: str = "retry_current_action",
) -> int:
    """
    Universal error recovery with smart navigation options

    Args:
        update: Telegram update object
        context: Bot context
        error_message: Custom error message to display
        return_state: Specific state to return to (default: END)
        show_retry: Whether to show retry option
        retry_callback: Callback data for retry button

    Returns:
        ConversationHandler state
    """
    try:
        # Build recovery keyboard
        keyboard = []

        if show_retry:
            keyboard.append(
                [InlineKeyboardButton("🔄 Try Again", callback_data=retry_callback)]
            )

        # Add core navigation options
        keyboard.extend(
            [
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
                [InlineKeyboardButton("📞 Help", callback_data="contact_support")],
            ]
        )

        recovery_message = f"{error_message}\n\nWhat would you like to do?"
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Clear any corrupted conversation state
        if context.user_data:
            # Preserve essential user info but clear conversation data
            essential_keys = ["user_id", "email", "phone_number"]
            preserved_data = {
                k: context.user_data.get(k)
                for k in essential_keys
                if k in context.user_data
            }
            context.user_data.clear()
            context.user_data.update(preserved_data)

        # Send recovery message
        if update.callback_query:
            await update.callback_query.edit_message_text(
                recovery_message, reply_markup=reply_markup, parse_mode="Markdown"
            )
        elif update.message:
            await update.message.reply_text(
                recovery_message, reply_markup=reply_markup, parse_mode="Markdown"
            )

        # Track recovery attempt
        user_id = update.effective_user.id if update.effective_user else 0
        logger.warning(
            f"Universal error recovery triggered for user {user_id}: {error_message}"
        )

        # Type-safe return: ensure int return type
        if return_state is None:
            return ConversationHandler.END
        elif isinstance(return_state, int):
            return return_state
        else:
            # Convert string state to END for type safety
            return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in universal_error_recovery: {e}")
        # Last resort fallback
        return await safe_navigation_fallback(
            update,
            context,
            message="⚠️ System error. Returning to main menu...",
            cleanup_conversation=True,
        )


def create_context_aware_keyboard(
    user_context: dict,
    base_buttons: List[List[InlineKeyboardButton]],
    context_conditions: Optional[Dict] = None,
) -> InlineKeyboardMarkup:
    """
    Create keyboard that adapts based on user context and state

    Args:
        user_context: Current user context/state
        base_buttons: Base buttons to always show
        context_conditions: Conditions for showing additional buttons

    Returns:
        Context-aware keyboard
    """
    buttons = base_buttons.copy()

    # Add context-specific buttons based on conditions
    if context_conditions:
        for condition, button_rows in context_conditions.items():
            if user_context.get(condition):
                buttons.extend(button_rows)

    # Always add navigation footer
    nav_footer = create_navigation_footer()
    buttons.extend(nav_footer)

    return InlineKeyboardMarkup(buttons)
