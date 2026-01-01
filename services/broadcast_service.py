"""Professional broadcast service with batch processing and analytics"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import uuid

from telegram import Bot
from telegram.error import TelegramError, Forbidden, BadRequest
from models import User
from database import get_session

logger = logging.getLogger(__name__)


class CampaignStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchResult:
    batch_number: int
    total_batches: int
    users_in_batch: int
    successful_sends: int
    failed_sends: int
    failed_users: List[Dict[str, Any]]
    processing_time: float


@dataclass
class CampaignResult:
    campaign_id: str
    status: CampaignStatus
    total_users: int
    total_successful: int
    total_failed: int
    total_batches: int
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None


class BroadcastService:
    """Professional broadcast service with batch processing and analytics"""

    BATCH_SIZE = 30
    BATCH_DELAY = 3.0  # 3 seconds delay between batches (Telegram compliance)
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0  # 2 seconds between retries

    def __init__(self, bot: Bot):
        self.bot = bot
        self.active_campaigns: Dict[str, CampaignResult] = {}

    async def start_broadcast_campaign(
        self,
        message: str,
        admin_user_id: int,
        target_users: Optional[List[User]] = None,
    ) -> str:
        """Start a new broadcast campaign"""
        campaign_id = str(uuid.uuid4())[:8]

        session = get_session()
        try:
            # Get all users if no specific targets provided
            if target_users is None:
                target_users = (
                    session.query(User).filter(User.telegram_id.isnot(None)).all()
                )

            total_users = len(target_users)
            if total_users == 0:
                await self.bot.send_message(
                    chat_id=admin_user_id,
                    text="❌ Broadcast Failed\n\nNo users found to send messages to.",
                )
                return campaign_id

            # Initialize campaign
            campaign = CampaignResult(
                campaign_id=campaign_id,
                status=CampaignStatus.PENDING,
                total_users=total_users,
                total_successful=0,
                total_failed=0,
                total_batches=(total_users + self.BATCH_SIZE - 1) // self.BATCH_SIZE,
                start_time=datetime.utcnow(),
            )

            self.active_campaigns[campaign_id] = campaign

            # Send campaign start notification
            await self.bot.send_message(
                chat_id=admin_user_id,
                text=f"🚀 Broadcast Campaign Started\n\n"
                f"📋 Campaign ID: `{campaign_id}`\n"
                f"👥 Target Users: {total_users:,}\n"
                f"📦 Total Batches: {campaign.total_batches}\n"
                f"⏱️ Estimated Duration: {campaign.total_batches * self.BATCH_DELAY:.1f}s\n\n"
                f"📊 Progress updates will be sent after each batch...",
                parse_mode="Markdown",
            )

            # Start background processing
            asyncio.create_task(
                self._process_campaign(
                    campaign_id, message, admin_user_id, target_users
                )
            )

            return campaign_id

        except Exception as e:
            logger.error(f"Error starting broadcast campaign: {e}")
            await self.bot.send_message(
                chat_id=admin_user_id,
                text=f"❌ Campaign Failed to Start\n\nError: {str(e)}",
            )
            return campaign_id
        finally:
            session.close()

    async def _process_campaign(
        self,
        campaign_id: str,
        message: str,
        admin_user_id: int,
        target_users: List[User],
    ):
        """Process broadcast campaign in background"""
        campaign = self.active_campaigns.get(campaign_id)
        if not campaign:
            return

        try:
            campaign.status = CampaignStatus.RUNNING

            # Process users in batches
            for batch_num in range(campaign.total_batches):
                start_idx = batch_num * self.BATCH_SIZE
                end_idx = min(start_idx + self.BATCH_SIZE, len(target_users))
                batch_users = target_users[start_idx:end_idx]

                # Process batch
                batch_result = await self._process_batch(
                    batch_users, message, batch_num + 1, campaign.total_batches
                )

                # Update campaign stats
                campaign.total_successful += batch_result.successful_sends
                campaign.total_failed += batch_result.failed_sends

                # Send batch analytics to admin
                await self._send_batch_analytics(
                    admin_user_id, campaign_id, batch_result
                )

                # Delay between batches (except for last batch)
                if batch_num < campaign.total_batches - 1:
                    await asyncio.sleep(self.BATCH_DELAY)

            # Campaign completed
            campaign.status = CampaignStatus.COMPLETED
            campaign.end_time = datetime.utcnow()
            campaign.duration = (
                campaign.end_time - campaign.start_time
            ).total_seconds()

            # Send final analytics
            await self._send_final_analytics(admin_user_id, campaign)

        except Exception as e:
            logger.error(f"Error processing campaign {campaign_id}: {e}")
            campaign.status = CampaignStatus.FAILED
            await self.bot.send_message(
                chat_id=admin_user_id,
                text=f"❌ Campaign {campaign_id} Failed\n\nError: {str(e)}",
            )

    async def _process_batch(
        self,
        batch_users: List[User],
        message: str,
        batch_number: int,
        total_batches: int,
    ) -> BatchResult:
        """Process a single batch with retry logic"""
        start_time = datetime.utcnow()
        successful = 0
        failed = 0
        failed_users = []

        for user in batch_users:
            telegram_id = str(user.telegram_id) if user.telegram_id else None
            if not telegram_id:
                failed += 1
                failed_users.append(
                    {
                        "user_id": user.id,
                        "telegram_id": None,
                        "reason": "No Telegram ID",
                    }
                )
                continue

            success = await self._send_message_with_retry(telegram_id, message)
            if success:
                successful += 1
            else:
                failed += 1
                failed_users.append(
                    {
                        "user_id": user.id,
                        "telegram_id": telegram_id,
                        "reason": "Failed after retries",
                    }
                )

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        return BatchResult(
            batch_number=batch_number,
            total_batches=total_batches,
            users_in_batch=len(batch_users),
            successful_sends=successful,
            failed_sends=failed,
            failed_users=failed_users,
            processing_time=processing_time,
        )

    async def _send_message_with_retry(self, telegram_id: str, message: str) -> bool:
        """Send message with retry logic"""
        for attempt in range(self.MAX_RETRIES):
            try:
                await self.bot.send_message(chat_id=telegram_id, text=message, parse_mode="HTML")
                return True
            except Forbidden:
                # User blocked the bot - don't retry
                logger.info(f"User {telegram_id} has blocked the bot")
                return False
            except BadRequest as e:
                # Chat not found or other bad request - don't retry
                logger.info(f"Bad request for user {telegram_id}: {e}")
                return False
            except TelegramError as e:
                logger.warning(
                    f"Telegram error for user {telegram_id} (attempt {attempt + 1}): {e}"
                )
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY)
                else:
                    return False
            except Exception as e:
                logger.error(f"Unexpected error sending to user {telegram_id}: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY)
                else:
                    return False

        return False

    async def _send_batch_analytics(
        self, admin_user_id: int, campaign_id: str, batch_result: BatchResult
    ):
        """Send batch completion analytics to admin"""
        campaign = self.active_campaigns.get(campaign_id)
        if not campaign:
            return

        progress_percentage = (
            batch_result.batch_number / batch_result.total_batches
        ) * 100
        remaining_batches = batch_result.total_batches - batch_result.batch_number
        estimated_remaining = remaining_batches * self.BATCH_DELAY

        analytics_text = f"""📊 Batch {batch_result.batch_number}/{batch_result.total_batches} Completed

