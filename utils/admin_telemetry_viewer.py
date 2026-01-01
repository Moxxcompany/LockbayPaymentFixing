"""
Admin telemetry viewer - displays performance metrics
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import Config
from utils.performance_telemetry import telemetry

logger = logging.getLogger(__name__)


async def view_telemetry_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display performance telemetry statistics (admin only)"""
    user_id = update.effective_user.id
    
    # Admin check
    if user_id not in Config.ADMIN_USER_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    try:
        summary = telemetry.get_summary()
        
        uptime_hours = summary['uptime_seconds'] / 3600
        
        message = "📊 *PERFORMANCE TELEMETRY*\n\n"
        message += f"⏱️ *Uptime:* {uptime_hours:.2f} hours\n\n"
        
        # Cache metrics
        if summary['cache_metrics']:
            message += "📦 *CACHE METRICS:*\n"
            for cache_name, metrics in summary['cache_metrics'].items():
                message += f"\n*{cache_name}*:\n"
                message += f"• Requests: {metrics['total_requests']}\n"
                message += f"• Hits: {metrics['hits']} | Misses: {metrics['misses']}\n"
                message += f"• Hit Rate: {metrics['hit_rate']}\n"
                message += f"• Invalidations: {metrics['invalidations']}\n"
        
        # Latency metrics
        if summary['latency_metrics']:
            message += "\n⏱️ *LATENCY METRICS:*\n"
            for op_name, metrics in summary['latency_metrics'].items():
                message += f"\n*{op_name}*:\n"
                message += f"• Samples: {metrics['count']}\n"
                message += f"• Avg: {metrics['average_ms']}ms\n"
                message += f"• P95: {metrics['p95_ms']}ms\n"
                message += f"• P99: {metrics['p99_ms']}ms\n"
        
        if not summary['cache_metrics'] and not summary['latency_metrics']:
            message += "_No metrics collected yet. Metrics appear after bot activity._"
        
        await update.message.reply_text(message, parse_mode="Markdown")
        
        # Also log to console
        telemetry.log_summary()
        
    except Exception as e:
        logger.error(f"Error displaying telemetry: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
