"""
Group Event Broadcast Service - Sends trade lifecycle events to all registered Telegram groups

Events broadcasted:
- Trade created (escrow created)
- Trade funded (payment confirmed)
- Seller accepted
- Escrow completed (funds released)
- Rating submitted
- New user onboarded (first-time user)
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from telegram import Bot
from telegram.error import TelegramError, Forbidden
from config import Config
from database import SessionLocal
from sqlalchemy import select, update

logger = logging.getLogger(__name__)


class GroupEventService:
    """Broadcasts trade lifecycle events to all registered Telegram groups"""
    
    def __init__(self):
        self.name = "GroupEventService"
    
    def _get_active_groups(self) -> List[Dict[str, Any]]:
        """Get all active groups from database"""
        try:
            from models import BotGroup
            with SessionLocal() as session:
                groups = session.query(BotGroup).filter(
                    BotGroup.is_active == True,
                    BotGroup.events_enabled == True
                ).all()
                return [{"chat_id": g.chat_id, "chat_title": g.chat_title} for g in groups]
        except Exception as e:
            logger.error(f"Error fetching active groups: {e}")
            return []
    
    async def _broadcast_to_groups(self, message: str, exclude_chat_id: Optional[int] = None) -> int:
        """Send a message to all registered active groups"""
        if not Config.BOT_TOKEN:
            logger.debug("Bot token not configured - skipping group broadcast")
            return 0
        
        groups = self._get_active_groups()
        if not groups:
            logger.debug("No active groups registered - skipping broadcast")
            return 0
        
        bot = Bot(Config.BOT_TOKEN)
        sent_count = 0
        
        for group in groups:
            chat_id = group["chat_id"]
            if exclude_chat_id and chat_id == exclude_chat_id:
                continue
            
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='HTML'
                )
                sent_count += 1
            except Forbidden:
                # Bot was removed from group - mark as inactive
                logger.warning(f"Bot removed from group {chat_id} - marking inactive")
                self._deactivate_group(chat_id)
            except TelegramError as e:
                logger.error(f"Failed to send to group {chat_id}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error sending to group {chat_id}: {e}")
        
        return sent_count
    
    def _deactivate_group(self, chat_id: int):
        """Mark a group as inactive (bot was removed)"""
        try:
            from models import BotGroup
            with SessionLocal() as session:
                session.execute(
                    update(BotGroup).where(BotGroup.chat_id == chat_id).values(
                        is_active=False,
                        removed_at=datetime.now(timezone.utc)
                    )
                )
                session.commit()
        except Exception as e:
            logger.error(f"Error deactivating group {chat_id}: {e}")
    
    # ============================================================================
    # EVENT BROADCASTS
    # ============================================================================
    
    async def broadcast_trade_created(self, data: Dict[str, Any]) -> int:
        """Broadcast when a new escrow trade is created"""
        escrow_id = data.get('escrow_id', 'Unknown')
        amount = data.get('amount', 0)
        currency = data.get('currency', 'USD')
        buyer_name = data.get('buyer_info', 'Anonymous')
        
        amount_display = f"${amount:.2f}" if currency == 'USD' else f"{amount} {currency}"
        
        message = (
            f"<b>New Trade Created</b>\n\n"
            f"Trade ID: <code>{escrow_id}</code>\n"
            f"Amount: {amount_display}\n"
            f"Buyer: {buyer_name}\n\n"
            f"Awaiting payment..."
        )
        
        count = await self._broadcast_to_groups(message)
        if count > 0:
            logger.info(f"Broadcasted trade_created {escrow_id} to {count} groups")
        return count
    
    async def broadcast_trade_funded(self, data: Dict[str, Any]) -> int:
        """Broadcast when escrow is funded (payment confirmed)"""
        escrow_id = data.get('escrow_id', 'Unknown')
        amount = data.get('amount', 0)
        currency = data.get('currency', 'USD')
        buyer_name = data.get('buyer_info', 'Anonymous')
        
        amount_display = f"${amount:.2f}" if currency == 'USD' else f"{amount} {currency}"
        
        message = (
            f"<b>Trade Funded</b>\n\n"
            f"Trade ID: <code>{escrow_id}</code>\n"
            f"Amount: {amount_display}\n"
            f"Buyer: {buyer_name}\n\n"
            f"Payment confirmed. Waiting for seller to accept."
        )
        
        count = await self._broadcast_to_groups(message)
        if count > 0:
            logger.info(f"Broadcasted trade_funded {escrow_id} to {count} groups")
        return count
    
    async def broadcast_seller_accepted(self, data: Dict[str, Any]) -> int:
        """Broadcast when seller accepts the trade"""
        escrow_id = data.get('escrow_id', 'Unknown')
        amount = data.get('amount', 0)
        currency = data.get('currency', 'USD')
        seller_name = data.get('seller_info', 'Anonymous')
        
        amount_display = f"${amount:.2f}" if currency == 'USD' else f"{amount} {currency}"
        
        message = (
            f"<b>Seller Accepted Trade</b>\n\n"
            f"Trade ID: <code>{escrow_id}</code>\n"
            f"Amount: {amount_display}\n"
            f"Seller: {seller_name}\n\n"
            f"Trade is now active. Delivery in progress."
        )
        
        count = await self._broadcast_to_groups(message)
        if count > 0:
            logger.info(f"Broadcasted seller_accepted {escrow_id} to {count} groups")
        return count
    
    async def broadcast_escrow_completed(self, data: Dict[str, Any]) -> int:
        """Broadcast when escrow is completed (funds released)"""
        escrow_id = data.get('escrow_id', 'Unknown')
        amount = data.get('amount', 0)
        currency = data.get('currency', 'USD')
        
        amount_display = f"${amount:.2f}" if currency == 'USD' else f"{amount} {currency}"
        
        message = (
            f"<b>Trade Completed</b>\n\n"
            f"Trade ID: <code>{escrow_id}</code>\n"
            f"Amount: {amount_display}\n\n"
            f"Funds released successfully. Trade closed."
        )
        
        count = await self._broadcast_to_groups(message)
        if count > 0:
            logger.info(f"Broadcasted escrow_completed {escrow_id} to {count} groups")
        return count
    
    async def broadcast_rating_submitted(self, data: Dict[str, Any]) -> int:
        """Broadcast when a rating is submitted"""
        escrow_id = data.get('escrow_id', 'Unknown')
        rating = data.get('rating', 0)
        reviewer_name = data.get('reviewer_info', 'Anonymous')
        
        stars = int(rating)
        star_display = "★" * stars + "☆" * (5 - stars)
        
        message = (
            f"<b>Trade Rated</b>\n\n"
            f"Trade ID: <code>{escrow_id}</code>\n"
            f"Rating: {star_display} ({rating}/5)\n"
            f"By: {reviewer_name}\n\n"
            f"Another successful trade on LockBay!"
        )
        
        count = await self._broadcast_to_groups(message)
        if count > 0:
            logger.info(f"Broadcasted rating {escrow_id} to {count} groups")
        return count
    
    async def broadcast_new_user_onboarded(self, data: Dict[str, Any]) -> int:
        """Broadcast when a new user joins LockBay"""
        first_name = data.get('first_name', 'New User')
        username = data.get('username')
        
        user_display = f"{first_name}"
        if username:
            user_display = f"{first_name} (@{username})"
        
        message = (
            f"<b>New User Joined</b>\n\n"
            f"Welcome {user_display} to LockBay!\n\n"
            f"Our community grows stronger. Start your first secure trade today."
        )
        
        count = await self._broadcast_to_groups(message)
        if count > 0:
            logger.info(f"Broadcasted new_user_onboarded to {count} groups")
        return count
    
    # ============================================================================
    # GROUP MANAGEMENT
    # ============================================================================
    
    @staticmethod
    def register_group(chat_id: int, chat_title: str, chat_type: str) -> bool:
        """Register a new group or reactivate an existing one"""
        try:
            from models import BotGroup
            with SessionLocal() as session:
                existing = session.query(BotGroup).filter(BotGroup.chat_id == chat_id).first()
                
                if existing:
                    existing.is_active = True
                    existing.chat_title = chat_title
                    existing.chat_type = chat_type
                    existing.removed_at = None
                    existing.events_enabled = True
                    logger.info(f"Reactivated group: {chat_title} ({chat_id})")
                else:
                    new_group = BotGroup(
                        chat_id=chat_id,
                        chat_title=chat_title,
                        chat_type=chat_type,
                        is_active=True,
                        events_enabled=True
                    )
                    session.add(new_group)
                    logger.info(f"Registered new group: {chat_title} ({chat_id})")
                
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Error registering group {chat_id}: {e}")
            return False
    
    @staticmethod
    def unregister_group(chat_id: int) -> bool:
        """Mark a group as inactive when bot is removed"""
        try:
            from models import BotGroup
            with SessionLocal() as session:
                session.execute(
                    update(BotGroup).where(BotGroup.chat_id == chat_id).values(
                        is_active=False,
                        removed_at=datetime.now(timezone.utc)
                    )
                )
                session.commit()
                logger.info(f"Unregistered group: {chat_id}")
                return True
        except Exception as e:
            logger.error(f"Error unregistering group {chat_id}: {e}")
            return False


# Global instance
group_event_service = GroupEventService()
