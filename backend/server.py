"""
Backend server entry point for Emergent platform.
Bootstraps the Lockbay Telegram Bot webhook server.
"""
import os
import sys
import logging

# Add the parent directory to path so we can import from /app root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment from root .env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Override WEBHOOK_PORT to match Emergent's expected port
os.environ["WEBHOOK_PORT"] = "8001"
os.environ["USE_WEBHOOK"] = "true"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram.request').setLevel(logging.WARNING)
logging.getLogger('telegram.ext').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info("Starting Lockbay Bot via Emergent backend server...")

# Change working directory to app root for correct relative paths
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the FastAPI app from webhook_server
from webhook_server import app as webhook_app

# Create a wrapper app that will initialize the bot on startup
from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio

_bot_initialized = False

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Initialize the Telegram bot and all handlers on startup."""
    global _bot_initialized
    
    logger.info("Initializing Lockbay Telegram Bot...")
    
    try:
        # Run the bot initialization (same as production_start.py + main.py)
        from config import Config
        Config.log_environment_config()
        
        # Validate configuration
        try:
            Config.validate_production_config()
        except Exception as e:
            logger.warning(f"Config validation warning: {e}")
        
        # Initialize the bot application
        from main import (
            setup_critical_only, 
            register_handlers_directly, 
            register_emergency_handlers,
            run_commands_migration,
            start_background_systems
        )
        from telegram.ext import Application
        from telegram.request import HTTPXRequest
        
        if not Config.BOT_TOKEN:
            logger.error("BOT_TOKEN not set! Bot will not start.")
        else:
            # Create telegram application
            request = HTTPXRequest(
                connect_timeout=30.0,
                read_timeout=30.0,
                write_timeout=30.0,
                connection_pool_size=32
            )
            bot_application = Application.builder().token(Config.BOT_TOKEN).request(request).build()
            
            # Register handlers
            register_emergency_handlers(bot_application)
            logger.info("Emergency handlers registered")
            
            # Register update interceptor
            from utils.update_interceptor import register_update_interceptor
            register_update_interceptor(bot_application)
            
            # Setup critical infrastructure
            from utils.startup_optimizer import StartupOptimizer
            from utils.background_operations import CriticalOperationsManager
            
            StartupOptimizer.enable_lazy_imports()
            StartupOptimizer.optimize_startup_performance()
            
            await CriticalOperationsManager.setup_critical_infrastructure(bot_application)
            await register_handlers_directly(bot_application)
            
            # Register all the critical handlers from main.py's run_webhook_optimized
            # (abbreviated - importing key handler registrations)
            from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters
            from utils.conversation_protection import create_blocking_aware_handler, create_blocking_aware_command_handler
            
            # Register /start and /cancel commands
            from handlers.start import start_handler
            from handlers.commands import (
                menu_command, wallet_command, escrow_command, profile_command, 
                help_command, orders_command, settings_command, support_command
            )
            from handlers.admin import admin_command, handle_broadcast_command
            
            for cmd, func in [
                ("start", start_handler), ("admin", admin_command),
                ("menu", menu_command), ("wallet", wallet_command),
                ("escrow", escrow_command), ("profile", profile_command),
                ("help", help_command), ("orders", orders_command),
                ("settings", settings_command), ("support", support_command),
            ]:
                blocked = create_blocking_aware_command_handler(func)
                bot_application.add_handler(CommandHandler(cmd, blocked), group=0)
            
            # Register unified callback dispatcher
            from utils.callback_dispatcher import initialize_callback_system
            unified_callback_handler = initialize_callback_system()
            bot_application.add_handler(unified_callback_handler, group=0)
            
            # Register text router
            from handlers.text_router import create_unified_text_handler
            unified_text_handler = create_unified_text_handler()
            bot_application.add_handler(unified_text_handler, group=0)
            
            # Register direct handlers
            try:
                from handlers.escrow_direct import DIRECT_ESCROW_HANDLERS
                for handler in DIRECT_ESCROW_HANDLERS:
                    bot_application.add_handler(handler, group=-1)
                    
                from handlers.user_rating_direct import DIRECT_RATING_HANDLERS
                for handler in DIRECT_RATING_HANDLERS:
                    bot_application.add_handler(handler, group=-1)
                    
                from handlers.contact_management_direct import DIRECT_CONTACT_HANDLERS
                for handler in DIRECT_CONTACT_HANDLERS:
                    bot_application.add_handler(handler, group=-1)
                
                from handlers.messages_hub_direct import DIRECT_MESSAGES_HANDLERS
                for handler in DIRECT_MESSAGES_HANDLERS:
                    bot_application.add_handler(handler, group=-1)
                
                from handlers.onboarding_router import register_onboarding_handlers
                register_onboarding_handlers(bot_application)
                
                logger.info("All direct handlers registered")
            except Exception as e:
                logger.error(f"Direct handler registration error: {e}")
            
            # Initialize and start bot application
            await bot_application.initialize()
            await bot_application.start()
            logger.info("Bot application initialized and started")
            
            # Set webhook with Telegram
            webhook_url = Config.TELEGRAM_WEBHOOK_URL or Config.WEBHOOK_URL
            if webhook_url:
                try:
                    result = await bot_application.bot.set_webhook(
                        url=webhook_url,
                        allowed_updates=["message", "callback_query", "my_chat_member"],
                        drop_pending_updates=True
                    )
                    if result:
                        logger.info(f"Webhook registered: {webhook_url}")
                    else:
                        logger.error("Webhook registration failed")
                except Exception as e:
                    logger.error(f"Webhook registration error: {e}")
            
            # Set bot application reference in webhook_server
            from webhook_server import set_bot_application
            await set_bot_application(bot_application)
            
            # Start background systems
            asyncio.create_task(start_background_systems())
            
            _bot_initialized = True
            logger.info("Lockbay Bot fully initialized and ready!")
    
    except Exception as e:
        logger.error(f"Bot initialization failed: {e}")
        import traceback
        traceback.print_exc()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Lockbay Bot...")

# Override the webhook_app's lifespan with our initialization
webhook_app.router.lifespan_context = lifespan

# Export the app for uvicorn
app = webhook_app
