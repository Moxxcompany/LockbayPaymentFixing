#!/usr/bin/env python3
"""
Escrow State Machine with Atomic Operations
Comprehensive state management with race condition protection
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from contextlib import contextmanager
from enum import Enum

from database import SessionLocal
from utils.atomic_transactions import atomic_transaction, locked_escrow_operation
from models import EscrowStatus

logger = logging.getLogger(__name__)


class EscrowTransition(Enum):
    """Valid escrow state transitions"""

    # Creation flow
    CREATE = "create"  # None -> CREATED
    START_PAYMENT = "start_payment"  # CREATED -> PAYMENT_PENDING
    CONFIRM_PAYMENT = "confirm_payment"  # PAYMENT_PENDING -> PAYMENT_CONFIRMED
    AWAIT_SELLER = "await_seller"  # PAYMENT_CONFIRMED -> AWAITING_SELLER
    SELLER_ACCEPT = "seller_accept"  # AWAITING_SELLER -> PENDING_DEPOSIT
    ACTIVATE = "activate"  # PENDING_DEPOSIT -> ACTIVE

    # Resolution flow
    RELEASE = "release"  # ACTIVE -> COMPLETED
    REFUND = "refund"  # ACTIVE -> REFUNDED
    DISPUTE = "dispute"  # ACTIVE -> DISPUTED
    RESOLVE_DISPUTE = "resolve_dispute"  # DISPUTED -> COMPLETED/REFUNDED

    # Cancellation flow
    CANCEL = "cancel"  # Multiple states -> CANCELLED
    EXPIRE = "expire"  # PENDING_* -> EXPIRED


class EscrowStateValidator:
    """Validates escrow state transitions and prevents invalid changes"""

    # Valid state transition map
    VALID_TRANSITIONS: Dict[Optional[str], Set[str]] = {
        # From None/Creation
        None: {EscrowStatus.CREATED.value},
        # Creation flow
        EscrowStatus.CREATED.value: {
            EscrowStatus.PAYMENT_PENDING.value,
            EscrowStatus.CANCELLED.value,
        },
        EscrowStatus.PAYMENT_PENDING.value: {
            EscrowStatus.PAYMENT_CONFIRMED.value,
            EscrowStatus.CANCELLED.value,
            EscrowStatus.EXPIRED.value,
        },
        EscrowStatus.PAYMENT_CONFIRMED.value: {
            EscrowStatus.AWAITING_SELLER.value,
            EscrowStatus.CANCELLED.value,
        },
        EscrowStatus.AWAITING_SELLER.value: {
            EscrowStatus.PENDING_SELLER.value,  # Seller accepts
            EscrowStatus.PENDING_DEPOSIT.value,  # Direct to deposit
            EscrowStatus.CANCELLED.value,
            EscrowStatus.EXPIRED.value,
        },
        EscrowStatus.PENDING_SELLER.value: {
            EscrowStatus.PENDING_DEPOSIT.value,
            EscrowStatus.CANCELLED.value,
            EscrowStatus.EXPIRED.value,
        },
        EscrowStatus.PENDING_DEPOSIT.value: {
            EscrowStatus.ACTIVE.value,
            EscrowStatus.CANCELLED.value,
            EscrowStatus.EXPIRED.value,
        },
        # Active state transitions - BUSINESS RULE: User cancellation blocked, admin override allowed
        EscrowStatus.ACTIVE.value: {
            EscrowStatus.COMPLETED.value,  # Release (buyer only)
            EscrowStatus.REFUNDED.value,  # Refund (admin resolution only)
            EscrowStatus.DISPUTED.value,  # Dispute (buyer/seller)
            EscrowStatus.CANCELLED.value,  # Admin override only (validated at handler level)
        },
        # Dispute resolution
        EscrowStatus.DISPUTED.value: {
            EscrowStatus.COMPLETED.value,  # Resolve to seller
            EscrowStatus.REFUNDED.value,  # Resolve to buyer
            EscrowStatus.CANCELLED.value,  # Admin decision
        },
        # Terminal states (no transitions allowed)
        EscrowStatus.COMPLETED.value: set(),
        EscrowStatus.REFUNDED.value: set(),
        EscrowStatus.CANCELLED.value: set(),
        EscrowStatus.EXPIRED.value: set(),
    }

    @classmethod
    def is_valid_transition(
        cls, current_status: Optional[str], new_status: str, is_admin: bool = False
    ) -> bool:
        """Check if state transition is valid with admin context support"""
        valid_next_states = cls.VALID_TRANSITIONS.get(current_status, set())

        # ADMIN OVERRIDE: Allow ACTIVE -> CANCELLED only for admins
        if (
            current_status == EscrowStatus.ACTIVE.value
            and new_status == EscrowStatus.CANCELLED.value
            and not is_admin
        ):
            return False  # Block user cancellation of ACTIVE escrows

        return new_status in valid_next_states

    @classmethod
    def get_valid_transitions(cls, current_status: Optional[str]) -> Set[str]:
        """Get all valid next states for current status"""
        return cls.VALID_TRANSITIONS.get(current_status, set())

    @classmethod
    def is_terminal_state(cls, status: str) -> bool:
        """Check if status is terminal (no further transitions)"""
        return len(cls.VALID_TRANSITIONS.get(status, set())) == 0


class AtomicEscrowOperation:
    """Atomic escrow operations with state validation and locking"""

    def __init__(self, escrow_id: str):
        self.escrow_id = escrow_id
        self.operations = []
        self.validator = EscrowStateValidator()

    @contextmanager
    def transaction(self):
        """Context manager for atomic escrow operations"""
        with atomic_transaction() as session:
            with locked_escrow_operation(self.escrow_id, session) as escrow:
                yield escrow, session

    def change_status(self, new_status: str, **fields) -> bool:
        """Atomically change escrow status with validation"""
        try:
            with self.transaction() as (escrow, session):
                current_status = escrow.status

                # Validate transition
                if not self.validator.is_valid_transition(current_status, new_status):
                    logger.error(
                        f"Invalid escrow transition: {current_status} -> {new_status} for {self.escrow_id}"
                    )
                    return False

                # Apply status change
                escrow.status = new_status
                escrow.updated_at = datetime.utcnow()

                # Apply additional fields
                for field, value in fields.items():
                    if hasattr(escrow, field):
                        setattr(escrow, field, value)
                    else:
                        logger.warning(f"Unknown escrow field: {field}")

                logger.info(
                    f"Escrow {self.escrow_id} status changed: {current_status} -> {new_status}"
                )
                return True

        except Exception as e:
            logger.error(f"Error changing escrow status: {e}")
            return False

    def release_with_payment(
        self, seller_user_id: int, amount: float, currency: str = "USD"
    ) -> bool:
        """Atomically release escrow and credit seller"""
        try:
            with self.transaction() as (escrow, session):
                # Validate current state
                if escrow.status != EscrowStatus.ACTIVE.value:
                    logger.error(
                        f"Cannot release non-active escrow {self.escrow_id}: {escrow.status}"
                    )
                    return False

                # Credit seller wallet atomically within same transaction
                from services.crypto import CryptoServiceAtomic

                credit_success = CryptoServiceAtomic.credit_user_wallet_atomic(
                    user_id=seller_user_id,
                    amount=amount,
                    currency=currency,
                    escrow_id=escrow.id,
                    transaction_type="escrow_release",
                    description=f"💰 Escrow release for #{escrow.escrow_id}: ${amount:.2f}",
                    session=session,
                )

                if not credit_success:
                    logger.error(
                        f"Failed to credit seller for escrow release {self.escrow_id}"
                    )
                    return False

                # Update escrow status
                escrow.status = EscrowStatus.COMPLETED.value
                escrow.completed_at = datetime.utcnow()
                escrow.resolution_type = "released"

                logger.info(
                    f"Successfully released escrow {self.escrow_id} with payment to seller"
                )
                
                # Send admin notification about escrow completion
                try:
                    from services.admin_trade_notifications import admin_trade_notifications
                    from models import User
                    
                    # Get buyer and seller information
                    buyer = session.query(User).filter(User.id == escrow.buyer_id).first()
                    seller = session.query(User).filter(User.id == escrow.seller_id).first() if escrow.seller_id else None
                    
                    buyer_info = (
                        buyer.username or buyer.first_name or f"User_{buyer.telegram_id}"
                        if buyer else "Unknown Buyer"
                    )
                    seller_info = (
                        seller.username or seller.first_name or f"User_{seller.telegram_id}"
                        if seller else escrow.seller_username or escrow.seller_email or "Unknown Seller"
                    )
                    
                    escrow_completion_data = {
                        'escrow_id': escrow.escrow_id,
                        'amount': float(escrow.amount) if escrow.amount else 0.0,
                        'currency': 'USD',
                        'buyer_info': buyer_info,
                        'seller_info': seller_info,
                        'resolution_type': 'released',
                        'completed_at': escrow.completed_at
                    }
                    
                    # Send admin notification asynchronously
                    import asyncio
                    asyncio.create_task(
                        admin_trade_notifications.notify_escrow_completed(escrow_completion_data)
                    )
                    logger.info(f"Admin notification queued for escrow completion: {escrow.escrow_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to queue admin notification for escrow completion: {e}")
                
                return True

        except Exception as e:
            logger.error(f"Error releasing escrow with payment: {e}")
            return False

    def refund_with_payment(
        self, buyer_user_id: int, amount: float, currency: str = "USD"
    ) -> bool:
        """Atomically refund escrow and credit buyer"""
        try:
            with self.transaction() as (escrow, session):
                # Validate current state
                if escrow.status not in [
                    EscrowStatus.ACTIVE.value,
                    EscrowStatus.DISPUTED.value,
                ]:
                    logger.error(
                        f"Cannot refund escrow {self.escrow_id} in status: {escrow.status}"
                    )
                    return False

                # Credit buyer wallet atomically
                from services.crypto import CryptoServiceAtomic

                credit_success = CryptoServiceAtomic.credit_user_wallet_atomic(
                    user_id=buyer_user_id,
                    amount=amount,
                    currency=currency,
                    escrow_id=escrow.id,
                    transaction_type="refund",
                    description=f"💸 Escrow refund for #{escrow.escrow_id}: ${amount:.2f}",
                    session=session,
                )

                if not credit_success:
                    logger.error(
                        f"Failed to credit buyer for escrow refund {self.escrow_id}"
                    )
                    return False

                # Update escrow status
                escrow.status = EscrowStatus.REFUNDED.value
                escrow.completed_at = datetime.utcnow()
                escrow.resolution_type = "refunded"

                logger.info(
                    f"Successfully refunded escrow {self.escrow_id} with payment to buyer"
                )
                
                # Send admin notification about escrow completion (refund)
                try:
                    from services.admin_trade_notifications import admin_trade_notifications
                    from models import User
                    
                    # Get buyer and seller information
                    buyer = session.query(User).filter(User.id == escrow.buyer_id).first()
                    seller = session.query(User).filter(User.id == escrow.seller_id).first() if escrow.seller_id else None
                    
                    buyer_info = (
                        buyer.username or buyer.first_name or f"User_{buyer.telegram_id}"
                        if buyer else "Unknown Buyer"
                    )
                    seller_info = (
                        seller.username or seller.first_name or f"User_{seller.telegram_id}"
                        if seller else escrow.seller_username or escrow.seller_email or "Unknown Seller"
                    )
                    
                    escrow_completion_data = {
                        'escrow_id': escrow.escrow_id,
                        'amount': float(escrow.amount) if escrow.amount else 0.0,
                        'currency': 'USD',
                        'buyer_info': buyer_info,
                        'seller_info': seller_info,
                        'resolution_type': 'refunded',
                        'completed_at': escrow.completed_at
                    }
                    
                    # Send admin notification asynchronously
                    import asyncio
                    asyncio.create_task(
                        admin_trade_notifications.notify_escrow_completed(escrow_completion_data)
                    )
                    logger.info(f"Admin notification queued for escrow refund completion: {escrow.escrow_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to queue admin notification for escrow refund completion: {e}")
                
                return True

        except Exception as e:
            logger.error(f"Error refunding escrow with payment: {e}")
            return False

    def activate_from_deposit(self, tx_hash: str, amount_usd: float) -> bool:
        """Atomically activate escrow from confirmed deposit"""
        try:
            with self.transaction() as (escrow, session):
                # Validate current state
                if escrow.status != EscrowStatus.PENDING_DEPOSIT.value:
                    logger.error(
                        f"Cannot activate escrow {self.escrow_id} from status: {escrow.status}"
                    )
                    return False

                # Update escrow to active
                escrow.status = EscrowStatus.ACTIVE.value
                escrow.payment_confirmed_at = datetime.utcnow()
                escrow.deposit_tx_hash = tx_hash
                # Note: confirmed_amount field doesn't exist in database schema
                # Using amount field instead for tracking confirmed payments

                logger.info(
                    f"Successfully activated escrow {self.escrow_id} from deposit: {amount_usd} USD"
                )
                return True

        except Exception as e:
            logger.error(f"Error activating escrow from deposit: {e}")
            return False

    def cancel_with_refund(
        self, reason: str, refund_amount: Optional[float] = None
    ) -> bool:
        """Atomically cancel escrow with optional refund"""
        try:
            with self.transaction() as (escrow, session):
                # Check if refund is needed and possible
                if refund_amount and refund_amount > 0:
                    from services.crypto import CryptoServiceAtomic

                    refund_success = CryptoServiceAtomic.credit_user_wallet_atomic(
                        user_id=escrow.buyer_id,
                        amount=refund_amount,
                        currency="USD",
                        escrow_id=escrow.id,
                        transaction_type="refund",
                        description=f"💸 Cancellation refund for #{escrow.escrow_id}: ${refund_amount:.2f}",
                        session=session,
                    )

                    if not refund_success:
                        logger.error(
                            f"Failed to process refund for cancelled escrow {self.escrow_id}"
                        )
                        return False

                # Update escrow status
                escrow.status = EscrowStatus.CANCELLED.value
                escrow.updated_at = datetime.utcnow()
                escrow.cancelled_reason = reason

                logger.info(
                    f"Successfully cancelled escrow {self.escrow_id} with reason: {reason}"
                )
                return True

        except Exception as e:
            logger.error(f"Error cancelling escrow: {e}")
            return False


class EscrowConcurrencyManager:
    """Manages concurrent escrow operations to prevent race conditions"""

    @staticmethod
    def get_escrow_operation(escrow_id: str) -> AtomicEscrowOperation:
        """Get atomic operation manager for escrow"""
        return AtomicEscrowOperation(escrow_id)

    @staticmethod
    def batch_process_escrows(
        escrow_operations: List[Tuple[str, str, Dict]],
    ) -> Dict[str, bool]:
        """Process multiple escrow operations in order with proper locking"""
        results = {}

        for escrow_id, operation, params in escrow_operations:
            try:
                op_manager = AtomicEscrowOperation(escrow_id)

                if operation == "change_status":
                    results[escrow_id] = op_manager.change_status(**params)
                elif operation == "release":
                    results[escrow_id] = op_manager.release_with_payment(**params)
                elif operation == "refund":
                    results[escrow_id] = op_manager.refund_with_payment(**params)
                elif operation == "cancel":
                    results[escrow_id] = op_manager.cancel_with_refund(**params)
                else:
                    logger.error(f"Unknown escrow operation: {operation}")
                    results[escrow_id] = False

            except Exception as e:
                logger.error(f"Error processing escrow {escrow_id}: {e}")
                results[escrow_id] = False

        return results

    @staticmethod
    def validate_escrow_transition(escrow_id: str, new_status: str) -> bool:
        """Validate if escrow transition is allowed using unified validation system"""
        try:
            with SessionLocal() as session:
                from models import Escrow
                from utils.status_flows import UnifiedTransitionValidator, UnifiedTransactionType

                escrow = (
                    session.query(Escrow).filter(Escrow.escrow_id == escrow_id).first()
                )

                if not escrow:
                    return False

                # Use unified validation system for consistency
                validator = UnifiedTransitionValidator()
                result = validator.validate_transition(
                    current_status=str(escrow.status),
                    new_status=new_status,
                    transaction_type=UnifiedTransactionType.ESCROW
                )
                
                return result.is_valid

        except Exception as e:
            logger.error(f"Error validating escrow transition: {e}")
            return False

    @staticmethod
    def get_escrow_status_safely(escrow_id: str) -> Optional[str]:
        """Get current escrow status without locking"""
        try:
            with SessionLocal() as session:
                from models import Escrow

                escrow = (
                    session.query(Escrow).filter(Escrow.escrow_id == escrow_id).first()
                )
                return str(escrow.status) if escrow else None

        except Exception as e:
            logger.error(f"Error getting escrow status: {e}")
            return None


# Global convenience functions
def atomic_escrow_operation(escrow_id: str) -> AtomicEscrowOperation:
    """Create atomic escrow operation manager"""
    return AtomicEscrowOperation(escrow_id)


def validate_transition(current_status: Optional[str], new_status: str) -> bool:
    """Quick transition validation"""
    return EscrowStateValidator.is_valid_transition(current_status, new_status)


def get_valid_next_states(current_status: str) -> Set[str]:
    """Get valid next states for current status"""
    return EscrowStateValidator.get_valid_transitions(current_status)


# Export main classes and functions
__all__ = [
    "AtomicEscrowOperation",
    "EscrowStateValidator",
    "EscrowConcurrencyManager",
    "EscrowTransition",
    "atomic_escrow_operation",
    "validate_transition",
    "get_valid_next_states",
]
