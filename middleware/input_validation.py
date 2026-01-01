"""Comprehensive input validation middleware for security"""

import re
import html
import logging
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import unicodedata
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Input validation security levels"""

    BASIC = "basic"
    STRICT = "strict"
    PARANOID = "paranoid"


class InputType(Enum):
    """Types of input validation"""

    TEXT = "text"
    EMAIL = "email"
    PHONE = "phone"
    AMOUNT = "amount"
    ADDRESS = "address"
    USERNAME = "username"
    PASSWORD = "password"
    URL = "url"
    FILE_NAME = "file_name"
    CRYPTO_ADDRESS = "crypto_address"
    TELEGRAM_ID = "telegram_id"
    JSON_DATA = "json_data"


@dataclass
class ValidationRule:
    """Individual validation rule"""

    name: str
    input_type: InputType
    required: bool = False
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    allow_unicode: bool = True
    sanitize: bool = True
    custom_validator: Optional[Callable] = None


@dataclass
class ValidationResult:
    """Result of input validation"""

    is_valid: bool
    sanitized_value: Any = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class SecuritySanitizer:
    """Advanced input sanitization for security"""

    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"onload\s*=",
        r"onerror\s*=",
        r"onclick\s*=",
        r"onmouseover\s*=",
        r"<iframe[^>]*>.*?</iframe>",
        r"<object[^>]*>.*?</object>",
        r"<embed[^>]*>.*?</embed>",
        r"<link[^>]*>",
        r"<meta[^>]*>",
        r"expression\s*\(",
        r"@import",
        r"<svg[^>]*>.*?</svg>",
    ]

    # SQL injection patterns
    SQL_PATTERNS = [
        r"(union|select|insert|delete|update|drop|create|alter|exec|execute)\s+",
        r"(or|and)\s+\d+\s*=\s*\d+",
        r";\s*(drop|delete|truncate|alter)",
        r"--\s*",
        r"/\*.*?\*/",
        r"'\s*or\s*'.*?'\s*=\s*'",
        r'"\s*or\s*".*?"\s*=\s*"',
    ]

    # Command injection patterns
    COMMAND_PATTERNS = [
        r"[;&|`]",
        r"\$\(.*?\)",
        r"`.*?`",
        r"\|\s*(rm|cat|ls|pwd|whoami|id|netstat|ps)",
        r"(curl|wget|nc|telnet)\s+",
    ]

    @classmethod
    def sanitize_text(
        cls, text: str, level: ValidationLevel = ValidationLevel.STRICT
    ) -> str:
        """Sanitize text input against various attacks"""
        if not isinstance(text, str):
            text = str(text)

        # Basic sanitization
        text = html.escape(text, quote=True)

        if level in [ValidationLevel.STRICT, ValidationLevel.PARANOID]:
            # Remove/neutralize XSS patterns
            for pattern in cls.XSS_PATTERNS:
                text = re.sub(pattern, "", text, flags=re.IGNORECASE)

            # Remove SQL injection patterns
            for pattern in cls.SQL_PATTERNS:
                text = re.sub(pattern, "", text, flags=re.IGNORECASE)

            if level == ValidationLevel.PARANOID:
                # Remove command injection patterns
                for pattern in cls.COMMAND_PATTERNS:
                    text = re.sub(pattern, "", text, flags=re.IGNORECASE)

                # Remove control characters
                text = "".join(
                    c
                    for c in text
                    if unicodedata.category(c)[0] != "C" or c in "\n\r\t"
                )

        return text.strip()

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize filename for safe storage"""
        if not filename:
            return ""

        # Remove path traversal attempts
        filename = filename.replace("..", "").replace("/", "").replace("\\", "")

        # Remove dangerous characters
        dangerous_chars = '<>:"|?*'
        for char in dangerous_chars:
            filename = filename.replace(char, "_")

        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
            filename = name[: 255 - len(ext) - 1] + "." + ext if ext else name[:255]

        return filename.strip()

    @classmethod
    def detect_suspicious_patterns(cls, text: str) -> List[str]:
        """Detect suspicious patterns in input"""
        suspicious = []

        # Check for encoding attempts
        if any(
            pattern in text.lower()
            for pattern in ["%3c", "&lt;", "&#x", "\\u00", "\\x"]
        ):
            suspicious.append("Potential encoding bypass attempt")

        # Check for data URIs
        if "data:" in text.lower():
            suspicious.append("Data URI detected")

        # Check for Base64-like patterns
        import base64
        import binascii

        try:
            if len(text) > 20 and len(text) % 4 == 0:
                base64.b64decode(text, validate=True)
                suspicious.append("Potential Base64 encoded data")
        except (ValueError, binascii.Error):
            pass

        # Check for extremely long inputs (possible DoS)
        if len(text) > 10000:
            suspicious.append("Unusually long input")

        return suspicious


