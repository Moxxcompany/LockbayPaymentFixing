"""
Auto Earnings Service - Wallet Cashback System
Provides immediate wallet credits after every transaction
"""

import logging
from typing import Dict, List
from datetime import datetime
from database import SessionLocal
from models import UserEarnings
from services.crypto import CryptoServiceAtomic
from config import Config

logger = logging.getLogger(__name__)


class AutoEarningsService:
    """Service to manage automatic wallet earnings after transactions"""

    # Earnings rates for different transaction types
    ESCROW_EARNINGS_RATE = 0.005  # 0.5% of escrow value
    EXCHANGE_EARNINGS_RATE = 0.003  # 0.3% of exchange amount
    CASHOUT_EARNINGS_FIXED = {  # Fixed earnings based on cashout amount
        "small": 0.25,  # Under $50
        "medium": 0.50,  # $50-$200
        "large": 1.00,  # Over $200
    }

    # Milestone levels for earnings tracking
    MILESTONE_LEVELS = {
        "bronze": 5.0,  # $5+ earned
        "silver": 20.0,  # $20+ earned
        "gold": 50.0,  # $50+ earned
        "diamond": 100.0,  # $100+ earned
    }

    @classmethod
    def format_currency(cls, amount: float) -> str:
        """Format amount with platform currency symbol"""
        if Config.PLATFORM_CURRENCY == "JPY":
            return f"{Config.PLATFORM_CURRENCY_SYMBOL}{int(amount)}"
        return f"{Config.PLATFORM_CURRENCY_SYMBOL}{amount:.2f}"

    @classmethod
    async def process_escrow_earnings(
        cls, user_id: int, escrow_amount_usd: float
    ) -> Dict:
        """Process earnings for completed escrow transactions"""
        try:
            # Calculate earnings (0.5% of escrow value)
            earnings_amount = escrow_amount_usd * cls.ESCROW_EARNINGS_RATE

            # Minimum $0.01, maximum $10.00 to keep reasonable
            earnings_amount = max(0.01, min(earnings_amount, 10.0))

            # Credit user wallet
            credit_success = CryptoServiceAtomic.credit_user_wallet_atomic(
                user_id=user_id,
                amount=earnings_amount,
                currency="USD",
                transaction_type="earnings_escrow",
                description=f"Auto-earnings from escrow completion (${escrow_amount_usd:.2f})",
            )

            if credit_success:
                # Update earnings tracking
                earnings_data = await cls._update_earnings_tracking(
                    user_id, earnings_amount, "escrow", escrow_amount_usd
                )

                logger.info(
                    f"Escrow earnings processed: User {user_id} earned ${earnings_amount:.2f}"
                )

                return {
                    "success": True,
                    "earnings_amount": earnings_amount,
                    "escrow_amount": escrow_amount_usd,
                    "new_milestones": earnings_data.get("new_milestones", []),
                    "total_earnings": earnings_data.get("total_earnings", 0),
                    "message": f"🎉 You earned {cls.format_currency(earnings_amount)}! Added to your wallet.",
                }
            else:
                return {"success": False, "error": "Failed to credit wallet"}

        except Exception as e:
            logger.error(f"Error processing escrow earnings for user {user_id}: {e}")
            return {"success": False, "error": str(e)}

    @classmethod
    async def process_exchange_earnings(
        cls, user_id: int, exchange_amount_usd: float, exchange_reference: str = None
    ) -> Dict:
        """Process earnings for quick exchange transactions with idempotency"""
        try:
            # Generate unique exchange reference if not provided
            if not exchange_reference:
                from datetime import datetime
                exchange_reference = f"EX_{user_id}_{int(datetime.utcnow().timestamp())}"
            
            # Check if earnings already processed for this exchange
            if await cls._is_exchange_earnings_processed(user_id, exchange_reference, exchange_amount_usd):
                logger.info(f"Exchange earnings already processed for user {user_id}, reference: {exchange_reference}")
                return {
                    "success": True,
                    "earnings_amount": 0,
                    "exchange_amount": exchange_amount_usd,
                    "message": "Earnings already processed for this exchange",
                    "duplicate_prevented": True
                }

            # Calculate earnings (0.3% of exchange amount)
            earnings_amount = exchange_amount_usd * cls.EXCHANGE_EARNINGS_RATE

            # Minimum $0.01, maximum $5.00
            earnings_amount = max(0.01, min(earnings_amount, 5.0))

            # Credit user wallet with exchange reference
            credit_success = CryptoServiceAtomic.credit_user_wallet_atomic(
                user_id=user_id,
                amount=earnings_amount,
                currency="USD",
                transaction_type="earnings_exchange",
                description=f"Auto-earnings from exchange (${exchange_amount_usd:.2f}) - Ref: {exchange_reference}",
            )

            if credit_success:
                # Record exchange earnings to prevent duplicates
                await cls._record_exchange_earnings(user_id, exchange_reference, exchange_amount_usd, earnings_amount)
                
                # Update earnings tracking
                earnings_data = await cls._update_earnings_tracking(
                    user_id, earnings_amount, "exchange", exchange_amount_usd
                )

                logger.info(
                    f"Exchange earnings processed: User {user_id} earned ${earnings_amount:.2f}"
                )

                return {
                    "success": True,
                    "earnings_amount": earnings_amount,
                    "exchange_amount": exchange_amount_usd,
                    "exchange_reference": exchange_reference,
                    "new_milestones": earnings_data.get("new_milestones", []),
                    "total_earnings": earnings_data.get("total_earnings", 0),
                    "message": f"🎉 You earned {cls.format_currency(earnings_amount)}! Added to your wallet.",
                }
            else:
                return {"success": False, "error": "Failed to credit wallet"}

        except Exception as e:
            logger.error(f"Error processing exchange earnings for user {user_id}: {e}")
            return {"success": False, "error": str(e)}

    @classmethod
    async def process_cashout_earnings(
        cls, user_id: int, cashout_amount_usd: float, cashout_type: str = "general"
    ) -> Dict:
        """Process earnings for successful cashout transactions"""
        try:
            # Determine fixed earnings based on cashout amount
            if cashout_amount_usd < 50:
                earnings_amount = cls.CASHOUT_EARNINGS_FIXED["small"]
            elif cashout_amount_usd < 200:
                earnings_amount = cls.CASHOUT_EARNINGS_FIXED["medium"]
            else:
                earnings_amount = cls.CASHOUT_EARNINGS_FIXED["large"]

            # Credit user wallet
            credit_success = CryptoServiceAtomic.credit_user_wallet_atomic(
                user_id=user_id,
                amount=earnings_amount,
                currency="USD",
                transaction_type="earnings_cashout",
                description=f"Auto-earnings from {cashout_type} cashout (${cashout_amount_usd:.2f})",
            )

            if credit_success:
                # Update earnings tracking
                earnings_data = await cls._update_earnings_tracking(
                    user_id, earnings_amount, "cashout", cashout_amount_usd
                )

                logger.info(
                    f"Cashout earnings processed: User {user_id} earned ${earnings_amount:.2f}"
                )

                return {
                    "success": True,
                    "earnings_amount": earnings_amount,
                    "cashout_amount": cashout_amount_usd,
                    "new_milestones": earnings_data.get("new_milestones", []),
                    "total_earnings": earnings_data.get("total_earnings", 0),
                    "message": f"🎉 You earned {cls.format_currency(earnings_amount)}! Added to your wallet.",
                }
            else:
                return {"success": False, "error": "Failed to credit wallet"}

        except Exception as e:
            logger.error(f"Error processing cashout earnings for user {user_id}: {e}")
            return {"success": False, "error": str(e)}

    @classmethod
    async def _update_earnings_tracking(
        cls,
        user_id: int,
        earnings_amount: float,
        transaction_type: str,
        transaction_amount: float,
    ) -> Dict:
        """Update earnings tracking and check for milestones"""
        session = SessionLocal()
        try:
            # Get or create earnings record (now properly named UserEarnings)
            earnings = UserEarnings.get_or_create_for_user(session, user_id)

            # Convert to earnings tracking instead of savings tracking
            current_total = float(earnings.total_savings_usd or 0)
            new_total = current_total + earnings_amount

            # Update earnings instead of savings
            earnings.total_savings_usd = new_total  # Repurpose as total_earnings_usd
            earnings.this_month_savings_usd = (
                float(earnings.this_month_savings_usd or 0) + earnings_amount
            )
            earnings.this_week_savings_usd = (
                float(earnings.this_week_savings_usd or 0) + earnings_amount
            )

            # Check for new milestones
            new_milestones = cls._check_milestones(current_total, new_total, earnings)

            # Update transaction counters based on type
            if transaction_type == "escrow":
                earnings.total_escrows_completed = (
                    earnings.total_escrows_completed or 0
                ) + 1
                earnings.total_escrow_volume_usd = (
                    float(earnings.total_escrow_volume_usd or 0) + transaction_amount
                )
            elif transaction_type == "cashout":
                earnings.total_cashouts = (earnings.total_cashouts or 0) + 1

            earnings.updated_at = datetime.utcnow()
            session.commit()

            # Send milestone notifications if any
            if new_milestones:
                await cls._send_milestone_notifications(user_id, new_milestones)

            return {
                "total_earnings": new_total,
                "monthly_earnings": float(earnings.this_month_savings_usd or 0),
                "weekly_earnings": float(earnings.this_week_savings_usd or 0),
                "new_milestones": new_milestones,
                "achievements": cls._get_achievements_summary(earnings),
            }

        except Exception as e:
            logger.error(f"Error updating earnings tracking: {e}")
            session.rollback()
            return {"error": str(e)}
        finally:
            session.close()

    @classmethod
    def _check_milestones(
        cls, old_total: float, new_total: float, earnings_record
    ) -> List[str]:
        """Check if user achieved new earning milestones"""
        new_milestones = []

        for milestone, threshold in cls.MILESTONE_LEVELS.items():
            milestone_field = f"milestone_{milestone}_achieved"

            if old_total < threshold <= new_total and not getattr(
                earnings_record, milestone_field, False
            ):
                # User just achieved this milestone
                setattr(earnings_record, milestone_field, True)
                new_milestones.append(f"earner_{milestone}")

        return new_milestones

    @classmethod
    async def _send_milestone_notifications(cls, user_id: int, milestones: List[str]):
        """Send milestone achievement notifications to user"""
        if not milestones:
            return

        try:
            from utils.bot import get_bot_instance
            from models import User

            session = SessionLocal()
            user = session.query(User).filter(User.id == user_id).first()
            if not user or not user.telegram_id:
                session.close()
                return

            bot = get_bot_instance()

            for milestone in milestones:
                celebration_message = cls._get_milestone_celebration_message(milestone)
                if celebration_message:
                    try:
                        await bot.send_message(
                            chat_id=user.telegram_id,
                            text=celebration_message,
                            parse_mode="HTML",
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to send milestone celebration to user {user_id}: {e}"
                        )

            session.close()
        except Exception as e:
            logger.error(f"Error sending milestone celebrations: {e}")

    @classmethod
    def _get_milestone_celebration_message(cls, milestone: str) -> str:
        """Get celebration message for achievement milestone"""
        messages = {
            "earner_bronze": """🥉 <b>Bronze Earner Achievement!</b>
            
<b>🎉 You've earned $5+ with LockBay!</b>

Every transaction pays you back! Keep trading to earn even more.

<b>Next Goal:</b> Silver Earner ($20+) 🥈""",
            "earner_silver": """🥈 <b>Silver Earner Achievement!</b>
            
<b>🎉 You've earned $20+ with LockBay!</b>

You're making money while saving money! Your wallet loves you.

<b>Next Goal:</b> Gold Earner ($50+) 🥇""",
            "earner_gold": """🥇 <b>Gold Earner Achievement!</b>
            
<b>🎉 You've earned $50+ with LockBay!</b>

Outstanding earning power! You're turning every transaction into profit.

<b>Next Goal:</b> Diamond Earner ($100+) 💎""",
            "earner_diamond": """💎 <b>Diamond Earner Achievement!</b>
            
<b>🎉 You've earned $100+ with LockBay!</b>

Elite earner status! You've mastered the art of profitable trading. 🚀""",
        }

        return messages.get(milestone, "")

    @classmethod
    def _get_achievements_summary(cls, earnings_record) -> Dict:
        """Get summary of user achievements"""
        achievements = {}

        for milestone in cls.MILESTONE_LEVELS.keys():
            milestone_field = f"milestone_{milestone}_achieved"
            achievements[f"{milestone}_earner"] = getattr(
                earnings_record, milestone_field, False
            )

        return achievements

    @classmethod
    async def get_user_earnings_summary(cls, user_id: int) -> Dict:
        """Get comprehensive earnings summary for user"""
        session = SessionLocal()
        try:
            earnings = UserEarnings.get_or_create_for_user(session, user_id)

            return {
                "total_earnings": float(earnings.total_savings_usd or 0),
                "monthly_earnings": float(earnings.this_month_savings_usd or 0),
                "weekly_earnings": float(earnings.this_week_savings_usd or 0),
                "total_transactions": (earnings.total_escrows_completed or 0)
                + (earnings.total_cashouts or 0),
                "total_escrows": earnings.total_escrows_completed or 0,
                "total_cashouts": earnings.total_cashouts or 0,
                "total_volume": float(earnings.total_escrow_volume_usd or 0),
                "achievements": cls._get_achievements_summary(earnings),
                "milestone_progress": cls._get_milestone_progress(
                    float(earnings.total_savings_usd or 0)
                ),
            }

        except Exception as e:
            logger.error(f"Error getting earnings summary for user {user_id}: {e}")
            return {
                "total_earnings": 0,
                "monthly_earnings": 0,
                "weekly_earnings": 0,
                "error": str(e),
            }
        finally:
            session.close()

    @classmethod
    def _get_milestone_progress(cls, total_earnings: float) -> Dict:
        """Get progress towards next milestone"""
        for milestone, threshold in sorted(
            cls.MILESTONE_LEVELS.items(), key=lambda x: x[1]
        ):
            if total_earnings < threshold:
                return {
                    "next_milestone": milestone,
                    "next_threshold": threshold,
                    "progress": total_earnings,
                    "remaining": threshold - total_earnings,
                    "percentage": (total_earnings / threshold) * 100,
                }

        # All milestones achieved
        return {
            "next_milestone": "completed",
            "next_threshold": max(cls.MILESTONE_LEVELS.values()),
            "progress": total_earnings,
            "remaining": 0,
            "percentage": 100,
        }

    @classmethod
    async def _is_exchange_earnings_processed(cls, user_id: int, exchange_reference: str, exchange_amount: float) -> bool:
        """Check if exchange earnings already processed for this reference"""
        session = SessionLocal()
        try:
            from models import Transaction
            
            # Check for existing earnings transaction with this exchange reference
            existing_transaction = session.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == "earnings_exchange",
                Transaction.description.contains(exchange_reference)
            ).first()
            
            # Additional check for recent identical exchange earnings (same amount, recent time)
            if not existing_transaction:
                from datetime import datetime, timedelta
                recent_cutoff = datetime.utcnow() - timedelta(minutes=30)  # 30 minutes window
                
                recent_identical = session.query(Transaction).filter(
                    Transaction.user_id == user_id,
                    Transaction.transaction_type == "earnings_exchange",
                    Transaction.description.contains(f"(${exchange_amount:.2f})"),
                    Transaction.created_at >= recent_cutoff
                ).first()
                
                if recent_identical:
                    logger.warning(f"Found recent identical exchange earnings for user {user_id}, amount ${exchange_amount:.2f}")
                    return True
            
            return existing_transaction is not None
            
        except Exception as e:
            logger.error(f"Error checking exchange earnings status: {e}")
            return False  # If check fails, allow processing but log error
        finally:
            session.close()

    @classmethod
    async def _record_exchange_earnings(cls, user_id: int, exchange_reference: str, exchange_amount: float, earnings_amount: float):
        """Record exchange earnings processing to prevent future duplicates"""
        session = SessionLocal()
        try:
            # This is handled by the wallet credit transaction, but we can add additional tracking if needed
            logger.info(f"Exchange earnings recorded: User {user_id}, Ref: {exchange_reference}, Amount: ${earnings_amount:.2f}")
            
        except Exception as e:
            logger.error(f"Error recording exchange earnings: {e}")
        finally:
            session.close()
