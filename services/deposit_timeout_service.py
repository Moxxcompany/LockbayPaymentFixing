"""
Deposit Timeout Service - Clear expiration warnings for payment addresses
Manages address expiration and provides clear user notifications
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from database import SessionLocal
from models import Escrow, ExchangeOrder
from services.consolidated_notification_service import (
    consolidated_notification_service as notification_hub,
)
from config import Config
from telegram import Bot

logger = logging.getLogger(__name__)


@dataclass
class DepositTimeout:
    """Data class for deposit timeout tracking"""

    identifier: str  # escrow_id or exchange_order_id
    timeout_type: str  # 'escrow' or 'exchange'
    user_id: int
    currency: str
    address: str
    amount: float
    expires_at: datetime
    warning_sent_1h: bool = False
    warning_sent_15min: bool = False
    warning_sent_5min: bool = False


class DepositTimeoutService:
    """Service for managing deposit address timeouts and user warnings"""

    def __init__(self):
        self.active_timeouts: Dict[str, DepositTimeout] = {}
        self.monitoring_task = None

        # Default timeout periods
        self.escrow_timeout_hours = 24  # 24 hours for escrow deposits
        self.exchange_timeout_minutes = (
            15  # 15 minutes for exchange deposits (after rate lock)
        )

        # Warning intervals (before expiration)
        self.warning_intervals = [
            timedelta(hours=1),  # 1 hour before
            timedelta(minutes=15),  # 15 minutes before
            timedelta(minutes=5),  # 5 minutes before
        ]

    async def start_monitoring(self):
        """Start background monitoring for deposit timeouts"""
        if self.monitoring_task is None:
            self.monitoring_task = asyncio.create_task(self._monitor_deposit_timeouts())
            logger.info("Deposit timeout monitoring started")

    async def _monitor_deposit_timeouts(self):
        """Background task to monitor and send timeout warnings"""
        while True:
            try:
                await self._check_and_send_warnings()
                await self._cleanup_expired_deposits()
            except Exception as e:
                logger.error(f"Error in deposit timeout monitoring: {e}")

            # Check every 2 minutes
            await asyncio.sleep(120)

    def create_escrow_deposit_timeout(
        self, escrow_id: str, user_id: int, currency: str, address: str, amount: float
    ) -> DepositTimeout:
        """Create timeout tracking for escrow deposit"""
        identifier = f"escrow_{escrow_id}"
        expires_at = datetime.utcnow() + timedelta(hours=self.escrow_timeout_hours)

        timeout = DepositTimeout(
            identifier=identifier,
            timeout_type="escrow",
            user_id=user_id,
            currency=currency,
            address=address,
            amount=amount,
            expires_at=expires_at,
        )

        self.active_timeouts[identifier] = timeout
        logger.info(
            f"Created escrow deposit timeout for {identifier} - expires {expires_at}"
        )
        return timeout

    def create_exchange_deposit_timeout(
        self,
        exchange_order_id: int,
        user_id: int,
        currency: str,
        address: str,
        amount: float,
        custom_timeout_minutes: Optional[int] = None,
    ) -> DepositTimeout:
        """Create timeout tracking for exchange deposit"""
        identifier = f"exchange_{exchange_order_id}"
        timeout_minutes = custom_timeout_minutes or self.exchange_timeout_minutes
        expires_at = datetime.utcnow() + timedelta(minutes=timeout_minutes)

        timeout = DepositTimeout(
            identifier=identifier,
            timeout_type="exchange",
            user_id=user_id,
            currency=currency,
            address=address,
            amount=amount,
            expires_at=expires_at,
        )

        self.active_timeouts[identifier] = timeout
        logger.info(
            f"Created exchange deposit timeout for {identifier} - expires {expires_at}"
        )
        return timeout

    def extend_timeout(self, identifier: str, additional_minutes: int) -> bool:
        """Extend deposit timeout by additional minutes"""
        timeout = self.active_timeouts.get(identifier)
        if not timeout:
            return False

        timeout.expires_at += timedelta(minutes=additional_minutes)
        # Reset warnings for extended timeout
        timeout.warning_sent_1h = False
        timeout.warning_sent_15min = False
        timeout.warning_sent_5min = False

        logger.info(
            f"Extended timeout for {identifier} by {additional_minutes} minutes"
        )
        return True

    def cancel_timeout(self, identifier: str) -> bool:
        """Cancel deposit timeout (when payment is received)"""
        if identifier in self.active_timeouts:
            del self.active_timeouts[identifier]
            logger.info(f"Cancelled timeout for {identifier}")
            return True
        return False

    async def _check_and_send_warnings(self):
        """Check timeouts and send appropriate warnings"""
        now = datetime.utcnow()
        if Config.BOT_TOKEN:
            bot = Bot(Config.BOT_TOKEN)
        else:
            return

        for identifier, timeout in self.active_timeouts.items():
            time_remaining = timeout.expires_at - now

            # Skip if already expired
            if time_remaining.total_seconds() <= 0:
                continue

            # Check for 1-hour warning
            if (
                time_remaining <= self.warning_intervals[0]
                and not timeout.warning_sent_1h
                and timeout.timeout_type == "escrow"
            ):  # Only for escrow (longer timeouts)

                await self._send_warning_message(bot, timeout, "1 hour")
                timeout.warning_sent_1h = True

            # Check for 15-minute warning
            elif (
                time_remaining <= self.warning_intervals[1]
                and not timeout.warning_sent_15min
            ):

                await self._send_warning_message(bot, timeout, "15 minutes")
                timeout.warning_sent_15min = True

            # Check for 5-minute warning
            elif (
                time_remaining <= self.warning_intervals[2]
                and not timeout.warning_sent_5min
            ):

                await self._send_warning_message(bot, timeout, "5 minutes")
                timeout.warning_sent_5min = True

    async def _send_warning_message(
        self, bot: Bot, timeout: DepositTimeout, time_left: str
    ):
        """Send timeout warning message to user"""
        try:
            if timeout.timeout_type == "escrow":
                message = f"""⏰ *Payment Reminder - {time_left} left*

