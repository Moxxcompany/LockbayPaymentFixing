"""
Unified Callback Dispatcher - Consolidates Scattered Callback Logic

Provides consistent callback_data encoding/decoding and centralized handler registry.
Replaces scattered patterns with clean action-based routing.

Usage:
    # Encode callback data
    callback_data = encode_callback("select_bank", bank_id="123", user_id="456")
    
    # Register handler
    callback_registry.register("select_bank", handle_bank_selection)
    
    # Process callback (automatic in dispatcher)
    await process_callback(update, context)
"""

import logging
import json
import re
from typing import Dict, Any, Callable, Optional
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

logger = logging.getLogger(__name__)


class CallbackRegistry:
    """Central registry for callback handlers"""
    
    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._legacy_patterns: Dict[str, str] = {}
    
    def register(self, action: str, handler: Callable, legacy_pattern: Optional[str] = None):
        """
        Register a callback handler
        
        Args:
            action: Action name (e.g., "select_bank", "wallet_deposit")
            handler: Handler function 
            legacy_pattern: Optional legacy regex pattern for migration
        """
        self._handlers[action] = handler
        if legacy_pattern:
            self._legacy_patterns[legacy_pattern] = action
        logger.info(f"📋 CALLBACK_REGISTRY: Registered '{action}' handler")
    
    def get_handler(self, action: str) -> Optional[Callable]:
        """Get handler for action"""
        return self._handlers.get(action)
    
    def get_legacy_action(self, pattern: str) -> Optional[str]:
        """Map legacy pattern to action"""
        return self._legacy_patterns.get(pattern)
    
    def list_actions(self) -> list:
        """List all registered actions"""
        return list(self._handlers.keys())


# Global registry instance
callback_registry = CallbackRegistry()


def encode_callback(action: str, **params) -> str:
    """
    Encode callback data with consistent format
    
    Args:
        action: Action name (e.g., "select_bank")
        **params: Action parameters (e.g., bank_id="123")
    
    Returns:
        Encoded callback_data string
        
    Example:
        encode_callback("select_bank", bank_id="123", user_id="456")
        # Returns: "select_bank:eyJiYW5rX2lkIjoiMTIzIiwidXNlcl9pZCI6IjQ1NiJ9"
    """
    try:
        if params:
            # Base64 encode params for compact representation
            import base64
            params_json = json.dumps(params, separators=(',', ':'))
            params_b64 = base64.b64encode(params_json.encode()).decode()
            result = f"{action}:{params_b64}"
        else:
            result = action
        
        # CRITICAL: Enforce Telegram's 64-byte callback_data limit
        if len(result) > 64:
            logger.error(f"❌ CALLBACK_TOO_LONG: action={action}, length={len(result)}, limit=64")
            # Fallback: use just action without params
            return action
        
        return result
    except Exception as e:
        logger.error(f"❌ ENCODE_ERROR: action={action}, params={params}, error={e}")
        return action  # Fallback to simple action


def decode_callback(callback_data: str) -> tuple[str, Dict[str, Any]]:
    """
    FIXED: Decode callback data with improved fallback handling.
    
    Handles both base64-encoded JSON parameters and plain text parameters.
    
    Args:
        callback_data: Callback data string (either encoded or plain)
    
    Returns:
        Tuple of (action, params_dict)
        
    Example:
        decode_callback("select_bank:eyJiYW5rX2lkIjoiMTIzIn0")  # Base64 JSON
        decode_callback("select_verified_bank:0")              # Plain text
    """
    try:
        if ":" in callback_data:
            action, param_str = callback_data.split(":", 1)
            
            # ENHANCED: Try base64 decoding first, fallback to plain text
            try:
                import base64
                # Check if it looks like base64 (length multiple of 4, valid chars)
                if len(param_str) % 4 == 0 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in param_str):
                    params_json = base64.b64decode(param_str.encode()).decode()
                    params = json.loads(params_json)
                    logger.debug(f"🔓 BASE64_DECODE: {action} -> {params}")
                    return action, params
                else:
                    # Not base64 - treat as plain text parameter
                    params = {"param": param_str}
                    logger.debug(f"🔓 PLAIN_DECODE: {action} -> {params}")
                    return action, params
                    
            except (Exception,):
                # Base64 decode failed - treat as plain text
                params = {"param": param_str}
                logger.debug(f"🔓 FALLBACK_DECODE: {action} -> {params}")
                return action, params
            
        else:
            return callback_data, {}
            
    except Exception as e:
        logger.warning(f"⚠️ DECODE_ERROR: callback_data={callback_data}, error={e}")
        # Final fallback: treat as legacy format (action:param)
        if ":" in callback_data:
            parts = callback_data.split(":", 1)
            return parts[0], {"param": parts[1]}
        return callback_data, {}


