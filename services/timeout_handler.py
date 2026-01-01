"""
Systematic Timeout Handler Service
Provides unified timeout detection and handling across all system components
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)


class TimeoutType(Enum):
    """Types of timeouts in the system"""
    EXCHANGE_PAYMENT = "exchange_payment"
    EXCHANGE_PROCESSING = "exchange_processing"
    ESCROW_PAYMENT = "escrow_payment"
    ESCROW_RESPONSE = "escrow_response"
    RATE_LOCK = "rate_lock"
    EMAIL_VERIFICATION = "email_verification"
    OTP_VERIFICATION = "otp_verification"
    CONVERSATION_SESSION = "conversation_session"
    WEBHOOK_RESPONSE = "webhook_response"
    CASHOUT_PROCESSING = "cashout_processing"


class TimeoutAction(Enum):
    """Actions to take when timeout is detected"""
    CANCEL_ORDER = "cancel_order"
    REFUND_PAYMENT = "refund_payment"
    SEND_REMINDER = "send_reminder"
    ESCALATE_MANUAL = "escalate_manual"
    RETRY_OPERATION = "retry_operation"
    CLEANUP_RESOURCE = "cleanup_resource"
    MARK_EXPIRED = "mark_expired"


@dataclass
class TimeoutRule:
    """Configuration for timeout detection and handling"""
    timeout_type: TimeoutType
    timeout_duration: timedelta
    warning_threshold: Optional[timedelta]  # Send warning before timeout
    action: TimeoutAction
    retry_count: int = 0
    escalate_after: Optional[timedelta] = None
    enabled: bool = True


@dataclass
class TimeoutEvent:
    """Represents a detected timeout event"""
    timeout_type: TimeoutType
    entity_id: str
    entity_type: str  # 'exchange_order', 'escrow', etc.
    user_id: int
    timeout_at: datetime
    detected_at: datetime
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    additional_data: Dict[str, Any] = None


class SystematicTimeoutHandler:
    """Unified timeout detection and handling service"""
    
    # Default timeout rules configuration
    DEFAULT_TIMEOUT_RULES = [
        TimeoutRule(
            timeout_type=TimeoutType.EXCHANGE_PAYMENT,
            timeout_duration=timedelta(hours=1),
            warning_threshold=timedelta(minutes=45),
            action=TimeoutAction.CANCEL_ORDER,
            escalate_after=timedelta(hours=2)
        ),
        TimeoutRule(
            timeout_type=TimeoutType.EXCHANGE_PROCESSING,
            timeout_duration=timedelta(hours=4),
            warning_threshold=timedelta(hours=3),
            action=TimeoutAction.ESCALATE_MANUAL,
            escalate_after=timedelta(hours=6)
        ),
        TimeoutRule(
            timeout_type=TimeoutType.ESCROW_PAYMENT,
            timeout_duration=timedelta(minutes=15),  # CRITICAL FIX: 15 minutes for payment timeout
            warning_threshold=timedelta(minutes=10),  # Warn at 10 minutes
            action=TimeoutAction.CANCEL_ORDER,
            escalate_after=timedelta(minutes=30)  # Escalate if still unresolved after 30 minutes
        ),
        TimeoutRule(
            timeout_type=TimeoutType.ESCROW_RESPONSE,
            timeout_duration=timedelta(hours=72),
            warning_threshold=timedelta(hours=60),
            action=TimeoutAction.SEND_REMINDER,
            escalate_after=timedelta(hours=96)
        ),
        TimeoutRule(
            timeout_type=TimeoutType.RATE_LOCK,
            timeout_duration=timedelta(minutes=10),
            warning_threshold=None,
            action=TimeoutAction.CLEANUP_RESOURCE,
            escalate_after=None
        ),
        TimeoutRule(
            timeout_type=TimeoutType.EMAIL_VERIFICATION,
            timeout_duration=timedelta(hours=24),
            warning_threshold=timedelta(hours=20),
            action=TimeoutAction.CLEANUP_RESOURCE,
            escalate_after=None
        ),
        TimeoutRule(
            timeout_type=TimeoutType.OTP_VERIFICATION,
            timeout_duration=timedelta(minutes=10),
            warning_threshold=timedelta(minutes=8),
            action=TimeoutAction.CLEANUP_RESOURCE,
            escalate_after=None
        ),
        TimeoutRule(
            timeout_type=TimeoutType.CONVERSATION_SESSION,
            timeout_duration=timedelta(hours=1),
            warning_threshold=None,
            action=TimeoutAction.CLEANUP_RESOURCE,
            escalate_after=None
        ),
        TimeoutRule(
            timeout_type=TimeoutType.WEBHOOK_RESPONSE,
            timeout_duration=timedelta(minutes=30),
            warning_threshold=None,
            action=TimeoutAction.RETRY_OPERATION,
            retry_count=3,
            escalate_after=timedelta(hours=2)
        ),
        TimeoutRule(
            timeout_type=TimeoutType.CASHOUT_PROCESSING,
            timeout_duration=timedelta(hours=6),
            warning_threshold=timedelta(hours=4),
            action=TimeoutAction.ESCALATE_MANUAL,
            escalate_after=timedelta(hours=12)
        ),
    ]
    
    @classmethod
    async def scan_for_timeouts(cls) -> List[TimeoutEvent]:
        """
        Scan the entire system for timeout events
        
        Returns:
            List of detected timeout events
        """
        detected_timeouts = []
        
        try:
            from database import SessionLocal
            session = SessionLocal()
            
            try:
                # Scan all timeout types
                for rule in cls.DEFAULT_TIMEOUT_RULES:
                    if not rule.enabled:
                        continue
                        
                    timeouts = await cls._scan_timeout_type(session, rule)
                    detected_timeouts.extend(timeouts)
                
                # Log summary
                if detected_timeouts:
                    timeout_summary = {}
                    for timeout in detected_timeouts:
                        timeout_type = timeout.timeout_type.value
                        timeout_summary[timeout_type] = timeout_summary.get(timeout_type, 0) + 1
                    
                    logger.info(f"🕐 TIMEOUT_SCAN_COMPLETED: Found {len(detected_timeouts)} timeouts: {timeout_summary}")
                else:
                    logger.debug("🕐 TIMEOUT_SCAN: No timeouts detected")
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error in timeout scan: {e}")
        
        return detected_timeouts
    
    @classmethod
    async def _scan_timeout_type(
        cls,
        session,
        rule: TimeoutRule
    ) -> List[TimeoutEvent]:
        """Scan for specific timeout type"""
        timeouts = []
        
        try:
            if rule.timeout_type == TimeoutType.EXCHANGE_PAYMENT:
                timeouts.extend(await cls._scan_exchange_payment_timeouts(session, rule))
            
            elif rule.timeout_type == TimeoutType.EXCHANGE_PROCESSING:
                timeouts.extend(await cls._scan_exchange_processing_timeouts(session, rule))
            
            elif rule.timeout_type == TimeoutType.ESCROW_PAYMENT:
                timeouts.extend(await cls._scan_escrow_payment_timeouts(session, rule))
            
            elif rule.timeout_type == TimeoutType.ESCROW_RESPONSE:
                timeouts.extend(await cls._scan_escrow_response_timeouts(session, rule))
            
            elif rule.timeout_type == TimeoutType.RATE_LOCK:
                timeouts.extend(await cls._scan_rate_lock_timeouts(session, rule))
            
            elif rule.timeout_type == TimeoutType.EMAIL_VERIFICATION:
                timeouts.extend(await cls._scan_email_verification_timeouts(session, rule))
            
            elif rule.timeout_type == TimeoutType.OTP_VERIFICATION:
                timeouts.extend(await cls._scan_otp_verification_timeouts(session, rule))
            
            elif rule.timeout_type == TimeoutType.CONVERSATION_SESSION:
                timeouts.extend(await cls._scan_conversation_session_timeouts(session, rule))
            
            elif rule.timeout_type == TimeoutType.WEBHOOK_RESPONSE:
                timeouts.extend(await cls._scan_webhook_response_timeouts(session, rule))
            
            elif rule.timeout_type == TimeoutType.CASHOUT_PROCESSING:
                timeouts.extend(await cls._scan_cashout_processing_timeouts(session, rule))
                
        except Exception as e:
            logger.error(f"Error scanning {rule.timeout_type.value} timeouts: {e}")
        
        return timeouts
    
    @classmethod
    async def _scan_exchange_payment_timeouts(
        cls,
        session,
        rule: TimeoutRule
    ) -> List[TimeoutEvent]:
        """Scan for exchange payment timeouts"""
        from models import ExchangeOrder
        
        timeouts = []
        cutoff_time = datetime.utcnow() - rule.timeout_duration
        
        # Check ExchangeOrder payment timeouts
        expired_orders = (
            session.query(ExchangeOrder)
            .filter(
                ExchangeOrder.status.in_(["created", "rate_locked", "payment_pending"]),
                ExchangeOrder.created_at < cutoff_time,
                ExchangeOrder.completed_at.is_(None)
            )
            .all()
        )
        
        for order in expired_orders:
            timeouts.append(TimeoutEvent(
                timeout_type=rule.timeout_type,
                entity_id=str(order.id),
                entity_type="exchange_order",
                user_id=order.user_id,
                timeout_at=order.created_at + rule.timeout_duration,
                detected_at=datetime.utcnow(),
                amount=order.source_amount,
                currency=order.source_currency,
                additional_data={"order_type": order.order_type}
            ))
        
        return timeouts
    
    @classmethod
    async def _scan_exchange_processing_timeouts(
        cls,
        session,
        rule: TimeoutRule
    ) -> List[TimeoutEvent]:
        """Scan for exchange processing timeouts"""
        from models import ExchangeOrder
        
        timeouts = []
        cutoff_time = datetime.utcnow() - rule.timeout_duration
        
        # Check stuck processing orders
        stuck_orders = (
            session.query(ExchangeOrder)
            .filter(
                ExchangeOrder.status.in_(["processing", "payment_confirmed"]),
                ExchangeOrder.updated_at < cutoff_time,
                ExchangeOrder.completed_at.is_(None)
            )
            .all()
        )
        
        for order in stuck_orders:
            timeouts.append(TimeoutEvent(
                timeout_type=rule.timeout_type,
                entity_id=str(order.id),
                entity_type="exchange_order",
                user_id=order.user_id,
                timeout_at=order.updated_at + rule.timeout_duration,
                detected_at=datetime.utcnow(),
                amount=order.source_amount,
                currency=order.source_currency,
                additional_data={"order_type": order.order_type}
            ))
        
        return timeouts
    
    @classmethod
    async def _scan_escrow_payment_timeouts(
        cls,
        session,
        rule: TimeoutRule
    ) -> List[TimeoutEvent]:
        """Scan for escrow payment timeouts"""
        from models import Escrow
        
        timeouts = []
        cutoff_time = datetime.utcnow() - rule.timeout_duration
        
        # Check escrows waiting for payment
        timeout_escrows = (
            session.query(Escrow)
            .filter(
                Escrow.status.in_(["pending_payment", "awaiting_deposit", "payment_pending", "awaiting_payment"]),  # CRITICAL FIX: Include payment_pending status
                Escrow.created_at < cutoff_time,
                Escrow.completed_at.is_(None)  # Use completed_at instead of resolved_at
            )
            .all()
        )
        
        for escrow in timeout_escrows:
            timeouts.append(TimeoutEvent(
                timeout_type=rule.timeout_type,
                entity_id=escrow.escrow_id,
                entity_type="escrow",
                user_id=escrow.buyer_id,
                timeout_at=escrow.created_at + rule.timeout_duration,
                detected_at=datetime.utcnow(),
                amount=escrow.amount,
                currency="USD",
                additional_data={"seller_id": escrow.seller_id}
            ))
        
        return timeouts
    
    @classmethod
    async def _scan_escrow_response_timeouts(
        cls,
        session,
        rule: TimeoutRule
    ) -> List[TimeoutEvent]:
        """Scan for escrow response timeouts"""
        from models import Escrow
        
        timeouts = []
        cutoff_time = datetime.utcnow() - rule.timeout_duration
        
        # Check escrows waiting for seller response
        timeout_escrows = (
            session.query(Escrow)
            .filter(
                Escrow.status.in_(["pending_seller_confirmation", "active"]),
                Escrow.updated_at < cutoff_time,
                Escrow.completed_at.is_(None)  # Use completed_at instead of resolved_at
            )
            .all()
        )
        
        for escrow in timeout_escrows:
            timeouts.append(TimeoutEvent(
                timeout_type=rule.timeout_type,
                entity_id=escrow.escrow_id,
                entity_type="escrow",
                user_id=escrow.seller_id,
                timeout_at=escrow.updated_at + rule.timeout_duration,
                detected_at=datetime.utcnow(),
                amount=escrow.amount,
                currency="USD",
                additional_data={"buyer_id": escrow.buyer_id}
            ))
        
        return timeouts
    
    @classmethod
    async def _scan_rate_lock_timeouts(
        cls,
        session,
        rule: TimeoutRule
    ) -> List[TimeoutEvent]:
        """Scan for expired rate locks"""
        from models import ExchangeOrder
        
        timeouts = []
        now = datetime.utcnow()
        
        # Check expired rate locks in ExchangeOrder
        expired_locks = (
            session.query(ExchangeOrder)
            .filter(
                ExchangeOrder.rate_lock_expires_at < now,
                ExchangeOrder.status.in_(["rate_locked", "created"]),
                ExchangeOrder.completed_at.is_(None)
            )
            .all()
        )
        
        for order in expired_locks:
            timeouts.append(TimeoutEvent(
                timeout_type=rule.timeout_type,
                entity_id=str(order.id),
                entity_type="exchange_order",
                user_id=order.user_id,
                timeout_at=order.rate_lock_expires_at,
                detected_at=now,
                amount=order.source_amount,
                currency=order.source_currency
            ))
        
        return timeouts
    
    @classmethod
    async def _scan_email_verification_timeouts(
        cls,
        session,
        rule: TimeoutRule
    ) -> List[TimeoutEvent]:
        """Scan for expired email verifications"""
        from models import EmailVerification
        
        timeouts = []
        now = datetime.utcnow()
        
        expired_verifications = (
            session.query(EmailVerification)
            .filter(
                EmailVerification.expires_at < now,
                EmailVerification.verified == False,
                EmailVerification.user_id.isnot(None)
            )
            .all()
        )
        
        for verification in expired_verifications:
            timeouts.append(TimeoutEvent(
                timeout_type=rule.timeout_type,
                entity_id=str(verification.id),
                entity_type="email_verification",
                user_id=verification.user_id,
                timeout_at=verification.expires_at,
                detected_at=now,
                additional_data={"purpose": verification.purpose, "email": verification.email}
            ))
        
        return timeouts
    
    @classmethod
    async def _scan_otp_verification_timeouts(
        cls,
        session,
        rule: TimeoutRule
    ) -> List[TimeoutEvent]:
        """Scan for expired OTP verifications"""
        # OTP timeouts are typically handled by the OTP service itself
        # This is a placeholder for any persistent OTP records
        return []
    
    @classmethod
    async def _scan_conversation_session_timeouts(
        cls,
        session,
        rule: TimeoutRule
    ) -> List[TimeoutEvent]:
        """Scan for expired conversation sessions - skipped as model doesn't exist"""
        # ConversationSession model doesn't exist in current schema
        return []
    
    @classmethod
    async def _scan_webhook_response_timeouts(
        cls,
        session,
        rule: TimeoutRule
    ) -> List[TimeoutEvent]:
        """Scan for webhook response timeouts"""
        from models import WebhookEventLedger
        
        timeouts = []
        cutoff_time = datetime.utcnow() - rule.timeout_duration
        
        # Check unprocessed webhooks using correct model
        stuck_webhooks = (
            session.query(WebhookEventLedger)
            .filter(
                WebhookEventLedger.status == "failed",
                WebhookEventLedger.created_at < cutoff_time
            )
            .all()
        )
        
        for webhook in stuck_webhooks:
            timeouts.append(TimeoutEvent(
                timeout_type=rule.timeout_type,
                entity_id=str(webhook.id),
                entity_type="webhook_event",
                user_id=0,  # System level
                timeout_at=webhook.created_at + rule.timeout_duration,
                detected_at=datetime.utcnow(),
                additional_data={"event_provider": webhook.event_provider, "event_id": webhook.event_id}
            ))
        
        return timeouts
    
    @classmethod
    async def _scan_cashout_processing_timeouts(
        cls,
        session,
        rule: TimeoutRule
    ) -> List[TimeoutEvent]:
        """Scan for cashout processing timeouts"""
        from models import Cashout
        
        timeouts = []
        cutoff_time = datetime.utcnow() - rule.timeout_duration
        
        # Check stuck cashouts - using created_at instead of updated_at
        stuck_cashouts = (
            session.query(Cashout)
            .filter(
                Cashout.status.in_(["pending", "processing", "review"]),
                Cashout.created_at < cutoff_time,
                Cashout.completed_at.is_(None)
            )
            .all()
        )
        
        for cashout in stuck_cashouts:
            timeouts.append(TimeoutEvent(
                timeout_type=rule.timeout_type,
                entity_id=str(cashout.id),
                entity_type="cashout",
                user_id=cashout.user_id,
                timeout_at=cashout.created_at + rule.timeout_duration,
                detected_at=datetime.utcnow(),
                amount=cashout.amount,
                currency=cashout.currency,
                additional_data={"cashout_type": cashout.cashout_type}
            ))
        
        return timeouts
    
    @classmethod
    async def handle_timeout_event(cls, timeout_event: TimeoutEvent) -> bool:
        """
        Handle a detected timeout event
        
        Args:
            timeout_event: The timeout event to handle
            
        Returns:
            True if handled successfully, False otherwise
        """
        try:
            # Get the appropriate rule for this timeout type
            rule = next(
                (r for r in cls.DEFAULT_TIMEOUT_RULES if r.timeout_type == timeout_event.timeout_type),
                None
            )
            
            if not rule:
                logger.warning(f"No rule found for timeout type: {timeout_event.timeout_type}")
                return False
            
            # Execute the appropriate action
            success = await cls._execute_timeout_action(timeout_event, rule)
            
            # Log the action
            if success:
                logger.info(f"✅ TIMEOUT_HANDLED: {timeout_event.timeout_type.value} for {timeout_event.entity_type} {timeout_event.entity_id}")
            else:
                logger.warning(f"⚠️ TIMEOUT_HANDLING_FAILED: {timeout_event.timeout_type.value} for {timeout_event.entity_type} {timeout_event.entity_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error handling timeout event: {e}")
            return False
    
    @classmethod
    async def _execute_timeout_action(
        cls,
        timeout_event: TimeoutEvent,
        rule: TimeoutRule
    ) -> bool:
        """Execute the timeout action based on the rule"""
        
        if rule.action == TimeoutAction.CANCEL_ORDER:
            return await cls._cancel_order_action(timeout_event)
        
        elif rule.action == TimeoutAction.REFUND_PAYMENT:
            return await cls._refund_payment_action(timeout_event)
        
        elif rule.action == TimeoutAction.SEND_REMINDER:
            return await cls._send_reminder_action(timeout_event)
        
        elif rule.action == TimeoutAction.ESCALATE_MANUAL:
            return await cls._escalate_manual_action(timeout_event)
        
        elif rule.action == TimeoutAction.RETRY_OPERATION:
            return await cls._retry_operation_action(timeout_event)
        
        elif rule.action == TimeoutAction.CLEANUP_RESOURCE:
            return await cls._cleanup_resource_action(timeout_event)
        
        elif rule.action == TimeoutAction.MARK_EXPIRED:
            return await cls._mark_expired_action(timeout_event)
        
        else:
            logger.warning(f"Unknown timeout action: {rule.action}")
            return False
    
    @classmethod
    async def _cancel_order_action(cls, timeout_event: TimeoutEvent) -> bool:
        """Cancel the order and process refund if applicable"""
        try:
            from database import SessionLocal
            
            session = SessionLocal()
            
            try:
                # Handle escrows
                if timeout_event.entity_type == "escrow":
                    from models import Escrow
                    order = session.query(Escrow).filter(
                        Escrow.escrow_id == timeout_event.entity_id
                    ).first()
                    
                    if not order:
                        logger.warning(f"❌ ESCROW_NOT_FOUND: {timeout_event.entity_id}")
                        return False
                    
                    # CRITICAL FIX: For unpaid escrows, just cancel - don't refund!
                    if not order.payment_confirmed_at:
                        logger.info(f"🚫 ESCROW_TIMEOUT_CANCEL: {order.escrow_id} - No payment received, cancelling without refund")
                        order.status = "cancelled"
                        order.cancelled_reason = f"Automatic cancellation due to {timeout_event.timeout_type.value} timeout - no payment received"
                        order.completed_at = datetime.utcnow()
                        session.commit()
                        logger.info(f"✅ ESCROW_CANCELLED: {order.escrow_id} successfully cancelled")
                        return True
                    else:
                        # Paid escrows need refund processing
                        try:
                            from services.automatic_refund_service import AutomaticRefundService
                            refund_result = await AutomaticRefundService._process_order_refund(
                                order=order,
                                order_type="escrow",
                                refund_reason=f"Automatic cancellation due to {timeout_event.timeout_type.value} timeout",
                                session=session
                            )
                            return refund_result["success"]
                        except Exception as refund_error:
                            logger.error(f"❌ ESCROW_REFUND_FAILED: {order.escrow_id} - {refund_error}")
                            # Still cancel even if refund fails
                            order.status = "cancelled"
                            order.cancelled_reason = f"Automatic cancellation due to {timeout_event.timeout_type.value} timeout - refund failed: {str(refund_error)}"
                            order.completed_at = datetime.utcnow()
                            session.commit()
                            return True
                
                # Handle exchange orders  
                elif timeout_event.entity_type == "exchange_order":
                    from models import ExchangeOrder
                    order = session.query(ExchangeOrder).filter(
                        ExchangeOrder.id == int(timeout_event.entity_id)
                    ).first()
                    
                    if not order:
                        logger.warning(f"❌ EXCHANGE_NOT_FOUND: {timeout_event.entity_id}")
                        return False
                    
                    # Cancel exchange order
                    order.status = "cancelled"
                    order.completed_at = datetime.utcnow()
                    session.commit()
                    logger.info(f"✅ EXCHANGE_CANCELLED: {order.id} successfully cancelled")
                    return True
                
                else:
                    logger.warning(f"❌ UNKNOWN_ENTITY_TYPE: {timeout_event.entity_type}")
                    return False
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"❌ CANCEL_ORDER_ERROR: {e}")
            return False
    
    @classmethod
    async def _refund_payment_action(cls, timeout_event: TimeoutEvent) -> bool:
        """Process refund for timeout"""
        # This is similar to cancel_order_action but focuses only on refund
        return await cls._cancel_order_action(timeout_event)
    
    @classmethod
    async def _send_reminder_action(cls, timeout_event: TimeoutEvent) -> bool:
        """Send reminder notification"""
        try:
            from services.consolidated_notification_service import consolidated_notification_service
            from models import User
            from database import SessionLocal
            
            session = SessionLocal()
            
            try:
                user = session.query(User).filter(User.id == timeout_event.user_id).first()
                if not user:
                    return False
                
                # Send reminder based on entity type
                if timeout_event.entity_type == "escrow":
                    message = f"⏰ Reminder: Your escrow {timeout_event.entity_id} needs attention!"
                elif timeout_event.entity_type in ["exchange_order", "direct_exchange"]:
                    message = f"⏰ Reminder: Your exchange {timeout_event.entity_id} is pending payment!"
                else:
                    message = f"⏰ Reminder: Action required for {timeout_event.entity_type} {timeout_event.entity_id}"
                
                # Send Telegram notification
                if user.telegram_id:
                    await consolidated_notification_service.send_telegram_message(
                        user.telegram_id, message
                    )
                
                # Send email notification if available
                if user.email:
                    await consolidated_notification_service.send_email_notification(
                        user.email, "Reminder: Action Required", message
                    )
                
                return True
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error in send reminder action: {e}")
            return False
    
    @classmethod
    async def _escalate_manual_action(cls, timeout_event: TimeoutEvent) -> bool:
        """Escalate to manual review"""
        try:
            from services.consolidated_notification_service import consolidated_notification_service
            
            await consolidated_notification_service.send_admin_alert(
                f"🚨 TIMEOUT_ESCALATION\n"
                f"Type: {timeout_event.timeout_type.value}\n"
                f"Entity: {timeout_event.entity_type} {timeout_event.entity_id}\n"
                f"User: {timeout_event.user_id}\n"
                f"Amount: {timeout_event.amount} {timeout_event.currency}\n"
                f"Timeout At: {timeout_event.timeout_at}\n"
                f"Data: {timeout_event.additional_data}\n\n"
                f"Manual intervention required!"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error in escalate manual action: {e}")
            return False
    
    @classmethod
    async def _retry_operation_action(cls, timeout_event: TimeoutEvent) -> bool:
        """Retry the operation"""
        try:
            # This would trigger a retry of the specific operation
            # Implementation depends on the entity type
            logger.info(f"Retrying operation for {timeout_event.entity_type} {timeout_event.entity_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error in retry operation action: {e}")
            return False
    
    @classmethod
    async def _cleanup_resource_action(cls, timeout_event: TimeoutEvent) -> bool:
        """OPTIMIZED: Clean up expired resource with connection pooling"""
        try:
            from database import SessionLocal
            
            # OPTIMIZATION: Use connection pooling and faster operations
            session = SessionLocal()
            
            try:
                if timeout_event.entity_type == "email_verification":
                    from models import EmailVerification
                    # OPTIMIZATION: Direct delete query instead of fetch-then-delete
                    deleted_count = session.query(EmailVerification).filter(
                        EmailVerification.id == int(timeout_event.entity_id)
                    ).delete(synchronize_session=False)
                    
                    if deleted_count > 0:
                        session.commit()
                        return True
                
                # Skip conversation_session as model doesn't exist
                
                # Add more cleanup logic for other resource types
                return True
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error in cleanup resource action: {e}")
            return False
    
    @classmethod
    async def _mark_expired_action(cls, timeout_event: TimeoutEvent) -> bool:
        """Mark entity as expired"""
        try:
            from database import SessionLocal
            
            session = SessionLocal()
            
            try:
                # Mark as expired without refund processing
                if timeout_event.entity_type == "exchange_order":
                    from models import ExchangeOrder
                    order = session.query(ExchangeOrder).filter(
                        ExchangeOrder.id == int(timeout_event.entity_id)
                    ).first()
                    
                    if order:
                        order.status = "expired"
                        order.completed_at = datetime.utcnow()
                        session.commit()
                        logger.info(f"✅ EXCHANGE_MARKED_EXPIRED: {order.id}")
                        return True
                
                logger.info(f"✅ MARK_EXPIRED_SUCCESS: {timeout_event.entity_type} {timeout_event.entity_id}")
                return True
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"❌ MARK_EXPIRED_ERROR: {e}")
            return False


