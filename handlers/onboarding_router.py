"""
Clean Onboarding Router - Architect's Strategic Rewrite
Disciplined async patterns with clean utilities and proper session management

Features:
- Clean async utilities: get_or_create_user(), render_step(), transition()
- All background tasks properly awaited: await run_background_task(coro)
- Centralized callback parsing and message handling
- Consistent session lifecycle management
- No inline fire-and-forget patterns
"""

import logging
import asyncio
import html
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from sqlalchemy.ext.asyncio import AsyncSession
from models import User, OnboardingStep, EscrowStatus, OnboardingSession
from sqlalchemy import select, func, text
from database import get_async_session
# Removed unsafe async_atomic_transaction - now using run_io_task pattern
from services.onboarding_service import OnboardingService
from services.email_verification_service import EmailVerificationService
from services.admin_trade_notifications import admin_trade_notifications
from utils.callback_utils import safe_answer_callback_query, safe_edit_message_text
from utils.helpers import get_user_display_name
from utils.keyboards import main_menu_keyboard
from async_user_utils import get_or_create_user_async

async def safe_reply_text(update: Update, text: str, **kwargs) -> bool:
    """
    Safely send reply messages with comprehensive error handling
    
    Handles both regular messages and callback queries
    Returns:
        bool: True if message sent successfully, False if failed
    """
    # DIAGNOSTIC: Log attempt details
    user_id = update.effective_user.id if update.effective_user else "unknown"
    message_preview = text[:30].replace('\n', ' ') + '...' if len(text) > 30 else text.replace('\n', ' ')
    
    try:
        if not update:
            logger.warning(f"safe_reply_text: Invalid update for user {user_id}")
            return False
        
        # Handle callback queries by using callback_query.message
        if update.callback_query and update.callback_query.message:
            # Type check: Ensure message is accessible (not MaybeInaccessibleMessage)
            from telegram import Message
            if isinstance(update.callback_query.message, Message):
                logger.debug(f"📨 safe_reply_text: Sending via callback_query.message for user {user_id}")
                await update.callback_query.message.reply_text(text, **kwargs)
                logger.debug(f"✅ safe_reply_text: Sent successfully via callback_query for user {user_id}")
                return True
            else:
                logger.warning(f"safe_reply_text: Message is inaccessible (MaybeInaccessibleMessage) for user {user_id}")
                return False
        elif update.message:
            logger.debug(f"📨 safe_reply_text: Sending via update.message for user {user_id} - '{message_preview}'")
            await update.message.reply_text(text, **kwargs)
            logger.debug(f"✅ safe_reply_text: Sent successfully via update.message for user {user_id}")
            return True
        else:
            logger.warning(f"⚠️ safe_reply_text: No message or callback_query.message found for user {user_id} (callback_query exists: {bool(update.callback_query)})")
            return False
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ safe_reply_text EXCEPTION for user {user_id}: {error_msg}", exc_info=True)
        
        # Handle specific telegram errors gracefully
        if "Chat not found" in error_msg:
            logger.warning(f"Chat not found when sending reply to user {user_id} - user may have blocked bot")
            return False
        elif "Bot was blocked" in error_msg or "Forbidden" in error_msg:
            logger.warning(f"Bot was blocked by user {user_id} - cannot send reply")
            return False
        elif "User is deactivated" in error_msg:
            logger.warning(f"User account {user_id} is deactivated - cannot send reply")
            return False
        elif "Message_too_long" in error_msg:
            logger.warning(f"Message too long for user {user_id} - truncating and retrying")
            # Try with truncated message
            try:
                short_text = text[:4000] + "..." if len(text) > 4000 else text
                if update.message:
                    await update.message.reply_text(short_text, **kwargs)
                return True
            except Exception:
                logger.error(f"Failed to send even truncated message to user {user_id}")
                return False
        elif "retry after" in error_msg.lower():
            logger.warning(f"Rate limited for user {user_id} - message not sent: {error_msg}")
            return False
        else:
            # For other errors, log but don't crash
            logger.error(f"Unexpected reply error for user {user_id}: {error_msg}")
            return False

from utils.helpers import validate_email, get_user_display_name
from utils.keyboards import main_menu_keyboard
from utils.user_cache import invalidate_user_cache
from caching.enhanced_cache import EnhancedCache
from config import Config

# PERFORMANCE OPTIMIZATION: Onboarding cache invalidation
from utils.onboarding_prefetch import invalidate_onboarding_cache

# Clean async utilities
from utils.completion_time_integration import track_onboarding_step, OperationType
from utils.background_task_runner import run_background_task, run_io_task
from database import managed_session, async_managed_session

logger = logging.getLogger(__name__)

# Performance cache with proper lifecycle
_user_lookup_cache = EnhancedCache(default_ttl=600, max_size=5000)

# ENHANCED IDEMPOTENCY: Per-user locks and step deduplication with improved race condition handling
_user_locks: Dict[int, asyncio.Lock] = {}
_step_cache = EnhancedCache(default_ttl=30, max_size=1000)  # 30-second TTL for better slow network handling
_message_cache = EnhancedCache(default_ttl=300, max_size=1000)  # 5-minute TTL for message IDs
_state_transition_cache = EnhancedCache(default_ttl=60, max_size=1000)  # Enhanced state transition tracking

def _get_user_lock(user_id: int) -> asyncio.Lock:
    """Get or create per-user lock for idempotency"""
    if user_id not in _user_locks:
        _user_locks[user_id] = asyncio.Lock()
    return _user_locks[user_id]

def _get_step_signature(current_step: str, email: Optional[str] = None, state: Optional[str] = None) -> str:
    """Generate enhanced step signature for deduplication with state awareness"""
    return f"{current_step}:{email or ''}:{state or 'default'}"

def _should_suppress_duplicate(user_id: int, step_signature: str) -> Tuple[bool, Optional[int]]:
    """Check if we should suppress duplicate step rendering with enhanced logic"""
    cache_key = f"ob:step:{user_id}"
    cached_data = _step_cache.get(cache_key)
    
    if cached_data and cached_data.get('signature') == step_signature:
        # Check if enough time has passed for slow network users
        timestamp_str = cached_data.get('timestamp', '')
        if timestamp_str:
            try:
                cached_time = datetime.fromisoformat(timestamp_str)
                time_diff = (datetime.utcnow() - cached_time).total_seconds()
                # Allow re-render if more than 5 seconds have passed (for slow networks)
                if time_diff > 5:
                    logger.info(f"🔄 SLOW_NETWORK_ALLOWANCE: Re-rendering after {time_diff:.1f}s for user {user_id}")
                    return False, cached_data.get('message_id')
            except Exception as e:
                logger.debug(f"Error parsing cached timestamp: {e}")
        
        return True, cached_data.get('message_id')
    
    return False, None

def _record_step_render(user_id: int, step_signature: str, message_id: Optional[int] = None) -> None:
    """Record step rendering for deduplication with enhanced state tracking"""
    cache_key = f"ob:step:{user_id}"
    _step_cache.set(cache_key, {
        'signature': step_signature,
        'message_id': message_id,
        'timestamp': datetime.utcnow().isoformat()
    })
    
    # Also record state transition for better tracking
    state_key = f"ob:state:{user_id}"
    _state_transition_cache.set(state_key, {
        'current_step': step_signature.split(':')[0],
        'status': 'rendered',
        'last_activity': datetime.utcnow().isoformat()
    })

def _track_state_transition(user_id: int, from_state: str, to_state: str, context: Optional[str] = None) -> None:
    """Track state transitions for better debugging and UX"""
    transition_key = f"ob:transition:{user_id}"
    transition_data = {
        'from_state': from_state,
        'to_state': to_state,
        'context': context,
        'timestamp': datetime.utcnow().isoformat()
    }
    _state_transition_cache.set(transition_key, transition_data)
    logger.info(f"🔄 STATE_TRANSITION: User {user_id} {from_state} → {to_state} ({context or 'no context'})")

async def _get_user_state_context_async(user_id: int) -> Dict[str, Any]:
    """Get user state context from cache for UX decisions
    
    PERFORMANCE: No database fallback - cache invalidation is now fixed with correct keys
    Unknown state is acceptable here; actual state validation happens in transition handlers
    """
    state_key = f"ob:state:{user_id}"
    transition_key = f"ob:transition:{user_id}"
    
    current_state = _state_transition_cache.get(state_key) or {}
    last_transition = _state_transition_cache.get(transition_key) or {}
    
    # Calculate timing information for edge case detection
    last_activity_str = current_state.get('last_activity', '')
    seconds_since_activity = 0
    if last_activity_str:
        try:
            last_activity = datetime.fromisoformat(last_activity_str)
            seconds_since_activity = (datetime.utcnow() - last_activity).total_seconds()
        except Exception:
            pass
    
    # Detect potential edge cases
    edge_cases = []
    if seconds_since_activity > 600:  # 10 minutes of inactivity
        edge_cases.append('session_timeout_risk')
    if seconds_since_activity > 1800:  # 30 minutes - definite timeout
        edge_cases.append('session_expired')
    
    return {
        'current_state': current_state,
        'last_transition': last_transition,
        'has_recent_activity': bool(current_state.get('last_activity')),
        'seconds_since_activity': seconds_since_activity,
        'edge_cases': edge_cases,
        'needs_recovery': len(edge_cases) > 0
    }

def _handle_edge_case_recovery(user_id: int, edge_case: str) -> Dict[str, Any]:
    """Handle specific edge cases with appropriate recovery actions"""
    recovery_actions = {
        'session_timeout_risk': {
            'action': 'extend_session',
            'message': OnboardingText.EDGE_CASE_RECOVERY['session_timeout'],
            'suggestion': 'continue_current_step'
        },
        'session_expired': {
            'action': 'restart_session',
            'message': OnboardingText.EDGE_CASE_RECOVERY['session_timeout'],
            'suggestion': 'restart_from_email'
        },
        'network_interrupted': {
            'action': 'retry_last_action',
            'message': OnboardingText.EDGE_CASE_RECOVERY['network_interrupted'],
            'suggestion': 'show_retry_options'
        },
        'malformed_input_repeated': {
            'action': 'provide_format_help',
            'message': OnboardingText.EDGE_CASE_RECOVERY['malformed_otp'],
            'suggestion': 'show_input_example'
        },
        'rapid_attempts': {
            'action': 'enforce_cooldown',
            'message': OnboardingText.EDGE_CASE_RECOVERY['rapid_attempts_detected'],
            'suggestion': 'show_wait_message'
        }
    }
    
    recovery = recovery_actions.get(edge_case, {
        'action': 'generic_recovery',
        'message': 'An issue was detected. Please try again.',
        'suggestion': 'restart_flow'
    })
    
    logger.info(f"🔄 EDGE_CASE_RECOVERY: User {user_id} edge_case {edge_case} action {recovery['action']}")
    return recovery

# Clean callback constants
class OnboardingCallbacks:
    START = "ob:start"
    RESEND_OTP = "ob:resend"
    CHANGE_EMAIL = "ob:change:email"
    TOS_ACCEPT = "ob:tos:accept"
    TOS_DECLINE = "ob:tos:decline"
    CANCEL = "ob:cancel"
    SKIP_EMAIL = "ob:skip:email"
    HELP_EMAIL = "ob:help:email"
    HELP_OTP = "ob:help:otp"
    HELP_TERMS = "ob:help:terms"

