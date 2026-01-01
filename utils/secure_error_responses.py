"""
SECURITY: Secure Error Response System
Prevents information disclosure through error messages while maintaining debugging capability
"""

import logging
import re
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories for secure error classification"""

    USER_INPUT = "user_input"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATABASE = "database"
    NETWORK = "network"
    API_EXTERNAL = "api_external"
    SYSTEM = "system"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"


class SecureErrorResponses:
    """SECURITY: Provides sanitized error messages for users while preserving debug info"""

    # Generic user-safe error messages
    SAFE_MESSAGES = {
        ErrorCategory.USER_INPUT: "Please check your input and try again.",
        ErrorCategory.AUTHENTICATION: "Authentication failed. Please try again.",
        ErrorCategory.AUTHORIZATION: "Access denied. You don't have permission for this action.",
        ErrorCategory.DATABASE: "We're experiencing technical difficulties. Please try again later.",
        ErrorCategory.NETWORK: "Connection issue. Please check your internet and try again.",
        ErrorCategory.API_EXTERNAL: "Service temporarily unavailable. Please try again later.",
        ErrorCategory.SYSTEM: "System error occurred. Please try again or contact support.",
        ErrorCategory.VALIDATION: "Invalid data provided. Please check your input.",
        ErrorCategory.CONFIGURATION: "Service configuration issue. Please contact support.",
    }

    # Patterns that should never appear in user messages
    SENSITIVE_PATTERNS = [
        # Database information
        r"database.*error|sqlalchemy|postgresql|connection.*failed",
        r"table.*does.*not.*exist|column.*unknown|syntax.*error.*at",
        r"duplicate.*key.*value|foreign.*key.*constraint|check.*constraint",
        # File paths and system info
        r"/[a-zA-Z0-9_\-/\.]+\.py|C:\\[a-zA-Z0-9_\-\\\.]+",
        r'line.*\d+.*in.*<.*>|File.*".*".*line.*\d+',
        r"Traceback.*most.*recent.*call|raise.*Exception",
        # Network and connection details
        r"connection.*refused|timeout.*error|dns.*resolution",
        r"http[s]?://[^\s]+|port.*\d+.*connection",
        r"SSL.*certificate|TLS.*handshake|socket.*error",
        # API keys and secrets
        r"api.*key|secret.*key|token.*invalid|authentication.*header",
        r"bearer.*token|authorization.*failed|signature.*mismatch",
        # Internal application details
        r"handler.*not.*found|function.*not.*defined|module.*not.*found",
        r"import.*error|attribute.*error|name.*error",
        r"memory.*error|cpu.*usage|disk.*space",
    ]

    @classmethod
    def get_safe_error_message(
        cls, category: ErrorCategory, custom_message: Optional[str] = None
    ) -> str:
        """
        SECURITY: Get user-safe error message for given category

        Args:
            category: Error category for appropriate message selection
            custom_message: Optional custom message (will be sanitized)

        Returns:
            Sanitized error message safe for user display
        """
        if custom_message:
            # Sanitize custom message
            safe_custom = cls._sanitize_error_message(custom_message)
            if safe_custom and len(safe_custom.strip()) > 0:
                return safe_custom

        # Return generic safe message
        return cls.SAFE_MESSAGES.get(category, cls.SAFE_MESSAGES[ErrorCategory.SYSTEM])

    @classmethod
    def _sanitize_error_message(cls, message: str) -> str:
        """
        SECURITY: Remove sensitive information from error messages

        Args:
            message: Original error message

        Returns:
            Sanitized message safe for users
        """
        if not message:
            return ""

        # Convert to lowercase for pattern matching
        message_lower = message.lower()

        # Check for sensitive patterns
        for pattern in cls.SENSITIVE_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                # Message contains sensitive info - return generic message
                return ""

        # Remove specific sensitive content while preserving safe parts
        sanitized = message

        # Remove file paths
        sanitized = re.sub(r"/[a-zA-Z0-9_\-/\.]+\.py", "[file]", sanitized)
        sanitized = re.sub(r"C:\\[a-zA-Z0-9_\-\\\.]+", "[file]", sanitized)

        # Remove line numbers and function references
        sanitized = re.sub(r"line \d+", "line [X]", sanitized)
        sanitized = re.sub(r"in <[^>]+>", "in [function]", sanitized)

        # Remove URLs and IPs
        sanitized = re.sub(r"http[s]?://[^\s]+", "[url]", sanitized)
        sanitized = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "[ip]", sanitized)

        # Remove port numbers
        sanitized = re.sub(r"port \d+", "port [X]", sanitized)

        # Final length check - if too much was removed, return generic message
        if len(sanitized.strip()) < len(message) * 0.3:  # If more than 70% removed
            return ""

        return sanitized.strip()

    @classmethod
    def log_secure_error(
        cls,
        error: Exception,
        category: ErrorCategory,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> str:
        """
        SECURITY: Log error with full details internally while generating safe error ID

        Args:
            error: The exception that occurred
            category: Error category for classification
            context: Additional context information
            user_id: User ID if applicable

        Returns:
            Error ID for user reference and support
        """
        # Generate unique error ID
        error_id = (
            f"ERR_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        )

        # Prepare context information
        log_context = {
            "error_id": error_id,
            "category": category.value,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context or {},
        }

        # Log full error details internally (these logs should be secured)
        logger.error(
            f"Error {error_id}: {str(error)}", extra=log_context, exc_info=True
        )

        # For critical categories, also log as critical
        if category in [
            ErrorCategory.DATABASE,
            ErrorCategory.SYSTEM,
            ErrorCategory.CONFIGURATION,
        ]:
            logger.critical(
                f"Critical error {error_id} in {category.value}: {type(error).__name__}"
            )

        return error_id

    @classmethod
    def create_user_error_response(
        cls,
        error: Exception,
        category: ErrorCategory,
        custom_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        include_error_id: bool = True,
    ) -> Dict[str, Any]:
        """
        SECURITY: Create complete user error response with safe messaging

        Args:
            error: The exception that occurred
            category: Error category
            custom_message: Optional custom message
            context: Additional context
            user_id: User ID if applicable
            include_error_id: Whether to include error ID in response

        Returns:
            Dictionary with safe user message and error details
        """
        # Log error and get error ID
        error_id = cls.log_secure_error(error, category, context, user_id)

        # Get safe user message
        safe_message = cls.get_safe_error_message(category, custom_message)

        # Build response
        response = {
            "success": False,
            "message": safe_message,
            "category": category.value,
        }

        if include_error_id:
            response["error_id"] = error_id
            response["support_message"] = (
                f"If this issue persists, please contact support with error ID: {error_id}"
            )

        return response


class DatabaseErrorHandler:
    """SECURITY: Specialized handler for database errors"""

    @staticmethod
    def handle_db_error(
        error: Exception,
        operation: str = "database operation",
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Handle database errors with secure messaging"""
        return SecureErrorResponses.create_user_error_response(
            error=error,
            category=ErrorCategory.DATABASE,
            custom_message="Database temporarily unavailable. Please try again.",
            context={"operation": operation},
            user_id=user_id,
        )