class InputValidator:
    """Comprehensive input validation system"""

    def __init__(self, level: ValidationLevel = ValidationLevel.STRICT):
        self.level = level
        self.sanitizer = SecuritySanitizer()

    def validate_text(self, value: str, rule: ValidationRule) -> ValidationResult:
        """Validate text input"""
        result = ValidationResult(is_valid=True)

        if not value and rule.required:
            result.is_valid = False
            result.errors.append(f"{rule.name} is required")
            return result

        if not value:
            result.sanitized_value = ""
            return result

        # Length validation
        if rule.min_length and len(value) < rule.min_length:
            result.is_valid = False
            result.errors.append(
                f"{rule.name} must be at least {rule.min_length} characters"
            )

        if rule.max_length and len(value) > rule.max_length:
            result.is_valid = False
            result.errors.append(
                f"{rule.name} must be no more than {rule.max_length} characters"
            )

        # Pattern validation
        if rule.pattern and not re.match(rule.pattern, value):
            result.is_valid = False
            result.errors.append(f"{rule.name} format is invalid")

        # Unicode validation
        if not rule.allow_unicode:
            try:
                value.encode("ascii")
            except UnicodeEncodeError:
                result.is_valid = False
                result.errors.append(f"{rule.name} contains invalid characters")

        # Security sanitization
        if rule.sanitize:
            sanitized = self.sanitizer.sanitize_text(value, self.level)
            result.sanitized_value = sanitized

            # Detect suspicious patterns
            suspicious = self.sanitizer.detect_suspicious_patterns(value)
            if suspicious:
                result.warnings.extend(suspicious)
                logger.warning(
                    f"Suspicious input detected in {rule.name}: {suspicious}"
                )
        else:
            result.sanitized_value = value

        # Custom validation
        if rule.custom_validator:
            try:
                custom_result = rule.custom_validator(result.sanitized_value)
                if not custom_result:
                    result.is_valid = False
                    result.errors.append(f"{rule.name} failed custom validation")
            except Exception as e:
                result.is_valid = False
                result.errors.append(f"{rule.name} validation error: {str(e)}")

        return result

    def validate_email(self, value: str, rule: ValidationRule) -> ValidationResult:
        """Validate email address"""
        result = ValidationResult(is_valid=True)

        if not value and rule.required:
            result.is_valid = False
            result.errors.append(f"{rule.name} is required")
            return result

        if not value:
            result.sanitized_value = ""
            return result

        # Basic email pattern
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, value):
            result.is_valid = False
            result.errors.append(f"{rule.name} is not a valid email address")

        # Sanitize
        result.sanitized_value = value.lower().strip()

        # Additional security checks
        suspicious_domains = ["tempmail", "10minutemail", "guerrillamail", "mailinator"]
        domain = value.split("@")[1] if "@" in value else ""
        if any(suspect in domain.lower() for suspect in suspicious_domains):
            result.warnings.append("Temporary email service detected")

        return result

    def validate_amount(
        self, value: Union[str, int, float, Decimal], rule: ValidationRule
    ) -> ValidationResult:
        """Validate monetary amount"""
        result = ValidationResult(is_valid=True)

        if value is None and rule.required:
            result.is_valid = False
            result.errors.append(f"{rule.name} is required")
            return result

        if value is None:
            result.sanitized_value = None
            return result

        # Convert to Decimal for precision
        try:
            if isinstance(value, str):
                # Remove currency symbols and spaces
                clean_value = re.sub(r"[^\d.-]", "", value)
                decimal_value = Decimal(clean_value)
            else:
                decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError):
            result.is_valid = False
            result.errors.append(f"{rule.name} is not a valid amount")
            return result

        # Check for negative amounts
        if decimal_value < 0:
            result.is_valid = False
            result.errors.append(f"{rule.name} cannot be negative")

        # Check for excessive precision (more than 8 decimal places)
        exponent = decimal_value.as_tuple().exponent
        if isinstance(exponent, int) and exponent < -8:
            result.is_valid = False
            result.errors.append(f"{rule.name} has too many decimal places (max 8)")

        # Check for extremely large amounts (possible overflow attempt)
        if decimal_value > Decimal("1000000000"):  # 1 billion
            result.warnings.append("Very large amount detected")

        result.sanitized_value = decimal_value
        return result

    def validate_crypto_address(
        self, value: str, rule: ValidationRule
    ) -> ValidationResult:
        """Validate cryptocurrency address"""
        result = ValidationResult(is_valid=True)

        if not value and rule.required:
            result.is_valid = False
            result.errors.append(f"{rule.name} is required")
            return result

        if not value:
            result.sanitized_value = ""
            return result

        # Basic format validation (this would be expanded for specific cryptocurrencies)
        if len(value) < 25 or len(value) > 62:
            result.is_valid = False
            result.errors.append(f"{rule.name} length is invalid for crypto address")

        # Check for valid characters
        if not re.match(r"^[A-Za-z0-9]+$", value):
            result.is_valid = False
            result.errors.append(f"{rule.name} contains invalid characters")

        result.sanitized_value = value.strip()
        return result

    def validate_phone(self, value: str, rule: ValidationRule) -> ValidationResult:
        """Validate phone number"""
        result = ValidationResult(is_valid=True)

        if not value and rule.required:
            result.is_valid = False
            result.errors.append(f"{rule.name} is required")
            return result

        if not value:
            result.sanitized_value = ""
            return result

        # Remove all non-digit characters
        digits_only = re.sub(r"[^\d+]", "", value)

        # Basic phone number validation
        if not re.match(r"^\+?[1-9]\d{1,14}$", digits_only):
            result.is_valid = False
            result.errors.append(f"{rule.name} is not a valid phone number")

        result.sanitized_value = digits_only
        return result

    def validate_input(self, value: Any, rule: ValidationRule) -> ValidationResult:
        """Main validation method that routes to specific validators"""
        try:
            if rule.input_type == InputType.TEXT:
                return self.validate_text(str(value) if value is not None else "", rule)
            elif rule.input_type == InputType.EMAIL:
                return self.validate_email(
                    str(value) if value is not None else "", rule
                )
            elif rule.input_type == InputType.AMOUNT:
                return self.validate_amount(value, rule)
            elif rule.input_type == InputType.CRYPTO_ADDRESS:
                return self.validate_crypto_address(
                    str(value) if value is not None else "", rule
                )
            elif rule.input_type == InputType.PHONE:
                return self.validate_phone(
                    str(value) if value is not None else "", rule
                )
            elif rule.input_type == InputType.FILE_NAME:
                result = ValidationResult(is_valid=True)
                result.sanitized_value = self.sanitizer.sanitize_filename(
                    str(value) if value else ""
                )
                return result
            else:
                # Default to text validation
                return self.validate_text(str(value) if value is not None else "", rule)

        except Exception as e:
            logger.error(f"Validation error for {rule.name}: {e}")
            result = ValidationResult(is_valid=False)
            result.errors.append(f"Validation failed: {str(e)}")
            return result

    def validate_batch(
        self, data: Dict[str, Any], rules: List[ValidationRule]
    ) -> Dict[str, ValidationResult]:
        """Validate multiple inputs at once"""
        results = {}

        for rule in rules:
            value = data.get(rule.name)
            results[rule.name] = self.validate_input(value, rule)

        return results

    def is_all_valid(self, results: Dict[str, ValidationResult]) -> bool:
        """Check if all validation results are valid"""
        return all(result.is_valid for result in results.values())

    def get_sanitized_data(
        self, results: Dict[str, ValidationResult]
    ) -> Dict[str, Any]:
        """Extract sanitized data from validation results"""
        return {
            name: result.sanitized_value
            for name, result in results.items()
            if result.is_valid
        }

    def get_all_errors(self, results: Dict[str, ValidationResult]) -> List[str]:
        """Get all validation errors"""
        all_errors = []
        for name, result in results.items():
            all_errors.extend(result.errors)
        return all_errors


# Common validation rules
COMMON_RULES = {
    "telegram_id": ValidationRule(
        name="telegram_id",
        input_type=InputType.TELEGRAM_ID,
        required=True,
        pattern=r"^\d+$",
        max_length=15,
    ),
    "username": ValidationRule(
        name="username",
        input_type=InputType.USERNAME,
        required=False,
        min_length=3,
        max_length=32,
        pattern=r"^[a-zA-Z0-9_]+$",
    ),
    "email": ValidationRule(
        name="email", input_type=InputType.EMAIL, required=False, max_length=254
    ),
    "amount": ValidationRule(name="amount", input_type=InputType.AMOUNT, required=True),
    "crypto_address": ValidationRule(
        name="crypto_address", input_type=InputType.CRYPTO_ADDRESS, required=True
    ),
    "phone": ValidationRule(name="phone", input_type=InputType.PHONE, required=False),
}

# Global validator instance
input_validator = InputValidator(ValidationLevel.STRICT)
