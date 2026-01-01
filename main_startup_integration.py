"""
Email Queue Initialization Integration
Add this to main.py or production_start.py to initialize the background email queue
"""

import asyncio
import logging
from services.background_email_queue import background_email_queue

logger = logging.getLogger(__name__)

async def initialize_background_email_system():
    """Initialize the background email queue system for production"""
    try:
        logger.info("🚀 Initializing background email queue system...")
        success = await background_email_queue.initialize()
        
        if success:
            logger.info("✅ Background email queue system initialized successfully")
            
            # Log queue health check
            health = await background_email_queue.health_check()
            logger.info(f"📊 Email Queue Health: {health.get('status', 'unknown')}")
            
            return True
        else:
            logger.error("❌ Background email queue initialization failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Critical error initializing background email system: {e}")
        return False

async def shutdown_background_email_system():
    """Gracefully shutdown the background email queue system"""
    try:
        logger.info("🔄 Shutting down background email queue system...")
        await background_email_queue.shutdown()
        logger.info("✅ Background email queue shutdown completed")
    except Exception as e:
        logger.error(f"❌ Error shutting down background email system: {e}")

# Add to main.py startup sequence:
# await initialize_background_email_system()

# Add to main.py shutdown sequence:  
# await shutdown_background_email_system()