class APIErrorHandler:
    """SECURITY: Specialized handler for external API errors"""

    @staticmethod
    def handle_api_error(
        error: Exception, service_name: str, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Handle external API errors with secure messaging"""
        return SecureErrorResponses.create_user_error_response(
            error=error,
            category=ErrorCategory.API_EXTERNAL,
            custom_message=f"{service_name} service temporarily unavailable.",
            context={"service": service_name},
            user_id=user_id,
        )


class NetworkErrorHandler:
    """SECURITY: Specialized handler for network errors"""

    @staticmethod
    def handle_network_error(
        error: Exception,
        operation: str = "network operation",
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Handle network errors with secure messaging"""
        return SecureErrorResponses.create_user_error_response(
            error=error,
            category=ErrorCategory.NETWORK,
            custom_message="Connection issue. Please check your internet connection.",
            context={"operation": operation},
            user_id=user_id,
        )


# Convenience functions for quick error handling
def safe_error_response(
    error: Exception,
    category: ErrorCategory,
    custom_message: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """SECURITY: Quick function to create safe error response"""
    return SecureErrorResponses.create_user_error_response(
        error, category, custom_message, user_id=user_id
    )


def safe_database_error(
    error: Exception, user_id: Optional[int] = None
) -> Dict[str, Any]:
    """SECURITY: Quick database error handler"""
    return DatabaseErrorHandler.handle_db_error(error, user_id=user_id)


def safe_api_error(
    error: Exception, service_name: str, user_id: Optional[int] = None
) -> Dict[str, Any]:
    """SECURITY: Quick API error handler"""
    return APIErrorHandler.handle_api_error(error, service_name, user_id)


def safe_network_error(
    error: Exception, user_id: Optional[int] = None
) -> Dict[str, Any]:
    """SECURITY: Quick network error handler"""
    return NetworkErrorHandler.handle_network_error(error, user_id=user_id)