🎯 Campaign: `{campaign_id}`
📦 Batch Stats:
├ 👥 Users: {batch_result.users_in_batch}
├ ✅ Successful: {batch_result.successful_sends}
├ ❌ Failed: {batch_result.failed_sends}
└ ⏱️ Time: {batch_result.processing_time:.1f}s

📈 Overall Progress:
├ 🎯 Total Delivered: {campaign.total_successful:,}
├ ❌ Total Failed: {campaign.total_failed:,}
├ 📊 Progress: {progress_percentage:.1f}%
└ ⏳ Est. Remaining: {estimated_remaining:.1f}s"""

        if batch_result.failed_sends > 0 and len(batch_result.failed_users) <= 5:
            failed_details = "\n".join(
                [
                    f"• {user['telegram_id'] or 'N/A'}: {user['reason']}"
                    for user in batch_result.failed_users[:5]
                ]
            )
            analytics_text += f"\n\n❌ Failed Users:\n{failed_details}"

        try:
            await self.bot.send_message(
                chat_id=admin_user_id, text=analytics_text, parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error sending batch analytics: {e}")

    async def _send_final_analytics(self, admin_user_id: int, campaign: CampaignResult):
        """Send final campaign analytics to admin"""
        success_rate = (
            (campaign.total_successful / campaign.total_users) * 100
            if campaign.total_users > 0
            else 0
        )

        final_text = f"""🎉 Campaign {campaign.campaign_id} Completed!

