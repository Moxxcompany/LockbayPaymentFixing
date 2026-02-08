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

# Add middleware to strip /api prefix since Emergent ingress forwards /api/* with prefix intact
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

class StripApiPrefixMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        if request.url.path.startswith("/api"):
            request.scope["path"] = request.url.path[4:] or "/"
        return await call_next(request)

webhook_app.add_middleware(StripApiPrefixMiddleware)

from contextlib import asynccontextmanager
import asyncio

async def _init_bot():
    """
    Mirror the FULL initialization from main.py run_webhook_optimized()
    WITHOUT starting uvicorn (since supervisor already runs it).
    """
    from config import Config
    Config.log_environment_config()
    
    try:
        Config.validate_production_config()
    except Exception as e:
        logger.warning(f"Config validation warning: {e}")
    
    if not Config.BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return None

    # --- State Manager ---
    try:
        from services.state_manager import initialize_state_manager
        await initialize_state_manager()
    except Exception as e:
        logger.warning(f"State Manager init warning: {e}")

    # --- Background Email Queue ---
    try:
        from main_startup_integration import initialize_background_email_system
        await initialize_background_email_system()
    except Exception as e:
        logger.warning(f"Email queue init warning: {e}")

    # --- Database ---
    try:
        from database import test_connection, create_tables
        if not test_connection():
            raise ConnectionError("DB connection test failed")
        create_tables()
    except Exception as e:
        logger.error(f"DB init error: {e}")

    Config.validate_retry_system_configuration()
    Config.validate_manual_refunds_configuration()
    Config.validate_webhook_urls()

    # --- Create Telegram Application ---
    from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters
    from telegram.request import HTTPXRequest
    from utils.conversation_protection import create_blocking_aware_handler, create_blocking_aware_command_handler

    request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0, write_timeout=30.0, connection_pool_size=32)
    application = Application.builder().token(Config.BOT_TOKEN).request(request).build()

    # --- Register emergency handlers ---
    from main import register_emergency_handlers
    register_emergency_handlers(application)

    # --- Update interceptor ---
    from utils.update_interceptor import register_update_interceptor
    register_update_interceptor(application)

    # --- Critical infrastructure ---
    from utils.startup_optimizer import StartupOptimizer
    from utils.background_operations import CriticalOperationsManager
    StartupOptimizer.enable_lazy_imports()
    StartupOptimizer.optimize_startup_performance()
    await CriticalOperationsManager.setup_critical_infrastructure(application)

    # --- Register handlers (same as main.py run_webhook_optimized lines ~500-1060) ---
    from handlers.start import start_handler
    from handlers.commands import (
        menu_command, wallet_command, escrow_command, profile_command,
        help_command, orders_command, settings_command, support_command
    )
    from handlers.admin import admin_command, handle_broadcast_command

    # /start with deep linking
    blocked_start = create_blocking_aware_command_handler(start_handler)
    application.add_handler(CommandHandler("start", blocked_start), group=0)

    # /admin and /broadcast
    blocked_admin = create_blocking_aware_command_handler(admin_command)
    application.add_handler(CommandHandler("admin", blocked_admin), group=0)
    blocked_broadcast = create_blocking_aware_command_handler(handle_broadcast_command)
    application.add_handler(CommandHandler("broadcast", blocked_broadcast), group=0)

    # Menu commands
    for cmd, func in [
        ("menu", menu_command), ("wallet", wallet_command), ("escrow", escrow_command),
        ("profile", profile_command), ("help", help_command), ("orders", orders_command),
        ("settings", settings_command), ("support", support_command),
    ]:
        blocked = create_blocking_aware_command_handler(func)
        application.add_handler(CommandHandler(cmd, blocked), group=0)

    # --- ALL callback query handlers (from main.py critical_handlers list) ---
    from handlers.wallet_direct import (
        show_crypto_funding_options, start_add_funds, handle_bank_selection, handle_deposit_currency_selection,
        show_deposit_qr, handle_save_bank_account, handle_cancel_bank_save, handle_add_new_bank,
        show_saved_bank_accounts_management, show_saved_crypto_addresses_management,
        show_comprehensive_transaction_history, handle_back_to_main, handle_ngn_bank_account_input,
        handle_wallet_menu, handle_wallet_cashout, handle_auto_cashout_bank_selection,
        handle_auto_cashout_crypto_selection, handle_toggle_auto_cashout,
        handle_set_auto_cashout_bank, handle_set_auto_cashout_crypto,
        handle_confirm_unverified_cashout
    )
    from handlers.fincra_payment import FincraPaymentHandler
    from handlers.commands import show_account_settings, show_cashout_settings, show_notification_settings
    from handlers.start import show_help_from_onboarding_callback, handle_demo_exchange, handle_demo_escrow
    from handlers.missing_handlers import (
        handle_main_menu_callback, handle_my_escrows, handle_menu_escrows,
        handle_wal_history, handle_withdrawal_history, handle_exchange_crypto, handle_complete_trading,
        handle_quick_rating_access, handle_settings_verify_email, handle_start_email_verification
    )
    from handlers.ux_improvements import handle_contact_support
    from handlers.messages_hub import show_trades_messages_hub, handle_start_dispute, handle_dispute_trade
    from handlers.escrow import (
        start_secure_trade, handle_escrow_crypto_selection, handle_payment_method_selection,
        handle_release_funds, handle_cancel_release_funds, handle_confirm_release_funds, handle_mark_delivered
    )
    from handlers.referral import handle_invite_friends, handle_referral_stats, handle_referral_leaderboard
    from handlers.contact_management import ContactManagementHandler
    from handlers.admin import (
        handle_admin_main, handle_admin_analytics, handle_admin_disputes, handle_admin_reports,
        handle_admin_manual_ops, handle_admin_manual_cashouts, handle_admin_health
    )

    critical_handlers = [
        (show_crypto_funding_options, '^(crypto_funding_start|crypto_funding_start_direct|crypto_funding_options)$'),
        (FincraPaymentHandler.start_wallet_funding, '^fincra_start_payment$'),
        (handle_bank_selection, '^wallet_select_bank:.*$'),
        (handle_deposit_currency_selection, '^deposit_currency:'),
        (show_deposit_qr, '^show_deposit_qr$'),
        (handle_save_bank_account, '^save_bank_account$'),
        (handle_add_new_bank, '^add_new_bank$'),
        (profile_command, '^menu_profile$'),
        (show_account_settings, '^user_settings$'),
        (show_cashout_settings, '^cashout_settings$'),
        (show_comprehensive_transaction_history, '^wallet_history$'),
        (handle_wal_history, '^wal_history$'),
        (show_saved_bank_accounts_management, '^manage_bank_accounts$'),
        (show_saved_crypto_addresses_management, '^manage_crypto_addresses$'),
        (show_help_from_onboarding_callback, '^menu_help$'),
        (handle_main_menu_callback, '^main_menu$'),
        (handle_back_to_main, '^back_to_main$'),
        (show_trades_messages_hub, '^trades_messages_hub$'),
        (start_secure_trade, '^(start_secure_trade|create_escrow)$'),
        (handle_demo_exchange, '^demo_exchange$'),
        (handle_demo_escrow, '^demo_escrow$'),
        (handle_invite_friends, '^invite_friends$'),
        (handle_referral_stats, '^referral_stats$'),
        (handle_referral_leaderboard, '^referral_leaderboard$'),
        (handle_my_escrows, '^my_escrows$'),
        (handle_menu_escrows, '^menu_escrows$'),
        (handle_withdrawal_history, '^withdrawal_history$'),
        (handle_wallet_menu, '^menu_wallet$'),
        (handle_deposit_currency_selection, '^wallet_deposit$'),
        (handle_wallet_cashout, '^wallet_withdraw$'),
        (ContactManagementHandler().contact_management_menu, '^contact_menu$'),
        (handle_admin_main, '^admin_main$'),
        (handle_admin_analytics, '^admin_analytics$'),
        (handle_admin_disputes, '^admin_disputes$'),
        (handle_admin_reports, '^admin_reports$'),
        (handle_admin_manual_ops, '^admin_manual_ops$'),
        (handle_admin_manual_cashouts, '^admin_manual_cashouts$'),
        (handle_admin_health, '^admin_health$'),
        (handle_payment_method_selection, '^payment_.*$'),
        (handle_payment_method_selection, '^wallet_insufficient$'),
        # HIGH-FREQUENCY MISSING PATTERNS
        (start_add_funds, '^wallet_add_funds$'),
        (start_secure_trade, '^menu_create$'),
        (show_cashout_settings, '^auto_cashout_settings$'),
        (handle_toggle_auto_cashout, '^toggle_auto_cashout$'),
        (handle_auto_cashout_bank_selection, '^auto_cashout_set_bank$'),
        (handle_auto_cashout_crypto_selection, '^auto_cashout_set_crypto$'),
        (handle_set_auto_cashout_bank, '^set_auto_bank:.*$'),
        (handle_set_auto_cashout_crypto, '^set_auto_crypto:.*$'),
        (handle_wallet_menu, '^wallet_menu$'),
        (handle_release_funds, '^release_funds_.*$'),
        (handle_cancel_release_funds, '^cancel_release_.*$'),
        (handle_confirm_release_funds, '^confirm_release_.*$'),
        (handle_mark_delivered, '^mark_delivered_.*$'),
        (handle_start_dispute, '^start_dispute$'),
        (handle_dispute_trade, '^dispute_trade:.*$'),
        (handle_exchange_crypto, '^exchange_crypto$'),
        (handle_complete_trading, '^(complete_trading|complete_escrow|onboarding_complete|first_trade)$'),
        (handle_contact_support, '^contact_support$'),
        (handle_quick_rating_access, '^quick_rate:.*$'),
        (handle_settings_verify_email, '^settings_verify_email$'),
        (handle_start_email_verification, '^start_email_verification$'),
        (show_notification_settings, '^notification_settings$'),
        (handle_confirm_unverified_cashout, '^confirm_unverified_cashout$'),
    ]

    for handler_func, pattern in critical_handlers:
        blocked = create_blocking_aware_handler(handler_func)
        application.add_handler(CallbackQueryHandler(blocked, pattern=pattern), group=0)
    logger.info(f"Registered {len(critical_handlers)} callback handlers")

    # --- Unified callback dispatcher (catch-all for remaining callbacks) ---
    from utils.callback_dispatcher import initialize_callback_system
    unified_callback_handler = initialize_callback_system()
    application.add_handler(unified_callback_handler, group=0)

    # --- Text router ---
    from handlers.text_router import create_unified_text_handler
    unified_text_handler = create_unified_text_handler()
    application.add_handler(unified_text_handler, group=0)

    # --- Direct handlers (group=-1, higher priority) ---
    try:
        from handlers.escrow_direct import DIRECT_ESCROW_HANDLERS
        for handler in DIRECT_ESCROW_HANDLERS:
            application.add_handler(handler, group=-1)

        from handlers.user_rating_direct import DIRECT_RATING_HANDLERS
        for handler in DIRECT_RATING_HANDLERS:
            application.add_handler(handler, group=-1)

        from handlers.contact_management_direct import DIRECT_CONTACT_HANDLERS
        for handler in DIRECT_CONTACT_HANDLERS:
            application.add_handler(handler, group=-1)

        from handlers.messages_hub_direct import DIRECT_MESSAGES_HANDLERS
        for handler in DIRECT_MESSAGES_HANDLERS:
            application.add_handler(handler, group=-1)

        from handlers.onboarding_router import register_onboarding_handlers
        register_onboarding_handlers(application)

        logger.info("All direct handlers registered")
    except Exception as e:
        logger.error(f"Direct handler registration error: {e}")

    # --- Transaction history handlers ---
    from main import register_handlers_directly
    await register_handlers_directly(application)

    # --- Initialize and start bot ---
    await application.initialize()
    await application.start()
    logger.info("Bot application initialized and started")

    return application


