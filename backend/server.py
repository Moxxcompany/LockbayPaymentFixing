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
            # Strip /api prefix so routes match
            request.scope["path"] = request.url.path[4:] or "/"
        return await call_next(request)

webhook_app.add_middleware(StripApiPrefixMiddleware)

from contextlib import asynccontextmanager
import asyncio

@asynccontextmanager
async def lifespan(application):
    """Initialize the Telegram bot using main.py's full run_webhook_optimized flow."""
    
    logger.info("Initializing Lockbay Telegram Bot...")
    
    try:
        from config import Config
        Config.log_environment_config()
        
        try:
            Config.validate_production_config()
        except Exception as e:
            logger.warning(f"Config validation warning: {e}")
        
        if not Config.BOT_TOKEN:
            logger.error("BOT_TOKEN not set! Bot will not start.")
        else:
            # Use the FULL run_webhook_optimized from main.py 
            # This registers ALL handlers correctly (commands, callbacks, text router, direct handlers, etc.)
            from main import run_webhook_optimized, start_background_systems
            from utils.startup_optimizer import StartupOptimizer
            
            StartupOptimizer.enable_lazy_imports()
            StartupOptimizer.optimize_startup_performance()
            
            # run_webhook_optimized creates the bot application and registers everything
            monitor = None
            try:
                from utils.background_operations import CriticalOperationsManager
                monitor = CriticalOperationsManager()
            except Exception:
                pass
            
            bot_application = await run_webhook_optimized(monitor)
            
            if bot_application:
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
                
                logger.info("Lockbay Bot fully initialized and ready!")
            else:
                logger.error("run_webhook_optimized returned None - bot not initialized")
    
    except Exception as e:
        logger.error(f"Bot initialization failed: {e}")
        import traceback
        traceback.print_exc()
    
    yield
    
    logger.info("Shutting down Lockbay Bot...")

# Override the webhook_app's lifespan with our initialization
webhook_app.router.lifespan_context = lifespan

# Export the app for uvicorn
app = webhook_app
