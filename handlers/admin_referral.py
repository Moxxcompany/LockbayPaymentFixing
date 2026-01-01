"""Admin referral management handlers for Telegram bot"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from utils.admin_security import is_admin_secure
from utils.callback_utils import safe_answer_callback_query, safe_edit_message_text
from services.referral_admin_service import ReferralAdminService

logger = logging.getLogger(__name__)

async def handle_admin_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main admin referral management panel"""
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.message:
            await update.message.reply_text("❌ Access denied. Admin access required.")
        elif update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return None

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query, "🎯")

    # Get system analytics
    analytics = ReferralAdminService.get_system_analytics(days=30)
    config = ReferralAdminService.get_current_config()

    # COMPACT REFERRAL ADMIN PANEL - 70% less clutter
    total_users = analytics["total_stats"]["total_users_referred"]
    rewards_paid = analytics["total_stats"]["total_rewards_paid"]
    pending_alerts = analytics["fraud_alerts"]["pending_total"]
    system_status = "✅ ON" if config["system_enabled"] else "❌ OFF"

    message = f"""🎯 Referral Admin
📊 {total_users:,} users • ${rewards_paid:,.0f} paid • {pending_alerts} alerts
⚙️ System: {system_status} • ${config['referrer_reward_usd']:.0f} reward

Choose action:"""

    # COMPACT KEYBOARD - Streamlined admin actions
    keyboard = [
        [
            InlineKeyboardButton(
                "📈 Analytics", callback_data="admin_referral_analytics"
            ),
            InlineKeyboardButton("⚙️ Config", callback_data="admin_referral_config"),
        ],
        [
            InlineKeyboardButton("🚨 Alerts", callback_data="admin_referral_alerts"),
            InlineKeyboardButton("👥 Users", callback_data="admin_referral_users"),
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_referrals"),
            InlineKeyboardButton("🏠 Back", callback_data="admin_main"),
        ],
    ]

    if query:
        await safe_edit_message_text(
            query,
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        if update.message:
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

async def handle_admin_referral_analytics(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Show detailed referral analytics"""
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        return None

    query = update.callback_query
    await safe_answer_callback_query(query, "📈")

    # Get analytics for different periods
    analytics_7d = ReferralAdminService.get_system_analytics(days=7)
    analytics_30d = ReferralAdminService.get_system_analytics(days=30)
    analytics_90d = ReferralAdminService.get_system_analytics(days=90)

    message = f"""📈 Referral System Analytics

7 Days:
• New Referrals: {analytics_7d['total_stats']['recent_referrals']}
• Rewards Paid: ${analytics_7d['total_stats']['total_rewards_paid']:.2f}
• Conversion: {analytics_7d['total_stats']['conversion_rate']}%

30 Days:
• New Referrals: {analytics_30d['total_stats']['recent_referrals']}
• Rewards Paid: ${analytics_30d['total_stats']['total_rewards_paid']:.2f}
• Conversion: {analytics_30d['total_stats']['conversion_rate']}%

90 Days:
• New Referrals: {analytics_90d['total_stats']['recent_referrals']}
• Rewards Paid: ${analytics_90d['total_stats']['total_rewards_paid']:.2f}
• Conversion: {analytics_90d['total_stats']['conversion_rate']}%

System Health:
• Fraud Rate: {analytics_30d['system_health']['fraud_rate']}%
• Growth Trend: {analytics_30d['system_health']['growth_trend'].title()}

Top Referrers (All Time):"""

    for i, referrer in enumerate(analytics_30d["top_referrers"][:5], 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        message += f"\n{emoji} {referrer['display_name']}: {referrer['referral_count']} referrals"

    keyboard = [
        [
            InlineKeyboardButton(
                "📊 Export Report", callback_data="admin_referral_export"
            ),
            InlineKeyboardButton(
                "🎯 View Trends", callback_data="admin_referral_trends"
            ),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_referrals")],
    ]

    await safe_edit_message_text(
        query,
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def handle_admin_referral_config(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Show and manage referral configuration"""
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        return None

    query = update.callback_query
    await safe_answer_callback_query(query, "⚙️")

    config = ReferralAdminService.get_current_config()

    message = f"""⚙️ Referral System Configuration

💰 Reward Settings:
• Referrer Reward: ${config['referrer_reward_usd']:.2f}
• Referee Bonus: ${config['referee_reward_usd']:.2f}
• Min Activity: ${config['min_activity_for_reward']:.2f}

🎯 System Settings:
• Status: {'✅ Enabled' if config['system_enabled'] else '❌ Disabled'}
• Max Referrals/User: {config['max_referrals_per_user'] or 'Unlimited'}
• Reward Cap/User: ${config['reward_cap_per_user']:.2f if config['reward_cap_per_user'] else 'Unlimited'}

🛡️ Fraud Protection:
• Fraud Detection: {'✅ Enabled' if config['enable_fraud_detection'] else '❌ Disabled'}
• Min Account Age: {config['min_account_age_hours']}h
• Max Referrals/Day: {config['max_referrals_per_day']}

📅 Last Updated: {config['updated_at'][:19] if config['updated_at'] else 'Never'}
👤 Updated By: Admin {config['updated_by_admin_id'] or 'System'}"""

    keyboard = [
        [
            InlineKeyboardButton(
                "💰 Edit Rewards", callback_data="admin_config_rewards"
            ),
            InlineKeyboardButton(
                "⚙️ System Settings", callback_data="admin_config_system"
            ),
        ],
        [
            InlineKeyboardButton(
                "🛡️ Fraud Settings", callback_data="admin_config_fraud"
            ),
            InlineKeyboardButton(
                "🔄 Reset to Default", callback_data="admin_config_reset"
            ),
        ],
        [
            InlineKeyboardButton("✅ Save Changes", callback_data="admin_config_save"),
            InlineKeyboardButton("🔙 Back", callback_data="admin_referrals"),
        ],
    ]

    await safe_edit_message_text(
        query,
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def handle_admin_referral_alerts(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Show pending fraud alerts"""
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        return None

    query = update.callback_query
    await safe_answer_callback_query(query, "🚨")

    alerts = ReferralAdminService.get_pending_fraud_alerts()

    if not alerts:
        message = """🚨 Fraud Alert Management

✅ No pending fraud alerts!

All referral activity appears normal."""

        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_referrals")]]
    else:
        message = f"""🚨 Fraud Alert Management

⚠️ {len(alerts)} Pending Alerts

Recent Alerts:"""

        for alert in alerts[:5]:
            severity_emoji = (
                "🔥"
                if alert["severity"] == "critical"
                else "⚠️" if alert["severity"] == "high" else "⚡"
            )
            message += f"""

{severity_emoji} Alert #{alert['alert_id']}
• User: {alert['user_info']['first_name']} (@{alert['user_info']['username']})
• Type: {alert['alert_type'].replace('_', ' ').title()}
• Severity: {alert['severity'].title()}
• Description: {alert['description']}"""

        if len(alerts) > 5:
            message += f"\n\n... and {len(alerts) - 5} more alerts"

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔍 Review Alerts", callback_data="admin_alerts_review"
                ),
                InlineKeyboardButton(
                    "⚡ Quick Actions", callback_data="admin_alerts_quick"
                ),
            ],
            [
                InlineKeyboardButton(
                    "📊 Alert Stats", callback_data="admin_alerts_stats"
                ),
                InlineKeyboardButton("🔙 Back", callback_data="admin_referrals"),
            ],
        ]

    await safe_edit_message_text(
        query,
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def handle_admin_referral_users(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """User management interface"""
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        return None

    query = update.callback_query
    await safe_answer_callback_query(query, "👥")

    # Get top referrers for management
    analytics = ReferralAdminService.get_system_analytics(days=90)
    top_referrers = analytics["top_referrers"][:10]

    message = """👥 User Management

🎯 Quick Actions:
• Search specific user
• Bulk operations
• Top performer management

🏆 Top Referrers (90 days):"""

    for i, referrer in enumerate(top_referrers[:5], 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        message += f"\n{emoji} {referrer['display_name']}: {referrer['referral_count']} referrals"

    keyboard = [
        [
            InlineKeyboardButton("🔍 Search User", callback_data="admin_user_search"),
            InlineKeyboardButton("👑 Top Performers", callback_data="admin_user_top"),
        ],
        [
            InlineKeyboardButton("🚫 Block Users", callback_data="admin_user_block"),
            InlineKeyboardButton("📊 Bulk Operations", callback_data="admin_user_bulk"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_referrals")],
    ]

    await safe_edit_message_text(
        query,
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def admin_referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command handler for /admin_referrals"""
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.message:
            await update.message.reply_text("❌ Access denied. Admin access required.")
        return None

    await handle_admin_referrals(update, context)

# Additional callback handlers for specific actions
async def handle_admin_config_rewards(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Handle reward configuration editing"""
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        return None

    query = update.callback_query
    await safe_answer_callback_query(query, "💰")

    # Store context for conversation handling
    if context.user_data is not None:
        context.user_data["admin_config_mode"] = "rewards"

    from utils.referral import ReferralSystem
    
    message = f"""💰 Edit Reward Configuration

Please send the new values in this format:
`referrer_reward referee_reward min_activity`

Example: `6.0 4.0 75.0`

Current values:
• Referrer Reward: ${ReferralSystem.REFERRER_REWARD_USD:.2f}
• Referee Bonus: ${ReferralSystem.REFEREE_REWARD_USD:.2f}  
• Min Activity: ${ReferralSystem.MIN_ACTIVITY_FOR_REWARD:.2f}

Send /cancel to abort."""

    keyboard = [
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_referral_config")]
    ]

    await safe_edit_message_text(
        query,
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def handle_admin_toggle_system(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Toggle referral system on/off"""
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        return None

    query = update.callback_query
    await safe_answer_callback_query(query, "⚙️")

    config = ReferralAdminService.get_current_config()
    new_status = not config["system_enabled"]

    result = ReferralAdminService.update_config(
        admin_user_id=user.id,
        updates={"system_enabled": new_status},
        reason=f"System {'enabled' if new_status else 'disabled'} via admin panel",
    )

    if result["success"]:
        pass
    else:
        f"❌ Error updating system status: {result['error']}"

    # Return to config panel
    await handle_admin_referral_config(update, context)