@asynccontextmanager
async def lifespan(fastapi_app):
    """Initialize the Telegram bot on startup."""
    
    logger.info("Initializing Lockbay Telegram Bot...")
    
    try:
        bot_application = await _init_bot()
        
        if bot_application:
            from config import Config
            
            # Set webhook with Telegram
            webhook_url = Config.TELEGRAM_WEBHOOK_URL or Config.WEBHOOK_URL
            if webhook_url:
                try:
                    result = await bot_application.bot.set_webhook(
                        url=webhook_url,
                        allowed_updates=["message", "callback_query", "my_chat_member"],
                        drop_pending_updates=True
                    )
                    logger.info(f"Webhook registered: {webhook_url}" if result else "Webhook registration failed")
                except Exception as e:
                    logger.error(f"Webhook registration error: {e}")
            
            # Set bot application reference in webhook_server
            from webhook_server import set_bot_application
            await set_bot_application(bot_application)
            
            # Start background systems
            from main import start_background_systems
            asyncio.create_task(start_background_systems())
            
            logger.info("Lockbay Bot fully initialized and ready!")
        else:
            logger.error("Bot initialization returned None")
    
    except Exception as e:
        logger.error(f"Bot initialization failed: {e}")
        import traceback
        traceback.print_exc()
    
    yield
    
    logger.info("Shutting down Lockbay Bot...")

# Override the webhook_app's lifespan
webhook_app.router.lifespan_context = lifespan

# Export the app for uvicorn
app = webhook_app
