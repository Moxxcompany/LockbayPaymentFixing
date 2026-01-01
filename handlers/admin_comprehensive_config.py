#!/usr/bin/env python3
"""
Comprehensive Configuration Admin Interface
Complete admin control panel for all platform settings - Phases 1-3
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from services.comprehensive_config_service import ComprehensiveConfigService
from utils.admin_security import admin_required
from utils.error_handler import error_handler
from utils.callback_utils import safe_answer_callback_query

logger = logging.getLogger(__name__)

# Conversation states
(
    MAIN_MENU,
    PHASE1_MENU,
    PHASE2_MENU,
    PHASE3_MENU,
    EDIT_VALUE,
    AUDIT_MENU,
    AB_TEST_MENU,
    ROLLBACK_MENU,
) = range(8)


class AdminComprehensiveConfigHandler:
    """Complete admin interface for platform configuration management"""

    def __init__(self):
        self.config_service = ComprehensiveConfigService()
        logger.info("Admin comprehensive config handler initialized")

    @admin_required
    async def show_config_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Main configuration management menu"""
        try:
            current_config = self.config_service.get_current_config()
            
            status_emoji = "🟢" if current_config.get("platform_enabled") else "🔴"
            maintenance_emoji = "🚧" if current_config.get("maintenance_mode") else "✅"
            
            menu_text = f"""
🏛️ LockBay Platform Configuration Center

System Status
{status_emoji} Platform: {'Enabled' if current_config.get('platform_enabled') else 'Disabled'}
{maintenance_emoji} Maintenance: {'Active' if current_config.get('maintenance_mode') else 'Normal'}
📊 Config Version: {current_config.get('config_version', '3.0')}

Configuration Phases
{'✅' if current_config.get('phase_1_enabled') else '❌'} Phase 1: Financial Controls
{'✅' if current_config.get('phase_2_enabled') else '❌'} Phase 2: Security & Monitoring  
{'✅' if current_config.get('phase_3_enabled') else '❌'} Phase 3: Advanced Features

Select a configuration category to manage:
"""

            keyboard = [
                [
                    InlineKeyboardButton("💰 Financial Controls", callback_data="config_phase1"),
                    InlineKeyboardButton("🛡️ Security & Monitoring", callback_data="config_phase2"),
                ],
                [
                    InlineKeyboardButton("⚡ Advanced Features", callback_data="config_phase3"),
                    InlineKeyboardButton("📊 A/B Testing", callback_data="config_ab_testing"),
                ],
                [
                    InlineKeyboardButton("📋 Audit Trail", callback_data="config_audit"),
                    InlineKeyboardButton("🔄 Rollback", callback_data="config_rollback"),
                ],
                [
                    InlineKeyboardButton("🎛️ Quick Actions", callback_data="config_quick_actions"),
                    InlineKeyboardButton("❌ Close", callback_data="admin_main_menu"),
                ],
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            # FIXED: Use unified message handling to prevent duplication
            from utils.message_utils import send_unified_message
            await send_unified_message(
                update, menu_text, reply_markup=reply_markup, parse_mode="Markdown"
            )

            return MAIN_MENU

        except Exception as e:
            logger.error(f"Error showing config main menu: {e}")
            if update.effective_message:
                await update.effective_message.reply_text("❌ Error loading configuration menu")
            return ConversationHandler.END

    @admin_required
    async def handle_phase1_financial_controls(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Phase 1: Financial Controls Management"""
        try:
            config = self.config_service.get_current_config()
            
            menu_text = f"""
💰 Phase 1: Financial Controls

Escrow & Trading Limits
• Min Escrow: ${config.get('min_escrow_amount_usd', 5.0):.2f}
• Max Escrow: ${config.get('max_escrow_amount_usd', 100000.0):,.2f}
• Min Exchange: ${config.get('min_exchange_amount_usd', 5.0):.2f}
• Escrow Fee: {config.get('escrow_fee_percentage', 5.0):.1f}%
• Exchange Markup: {config.get('exchange_markup_percentage', 5.0):.1f}%

CashOut Limits
• Min CashOut: ${config.get('min_cashout_amount_usd', 1.0):.2f}
• Max CashOut: ${config.get('max_cashout_amount_usd', 10000.0):,.2f}
• Admin Approval Threshold: ${config.get('admin_approval_threshold_usd', 500.0):,.2f}
• Auto Cashout Min: ${config.get('min_auto_cashout_amount_usd', 25.0):.2f}

Fee Structure
• TRC20 Fee: ${config.get('trc20_flat_fee_usd', 4.0):.2f}
• ERC20 Fee: ${config.get('erc20_flat_fee_usd', 4.0):.2f}
• NGN Fee: ₦{config.get('ngn_flat_fee_naira', 2000.0):.2f}
• Cashout %: {config.get('percentage_cashout_fee', 2.0):.1f}%
"""

            keyboard = [
                [
                    InlineKeyboardButton("📊 Escrow Limits", callback_data="edit_escrow_limits"),
                    InlineKeyboardButton("💸 CashOut Limits", callback_data="edit_cashout_limits"),
                ],
                [
                    InlineKeyboardButton("💳 Fee Structure", callback_data="edit_fee_structure"),
                    InlineKeyboardButton("📈 Markup Settings", callback_data="edit_markup_settings"),
                ],
                [
                    InlineKeyboardButton("🔍 Regional Pricing", callback_data="edit_regional_pricing"),
                    InlineKeyboardButton("🔙 Back", callback_data="config_main_menu"),
                ],
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            if update.callback_query:
                await update.callback_query.edit_message_text(
                text=menu_text, reply_markup=reply_markup, parse_mode="Markdown"
            )

            return PHASE1_MENU

        except Exception as e:
            logger.error(f"Error showing Phase 1 menu: {e}")
            if update.callback_query:
                await safe_answer_callback_query(update.callback_query, "❌ Error loading financial controls")
            return MAIN_MENU

    @admin_required
    async def handle_phase2_security_monitoring(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Phase 2: Security & Monitoring Management"""
        try:
            config = self.config_service.get_current_config()
            
            menu_text = f"""
🛡️ Phase 2: Security & Monitoring

Anomaly Detection Thresholds
• Low Risk: {config.get('low_anomaly_threshold', 30.0):.1f}
• Medium Risk: {config.get('medium_anomaly_threshold', 50.0):.1f}
• High Risk: {config.get('high_anomaly_threshold', 70.0):.1f}
• Critical Risk: {config.get('critical_anomaly_threshold', 85.0):.1f}

Security Parameters
• Suspicious Cashout: {int(config.get('suspicious_cashout_threshold', 0.8) * 100)}% of balance
• Rapid Transaction Limit: {config.get('rapid_transaction_threshold', 5)} transactions
• Analysis Window: {config.get('rapid_transaction_window_seconds', 300)} seconds
• Historical Analysis: {config.get('transaction_analysis_days', 90)} days

Balance Monitoring
• Fincra Threshold: ₦{config.get('fincra_low_balance_threshold_ngn', 100000.0):,.2f}
• Kraken Threshold: ${config.get('kraken_low_balance_threshold_usd', 1000.0):,.2f}
• Alert Cooldown: {config.get('balance_alert_cooldown_hours', 6)} hours

Daily Balance Email Reports
• Email Reports: {'✅ Enabled' if config.get('balance_email_enabled', True) else '❌ Disabled'}
• Email Frequency: Every {config.get('balance_email_frequency_hours', 12)} hours
• Email Times: {config.get('balance_email_times', '09:00,21:00')}
"""

            keyboard = [
                [
                    InlineKeyboardButton("🎯 Anomaly Thresholds", callback_data="edit_anomaly_thresholds"),
                    InlineKeyboardButton("🔒 Security Parameters", callback_data="edit_security_params"),
                ],
                [
                    InlineKeyboardButton("📊 Balance Monitoring", callback_data="edit_balance_monitoring"),
                    InlineKeyboardButton("📧 Daily Email Reports", callback_data="edit_daily_balance_emails"),
                ],
                [
                    InlineKeyboardButton("🚨 Alert Settings", callback_data="edit_alert_settings"),
                    InlineKeyboardButton("⏰ Email Schedule", callback_data="edit_email_schedule"),
                ],
                [
                    InlineKeyboardButton("📈 Risk Analytics", callback_data="view_risk_analytics"),
                    InlineKeyboardButton("🔙 Back", callback_data="config_main_menu"),
                ],
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            if update.callback_query:
                await update.callback_query.edit_message_text(
                text=menu_text, reply_markup=reply_markup, parse_mode="Markdown"
            )

            return PHASE2_MENU

        except Exception as e:
            logger.error(f"Error showing Phase 2 menu: {e}")
            if update.callback_query:
                await safe_answer_callback_query(update.callback_query, "❌ Error loading security settings")
            return MAIN_MENU

    @admin_required
    async def handle_phase3_advanced_features(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Phase 3: Advanced Features Management"""
        try:
            config = self.config_service.get_current_config()
            
            menu_text = f"""
⚡ Phase 3: Advanced Features

Timeouts & Limits
• Delivery Timeout: {config.get('default_delivery_timeout_hours', 72)} hours
• Max Delivery: {config.get('max_delivery_timeout_hours', 336)} hours
• Exchange Timeout: {config.get('crypto_exchange_timeout_minutes', 60)} minutes
• Rate Lock: {config.get('rate_lock_duration_minutes', 15)} minutes
• Max File Size: {config.get('max_file_size_mb', 20)} MB

Regional Adjustments
• Global Regional: {'✅' if config.get('enable_global_regional_adjustments') else '❌'}
• Developing: {int(config.get('regional_multiplier_developing', 0.4) * 100)}%
• Emerging: {int(config.get('regional_multiplier_emerging', 0.6) * 100)}%
• Developed: {int(config.get('regional_multiplier_developed', 1.0) * 100)}%

Performance Settings
• Batch Processing: {'✅' if config.get('enable_batch_processing') else '❌'}
• Batch Size: {config.get('batch_size_limit', 100)}
• Cache Duration: {config.get('cache_duration_minutes', 15)} minutes
• Job Interval: {config.get('background_job_interval_minutes', 5)} minutes
"""

            keyboard = [
                [
                    InlineKeyboardButton("⏱️ Timeouts & Limits", callback_data="edit_timeouts"),
                    InlineKeyboardButton("🌍 Regional Settings", callback_data="edit_regional_settings"),
                ],
                [
                    InlineKeyboardButton("⚡ Performance", callback_data="edit_performance_settings"),
                    InlineKeyboardButton("🔧 System Flags", callback_data="edit_system_flags"),
                ],
                [
                    InlineKeyboardButton("📊 Performance Monitor", callback_data="view_performance_monitor"),
                    InlineKeyboardButton("🔙 Back", callback_data="config_main_menu"),
                ],
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            if update.callback_query:
                await update.callback_query.edit_message_text(
                text=menu_text, reply_markup=reply_markup, parse_mode="Markdown"
            )

            return PHASE3_MENU

        except Exception as e:
            logger.error(f"Error showing Phase 3 menu: {e}")
            if update.callback_query:
                await safe_answer_callback_query(update.callback_query, "❌ Error loading advanced features")
            return MAIN_MENU

    @admin_required
    async def handle_ab_testing_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """A/B Testing Management Interface"""
        try:
            config = self.config_service.get_current_config()
            
            menu_text = f"""
📊 A/B Testing Framework

Current Status
• A/B Testing: {'✅ Enabled' if config.get('enable_ab_testing') else '❌ Disabled'}
• Traffic Split: {config.get('ab_test_traffic_percentage', 10.0):.1f}% of users
• Test Duration: {config.get('ab_test_duration_days', 14)} days

Active Tests
🔬 Loading active tests...

**Test Results**
📈 Performance metrics and statistical significance analysis
"""

            keyboard = [
                [
                    InlineKeyboardButton("🆕 Create Test", callback_data="create_ab_test"),
                    InlineKeyboardButton("📊 View Results", callback_data="view_ab_results"),
                ],
                [
                    InlineKeyboardButton("⚙️ Test Settings", callback_data="edit_ab_settings"),
                    InlineKeyboardButton("🛑 Stop Tests", callback_data="stop_ab_tests"),
                ],
                [
                    InlineKeyboardButton("📈 Analytics", callback_data="view_ab_analytics"),
                    InlineKeyboardButton("🔙 Back", callback_data="config_main_menu"),
                ],
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            if update.callback_query:
                await update.callback_query.edit_message_text(
                text=menu_text, reply_markup=reply_markup, parse_mode="Markdown"
            )

            return AB_TEST_MENU

        except Exception as e:
            logger.error(f"Error showing A/B testing menu: {e}")
            if update.callback_query:
                await safe_answer_callback_query(update.callback_query, "❌ Error loading A/B testing interface")
            return MAIN_MENU

    @admin_required
    async def handle_audit_trail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Configuration audit trail interface"""
        try:
            audits = self.config_service.get_configuration_audit(days_back=7)
            
            audit_text = "📋 Configuration Audit Trail (Last 7 Days)\n\n"
            
            if not audits:
                audit_text += "No configuration changes in the last 7 days."
            else:
                for audit in audits[:10]:  # Show last 10 changes
                    risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(audit["risk_level"], "⚪")
                    audit_text += f"{risk_emoji} {audit['field_name']}\n"
                    audit_text += f"   `{audit['old_value']}` → `{audit['new_value']}`\n"
                    audit_text += f"   By Admin {audit['changed_by_admin_id']} • {audit['changed_at'][:16]}\n"
                    if audit['change_reason']:
                        audit_text += f"   💬 {audit['change_reason']}\n"
                    audit_text += "\n"

            keyboard = [
                [
                    InlineKeyboardButton("📊 Full Audit", callback_data="view_full_audit"),
                    InlineKeyboardButton("🎯 Filter by Risk", callback_data="filter_audit_risk"),
                ],
                [
                    InlineKeyboardButton("📈 Impact Analysis", callback_data="view_impact_analysis"),
                    InlineKeyboardButton("🔙 Back", callback_data="config_main_menu"),
                ],
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            if update.callback_query:
                await update.callback_query.edit_message_text(
                text=audit_text, reply_markup=reply_markup, parse_mode="Markdown"
            )

            return AUDIT_MENU

        except Exception as e:
            logger.error(f"Error showing audit trail: {e}")
            if update.callback_query:
                await safe_answer_callback_query(update.callback_query, "❌ Error loading audit trail")
            return MAIN_MENU

    @admin_required
    async def handle_quick_actions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Quick configuration actions"""
        try:
            config = self.config_service.get_current_config()
            
            quick_actions_text = """
🎛️ Quick Configuration Actions

Choose a quick action to perform:
"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🚧 Toggle Maintenance" if not config.get('maintenance_mode') else "✅ Exit Maintenance",
                        callback_data="toggle_maintenance"
                    ),
                    InlineKeyboardButton(
                        "❌ Disable Platform" if config.get('platform_enabled') else "✅ Enable Platform",
                        callback_data="toggle_platform"
                    ),
                ],
                [
                    InlineKeyboardButton("📊 Export Config", callback_data="export_config"),
                    InlineKeyboardButton("📥 Import Config", callback_data="import_config"),
                ],
                [
                    InlineKeyboardButton("🔄 Reset to Defaults", callback_data="reset_defaults"),
                    InlineKeyboardButton("🔙 Back", callback_data="config_main_menu"),
                ],
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            if update.callback_query:
                await update.callback_query.edit_message_text(
                text=quick_actions_text, reply_markup=reply_markup, parse_mode="Markdown"
            )

            return MAIN_MENU

        except Exception as e:
            logger.error(f"Error showing quick actions: {e}")
            if update.callback_query:
                await safe_answer_callback_query(update.callback_query, "❌ Error loading quick actions")
            return MAIN_MENU

    @admin_required
    async def handle_toggle_maintenance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle maintenance mode"""
        try:
            admin_user = update.effective_user
            if not admin_user:
                return MAIN_MENU
                
            config = self.config_service.get_current_config()
            new_maintenance_state = not config.get('maintenance_mode', False)
            
            result = self.config_service.update_config(
                admin_user_id=admin_user.id,
                updates={"maintenance_mode": new_maintenance_state},
                reason=f"Maintenance mode {'activated' if new_maintenance_state else 'deactivated'} via quick action"
            )
            
            status_text = "🚧 Maintenance mode activated" if new_maintenance_state else "✅ Maintenance mode deactivated"
            if update.callback_query:
                await safe_answer_callback_query(update.callback_query, status_text)
            
            # Return to main menu with updated status
            await self.show_config_main_menu(update, context)
            return MAIN_MENU

        except Exception as e:
            logger.error(f"Error toggling maintenance mode: {e}")
            if update.callback_query:
                await safe_answer_callback_query(update.callback_query, "❌ Error updating maintenance mode")
            return MAIN_MENU

    @admin_required
    async def handle_edit_value_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle request to edit a specific configuration value"""
        try:
            if not update.callback_query or not update.callback_query.data:
                return MAIN_MENU
                
            callback_data = update.callback_query.data
            
            # Parse which value to edit
            if callback_data.startswith("edit_"):
                edit_type = callback_data[5:]  # Remove "edit_" prefix
                if context.user_data is not None:
                    context.user_data['editing_type'] = edit_type
                
                edit_prompts = {
                    "escrow_limits": "💰 Enter new escrow limits (format: min_usd,max_usd):",
                    "cashout_limits": "💸 Enter new cashout limits (format: min_usd,max_usd,approval_threshold):",
                    "fee_structure": "💳 Enter new fee structure (format: trc20_fee,erc20_fee,ngn_fee):",
                    "markup_settings": "📈 Enter markup percentages (format: escrow_fee%,exchange_markup%):",
                    "anomaly_thresholds": "🎯 Enter anomaly thresholds (format: low,medium,high,critical):",
                    "security_params": "🔒 Enter security parameters (format: cashout_threshold,rapid_limit,window_seconds):",
                    "balance_monitoring": "📊 Enter balance thresholds (format: fincra_ngn,kraken_usd,cooldown_hours):",
                    "daily_balance_emails": "📧 Enter email settings (format: enabled,frequency_hours - true/false,12):",
                    "email_schedule": "⏰ Enter email times (format: HH:MM,HH:MM - e.g., 09:00,21:00):",
                    "timeouts": "⏱️ Enter timeout settings (format: delivery_hours,max_hours,exchange_minutes):",
                    "regional_settings": "🌍 Enter regional multipliers (format: developing,emerging,developed):",
                    "performance_settings": "⚡ Enter performance settings (format: batch_size,cache_minutes,job_interval):",
                }
                
                prompt_text = edit_prompts.get(edit_type, "📝 Enter new configuration values:")
                
                if update.callback_query:
                    await update.callback_query.edit_message_text(
                        text=f"{prompt_text}\n\nSend 'cancel' to abort.",
                        parse_mode="Markdown"
                    )
                
                return EDIT_VALUE

        except Exception as e:
            logger.error(f"Error handling edit value request: {e}")
            if update.callback_query:
                await safe_answer_callback_query(update.callback_query, "❌ Error processing edit request")
            return MAIN_MENU

    @admin_required
    async def handle_value_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user input for configuration value changes"""
        try:
            if not update.message or not update.message.text:
                return MAIN_MENU
                
            message_text = update.message.text.strip()
            
            # Enhanced input validation
            if not message_text or len(message_text.strip()) == 0:
                if update.message:
                    await update.message.reply_text("❌ Empty input. Please provide valid configuration values or send 'cancel' to abort.")
                return EDIT_VALUE
            
            if message_text.lower() == 'cancel':
                if update.message:
                    await update.message.reply_text("❌ Configuration edit cancelled.")
                await self.show_config_main_menu(update, context)
                return MAIN_MENU
            
            editing_type = context.user_data.get('editing_type') if context.user_data else None
            admin_user = update.effective_user
            
            if not admin_user:
                return MAIN_MENU
            
            # Enhanced security: input sanitization
            message_text = message_text.replace(';', '').replace('--', '').strip()
            
            # Parse input based on editing type with validation
            updates = {}
            parsing_errors = []
            
            if editing_type == "escrow_limits":
                values = [float(x.strip()) for x in message_text.split(',')]
                if len(values) >= 2:
                    updates = {
                        "min_escrow_amount_usd": values[0],
                        "max_escrow_amount_usd": values[1]
                    }
            
            elif editing_type == "cashout_limits":
                values = [float(x.strip()) for x in message_text.split(',')]
                if len(values) >= 3:
                    updates = {
                        "min_cashout_amount_usd": values[0],
                        "max_cashout_amount_usd": values[1],
                        "admin_approval_threshold_usd": values[2]
                    }
            
            elif editing_type == "anomaly_thresholds":
                values = [float(x.strip()) for x in message_text.split(',')]
                if len(values) >= 4:
                    updates = {
                        "low_anomaly_threshold": values[0],
                        "medium_anomaly_threshold": values[1],
                        "high_anomaly_threshold": values[2],
                        "critical_anomaly_threshold": values[3]
                    }
            
            # Add more parsing logic for other types...
            
            if updates:
                result = self.config_service.update_config(
                    admin_user_id=admin_user.id,
                    updates=updates,
                    reason=f"Manual update via admin interface: {editing_type}"
                )
                
                if update.message:
                    await update.message.reply_text(
                        f"✅ Configuration updated successfully!\n\n"
                        f"Updated fields: {', '.join(updates.keys())}"
                    )
            else:
                if update.message:
                    await update.message.reply_text(
                        "❌ Invalid input format. Please check the format and try again."
                    )
            
            # Return to appropriate menu
            await self.show_config_main_menu(update, context)
            return MAIN_MENU

        except Exception as e:
            logger.error(f"Error handling value input: {e}")
            if update.message:
                await update.message.reply_text("❌ Error processing configuration update")
            await self.show_config_main_menu(update, context)
            return MAIN_MENU


# NOTE: ConversationHandler removed - was unused and not registered in main.py
# Individual handlers can be registered directly if needed in the future