"""
Promotional Message Background Job

Runs every 30 minutes via the ConsolidatedScheduler.
Checks if any users' local time matches the morning (10 AM) or evening (6 PM) send window,
and sends them a promotional message if they haven't already received one today.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def run_promo_messages():
    """
    Main entry point for the promo message job.
    Determines which session(s) to process based on UTC time
    and delegates to the promo service.
    """
    try:
        from services.promo_message_service import send_promo_messages
        
        current_utc_hour = datetime.now(timezone.utc).hour
        
        # Morning session: run for all UTC hours since different timezones
        # have 10 AM at different UTC hours
        morning_stats = await send_promo_messages("morning")
        
        # Evening session: same logic
        evening_stats = await send_promo_messages("evening")
        
        total_sent = morning_stats.get("sent", 0) + evening_stats.get("sent", 0)
        total_failed = morning_stats.get("failed", 0) + evening_stats.get("failed", 0)
        
        if total_sent > 0 or total_failed > 0:
            logger.info(
                f"Promo job complete — "
                f"morning: {morning_stats.get('sent', 0)} sent, "
                f"evening: {evening_stats.get('sent', 0)} sent, "
                f"total_failed: {total_failed}"
            )
        
    except Exception as e:
        logger.error(f"Promo message job failed: {e}")