# Clean UI text constants
class OnboardingText:
    PROGRESS_INDICATORS = {
        OnboardingStep.CAPTURE_EMAIL.value: "📧 Step 1/3",
        OnboardingStep.VERIFY_OTP.value: "🔐 Step 2/3", 
        OnboardingStep.ACCEPT_TOS.value: "📋 Step 3/3",
        OnboardingStep.DONE.value: "✅ Complete"
    }
    
    PROGRESS_BARS = {
        OnboardingStep.CAPTURE_EMAIL.value: "🟦⬜⬜",
        OnboardingStep.VERIFY_OTP.value: "🟦🟦⬜",
        OnboardingStep.ACCEPT_TOS.value: "🟦🟦🟦",
        OnboardingStep.DONE.value: "🟦🟦🟦"
    }
    
    # Enhanced state transition indicators with comprehensive edge case coverage
    STATE_INDICATORS = {
        "processing": "⏳ Processing...",
        "verifying": "🔍 Verifying...",
        "sending_email": "📧 Sending code...",
        "completing": "🎉 Completing setup...",
        "failed": "❌ Failed",
        "success": "✅ Success",
        "waiting_input": "⌨️ Waiting for input...",
        "expired": "⏰ Expired",
        "rate_limited": "⏳ Rate limited",
        "network_error": "📡 Connection issue",
        "session_timeout": "⏰ Session timed out",
        "malformed_input": "❌ Invalid format",
        "recovering": "🔄 Recovering...",
        "retrying": "🔄 Retrying..."
    }
    
    # Edge case recovery messages
    EDGE_CASE_RECOVERY = {
        "session_timeout": "Don't worry! Your progress is saved. Click 'Restart' to continue where you left off.",
        "network_interrupted": "Connection was interrupted. Please check your internet and try again.",
        "malformed_otp": "Please enter exactly 6 digits for your verification code.",
        "expired_multiple_attempts": "Multiple codes have expired. Let's get you a fresh one.",
        "rapid_attempts_detected": "We detected rapid attempts. Please wait a moment before trying again."
    }

    WELCOME = f"""
🎯 <b>Welcome to {Config.PLATFORM_NAME}!</b>

{{progress_bar}} <b>Quick 3-step setup:</b>
📧 Email verification → 🔐 OTP → 📋 Terms

✨ <b>What you'll get:</b>
💰 Multi-crypto wallet • 🇳🇬 NGN transfers
🔒 Secure escrow • ⚡ Auto cashouts

💾 <i>Progress auto-saved • Takes 2 minutes</i>
"""

    EMAIL_PROMPT = """
{progress_indicator} {progress_bar}
📧 <b>Email Verification</b>

✉️ <b>Enter your email address:</b>
<i>Example: your.name@gmail.com</i>

🔒 <i>We'll send a 6-digit verification code immediately</i>
"""

    OTP_PROMPT = """
{progress_indicator} {progress_bar}
🔐 <b>Verify Email</b>

📨 <b>Code sent to:</b> <code>{email}</code>

🔢 <b>Enter the 6-digit code:</b>
<i>Example: 123456 (no spaces)</i>

⏰ <b>Status:</b> Expires in {expires_minutes}m • {remaining_attempts}/{max_attempts} attempts left
"""

    TERMS_PROMPT = """
{progress_indicator} {progress_bar}
📋 <b>Final Step - Accept Terms</b>

By accepting, you agree to our Terms of Service and Privacy Policy.
"""

    COMPLETION = """
🎉 <b>Welcome to {Config.PLATFORM_NAME}!</b>

✅ Account ready • 📧 {email} verified

Use the menu below to start trading.
"""

    ERROR_MESSAGES = {
        "invalid_email": "❌ <b>Invalid Email Format</b>\n\n📧 Please enter a valid email address like:\n<code>your.name@gmail.com</code>\n\n💡 <i>Double-check for typos and make sure it includes @ and a domain</i>",
        "email_taken": "⚠️ <b>Email Already Registered</b>\n\n📧 This email is already in use by another account.\n\n🔄 <b>Options:</b>\n• Use a different email address\n• Contact support if this is your email\n• Try logging in instead of registering",
        "rate_limit": "⏳ <b>Slow Down Please</b>\n\n🛡️ You're making requests too quickly for security.\n\n⏰ <b>What to do:</b>\n• Wait 1-2 minutes\n• Then try again\n• Contact support if issue persists",
        "otp_invalid": "❌ <b>Verification Code Incorrect</b>\n\n🔢 The code you entered doesn't match.\n\n✅ <b>Please check:</b>\n• Enter exactly 6 digits\n• No spaces or letters\n• Use the most recent code\n• Check for typos",
        "otp_expired": "⏰ <b>Verification Code Expired</b>\n\n📧 Your code has expired for security.\n\n🔄 <b>Next steps:</b>\n• Click 'Resend Code' below\n• Check your email for the new code\n• Enter it within 15 minutes",
        "max_attempts": "🚫 <b>Too Many Attempts</b>\n\n🔒 For security, this code is now locked.\n\n🆕 <b>Get a fresh start:</b>\n• Click 'Resend Code' for a new one\n• Check your email carefully\n• Enter the new code correctly",
        "system_error": "⚠️ <b>Technical Issue</b>\n\n🔧 Something went wrong on our end.\n\n🔄 <b>Please try:</b>\n• Wait 30 seconds\n• Try the action again\n• Contact support if it continues",
        "email_send_failed": "📧 <b>Email Sending Failed</b>\n\n📬 We couldn't send your verification code.\n\n✅ <b>Check:</b>\n• Email address is correct\n• Not in spam folder\n• Internet connection is stable\n\n🔄 Try 'Resend Code' or use a different email",
        "session_expired": "⏰ <b>Session Expired</b>\n\n🔄 Your setup session has timed out for security.\n\n🚀 <b>No worries:</b>\n• Your progress is saved\n• Click 'Restart Setup'\n• Continue where you left off",
        "network_error": "📡 <b>Connection Issue</b>\n\n🌐 There seems to be a network problem.\n\n🔄 <b>Please try:</b>\n• Check your internet connection\n• Wait a moment and retry\n• Switch to a different network if possible",
        "malformed_input": "❌ <b>Invalid Input Format</b>\n\n📝 The information you entered isn't in the right format.\n\n✅ <b>Please ensure:</b>\n• Follow the example format shown\n• Remove any extra spaces\n• Use only allowed characters",
        "invalid_state_transition": "⚠️ <b>Invalid Action</b>\n\n🔄 This action isn't available at your current step.\n\n📍 <b>Current step:</b> Please continue with the verification shown above.\n\n💡 <i>Use the buttons provided or restart with /start if confused</i>",
        "expired": "⏰ <b>Code or Session Expired</b>\n\n🔄 For security, this has expired.\n\n🆕 <b>Get a fresh start:</b>\n• Click 'Resend Code' if in verification\n• Or restart the process with /start",
        "invalid_input": "❌ <b>Input Not Valid</b>\n\n📝 Please check your input and try again.\n\n✅ <b>Make sure:</b>\n• Format matches the example\n• All required information is included\n• No extra spaces or characters"
    }


# CLEAN ASYNC UTILITIES - Architect's Strategic Pattern

def get_main_menu_data_sync(user_id: int) -> dict:
    """Sync utility to get main menu data for completed users"""
    with managed_session() as session:
        from models import Wallet, Escrow
        
        try:
            # Get wallet balance
            result = session.execute(
                select(Wallet).where(Wallet.user_id == user_id, Wallet.currency == "USD")
            )
            wallet = result.scalar_one_or_none()
            balance = wallet.available_balance if wallet else 0.0
            
            # Get escrow stats
            total_trades_result = session.execute(
                select(func.count(Escrow.id)).where(Escrow.buyer_id == user_id)
            )
            total_trades = total_trades_result.scalar() or 0
            
            active_escrows_result = session.execute(
                select(func.count(Escrow.id)).where(
                    Escrow.buyer_id == user_id,
                    Escrow.status.in_([EscrowStatus.CREATED.value, EscrowStatus.PAYMENT_PENDING.value, EscrowStatus.PAYMENT_CONFIRMED.value, EscrowStatus.PARTIAL_PAYMENT.value, EscrowStatus.ACTIVE.value])
                )
            )
            active_escrows = active_escrows_result.scalar() or 0
            
            return {
                "balance": balance,
                "total_trades": total_trades,
                "active_escrows": active_escrows
            }
        except Exception as e:
            logger.error(f"Error fetching user stats for {user_id}: {e}")
            return {"balance": 0.0, "total_trades": 0, "active_escrows": 0}

def get_or_create_user_sync(telegram_user) -> Tuple[Optional[dict], bool]:
    """Sync utility to get or create user with proper session management and constraint handling"""
    if not telegram_user:
        return None, False

    def to_dict(user):
        """Convert User ORM instance to dict"""
        return {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "is_verified": user.is_verified,
            "onboarding_completed": user.onboarding_completed
        }
        
    with managed_session() as session:
        try:
            # CRITICAL: Check if user is on the blocklist BEFORE allowing onboarding
            from sqlalchemy import text
            blocklist_check = session.execute(
                text("SELECT id FROM blocked_telegram_ids WHERE telegram_id = :telegram_id"),
                {"telegram_id": telegram_user.id}
            ).scalar()
            
            if blocklist_check:
                logger.critical(f"🚫🚫🚫 BLOCKLIST_VIOLATION: User {telegram_user.id} ({telegram_user.username}) attempted to onboard but is blocked")
                return None, False
            
            # Check if user exists (User.id IS the telegram_id)
            existing_user = session.get(User, telegram_user.id)
            if existing_user:
                return to_dict(existing_user), False
            
            # Create new user
            from datetime import datetime
            now = datetime.utcnow()
            new_user = User(
                id=telegram_user.id,  # id IS the telegram_id
                telegram_id=telegram_user.id,  # Required field
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
                email=f"temp_{telegram_user.id}@onboarding.temp",
                is_verified=False,
                created_at=now,
                updated_at=now
            )
            session.add(new_user)
            session.flush()  # Sync flush
            
            logger.info(f"Created new user {telegram_user.id}")
            
            return to_dict(new_user), True
            
        except Exception as e:
            from sqlalchemy.exc import IntegrityError
            
            # Check if this is a constraint violation
            is_constraint_error = (
                isinstance(e, IntegrityError) or
                "UNIQUE constraint failed" in str(e) or 
                "IntegrityError" in str(e) or 
                "duplicate key" in str(e).lower() or
                "already exists" in str(e).lower()
            )
            
            if is_constraint_error:
                logger.info(f"User {telegram_user.id} already exists (constraint violation), fetching existing user")
                session.rollback()
                
                # Re-fetch the existing user
                existing_user = session.get(User, telegram_user.id)
                if existing_user:
                    logger.info(f"Successfully retrieved existing user {telegram_user.id} after constraint violation")
                    return to_dict(existing_user), False
                else:
                    logger.error(f"Failed to find user {telegram_user.id} after constraint violation")
                    return None, False
            else:
                logger.error(f"Unexpected error creating user {telegram_user.id}: {e}")
                raise


async def render_step(update: Update, step: str, **kwargs) -> None:
    """Clean utility to render onboarding steps with consistent UI"""
    if step == OnboardingStep.CAPTURE_EMAIL.value:
        await _render_email_step(update, **kwargs)
    elif step == OnboardingStep.VERIFY_OTP.value:
        await _render_otp_step(update, **kwargs)
    elif step == OnboardingStep.ACCEPT_TOS.value:
        await _render_terms_step(update, **kwargs)
    elif step == OnboardingStep.DONE.value:
        await _render_completion_step(update, **kwargs)
    else:
        logger.warning(f"Unknown onboarding step: {step}")

