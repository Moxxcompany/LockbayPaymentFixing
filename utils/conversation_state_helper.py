"""Helper functions for managing conversation state with automatic timestamp tracking"""
import time
from typing import Optional
from telegram.ext import ContextTypes
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update as sqlalchemy_update
from models import User
from utils.normalizers import normalize_telegram_id
import logging

logger = logging.getLogger(__name__)


def _invalidate_route_cache(user_id: int) -> None:
    """Invalidate RouteGuard cache when conversation_state changes"""
    try:
        from utils.route_guard import RouteGuard
        RouteGuard.invalidate_conversation_cache(user_id)
    except Exception as e:
        logger.debug(f"Could not invalidate route cache: {e}")


def set_conversation_state_context(
    context: ContextTypes.DEFAULT_TYPE, 
    state: Optional[str]
) -> None:
    """Set conversation state in context with automatic timestamp tracking
    
    Args:
        context: Telegram context
        state: Conversation state (or None to clear)
    """
    # user_data is always initialized by python-telegram-bot framework
    # Type assertion to satisfy type checker
    if context.user_data is None:
        logger.warning("context.user_data is unexpectedly None")
        return
        
    context.user_data['conversation_state'] = state
    
    if state:
        # Set timestamp when state is active
        context.user_data['conversation_state_timestamp'] = time.time()
        logger.debug(f"Set conversation_state='{state}' with timestamp")
    else:
        # Clear timestamp when state is cleared
        context.user_data['conversation_state_timestamp'] = 0
        logger.debug("Cleared conversation_state and timestamp")


async def set_conversation_state_db(
    user_id: int,
    state: Optional[str],
    session: AsyncSession
) -> None:
    """Set conversation state in database
    
    Args:
        user_id: Telegram user ID
        state: Conversation state (or None to clear)
        session: Database session
    """
    normalized_id = normalize_telegram_id(user_id)
    if not normalized_id:
        logger.warning(f"Invalid user_id: {user_id}")
        return
    
    stmt = sqlalchemy_update(User).where(
        User.telegram_id == normalized_id
    ).values(conversation_state=state)
    
    await session.execute(stmt)
    
    # PERFORMANCE: Invalidate RouteGuard cache when conversation_state changes
    _invalidate_route_cache(user_id)
    
    if state:
        logger.debug(f"Set database conversation_state='{state}' for user {user_id}")
    else:
        logger.debug(f"Cleared database conversation_state for user {user_id}")


async def set_conversation_state_both(
    user_id: int,
    state: Optional[str],
    context: ContextTypes.DEFAULT_TYPE,
    session: AsyncSession
) -> None:
    """Set conversation state in both context and database with timestamp
    
    Args:
        user_id: Telegram user ID
        state: Conversation state (or None to clear)
        context: Telegram context
        session: Database session
    """
    set_conversation_state_context(context, state)
    await set_conversation_state_db(user_id, state, session)


def set_conversation_state_db_sync(
    user_obj: User, 
    state: Optional[str],
    context: Optional[ContextTypes.DEFAULT_TYPE] = None
) -> None:
    """Set conversation state on user object directly (for sync sessions)
    
    This is a synchronous helper for handlers that use synchronous database sessions.
    
    Args:
        user_obj: User model object
        state: Conversation state (or None to clear)
        context: Optional Telegram context to also set timestamp tracking
    """
    user_obj.conversation_state = state
    
    # PERFORMANCE: Invalidate RouteGuard cache when conversation_state changes
    if hasattr(user_obj, 'telegram_id') and user_obj.telegram_id:
        _invalidate_route_cache(user_obj.telegram_id)
    
    # TIMESTAMP FIX: Also set timestamp in context if provided
    if context is not None:
        set_conversation_state_context(context, state)
    
    if state:
        logger.debug(f"Set conversation_state='{state}' on user object")
    else:
        logger.debug("Cleared conversation_state on user object")