# Global function to run timeout scan and handling
async def run_systematic_timeout_check():
    """
    Main function to scan for and handle all timeout events
    """
    try:
        logger.info("🕐 STARTING_SYSTEMATIC_TIMEOUT_CHECK")
        
        # Scan for all timeout events
        timeout_events = await SystematicTimeoutHandler.scan_for_timeouts()
        
        if not timeout_events:
            logger.debug("🕐 NO_TIMEOUTS_DETECTED")
            return
        
        # Handle each timeout event
        handled_count = 0
        failed_count = 0
        
        # OPTIMIZATION: Process events concurrently in batches to reduce execution time
        import asyncio
        batch_size = 10  # Process 10 events simultaneously
        
        # Process in batches to prevent overwhelming the system
        for i in range(0, len(timeout_events), batch_size):
            batch = timeout_events[i:i + batch_size]
            logger.debug(f"📦 Processing batch {i//batch_size + 1}: {len(batch)} events")
            
            # Process batch concurrently
            batch_tasks = [
                SystematicTimeoutHandler.handle_timeout_event(timeout_event)
                for timeout_event in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process results
            for timeout_event, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error handling timeout event {timeout_event.entity_id}: {result}")
                    failed_count += 1
                elif result:
                    handled_count += 1
                    logger.info(f"✅ TIMEOUT_HANDLED: {timeout_event.timeout_type.value} for {timeout_event.entity_type} {timeout_event.entity_id}")
                else:
                    failed_count += 1
                    logger.warning(f"⚠️ TIMEOUT_HANDLING_FAILED: {timeout_event.timeout_type.value} for {timeout_event.entity_type} {timeout_event.entity_id}")
            
            # Brief pause between batches to prevent overwhelming
            if i + batch_size < len(timeout_events):
                await asyncio.sleep(0.1)
        
        # Log summary
        logger.info(f"✅ SYSTEMATIC_TIMEOUT_CHECK_COMPLETED: "
                   f"Handled: {handled_count}, Failed: {failed_count}, Total: {len(timeout_events)}")
        
    except Exception as e:
        logger.error(f"Error in systematic timeout check: {e}")