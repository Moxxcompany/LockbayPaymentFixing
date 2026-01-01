"""
Simple Auto-Release Task Runner

This creates a lightweight background task that runs the auto-release service
periodically without requiring the complex scheduler system.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from services.standalone_auto_release_service import auto_release_service

logger = logging.getLogger(__name__)

class AutoReleaseTaskRunner:
    """Simple task runner for auto-release functionality"""
    
    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.last_warning_check = None
        self.last_auto_release_check = None
        
    async def start(self):
        """Start the background task runner"""
        if self.running:
            logger.warning("Auto-release task runner already running")
            return
            
        self.running = True
        self.task = asyncio.create_task(self._run_loop())
        logger.info("✅ Auto-release task runner started")
        
    async def stop(self):
        """Stop the background task runner"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("✅ Auto-release task runner stopped")
        
    async def _run_loop(self):
        """Main loop for auto-release checks"""
        try:
            while self.running:
                current_time = datetime.now(timezone.utc)
                
                # Check delivery warnings every 30 minutes
                if (self.last_warning_check is None or 
                    current_time - self.last_warning_check >= timedelta(minutes=30)):
                    try:
                        warnings_sent = await auto_release_service.send_delivery_deadline_warnings()
                        self.last_warning_check = current_time
                        if warnings_sent > 0:
                            logger.info(f"✅ Delivery warnings: {warnings_sent} sent")
                    except Exception as e:
                        logger.error(f"❌ Error in delivery warning check: {e}")
                
                # Check auto-releases every 10 minutes
                if (self.last_auto_release_check is None or 
                    current_time - self.last_auto_release_check >= timedelta(minutes=10)):
                    try:
                        auto_releases = await auto_release_service.process_auto_release()
                        self.last_auto_release_check = current_time
                        if auto_releases > 0:
                            logger.info(f"✅ Auto-releases: {auto_releases} processed")
                    except Exception as e:
                        logger.error(f"❌ Error in auto-release check: {e}")
                
                # Sleep for 60 seconds before next check
                await asyncio.sleep(60)
                
        except asyncio.CancelledError:
            logger.info("Auto-release task runner cancelled")
        except Exception as e:
            logger.error(f"❌ Error in auto-release task runner: {e}")
            
    async def run_manual_check(self):
        """Run a manual check now (for testing/debugging)"""
        try:
            logger.info("🔄 Running manual auto-release check...")
            results = await auto_release_service.run_full_check()
            logger.info(f"✅ Manual check complete: {results}")
            return results
        except Exception as e:
            logger.error(f"❌ Error in manual check: {e}")
            return {"success": False, "error": str(e)}

# Global task runner instance
task_runner = AutoReleaseTaskRunner()

async def start_auto_release_background_task():
    """Start the auto-release background task"""
    await task_runner.start()

async def stop_auto_release_background_task():
    """Stop the auto-release background task"""
    await task_runner.stop()

async def run_manual_auto_release_check():
    """Run a manual auto-release check"""
    return await task_runner.run_manual_check()