async def unified_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Unified callback handler that dispatches to registered handlers
    
    This replaces multiple scattered CallbackQueryHandler registrations
    with a single dispatcher that routes based on action.
    """
    callback_data = ""  # Initialize for error handling scope
    try:
        query = update.callback_query
        if not query:
            return
        
        callback_data = query.data or ""
        if not callback_data:
            logger.warning("⚠️ EMPTY_CALLBACK: No callback_data in query")
            return
        
        # Decode action and parameters
        action, params = decode_callback(callback_data)
        
        # Get handler for action
        handler = callback_registry.get_handler(action)
        if not handler:
            logger.warning(f"⚠️ UNREGISTERED_ACTION: action={action}, callback_data={callback_data}")
            await query.answer("❌ Action not recognized")
            return
        
        # Add decoded params to context for handler access (ensure user_data exists)
        if context.user_data is None:
            context.user_data = {}
        
        context.user_data.update({
            'callback_action': action,
            'callback_params': params,
            'callback_data': callback_data
        })
        
        logger.info(f"🎯 CALLBACK_DISPATCH: action={action}, params={params}")
        
        # Call the handler
        await handler(update, context)
        
    except Exception as e:
        logger.error(f"❌ CALLBACK_DISPATCH_ERROR: callback_data={callback_data}, error={e}", exc_info=True)
        if update.callback_query:
            await update.callback_query.answer("❌ Processing error")


def create_unified_handler() -> CallbackQueryHandler:
    """
    Create the unified CallbackQueryHandler with scoped pattern
    
    Only matches registered actions to avoid breaking legacy handlers.
    
    Returns:
        CallbackQueryHandler that dispatches only registered callbacks
    """
    # CRITICAL FIX: Only match registered actions, not all callbacks
    # This prevents breaking legacy handlers by using catch-all pattern
    registered_actions = list(callback_registry._handlers.keys())
    if not registered_actions:
        # No actions registered yet - return a handler that matches nothing
        return CallbackQueryHandler(unified_callback_handler, pattern=r'^$')
    
    # Create pattern that only matches registered actions
    actions_pattern = '|'.join(re.escape(action) for action in registered_actions)
    pattern = f'^({actions_pattern})(:.*)?$'
    
    logger.info(f"🎯 SCOPED_PATTERN: {pattern} (matches {len(registered_actions)} actions)")
    
    return CallbackQueryHandler(unified_callback_handler, pattern=pattern)


# Convenience functions for common patterns
def get_callback_param(context: ContextTypes.DEFAULT_TYPE, key: str, default: Any = None) -> Any:
    """Get callback parameter from context"""
    if context.user_data is None:
        return default
    return context.user_data.get('callback_params', {}).get(key, default)


def get_callback_action(context: ContextTypes.DEFAULT_TYPE) -> Optional[str]:
    """Get callback action from context"""
    if context.user_data is None:
        return None
    return context.user_data.get('callback_action')


# Registration helpers for migration
def register_wallet_callbacks():
    """Register wallet-related callbacks"""
    from handlers.wallet_direct import handle_select_bank, handle_select_verified_bank
    
    callback_registry.register("select_bank", handle_select_bank, "^select_bank:.*$")
    callback_registry.register("select_verified_bank", handle_select_verified_bank, "^select_verified_bank:.*$")


def register_admin_callbacks():
    """Register admin-related callbacks"""
    # These will be migrated in phases
    pass


def register_support_callbacks():
    """Register support-related callbacks"""
    # These will be migrated in phases  
    pass


def initialize_callback_system():
    """Initialize the unified callback system"""
    logger.info("🚀 CALLBACK_SYSTEM: Initializing unified callback dispatcher...")
    
    # Register core callbacks
    register_wallet_callbacks()
    
    # Log registered actions
    actions = callback_registry.list_actions()
    logger.info(f"📋 CALLBACK_SYSTEM: Registered {len(actions)} actions: {actions}")
    
    logger.info("✅ CALLBACK_SYSTEM: Unified callback dispatcher ready")
    
    return create_unified_handler()