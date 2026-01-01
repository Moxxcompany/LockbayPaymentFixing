#!/usr/bin/env python3
"""
Gunicorn-Compatible Startup Script for LockBay Telegram Bot
Hybrid approach: Initialize bot in background thread, serve webhooks with gunicorn workers
"""
import os
import sys
import logging
import asyncio
import threading

# Setup environment variables before any imports
os.environ.setdefault("TZ", "UTC")
os.environ.setdefault("USE_WEBHOOK", "true")
os.environ.setdefault("WEBHOOK_HOST", "0.0.0.0")
os.environ.setdefault("WEBHOOK_PATH", "")
port = os.environ.get("PORT", "5000")
os.environ.setdefault("WEBHOOK_PORT", port)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Suppress bot token in logs (security)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram.request').setLevel(logging.WARNING)
logging.getLogger('telegram.ext').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

logger.info("🚀 Gunicorn startup: Environment configured")
logger.info(f"📍 Webhook port: {port}")

# Initialize bot in a background thread (runs in master process before workers fork)
bot_initialized = threading.Event()

def initialize_bot_async():
    """Initialize bot in background thread"""
    try:
        logger.info("🤖 Initializing Telegram bot in background...")
        
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Import and run bot initialization from main.py
        from main import run_webhook_optimized
        from utils.performance_monitor import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        # This will initialize bot, register handlers, and set it in webhook_server
        # But it won't start uvicorn (gunicorn handles that)
        loop.run_until_complete(run_webhook_optimized(monitor))
        
        bot_initialized.set()
        logger.info("✅ Bot initialization complete, webhook server ready")
        
        # Keep event loop running for background tasks
        loop.run_forever()
        
    except Exception as e:
        logger.error(f"❌ Bot initialization failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Start bot initialization in background thread
init_thread = threading.Thread(target=initialize_bot_async, daemon=True)
init_thread.start()

# Wait for bot to be ready (with timeout)
logger.info("⏳ Waiting for bot initialization...")
if not bot_initialized.wait(timeout=60):
    logger.error("❌ Bot initialization timed out after 60 seconds")
    sys.exit(1)

logger.info("✅ Bot ready, proceeding with gunicorn worker startup")

# Import the app for gunicorn to serve
from webhook_server import app

# Gunicorn will import 'app' from this module
__all__ = ['app']

logger.info("✅ Gunicorn: FastAPI app loaded, ready to handle webhook requests")
