"""
Enhanced Input Validation Framework for Security
Comprehensive validation with security-focused checks across all handler inputs
"""

import re
import logging
from typing import Dict, Any
from decimal import Decimal, InvalidOperation
import html
import json
from urllib.parse import urlparse
import base64

logger = logging.getLogger(__name__)


class SecurityInputValidator:
    """Enhanced input validation with comprehensive security checks"""

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)",
        r"(--|\#|\/\*|\*\/)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(\bUNION\s+(ALL\s+)?SELECT)",
        r"(\bINTO\s+(OUT|DUMP)FILE)",
        r"(\bLOAD_FILE\s*\()",
        r"(\bSLEEP\s*\()",
        r"(\bWAITFOR\s+DELAY)",
        r"(\bCONVERT\s*\()",
        r"(\bCAST\s*\()",
    ]

    # XSS injection patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"onload\s*=",
        r"onerror\s*=",
        r"onclick\s*=",
        r"onmouseover\s*=",
        r"onfocus\s*=",
        r"onblur\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
        r"<form[^>]*>",
        r"<input[^>]*>",
        r"document\.cookie",
        r"document\.write",
        r"eval\s*\(",
        r"setTimeout\s*\(",
        r"setInterval\s*\(",
    ]

    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"(\||&|;|\$\(|\`)",
        r"(\\|\.\./|\.\.\\)",
        r"(/bin/|/usr/bin/|cmd\.exe|powershell)",
        r"(nc\s|netcat|wget|curl)",
        r"(rm\s|del\s|format\s)",
        r"(>|<|>>|<<)",
        r"(sudo|su\s|chmod|chown)",
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"(\.\.\/|\.\.\\)",
        r"(\/\.\.|\\\.\.)",
        r"(%2e%2e%2f|%2e%2e%5c)",
        r"(\.\.%2f|\.\.%5c)",
        r"(%252e%252e%252f|%252e%252e%255c)",
    ]

    # NoSQL injection patterns
    NOSQL_INJECTION_PATTERNS = [
        r"(\$where|\$ne|\$gt|\$lt|\$gte|\$lte)",
        r"(\$regex|\$in|\$nin|\$exists)",
        r"(\$or|\$and|\$not|\$nor)",
        r"(this\s*\.\s*[\w]+)",
        r"(function\s*\(\s*\)\s*\{)",
        r"(\}[\s]*\)[\s]*;)",
    ]

    # LDAP injection patterns
    LDAP_INJECTION_PATTERNS = [
        r"(\(|\)|\*|\||&)",
        r"(\\[0-9a-fA-F]{2})",
        r"(\x00|\x2a|\x28|\x29)",
    ]

    @classmethod
    def validate_and_sanitize_input(
        cls,
        input_value: Any,
        input_type: str,
        max_length: int = 1000,
        required: bool = True,
    ) -> Dict[str, Any]:
        """Comprehensive input validation and sanitization"""
        result: Dict[str, Any] = {
            "is_valid": False,
            "sanitized_value": None,
            "warnings": [],
            "errors": [],
            "security_score": 100,
        }

        try:
            # Handle None/empty inputs
            if input_value is None or (
                isinstance(input_value, str) and input_value.strip() == ""
            ):
                if required:
                    result["errors"].append(f"{input_type} is required")
                    return result
                else:
                    result["is_valid"] = True
                    result["sanitized_value"] = ""
                    return result

            # Convert to string for processing
            str_value = str(input_value).strip()

            # Length validation
            if len(str_value) > max_length:
                result["errors"].append(
                    f"{input_type} exceeds maximum length of {max_length}"
                )
                return result

            # Security pattern checks
            security_issues = cls._check_security_patterns(str_value)
            if security_issues:
                result["errors"].extend(security_issues["errors"])
                result["warnings"].extend(security_issues["warnings"])
                result["security_score"] = security_issues["score"]

                # Block critical security issues
                if security_issues["score"] < 50:
                    result["errors"].append(
                        "Input contains dangerous patterns and has been blocked"
                    )
                    return result

            # Type-specific validation
            if input_type == "username":
                validated = cls._validate_username(str_value)
            elif input_type == "email":
                validated = cls._validate_email(str_value)
            elif input_type == "amount":
                validated = cls._validate_amount(str_value)
            elif input_type == "crypto_address":
                validated = cls._validate_crypto_address(str_value)
            elif input_type == "description":
                validated = cls._validate_description(str_value)
            elif input_type == "url":
                validated = cls._validate_url(str_value)
            elif input_type == "json":
                validated = cls._validate_json(str_value)
            elif input_type == "base64":
                validated = cls._validate_base64(str_value)
            else:
                validated = cls._validate_generic_text(str_value)

            if not validated["is_valid"]:
                result["errors"].extend(validated["errors"])
                return result

            # Sanitization
            sanitized = cls._sanitize_input(validated["value"])

            result["is_valid"] = True
            result["sanitized_value"] = sanitized

            return result

        except Exception as e:
            logger.error(f"Input validation error: {e}")
            result["errors"].append(f"Validation error: {str(e)}")
            return result

    @classmethod
    def _check_security_patterns(cls, input_value: str) -> Dict[str, Any]:
        """Check input against security patterns"""
        issues: Dict[str, Any] = {"errors": [], "warnings": [], "score": 100}

        # SQL injection check
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, input_value, re.IGNORECASE):
                issues["errors"].append("Potential SQL injection detected")
                issues["score"] -= 30
                break

        # XSS check
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, input_value, re.IGNORECASE):
                issues["errors"].append("Potential XSS attack detected")
                issues["score"] -= 25
                break

        # Command injection check
        for pattern in cls.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, input_value, re.IGNORECASE):
                issues["errors"].append("Potential command injection detected")
                issues["score"] -= 35
                break

        # Path traversal check
        for pattern in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, input_value, re.IGNORECASE):
                issues["errors"].append("Potential path traversal detected")
                issues["score"] -= 20
                break

        # NoSQL injection check
        for pattern in cls.NOSQL_INJECTION_PATTERNS:
            if re.search(pattern, input_value, re.IGNORECASE):
                issues["warnings"].append("Potential NoSQL injection pattern detected")
                issues["score"] -= 15
                break

        # LDAP injection check
        for pattern in cls.LDAP_INJECTION_PATTERNS:
            if re.search(pattern, input_value, re.IGNORECASE):
                issues["warnings"].append("Potential LDAP injection pattern detected")
                issues["score"] -= 10
                break

        # Additional suspicious patterns
        suspicious_patterns = [
            r"(\x00|\x1a|\x0d|\x0a)",  # Null bytes and control characters
            r"(eval|exec|system|shell_exec|passthru)",  # Code execution functions
            r"(base64_decode|gzuncompress|str_rot13)",  # Encoding functions
            r"(/etc/passwd|/etc/shadow|win\.ini)",  # System files
            r"(0x[0-9a-fA-F]+)",  # Hexadecimal values
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, input_value, re.IGNORECASE):
                issues["warnings"].append("Suspicious pattern detected")
                issues["score"] -= 5
                break

        return issues

    @classmethod
    def _validate_username(cls, username: str) -> Dict[str, Any]:
        """Validate Telegram username"""
        result: Dict[str, Any] = {"is_valid": False, "value": username, "errors": []}

        # Add @ if missing
        if not username.startswith("@"):
            username = "@" + username

        # Check format
        pattern = re.compile(r"^@[a-zA-Z0-9_]{5,32}$")
        if not pattern.match(username):
            result["errors"].append("Invalid username format")
            return result

        # Reject purely numeric usernames
        numeric_part = username[1:]  # Remove @
        if numeric_part.isdigit():
            result["errors"].append("Username cannot be purely numeric")
            return result

        result["is_valid"] = True
        result["value"] = username
        return result

    @classmethod
    def _validate_email(cls, email: str) -> Dict[str, Any]:
        """Validate email address"""
        result: Dict[str, Any] = {"is_valid": False, "value": email.lower(), "errors": []}

        pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        if not pattern.match(email):
            result["errors"].append("Invalid email format")
            return result

        # Additional email security checks
        if len(email) > 254:
            result["errors"].append("Email address too long")
            return result

        # Check for suspicious domains
        suspicious_domains = ["example.com", "test.com", "tempmail.", "10minute"]
        domain = email.split("@")[1].lower()
        if any(sus in domain for sus in suspicious_domains):
            result["errors"].append("Suspicious email domain detected")
            return result

        result["is_valid"] = True
        return result

    @classmethod
    def _validate_amount(cls, amount_str: str) -> Dict[str, Any]:
        """Validate monetary amount"""
        result: Dict[str, Any] = {"is_valid": False, "value": amount_str, "errors": []}

        # Clean input
        cleaned = amount_str.replace(",", "").replace("$", "").strip()

        try:
            amount = Decimal(cleaned)
        except InvalidOperation:
            result["errors"].append("Invalid amount format")
            return result

        if amount < 0:
            result["errors"].append("Amount cannot be negative")
            return result

        if amount > 1000000:  # $1M limit
            result["errors"].append("Amount exceeds maximum limit")
            return result

        # Check decimal places
        exponent = amount.as_tuple().exponent
        if isinstance(exponent, int) and exponent < -2:
            result["errors"].append("Too many decimal places")
            return result

        result["is_valid"] = True
        result["value"] = amount
        return result

    @classmethod
    def _validate_crypto_address(cls, address: str) -> Dict[str, Any]:
        """Validate cryptocurrency address"""
        result: Dict[str, Any] = {"is_valid": False, "value": address.strip(), "errors": []}

        # Basic length and character checks
        if len(address) < 10 or len(address) > 100:
            result["errors"].append("Invalid address length")
            return result

        # Check for obvious invalid characters
        if not re.match(r"^[a-zA-Z0-9]+$", address):
            result["errors"].append("Invalid address characters")
            return result

        result["is_valid"] = True
        return result

    @classmethod
    def _validate_description(cls, description: str) -> Dict[str, Any]:
        """Validate text description"""
        result: Dict[str, Any] = {"is_valid": False, "value": description, "errors": []}

        if len(description) < 10:
            result["errors"].append("Description too short (minimum 10 characters)")
            return result

        if len(description) > 500:
            result["errors"].append("Description too long (maximum 500 characters)")
            return result

        # Check for excessive repetition
        if re.search(r"(.)\1{10,}", description):
            result["errors"].append("Excessive character repetition detected")
            return result

        result["is_valid"] = True
        return result

    @classmethod
    def _validate_url(cls, url: str) -> Dict[str, Any]:
        """Validate URL"""
        result: Dict[str, Any] = {"is_valid": False, "value": url, "errors": []}

        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                result["errors"].append("Invalid URL format")
                return result

            # Only allow safe schemes
            if parsed.scheme not in ["http", "https"]:
                result["errors"].append("Unsupported URL scheme")
                return result

            # Block localhost and internal IPs
            hostname = parsed.hostname
            if hostname in ["localhost", "127.0.0.1", "0.0.0.0"]:
                result["errors"].append("Localhost URLs not allowed")
                return result

            result["is_valid"] = True
            return result

        except Exception as e:
            result["errors"].append(f"URL validation error: {str(e)}")
            return result

    @classmethod
    def _validate_json(cls, json_str: str) -> Dict[str, Any]:
        """Validate JSON string"""
        result: Dict[str, Any] = {"is_valid": False, "value": json_str, "errors": []}

        try:
            parsed = json.loads(json_str)

            # Size limit
            if len(json_str) > 10000:
                result["errors"].append("JSON data too large")
                return result

            # Depth limit
            def get_depth(obj, depth=0):
                if isinstance(obj, dict):
                    return (
                        max(get_depth(v, depth + 1) for v in obj.values())
                        if obj
                        else depth
                    )
                elif isinstance(obj, list):
                    return (
                        max(get_depth(item, depth + 1) for item in obj)
                        if obj
                        else depth
                    )
                return depth

            if get_depth(parsed) > 10:
                result["errors"].append("JSON nesting too deep")
                return result

            result["is_valid"] = True
            result["value"] = parsed
            return result

        except json.JSONDecodeError as e:
            result["errors"].append(f"Invalid JSON: {str(e)}")
            return result

    @classmethod
    def _validate_base64(cls, base64_str: str) -> Dict[str, Any]:
        """Validate base64 encoded data"""
        result: Dict[str, Any] = {"is_valid": False, "value": base64_str, "errors": []}

        try:
            # Check format
            if not re.match(r"^[A-Za-z0-9+/]*={0,2}$", base64_str):
                result["errors"].append("Invalid base64 format")
                return result

            # Try to decode
            decoded = base64.b64decode(base64_str)

            # Size limits
            if len(decoded) > 1048576:  # 1MB limit
                result["errors"].append("Decoded data too large")
                return result

            result["is_valid"] = True
            result["value"] = decoded
            return result

        except Exception as e:
            result["errors"].append(f"Base64 validation error: {str(e)}")
            return result

    @classmethod
    def _validate_generic_text(cls, text: str) -> Dict[str, Any]:
        """Validate generic text input"""
        result: Dict[str, Any] = {"is_valid": True, "value": text, "errors": []}

        # Basic checks
        if len(text) > 10000:
            result["errors"].append("Text too long")
            result["is_valid"] = False
            return result

        # Check for null bytes
        if "\x00" in text:
            result["errors"].append("Null bytes not allowed")
            result["is_valid"] = False
            return result

        return result

    @classmethod
    def _sanitize_input(cls, input_value: Any) -> Any:
        """Sanitize input for safe storage and display"""
        if isinstance(input_value, str):
            # HTML entity encoding
            sanitized = html.escape(input_value)

            # Remove or replace dangerous characters
            sanitized = sanitized.replace("\x00", "")  # Remove null bytes
            sanitized = re.sub(
                r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", sanitized
            )  # Remove control chars

            return sanitized

        return input_value


