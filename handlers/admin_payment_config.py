"""Admin Payment Provider Configuration Handlers"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.payment_config_manager import payment_config_manager
from utils.callback_utils import safe_answer_callback_query

logger = logging.getLogger(__name__)


async def handle_admin_payment_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin payment provider configuration panel"""
    try:
        query = update.callback_query
        await safe_answer_callback_query(query)
        
        user_id = update.effective_user.id
        
        # Validate admin access
        if not payment_config_manager.validate_admin_access(user_id):
            await query.edit_message_text("❌ Access denied. Admin privileges required.")
            return
        
        # Get current configuration
        status = payment_config_manager.get_provider_status_summary()
        config = status.get('configuration', {})
        providers = status.get('providers', {})
        
        # Build status message
        message = "⚙️ Payment Provider Configuration\n\n"
        
        # Current primary provider
        primary = config.get('primary_provider', 'blockbee').upper()
        backup = config.get('backup_provider', 'dynopay').upper()
        
        message += f"🥇 Primary: {primary}\n"
        message += f"🥈 Backup: {backup}\n"
        message += f"🔄 Failover: {'Enabled' if config.get('failover_enabled') else 'Disabled'}\n\n"
        
        # Provider status
        message += "📊 Provider Status:\n"
        
        for provider_name, provider_info in providers.items():
            name = provider_name.upper()
            configured = "✅" if provider_info.get('configured') else "❌"
            enabled = "🟢" if provider_info.get('enabled') else "🔴"
            is_primary = "🥇" if provider_info.get('is_primary') else ""
            
            message += f"{is_primary} {name}: {configured} Configured, {enabled} Enabled\n"
        
        # Build keyboard
        keyboard = []
        
        # Primary provider switching
        if config.get('primary_provider') == 'dynopay':
            keyboard.append([InlineKeyboardButton("🔄 Switch to BlockBee Primary", callback_data="payment_config_set_primary_blockbee")])
        else:
            keyboard.append([InlineKeyboardButton("🔄 Switch to DynoPay Primary", callback_data="payment_config_set_primary_dynopay")])
        
        # Failover toggle
        if config.get('failover_enabled'):
            keyboard.append([InlineKeyboardButton("⏸️ Disable Failover", callback_data="payment_config_failover_disable")])
        else:
            keyboard.append([InlineKeyboardButton("▶️ Enable Failover", callback_data="payment_config_failover_enable")])
        
        # Provider enable/disable buttons
        provider_row = []
        
        blockbee_enabled = providers.get('blockbee', {}).get('enabled', False)
        if blockbee_enabled:
            provider_row.append(InlineKeyboardButton("🔴 Disable BlockBee", callback_data="payment_config_disable_blockbee"))
        else:
            provider_row.append(InlineKeyboardButton("🟢 Enable BlockBee", callback_data="payment_config_enable_blockbee"))
        
        dynopay_enabled = providers.get('dynopay', {}).get('enabled', False)
        if dynopay_enabled:
            provider_row.append(InlineKeyboardButton("🔴 Disable DynoPay", callback_data="payment_config_disable_dynopay"))
        else:
            provider_row.append(InlineKeyboardButton("🟢 Enable DynoPay", callback_data="payment_config_enable_dynopay"))
        
        keyboard.append(provider_row)
        
        # Navigation buttons
        keyboard.append([
            InlineKeyboardButton("📊 Provider Status", callback_data="admin_payment_status"),
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_payment_config")
        ])
        keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error handling payment config panel: {e}")
        await query.edit_message_text(
            "❌ Error loading payment configuration. Please try again.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")
            ]])
        )


async def handle_payment_config_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment configuration actions"""
    try:
        query = update.callback_query
        await safe_answer_callback_query(query)
        
        user_id = update.effective_user.id
        action = query.data
        
        # Validate admin access
        if not payment_config_manager.validate_admin_access(user_id):
            await query.edit_message_text("❌ Access denied. Admin privileges required.")
            return
        
        result = None
        
        # Handle different actions
        if action == "payment_config_set_primary_blockbee":
            result = payment_config_manager.set_primary_provider("blockbee", user_id)
            
        elif action == "payment_config_set_primary_dynopay":
            result = payment_config_manager.set_primary_provider("dynopay", user_id)
            
        elif action == "payment_config_failover_enable":
            result = payment_config_manager.toggle_failover(True, user_id)
            
        elif action == "payment_config_failover_disable":
            result = payment_config_manager.toggle_failover(False, user_id)
            
        elif action == "payment_config_enable_blockbee":
            result = payment_config_manager.toggle_provider("blockbee", True, user_id)
            
        elif action == "payment_config_disable_blockbee":
            result = payment_config_manager.toggle_provider("blockbee", False, user_id)
            
        elif action == "payment_config_enable_dynopay":
            result = payment_config_manager.toggle_provider("dynopay", True, user_id)
            
        elif action == "payment_config_disable_dynopay":
            result = payment_config_manager.toggle_provider("dynopay", False, user_id)
        
        # Show result and refresh config panel
        if result:
            if result.get('success'):
                # Show success message briefly
                await query.edit_message_text(
                    f"✅ {result.get('message', 'Configuration updated successfully')}\n\n"
                    "Refreshing configuration...",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔄 Continue", callback_data="admin_payment_config")
                    ]])
                )
                
                # Auto-refresh after 2 seconds
                import asyncio
                await asyncio.sleep(2)
                await handle_admin_payment_config(update, context)
                
            else:
                await query.edit_message_text(
                    f"❌ Error: {result.get('error', 'Configuration update failed')}\n\n"
                    "Please try again.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Back to Config", callback_data="admin_payment_config")
                    ]])
                )
        else:
            await query.edit_message_text(
                "❌ Unknown configuration action.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to Config", callback_data="admin_payment_config")
                ]])
            )
        
    except Exception as e:
        logger.error(f"Error handling payment config action: {e}")
        await query.edit_message_text(
            f"❌ Error processing configuration change: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Config", callback_data="admin_payment_config")
            ]])
        )


# Export handlers for registration
PAYMENT_CONFIG_HANDLERS = [
    {"type": "callback_query", "name": "handle_admin_payment_config", "pattern": "^admin_payment_config$"},
    {"type": "callback_query", "name": "handle_payment_config_action", "pattern": "^payment_config_"},
]