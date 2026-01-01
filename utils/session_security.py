"""
SECURITY: Enhanced Session Security System
Provides encrypted session storage and secure session management
"""

import json
import logging
import hashlib
import hmac
import secrets
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import base64
import os

logger = logging.getLogger(__name__)


class SessionSecurityManager:
    """SECURITY: Enhanced session security with encryption and integrity protection"""

    def __init__(self):
        self._encryption_key = self._get_or_generate_encryption_key()
        self._fernet = Fernet(self._encryption_key)
        self._session_hmac_key = self._get_session_hmac_key()

    def _get_or_generate_encryption_key(self) -> bytes:
        """SECURITY: Get or generate encryption key for session data"""
        # Try to get from environment first
        key_env = os.getenv("SESSION_ENCRYPTION_KEY", "").strip()

        if key_env:
            try:
                # Decode base64 key from environment
                return base64.urlsafe_b64decode(key_env.encode())
            except Exception as e:
                logger.warning(f"Invalid session encryption key in environment: {e}")

        # Generate new key if not found (for development)
        logger.warning(
            "Generating new session encryption key - sessions won't persist across restarts"
        )
        return Fernet.generate_key()

    def _get_session_hmac_key(self) -> bytes:
        """SECURITY: Get HMAC key for session integrity verification"""
        hmac_key = os.getenv("SESSION_HMAC_KEY", "").strip()

        if hmac_key:
            return hmac_key.encode()

        # Generate random key for development
        logger.warning(
            "Generating random session HMAC key - sessions won't persist across restarts"
        )
        return secrets.token_bytes(32)

    def encrypt_session_data(self, data: Dict[str, Any]) -> str:
        """SECURITY: Encrypt session data with integrity protection"""
        try:
            # Serialize data
            json_data = json.dumps(data, default=str)

            # Encrypt data
            encrypted_data = self._fernet.encrypt(json_data.encode())

            # Generate HMAC for integrity verification
            hmac_digest = hmac.new(
                self._session_hmac_key, encrypted_data, hashlib.sha256
            ).hexdigest()

            # Combine encrypted data and HMAC
            secured_data = {
                "data": base64.urlsafe_b64encode(encrypted_data).decode(),
                "hmac": hmac_digest,
                "timestamp": datetime.utcnow().isoformat(),
            }

            return base64.urlsafe_b64encode(json.dumps(secured_data).encode()).decode()

        except Exception as e:
            logger.error(f"Failed to encrypt session data: {e}")
            raise

    def decrypt_session_data(
        self, encrypted_data: str, max_age_hours: int = 24
    ) -> Optional[Dict[str, Any]]:
        """SECURITY: Decrypt and verify session data integrity"""
        try:
            # Decode base64
            secured_data = json.loads(
                base64.urlsafe_b64decode(encrypted_data.encode()).decode()
            )

            # Verify structure
            if not all(key in secured_data for key in ["data", "hmac", "timestamp"]):
                logger.warning("Invalid session data structure")
                return None

            # Check timestamp (prevent replay attacks)
            timestamp = datetime.fromisoformat(secured_data["timestamp"])
            if datetime.utcnow() - timestamp > timedelta(hours=max_age_hours):
                logger.warning("Session data expired")
                return None

            # Verify HMAC integrity
            encrypted_bytes = base64.urlsafe_b64decode(secured_data["data"].encode())
            expected_hmac = hmac.new(
                self._session_hmac_key, encrypted_bytes, hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(expected_hmac, secured_data["hmac"]):
                logger.warning("Session data integrity verification failed")
                return None

            # Decrypt data
            decrypted_data = self._fernet.decrypt(encrypted_bytes)
            return json.loads(decrypted_data.decode())

        except Exception as e:
            logger.error(f"Failed to decrypt session data: {e}")
            return None

    def generate_secure_session_token(self, user_id: int) -> str:
        """SECURITY: Generate cryptographically secure session token"""
        # Generate random token
        random_bytes = secrets.token_bytes(32)

        # Add user context and timestamp
        context = {
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "random": base64.urlsafe_b64encode(random_bytes).decode(),
        }

        # Create token with integrity protection
        token_data = json.dumps(context)
        token_hmac = hmac.new(
            self._session_hmac_key, token_data.encode(), hashlib.sha256
        ).hexdigest()

        return base64.urlsafe_b64encode(
            json.dumps({"token": token_data, "hmac": token_hmac}).encode()
        ).decode()

    def verify_session_token(
        self, token: str, user_id: int, max_age_hours: int = 8
    ) -> bool:
        """SECURITY: Verify session token authenticity and freshness"""
        try:
            # Decode token
            token_obj = json.loads(base64.urlsafe_b64decode(token.encode()).decode())

            # Verify HMAC
            expected_hmac = hmac.new(
                self._session_hmac_key, token_obj["token"].encode(), hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(expected_hmac, token_obj["hmac"]):
                return False

            # Parse token data
            context = json.loads(token_obj["token"])

            # Verify user ID
            if context.get("user_id") != user_id:
                return False

            # Verify timestamp
            timestamp = datetime.fromisoformat(context["timestamp"])
            if datetime.utcnow() - timestamp > timedelta(hours=max_age_hours):
                return False

            return True

        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return False


# Global instance
session_security = SessionSecurityManager()


def encrypt_sensitive_data(data: Dict[str, Any]) -> str:
    """SECURITY: Encrypt sensitive data for storage"""
    return session_security.encrypt_session_data(data)


def decrypt_sensitive_data(encrypted_data: str) -> Optional[Dict[str, Any]]:
    """SECURITY: Decrypt sensitive data from storage"""
    return session_security.decrypt_session_data(encrypted_data)


def generate_secure_token(user_id: int) -> str:
    """SECURITY: Generate secure session token"""
    return session_security.generate_secure_session_token(user_id)


def verify_secure_token(token: str, user_id: int) -> bool:
    """SECURITY: Verify secure session token"""
    return session_security.verify_session_token(token, user_id)