# Decorator for handler input validation
def validate_handler_inputs(**validation_rules):
    """
    Decorator to validate handler inputs

    Usage:
    @validate_handler_inputs(
        username={"type": "username", "required": True},
        amount={"type": "amount", "required": True, "max_length": 20}
    )
    """

    def decorator(func):
        from functools import wraps

        @wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            # Extract inputs from update and context
            inputs = {}

            # Get text from message or callback
            if update.message and update.message.text:
                inputs["message_text"] = update.message.text
            elif update.callback_query and update.callback_query.data:
                inputs["callback_data"] = update.callback_query.data

            # Validate inputs according to rules
            validation_errors = []

            for field_name, rules in validation_rules.items():
                if field_name in inputs:
                    validation_result = (
                        SecurityInputValidator.validate_and_sanitize_input(
                            inputs[field_name],
                            rules.get("type", "text"),
                            rules.get("max_length", 1000),
                            rules.get("required", False),
                        )
                    )

                    if not validation_result["is_valid"]:
                        validation_errors.extend(validation_result["errors"])
                    else:
                        # Update input with sanitized value
                        inputs[field_name] = validation_result["sanitized_value"]

            # Block execution if validation fails
            if validation_errors:
                logger.warning(
                    f"Input validation failed in {func.__name__}: {validation_errors}"
                )

                if update.message:
                    await update.message.reply_text(
                        "❌ Invalid input detected. Please check your input and try again."
                    )
                elif update.callback_query:
                    await update.callback_query.answer(
                        "Invalid input detected", show_alert=True
                    )
                return

            # Execute original handler with validated inputs
            return await func(update, context, *args, **kwargs)

        return wrapper

    return decorator