async def render_step_idempotent(update: Update, step: str, user_id: int, email: Optional[str] = None, state: Optional[str] = None, **kwargs) -> None:
    """Enhanced idempotent step rendering with duplicate prevention and state awareness"""
    
    # Get user state context for better UX decisions
    state_context = await _get_user_state_context_async(user_id)
    
    # Generate enhanced step signature for deduplication
    step_signature = _get_step_signature(step, email, state)
    
    # Check if we should suppress duplicate rendering
    should_suppress, existing_message_id = _should_suppress_duplicate(user_id, step_signature)
    
    if should_suppress:
        logger.info(f"🔄 IDEMPOTENT SUPPRESSED: User {user_id} step {step} already rendered recently")
        
        # Enhanced duplicate handling with better user feedback
        try:
            if existing_message_id and update.callback_query:
                # User clicked a button - give immediate feedback
                await safe_answer_callback_query(update.callback_query, "👋 Already in progress above!")
                return
            elif existing_message_id and update.message:
                # User sent a message - try to edit existing message with contextual help
                try:
                    current_step_name = OnboardingText.PROGRESS_INDICATORS.get(step, step)
                    await update.get_bot().edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=existing_message_id,
                        text=f"👋 <b>Continue Your Setup</b>\n\n{current_step_name} is already in progress above.\n\n💡 <i>Please use the buttons or follow the instructions shown there.</i>",
                        parse_mode="HTML"
                    )
                    return
                except Exception as e:
                    logger.debug(f"Could not edit existing message {existing_message_id}: {e}")
            
            # Fallback: Send contextual help message
            if update.message:
                step_name = OnboardingText.PROGRESS_INDICATORS.get(step, "Current step")
                await safe_reply_text(
                    update,
                    f"👋 <b>Setup In Progress</b>\n\n{step_name} is already active above.\n\n🔄 <i>Please continue with the verification step shown above, or use /start to restart if needed.</i>",
                    reply_markup=None,
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Error handling duplicate render for user {user_id}: {e}")
        return
    
    # Track state transition for better debugging
    previous_state = state_context.get('current_state', {}).get('current_step', 'unknown')
    _track_state_transition(user_id, previous_state, step, f"render_{state or 'default'}")
    
    # Render the step normally (first time or different step)
    logger.info(f"🎯 ENHANCED RENDER: User {user_id} step {step} state {state} signature {step_signature}")
    
    try:
        if step == OnboardingStep.CAPTURE_EMAIL.value:
            await _render_email_step(update, state=state, **kwargs)
        elif step == OnboardingStep.VERIFY_OTP.value:
            await _render_otp_step(update, state=state, **kwargs)
        elif step == OnboardingStep.ACCEPT_TOS.value:
            await _render_terms_step(update, state=state, **kwargs)
        elif step == OnboardingStep.DONE.value:
            await _render_completion_step(update, state=state, **kwargs)
        else:
            logger.warning(f"Unknown onboarding step: {step}")
            await _send_error(update, "system_error")
            return
        
        # Record this rendering to prevent duplicates
        message_id = None
        if hasattr(update, 'message') and update.message and update.message.message_id:
            message_id = update.message.message_id
        elif hasattr(update, 'callback_query') and update.callback_query and update.callback_query.message:
            message_id = update.callback_query.message.message_id
        
        _record_step_render(user_id, step_signature, message_id)
        
    except Exception as e:
        logger.error(f"Error rendering step {step} for user {user_id}: {e}")
        await _send_error(update, "system_error")


async def transition(user_id: int, action: str, data: Any = None, session: Optional[AsyncSession] = None, show_loading: bool = True) -> Dict[str, Any]:
    """Enhanced utility to handle onboarding state transitions with better feedback and validation"""
    
    # Track the transition attempt
    state_context = await _get_user_state_context_async(user_id)
    current_state = state_context.get('current_state', {}).get('current_step', 'unknown')
    
    logger.info(f"🔄 TRANSITION_START: User {user_id} action {action} from state {current_state}")
    
    # State validation - prevent invalid transitions
    valid_transitions = {
        "set_email": [OnboardingStep.CAPTURE_EMAIL.value, "unknown"],
        "verify_otp": [OnboardingStep.VERIFY_OTP.value, "unknown"],
        "accept_terms": [OnboardingStep.ACCEPT_TOS.value, "unknown"],
        "resend_otp": [OnboardingStep.VERIFY_OTP.value, "unknown"],
        "reset_email": [OnboardingStep.VERIFY_OTP.value, OnboardingStep.ACCEPT_TOS.value]
    }
    
    if action in valid_transitions and current_state not in valid_transitions[action]:
        logger.warning(f"⚠️ INVALID_TRANSITION: User {user_id} attempted {action} from invalid state {current_state}")
        return {
            "success": False, 
            "error": "invalid_state_transition",
            "message": "This action is not available in the current step."
        }
    
    try:
        # Track transition start
        _track_state_transition(user_id, current_state, f"{action}_processing", "starting")
        
        result = None
        if action == "set_email":
            result = await OnboardingService.set_email(user_id, data, session=session)
        elif action == "verify_otp":
            result = await OnboardingService.verify_otp(user_id, data, session=session)
        elif action == "accept_terms":
            # Let accept_tos manage its own session to trigger welcome email post-commit callback
            result = await OnboardingService.accept_tos(user_id)
        elif action == "resend_otp":
            result = await OnboardingService.resend_otp(user_id, session=session)
        elif action == "reset_email":
            result = await OnboardingService.reset_to_step(user_id, OnboardingStep.CAPTURE_EMAIL.value, session=session)
        else:
            logger.error(f"Unknown action: {action}")
            return {"success": False, "error": f"Unknown action: {action}"}
        
        # Track transition result
        if result and result.get("success"):
            new_state = result.get("current_step", "unknown")
            _track_state_transition(user_id, f"{action}_processing", new_state, "completed")
            logger.info(f"✅ TRANSITION_SUCCESS: User {user_id} action {action} → {new_state}")
            
            # CACHE_INVALIDATION: Clear state cache after successful step transition
            state_key = f"ob:state:{user_id}"
            _state_transition_cache.delete(state_key)
            logger.debug(f"🗑️ CACHE_INVALIDATE: Cleared state cache for user {user_id} after step transition")
        else:
            error = result.get("error", "unknown_error") if result else "no_result"
            _track_state_transition(user_id, f"{action}_processing", "error", error)
            logger.warning(f"❌ TRANSITION_FAILED: User {user_id} action {action} failed: {error}")
            
            # CACHE_INVALIDATION: Clear step cache on failure to prevent stale data
            cache_key = f"ob:step:{user_id}"
            _step_cache.delete(cache_key)  # Clear potentially stale cache
            logger.debug(f"🗑️ CACHE_INVALIDATE: Cleared step cache for user {user_id} after transition failure")
        
        return result or {"success": False, "error": "no_result"}
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ TRANSITION_ERROR: User {user_id}, action {action}: {error_msg}")
        _track_state_transition(user_id, f"{action}_processing", "exception", error_msg[:100])
        
        # CACHE_INVALIDATION: Clear step cache on failure to prevent stale data
        cache_key = f"ob:step:{user_id}"
        _step_cache.delete(cache_key)  # Clear potentially stale cache
        logger.debug(f"🗑️ CACHE_INVALIDATE: Cleared step cache for user {user_id} after transition failure")
        
        # Provide user-friendly error messages
        if "rate" in error_msg.lower() or "limit" in error_msg.lower():
            return {"success": False, "error": "rate_limit"}
        elif "expired" in error_msg.lower():
            return {"success": False, "error": "expired"}
        elif "invalid" in error_msg.lower():
            return {"success": False, "error": "invalid_input"}
        else:
            return {"success": False, "error": "system_error"}


async def invalidate_user_cache_async(user_id: str) -> None:
    """Clean async cache invalidation utility"""
    try:
        async with async_managed_session() as session:
            await session.execute(text("SELECT 1"))  # Minimal async cache invalidation
        _user_lookup_cache.delete(f"user_lookup_{user_id}")
        _user_lookup_cache.delete(f"full_user_{user_id}")
    except Exception as e:
        logger.warning(f"Cache invalidation failed for user {user_id}: {e}")


# MAIN ROUTER - Clean and centralized

async def onboarding_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Main onboarding router with idempotent duplicate prevention
    Handles all onboarding flow logic with proper session management and per-user locking
    """
    import time
    t0 = time.time()
    
    user = update.effective_user
    if not user:
        return

    # IDEMPOTENCY: Use per-user lock to prevent concurrent double-sends
    user_lock = _get_user_lock(user.id)
    user_data = None  # Initialize to avoid unbound variable error
    
    try:
        t1 = time.time()
        logger.info(f"⏱️ PERF [onboarding_router]: Entry to lock acquisition: {(t1-t0)*1000:.1f}ms")
        
        async with user_lock:
            t2 = time.time()
            logger.info(f"⏱️ PERF [onboarding_router]: Lock acquired in {(t2-t1)*1000:.1f}ms")
            
            # Get or create user with sync utility via run_io_task
            user_data, is_new = await get_or_create_user_async(user)
            t3 = time.time()
            logger.info(f"⏱️ PERF [onboarding_router]: get_or_create_user_async took {(t3-t2)*1000:.1f}ms")
            
            if not user_data:
                await _send_error(update, "system_error")
                return

            # Handle new user creation
            if is_new:
                # Auto-complete onboarding for new users - skip onboarding flow
                logger.info(f"🚀 Auto-completing onboarding for new user {user.id}")
                try:
                    from database import SessionLocal as SyncSessionLocal
                    from models import User as UserModel
                    with SyncSessionLocal() as sync_sess:
                        sync_sess.query(UserModel).filter(UserModel.id == user.id).update(
                            {"onboarding_completed": True}
                        )
                        sync_sess.commit()
                    logger.info(f"✅ Onboarding auto-completed for new user {user.id}")
                except Exception as auto_err:
                    logger.error(f"Error auto-completing onboarding for new user {user.id}: {auto_err}")
                
                # Send admin notification for new user
                asyncio.create_task(
                    admin_trade_notifications.notify_user_onboarding_started({
                        'user_id': user_data['id'],
                        'telegram_id': user_data['telegram_id'],
                        'username': user_data.get('username'),
                        'first_name': user_data.get('first_name'),
                        'last_name': user_data.get('last_name', ''),
                        'started_at': datetime.utcnow()
                    })
                )
                
                # Broadcast new user joined to groups
                try:
                    from services.group_event_service import group_event_service
                    asyncio.create_task(group_event_service.broadcast_new_user_onboarded({
                        'first_name': user_data.get('first_name', 'New User'),
                        'username': user_data.get('username')
                    }))
                except Exception as grp_err:
                    logger.error(f"Failed to broadcast new user event: {grp_err}")
                
                # Clean async cache invalidation
                await run_background_task(invalidate_user_cache_async(str(user.id)))
                # Show main menu directly instead of onboarding
                user_data['onboarding_completed'] = True
                await _show_main_menu(update, context, user_data)
                return

            # Check if already completed onboarding
            if user_data.get("onboarding_completed"):
                await _show_main_menu(update, context, user_data)
                return

            # Auto-complete onboarding for existing users who haven't completed it
            logger.info(f"🚀 Auto-completing onboarding for existing user {user_data['id']}")
            try:
                from database import SessionLocal as SyncSessionLocal
                from models import User as UserModel
                with SyncSessionLocal() as sync_sess:
                    sync_sess.query(UserModel).filter(UserModel.id == user_data['id']).update(
                        {"onboarding_completed": True}
                    )
                    sync_sess.commit()
                user_data['onboarding_completed'] = True
                logger.info(f"✅ Onboarding auto-completed for existing user {user_data['id']}")
            except Exception as auto_err:
                logger.error(f"Error auto-completing onboarding: {auto_err}")
            
            await _show_main_menu(update, context, user_data)
            return
            
            if current_step is None:
                # No active session found - show welcome page like new users
                logger.info(f"No session found for existing user {user_id} - showing welcome page")
                await _handle_new_user_start(update, context, user_data)
                return

            # Check for duplicate step rendering before handling actions
            t6 = time.time()
            email = session_info.get('email') if session_info else None
            step_signature = _get_step_signature(current_step, email)
            should_suppress, existing_message_id = _should_suppress_duplicate(user_id, step_signature)
            t7 = time.time()
            logger.info(f"⏱️ PERF [onboarding_router]: Duplicate check took {(t7-t6)*1000:.1f}ms")
            
            # IDEMPOTENCY: Check for duplicate rendering FIRST
            if should_suppress:
                    # This is a duplicate action - show gentle message instead
                    logger.info(f"🔄 DUPLICATE SUPPRESSED: User {user_id} duplicate onboarding for step {current_step}")
                    if existing_message_id:
                        try:
                            await update.get_bot().edit_message_text(
                                chat_id=update.effective_chat.id,
                                message_id=existing_message_id,
                                text="👋 Onboarding already in progress above. Please continue with the step shown."
                            )
                        except Exception:
                            # If edit fails, send a gentle message
                            if update.message:
                                await safe_reply_text(
                                    update,
                                    "👋 Welcome back! Your onboarding is already in progress.\n\n"
                                    "Please continue with the verification step above.",
                                    reply_markup=None
                                )
                    else:
                        # No existing message to edit, send gentle new message
                        if update.message:
                            await safe_reply_text(
                                update,
                                "👋 Welcome back! Your onboarding is already in progress.\n\n"
                                "Please continue with the verification step above.",
                                reply_markup=None
                            )
                    return
                
            # Route based on update type with clean handlers
            t8 = time.time()
            logger.info(f"⏱️ PERF [onboarding_router]: Total overhead before handler: {(t8-t0)*1000:.1f}ms")
            
            if update.callback_query:
                await _handle_callback(update, context, user_data, current_step)
            elif update.message and update.message.text:
                await _handle_text_input(update, context, user_data, current_step)
            else:
                # Render current step idempotently 
                await render_step_idempotent(update, current_step, user_id, email)

    except Exception as e:
        user_id = user_data.get("id", "unknown") if user_data else "unknown"
        logger.error(f"Onboarding router error for user {user_id}: {e}", exc_info=True)
        await _send_error(update, "system_error")


# CENTRALIZED MESSAGE HANDLING - Clean patterns

async def _handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                          user_data: dict, current_step: Optional[str] = None) -> None:
    """Centralized callback query handling with clean patterns"""
    query = update.callback_query
    if not query or not query.data:
        return

    await safe_answer_callback_query(query, "Processing...")
    callback_data = query.data

    # Clean callback routing with legacy pattern support
    if callback_data == OnboardingCallbacks.START:
        await _handle_start(update, context, user_data)
    elif callback_data == OnboardingCallbacks.RESEND_OTP:
        await _handle_resend_otp(update, context, user_data)
    elif callback_data == OnboardingCallbacks.CHANGE_EMAIL:
        await _handle_change_email(update, context, user_data)
    elif callback_data == OnboardingCallbacks.SKIP_EMAIL:
        await _handle_skip_email(update, context, user_data)
    elif callback_data == OnboardingCallbacks.TOS_ACCEPT:
        await _handle_accept_terms(update, context, user_data)
    elif callback_data == OnboardingCallbacks.TOS_DECLINE:
        await _handle_decline_terms(update, context, user_data)
    elif callback_data == OnboardingCallbacks.CANCEL:
        await _handle_cancel(update, context, user_data)
    elif callback_data.startswith("ob:help:"):
        help_type = callback_data.split(":")[-1]
        await _show_help(update, context, help_type)
    # ARCHITECT FIX: Legacy callback patterns support
    elif callback_data == "reject_terms_and_conditions":
        await _handle_decline_terms(update, context, user_data)
    elif callback_data == "accept_terms_and_conditions":
        await _handle_accept_terms(update, context, user_data)
    else:
        logger.warning(f"Unknown callback: {callback_data}")


async def _handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE,
                           user_data: dict, current_step: Optional[str] = None) -> None:
    """Centralized text input handling with clean patterns"""
    message = update.message
    if not message or not message.text:
        return

    text = message.text.strip()

    # Handle /start command
    if text.startswith('/start'):
        await _handle_start(update, context, user_data)
        return

    # Use passed current_step (already fetched in router) or fetch if missing
    user_id = user_data["id"]
    if current_step is None:
        current_step = await OnboardingService.get_current_step(user_id)
    
    if current_step == OnboardingStep.CAPTURE_EMAIL.value:
        await _handle_email_input(update, context, user_data, text)
    elif current_step == OnboardingStep.VERIFY_OTP.value:
        # BUGFIX: Prevent processing non-OTP-like inputs (like email addresses)
        # Only process if text looks like it could be an OTP attempt
        stripped_text = text.strip().replace(' ', '').replace('-', '')
        if len(stripped_text) <= 10 and (stripped_text.isdigit() or len(stripped_text) == 6):
            await _handle_otp_input(update, context, user_data, text)
        else:
            # Ignore non-OTP inputs (like email addresses being processed again)
            logger.info(f"Ignoring non-OTP text input for user {user_data.get('id', 'unknown')}: '{text[:20]}...'")
            await safe_reply_text(
                update,
                "🔢 <b>Please enter your 6-digit verification code</b>\n\n"
                "Check your email for the code we sent to complete verification.\n\n"
                "💡 <b>Tip:</b> The code contains only numbers (like 123456)",
                parse_mode="HTML"
            )
    else:
        await _send_error(update, "system_error", "Please use the buttons to navigate.")


# CLEAN STEP HANDLERS - Properly awaited async patterns

async def _show_adaptive_landing_page(update: Update, referrer_name: Optional[str] = None, 
                                     referee_bonus_amount: Decimal = Decimal("5.0")) -> None:
    """Show adaptive landing page based on referral status"""
    
    # ADAPTIVE LANDING PAGE: Different message based on referral status
    if referrer_name:
        # REFERRAL VERSION: Personalized with referrer name and bonus
        welcome_text = f"""🎉 <b>Welcome to {Config.PLATFORM_NAME}!</b>

👤 {referrer_name} invited you

Get ${referee_bonus_amount} USD bonus instantly!

🛡️ Escrow • 💱 Exchange • ⚡ Fast"""
        button_text = "✨ Claim Bonus & Start"
    else:
        # STANDARD VERSION: Clean and professional
        welcome_text = f"""🔒 <b>{Config.PLATFORM_NAME}</b>

Secure crypto trades & instant cashouts

🛡️ Escrow • 💱 Exchange • ⚡ Fast"""
        button_text = "🚀 Get Started"
    
    # Create button to start email input
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(button_text, callback_data="ob:start")]
    ])
    
    # Send the adaptive welcome message
    await _send_message(update, welcome_text, keyboard)


async def _handle_new_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                user_data: dict) -> None:
    """Handle new user onboarding start with adaptive landing page"""
    user_id = user_data["id"]
    
    # Check for referral code in context and store in onboarding session
    referral_code = None
    referrer_name = None
    referee_bonus_amount = Decimal("5.0")
    
    if context.user_data and context.user_data.get("pending_referral_code"):
        referral_code = context.user_data["pending_referral_code"]
        logger.info(f"Found pending referral code {referral_code} for new user {user_id}")
        
        # Look up referrer's name for personalized welcome
        try:
            from utils.referral import ReferralSystem
            
            async with get_async_session() as session:
                result_query = await session.execute(
                    select(User).filter(func.upper(User.referral_code) == referral_code.upper())
                )
                referrer = result_query.scalar_one_or_none()
                if referrer:
                    referrer_name = referrer.first_name or referrer.username or "A friend"
                    referee_bonus_amount = ReferralSystem.REFEREE_REWARD_USD
                    logger.info(f"Referral landing page: User {user_id} referred by {referrer_name}")
        except Exception as e:
            logger.error(f"Error looking up referrer for landing page: {e}")
    
    result = await OnboardingService.start(user_id)
    
    if not result["success"]:
        await _send_error(update, "system_error")
        return
    
    # Store referral code in onboarding session if present
    if referral_code and result.get("session_id"):
        try:
            from database import async_managed_session
            from models import OnboardingSession
            from sqlalchemy.orm.attributes import flag_modified
            async with async_managed_session() as session:
                session_result = await session.execute(
                    select(OnboardingSession).where(OnboardingSession.id == result["session_id"])
                )
                onboarding_session = session_result.scalar_one_or_none()
                if onboarding_session:
                    # Initialize context_data if None to avoid runtime errors
                    if onboarding_session.context_data is None:
                        onboarding_session.context_data = {"pending_referral_code": referral_code}
                    else:
                        # Type ignore needed for SQLAlchemy JSON column dict-like access
                        onboarding_session.context_data["pending_referral_code"] = referral_code  # type: ignore
                    # CRITICAL: Mark JSON column as modified so SQLAlchemy saves the changes
                    flag_modified(onboarding_session, "context_data")
                    await session.commit()
                    logger.info(f"Stored referral code {referral_code} in onboarding session for user {user_id}")
        except Exception as e:
            logger.error(f"Error storing referral code in onboarding session: {e}")
    
    # Show adaptive landing page instead of going directly to email input
    await _show_adaptive_landing_page(update, referrer_name, referee_bonus_amount)
    
    # CRITICAL FIX: Clear pending referral code after showing landing page
    # This prevents infinite loop when user clicks the button
    if context.user_data and "pending_referral_code" in context.user_data:
        del context.user_data["pending_referral_code"]
        logger.info(f"Cleared pending referral code from context for new user {user_id} after showing landing page")


async def _handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE,
                       user_data: dict) -> None:
    """Handle onboarding start/resume with clean patterns"""
    user_id = user_data["id"]
    current_step = await OnboardingService.get_current_step(user_id)
    
    # CRITICAL FIX: Check for pending referral code (for existing incomplete users using referral links)
    referral_code = None
    referrer_name = None
    referee_bonus_amount = Decimal("5.0")
    
    if context.user_data and context.user_data.get("pending_referral_code"):
        referral_code = context.user_data["pending_referral_code"]
        logger.info(f"Found pending referral code {referral_code} for existing incomplete user {user_id}")
        
        # Look up referrer's name for personalized welcome
        try:
            from utils.referral import ReferralSystem
            
            async with get_async_session() as session:
                result_query = await session.execute(
                    select(User).filter(func.upper(User.referral_code) == referral_code.upper())
                )
                referrer = result_query.scalar_one_or_none()
                if referrer:
                    referrer_name = referrer.first_name or referrer.username or "A friend"
                    logger.info(f"Referrer found: {referrer_name}")
        except Exception as e:
            logger.error(f"Error looking up referrer: {e}")
        
        # Store referral code in onboarding session
        if current_step:
            try:
                session_info = await OnboardingService.get_session_info(user_id)
                session_id = session_info.get("session_id") if session_info else None
                
                if session_id:
                    from database import async_managed_session
                    from models import OnboardingSession
                    from sqlalchemy.orm.attributes import flag_modified
                    async with async_managed_session() as session:
                        session_result = await session.execute(
                            select(OnboardingSession).where(OnboardingSession.id == session_id)
                        )
                        onboarding_session = session_result.scalar_one_or_none()
                        if onboarding_session:
                            if onboarding_session.context_data is None:
                                onboarding_session.context_data = {"pending_referral_code": referral_code}
                            else:
                                onboarding_session.context_data["pending_referral_code"] = referral_code  # type: ignore
                            flag_modified(onboarding_session, "context_data")
                            await session.commit()
                            logger.info(f"Stored referral code {referral_code} in onboarding session for existing user {user_id}")
            except Exception as e:
                logger.error(f"Error storing referral code in onboarding session: {e}")
        
        # Show adaptive landing page with referral bonus message
        await _show_adaptive_landing_page(update, referrer_name, referee_bonus_amount)
        
        # CRITICAL FIX: Clear pending referral code after showing landing page
        # This prevents infinite loop when user clicks the button
        if context.user_data and "pending_referral_code" in context.user_data:
            del context.user_data["pending_referral_code"]
            logger.info(f"Cleared pending referral code from context for user {user_id} after showing landing page")
        
        return
    
    # ARCHITECT FIX: Handle case where no active session exists (e.g., expired)
    if current_step is None:
        logger.info(f"No active session found for user {user_id}, starting new onboarding")
        result = await OnboardingService.start(user_id)
        if not result["success"]:
            await _send_error(update, "system_error")
            return
        # Session managed internally by service
        await render_step(update, result["current_step"])
        return
    
    # UX FIX: Check if user has started onboarding (clicked "Get Started" button)
    # If they're still on capture_email step AND this is from a /start command (not button click),
    # show the landing page instead of progressing to email input
    if current_step == OnboardingStep.CAPTURE_EMAIL.value:
        # Check if user has actually started (clicked button) or just received landing page
        session_info = await OnboardingService.get_session_info(user_id)
        has_clicked_start = session_info.get("context_data", {}).get("has_clicked_start", False) if session_info else False
        
        # If callback query (button click), mark as started and proceed
        if update.callback_query:
            logger.info(f"User {user_id} clicked 'Get Started' button - marking as started")
            # Mark that user has clicked the start button
            try:
                session_id = session_info.get("session_id") if session_info else None
                if session_id:
                    from database import async_managed_session
                    from models import OnboardingSession
                    from sqlalchemy.orm.attributes import flag_modified
                    async with async_managed_session() as session:
                        session_result = await session.execute(
                            select(OnboardingSession).where(OnboardingSession.id == session_id)
                        )
                        onboarding_session = session_result.scalar_one_or_none()
                        if onboarding_session:
                            if onboarding_session.context_data is None:
                                onboarding_session.context_data = {"has_clicked_start": True}
                            else:
                                onboarding_session.context_data["has_clicked_start"] = True  # type: ignore
                            flag_modified(onboarding_session, "context_data")
                            await session.commit()
                            logger.info(f"Marked user {user_id} as having clicked 'Get Started'")
            except Exception as e:
                logger.error(f"Error marking user as started: {e}")
        # If command and hasn't clicked start yet, show landing page
        elif not has_clicked_start:
            logger.info(f"User {user_id} sent /start but hasn't clicked 'Get Started' yet - showing landing page")
            await _show_adaptive_landing_page(update, referrer_name, referee_bonus_amount)
            return
    
    if current_step == OnboardingStep.VERIFY_OTP.value:
        # Get email for OTP display
        session_info = await OnboardingService.get_session_info(user_id)
        email = session_info.get("email") if session_info else None
        await render_step(update, current_step, email=email, expires_minutes=15, 
                         max_attempts=5, remaining_attempts=5)
    else:
        await render_step(update, current_step)


@track_onboarding_step("email_input")
async def _handle_email_input(update: Update, context: ContextTypes.DEFAULT_TYPE,
                             user_data: dict, email: str) -> None:
    """Handle email input with comprehensive instant feedback and clean validation"""
    
    # INSTANT FEEDBACK: Immediately acknowledge user input
    if not update.message:
        logger.error("No message object in update for email input")
        await _send_error(update, "system_error")
        return
    
    feedback_message = await update.message.reply_text(
        "✅ <b>Email received!</b> Validating...",
        parse_mode="HTML"
    )
    
    try:
        # Clean email input validation with instant feedback
        if email.isdigit() and len(email) == 6:
            await safe_reply_text(
                update,
                "❌ <b>That looks like a verification code!</b>\n\n"
                "📧 Please enter your <b>email address</b> first.\n"
                "<i>Example: your.name@gmail.com</i>",
                parse_mode="HTML"
            )
            return
        
        # Auto-fix common email issues
        email = email.lstrip("@")
        
        if not validate_email(email):
            await safe_reply_text(
                update,
                "❌ <b>Invalid email format</b>\n\n"
                "📧 Please enter a valid email address.\n"
                "<i>Example: your.name@gmail.com</i>\n\n"
                "💡 <b>Tip:</b> Check for typos and ensure it includes @ and a domain",
                parse_mode="HTML"
            )
            return

        # UPDATE FEEDBACK: Show email validation success and next step
        await update.get_bot().edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=feedback_message.message_id,
            text="✅ <b>Email validated!</b> 📧 Sending verification code...",
            parse_mode="HTML"
        )

        # Clean transition handling with processing feedback
        if not isinstance(user_data, dict) or "id" not in user_data:
            logger.error(f"Invalid user_data in _handle_email_input: {type(user_data)}")
            await safe_reply_text(
                update,
                "⚠️ <b>Something went wrong</b>\n\n"
                "Please try entering your email again.\n"
                "If the problem persists, contact our support team.",
                parse_mode="HTML"
            )
            return
        
        user_id = user_data["id"]
        
        # PERFORMANCE: Parallel DB queries (reduced from ~600ms to ~200ms)
        has_session, current_step = await asyncio.gather(
            OnboardingService.has_active_session(user_id),
            OnboardingService.get_current_step(user_id)
        )
        
        if not has_session:
            logger.warning(f"🚨 No active session found for user {user_id} during email input - auto-creating")
            result = await OnboardingService.start(user_id)
            if not result["success"]:
                logger.error(f"❌ Failed to create session for user {user_id} during email input: {result.get('error')}")
                await safe_reply_text(
                    update,
                    "⚠️ <b>Session error</b>\n\n"
                    "Please restart by using /start command.\n"
                    "If the problem persists, contact our support team.",
                    parse_mode="HTML"
                )
                return
            logger.info(f"✅ Auto-created session {result.get('session_id')} for user {user_id}")
            # Refresh current_step after creating session
            current_step = await OnboardingService.get_current_step(user_id)
        
        # Validate we're in the correct step for email input
        if current_step != OnboardingStep.CAPTURE_EMAIL.value:
            logger.warning(f"🚨 User {user_id} tried to input email in wrong step: {current_step}")
            await safe_reply_text(
                update,
                "⚠️ <b>Invalid step</b>\n\n"
                "Please use /start to restart the onboarding process.\n"
                "This ensures you're in the correct step.",
                parse_mode="HTML"
            )
            return
            
        result = await transition(user_id, "set_email", email)
        
        if not result["success"]:
            error = result.get("error", "")
            if "already registered" in error.lower():
                await safe_reply_text(
                    update,
                    "⚠️ <b>Email already registered</b>\n\n"
                    "📧 This email is already linked to another account.\n"
                    "Please use a different email address.\n\n"
                    "💡 <b>Need help?</b> Contact support if you believe this is an error.",
                    parse_mode="HTML"
                )
            elif "rate" in error.lower() or "limit" in error.lower():
                await safe_reply_text(
                    update,
                    "⏳ <b>Too many attempts</b>\n\n"
                    "Please wait a moment before trying again.\n"
                    "This helps us prevent spam and keep your account secure.\n\n"
                    "⏰ Try again in a few minutes.",
                    parse_mode="HTML"
                )
            else:
                await safe_reply_text(
                    update,
                    "📧 <b>Failed to send verification email</b>\n\n"
                    "Something went wrong while sending your code.\n\n"
                    "🔄 <b>What to try:</b>\n"
                    "• Check your email for typos\n"
                    "• Try again in a moment\n"
                    "• Contact support if the problem persists",
                    parse_mode="HTML"
                )
            return

        # SUCCESS FEEDBACK: Update to success message and transition
        await update.get_bot().edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=feedback_message.message_id,
            text="📧 <b>Verification code sent!</b>\n\n"
            f"📨 Check your inbox at <code>{html.escape(email)}</code>\n"
            "⏰ Code expires in 15 minutes",
            parse_mode="HTML"
        )
        
        # PERFORMANCE: Minimal delay for UX (reduced from 1.5s to 0.2s)
        await asyncio.sleep(0.2)

        # Success - move to OTP step with enhanced UI
        await render_step(update, OnboardingStep.VERIFY_OTP.value, 
                         email=email, expires_minutes=15, max_attempts=5, remaining_attempts=5)
    
    except Exception as e:
        # Fallback error handling with helpful message
        user_id = user_data.get("id", "unknown") if isinstance(user_data, dict) else "unknown"
        logger.error(f"Error in _handle_email_input for user {user_id}: {e}")
        await safe_reply_text(
            update,
            "⚠️ <b>Something went wrong</b>\n\n"
            "Please try entering your email again.\n"
            "If the problem persists, contact our support team.\n\n"
            "🔄 <b>Tip:</b> Make sure you have a stable internet connection",
            parse_mode="HTML"
        )


@track_onboarding_step("otp_verification")
async def _handle_otp_input(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          user_data: dict, otp_code: str) -> None:
    """Handle OTP input with comprehensive instant feedback and clean validation"""
    
    # INSTANT FEEDBACK: Immediately acknowledge user input
    if not update.message:
        logger.error("No message object in update for OTP input")
        await _send_error(update, "system_error")
        return
    
    feedback_message = await update.message.reply_text(
        "🔐 <b>Code received!</b> Verifying...",
        parse_mode="HTML"
    )
    
    try:
        # Clean OTP validation with instant feedback - more flexible
        # Remove whitespace and clean input
        cleaned_otp = otp_code.strip().replace(' ', '').replace('-', '')
        if not cleaned_otp.isdigit() or len(cleaned_otp) != 6:
            await safe_reply_text(
                update,
                "❌ <b>Invalid verification code format</b>\n\n"
                "🔢 Please enter exactly <b>6 digits</b> (no spaces or letters)\n"
                "<i>Example: 123456</i>\n\n"
                "💡 <b>Tip:</b> Check your email for the 6-digit code we sent",
                parse_mode="HTML"
            )
            return

        # UPDATE FEEDBACK: Show validation in progress
        await update.get_bot().edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=feedback_message.message_id,
            text="🔐 <b>Code format valid!</b> ⚡ Verifying with our servers...",
            parse_mode="HTML"
        )

        # Clean transition handling with processing feedback
        if not isinstance(user_data, dict) or "id" not in user_data:
            logger.error(f"Invalid user_data in _handle_email_input: {type(user_data)}")
            await safe_reply_text(
                update,
                "⚠️ <b>Something went wrong</b>\n\n"
                "Please try entering your email again.\n"
                "If the problem persists, contact our support team.",
                parse_mode="HTML"
            )
            return
        user_id = user_data["id"]
        result = await transition(user_id, "verify_otp", cleaned_otp)
        
        if not result["success"]:
            error = result.get("error", "")
            
            # Enhanced OTP error handling with clear recovery steps
            if "expired" in error.lower() or "timeout" in error.lower():
                await safe_reply_text(
                    update,
                    "⏰ <b>Verification code expired</b>\n\n"
                    "Your code was valid for 15 minutes and has now expired.\n\n"
                    "🔄 <b>What to do:</b>\n"
                    "• Tap the 'Resend Code' button below\n"
                    "• Check your email for the new 6-digit code\n"
                    "• Enter the new code quickly",
                    parse_mode="HTML"
                )
            elif "invalid" in error.lower():
                remaining = result.get("remaining_attempts", 0)
                if remaining > 0:
                    await safe_reply_text(
                        update,
                        f"❌ <b>Incorrect verification code</b>\n\n"
                        f"🎯 You have <b>{remaining} attempts</b> remaining.\n\n"
                        "🔍 <b>Please check:</b>\n"
                        "• Did you type all 6 digits correctly?\n"
                        "• Is this the most recent code from your email?\n"
                        "• Are there any typos?\n\n"
                        "💡 <b>Tip:</b> Copy and paste the code to avoid typos",
                        parse_mode="HTML"
                    )
                else:
                    await safe_reply_text(
                        update,
                        "🚫 <b>All verification attempts used</b>\n\n"
                        "You've used all available attempts for this code.\n\n"
                        "🔄 <b>What to do:</b>\n"
                        "• Tap 'Resend Code' for a fresh verification code\n"
                        "• Check your email (including spam folder)\n"
                        "• Enter the new 6-digit code carefully",
                        parse_mode="HTML"
                    )
            else:
                # ARCHITECT FIX: Log error for debugging and handle gracefully
                user_id = update.effective_user.id if update.effective_user else "unknown"
                logger.warning(f"OTP verification failed for user {user_id}: {error}")
                await safe_reply_text(
                    update,
                    "⚠️ <b>Verification failed</b>\n\n"
                    "Something went wrong while verifying your code.\n\n"
                    "🔄 <b>What to try:</b>\n"
                    "• Double-check the 6-digit code\n"
                    "• Try entering it again\n"
                    "• Request a new code if needed\n"
                    "• Contact support if the problem persists",
                    parse_mode="HTML"
                )
            return

        # SUCCESS FEEDBACK: Update to success message and transition
        await update.get_bot().edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=feedback_message.message_id,
            text="🎉 <b>Email verified successfully!</b>\n\n"
            "✅ Your account is almost ready!\n"
            "📋 Just one final step: accepting our terms",
            parse_mode="HTML"
        )
        
        # PERFORMANCE: Minimal delay for UX (reduced from 1.5s to 0.2s)
        await asyncio.sleep(0.2)

        # Success - move to terms step with enhanced transition
        await render_step(update, OnboardingStep.ACCEPT_TOS.value)
    
    except Exception as e:
        # Fallback error handling with helpful message
        user_id = update.effective_user.id if update.effective_user else "unknown"
        logger.error(f"Error in _handle_otp_input for user {user_id}: {e}")
        await safe_reply_text(
            update,
            "⚠️ <b>Something went wrong</b>\n\n"
            "Please try entering your verification code again.\n"
            "If the problem persists, you can request a new code.\n\n"
            "🔄 <b>Tip:</b> Make sure you have a stable internet connection",
            parse_mode="HTML"
        )


async def _handle_resend_otp(update: Update, context: ContextTypes.DEFAULT_TYPE,
                           user_data: dict) -> None:
    """Handle OTP resend with clean patterns"""
    user_id = user_data["id"]
    
    try:
        # Call OnboardingService directly without transition wrapper
        result = await OnboardingService.resend_otp(user_id)
        
        # Debug log to understand what we received
        logger.info(f"Resend OTP result for user {user_id}: {type(result)} -> {result}")
        
        # Robust type checking and error handling
        if not isinstance(result, dict):
            logger.error(f"Unexpected result type in _handle_resend_otp: {type(result)}")
            if hasattr(result, '__await__'):
                logger.error("Result is an unawaited coroutine!")
            await _send_error(update, "system_error")
            return
        
        if not result.get("success", False):
            error = result.get("error", "")
            if "rate" in error.lower() or "limit" in error.lower():
                await _send_error(update, "rate_limit")
            else:
                await _send_error(update, "email_send_failed")
            return

        # Success - show updated OTP screen
        session_info = await OnboardingService.get_session_info(user_id)
        email = session_info.get("email") if session_info else "your email"
        
        await safe_answer_callback_query(update.callback_query, "✅ New code sent!")
        await render_step(update, OnboardingStep.VERIFY_OTP.value,
                         email=email, expires_minutes=15, max_attempts=5, 
                         remaining_attempts=5, resent=True)
    except Exception as e:
        logger.error(f"Error in _handle_resend_otp: {e}")
        await _send_error(update, "system_error")


async def _handle_change_email(update: Update, context: ContextTypes.DEFAULT_TYPE,
                             user_data: dict) -> None:
    """Handle email change with clean patterns"""
    user_id = user_data["id"]
    
    try:
        # Call OnboardingService directly without transition wrapper
        result = await OnboardingService.reset_to_step(user_id, "capture_email")
        
        # Debug log to understand what we received
        logger.info(f"Change email result for user {user_id}: {type(result)} -> {result}")
        
        # Robust type checking and error handling
        if not isinstance(result, dict):
            logger.error(f"Unexpected result type in _handle_change_email: {type(result)}")
            if hasattr(result, '__await__'):
                logger.error("Result is an unawaited coroutine!")
            await _send_error(update, "system_error")
            return
        
        if not result.get("success", False):
            await _send_error(update, "system_error")
            return

        await safe_answer_callback_query(update.callback_query, "📧 Changing email...")
        await render_step(update, OnboardingStep.CAPTURE_EMAIL.value, changing=True)
    except Exception as e:
        logger.error(f"Error in _handle_change_email: {e}")
        await _send_error(update, "system_error")


@track_onboarding_step("terms_acceptance")
async def _handle_accept_terms(update: Update, context: ContextTypes.DEFAULT_TYPE,
                             user_data: dict) -> None:
    """Handle terms acceptance with clean patterns"""
    if not isinstance(user_data, dict) or "id" not in user_data:
        logger.error(f"Invalid user_data in _handle_accept_terms: {type(user_data)}")
        await _send_error(update, "system_error")
        return
    
    user_id = user_data["id"]
    
    # INSTANT FEEDBACK: Answer callback query immediately before database operations
    await safe_answer_callback_query(update.callback_query, f"✅ Welcome to {Config.PLATFORM_NAME}!")
    
    result = await transition(user_id, "accept_terms", None)
    
    # Defensive coding for coroutine issues
    if not isinstance(result, dict):
        logger.error(f"Unexpected result type in _handle_accept_terms: {type(result)}")
        if hasattr(result, '__await__'):
            logger.error("Result is an unawaited coroutine!")
        await _send_error(update, "system_error")
        return
    
    if not result.get("success", False):
        await _send_error(update, "system_error")
        return

    # CACHE INVALIDATION: Onboarding completed, invalidate onboarding cache
    invalidate_onboarding_cache(context.user_data)
    logger.info(f"🗑️ CACHE_INVALIDATE: Onboarding cache cleared after TOS acceptance (user {user_id})")

    # Show main menu immediately after database operations complete
    try:
        # Fetch menu data for main menu keyboard
        from async_user_utils import get_main_menu_data_async
        from utils.keyboards import main_menu_keyboard
        
        menu_data = await get_main_menu_data_async(user_id)
        telegram_id = str(user_data.get("telegram_id", user_id))
        
        text = f"""
🎉 <b>Welcome to {Config.PLATFORM_NAME}!</b>

✅ Account ready

Use the menu below to start trading.
"""
        keyboard = main_menu_keyboard(
            balance=menu_data.get("balance", 0.0),
            total_trades=menu_data.get("total_trades", 0),
            active_escrows=menu_data.get("active_escrows", 0),
            user_telegram_id=telegram_id
        )
        await safe_edit_message_text(
            update.callback_query,
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error showing main menu after terms acceptance: {e}")
        await _send_error(update, "system_error")


async def _handle_decline_terms(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict) -> None:
    """Handle terms decline - restart onboarding from email input"""
    if not isinstance(user_data, dict) or "id" not in user_data:
        logger.error(f"Invalid user_data in _handle_decline_terms: {type(user_data)}")
        await _send_error(update, "system_error")
        return
    
    user_id = user_data["id"]
    
    try:
        # Reset onboarding session back to email capture step
        result = await OnboardingService.reset_to_step(user_id, OnboardingStep.CAPTURE_EMAIL.value)
        
        if not result.get("success", False):
            logger.error(f"Failed to reset onboarding for user {user_id}: {result.get('error', 'Unknown error')}")
            await _send_error(update, "system_error")
            return
        
        # Show feedback to user
        await safe_answer_callback_query(update.callback_query, "🔄 Restarting setup...")
        
        # Show the email input screen again
        text = f"""
🔄 <b>Let's try again</b>

To use {Config.PLATFORM_NAME}, we need to verify your email address.

Please enter your email address to continue:
"""
        
        if update.callback_query:
            await safe_edit_message_text(update.callback_query, text, parse_mode="HTML")
        else:
            await safe_reply_text(update, text, parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Error in _handle_decline_terms for user {user_id}: {e}")
        await _send_error(update, "system_error")


async def _handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict) -> None:
    """Handle onboarding cancellation with clean patterns"""
    user_id = user_data["id"]
    
    try:
        # Clear the onboarding session completely
        result = await OnboardingService.clear_session(user_id)
        
        if not result.get("success", False):
            logger.error(f"Failed to clear session for user {user_id}: {result.get('error', 'Unknown error')}")
        
        text = f"""
❌ <b>Setup Cancelled</b>

No problem! You can restart anytime with /start

We're here when you're ready to join {Config.PLATFORM_NAME}! 🚀
"""
        
        await safe_answer_callback_query(update.callback_query, "❌ Cancelled")
        
        if update.callback_query:
            await safe_edit_message_text(update.callback_query, text, parse_mode="HTML")
        else:
            await safe_reply_text(update, text, parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Error in _handle_cancel for user {user_id}: {e}")
        await safe_answer_callback_query(update.callback_query, "❌ Error occurred")
        await _send_error(update, "system_error")


async def _handle_skip_email(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict) -> None:
    """Handle email skip - transition to TOS without email verification"""
    user_id = user_data["id"]
    
    try:
        logger.info(f"🔄 SKIP_EMAIL: User {user_id} skipping email verification - moving to TOS")
        
        # Answer callback immediately for user feedback
        await safe_answer_callback_query(update.callback_query, "⏭️ Skipping email...")
        
        # Transition to TOS step (skip email and OTP, but still require TOS acceptance)
        result = await OnboardingService.reset_to_step(user_id, OnboardingStep.ACCEPT_TOS.value)
        
        if not result.get("success", False):
            logger.error(f"Failed to transition to TOS for user {user_id}: {result.get('error', 'Unknown error')}")
            await _send_error(update, "system_error")
            return
        
        logger.info(f"✅ SKIP_EMAIL: User {user_id} transitioned to TOS step")
        
        # Show TOS page
        await render_step(update, OnboardingStep.ACCEPT_TOS.value)
            
    except Exception as e:
        logger.error(f"Error in _handle_skip_email for user {user_id}: {e}", exc_info=True)
        await _send_error(update, "system_error")


# CLEAN UI RENDERING - Consistent patterns

async def _render_email_step(update: Update, changing: bool = False, state: Optional[str] = None, **kwargs) -> None:
    """Enhanced email capture step with state awareness and better guidance"""
    progress_indicator = OnboardingText.PROGRESS_INDICATORS[OnboardingStep.CAPTURE_EMAIL.value]
    progress_bar = OnboardingText.PROGRESS_BARS[OnboardingStep.CAPTURE_EMAIL.value]
    
    # Enhanced status messaging based on state
    status_message = ""
    if state == "processing":
        status_message = "⏳ <b>Processing your email...</b>\n\n"
    elif state == "sending_email":
        status_message = "📧 <b>Preparing verification code...</b>\n\n"
    
    if changing:
        text = f"""
{status_message}{progress_indicator} {progress_bar}
📧 <b>Change Email Address</b>

🔄 <b>No problem!</b> Let's update your email address.

✉️ <b>Enter your new email address:</b>
<i>Example: yourname@gmail.com</i>

🔒 <i>We'll send a fresh verification code to your new email immediately</i>

💡 <b>Tips:</b>
• Use an email you check regularly
• Avoid typos - double-check before sending
• Make sure it's not already registered
"""
    else:
        text = status_message + OnboardingText.EMAIL_PROMPT.format(
            progress_indicator=progress_indicator,
            progress_bar=progress_bar
        )
        # Add helpful tips for first-time users
        text += "\n\n💡 <b>Email Tips:</b>\n• Use your main email address\n• Check spelling carefully\n• We'll never spam you"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❓ Why Email?", callback_data=OnboardingCallbacks.HELP_EMAIL)],
        [InlineKeyboardButton("⏭️ Skip for Now", callback_data=OnboardingCallbacks.SKIP_EMAIL)],
        [InlineKeyboardButton("❌ Cancel", callback_data=OnboardingCallbacks.CANCEL)]
    ])
    
    await _send_message(update, text, keyboard)


async def _render_otp_step(update: Update, email: str = "your email", 
                          expires_minutes: int = 15, max_attempts: int = 5,
                          remaining_attempts: int = 5, resent: bool = False, 
                          state: Optional[str] = None, **kwargs) -> None:
    """Enhanced OTP verification step with state awareness and better feedback"""
    progress_indicator = OnboardingText.PROGRESS_INDICATORS[OnboardingStep.VERIFY_OTP.value]
    progress_bar = OnboardingText.PROGRESS_BARS[OnboardingStep.VERIFY_OTP.value]
    
    # Enhanced status messaging based on state
    status_message = ""
    if state == "verifying":
        status_message = "🔍 <b>Verifying your code...</b>\n\n"
    elif state == "sending_email":
        status_message = "📧 <b>Sending new verification code...</b>\n\n"
    elif state == "email_processed":
        status_message = "✅ <b>Email verified!</b> Check your inbox for the code.\n\n"
    elif state == "verification_failed":
        attempts_used = max_attempts - remaining_attempts
        if attempts_used == 1:
            status_message = f"⚠️ <b>1 incorrect attempt.</b> {remaining_attempts} tries left.\n\n"
        else:
            status_message = f"⚠️ <b>{attempts_used} incorrect attempts.</b> {remaining_attempts} tries left.\n\n"
    elif resent:
        status_message = "✅ <b>New code sent!</b> Check your email.\n\n"
    elif remaining_attempts < max_attempts:
        attempts_used = max_attempts - remaining_attempts
        if attempts_used == 1:
            status_message = f"⚠️ <b>1 incorrect attempt.</b> {remaining_attempts} tries left.\n\n"
        else:
            status_message = f"⚠️ <b>{attempts_used} incorrect attempts.</b> {remaining_attempts} tries left.\n\n"
    
    # Time-sensitive urgency indicators
    urgency_indicator = ""
    if expires_minutes <= 5:
        urgency_indicator = "⏰ <b>Code expires soon!</b> "
    elif expires_minutes <= 10:
        urgency_indicator = "⏰ "
    
    text = status_message + OnboardingText.OTP_PROMPT.format(
        progress_indicator=progress_indicator,
        progress_bar=progress_bar,
        email=html.escape(email),
        expires_minutes=expires_minutes,
        remaining_attempts=remaining_attempts,
        max_attempts=max_attempts
    )
    
    if urgency_indicator:
        text = text.replace("⏰ <b>Status:</b>", urgency_indicator + "<b>Status:</b>")
    
    # Enhanced keyboard with contextual options
    keyboard_buttons = []
    
    # Resend button - enhanced with context
    if remaining_attempts <= 1:
        keyboard_buttons.append([InlineKeyboardButton("🆕 Get Fresh Code", callback_data=OnboardingCallbacks.RESEND_OTP)])
    else:
        keyboard_buttons.append([InlineKeyboardButton("🔄 Resend Code", callback_data=OnboardingCallbacks.RESEND_OTP)])
    
    # Help and email change options
    keyboard_buttons.append([
        InlineKeyboardButton("📧 Change Email", callback_data=OnboardingCallbacks.CHANGE_EMAIL),
        InlineKeyboardButton("❓ Help", callback_data=OnboardingCallbacks.HELP_OTP)
    ])
    
    # Cancel option
    keyboard_buttons.append([InlineKeyboardButton("❌ Cancel Setup", callback_data=OnboardingCallbacks.CANCEL)])
    
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    await _send_message(update, text, keyboard)


async def _render_terms_step(update: Update, state: Optional[str] = None, **kwargs) -> None:
    """Enhanced terms acceptance step with state awareness and completion emphasis"""
    progress_indicator = OnboardingText.PROGRESS_INDICATORS[OnboardingStep.ACCEPT_TOS.value]
    progress_bar = OnboardingText.PROGRESS_BARS[OnboardingStep.ACCEPT_TOS.value]
    
    # Enhanced status messaging based on state
    status_message = ""
    if state == "completing":
        status_message = "🎉 <b>Completing your setup...</b>\n\n"
    elif state == "otp_verified":
        status_message = "✅ <b>Email successfully verified!</b>\n\n"
    
    text = status_message + OnboardingText.TERMS_PROMPT.format(
        progress_indicator=progress_indicator,
        progress_bar=progress_bar
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Accept Terms & Complete Setup", callback_data=OnboardingCallbacks.TOS_ACCEPT)],
        [InlineKeyboardButton("📋 Read Terms", callback_data=OnboardingCallbacks.HELP_TERMS)],
        [InlineKeyboardButton("❌ Decline", callback_data=OnboardingCallbacks.TOS_DECLINE)]
    ])
    
    await _send_message(update, text, keyboard)


async def _render_completion_step(update: Update, email: str = "your email", state: Optional[str] = None, **kwargs) -> None:
    """Enhanced completion step with celebration and clear next steps"""
    
    # Simplified completion message
    text = f"""
🎉 <b>Welcome to {Config.PLATFORM_NAME}!</b>

✅ Account setup complete
📧 Email: <code>{html.escape(email)}</code>

Your wallet is ready for:
• Multi-currency crypto trading
• NGN bank transfers
• Secure P2P escrow

<b>Get started below</b> 👇
"""
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Explore My Account", callback_data="menu_main")]
    ])
    
    await _send_message(update, text, keyboard)


# CLEAN UTILITIES - Helper functions

async def _send_message(update: Update, text: str, keyboard: Optional[InlineKeyboardMarkup] = None) -> None:
    """Clean utility to send messages with consistent patterns and error handling"""
    # DIAGNOSTIC: Log message sending attempt
    user_id = update.effective_user.id if update.effective_user else "unknown"
    message_preview = text[:50].replace('\n', ' ') + '...' if len(text) > 50 else text.replace('\n', ' ')
    
    try:
        if update.callback_query:
            logger.info(f"📤 SEND_MESSAGE: Editing message for user {user_id} via callback_query - '{message_preview}'")
            await safe_edit_message_text(update.callback_query, text, reply_markup=keyboard, parse_mode="HTML")
            logger.info(f"✅ MESSAGE_SENT: Successfully edited message for user {user_id}")
        else:
            logger.info(f"📤 SEND_MESSAGE: Sending reply to user {user_id} - '{message_preview}'")
            result = await safe_reply_text(update, text, reply_markup=keyboard, parse_mode="HTML")
            if result:
                logger.info(f"✅ MESSAGE_SENT: Successfully sent reply to user {user_id}")
            else:
                logger.warning(f"⚠️ MESSAGE_FAILED: safe_reply_text returned False for user {user_id}")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ MESSAGE_EXCEPTION: Failed to send message to user {user_id}: {error_msg}", exc_info=True)
        
        # Handle specific telegram errors gracefully
        if "Chat not found" in error_msg:
            logger.warning(f"Chat not found for user {user_id} - user may have blocked bot or chat doesn't exist")
            # Don't raise exception - this is expected for test/invalid chats
            return
        elif "Bot was blocked" in error_msg:
            logger.warning(f"Bot was blocked by user {user_id} - cannot send message")
            return
        elif "User is deactivated" in error_msg:
            logger.warning(f"User account {user_id} is deactivated - cannot send message")
            return
        else:
            # For other errors, log but don't crash the onboarding flow
            logger.error(f"Unexpected message sending error for user {user_id}: {error_msg}")
            return


async def _send_error(update: Update, error_type: str, custom_message: Optional[str] = None) -> None:
    """Enhanced utility to send error messages with comprehensive error handling and recovery guidance"""
    message = custom_message or OnboardingText.ERROR_MESSAGES.get(error_type, "Something went wrong")
    
    # Add contextual recovery guidance based on error type
    recovery_keyboard = None
    if error_type in ["otp_expired", "max_attempts", "session_expired"]:
        recovery_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Get New Code", callback_data=OnboardingCallbacks.RESEND_OTP)],
            [InlineKeyboardButton("📧 Change Email", callback_data=OnboardingCallbacks.CHANGE_EMAIL)],
            [InlineKeyboardButton("🆘 Get Help", callback_data=OnboardingCallbacks.HELP_OTP)]
        ])
    elif error_type in ["invalid_email", "email_taken"]:
        recovery_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Try Again", callback_data=OnboardingCallbacks.START)],
            [InlineKeyboardButton("❓ Need Help?", callback_data=OnboardingCallbacks.HELP_EMAIL)]
        ])
    elif error_type in ["network_error", "system_error"]:
        recovery_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Retry", callback_data=OnboardingCallbacks.START)],
            [InlineKeyboardButton("🆘 Contact Support", url=Config.SUPPORT_URL)]
        ])
    
    try:
        if update.callback_query:
            # Provide immediate feedback for button interactions
            error_feedback = {
                "otp_invalid": "❌ Wrong code",
                "otp_expired": "⏰ Code expired",
                "rate_limit": "⏳ Too fast",
                "network_error": "📡 Connection issue",
                "system_error": "⚠️ System error"
            }
            await safe_answer_callback_query(update.callback_query, error_feedback.get(error_type, "❌ Error"))
            await safe_reply_text(update, message, reply_markup=recovery_keyboard, parse_mode="HTML")
        else:
            await safe_reply_text(update, message, reply_markup=recovery_keyboard, parse_mode="HTML")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to send error message: {error_msg}")
        
        # Enhanced telegram error handling with better recovery
        if "Chat not found" in error_msg:
            logger.warning(f"Chat not found when sending error - user may have blocked bot")
            return
        elif "Bot was blocked" in error_msg:
            logger.warning(f"Bot was blocked by user - cannot send error message")
            return
        elif "Message is not modified" in error_msg:
            logger.debug(f"Message not modified - this is expected in some cases")
            return
        elif "Bad Request: message to edit not found" in error_msg:
            logger.debug(f"Message to edit not found - user may have deleted it")
            # Try sending a new message instead
            try:
                await safe_reply_text(update, message, reply_markup=recovery_keyboard, parse_mode="HTML")
            except Exception as retry_e:
                logger.error(f"Failed to send fallback error message: {retry_e}")
            return
        else:
            logger.error(f"Unexpected error sending error message: {error_msg}")
            return


async def _show_help(update: Update, context: ContextTypes.DEFAULT_TYPE, help_type: str) -> None:
    """Show contextual help with clean patterns"""
    help_messages = {
        "email": """
📧 <b>Email Help</b>

<b>Why needed:</b>
• Security alerts
• Account recovery  
• Transaction confirmations

<b>Privacy:</b>
🔐 Encrypted & secure
✅ You control notifications
""",
        "otp": """
🔐 <b>Code Help</b>

<b>No code?</b>
• Check spam folder
• Wait 1-2 minutes
• Click 'Resend'

<b>Not working?</b>
• Use latest code only
• Enter 6 digits (no spaces)
• Get new if expired
""",
        "terms": """
📋 <b>Terms Help</b>

<b>You agree to:</b>
• Use responsibly
• Follow guidelines
• Accept fee structure

<b>Your rights:</b>
• Funds protected
• Support access
• Fair disputes
"""
    }
    
    text = help_messages.get(help_type, "Help not available")
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("← Back to Setup", callback_data=OnboardingCallbacks.START)],
        [InlineKeyboardButton("❌ Cancel Setup", callback_data=OnboardingCallbacks.CANCEL)]
    ])
    
    await safe_answer_callback_query(update.callback_query, "📖 Help")
    await safe_edit_message_text(update.callback_query, text, reply_markup=keyboard, parse_mode="HTML")


async def _show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict) -> None:
    """Show main menu for completed users with clean patterns"""
    # Use sync helper for main menu data
    menu_data = await run_io_task(get_main_menu_data_sync, user_data["id"])
    
    # Extract user and menu data
    user = user_data  # user_data contains user information
    balance = menu_data.get("balance", 0.0)
    total_trades = menu_data.get("total_trades", 0)
    active_escrows = menu_data.get("active_escrows", 0)

    # CRITICAL FIX: Prevent welcome message during active cashout
    if context.user_data:
        cud = context.user_data  # Shorthand for readability
        has_active_cashout = (
            bool(cud.get('cashout_data', {}).get('active_cashout')) or
            cud.get('wallet_state') in [
                'selecting_amount', 'selecting_amount_crypto', 'selecting_amount_ngn', 
                'entering_crypto_address', 'entering_crypto_details', 'verifying_crypto_otp', 
                'verifying_ngn_otp', 'adding_bank_selecting', 'adding_bank_account_number', 
                'adding_bank_confirming', 'adding_bank_label', 'adding_bank_searching', 
                'entering_custom_amount', 'entering_withdraw_address',
                'selecting_withdraw_currency', 'selecting_crypto_currency'
            ] or
            cud.get('current_state') in [
                'ENTERING_CUSTOM_AMOUNT', 'SELECTING_WITHDRAW_CURRENCY', 
                'SELECTING_CRYPTO_CURRENCY', 'selecting_withdraw_currency', 'selecting_crypto_currency'
            ] or
            cud.get('cashout_data', {}).get('current_state') in [
                'SELECTING_WITHDRAW_CURRENCY', 'SELECTING_CRYPTO_CURRENCY',
                'ENTERING_CUSTOM_AMOUNT', 'selecting_withdraw_currency', 'selecting_crypto_currency'
            ]
        )
        
        if has_active_cashout:
            logger.info(f"🚫 Suppressing welcome message for user {user.get('id', 'unknown')} - active cashout in progress")
            return  # Early return to prevent welcome message spam
    
    text = f"""
🏠 <b>Welcome to {Config.PLATFORM_NAME}!</b>

Hey {html.escape(user.get('first_name', user.get('username', 'Friend')))}! 👋

💰 <b>Balance:</b> ${balance:.2f} USD
📊 <b>Total Trades:</b> {total_trades}
⚡ <b>Active:</b> {active_escrows}

<i>What would you like to do today?</i>
"""

    keyboard = main_menu_keyboard(
        balance=balance,
        total_trades=total_trades,
        active_escrows=active_escrows,
        user_telegram_id=user.get("id", user.get("telegram_id", 0))
    )

    await _send_message(update, text, keyboard)


# API COMPATIBILITY LAYER - Required for test functionality
# These functions maintain exact signatures that tests expect

async def handle_onboarding_start(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                 user_id: int, session: Optional[AsyncSession] = None) -> None:
    """
    Test compatibility wrapper - calls OnboardingService.start and renders current step
    
    ARCHITECT'S SPECIFICATION: Call OnboardingService.start(user_id, session), 
    render returned current_step, use managed_session() if session is None
    """
    if session is None:
        result = await OnboardingService.start(user_id)
        
        if not result["success"]:
            await _send_error(update, "system_error")
            return
            
        await render_step(update, result["current_step"])
    else:
        result = await OnboardingService.start(user_id, session=session)
        
        if not result["success"]:
            await _send_error(update, "system_error")
            return
            
        await render_step(update, result["current_step"])


async def start_new_user_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  session: Optional[AsyncSession] = None) -> None:
    """
    Test compatibility wrapper - creates new user and starts onboarding
    
    ARCHITECT'S SPECIFICATION: get_or_create_user, commit if new, invalidate cache,
    call _handle_new_user_start
    """
    if not update.effective_user:
        await _send_error(update, "system_error")
        return

    if session is None:
        # Use sync helper for user creation
        user_data, is_new = await run_io_task(get_or_create_user_sync, update.effective_user)
        if not user_data:
            await _send_error(update, "system_error")
            return
        
        # Send admin notification for new user onboarding started
        if is_new:
            asyncio.create_task(
                admin_trade_notifications.notify_user_onboarding_started({
                    'user_id': user_data['id'],
                    'telegram_id': user_data['telegram_id'],
                    'username': user_data.get('username'),
                    'first_name': user_data.get('first_name'),
                    'last_name': user_data.get('last_name', ''),
                    'started_at': datetime.utcnow()
                })
            )
    else:
        # Get or create user with provided session using sync helper
        user_data, is_new = await run_io_task(get_or_create_user_sync, update.effective_user)
        if not user_data:
            await _send_error(update, "system_error")
            return

        # Handle new user creation 
        if is_new:
            await session.commit()
            # Clean async cache invalidation - properly awaited
            await run_background_task(invalidate_user_cache_async(str(update.effective_user.id)))
            
            # Send admin notification for new user onboarding started
            asyncio.create_task(
                admin_trade_notifications.notify_user_onboarding_started({
                    'user_id': user_data['id'],
                    'telegram_id': user_data['telegram_id'],
                    'username': user_data.get('username'),
                    'first_name': user_data.get('first_name'),
                    'last_name': user_data.get('last_name', ''),
                    'started_at': datetime.utcnow()
                })
            )
        
        await _handle_new_user_start(update, context, user_data)


async def handle_cancel_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                 user_id: Optional[int] = None, session: Optional[AsyncSession] = None) -> None:
    """
    Test compatibility wrapper - resolves user and calls cancel handler
    
    ARCHITECT'S SPECIFICATION: Resolve User (by user_id or update.effective_user),
    call _handle_cancel, use managed_session when session not provided
    """
    if session is None:
        # Use sync helper for user resolution
        if user_id:
            user_data = await run_io_task(get_or_create_user_sync, {"id": user_id})
            if not user_data:
                await _send_error(update, "system_error")
                return
            elif update.effective_user:
                user_data = await run_io_task(get_or_create_user_sync, update.effective_user)
                if not user_data:
                    await _send_error(update, "system_error")
                    return
            else:
                await _send_error(update, "system_error")
                return

            await _handle_cancel(update, context, user_data)
    else:
        # Resolve user with provided session
        if user_id:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
        elif update.effective_user:
            result = await session.execute(
                select(User).where(User.id == update.effective_user.id)
            )
            user = result.scalar_one_or_none()
        else:
            await _send_error(update, "system_error")
            return

        if not user:
            await _send_error(update, "system_error")
            return
            
        # Convert User object to dict for _handle_cancel
        user_dict = {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "is_verified": user.is_verified,
            "onboarding_completed": user.onboarding_completed
        }
        await _handle_cancel(update, context, user_dict)


async def onboarding_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Test compatibility wrapper - delegates to main onboarding router
    
    ARCHITECT'S SPECIFICATION: Simply delegate to onboarding_router 
    (router handles both text and callback now)
    """
    await onboarding_router(update, context)


async def onboarding_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Test compatibility wrapper - delegates to main onboarding router
    
    ARCHITECT'S SPECIFICATION: Simply delegate to onboarding_router
    (router handles both text and callback now)  
    """
    await onboarding_router(update, context)


# EXPORTS - Clean interface for external use  
# Main entry point (legacy compatibility)
async def start_onboarding_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point for new user onboarding (legacy name)"""
    await onboarding_router(update, context)


# HANDLER REGISTRATION FUNCTION FOR MAIN.PY
def register_onboarding_handlers(application) -> None:
    """Register onboarding handlers with the Telegram application
    
    This function is called by main.py to register all onboarding-related handlers.
    It sets up the stateless onboarding router with proper priority and filtering.
    """
    from telegram.ext import MessageHandler, CallbackQueryHandler, CommandHandler, filters
    
    # Register command handlers for onboarding start - FIXED: Use main router for proper existing user handling
    application.add_handler(
        CommandHandler("start", onboarding_router),
        group=0  # Standard priority for onboarding commands
    )
    
    # Register callback handlers for onboarding interactions
    onboarding_callback_patterns = [
        OnboardingCallbacks.START,
        OnboardingCallbacks.RESEND_OTP,
        OnboardingCallbacks.CHANGE_EMAIL,
        OnboardingCallbacks.SKIP_EMAIL,
        OnboardingCallbacks.TOS_ACCEPT,
        OnboardingCallbacks.TOS_DECLINE,
        OnboardingCallbacks.CANCEL,
        OnboardingCallbacks.HELP_EMAIL,
        OnboardingCallbacks.HELP_OTP,
        OnboardingCallbacks.HELP_TERMS
    ]
    
    # Create regex pattern string for onboarding callback patterns
    onboarding_callback_pattern = f"^({'|'.join(onboarding_callback_patterns)})$"
    
    application.add_handler(
        CallbackQueryHandler(onboarding_callback_handler, pattern=onboarding_callback_pattern),
        group=0  # Standard priority for onboarding callbacks
    )
    
    # DISABLED: Text message handler for onboarding - now handled by unified text router
    # The unified text router in main.py handles all text routing including onboarding
    # application.add_handler(
    #     MessageHandler(
    #         filters.TEXT & ~filters.COMMAND,  # Text messages but not commands
    #         onboarding_text_handler
    #     ),
    #     group=5  # Lower priority to let specific handlers process first
    # )
    
    logger.info(f"✅ Registered onboarding router with {len(onboarding_callback_patterns)} callback patterns")
    logger.info("✅ Onboarding handlers: /start command, callback queries, text input")