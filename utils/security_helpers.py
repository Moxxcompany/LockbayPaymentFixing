"""
Security helper functions for authorization and access control
"""

import logging
from typing import Tuple, Optional
from models import User, Escrow, EscrowStatus

logger = logging.getLogger(__name__)


def require_escrow_participant(
    user_id: int, escrow_id: str, session
) -> Tuple[bool, Optional[Escrow], Optional[User]]:
    """
    CRITICAL SECURITY: Verify user is authorized participant in escrow

    Returns:
        (is_authorized, escrow, user)
    """
    try:
        # Get escrow
        escrow = session.query(Escrow).filter(Escrow.escrow_id == escrow_id).first()
        if not escrow:
            logger.warning(f"SECURITY: Escrow {escrow_id} not found")
            return False, None, None

        # Get user
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            logger.warning(f"SECURITY: User {user_id} not found")
            return False, escrow, None

        # Check participant authorization
        is_buyer = user.id == escrow.buyer_id
        is_seller = (
            (user.id == escrow.seller_id)
            or (escrow.seller_username == user.username)
            or (escrow.seller_email == user.email)
        )

        # Only allow messaging for active escrows
        if escrow.status not in [
            EscrowStatus.ACTIVE.value,
            EscrowStatus.DISPUTED.value,
            EscrowStatus.COMPLETED.value,
        ]:
            logger.warning(
                f"SECURITY: Messaging attempt on inactive escrow {escrow_id} (status: {escrow.status})"
            )
            return False, escrow, user

        if not (is_buyer or is_seller):
            logger.warning(
                f"SECURITY: Unauthorized messaging attempt by user {user_id} for escrow {escrow_id}"
            )
            return False, escrow, user

        # Additional security: ensure seller has actually accepted (seller_id is set)
        if not escrow.seller_id:
            logger.warning(
                f"SECURITY: Messaging attempt on escrow {escrow_id} without seller acceptance"
            )
            return False, escrow, user

        logger.info(
            f"SECURITY: Authorized participant {user_id} for escrow {escrow_id}"
        )
        return True, escrow, user

    except Exception as e:
        logger.error(f"SECURITY: Error in participant verification: {e}")
        return False, None, None


def log_security_event(
    event_type: str, user_id: int, escrow_id: str | None = None, details: str | None = None
):
    """Log security-related events for audit trail"""
    try:
        message = f"SECURITY_EVENT: {event_type} - User {user_id}"
        if escrow_id:
            message += f" - Escrow {escrow_id}"
        if details:
            message += f" - {details}"
        logger.warning(message)
    except Exception as e:
        logger.error(f"Error logging security event: {e}")


def rate_limit_check(user_id: int, action: str, max_per_minute: int = 10) -> bool:
    """
    Simple rate limiting for messaging and file uploads
    Returns True if action is allowed, False if rate limited
    """
    # This is a placeholder - in production you'd use Redis or similar
    # For now, we'll just log and allow (but the infrastructure is here)
    logger.debug(f"Rate limit check: User {user_id} action {action}")
    return True
