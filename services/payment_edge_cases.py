"""
Comprehensive edge case handling for payment confirmations, partial payments, and timeout scenarios.
Handles real-world payment complexities that can occur in cryptocurrency transactions.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, Tuple
from dataclasses import dataclass

from utils.atomic_transactions import atomic_transaction, locked_escrow_operation
from services.crypto import CryptoServiceAtomic
from models import Escrow, EscrowStatus, Transaction
from utils.universal_id_generator import UniversalIDGenerator
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class PaymentOutcome(Enum):
    """Possible outcomes of payment processing"""

    FULL_PAYMENT_ACCEPTED = "full_payment_accepted"
    PARTIAL_PAYMENT_STORED = "partial_payment_stored"
    OVERPAYMENT_REFUNDED = "overpayment_refunded"
    UNDERPAYMENT_REJECTED = "underpayment_rejected"
    LATE_PAYMENT_REJECTED = "late_payment_rejected"
    DUPLICATE_PAYMENT_IGNORED = "duplicate_payment_ignored"
    INVALID_STATE_REJECTED = "invalid_state_rejected"


@dataclass
class PaymentResult:
    """Result of payment processing with details"""

    outcome: PaymentOutcome
    success: bool
    amount_processed: float
    amount_remaining: float
    amount_refunded: float
    message: str
    escrow_activated: bool = False
    requires_notification: bool = True


class PaymentEdgeCaseHandler:
    """
    Comprehensive handler for payment edge cases and complex scenarios.
    """

    # Configuration constants
    PARTIAL_PAYMENT_MIN_THRESHOLD = 0.10  # 10% minimum for partial payments
    OVERPAYMENT_AUTO_REFUND_THRESHOLD = 1.50  # Auto-refund if >150% paid
    LATE_PAYMENT_GRACE_PERIOD_HOURS = 24  # Hours after escrow expires to accept payment
    AMOUNT_TOLERANCE_CENTS = 0.05  # 5 cent tolerance for amount matching
    MAX_PARTIAL_PAYMENTS = 5  # Maximum number of partial payments allowed

    @classmethod
    def process_payment_with_edge_handling(
        cls,
        escrow_id: str,
        tx_hash: str,
        amount_received: float,
        currency: str,
        confirmations: int = 0,
    ) -> PaymentResult:
        """
        Process payment with comprehensive edge case handling.

        Args:
            escrow_id: Escrow identifier
            tx_hash: Transaction hash
            amount_received: Amount received in USD
            currency: Currency of the payment
            confirmations: Number of blockchain confirmations

        Returns:
            PaymentResult with processing outcome and details
        """
        try:
            with atomic_transaction() as session:
                with locked_escrow_operation(escrow_id, session) as escrow:
                    return cls._process_payment_internal(
                        escrow,
                        tx_hash,
                        amount_received,
                        currency,
                        confirmations,
                        session,
                    )

        except SQLAlchemyError as e:
            logger.error(
                f"Database error processing payment for escrow {escrow_id}: {e}"
            )
            return PaymentResult(
                outcome=PaymentOutcome.INVALID_STATE_REJECTED,
                success=False,
                amount_processed=0.0,
                amount_remaining=0.0,
                amount_refunded=0.0,
                message="Database error during payment processing",
            )
        except ValueError as e:
            logger.error(
                f"Validation error processing payment for escrow {escrow_id}: {e}"
            )
            return PaymentResult(
                outcome=PaymentOutcome.INVALID_STATE_REJECTED,
                success=False,
                amount_processed=0.0,
                amount_remaining=0.0,
                amount_refunded=0.0,
                message=f"Validation error: {str(e)}",
            )
        except Exception as e:
            logger.error(
                f"Unexpected error processing payment for escrow {escrow_id}: {e}"
            )
            return PaymentResult(
                outcome=PaymentOutcome.INVALID_STATE_REJECTED,
                success=False,
                amount_processed=0.0,
                amount_remaining=0.0,
                amount_refunded=0.0,
                message="Unexpected error during payment processing",
            )

    @classmethod
    def _process_payment_internal(
        cls,
        escrow: Escrow,
        tx_hash: str,
        amount_received: float,
        currency: str,
        confirmations: int,
        session,
    ) -> PaymentResult:
        """Internal payment processing with edge case logic"""

        # 1. Validate escrow state and timing
        state_check = cls._validate_escrow_state_and_timing(escrow)
        if not state_check[0]:
            return PaymentResult(
                outcome=state_check[1],
                success=False,
                amount_processed=0.0,
                amount_remaining=0.0,
                amount_refunded=0.0,
                message=state_check[2],
            )

        # 2. Check for duplicate transaction
        if cls._is_duplicate_transaction(escrow, tx_hash, session):
            return PaymentResult(
                outcome=PaymentOutcome.DUPLICATE_PAYMENT_IGNORED,
                success=True,
                amount_processed=0.0,
                amount_remaining=0.0,
                amount_refunded=0.0,
                message="Transaction already processed",
            )

        # 3. Calculate payment details - CONVERT TO DECIMAL ONCE
        amount_received_decimal = Decimal(str(amount_received))
        expected_amount = (
            Decimal(str(escrow.total_amount)) if escrow.total_amount is not None else Decimal("0")
        )
        total_paid_previously = cls._get_total_payments_received(escrow, session)
        total_paid_now = total_paid_previously + amount_received_decimal
        remaining_amount = expected_amount - total_paid_now

        # 4. Record this payment transaction
        cls._record_payment_transaction(
            escrow, tx_hash, float(amount_received_decimal), currency, confirmations, session
        )

        # 5. Determine payment scenario and handle accordingly
        if abs(remaining_amount) <= Decimal(str(cls.AMOUNT_TOLERANCE_CENTS)):
            # Full payment (within tolerance)
            return cls._handle_full_payment(escrow, amount_received_decimal, session)

        elif remaining_amount > Decimal("0"):
            # Underpayment scenario
            return cls._handle_underpayment(
                escrow,
                amount_received_decimal,
                remaining_amount,
                total_paid_now,
                expected_amount,
                session,
            )

        else:
            # Overpayment scenario
            overpaid_amount = abs(remaining_amount)
            return cls._handle_overpayment(
                escrow, amount_received_decimal, overpaid_amount, session
            )

    @classmethod
    def _validate_escrow_state_and_timing(
        cls, escrow: Escrow
    ) -> Tuple[bool, PaymentOutcome, str]:
        """Validate escrow state and check for late payments"""

        # Check if escrow is in valid state for payment
        valid_states = [
            EscrowStatus.PENDING_DEPOSIT.value,
            EscrowStatus.PARTIAL_PAYMENT.value,  # Allow additional payments for partial state
        ]

        if escrow.status not in valid_states:
            return (
                False,
                PaymentOutcome.INVALID_STATE_REJECTED,
                f"Escrow {escrow.escrow_id} is in {escrow.status} state, cannot accept payment",
            )

        # Check for late payment (if escrow has expired)
        if escrow.expires_at is not None:
            grace_period = timedelta(hours=cls.LATE_PAYMENT_GRACE_PERIOD_HOURS)
            if datetime.utcnow() > (escrow.expires_at + grace_period):
                return (
                    False,
                    PaymentOutcome.LATE_PAYMENT_REJECTED,
                    f"Payment received too late for escrow {escrow.escrow_id}",
                )

        return (True, PaymentOutcome.FULL_PAYMENT_ACCEPTED, "Valid state")

    @classmethod
    def _is_duplicate_transaction(cls, escrow: Escrow, tx_hash: str, session) -> bool:
        """Check if this transaction hash was already processed for this escrow"""
        existing_tx = (
            session.query(Transaction)
            .filter(Transaction.escrow_id == escrow.id, Transaction.tx_hash == tx_hash)
            .first()
        )

        return existing_tx is not None

    @classmethod
    def _get_total_payments_received(cls, escrow: Escrow, session) -> float:
        """Calculate total amount already paid for this escrow"""
        from sqlalchemy import func

        total = (
            session.query(func.sum(Transaction.amount))
            .filter(
                Transaction.escrow_id == escrow.id,
                Transaction.transaction_type.in_(["deposit", "partial_deposit"]),
                Transaction.status == "completed",
            )
            .scalar()
        )

        return Decimal(str(total)) if total is not None else Decimal("0")

    @classmethod
    def _record_payment_transaction(
        cls,
        escrow: Escrow,
        tx_hash: str,
        amount: float,
        currency: str,
        confirmations: int,
        session,
    ):
        """Record the payment transaction in the database"""

        # Determine transaction type based on payment completeness
        expected_amount = (
            Decimal(str(escrow.total_amount)) if escrow.total_amount is not None else Decimal("0")
        )
        is_partial = amount < (
            expected_amount * 0.95
        )  # Less than 95% is considered partial

        transaction = Transaction(
            transaction_id=UniversalIDGenerator.generate_transaction_id(),
            user_id=escrow.buyer_id,
            escrow_id=escrow.id,
            transaction_type="partial_deposit" if is_partial else "deposit",
            amount=amount,
            currency=currency,
            status="completed",
            description=f"{currency} payment for escrow {escrow.escrow_id}: ${amount:.2f} USD ({confirmations} confirmations)",
            tx_hash=tx_hash,
            blockchain_address=getattr(escrow, "deposit_address", None),
            confirmations=confirmations,
            confirmed_at=datetime.utcnow(),
        )

        session.add(transaction)
        logger.info(
            f"Recorded payment transaction: {amount} USD for escrow {escrow.escrow_id}"
        )

    @classmethod
    def _handle_full_payment(
        cls, escrow: Escrow, amount_received: float, session
    ) -> PaymentResult:
        """Handle full payment scenario"""

        # Credit user's wallet
        credit_success = CryptoServiceAtomic.credit_user_wallet_atomic(
            user_id=int(escrow.buyer_id),
            amount=amount_received,
            currency="USD",
            escrow_id=int(escrow.id),
            transaction_type="deposit",
            description=f"Full payment for escrow {escrow.escrow_id}: ${amount_received:.2f} USD",
            session=session,
        )

        if not credit_success:
            return PaymentResult(
                outcome=PaymentOutcome.INVALID_STATE_REJECTED,
                success=False,
                amount_processed=0.0,
                amount_remaining=(
                    Decimal(str(escrow.total_amount))
                    if escrow.total_amount is not None
                    else Decimal("0")
                ),
                amount_refunded=0.0,
                message="Failed to credit wallet",
            )

        # Activate escrow
        escrow.status = EscrowStatus.ACTIVE.value
        escrow.payment_confirmed_at = datetime.utcnow()
        escrow.expires_at = datetime.utcnow() + timedelta(hours=24)

        return PaymentResult(
            outcome=PaymentOutcome.FULL_PAYMENT_ACCEPTED,
            success=True,
            amount_processed=amount_received,
            amount_remaining=0.0,
            amount_refunded=0.0,
            message=f"Full payment of ${amount_received:.2f} USD processed successfully",
            escrow_activated=True,
        )

    @classmethod
    def _handle_underpayment(
        cls,
        escrow: Escrow,
        amount_received: float,
        remaining_amount: float,
        total_paid: float,
        expected_amount: float,
        session,
    ) -> PaymentResult:
        """Handle underpayment scenarios"""

        payment_percentage = (total_paid / expected_amount) * 100

        # Check if payment meets minimum threshold
        if payment_percentage < (cls.PARTIAL_PAYMENT_MIN_THRESHOLD * 100):
            return PaymentResult(
                outcome=PaymentOutcome.UNDERPAYMENT_REJECTED,
                success=False,
                amount_processed=0.0,
                amount_remaining=expected_amount,
                amount_refunded=amount_received,  # Will be refunded
                message=f"Payment too small: ${amount_received:.2f} USD (only {payment_percentage:.1f}% of required amount)",
            )

        # Check if too many partial payments
        partial_payment_count = cls._count_partial_payments(escrow, session)
        if partial_payment_count >= cls.MAX_PARTIAL_PAYMENTS:
            return PaymentResult(
                outcome=PaymentOutcome.UNDERPAYMENT_REJECTED,
                success=False,
                amount_processed=0.0,
                amount_remaining=remaining_amount,
                amount_refunded=amount_received,
                message=f"Too many partial payments ({partial_payment_count}). Maximum {cls.MAX_PARTIAL_PAYMENTS} allowed.",
            )

        # Reject partial payment - keep as payment_pending for auto-cancellation
        # This aligns with business logic that doesn't support partial payments
        
        return PaymentResult(
            outcome=PaymentOutcome.UNDERPAYMENT_REJECTED,
            success=False,
            amount_processed=0.0,
            amount_remaining=expected_amount,
            amount_refunded=amount_received,  # Will be refunded
            message=f"Partial payments not supported. Payment ${amount_received:.2f} USD is insufficient (requires ${expected_amount:.2f}). Trade will auto-cancel after timeout.",
        )

    @classmethod
    def _handle_overpayment(
        cls, escrow: Escrow, amount_received: float, overpaid_amount: float, session
    ) -> PaymentResult:
        """Handle overpayment scenarios"""

        expected_amount = (
            Decimal(str(escrow.total_amount)) if escrow.total_amount is not None else Decimal("0")
        )
        overpayment_percentage = (
            (amount_received / expected_amount) * 100 if expected_amount > 0 else 0
        )

        # For significant overpayments, activate escrow and prepare refund
        if overpayment_percentage > (cls.OVERPAYMENT_AUTO_REFUND_THRESHOLD * 100):
            # Credit the expected amount
            credit_success = CryptoServiceAtomic.credit_user_wallet_atomic(
                user_id=int(escrow.buyer_id),
                amount=expected_amount,
                currency="USD",
                escrow_id=int(escrow.id),
                transaction_type="deposit",
                description=f"Escrow payment (overpaid): ${expected_amount:.2f} USD",
                session=session,
            )

            if credit_success:
                escrow.status = EscrowStatus.ACTIVE.value
                escrow.payment_confirmed_at = datetime.utcnow()
                escrow.expires_at = datetime.utcnow() + timedelta(hours=24)

            return PaymentResult(
                outcome=PaymentOutcome.OVERPAYMENT_REFUNDED,
                success=True,
                amount_processed=expected_amount,
                amount_remaining=0.0,
                amount_refunded=overpaid_amount,
                message=f"Overpayment detected: ${overpaid_amount:.2f} will be refunded",
                escrow_activated=credit_success,
            )

        else:
            # Small overpayment - treat as full payment
            credit_success = CryptoServiceAtomic.credit_user_wallet_atomic(
                user_id=int(escrow.buyer_id),
                amount=amount_received,
                currency="USD",
                escrow_id=int(escrow.id),
                transaction_type="deposit",
                description=f"Full payment (slightly overpaid): ${amount_received:.2f} USD",
                session=session,
            )

            if credit_success:
                escrow.status = EscrowStatus.ACTIVE.value
                escrow.payment_confirmed_at = datetime.utcnow()
                escrow.expires_at = datetime.utcnow() + timedelta(hours=24)

            return PaymentResult(
                outcome=PaymentOutcome.FULL_PAYMENT_ACCEPTED,
                success=True,
                amount_processed=amount_received,
                amount_remaining=0.0,
                amount_refunded=0.0,
                message=f"Payment accepted (small overpayment included): ${amount_received:.2f}",
                escrow_activated=credit_success,
            )

    @classmethod
    def _count_partial_payments(cls, escrow: Escrow, session) -> int:
        """Count number of partial payments for this escrow"""
        count = (
            session.query(Transaction)
            .filter(
                Transaction.escrow_id == escrow.id,
                Transaction.transaction_type == "partial_deposit",
                Transaction.status == "completed",
            )
            .count()
        )

        return count

    @classmethod
    async def handle_late_confirmation(
        cls, escrow_id: str, tx_hash: str, amount_usd: float, currency: str
    ) -> PaymentResult:
        """
        Handle payments that confirm after escrow expiration.
        These require special processing and user notification.
        """
        try:
            with atomic_transaction() as session:
                escrow = (
                    session.query(Escrow).filter(Escrow.escrow_id == escrow_id).first()
                )

                if not escrow:
                    return PaymentResult(
                        outcome=PaymentOutcome.INVALID_STATE_REJECTED,
                        success=False,
                        amount_processed=0.0,
                        amount_remaining=0.0,
                        amount_refunded=amount_usd,
                        message="Escrow not found",
                    )

                # Check if escrow is expired
                current_time = datetime.utcnow()
                grace_period = timedelta(hours=cls.LATE_PAYMENT_GRACE_PERIOD_HOURS)

                if escrow.expires_at is not None and current_time > (
                    escrow.expires_at + grace_period
                ):

                    # Late payment beyond grace period - refund user
                    refund_success = CryptoServiceAtomic.credit_user_wallet_atomic(
                        user_id=int(escrow.buyer_id),
                        amount=amount_usd,
                        currency="USD",
                        transaction_type="escrow_refund",
                        description=f"Late payment refund for expired escrow {escrow_id}: ${amount_usd:.2f} USD",
                        session=session,
                    )

                    # Record late payment transaction
                    transaction = Transaction(
                        transaction_id=UniversalIDGenerator.generate_transaction_id(),
                        user_id=int(escrow.buyer_id),
                        escrow_id=int(escrow.id),
                        transaction_type="late_payment_refund",
                        amount=amount_usd,
                        currency=currency,
                        status="completed",
                        description=f"Late payment refund for escrow {escrow_id}",
                        reference=tx_hash,
                        confirmed_at=current_time,
                    )
                    session.add(transaction)

                    return PaymentResult(
                        outcome=PaymentOutcome.LATE_PAYMENT_REJECTED,
                        success=refund_success,
                        amount_processed=0.0,
                        amount_remaining=(
                            Decimal(str(escrow.total_amount))
                            if escrow.total_amount is not None
                            else Decimal("0")
                        ),
                        amount_refunded=amount_usd,
                        message=f"Late payment refunded: escrow expired {cls.LATE_PAYMENT_GRACE_PERIOD_HOURS}h ago",
                    )

                else:
                    # Within grace period - process normally
                    return cls._process_payment_internal(
                        escrow, tx_hash, amount_usd, currency, 0, session
                    )

        except Exception as e:
            logger.error(
                f"Error handling late confirmation for escrow {escrow_id}: {e}"
            )
            return PaymentResult(
                outcome=PaymentOutcome.INVALID_STATE_REJECTED,
                success=False,
                amount_processed=0.0,
                amount_remaining=0.0,
                amount_refunded=0.0,
                message=f"Processing error: {str(e)}",
            )

    @classmethod
    async def process_automatic_refunds(cls) -> Dict[str, int]:
        """
        Process automatic refunds for rejected payments and overpayments.
        This should be called periodically by a background job.
        """
        stats = {
            "overpayments_processed": 0,
            "rejected_payments_refunded": 0,
            "late_payments_refunded": 0,
            "errors": 0,
        }

        try:
            with atomic_transaction():
                # Find transactions that need refunding
                # This would typically query a pending_refunds table or similar
                # For now, this is a placeholder for the refund processing logic

                logger.info("Automatic refund processing completed", extra=stats)
                return stats

        except Exception as e:
            logger.error(f"Error in automatic refund processing: {e}")
            stats["errors"] += 1
            return stats
