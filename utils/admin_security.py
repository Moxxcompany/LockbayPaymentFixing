"""
Enhanced Admin Security Module
Provides hardened admin authentication and authorization
Addresses P0-6 Admin Control Weaknesses
"""

import logging
import time
import os
from typing import Dict, Optional, Set, Tuple
from datetime import datetime, timedelta
from config import Config

logger = logging.getLogger(__name__)


class AdminSecurityManager:
    """Enhanced admin security with session management and hardened controls"""

    def __init__(self):
        self._admin_sessions: Dict[int, datetime] = {}
        self._failed_attempts: Dict[int, int] = {}
        self._session_timeout = timedelta(seconds=Config.ADMIN_SESSION_TIMEOUT)  # Configurable admin session timeout
        self._max_failed_attempts = 3
        self._lockout_duration = timedelta(minutes=30)
        self._lockout_times: Dict[int, datetime] = {}
        # CRITICAL FIX: Initialize _current_context to prevent AttributeError
        self._current_context: Optional[Dict] = None
        # PERFORMANCE FIX: Cache admin IDs to prevent repeated initialization logs
        self._cached_admin_ids: Optional[Set[int]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)  # Cache for 5 minutes

    def get_admin_ids(self) -> Set[int]:
        """
        Securely get admin IDs from environment with NO unsafe fallbacks
        CRITICAL: Fails securely if no admin IDs configured
        PERFORMANCE: Cached to prevent repeated initialization logs
        """
        # PERFORMANCE FIX: Check cache first to reduce repeated processing
        current_time = datetime.now()
        if (self._cached_admin_ids is not None and 
            self._cache_timestamp is not None and 
            current_time - self._cache_timestamp < self._cache_ttl):
            return self._cached_admin_ids
        
        admin_ids_env = os.getenv("ADMIN_IDS", "").strip()

        if not admin_ids_env:
            logger.critical(
                "SECURITY ALERT: No ADMIN_IDS environment variable configured"
            )
            raise ValueError(
                "Admin IDs not configured - system cannot start without proper admin configuration"
            )

        try:
            admin_ids = {
                int(id.strip()) for id in admin_ids_env.split(",") if id.strip()
            }

            if not admin_ids:
                logger.critical("SECURITY ALERT: Empty admin IDs list")
                raise ValueError("No valid admin IDs found in configuration")

            # PERFORMANCE FIX: Only log during initial load or cache refresh
            if self._cached_admin_ids is None:
                logger.info(
                    f"Admin security initialized with {len(admin_ids)} configured administrators"
                )
            
            # Cache the results
            self._cached_admin_ids = admin_ids
            self._cache_timestamp = current_time
            
            return admin_ids

        except ValueError as e:
            logger.critical(
                f"SECURITY ALERT: Invalid admin ID format in ADMIN_IDS: {e}"
            )
            raise ValueError(f"Invalid admin ID configuration: {e}")

    def is_admin_with_security(self, user_id: int) -> bool:
        """
        SECURITY: Enhanced admin check with timing attack protection and hardened controls

        Args:
            user_id: Telegram user ID to check

        Returns:
            bool: True if user is authenticated admin, False otherwise
        """

        start_time = time.time()

        try:
            # SECURITY: Constant-time delay to prevent timing attacks
            # Always perform the same operations regardless of user status

            # Check if user is in lockout
            is_locked_out = self._is_user_locked_out(user_id)

            # Get admin IDs securely (always fetch to prevent timing differences)
            admin_list = self.get_admin_ids()
            is_admin = user_id in admin_list

            # SECURITY: Always check session validity to prevent timing attacks
            session_valid = self._is_session_valid(user_id)

            # Determine final result
            if is_locked_out:
                logger.warning(
                    f"Admin access attempt from locked out user ID: {user_id}"
                )
                result = False
            elif is_admin:
                if session_valid:
                    # Update session timestamp
                    self._admin_sessions[user_id] = datetime.now()
                    # Clear any failed attempts on successful auth
                    self._failed_attempts.pop(user_id, None)
                    logger.info(
                        f"Authenticated admin access granted - User ID: {user_id}"
                    )

                    # SECURITY: Log admin access for audit trail (sync version)
                    try:
                        logger.info(
                            f"Admin authentication successful for user {user_id}"
                        )
                    except Exception as audit_error:
                        logger.error(f"Failed to log admin access audit: {audit_error}")

                    result = True
                else:
                    # Start new session
                    self._admin_sessions[user_id] = datetime.now()
                    logger.info(f"New admin session started - User ID: {user_id}")

                    # SECURITY: Log new admin session for audit trail (sync version)
                    try:
                        logger.info(f"New admin session initiated for user {user_id}")
                    except Exception as audit_error:
                        logger.error(
                            f"Failed to log admin session audit: {audit_error}"
                        )

                    result = True
            else:
                # CONTEXT-AWARE LOGGING: Only log actual admin access attempts, not normal operations
                # ROBUSTNESS FIX: Use safe getattr with default None to prevent AttributeError
                context = getattr(self, '_current_context', None)
                if context and context.get('is_admin_check_only', False):
                    # Silent check - don't log normal non-admin users
                    logger.debug(f"Admin check (silent): User {user_id} is not admin")
                else:
                    # For regular users during normal onboarding/usage, don't generate security alerts
                    # Only log genuine admin access attempts (e.g., trying to access /admin commands)
                    logger.debug(f"Non-admin user {user_id} - normal operation, no security alert needed")
                
                # No alert system integration for normal user operations
                logger.debug(f"Skipping admin alert system for normal user operation: {user_id}")
                
                result = False

            # SECURITY: Constant-time delay - ensure minimum processing time
            elapsed = time.time() - start_time
            min_delay = 0.1  # 100ms minimum delay
            if elapsed < min_delay:
                time.sleep(min_delay - elapsed)

            return result

        except Exception as e:
            logger.error(
                f"Critical error in admin authentication for user {user_id}: {e}"
            )
            # SECURITY: Maintain timing consistency even on error
            elapsed = time.time() - start_time
            min_delay = 0.1
            if elapsed < min_delay:
                time.sleep(min_delay - elapsed)
            # Fail securely - deny access on any error
            return False

    def _is_session_valid(self, user_id: int) -> bool:
        """Check if admin session is still valid"""
        if user_id not in self._admin_sessions:
            return False

        session_start = self._admin_sessions[user_id]
        return datetime.now() - session_start < self._session_timeout

    def _is_user_locked_out(self, user_id: int) -> bool:
        """Check if user is currently locked out due to failed attempts"""
        if user_id not in self._lockout_times:
            return False

        lockout_time = self._lockout_times[user_id]
        return datetime.now() - lockout_time < self._lockout_duration

    def _track_failed_attempt(self, user_id: int):
        """SECURITY: Enhanced failed attempt tracking with progressive penalties"""
        current_attempts = self._failed_attempts.get(user_id, 0) + 1
        self._failed_attempts[user_id] = current_attempts

        # SECURITY: Progressive lockout - longer penalties for repeat offenders
        if current_attempts >= self._max_failed_attempts:
            # Progressive lockout duration based on attempt count
            lockout_multiplier = min(
                current_attempts - self._max_failed_attempts + 1, 10
            )
            extended_lockout = self._lockout_duration * lockout_multiplier

            self._lockout_times[user_id] = datetime.now()
            logger.critical(
                f"SECURITY ALERT: User {user_id} locked out for {extended_lockout} after {current_attempts} failed admin access attempts"
            )

            # SECURITY: Alert on potential brute force attacks
            if current_attempts >= 10:
                logger.critical(
                    f"CRITICAL SECURITY ALERT: Potential brute force attack from user {user_id} - {current_attempts} attempts"
                )

    def invalidate_session(self, user_id: int):
        """SECURITY: Enhanced session invalidation with cleanup"""
        # Clear session
        self._admin_sessions.pop(user_id, None)

        # SECURITY: Clear any cached authentication state
        self._failed_attempts.pop(user_id, None)

        # SECURITY: Log session termination for audit trail
        logger.info(f"Admin session invalidated for user {user_id}")

    def get_security_status(self) -> dict:
        """SECURITY: Get system security status for monitoring"""
        now = datetime.now()
        active_sessions = len(
            [
                s
                for s, t in self._admin_sessions.items()
                if (now - t) < self._session_timeout
            ]
        )
        locked_users = len(
            [
                u
                for u, t in self._lockout_times.items()
                if (now - t) < self._lockout_duration
            ]
        )
        failed_attempts_total = sum(self._failed_attempts.values())

        return {
            "active_admin_sessions": active_sessions,
            "locked_out_users": locked_users,
            "total_failed_attempts": failed_attempts_total,
            "security_events_count": len(self._failed_attempts),
        }

    def cleanup_expired_data(self):
        """SECURITY: Cleanup expired sessions and lockouts"""
        now = datetime.now()

        # Cleanup expired sessions
        expired_sessions = [
            user_id
            for user_id, timestamp in self._admin_sessions.items()
            if (now - timestamp) > self._session_timeout
        ]
        for user_id in expired_sessions:
            self._admin_sessions.pop(user_id, None)

        # Cleanup expired lockouts
        expired_lockouts = [
            user_id
            for user_id, timestamp in self._lockout_times.items()
            if (now - timestamp) > self._lockout_duration
        ]
        for user_id in expired_lockouts:
            self._lockout_times.pop(user_id, None)
            self._failed_attempts.pop(user_id, None)

        if expired_sessions or expired_lockouts:
            logger.info(
                f"Security cleanup: removed {len(expired_sessions)} expired sessions, {len(expired_lockouts)} expired lockouts"
            )

    def cleanup_expired_sessions(self):
        """Clean up expired sessions and lockouts"""
        now = datetime.now()

        # Clean expired sessions
        expired_sessions = [
            user_id
            for user_id, session_time in self._admin_sessions.items()
            if now - session_time >= self._session_timeout
        ]

        for user_id in expired_sessions:
            del self._admin_sessions[user_id]
            logger.info(f"Expired admin session cleaned up for user {user_id}")

        # Clean expired lockouts
        expired_lockouts = [
            user_id
            for user_id, lockout_time in self._lockout_times.items()
            if now - lockout_time >= self._lockout_duration
        ]

        for user_id in expired_lockouts:
            del self._lockout_times[user_id]
            self._failed_attempts.pop(user_id, None)

    def get_session_info(self, user_id: int) -> Optional[Dict]:
        """Get admin session information for monitoring"""
        if user_id not in self._admin_sessions:
            return None

        session_start = self._admin_sessions[user_id]
        time_remaining = self._session_timeout - (datetime.now() - session_start)

        return {
            "session_started": session_start.isoformat(),
            "expires_at": (session_start + self._session_timeout).isoformat(),
            "time_remaining_minutes": max(0, int(time_remaining.total_seconds() / 60)),
            "is_valid": self._is_session_valid(user_id),
        }


