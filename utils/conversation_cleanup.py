"""
Unified Conversation State Cleanup Utility

Provides a single, reliable function to clear all conversation state across:
- Database conversation_state field
- Context user_data (in-memory)
- Cached routing decisions
- Escrow data

This prevents stale state bugs by ensuring consistent cleanup everywhere.
"""

import logging
from typing import Optional
from telegram.ext import ContextTypes
from database import async_managed_session
from models import User
from sqlalchemy import update

logger = logging.getLogger(__name__)

async def clear_user_conversation_state(
    user_id: int,
    context: Optional[ContextTypes.DEFAULT_TYPE] = None,
    trigger: str = "unknown"
) -> bool:
    """
    Clear all conversation state for a user - both database and in-memory.
    
    Args:
        user_id: Telegram user ID (int, not string)
        context: Optional Telegram context object (for clearing user_data)
        trigger: Reason for cleanup (for debugging logs)
        
    Returns:
        bool: True if cleanup succeeded, False if failed
        
    Usage:
        # From callback handler
        await clear_user_conversation_state(user.id, context, "back_to_menu")
        
        # From start command
        await clear_user_conversation_state(update.effective_user.id, context, "start_command")
    """
    success = True
    cleanup_steps = []
    
    try:
        # Step 1: Clear database conversation_state
        try:
            async with async_managed_session() as session:
                # FIX: telegram_id is bigint, compare with int not str
                result = await session.execute(
                    update(User)
                    .where(User.telegram_id == user_id)
                    .values(conversation_state=None)
                )
                await session.commit()
                rows_updated = result.rowcount if hasattr(result, 'rowcount') else 0
                cleanup_steps.append(f"db_state={rows_updated}_rows")
                logger.debug(f"✅ Cleared database conversation_state for user {user_id} ({rows_updated} rows)")
        except Exception as db_error:
            logger.error(f"❌ Failed to clear database state for user {user_id}: {db_error}")
            cleanup_steps.append("db_state=FAILED")
            success = False
        
        # Step 2: Clear context user_data (in-memory state)
        if context and hasattr(context, 'user_data') and context.user_data:
            try:
                # Store count before clearing
                data_count = len(context.user_data)
                context.user_data.clear()
                cleanup_steps.append(f"user_data={data_count}_items")
                logger.debug(f"✅ Cleared {data_count} items from context.user_data for user {user_id}")
            except Exception as context_error:
                logger.error(f"❌ Failed to clear context.user_data for user {user_id}: {context_error}")
                cleanup_steps.append("user_data=FAILED")
                success = False
        else:
            cleanup_steps.append("user_data=N/A")
        
        # Step 3: Clear route guard cache (if exists)
        try:
            from utils.route_guard import RouteGuard
            if hasattr(RouteGuard, '_user_state_cache'):
                cache_key = f"route_decision_{user_id}"
                if cache_key in RouteGuard._user_state_cache:
                    del RouteGuard._user_state_cache[cache_key]
                    cleanup_steps.append("route_cache=cleared")
                else:
                    cleanup_steps.append("route_cache=empty")
        except Exception as cache_error:
            logger.debug(f"Route cache cleanup skipped: {cache_error}")
            cleanup_steps.append("route_cache=N/A")
        
        # Log comprehensive cleanup summary
        status = "SUCCESS" if success else "PARTIAL"
        steps_str = ", ".join(cleanup_steps)
        logger.info(f"🧹 CLEANUP_{status}: user={user_id}, trigger={trigger}, steps=[{steps_str}]")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ CLEANUP_FAILED: user={user_id}, trigger={trigger}, error={e}")
        return False


async def clear_escrow_data(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int
) -> None:
    """
    Clear escrow-specific data from context.
    
    This is a specialized cleanup for escrow flows only.
    For general conversation cleanup, use clear_user_conversation_state().
    """
    if not context or not hasattr(context, 'user_data'):
        return
    
    escrow_keys = ['escrow_data', 'escrow_id', 'seller_info', 'amount', 'description']
    cleared = []
    
    for key in escrow_keys:
        if key in context.user_data:
            del context.user_data[key]
            cleared.append(key)
    
    if cleared:
        logger.info(f"🧹 ESCROW_CLEANUP: user={user_id}, cleared={cleared}")
