"""
Data Sanitization Module for P0-7 Data Exposure Risk Prevention
Provides comprehensive data sanitization and masking for logs, errors, and responses
"""

import re
import json
import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class DataSanitizer:
    """Comprehensive data sanitization for preventing information exposure"""

    # Sensitive data patterns
    SENSITIVE_PATTERNS = {
        "api_key": re.compile(
            r'(?i)(api[_-]?key|apikey|access[_-]?key|secret[_-]?key)["\':=\s]*([a-zA-Z0-9_-]{20,})',
            re.IGNORECASE,
        ),
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "phone": re.compile(r"(\+?1?\d{9,15})"),
        "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "bitcoin_address": re.compile(r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b"),
        "ethereum_address": re.compile(r"\b0x[a-fA-F0-9]{40}\b"),
        "private_key": re.compile(
            r'(?i)(private[_-]?key|priv[_-]?key)["\':=\s]*([a-fA-F0-9]{64})',
            re.IGNORECASE,
        ),
        "password": re.compile(
            r'(?i)(password|pwd|pass)["\':=\s]*([^\s"\']{8,})', re.IGNORECASE
        ),
        "token": re.compile(
            r'(?i)(token|bearer)["\':=\s]*([a-zA-Z0-9_-]{20,})', re.IGNORECASE
        ),
        "auth_header": re.compile(
            r'(?i)authorization["\':=\s]*([^\s"\']+)', re.IGNORECASE
        ),
    }

    # Sensitive field names to mask in dictionaries
    SENSITIVE_FIELDS = {
        "api_key",
        "apikey",
        "access_key",
        "secret_key",
        "secret",
        "password",
        "pwd",
        "pass",
        "token",
        "auth_token",
        "access_token",
        "private_key",
        "priv_key",
        "authorization",
        "auth",
        "email",
        "phone",
        "phone_number",
        "credit_card",
        "ssn",
        "account_number",
        "routing_number",
        "wallet_address",
        "brevo_api_key",
        "fincra_secret_key",
        "binance_api_key",
        "blockbee_api_key",
        "twilio_auth_token",
        "webhook_secret",
    }

    @classmethod
    def sanitize_text(cls, text: str, mask_char: str = "*") -> str:
        """
        Sanitize text by masking sensitive patterns

        Args:
            text: Text to sanitize
            mask_char: Character to use for masking

        Returns:
            Sanitized text with sensitive data masked
        """
        if not isinstance(text, str):
            text = str(text)

        sanitized = text

        # Apply pattern-based sanitization
        for pattern_name, pattern in cls.SENSITIVE_PATTERNS.items():

            def replace_match(match):
                prefix = match.group(1) if len(match.groups()) > 1 else ""
                sensitive_part = (
                    match.group(2) if len(match.groups()) > 1 else match.group(0)
                )

                # Keep first 2 and last 2 characters for debugging, mask the rest
                if len(sensitive_part) > 8:
                    masked = f"{sensitive_part[:2]}{mask_char * (len(sensitive_part) - 4)}{sensitive_part[-2:]}"
                else:
                    masked = mask_char * len(sensitive_part)

                return (
                    f"{prefix}[REDACTED-{pattern_name.upper()}:{masked}]"
                    if prefix
                    else f"[REDACTED-{pattern_name.upper()}:{masked}]"
                )

            sanitized = pattern.sub(replace_match, sanitized)

        return sanitized

    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any], deep: bool = True) -> Dict[str, Any]:
        """
        Sanitize dictionary by masking sensitive fields

        Args:
            data: Dictionary to sanitize
            deep: Whether to recursively sanitize nested structures

        Returns:
            Sanitized dictionary
        """
        if not isinstance(data, dict):
            return data

        sanitized = {}

        for key, value in data.items():
            key_lower = str(key).lower()

            # Check if key is sensitive
            if any(
                sensitive_field in key_lower for sensitive_field in cls.SENSITIVE_FIELDS
            ):
                # Mask sensitive values
                if isinstance(value, str) and len(value) > 8:
                    sanitized[key] = f"[REDACTED:{value[:2]}***{value[-2:]}]"
                else:
                    sanitized[key] = "[REDACTED]"
            elif deep and isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value, deep=True)
            elif deep and isinstance(value, list):
                sanitized[key] = cls.sanitize_list(value, deep=True)
            else:
                # For non-sensitive fields, still sanitize text content
                if isinstance(value, str):
                    sanitized[key] = cls.sanitize_text(value)
                else:
                    sanitized[key] = value

        return sanitized

    @classmethod
    def sanitize_list(cls, data: List[Any], deep: bool = True) -> List[Any]:
        """
        Sanitize list by masking sensitive items

        Args:
            data: List to sanitize
            deep: Whether to recursively sanitize nested structures

        Returns:
            Sanitized list
        """
        if not isinstance(data, list):
            return data

        sanitized = []

        for item in data:
            if deep and isinstance(item, dict):
                sanitized.append(cls.sanitize_dict(item, deep=True))
            elif deep and isinstance(item, list):
                sanitized.append(cls.sanitize_list(item, deep=True))
            elif isinstance(item, str):
                sanitized.append(cls.sanitize_text(item))
            else:
                sanitized.append(item)

        return sanitized

    @classmethod
    def sanitize_json(cls, json_str: str) -> str:
        """
        Sanitize JSON string by parsing and masking sensitive data

        Args:
            json_str: JSON string to sanitize

        Returns:
            Sanitized JSON string
        """
        try:
            data = json.loads(json_str)
            sanitized_data = cls.sanitize_dict(data, deep=True)
            return json.dumps(sanitized_data, indent=2)
        except (json.JSONDecodeError, TypeError):
            # If not valid JSON, treat as plain text
            return cls.sanitize_text(json_str)

    @classmethod
    def sanitize_error_message(cls, error_msg: str, include_type: bool = True) -> str:
        """
        Sanitize error messages to prevent sensitive data exposure

        Args:
            error_msg: Error message to sanitize
            include_type: Whether to include error type information

        Returns:
            Sanitized error message safe for logging/display
        """
        if not error_msg:
            return "Unknown error"

        # Convert to string if needed
        error_str = str(error_msg)

        # Sanitize sensitive patterns
        sanitized = cls.sanitize_text(error_str)

        # Remove stack traces with potential sensitive data
        lines = sanitized.split("\n")
        safe_lines = []

        for line in lines:
            # Skip lines that might contain file paths with sensitive info
            if "/home/" in line or "site-packages" in line or "Traceback" in line:
                if include_type:
                    safe_lines.append("[STACK_TRACE_REDACTED]")
                continue

            # Keep error messages but sanitize them
            safe_lines.append(line)

        result = "\n".join(safe_lines[:3])  # Limit to first 3 lines

        # Ensure we don't accidentally expose sensitive data in generic errors
        if len(result) > 200:
            result = result[:200] + "... [TRUNCATED]"

        return result if result.strip() else "Error details redacted for security"

    @classmethod
    def sanitize_api_response(
        cls, response: Union[Dict, str, Any]
    ) -> Union[Dict, str, Any]:
        """
        Sanitize API responses to prevent sensitive data exposure

        Args:
            response: API response to sanitize

        Returns:
            Sanitized API response
        """
        if isinstance(response, dict):
            return cls.sanitize_dict(response, deep=True)
        elif isinstance(response, str):
            try:
                # Try to parse as JSON first
                data = json.loads(response)
                return json.dumps(cls.sanitize_dict(data, deep=True))
            except json.JSONDecodeError:
                return cls.sanitize_text(response)
        elif isinstance(response, list):
            return cls.sanitize_list(response, deep=True)
        else:
            return cls.sanitize_text(str(response))

    @classmethod
    def safe_log_format(
        cls,
        message: str,
        context: Optional[Dict] = None,
        error: Optional[Exception] = None,
    ) -> str:
        """
        Create safe log message with sanitized context and error information

        Args:
            message: Base log message
            context: Optional context dictionary
            error: Optional exception

        Returns:
            Safe formatted log message
        """
        log_parts = [cls.sanitize_text(message)]

        if context:
            sanitized_context = cls.sanitize_dict(context, deep=True)
            log_parts.append(f"Context: {json.dumps(sanitized_context, default=str)}")

        if error:
            safe_error = cls.sanitize_error_message(str(error), include_type=True)
            log_parts.append(f"Error: {safe_error}")

        return " | ".join(log_parts)

    @classmethod
    def mask_api_key(cls, api_key: Optional[str], show_chars: int = 2) -> str:
        """
        Safely mask API key for logging

        Args:
            api_key: API key to mask
            show_chars: Number of characters to show at start/end (default: 2 for security)

        Returns:
            Masked API key safe for logging
        """
        if not api_key:
            return "[NO_API_KEY]"

        if len(api_key) <= show_chars * 2:
            return "[REDACTED]"

        return f"[API_KEY:{api_key[:show_chars]}***{api_key[-show_chars:]}]"

    @classmethod
    def mask_user_data(cls, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mask sensitive user data for safe logging/display

        Args:
            user_data: User data dictionary

        Returns:
            Masked user data safe for logging
        """
        return cls.sanitize_dict(user_data, deep=True)


# Global instance for application use
data_sanitizer = DataSanitizer()


# Convenience functions
def sanitize_for_log(data: Any) -> str:
    """Sanitize any data for safe logging"""
    if isinstance(data, dict):
        return json.dumps(data_sanitizer.sanitize_dict(data), default=str)
    elif isinstance(data, list):
        return json.dumps(data_sanitizer.sanitize_list(data), default=str)
    else:
        return data_sanitizer.sanitize_text(str(data))


def safe_error_log(error: Exception, context: Optional[Dict] = None) -> str:
    """Create safe error log message"""
    return data_sanitizer.safe_log_format("Error occurred", context, error)


def mask_api_key_safe(api_key: Optional[str]) -> str:
    """Safely mask API key for any logging"""
    return data_sanitizer.mask_api_key(api_key)