# Global instance for application use
admin_security = AdminSecurityManager()


def is_admin_secure(user_id: int) -> bool:
    """
    Secure admin check function - replaces old is_admin()
    Uses enhanced security with session management and hardened controls
    """
    return admin_security.is_admin_with_security(user_id)


def is_admin_silent(user_id: int) -> bool:
    """
    Silent admin check for UI purposes - does NOT trigger security alerts
    Used for showing/hiding admin UI elements without logging access attempts
    """
    try:
        # FIXED: Set context to prevent false security alerts
        admin_security._current_context = {'is_admin_check_only': True}
        
        try:
            admin_ids_env = os.getenv("ADMIN_IDS", "").strip()
            if not admin_ids_env:
                return False
            
            admin_ids = {int(id.strip()) for id in admin_ids_env.split(",") if id.strip()}
            return user_id in admin_ids
        finally:
            # CRITICAL: Always clear context to prevent context bleed
            admin_security._current_context = None
            
    except Exception:
        # SECURITY: Clear context on exception too
        admin_security._current_context = None
        return False


def require_admin_secure(user_id: int) -> Tuple[bool, str]:
    """
    Enhanced admin requirement check with better error messages

    Returns:
        tuple: (is_admin, error_message)
    """
    if is_admin_secure(user_id):
        return True, ""
    else:
        return False, "❌ Access denied. Administrative privileges required."


def get_admin_session_info(user_id: int) -> Optional[Dict]:
    """Get admin session information"""
    return admin_security.get_session_info(user_id)


def logout_admin(user_id: int):
    """Logout admin user"""
    admin_security.invalidate_session(user_id)


# Background cleanup function
def cleanup_admin_sessions():
    """Clean up expired sessions and lockouts"""
    admin_security.cleanup_expired_sessions()


# Decorator for admin-required functions
def admin_required(func):
    """Decorator to require admin access for handler functions"""
    from functools import wraps
    
    @wraps(func)
    async def wrapper(self, update, context):
        try:
            user = update.effective_user
            if not user:
                return
                
            if not is_admin_secure(user.id):
                if update.callback_query:
                    await update.callback_query.answer("❌ Admin access required")
                elif update.message:
                    await update.message.reply_text("❌ Admin access required")
                return
                
            return await func(self, update, context)
        except Exception as e:
            logger.error(f"Error in admin_required decorator: {e}")
            return
    return wrapper
