"""
Comprehensive Escrow Validation Service
Enforces business rules for escrow operations and state transitions.
"""

import logging
from typing import Dict, Any, Optional
from models import Escrow, EscrowStatus
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class EscrowValidationService:
    """Service for validating escrow operations and enforcing business rules"""

    @classmethod
    def validate_cancellation(
        cls,
        escrow: Escrow,
        user_id: int,
        is_admin: bool = False,
        session: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Validate if an escrow can be cancelled based on business rules

        Business Rules:
        - ACTIVE escrows cannot be cancelled by users (must dispute or release)
        - Only admins can cancel ACTIVE escrows (administrative override)
        - Buyers can only cancel their own pre-acceptance escrows
        - Sellers cannot cancel any escrows (they decline invitations instead)

        Returns:
            Dict with validation results:
            - allowed: bool
            - reason: str (if not allowed)
            - action_type: str (cancellation type)
        """
        try:
            if not escrow:
                return {
                    "allowed": False,
                    "reason": "Escrow not found",
                    "action_type": "invalid",
                }

            # Check if user is the buyer
            is_buyer = escrow.buyer_id == user_id

            # Sellers cannot cancel escrows - they decline invitations
            if not is_buyer and not is_admin:
                return {
                    "allowed": False,
                    "reason": "Only buyers can cancel escrows. Sellers decline invitations.",
                    "action_type": "unauthorized",
                }

            # BUSINESS RULE: ACTIVE escrows cannot be cancelled by users
            if str(escrow.status) == EscrowStatus.ACTIVE.value:
                if is_admin:
                    return {
                        "allowed": True,
                        "reason": "Admin override for ACTIVE escrow",
                        "action_type": "admin_cancellation",
                    }
                else:
                    return {
                        "allowed": False,
                        "reason": "ACTIVE escrows cannot be cancelled. Please dispute or release funds.",
                        "action_type": "active_escrow_restriction",
                    }

            # Check if escrow is in cancellable state for users
            user_cancellable_states = [
                EscrowStatus.CREATED.value,
                EscrowStatus.PAYMENT_PENDING.value,
                EscrowStatus.PAYMENT_CONFIRMED.value,
                EscrowStatus.AWAITING_SELLER.value,
                EscrowStatus.PENDING_SELLER.value,
                EscrowStatus.PENDING_DEPOSIT.value,
            ]

            # Admin can cancel additional states
            admin_cancellable_states = user_cancellable_states + [
                EscrowStatus.ACTIVE.value,
                EscrowStatus.DISPUTED.value,
            ]

            allowed_states = (
                admin_cancellable_states if is_admin else user_cancellable_states
            )

            if str(escrow.status) not in allowed_states:
                return {
                    "allowed": False,
                    "reason": f"Cannot cancel escrow in {escrow.status.replace('_', ' ').title()} status",
                    "action_type": "invalid_status",
                }

            # Validation passed
            return {
                "allowed": True,
                "reason": "Cancellation allowed",
                "action_type": (
                    "admin_cancellation" if is_admin else "buyer_cancellation"
                ),
            }

        except Exception as e:
            logger.error(f"Error validating escrow cancellation: {e}")
            return {
                "allowed": False,
                "reason": f"Validation error: {str(e)}",
                "action_type": "error",
            }

    @classmethod
    def validate_release(
        cls, escrow: Escrow, user_id: int, session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Validate if an escrow can be released by the buyer

        Business Rules:
        - Only buyers can release funds
        - Escrow must be ACTIVE
        - Cannot release disputed escrows (must resolve dispute first)
        """
        try:
            if not escrow:
                return {"allowed": False, "reason": "Escrow not found"}

            # Check if user is the buyer
            if escrow.buyer_id != user_id:
                return {
                    "allowed": False,
                    "reason": "Only buyers can release escrow funds",
                }

            # Check escrow status
            if escrow.status != EscrowStatus.ACTIVE.value:
                return {
                    "allowed": False,
                    "reason": f"Cannot release escrow in {escrow.status.replace('_', ' ').title()} status. Must be ACTIVE.",
                }

            return {"allowed": True, "reason": "Release allowed"}

        except Exception as e:
            logger.error(f"Error validating escrow release: {e}")
            return {"allowed": False, "reason": f"Validation error: {str(e)}"}

    @classmethod
    def validate_dispute(
        cls, escrow: Escrow, user_id: int, session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Validate if a dispute can be opened for an escrow

        Business Rules:
        - Only buyers or sellers involved in the escrow can open disputes
        - Escrow must be ACTIVE
        - Cannot dispute already disputed escrows
        """
        try:
            if not escrow:
                return {"allowed": False, "reason": "Escrow not found"}

            # Check if user is involved in the escrow
            is_buyer = escrow.buyer_id == user_id
            is_seller = escrow.seller_id == user_id

            if not (is_buyer or is_seller):
                return {
                    "allowed": False,
                    "reason": "Only escrow participants can open disputes",
                }

            # Check escrow status
            if escrow.status != EscrowStatus.ACTIVE.value:
                return {
                    "allowed": False,
                    "reason": f"Cannot dispute escrow in {escrow.status.replace('_', ' ').title()} status. Must be ACTIVE.",
                }

            return {"allowed": True, "reason": "Dispute allowed"}

        except Exception as e:
            logger.error(f"Error validating escrow dispute: {e}")
            return {"allowed": False, "reason": f"Validation error: {str(e)}"}

    @classmethod
    def get_available_actions(
        cls, escrow: Escrow, user_id: int, is_admin: bool = False
    ) -> Dict[str, bool]:
        """
        Get all available actions for a user on a specific escrow

        Returns:
            Dict with action availability:
            - can_cancel: bool
            - can_release: bool
            - can_dispute: bool
            - can_admin_cancel: bool (admin only)
        """
        try:
            cancellation_validation = cls.validate_cancellation(
                escrow, user_id, is_admin
            )
            release_validation = cls.validate_release(escrow, user_id)
            dispute_validation = cls.validate_dispute(escrow, user_id)

            return {
                "can_cancel": cancellation_validation["allowed"] and not is_admin,
                "can_release": release_validation["allowed"],
                "can_dispute": dispute_validation["allowed"],
                "can_admin_cancel": is_admin and cancellation_validation["allowed"],
            }

        except Exception as e:
            logger.error(f"Error getting available escrow actions: {e}")
            return {
                "can_cancel": False,
                "can_release": False,
                "can_dispute": False,
                "can_admin_cancel": False,
            }