🔒 *Escrow #{timeout.identifier.replace('escrow_', '')}*
💰 Waiting for your {timeout.amount:.6f} {timeout.currency} deposit

📍 *Payment Address:*
`{timeout.address}`

⚠️ *Important:* Your payment address expires in {time_left}. Please complete your deposit to secure the trade.

💡 *Need help?* Contact support if you're experiencing issues."""

            else:  # exchange
                message = f"""⏰ *Rate Lock Expiring - {time_left} left*

💱 *Exchange Order #{timeout.identifier.replace('exchange_', '')}*
💰 Send {timeout.amount:.6f} {timeout.currency}

📍 *Payment Address:*
`{timeout.address}`

⚠️ *Your locked rate expires in {time_left}!*
Complete your deposit now to secure this exchange rate.

📈 *Rate Protection:* Your current rate is protected during the deposit window."""

            await notification_hub.send_telegram_message(
                bot,
                timeout.user_id,
                message,
                parse_mode="HTML",
                notification_type="deposit_timeout",
            )

            logger.info(
                f"Sent {time_left} warning to user {timeout.user_id} for {timeout.identifier}"
            )

        except Exception as e:
            logger.error(f"Error sending warning message: {e}")

    async def _cleanup_expired_deposits(self):
        """Remove expired deposit timeouts and send final notifications"""
        now = datetime.utcnow()
        expired_identifiers = []
        if Config.BOT_TOKEN:
            bot = Bot(Config.BOT_TOKEN)
        else:
            return

        for identifier, timeout in self.active_timeouts.items():
            if now >= timeout.expires_at:
                expired_identifiers.append(identifier)

                # Send expiration notification
                try:
                    await self._send_expiration_message(bot, timeout)

                    # Update database status
                    await self._mark_deposit_expired(timeout)

                except Exception as e:
                    logger.error(f"Error handling expired deposit {identifier}: {e}")

        # Remove expired timeouts
        for identifier in expired_identifiers:
            del self.active_timeouts[identifier]
            logger.info(f"Cleaned up expired timeout: {identifier}")

    async def _send_expiration_message(self, bot: Bot, timeout: DepositTimeout):
        """Send expiration notification to user"""
        if timeout.timeout_type == "escrow":
            message = f"""❌ <b>Payment Address Expired</b>

🔒 <b>Escrow #{timeout.identifier.replace('escrow_', '')}</b>

Your payment address has expired without receiving the required deposit. 

🔄 <b>What happens now?</b>
• The escrow has been automatically cancelled
• You can create a new escrow with a fresh payment address
• All escrow terms remain the same

💡 <b>Need a longer deposit window?</b> Contact the other party to discuss extending payment time for future trades."""

        else:  # exchange
            message = f"""❌ <b>Exchange Rate Lock Expired</b>

💱 <b>Exchange Order #{timeout.identifier.replace('exchange_', '')}</b>

Your rate lock has expired without receiving payment.

🔄 <b>What happens now?</b>
• Your locked exchange rate is no longer available
• You can start a new exchange at current rates
• No funds were charged or lost

📈 <b>New Exchange:</b> Use /wallet to start a new exchange with current market rates."""

        await notification_hub.send_telegram_message(
            bot,
            timeout.user_id,
            message,
            parse_mode="HTML",
            notification_type="deposit_expired",
        )

    async def _mark_deposit_expired(self, timeout: DepositTimeout):
        """Mark the deposit as expired in database and release any reserved funds"""
        session = SessionLocal()
        try:
            if timeout.timeout_type == "escrow":
                escrow_id = timeout.identifier.replace("escrow_", "")
                escrow = (
                    session.query(Escrow).filter(Escrow.escrow_id == escrow_id).first()
                )
                if escrow:
                    # CRITICAL FIX: Release any reserved wallet funds before marking as expired
                    await self._release_expired_escrow_funds(escrow, session)
                    
                    setattr(escrow, "status", "expired")
                    setattr(escrow, "expired_at", datetime.utcnow())
                    session.commit()
                    logger.info(f"Marked escrow {escrow_id} as expired and released reserved funds")

            else:  # exchange
                order_id = int(timeout.identifier.replace("exchange_", ""))
                order = (
                    session.query(ExchangeOrder)
                    .filter(ExchangeOrder.id == order_id)
                    .first()
                )
                if order:
                    setattr(order, "status", "expired")
                    setattr(order, "expired_at", datetime.utcnow())
                    session.commit()
                    logger.info(f"Marked exchange order {order_id} as expired")

        except Exception as e:
            session.rollback()
            logger.error(f"Error marking deposit as expired: {e}")
        finally:
            session.close()

    async def _release_expired_escrow_funds(self, escrow, session):
        """Release any wallet funds reserved for an expired escrow"""
        try:
            from utils.escrow_balance_security import get_escrow_payment_method
            from services.crypto import CryptoServiceAtomic
            from models import User
            
            # Check if this escrow had wallet payment that needs fund release
            payment_method, wallet_contribution = get_escrow_payment_method(escrow)
            
            if payment_method in ["wallet", "hybrid"] and wallet_contribution > 0:
                # Get user details for audit trail
                user = session.query(User).filter(User.id == escrow.buyer_id).first()
                if user:
                    # Credit wallet funds back (expired escrow refund)
                    credit_success = CryptoServiceAtomic.credit_user_wallet_atomic(
                        user_id=escrow.buyer_id,
                        amount=wallet_contribution,
                        currency="USD",
                        transaction_type="escrow_refund",
                        description=f"Expired escrow fund release: #{escrow.escrow_id}",
                        escrow_id=escrow.id,
                        session=session
                    )
                    
                    if credit_success:
                        logger.critical(
                            f"🔓 EXPIRED ESCROW FUND RELEASE: User {escrow.buyer_id} "
                            f"refunded ${wallet_contribution:.2f} from expired escrow {escrow.escrow_id}"
                        )
                        
                        # Send notification to user about fund release
                        await self._send_fund_release_notification(escrow, wallet_contribution, user)
                    else:
                        logger.error(
                            f"Failed to release wallet funds for expired escrow {escrow.escrow_id}"
                        )
                        
        except Exception as e:
            logger.error(f"Error releasing expired escrow funds for {escrow.escrow_id}: {e}")
            # Don't let fund release errors block the expiration process
            
    async def _send_fund_release_notification(self, escrow, amount, user):
        """Send notification about fund release from expired escrow"""
        try:
            if user.telegram_id and Config.BOT_TOKEN:
                from telegram import Bot
                
                message = f"""💰 <b>Funds Released</b>

🔒 <b>Escrow #{escrow.escrow_id}</b>
Your reserved funds have been automatically released.

💵 <b>Amount:</b> ${amount:.2f} USD
📅 <b>Reason:</b> Payment deadline expired
✅ <b>Status:</b> Funds returned to wallet

💡 <b>What happened?</b>
• The escrow payment deadline expired
• Your wallet funds were automatically released
• You can create a new escrow anytime

Use /wallet to view your updated balance."""

                bot = Bot(Config.BOT_TOKEN)
                await bot.send_message(
                    chat_id=int(user.telegram_id),
                    text=message,
                    parse_mode="HTML"
                )
                
                logger.info(f"Sent fund release notification to user {user.id}")
                
        except Exception as e:
            logger.error(f"Error sending fund release notification: {e}")

    def get_active_timeouts_for_user(self, user_id: int) -> List[DepositTimeout]:
        """Get all active deposit timeouts for a user"""
        return [
            timeout
            for timeout in self.active_timeouts.values()
            if timeout.user_id == user_id
        ]

    def get_timeout_status(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Get timeout status and remaining time"""
        timeout = self.active_timeouts.get(identifier)
        if not timeout:
            return None

        now = datetime.utcnow()
        time_remaining = timeout.expires_at - now

        return {
            "identifier": timeout.identifier,
            "type": timeout.timeout_type,
            "expires_at": timeout.expires_at,
            "time_remaining_seconds": int(time_remaining.total_seconds()),
            "time_remaining_minutes": int(time_remaining.total_seconds() / 60),
            "is_expired": time_remaining.total_seconds() <= 0,
            "warnings_sent": {
                "1h": timeout.warning_sent_1h,
                "15min": timeout.warning_sent_15min,
                "5min": timeout.warning_sent_5min,
            },
        }


# Global instance
deposit_timeout_service = DepositTimeoutService()