📊 Final Statistics:
├ 👥 Total Users: {campaign.total_users:,}
├ ✅ Successful: {campaign.total_successful:,} ({success_rate:.1f}%)
├ ❌ Failed: {campaign.total_failed:,}
├ 📦 Total Batches: {campaign.total_batches}
├ ⏱️ Duration: {campaign.duration:.1f}s
└ 📅 Completed: {campaign.end_time.strftime('%H:%M:%S UTC') if campaign.end_time else 'Unknown'}

🎯 Campaign Performance:
{'🟢 Excellent' if success_rate >= 95 else '🟡 Good' if success_rate >= 80 else '🔴 Needs Review'}"""

        try:
            await self.bot.send_message(
                chat_id=admin_user_id, text=final_text, parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error sending final analytics: {e}")

    def get_campaign_status(self, campaign_id: str) -> Optional[CampaignResult]:
        """Get status of a specific campaign"""
        return self.active_campaigns.get(campaign_id)

    def get_active_campaigns(self) -> Dict[str, CampaignResult]:
        """Get all active campaigns"""
        return {
            cid: campaign
            for cid, campaign in self.active_campaigns.items()
            if campaign.status in [CampaignStatus.PENDING, CampaignStatus.RUNNING]
        }

    async def start_multimedia_broadcast_campaign(
        self,
        broadcast_data: Dict[str, Any],
        admin_user_id: int,
        target_users: Optional[List[User]] = None,
    ) -> str:
        """Start a multimedia broadcast campaign"""
        campaign_id = str(uuid.uuid4())[:8]

        if target_users is None:
            session = get_session()
            try:
                target_users = (
                    session.query(User).filter(User.telegram_id.isnot(None)).all()
                )
            finally:
                session.close()

        total_users = len(target_users)
        if total_users == 0:
            await self.bot.send_message(
                chat_id=admin_user_id,
                text="❌ Broadcast Failed\n\nNo users found to send messages to.",
            )
            return campaign_id

        # Initialize campaign
        campaign = CampaignResult(
            campaign_id=campaign_id,
            status=CampaignStatus.PENDING,
            total_users=total_users,
            total_successful=0,
            total_failed=0,
            total_batches=(total_users + self.BATCH_SIZE - 1) // self.BATCH_SIZE,
            start_time=datetime.utcnow(),
        )

        self.active_campaigns[campaign_id] = campaign

        # Send campaign start notification
        media_type = broadcast_data.get("type", "multimedia")
        await self.bot.send_message(
            chat_id=admin_user_id,
            text=f"🚀 {media_type.title()} Broadcast Campaign Started\n\n"
            f"📋 Campaign ID: `{campaign_id}`\n"
            f"👥 Target Users: {total_users:,}\n"
            f"📦 Total Batches: {campaign.total_batches}\n"
            f"⏱️ Estimated Duration: {campaign.total_batches * self.BATCH_DELAY:.1f}s\n\n"
            f"📊 Progress updates will be sent after each batch...",
            parse_mode="Markdown",
        )

        # Start background processing for multimedia
        asyncio.create_task(
            self._process_multimedia_campaign(
                campaign_id, broadcast_data, admin_user_id, target_users
            )
        )

        return campaign_id

    async def _process_multimedia_campaign(
        self,
        campaign_id: str,
        broadcast_data: Dict[str, Any],
        admin_user_id: int,
        target_users: List[User],
    ):
        """Process multimedia broadcast campaign in background"""
        campaign = self.active_campaigns.get(campaign_id)
        if not campaign:
            return

        try:
            campaign.status = CampaignStatus.RUNNING

            # Process users in batches
            for batch_num in range(campaign.total_batches):
                start_idx = batch_num * self.BATCH_SIZE
                end_idx = min(start_idx + self.BATCH_SIZE, len(target_users))
                batch_users = target_users[start_idx:end_idx]

                # Process multimedia batch
                batch_result = await self._process_multimedia_batch(
                    batch_users, broadcast_data, batch_num + 1, campaign.total_batches
                )

                # Update campaign stats
                campaign.total_successful += batch_result.successful_sends
                campaign.total_failed += batch_result.failed_sends

                # Send batch analytics to admin
                await self._send_batch_analytics(
                    admin_user_id, campaign_id, batch_result
                )

                # Delay between batches (except for last batch)
                if batch_num < campaign.total_batches - 1:
                    await asyncio.sleep(self.BATCH_DELAY)

            # Campaign completed
            campaign.status = CampaignStatus.COMPLETED
            campaign.end_time = datetime.utcnow()
            campaign.duration = (
                campaign.end_time - campaign.start_time
            ).total_seconds()

            # Send final analytics
            await self._send_final_analytics(admin_user_id, campaign)

        except Exception as e:
            logger.error(f"Error processing multimedia campaign {campaign_id}: {e}")
            campaign.status = CampaignStatus.FAILED
            await self.bot.send_message(
                chat_id=admin_user_id,
                text=f"❌ Campaign {campaign_id} Failed\n\nError: {str(e)}",
            )

    async def _process_multimedia_batch(
        self,
        batch_users: List[User],
        broadcast_data: Dict[str, Any],
        batch_number: int,
        total_batches: int,
    ) -> BatchResult:
        """Process a multimedia batch with retry logic"""
        start_time = datetime.utcnow()
        successful = 0
        failed = 0
        failed_users = []

        for user in batch_users:
            telegram_id = str(user.telegram_id) if user.telegram_id else None
            if not telegram_id:
                failed += 1
                failed_users.append(
                    {
                        "user_id": user.id,
                        "telegram_id": None,
                        "reason": "No Telegram ID",
                    }
                )
                continue

            success = await self._send_multimedia_with_retry(
                telegram_id, broadcast_data
            )
            if success:
                successful += 1
            else:
                failed += 1
                failed_users.append(
                    {
                        "user_id": user.id,
                        "telegram_id": telegram_id,
                        "reason": "Failed after retries",
                    }
                )

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        return BatchResult(
            batch_number=batch_number,
            total_batches=total_batches,
            users_in_batch=len(batch_users),
            successful_sends=successful,
            failed_sends=failed,
            failed_users=failed_users,
            processing_time=processing_time,
        )

    async def _send_multimedia_with_retry(
        self, telegram_id: str, broadcast_data: Dict[str, Any]
    ) -> bool:
        """Send multimedia message with retry logic"""
        from telegram.error import TelegramError, Forbidden, BadRequest

        for attempt in range(self.MAX_RETRIES):
            try:
                media_type = broadcast_data.get("type")

                if media_type == "photo":
                    await self.bot.send_photo(
                        chat_id=telegram_id,
                        photo=broadcast_data["file_id"],
                        caption=broadcast_data.get("caption", ""),
                    )
                elif media_type == "document":
                    await self.bot.send_document(
                        chat_id=telegram_id,
                        document=broadcast_data["file_id"],
                        caption=broadcast_data.get("caption", ""),
                    )
                elif media_type == "video":
                    await self.bot.send_video(
                        chat_id=telegram_id,
                        video=broadcast_data["file_id"],
                        caption=broadcast_data.get("caption", ""),
                    )
                elif media_type == "audio":
                    await self.bot.send_audio(
                        chat_id=telegram_id,
                        audio=broadcast_data["file_id"],
                        caption=broadcast_data.get("caption", ""),
                    )
                elif media_type == "text":
                    await self.bot.send_message(
                        chat_id=telegram_id,
                        text=broadcast_data["text"],
                        entities=broadcast_data.get("entities", []),
                    )
                elif media_type == "poll":
                    await self.bot.send_poll(
                        chat_id=telegram_id,
                        question=broadcast_data["question"],
                        options=broadcast_data["options"],
                        is_anonymous=True,
                    )
                else:
                    # Fallback to text
                    await self.bot.send_message(
                        chat_id=telegram_id, text=str(broadcast_data)
                    )

                return True

            except Forbidden:
                # User blocked the bot - don't retry
                logger.info(f"User {telegram_id} has blocked the bot")
                return False
            except BadRequest as e:
                # Chat not found or other bad request - don't retry
                logger.info(f"Bad request for user {telegram_id}: {e}")
                return False
            except TelegramError as e:
                logger.warning(
                    f"Telegram error for user {telegram_id} (attempt {attempt + 1}): {e}"
                )
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY)
                else:
                    return False
            except Exception as e:
                logger.error(f"Unexpected error sending to user {telegram_id}: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY)
                else:
                    return False

        return False


# Global broadcast service instance
broadcast_service: Optional[BroadcastService] = None


def get_broadcast_service(bot: Bot) -> BroadcastService:
    """Get or create broadcast service instance"""
    global broadcast_service
    if broadcast_service is None:
        broadcast_service = BroadcastService(bot)
    return broadcast_service
