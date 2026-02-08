#!/usr/bin/env python3
"""
Production-Ready Telegram Bot Startup Script
With singleton process management and graceful shutdown
"""

import os
import sys
import time
import logging

# Force unbuffered output so Railway/Docker logs appear immediately
os.environ["PYTHONUNBUFFERED"] = "1"
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Immediate startup signal for Railway deploy logs
print("🚀 LockBay production_start.py launching...", flush=True)

# Production startup - logs appear after app initialization
logger = logging.getLogger(__name__)

def setup_environment():
    """Setup production environment variables"""
    # Set timezone to UTC to prevent tzlocal warning
    os.environ.setdefault("TZ", "UTC")
    
    os.environ.setdefault("USE_WEBHOOK", "true")
    os.environ.setdefault("WEBHOOK_HOST", "0.0.0.0")
    os.environ.setdefault("WEBHOOK_PATH", "")
    
    # Auto-detect Railway or other hosting environment
    port = os.environ.get("PORT", "5000")
    os.environ.setdefault("WEBHOOK_PORT", port)
    
    # Check for production environment indicators (for logging purposes)
    railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    is_deployment = os.environ.get("REPLIT_DEPLOYMENT") == "1"
    environment = os.environ.get("ENVIRONMENT", "").lower()
    
    # Determine if we're in production (for logging purposes only)
    # Config.py handles all webhook URL logic
    is_production = (
        railway_domain or 
        is_deployment or 
        environment == "production"
    )
    
    if is_production:
        logger.info("🚀 Production mode detected - Config.py will handle webhook URL")
        logger.info("✅ Environment configured for production")
    else:
        logger.info("🧪 Development mode detected - Config.py will handle webhook URL")
        logger.info("✅ Environment configured for development")
    
    return is_production

def setup_logging():
    """Setup detailed logging for bot activities with security redaction"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Enable detailed logging for bot components
    logging.getLogger('telegram').setLevel(logging.INFO)
    logging.getLogger('handlers').setLevel(logging.INFO)
    logging.getLogger('services').setLevel(logging.INFO)
    logging.getLogger('utils').setLevel(logging.INFO)
    
    # SECURITY FIX: Prevent bot token exposure in logs
    # Set httpx and telegram HTTP request logging to WARNING to avoid logging full URLs with tokens
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram.request').setLevel(logging.WARNING)
    logging.getLogger('telegram.ext').setLevel(logging.WARNING)
    
    # Note: Using print here because logger isn't fully configured yet
    logger.info("✅ Detailed logging enabled for real-time bot activities")
    logger.info("🔒 Security: Bot token logging suppressed for httpx and telegram requests")


def validate_webhook_secrets():
    """Validate required webhook secrets exist at application startup"""
    logger = logging.getLogger(__name__)
    
    required_secrets = [
        ("FINCRA_WEBHOOK_ENCRYPTION_KEY", "Fincra"),
        ("DYNOPAY_WEBHOOK_SECRET", "DynoPay"),
    ]
    
    missing = []
    for secret_name, provider in required_secrets:
        if not os.getenv(secret_name):
            if os.getenv("BYPASS_WEBHOOK_VALIDATION") == "true":
                logger.warning(f"⚠️ BYPASS: Missing {provider} secret ({secret_name}), but continuing due to BYPASS_WEBHOOK_VALIDATION=true")
                continue
            missing.append(f"{provider} ({secret_name})")
    
    if missing:
        error_msg = f"❌ STARTUP ERROR: Missing webhook secrets: {', '.join(missing)}"
        logger.critical(error_msg)
        sys.exit(1)
    
    success_msg = "✅ All webhook secrets configured"
    logger.info(success_msg)

def main():
    """Production startup sequence with singleton management"""
    # Setup logging first for detailed activity monitoring
    setup_logging()
    
    logger.info(f"⏰ Startup time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Validate webhook secrets before starting - fail fast if missing
    validate_webhook_secrets()
    
    # Setup environment and detect mode
    is_production = setup_environment()
    
    if is_production:
        logger.info("🚀 Starting Telegram Bot - Production Mode")
    else:
        logger.info("🧪 Starting Telegram Bot - Development Mode")
    
    # Run comprehensive configuration validation
    try:
        from config import Config
        
        # Log environment configuration (includes database source)
        logger.info("🔧 Logging environment configuration...")
        Config.log_environment_config()
        
        logger.info("🔍 Running production configuration validation...")
        validation_result = Config.validate_production_config()
        
        # Exit if critical issues found in production
        if validation_result['issues'] and is_production:
            logger.critical("=" * 80)
            logger.critical("🚨 FATAL: Cannot start bot with critical configuration issues")
            logger.critical("=" * 80)
            logger.critical("Please fix the issues above and restart the bot")
            logger.critical("Refer to PRODUCTION_DEPLOYMENT_CHECKLIST.md for configuration guide")
            sys.exit(1)
        elif validation_result['issues']:
            logger.warning("⚠️ Development mode - continuing despite configuration issues")
        
    except Exception as e:
        logger.error(f"❌ Configuration validation failed: {e}")
        if is_production:
            logger.critical("Cannot continue with unvalidated configuration in production")
            sys.exit(1)
    
    # Perform comprehensive startup cleanup
    try:
        from utils.startup_cleanup import startup_cleaner
        from utils.process_manager import process_manager
        
        logger.info("🧽 Starting comprehensive system cleanup...")
        cleanup_report = startup_cleaner.perform_startup_cleanup()
        
        if cleanup_report['stale_processes_found'] > 0:
            logger.info(f"🗿 Found and cleaned {cleanup_report['stale_processes_cleaned']}/{cleanup_report['stale_processes_found']} stale processes")
        
        if cleanup_report['port_conflicts_found'] > 0:
            logger.warning(f"⚠️ Resolved {cleanup_report['port_conflicts_found']} port conflicts")
        
        logger.info("🔒 Establishing singleton process...")
        singleton_port = int(os.environ.get("PORT", "5000"))
        if not process_manager.ensure_singleton(port=singleton_port):
            logger.error("❌ Another instance is already running or port conflicts exist")
            logger.info("💡 If this is unexpected, wait 30 seconds and try again")
            sys.exit(1)
        
        logger.info("✅ Singleton process established - no duplicates possible")
        
    except Exception as e:
        logger.error(f"❌ Singleton setup failed: {e}")
        sys.exit(1)
    
    # Import and start bot
    try:
        from main import main as bot_main
        bot_main()
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Bot stopped by user")
        # Cleanup singleton lock
        try:
            from utils.process_manager import process_manager
            process_manager.release_lock()
            logger.info("✅ Process lock released")
        except Exception as e:
            logger.warning(f"⚠️ Could not release process lock: {e}")
    except Exception as e:
        logger.error(f"❌ Bot startup failed: {e}")
        import traceback
        traceback.print_exc()
        # Cleanup singleton lock on failure
        try:
            from utils.process_manager import process_manager
            process_manager.release_lock()
        except Exception as cleanup_error:
            logger.warning(f"⚠️ Could not release process lock during cleanup: {cleanup_error}")
        sys.exit(1)

if __name__ == "__main__":
    main()
