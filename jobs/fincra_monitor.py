#!/usr/bin/env python3
"""Fincra Real-time Payment Monitoring"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from database import SessionLocal
from models import Transaction, TransactionType, User, UnifiedTransactionStatus
from services.fincra_service import fincra_service
from utils.financial_audit_logger import (
    FinancialAuditLogger, 
    FinancialEventType, 
    EntityType, 
    FinancialContext
)
from utils.unified_transaction_state_validator import (
    UnifiedTransactionStateValidator,
    StateTransitionError
)

logger = logging.getLogger(__name__)

# Initialize financial audit logger for comprehensive NGN monitoring tracking
audit_logger = FinancialAuditLogger()


class FincraMonitor:
    """Monitor NGN payments for real-time confirmation with Fincra's superior API"""

    def __init__(self):
        self.session = None

    async def check_pending_ngn_payments(self):
        """Check all pending NGN payments for confirmation"""
        session = SessionLocal()
        try:
            # Get pending NGN transactions from last 24 hours
            cutoff_time = datetime.utcnow() - timedelta(hours=24)

            pending_transactions = (
                session.query(Transaction)
                .filter(
                    Transaction.currency == "NGN",
                    Transaction.status == "pending",
                    Transaction.transaction_type == TransactionType.DEPOSIT.value,
                    Transaction.created_at >= cutoff_time,
                )
                .all()
            )

            # AUDIT: Log NGN payment status check initiation
            audit_logger.log_financial_event(
                event_type=FinancialEventType.NGN_PAYMENT_STATUS_CHECKED,
                entity_type=EntityType.NGN_PAYMENT,
                entity_id=f"status_check_{int(__import__('time').time())}",
                user_id=None,
                financial_context=FinancialContext(currency="NGN"),
                previous_state=None,
                new_state="checking",
                additional_data={
                    "pending_count": len(pending_transactions),
                    "source": "fincra_monitor.check_pending_ngn_payments"
                }
            )

            logger.info(
                f"Checking {len(pending_transactions)} pending NGN payments with Fincra"
            )

            for transaction in pending_transactions:
                await self._check_transaction_status(transaction, session)

        except Exception as e:
            logger.error(f"Error checking pending NGN payments: {e}")
        finally:
            session.close()

    async def _check_transaction_status(self, transaction: Transaction, session):
        """Check individual transaction status with Fincra's real-time API"""
        try:
            if not transaction.blockchain_address:
                logger.warning(f"No reference for transaction {transaction.id}")
                return

            # Get string value from database column
            reference = str(transaction.blockchain_address)

            # First try new transfer status API for real-time updates
            status_result = await fincra_service.check_transfer_status_by_reference(
                reference
            )

            if not status_result:
                # Fallback to payment verification for backwards compatibility
                status_result = await fincra_service.verify_payment(reference)

            if status_result:
                current_status = status_result.get("status", "pending").lower()

                if (
                    current_status in ["successful", "completed", "success"]
                    and str(transaction.status) == "pending"
                ):
                    # AUDIT: Log NGN transaction reconciliation - BEFORE status update
                    audit_logger.log_financial_event(
                        event_type=FinancialEventType.NGN_TRANSACTION_RECONCILED,
                        entity_type=EntityType.NGN_PAYMENT,
                        entity_id=reference,
                        user_id=transaction.user_id,
                        financial_context=FinancialContext(
                            amount=Decimal(str(transaction.amount)),
                            currency="NGN"
                        ),
                        previous_state="pending",
                        new_state="confirmed",
                        related_entities={
                            "transaction_id": str(transaction.id),
                            "reference": reference
                        },
                        additional_data={
                            "fincra_status": current_status,
                            "source": "fincra_monitor._check_transaction_status"
                        }
                    )
                    
                    # Transfer/payment confirmed - update transaction with validation
                    try:
                        current_status = UnifiedTransactionStatus(transaction.status)
                        is_valid, reason = UnifiedTransactionStateValidator.validate_transition(
                            current_status, 
                            UnifiedTransactionStatus.COMPLETED,
                            transaction_id=str(transaction.id)
                        )
                        
                        if is_valid:
                            transaction.status = "completed"  # type: ignore
                            transaction.confirmed_at = datetime.utcnow()  # type: ignore

                            # Add real-time transfer details if available
                            if "transfer_id" in status_result:
                                transaction.blockchain_tx_id = status_result.get("transfer_id")  # type: ignore

                            session.commit()
                        else:
                            logger.error(
                                f"🚫 FINCRA_TX_TRANSITION_BLOCKED: {current_status.value}→COMPLETED "
                                f"for transaction {transaction.id}: {reason}"
                            )
                            # Webhook idempotency - acknowledge but don't process duplicate
                            return
                    except StateTransitionError as e:
                        logger.error(
                            f"🚫 FINCRA_TX_TRANSITION_BLOCKED: Invalid state transition for "
                            f"transaction {transaction.id}: {e}"
                        )
                        # Webhook idempotency - late/duplicate webhook, acknowledge but don't process
                        return
                    except Exception as e:
                        logger.error(
                            f"🚫 FINCRA_TX_VALIDATION_ERROR: Error validating transition for "
                            f"transaction {transaction.id}: {e}"
                        )
                        # Continue with status update for unknown status values (legacy compatibility)
                        transaction.status = "completed"  # type: ignore
                        transaction.confirmed_at = datetime.utcnow()  # type: ignore
                        session.commit()

                    recipient_info = ""
                    if status_result.get("recipient_name"):
                        recipient_info = f" to {status_result['recipient_name']}"
                    elif status_result.get("bank_name"):
                        recipient_info = f" via {status_result['bank_name']}"

                    logger.info(
                        f"✅ NGN transfer confirmed: {transaction.blockchain_address} for ${transaction.amount}{recipient_info}"
                    )

                    # Handle confirmed payment (credit wallet, etc.)
                    await self._handle_confirmed_payment(transaction, session)

                elif current_status in ["failed", "cancelled", "rejected"]:
                    # Transfer/payment failed - update transaction with validation
                    try:
                        tx_current_status = UnifiedTransactionStatus(transaction.status)
                        is_valid, reason = UnifiedTransactionStateValidator.validate_transition(
                            tx_current_status,
                            UnifiedTransactionStatus.FAILED,
                            transaction_id=str(transaction.id)
                        )
                        
                        if is_valid:
                            transaction.status = "failed"  # type: ignore
                            session.commit()

                            failure_reason = status_result.get(
                                "failure_reason", "Unknown error"
                            )
                            logger.warning(
                                f"❌ NGN transfer failed: {transaction.blockchain_address} - {failure_reason}"
                            )
                        else:
                            logger.error(
                                f"🚫 FINCRA_TX_TRANSITION_BLOCKED: {tx_current_status.value}→FAILED "
                                f"for transaction {transaction.id}: {reason}"
                            )
                            # Webhook idempotency - acknowledge but don't process duplicate
                            return
                    except StateTransitionError as e:
                        logger.error(
                            f"🚫 FINCRA_TX_TRANSITION_BLOCKED: Invalid state transition for "
                            f"transaction {transaction.id}: {e}"
                        )
                        # Webhook idempotency - late/duplicate webhook, acknowledge but don't process
                        return
                    except Exception as e:
                        logger.error(
                            f"🚫 FINCRA_TX_VALIDATION_ERROR: Error validating transition for "
                            f"transaction {transaction.id}: {e}"
                        )
                        # Continue with status update for unknown status values (legacy compatibility)
                        transaction.status = "failed"  # type: ignore
                        session.commit()
                        
                        failure_reason = status_result.get(
                            "failure_reason", "Unknown error"
                        )
                        logger.warning(
                            f"❌ NGN transfer failed: {transaction.blockchain_address} - {failure_reason}"
                        )

        except Exception as e:
            logger.error(f"Error checking transaction {transaction.id}: {e}")

    async def _handle_confirmed_payment(self, transaction: "Transaction", session):
        """Handle confirmed payment - credit wallet or activate escrow"""
        try:
            if transaction.transaction_type == "deposit":
                # CRITICAL SECURITY FIX: Check for duplicate NGN payment processing
                existing_wallet_credit = session.query(Transaction).filter(
                    Transaction.user_id == transaction.user_id,
                    Transaction.transaction_type == "wallet_deposit",
                    Transaction.description.contains(f"NGN TX: {transaction.id}"),
                    Transaction.status == "completed"
                ).first()
                
                if existing_wallet_credit:
                    logger.warning(f"🚨 DUPLICATE BLOCKED: NGN payment {transaction.id} already credited to wallet")
                    return
                
                # Credit user's wallet for NGN deposit
                from services.crypto import CryptoServiceAtomic
                
                credit_success = CryptoServiceAtomic.credit_user_wallet_atomic(
                    user_id=transaction.user_id,
                    amount=float(transaction.amount),
                    currency="USD",
                    transaction_type="wallet_deposit",
                    description=f"NGN payment confirmed: +${transaction.amount:.2f} (NGN TX: {transaction.id})",
                    session=session
                )
                
                if not credit_success:
                    logger.error(f"Failed to credit wallet for NGN payment {transaction.id}")
                    return
                
                logger.info(f"✅ Wallet credited: ${transaction.amount:.2f} USD for NGN payment {transaction.id}")
                
                from services.consolidated_notification_service import (
                    consolidated_notification_service as NotificationService,
                )
                from telegram import Bot
                from config import Config

                # Send notification to user about confirmed deposit
                if Config.BOT_TOKEN:
                    user = (
                        session.query(User)
                        .filter(User.id == transaction.user_id)
                        .first()
                    )
                    if user and user.telegram_id:
                        bot = Bot(Config.BOT_TOKEN)
                        await NotificationService.send_telegram_message(
                            bot,
                            int(user.telegram_id),
                            f"✅ NGN payment confirmed! ${transaction.amount:.2f} has been credited to your wallet.",
                        )

        except Exception as e:
            logger.error(f"Error handling confirmed payment notification: {e}")


# Global monitor instance
fincra_monitor = FincraMonitor()


async def check_ngn_payments():
    """Background job to check NGN payment confirmations with Fincra"""
    await fincra_monitor.check_pending_ngn_payments()
