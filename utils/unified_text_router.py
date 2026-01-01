"""
Unified Text Router - Phase 1 Critical Fix
Consolidates all text message handling to prevent handler competition
"""

import logging
from typing import Optional, Dict, Any, Callable
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class UnifiedTextRouter:
    """
    Single entry point for all text message processing
    Routes messages to appropriate handlers based on conversation state
    """
    
    def __init__(self):
        # Registry of conversation state -> handler mappings
        self._conversation_handlers: Dict[str, Callable] = {}
        # Default fallback handler
        self._fallback_handler: Optional[Callable] = None
        
    def register_conversation_handler(self, conversation_type: str, handler: Callable):
        """Register a handler for a specific conversation type"""
        self._conversation_handlers[conversation_type] = handler
        logger.info(f"📝 Registered text handler for conversation: {conversation_type}")
        
    def set_fallback_handler(self, handler: Callable):
        """Set fallback handler for unmatched text"""
        self._fallback_handler = handler
        logger.info("📝 Registered fallback text handler")
        
    async def route_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """
        Main text routing function - determines which handler should process the message
        """
        user = update.effective_user
        if not user:
            return
            
        text = update.message.text if update.message else None
        if not text:
            return
            
        user_id = user.id
        
        # Get current conversation state from context
        conversation_state = self._get_active_conversation(context)
        
        logger.debug(f"🔀 Text Router: User {user_id} in conversation '{conversation_state}' sent: '{text[:50]}...'")
        
        # Route to appropriate handler based on conversation state
        if conversation_state and conversation_state in self._conversation_handlers:
            handler = self._conversation_handlers[conversation_state]
            logger.debug(f"📨 Routing to conversation handler: {conversation_state}")
            try:
                return await handler(update, context)
            except Exception as e:
                logger.error(f"❌ Error in conversation handler {conversation_state}: {e}")
                # Fall through to fallback
        
        # Handle special cases that bypass normal conversation flow
        special_result = await self._handle_special_cases(update, context, text)
        if special_result is not None:
            return special_result
            
        # Use fallback handler if available
        if self._fallback_handler:
            logger.debug("📨 Routing to fallback handler")
            try:
                return await self._fallback_handler(update, context)
            except Exception as e:
                logger.error(f"❌ Error in fallback handler: {e}")
        
        # Last resort - log unhandled text
        logger.warning(f"⚠️ Unhandled text message from user {user_id}: '{text[:100]}'")
        
    def _get_active_conversation(self, context: ContextTypes.DEFAULT_TYPE) -> Optional[str]:
        """Determine active conversation type from context"""
        if not context.user_data:
            return None
            
        # Check for active conversation states in priority order
        conversation_checks = [
            # Highest priority - OTP verification must come FIRST before any wallet operations
            ("otp_verification", lambda: (
                # Check wallet_state for OTP verification
                context.user_data.get("wallet_state") in ["verifying_crypto_otp", "verifying_ngn_otp"] or
                # Check current_state for OTP verification (both lowercase and uppercase variants)
                context.user_data.get("current_state") in ["VERIFYING_CRYPTO_OTP", "VERIFYING_NGN_OTP", "verifying_crypto_otp", "verifying_ngn_otp"] or
                # Check wallet_data state for OTP verification
                context.user_data.get("wallet_data", {}).get("state") in ["verifying_crypto_otp", "verifying_ngn_otp"] or
                # Check if awaiting OTP verification
                context.user_data.get("awaiting_otp_verification", False) or
                # Check for active cashout with OTP step
                (
                    context.user_data.get("cashout_data", {}).get("active_cashout") and
                    context.user_data.get("cashout_data", {}).get("verification_id")
                )
            )),
            # High priority conversations
            ("dispute_chat", lambda: context.user_data.get("in_dispute_chat")),
            ("escrow_creation", lambda: context.user_data.get("escrow_data", {}).get("creating_escrow")),
            ("exchange_flow", lambda: context.user_data.get("exchange_data", {}).get("expecting_amount") or context.user_data.get("exchange_data", {}).get("expecting_bank_details") or context.user_data.get("exchange_data", {}).get("expecting_wallet_address")),
            # FIXED: wallet_input now excludes OTP verification states since they're handled above
            ("wallet_input", lambda: (
                # Check wallet_state (original logic - EXCLUDING OTP states)
                context.user_data.get("wallet_state") in [
                    "selecting_amount", "selecting_amount_crypto", "selecting_amount_ngn", 
                    "entering_crypto_address", "entering_crypto_details",
                    "adding_bank_selecting", "adding_bank_account_number", 
                    "adding_bank_confirming", "adding_bank_label", "adding_bank_searching", 
                    "entering_custom_amount", "entering_withdraw_address",
                    "selecting_withdraw_currency", "selecting_crypto_currency"
                ] or
                # Check current_state (enhanced - EXCLUDING OTP states)
                context.user_data.get("current_state") in [
                    "ENTERING_CUSTOM_AMOUNT", "SELECTING_WITHDRAW_CURRENCY", 
                    "SELECTING_CRYPTO_CURRENCY", "selecting_withdraw_currency", "selecting_crypto_currency"
                ] or
                # Check wallet_data['state'] (new - broader detection - EXCLUDING OTP states)
                context.user_data.get("wallet_data", {}).get("state") in [
                    "selecting_amount", "selecting_amount_crypto", "selecting_amount_ngn",
                    "entering_crypto_address", "entering_crypto_details",
                    "entering_custom_amount", "entering_withdraw_address",
                    "selecting_withdraw_currency", "selecting_crypto_currency"
                ] or
                # Check cashout_data current_state for currency selection
                context.user_data.get("cashout_data", {}).get("current_state") in [
                    "SELECTING_WITHDRAW_CURRENCY", "SELECTING_CRYPTO_CURRENCY",
                    "selecting_withdraw_currency", "selecting_crypto_currency"
                ] or
                # Check for active cashout with crypto method requiring address input (NON-OTP)
                (
                    context.user_data.get("cashout_data", {}).get("method") == "crypto" and
                    context.user_data.get("cashout_data", {}).get("currency") in ["ETH", "BTC", "USDT", "LTC", "DOGE", "TRX"] and
                    context.user_data.get("cashout_data", {}).get("amount") and
                    not context.user_data.get("cashout_data", {}).get("verification_id")  # NOT in OTP verification phase
                ) or
                # Legacy string states
                str(context.user_data.get("wallet_state")) in ["305", "321", "325"]
            )),
            ("cashout_flow", lambda: context.user_data.get("cashout_data", {}).get("active_cashout")),
            ("cashout_hash_input", lambda: context.user_data.get("awaiting_hash_input")),
            ("bank_reference_input", lambda: context.user_data.get("awaiting_bank_reference")),
            ("contact_management", lambda: context.user_data.get("contact_data", {}).get("active_contact")),
            ("chat_messaging", lambda: context.user_data.get("active_chat_session")),
            # Medium priority
            ("crypto_address_input", lambda: context.user_data.get("expecting_crypto_address")),
            ("amount_input", lambda: context.user_data.get("expecting_amount")),
            ("bank_reference_input", lambda: context.user_data.get("expecting_bank_reference")),
            ("hash_input", lambda: context.user_data.get("expecting_hash_input")),
            # General conversation fallback
            ("onboarding", lambda: context.user_data.get("onboarding_active")),
        ]
        
        for conv_type, check_func in conversation_checks:
            try:
                if check_func():
                    return conv_type
            except (KeyError, AttributeError, TypeError):
                continue
                
        return None
        
    async def _handle_special_cases(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> Optional[Any]:
        """Handle special text patterns that should bypass normal routing"""
        
        # Command-like text that should be treated specially
        if text.startswith('/'):
            return None  # Let command handlers process
            
        # Special keywords that trigger specific actions
        special_keywords = {
            'cancel': self._handle_cancel_keyword,
            'stop': self._handle_stop_keyword,
            'help': self._handle_help_keyword,
            'menu': self._handle_menu_keyword,
        }
        
        text_lower = text.lower().strip()
        if text_lower in special_keywords:
            logger.debug(f"🔑 Special keyword detected: {text_lower}")
            try:
                return await special_keywords[text_lower](update, context)
            except Exception as e:
                logger.error(f"❌ Error handling special keyword {text_lower}: {e}")
                
        return None
        
    async def _handle_cancel_keyword(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """Handle 'cancel' keyword - clear states and show menu"""
        from utils.session_state_manager import session_state_manager
        await session_state_manager.clear_user_state(update.effective_user.id)
        
        # Import here to avoid circular imports
        from handlers.menu import show_main_menu
        return await show_main_menu(update, context)
        
    async def _handle_stop_keyword(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """Handle 'stop' keyword - similar to cancel"""
        return await self._handle_cancel_keyword(update, context)
        
    async def _handle_help_keyword(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """Handle 'help' keyword - show help menu"""
        help_text = """
🆘 **LockBay Help**

**Quick Commands:**
• Type 'menu' - Return to main menu
• Type 'cancel' - Cancel current operation
• Type 'help' - Show this help

**Features:**
• 💰 Secure Escrow Trading
• 💱 Direct Exchange
• 💬 Trade Messaging
• 👤 Account Management

**Support:**
Use the trade messages feature to contact support during active trades.
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
        
    async def _handle_menu_keyword(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """Handle 'menu' keyword - show main menu"""
        from handlers.menu import show_main_menu
        return await show_main_menu(update, context)

# Global router instance
unified_text_router = UnifiedTextRouter()

# Register OTP verification handler
def register_otp_verification_handler():
    """Register OTP verification handler with the unified text router"""
    from handlers.otp_verification import handle_otp_verification
    unified_text_router.register_conversation_handler("otp_verification", handle_otp_verification)
    logger.info("✅ OTP verification handler registered with unified text router")

# Note: OTP verification handler registration moved to main.py startup sequence
# for eager registration at startup (prevents import time issues)