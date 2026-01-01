"""
Admin Retry Command Registry
Registers all admin retry-related bot commands with the application
"""

import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from handlers.admin_retry_commands import (
    admin_retry_queue_command,
    admin_force_retry_command, 
    admin_force_refund_command,
    admin_retry_stats_command,
    handle_admin_retry_queue,
    handle_admin_retry_queue_details,
    handle_admin_retry_stats,
    handle_admin_retry_force_process,
    handle_admin_retry_failed_items
)

logger = logging.getLogger(__name__)


class AdminRetryCommandRegistry:
    """Registry for all admin retry-related commands and callbacks"""
    
    @staticmethod
    def register_all_commands(application: Application) -> bool:
        """Register all admin retry commands with the application"""
        try:
            logger.info("🔄 ADMIN_RETRY_REGISTRY: Starting registration of admin retry commands...")
            
            # Register command handlers
            AdminRetryCommandRegistry.register_command_handlers(application)
            
            # Register callback handlers
            AdminRetryCommandRegistry.register_callback_handlers(application)
            
            logger.info("✅ ADMIN_RETRY_REGISTRY: All admin retry commands registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ ADMIN_RETRY_REGISTRY: Failed to register commands: {e}")
            return False
    
    @staticmethod
    def register_command_handlers(application: Application):
        """Register admin retry command handlers"""
        commands = [
            ("admin_retry_queue", admin_retry_queue_command),
            ("admin_force_retry", admin_force_retry_command),
            ("admin_force_refund", admin_force_refund_command),
            ("admin_retry_stats", admin_retry_stats_command),
        ]
        
        for command, handler in commands:
            application.add_handler(CommandHandler(command, handler))
            logger.info(f"✅ ADMIN_RETRY_REGISTRY: Registered command /{command}")
    
    @staticmethod
    def register_callback_handlers(application: Application):
        """Register admin retry callback query handlers"""
        callbacks = [
            ("^admin_retry_queue$", handle_admin_retry_queue),
            ("^admin_retry_queue_details$", handle_admin_retry_queue_details),
            ("^admin_retry_stats$", handle_admin_retry_stats),
            ("^admin_retry_force_process$", handle_admin_retry_force_process),
            ("^admin_retry_failed_items$", handle_admin_retry_failed_items),
        ]
        
        for pattern, handler in callbacks:
            application.add_handler(CallbackQueryHandler(handler, pattern=pattern))
            logger.debug(f"✅ ADMIN_RETRY_REGISTRY: Registered callback {pattern}")
        
        logger.info(f"✅ ADMIN_RETRY_REGISTRY: Registered {len(callbacks)} callback handlers")