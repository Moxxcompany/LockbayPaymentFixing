"""
Safe database repository helpers with proper type handling.

This module provides centralized, type-safe database access patterns
to prevent type mismatches and ensure consistent query behavior.
"""

import logging
from typing import Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User
from utils.normalizers import normalize_telegram_id, normalize_user_id

logger = logging.getLogger(__name__)


class UserRepository:
    """Safe user database operations with proper type handling."""
    
    @staticmethod
    def get_user_by_telegram_id(session: Session, telegram_id: Union[int, str, None]) -> Optional[User]:
        """
        Get user by telegram_id with proper type normalization.
        
        Args:
            session: SQLAlchemy session
            telegram_id: Telegram ID as int, str, or None
            
        Returns:
            User object or None if not found
            
        Raises:
            TypeError: If telegram_id cannot be normalized to int
            ValueError: If telegram_id is invalid
        """
        if telegram_id is None:
            return None
            
        normalized_id = normalize_telegram_id(telegram_id)
        if normalized_id is None:
            return None
            
        try:
            result = session.execute(
                select(User).where(User.telegram_id == normalized_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error querying user by telegram_id {normalized_id}: {e}")
            raise
    
    @staticmethod
    async def get_user_by_telegram_id_async(session: AsyncSession, telegram_id: Union[int, str, None]) -> Optional[User]:
        """
        Async version of get_user_by_telegram_id.
        
        Args:
            session: Async SQLAlchemy session
            telegram_id: Telegram ID as int, str, or None
            
        Returns:
            User object or None if not found
            
        Raises:
            TypeError: If telegram_id cannot be normalized to int
            ValueError: If telegram_id is invalid
        """
        if telegram_id is None:
            return None
            
        normalized_id = normalize_telegram_id(telegram_id)
        if normalized_id is None:
            return None
            
        try:
            result = await session.execute(
                select(User).where(User.telegram_id == normalized_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error querying user by telegram_id {normalized_id}: {e}")
            raise
    
    @staticmethod
    def get_user_by_id(session: Session, user_id: Union[int, str, None]) -> Optional[User]:
        """
        Get user by database ID with proper type normalization.
        
        Args:
            session: SQLAlchemy session
            user_id: Database user ID as int, str, or None
            
        Returns:
            User object or None if not found
            
        Raises:
            TypeError: If user_id cannot be normalized to int
            ValueError: If user_id is invalid
        """
        if user_id is None:
            return None
            
        normalized_id = normalize_user_id(user_id)
        if normalized_id is None:
            return None
            
        try:
            result = session.execute(
                select(User).where(User.id == normalized_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error querying user by id {normalized_id}: {e}")
            raise
    
    @staticmethod
    async def get_user_by_id_async(session: AsyncSession, user_id: Union[int, str, None]) -> Optional[User]:
        """
        Async version of get_user_by_id.
        
        Args:
            session: Async SQLAlchemy session
            user_id: Database user ID as int, str, or None
            
        Returns:
            User object or None if not found
            
        Raises:
            TypeError: If user_id cannot be normalized to int
            ValueError: If user_id is invalid
        """
        if user_id is None:
            return None
            
        normalized_id = normalize_user_id(user_id)
        if normalized_id is None:
            return None
            
        try:
            result = await session.execute(
                select(User).where(User.id == normalized_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error querying user by id {normalized_id}: {e}")
            raise


def resolve_user_id_to_db_id(session: Session, user_id: Union[int, str, None]) -> Optional[int]:
    """
    Resolve any user identifier (telegram_id or db_id) to database ID.
    
    This function tries to resolve the user_id as:
    1. Database ID first (most common case)
    2. Telegram ID second (fallback)
    
    Args:
        session: SQLAlchemy session
        user_id: User identifier as int, str, or None
        
    Returns:
        Database user ID (int) or None if not found
        
    Raises:
        TypeError: If user_id cannot be normalized
    """
    if user_id is None:
        return None
    
    try:
        # First, try as database ID
        normalized_id = normalize_user_id(user_id)
        if normalized_id is not None:
            user = UserRepository.get_user_by_id(session, normalized_id)
            if user is not None:
                logger.debug(f"User ID {user_id} resolved as database ID")
                return user.id  # type: ignore[return-value]
    except (TypeError, ValueError):
        # If it fails user_id normalization, it might be a telegram_id
        pass
    
    try:
        # Second, try as telegram_id
        normalized_telegram_id = normalize_telegram_id(user_id)
        if normalized_telegram_id is not None:
            user = UserRepository.get_user_by_telegram_id(session, normalized_telegram_id)
            if user is not None:
                logger.info(f"Resolved telegram_id {user_id} to database ID {user.id}")
                return user.id  # type: ignore[return-value]
    except (TypeError, ValueError) as e:
        logger.warning(f"Could not normalize user_id {user_id} as telegram_id: {e}")
    
    logger.warning(f"User ID {user_id} not found as database ID or telegram_id")
    return None


async def resolve_user_id_to_db_id_async(session: AsyncSession, user_id: Union[int, str, None]) -> Optional[int]:
    """
    Async version of resolve_user_id_to_db_id.
    
    Args:
        session: Async SQLAlchemy session
        user_id: User identifier as int, str, or None
        
    Returns:
        Database user ID (int) or None if not found
        
    Raises:
        TypeError: If user_id cannot be normalized
    """
    if user_id is None:
        return None
    
    try:
        # First, try as database ID
        normalized_id = normalize_user_id(user_id)
        if normalized_id is not None:
            user = await UserRepository.get_user_by_id_async(session, normalized_id)
            if user is not None:
                logger.debug(f"User ID {user_id} resolved as database ID")
                return user.id  # type: ignore[return-value]
    except (TypeError, ValueError):
        # If it fails user_id normalization, it might be a telegram_id
        pass
    
    try:
        # Second, try as telegram_id
        normalized_telegram_id = normalize_telegram_id(user_id)
        if normalized_telegram_id is not None:
            user = await UserRepository.get_user_by_telegram_id_async(session, normalized_telegram_id)
            if user is not None:
                logger.info(f"Resolved telegram_id {user_id} to database ID {user.id}")
                return user.id  # type: ignore[return-value]
    except (TypeError, ValueError) as e:
        logger.warning(f"Could not normalize user_id {user_id} as telegram_id: {e}")
    
    logger.warning(f"User ID {user_id} not found as database ID or telegram_id")
    return None