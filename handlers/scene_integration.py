"""
Scene Engine Handler Integration

Integrates Scene Engine with existing Telegram handlers using the strangler pattern.
Allows scenes to run alongside existing handlers for gradual migration.
"""

import logging
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

from services.scene_engine import handle_scene_message, start_user_scene
from services.scene_integration_test import quick_scene_test

logger = logging.getLogger(__name__)

class SceneHandlerIntegration:
    """Integration layer for Scene Engine with existing handlers"""
    
    def __init__(self):
        self.scene_enabled = True
        self.fallback_to_handlers = True
    
    async def try_scene_handler(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE
    ) -> bool:
        """Try to handle message with Scene Engine first"""
        if not self.scene_enabled:
            return False
        
        try:
            # Let Scene Engine try to handle the message
            handled = await handle_scene_message(update, context)
            
            if handled:
                logger.debug(f"Scene Engine handled message for user {update.effective_user.id if update.effective_user else 'None'}")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Scene Engine error: {e}")
            # If Scene Engine fails, fall back to regular handlers
            return False
    
    async def start_scene_flow(
        self, 
        scene_id: str, 
        user_id: int, 
        initial_data: Optional[dict] = None
    ) -> bool:
        """Start a scene flow for a user"""
        if not self.scene_enabled:
            return False
        
        try:
            return await start_user_scene(scene_id, user_id, initial_data)
        except Exception as e:
            logger.error(f"Failed to start scene {scene_id}: {e}")
            return False

# Global integration instance
scene_integration = SceneHandlerIntegration()

# Helper functions for existing handlers
async def try_scene_first(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Try Scene Engine before falling back to existing handlers"""
    return await scene_integration.try_scene_handler(update, context)

async def start_ngn_cashout_scene(user_id: int, initial_amount: Optional[float] = None) -> bool:
    """Start NGN cashout scene"""
    initial_data = {'amount': initial_amount} if initial_amount else {}
    return await scene_integration.start_scene_flow('ngn_cashout', user_id, initial_data)

async def start_crypto_cashout_scene(user_id: int, crypto: Optional[str] = None) -> bool:
    """Start crypto cashout scene"""
    initial_data = {'selected_crypto': crypto} if crypto else {}
    return await scene_integration.start_scene_flow('crypto_cashout', user_id, initial_data)

async def start_wallet_funding_scene(user_id: int) -> bool:
    """Start wallet funding scene"""
    return await scene_integration.start_scene_flow('wallet_funding', user_id)

async def start_escrow_creation_scene(user_id: int) -> bool:
    """Start escrow creation scene"""
    return await scene_integration.start_scene_flow('escrow_creation', user_id)

# Integration test functions
async def test_scene_integration() -> dict:
    """Test Scene Engine integration"""
    try:
        from services.scene_integration_test import run_scene_integration_tests
        return await run_scene_integration_tests()
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Scene integration test failed'
        }

async def verify_scene_engine() -> bool:
    """Quick verification that Scene Engine is working"""
    return await quick_scene_test()