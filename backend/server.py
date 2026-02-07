"""
Backend server wrapper for LockBay Telegram Escrow Bot.
Initializes the Telegram bot and exposes the webhook FastAPI app on port 8001.
"""
import sys
import os

# Add the app root to Python path so all imports work
sys.path.insert(0, '/app')
os.chdir('/app')

# Load environment variables from /app/.env
from dotenv import load_dotenv
load_dotenv('/app/.env', override=True)

import logging
import asyncio
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
# Suppress noisy loggers
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram.request').setLevel(logging.WARNING)
logging.getLogger('telegram.ext').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Global bot application reference
_bot_application = None
_startup_complete = False


async def initialize_bot():
    """Initialize the Telegram bot application with all handlers."""
    global _bot_application, _startup_complete

    from config import Config
    Config.log_environment_config()

    from telegram.ext import Application
    from telegram.request import HTTPXRequest

    if not Config.BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set")

    logger.info(f"Initializing bot with token ending ...{Config.BOT_TOKEN[-6:]}")

    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        connection_pool_size=32,
    )
    application = Application.builder().token(Config.BOT_TOKEN).request(request).build()

    # Register emergency handlers
    from main import register_emergency_handlers
    register_emergency_handlers(application)

    # Register direct handlers
    from main import register_handlers_directly
    await register_handlers_directly(application)

    # Register critical handlers from main.py (simplified subset)
    from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters
    from utils.conversation_protection import create_blocking_aware_handler, create_blocking_aware_command_handler

    # /start command
    from handlers.start import start_handler
    application.add_handler(CommandHandler("start", create_blocking_aware_command_handler(start_handler)), group=0)

    # /cancel command
    async def emergency_cancel_command(update, context):
        from utils.conversation_cleanup import clear_user_conversation_state
        user_id = update.effective_user.id
        await clear_user_conversation_state(user_id=user_id, context=context, trigger="cancel_command")
        await update.message.reply_text("Session reset. Use /start to return to the main menu.")
    application.add_handler(CommandHandler("cancel", create_blocking_aware_command_handler(emergency_cancel_command)), group=0)

    # /admin command
    from handlers.admin import admin_command
    application.add_handler(CommandHandler("admin", create_blocking_aware_command_handler(admin_command)), group=0)

    # Menu commands
    from handlers.commands import (
        menu_command, wallet_command, escrow_command, profile_command,
        help_command, orders_command, settings_command, support_command
    )
    for cmd, func in [
        ("menu", menu_command), ("wallet", wallet_command), ("escrow", escrow_command),
        ("profile", profile_command), ("help", help_command), ("orders", orders_command),
        ("settings", settings_command), ("support", support_command),
    ]:
        application.add_handler(CommandHandler(cmd, create_blocking_aware_command_handler(func)), group=0)

    # Unified callback dispatcher
    from utils.callback_dispatcher import initialize_callback_system
    application.add_handler(initialize_callback_system(), group=0)

    # Hamburger menu
    from handlers.menu import show_hamburger_menu, show_partner_program
    application.add_handler(CallbackQueryHandler(create_blocking_aware_handler(show_hamburger_menu), pattern='^hamburger_menu$'), group=1)
    application.add_handler(CallbackQueryHandler(create_blocking_aware_handler(show_partner_program), pattern='^partner_program$'), group=1)

    # Critical callback handlers
    from handlers.wallet_direct import (
        show_crypto_funding_options, start_add_funds, handle_bank_selection,
        handle_deposit_currency_selection, handle_wallet_menu, handle_wallet_cashout,
        handle_back_to_main, handle_ngn_bank_account_input, handle_confirm_unverified_cashout,
        show_comprehensive_transaction_history, show_saved_bank_accounts_management,
        show_saved_crypto_addresses_management,
    )
    from handlers.escrow import (
        start_secure_trade, handle_payment_method_selection, handle_release_funds,
        handle_cancel_release_funds, handle_confirm_release_funds, handle_mark_delivered,
        handle_make_payment,
    )
    from handlers.start import show_help_from_onboarding_callback, handle_demo_exchange, handle_demo_escrow, navigate_to_dashboard
    from handlers.missing_handlers import (
        handle_main_menu_callback, handle_my_escrows, handle_menu_escrows,
        handle_wal_history, handle_withdrawal_history, handle_exchange_crypto,
        handle_complete_trading, handle_quick_rating_access,
        handle_settings_verify_email, handle_start_email_verification,
    )
    from handlers.messages_hub import show_trades_messages_hub, handle_start_dispute, handle_dispute_trade
    from handlers.referral import handle_invite_friends, handle_referral_stats, handle_referral_leaderboard
    from handlers.contact_management import ContactManagementHandler
    from handlers.fincra_payment import FincraPaymentHandler
    from handlers.exchange_handler import ExchangeHandler
    from handlers.admin import (
        handle_admin_main, handle_admin_analytics, handle_admin_disputes,
        handle_admin_reports, handle_admin_manual_ops, handle_admin_manual_cashouts, handle_admin_health,
    )
    from handlers.commands import show_account_settings, show_cashout_settings

    critical_cb = [
        (show_crypto_funding_options, '^(crypto_funding_start|crypto_funding_start_direct|crypto_funding_options)$'),
        (FincraPaymentHandler.start_wallet_funding, '^fincra_start_payment$'),
        (handle_bank_selection, '^wallet_select_bank:.*$'),
        (handle_deposit_currency_selection, '^deposit_currency:'),
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
        (start_add_funds, '^wallet_add_funds$'),
        (start_secure_trade, '^menu_create$'),
        (handle_release_funds, '^release_funds_.*$'),
        (handle_cancel_release_funds, '^cancel_release_.*$'),
        (handle_confirm_release_funds, '^confirm_release_.*$'),
        (handle_mark_delivered, '^mark_delivered_.*$'),
        (handle_start_dispute, '^start_dispute$'),
        (handle_dispute_trade, '^dispute_trade:.*$'),
        (handle_exchange_crypto, '^exchange_crypto$'),
        (handle_complete_trading, '^complete_trading$'),
        (handle_quick_rating_access, '^quick_rating_access$'),
        (handle_settings_verify_email, '^settings_verify_email$'),
        (handle_start_email_verification, '^start_email_verification$'),
        (handle_confirm_unverified_cashout, '^confirm_unverified_cashout_.*$'),
        (handle_wallet_menu, '^wallet_menu$'),
        (show_cashout_settings, '^auto_cashout_settings$'),
    ]

    # Payment handlers at highest priority
    application.add_handler(CallbackQueryHandler(create_blocking_aware_handler(handle_make_payment), pattern='^make_payment_'), group=-10)
    application.add_handler(CallbackQueryHandler(create_blocking_aware_handler(handle_make_payment), pattern='^pay_escrow_'), group=-10)
    application.add_handler(CallbackQueryHandler(create_blocking_aware_handler(handle_make_payment), pattern='^pay_escrow:'), group=-10)

    for func, pattern in critical_cb:
        try:
            application.add_handler(CallbackQueryHandler(create_blocking_aware_handler(func), pattern=pattern), group=0)
        except Exception as e:
            logger.error(f"Failed to register {func.__name__}: {e}")

    # Global continue_to_dashboard
    async def global_continue_to_dashboard(update, context):
        return await navigate_to_dashboard(update, context, source="quick_guide")
    application.add_handler(CallbackQueryHandler(create_blocking_aware_handler(global_continue_to_dashboard), pattern='^continue_to_dashboard$'), group=0)

    # Direct handler sets
    try:
        from handlers.escrow_direct import DIRECT_ESCROW_HANDLERS
        for h in DIRECT_ESCROW_HANDLERS:
            application.add_handler(h, group=-1)
        from handlers.user_rating_direct import DIRECT_RATING_HANDLERS
        for h in DIRECT_RATING_HANDLERS:
            application.add_handler(h, group=-1)
        from handlers.contact_management_direct import DIRECT_CONTACT_HANDLERS
        for h in DIRECT_CONTACT_HANDLERS:
            application.add_handler(h, group=-1)
        from handlers.admin_cashout_direct import DIRECT_ADMIN_CASHOUT_HANDLERS
        for h in DIRECT_ADMIN_CASHOUT_HANDLERS:
            application.add_handler(h, group=-1)
        from handlers.admin_transactions_direct import DIRECT_ADMIN_TRANSACTION_HANDLERS
        for h in DIRECT_ADMIN_TRANSACTION_HANDLERS:
            application.add_handler(h, group=-1)
        from handlers.admin_broadcast_direct import DIRECT_ADMIN_BROADCAST_HANDLERS
        for h in DIRECT_ADMIN_BROADCAST_HANDLERS:
            application.add_handler(h, group=1)
        from handlers.admin_rating_direct import DIRECT_ADMIN_RATING_HANDLERS
        for h in DIRECT_ADMIN_RATING_HANDLERS:
            application.add_handler(h, group=-1)
        from handlers.seller_profile import SELLER_PROFILE_HANDLERS
        for h in SELLER_PROFILE_HANDLERS:
            application.add_handler(h, group=-1)
        from handlers.rating_ui_enhancements import RATING_UI_HANDLERS
        for h in RATING_UI_HANDLERS:
            application.add_handler(h, group=-1)
        from handlers.admin_comprehensive_config_direct import DIRECT_ADMIN_CONFIG_HANDLERS
        for h in DIRECT_ADMIN_CONFIG_HANDLERS:
            application.add_handler(h, group=-1)
        from handlers.admin_maintenance import register_maintenance_handlers
        register_maintenance_handlers(application)
        from handlers.ux_improvements import UX_IMPROVEMENT_HANDLERS
        for h in UX_IMPROVEMENT_HANDLERS:
            application.add_handler(h, group=-1)
        from handlers.dispute_chat_direct import DIRECT_DISPUTE_HANDLERS
        for h in DIRECT_DISPUTE_HANDLERS:
            application.add_handler(h, group=-1)
        from handlers.messages_hub_direct import DIRECT_MESSAGES_HANDLERS
        for h in DIRECT_MESSAGES_HANDLERS:
            application.add_handler(h, group=-1)
        from handlers.multi_dispute_manager_direct import DIRECT_MULTI_DISPUTE_HANDLERS
        for h in DIRECT_MULTI_DISPUTE_HANDLERS:
            application.add_handler(h, group=-1)
        from handlers.session_ui_direct import DIRECT_SESSION_UI_HANDLERS
        for h in DIRECT_SESSION_UI_HANDLERS:
            application.add_handler(h, group=-1)
        from handlers.fincra_payment import register_fincra_handlers
        register_fincra_handlers(application)
        from handlers.onboarding_router import register_onboarding_handlers
        register_onboarding_handlers(application)
        logger.info("All direct handler sets registered")
    except Exception as e:
        logger.error(f"Direct handler registration error: {e}")

    # Unified text router
    from handlers.text_router import create_unified_text_handler
    application.add_handler(create_unified_text_handler(), group=0)

    # Support chat
    from handlers.support_chat import create_support_conversation_handler, view_support_tickets, open_support_chat
    application.add_handler(create_support_conversation_handler(), group=1)
    application.add_handler(CallbackQueryHandler(view_support_tickets, pattern='^view_support_tickets$'), group=0)
    application.add_handler(CallbackQueryHandler(open_support_chat, pattern='^support_chat_open:'), group=0)

    # Rating conversation
    from handlers.user_rating import create_rating_conversation_handler
    application.add_handler(create_rating_conversation_handler(), group=1)

    # Exchange handlers
    application.add_handler(CallbackQueryHandler(ExchangeHandler.start_exchange, pattern='^start_exchange$'), group=0)

    # Bank input handler
    application.add_handler(
        MessageHandler(filters.Regex(r"^\d{10}$") & ~filters.COMMAND, create_blocking_aware_handler(handle_ngn_bank_account_input)),
        group=0
    )

    # Initialize application
    import random
    from telegram.error import TimedOut
    for attempt in range(1, 4):
        try:
            logger.info(f"Bot init attempt {attempt}/3...")
            await application.initialize()
            logger.info("Bot initialized successfully")
            break
        except (TimedOut, Exception) as e:
            if attempt == 3:
                raise
            delay = 2 * (2 ** (attempt - 1)) + random.uniform(0, 1)
            logger.warning(f"Init attempt {attempt} failed: {e}, retrying in {delay:.1f}s")
            await asyncio.sleep(delay)

    await application.start()
    logger.info("Bot application started")

    _bot_application = application
    _startup_complete = True
    return application


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Initialize bot and webhook systems on startup."""
    global _bot_application, _startup_complete

    logger.info("=== LockBay Bot Server Starting ===")

    # Initialize database
    try:
        from database import test_connection, create_tables
        if test_connection():
            create_tables()
            logger.info("Database initialized")
        else:
            logger.error("Database connection failed")
    except Exception as e:
        logger.error(f"Database init error: {e}")

    # Initialize state manager
    try:
        from services.state_manager import initialize_state_manager
        await initialize_state_manager()
    except Exception as e:
        logger.error(f"State manager init error: {e}")

    # Initialize bot
    try:
        application = await initialize_bot()
        _bot_application = application

        # Set webhook with Telegram
        from config import Config
        webhook_url = Config.WEBHOOK_URL
        if webhook_url:
            result = await application.bot.set_webhook(
                url=webhook_url,
                allowed_updates=["message", "callback_query", "my_chat_member"],
                drop_pending_updates=True,
            )
            if result:
                logger.info(f"Webhook registered: {webhook_url}")
                info = await application.bot.get_webhook_info()
                logger.info(f"Webhook info: pending={info.pending_update_count}, url={info.url}")
            else:
                logger.error("Webhook registration failed")
        else:
            logger.error("WEBHOOK_URL not set!")

        # Initialize bot commands menu
        try:
            from utils.bot_commands import initialize_bot_commands
            await initialize_bot_commands(application)
        except Exception as e:
            logger.error(f"Bot commands setup error: {e}")

    except Exception as e:
        logger.error(f"Bot initialization failed: {e}")
        import traceback
        traceback.print_exc()

    # Start background systems
    try:
        from services.webhook_startup_service import webhook_startup_service
        await webhook_startup_service.initialize_webhook_system()
    except Exception as e:
        logger.error(f"Webhook system init error: {e}")

    try:
        from services.background_email_queue import initialize_email_queue
        await initialize_email_queue()
    except Exception as e:
        logger.error(f"Email queue init error: {e}")

    logger.info("=== LockBay Bot Server Ready ===")

    yield

    # Shutdown
    logger.info("Shutting down...")
    if _bot_application:
        try:
            await _bot_application.stop()
            await _bot_application.shutdown()
        except Exception as e:
            logger.error(f"Shutdown error: {e}")


from fastapi import APIRouter

# Create the FastAPI app
app = FastAPI(
    title="LockBay Telegram Bot",
    lifespan=lifespan,
)

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="/app/static"), name="static")
except Exception:
    pass

# Templates
try:
    templates = Jinja2Templates(directory="/app/templates")
except Exception:
    templates = None

# All routes go under /api prefix to match Kubernetes ingress routing
api = APIRouter(prefix="/api")


@api.get("/health")
async def health():
    return {
        "status": "healthy",
        "bot_ready": _startup_complete,
        "timestamp": time.time(),
    }


@api.get("/")
async def root():
    return {"status": "LockBay Bot Server", "ready": _startup_complete}


@api.post("/webhook")
async def webhook(request: Request):
    """Handle Telegram webhook updates."""
    import orjson
    from telegram import Update

    if not _bot_application or not _startup_complete:
        return JSONResponse({"error": "Bot not initialized"}, status_code=503)

    try:
        body = await request.body()
        if not body:
            return JSONResponse({"error": "Empty body"}, status_code=400)

        data = orjson.loads(body)
        if not isinstance(data, dict) or "update_id" not in data:
            return JSONResponse({"error": "Invalid data"}, status_code=400)

        update = Update.de_json(data, _bot_application.bot)
        if not update:
            return JSONResponse({"error": "Invalid update"}, status_code=400)

        # Process asynchronously
        msg_type = "callback_query" if update.callback_query else "message" if update.message else "other"
        msg_text = ""
        if update.message and update.message.text:
            msg_text = update.message.text[:30]
        elif update.callback_query and update.callback_query.data:
            msg_text = update.callback_query.data[:30]
        logger.info(f"📨 WEBHOOK_UPDATE: type={msg_type}, text='{msg_text}', user={update.effective_user.id if update.effective_user else 'unknown'}")
        asyncio.create_task(_bot_application.process_update(update))

        return JSONResponse({"ok": True})

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# DynoPay webhook endpoints
@api.post("/webhook/dynopay/escrow")
async def dynopay_escrow_webhook(request: Request):
    try:
        from handlers.dynopay_webhook_simplified import handle_dynopay_escrow_webhook
        return await handle_dynopay_escrow_webhook(request)
    except Exception as e:
        logger.error(f"DynoPay escrow webhook error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@api.post("/webhook/dynopay/wallet")
async def dynopay_wallet_webhook(request: Request):
    try:
        from handlers.dynopay_webhook_simplified import handle_dynopay_wallet_webhook
        return await handle_dynopay_wallet_webhook(request)
    except Exception as e:
        logger.error(f"DynoPay wallet webhook error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@api.post("/webhook/dynopay/exchange")
async def dynopay_exchange_webhook(request: Request):
    try:
        from handlers.dynopay_webhook_simplified import handle_dynopay_exchange_webhook
        return await handle_dynopay_exchange_webhook(request)
    except Exception as e:
        logger.error(f"DynoPay exchange webhook error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# Fincra webhook
@api.post("/webhook/fincra")
async def fincra_webhook(request: Request):
    try:
        from handlers.fincra_webhook_simplified import handle_fincra_webhook
        return await handle_fincra_webhook(request)
    except Exception as e:
        logger.error(f"Fincra webhook error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# BlockBee webhook
@api.post("/webhook/blockbee/{coin}")
async def blockbee_webhook(coin: str, request: Request):
    try:
        from handlers.blockbee_webhook_new import handle_blockbee_callback
        return await handle_blockbee_callback(coin, request)
    except Exception as e:
        logger.error(f"BlockBee webhook error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# Twilio webhook
@api.post("/webhook/twilio/status")
async def twilio_status_webhook(request: Request):
    try:
        from routes.twilio_webhook import handle_twilio_status_callback
        return await handle_twilio_status_callback(request)
    except Exception as e:
        logger.error(f"Twilio webhook error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# Public profile page
@api.get("/u/{profile_slug}")
async def public_profile(profile_slug: str, request: Request):
    try:
        from services.public_profile_service import PublicProfileService
        profile_data = await PublicProfileService.get_public_profile(profile_slug)
        if not profile_data:
            return JSONResponse({"error": "Profile not found"}, status_code=404)
        if templates:
            return templates.TemplateResponse("public_profile.html", {"request": request, **profile_data})
        return JSONResponse(profile_data)
    except Exception as e:
        logger.error(f"Profile error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# Warmup endpoint
@api.get("/warmup")
async def warmup():
    return {"status": "warm", "bot_ready": _startup_complete}

# Also add non-prefixed health for internal checks
@app.get("/health")
async def internal_health():
    return {"status": "healthy", "bot_ready": _startup_complete}

# Include the API router
app.include_router(api)
