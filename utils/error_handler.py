"""Comprehensive error handling system with standardized responses"""

import logging
import traceback
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import asyncio
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Error categories for classification"""

    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    PAYMENT = "payment"
    EXTERNAL_API = "external_api"
    DATABASE = "database"
    NETWORK = "network"
    SYSTEM = "system"
    BUSINESS_LOGIC = "business_logic"
    USER_INPUT = "user_input"
    CONFIGURATION = "configuration"


class ErrorSeverity(Enum):
    """Error severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class StandardError:
    """Standard error response structure"""

    code: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    user_message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    trace_id: Optional[str] = None
    retry_after: Optional[int] = None
    recoverable: bool = True

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


class ErrorCodes:
    """Centralized error codes"""

    # Validation Errors (1000-1999)
    INVALID_INPUT = "1001"
    MISSING_REQUIRED_FIELD = "1002"
    INVALID_FORMAT = "1003"
    VALUE_OUT_OF_RANGE = "1004"
    INVALID_AMOUNT = "1005"
    INVALID_ADDRESS = "1006"

    # Authentication Errors (2000-2999)
    UNAUTHORIZED = "2001"
    INVALID_CREDENTIALS = "2002"
    TOKEN_EXPIRED = "2003"
    ACCOUNT_LOCKED = "2004"
    VERIFICATION_REQUIRED = "2005"

    # Authorization Errors (3000-3999)
    FORBIDDEN = "3001"
    INSUFFICIENT_PERMISSIONS = "3002"
    FEATURE_DISABLED = "3003"
    REGION_RESTRICTED = "3004"

    # Rate Limiting (4000-4999)
    RATE_LIMIT_EXCEEDED = "4001"
    TOO_MANY_REQUESTS = "4002"
    QUOTA_EXCEEDED = "4003"

    # Payment Errors (5000-5999)
    INSUFFICIENT_FUNDS = "5001"
    PAYMENT_FAILED = "5002"
    INVALID_PAYMENT_METHOD = "5003"
    PAYMENT_TIMEOUT = "5004"
    CASHOUT_FAILED = "5005"
    ESCROW_ERROR = "5006"

    # External API Errors (6000-6999)
    EXTERNAL_SERVICE_UNAVAILABLE = "6001"
    API_QUOTA_EXCEEDED = "6002"
    EXTERNAL_TIMEOUT = "6003"
    INVALID_API_RESPONSE = "6004"

    # Database Errors (7000-7999)
    DATABASE_ERROR = "7001"
    CONNECTION_FAILED = "7002"
    TRANSACTION_FAILED = "7003"
    CONSTRAINT_VIOLATION = "7004"

    # System Errors (8000-8999)
    INTERNAL_ERROR = "8001"
    SERVICE_UNAVAILABLE = "8002"
    MAINTENANCE_MODE = "8003"
    CONFIGURATION_ERROR = "8004"

    # Business Logic Errors (9000-9999)
    ESCROW_NOT_FOUND = "9001"
    INVALID_ESCROW_STATE = "9002"
    TRADE_ALREADY_COMPLETED = "9003"
    INSUFFICIENT_BALANCE = "9004"
    MINIMUM_AMOUNT_NOT_MET = "9005"


class ErrorResponseBuilder:
    """Builder for standardized error responses"""

    @staticmethod
    def validation_error(message: str, details: Optional[Dict] = None) -> StandardError:
        """Create validation error"""
        return StandardError(
            code=ErrorCodes.INVALID_INPUT,
            message=f"Validation failed: {message}",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            user_message="Please check your input and try again.",
            details=details,
        )

    @staticmethod
    def authentication_error(message: str = "Authentication required") -> StandardError:
        """Create authentication error"""
        return StandardError(
            code=ErrorCodes.UNAUTHORIZED,
            message=message,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.MEDIUM,
            user_message="Please verify your identity to continue.",
            recoverable=True,
        )

    @staticmethod
    def rate_limit_error(retry_after: int = 60) -> StandardError:
        """Create rate limit error"""
        return StandardError(
            code=ErrorCodes.RATE_LIMIT_EXCEEDED,
            message="Rate limit exceeded",
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            user_message=f"Too many requests. Please wait {retry_after} seconds and try again.",
            retry_after=retry_after,
        )

    @staticmethod
    def payment_error(
        message: str, code: str = ErrorCodes.PAYMENT_FAILED
    ) -> StandardError:
        """Create payment error"""
        return StandardError(
            code=code,
            message=f"Payment error: {message}",
            category=ErrorCategory.PAYMENT,
            severity=ErrorSeverity.HIGH,
            user_message="Payment processing failed. Please try again or contact support.",
            recoverable=True,
        )

    @staticmethod
    def external_api_error(service: str, message: str) -> StandardError:
        """Create external API error"""
        return StandardError(
            code=ErrorCodes.EXTERNAL_SERVICE_UNAVAILABLE,
            message=f"{service} service error: {message}",
            category=ErrorCategory.EXTERNAL_API,
            severity=ErrorSeverity.HIGH,
            user_message="External service is temporarily unavailable. Please try again later.",
            details={"service": service},
        )

    @staticmethod
    def database_error(message: str) -> StandardError:
        """Create database error"""
        return StandardError(
            code=ErrorCodes.DATABASE_ERROR,
            message=f"Database error: {message}",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.CRITICAL,
            user_message="System temporarily unavailable. Please try again later.",
            recoverable=False,
        )

    @staticmethod
    def business_logic_error(
        message: str, code: str, user_message: str
    ) -> StandardError:
        """Create business logic error"""
        return StandardError(
            code=code,
            message=message,
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            user_message=user_message,
            recoverable=True,
        )


class RetryConfig:
    """Retry configuration for error handling"""

    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
    ):
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay


class RetryHandler:
    """Retry mechanism for recoverable errors"""

    @staticmethod
    async def retry_async(func, config: RetryConfig, *args, **kwargs):
        """Retry async function with exponential backoff"""
        last_exception = None

        for attempt in range(config.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                # Check if error is retryable
                if not RetryHandler._is_retryable(e):
                    raise e

                if attempt < config.max_attempts - 1:
                    delay = min(
                        config.delay * (config.backoff_factor**attempt),
                        config.max_delay,
                    )
                    logger.warning(
                        f"Retry attempt {attempt + 1} failed, retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All retry attempts failed: {e}")

        raise last_exception

    @staticmethod
    def retry_sync(func, config: RetryConfig, *args, **kwargs):
        """Retry sync function with exponential backoff"""
        import time

        last_exception = None

        for attempt in range(config.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if not RetryHandler._is_retryable(e):
                    raise e

                if attempt < config.max_attempts - 1:
                    delay = min(
                        config.delay * (config.backoff_factor**attempt),
                        config.max_delay,
                    )
                    logger.warning(
                        f"Retry attempt {attempt + 1} failed, retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)

        raise last_exception

    @staticmethod
    def _is_retryable(exception: Exception) -> bool:
        """Check if exception is retryable"""
        retryable_exceptions = [
            "TimeoutError",
            "ConnectionError",
            "HTTPError",
            "TemporaryFailure",
        ]

        exception_name = exception.__class__.__name__
        return any(retryable in exception_name for retryable in retryable_exceptions)


class ErrorHandler:
    """Comprehensive error handling system"""

    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.circuit_breakers: Dict[str, Dict] = {}

    def handle_error(
        self, error: Exception, context: Optional[Dict] = None
    ) -> StandardError:
        """Handle any exception and return standardized error"""
        try:
            # Classify error
            standard_error = self._classify_error(error, context)

            # Log error
            self._log_error(standard_error, error, context)

            # Update metrics
            self._update_error_metrics(standard_error)

            # Check circuit breaker
            self._check_circuit_breaker(standard_error)

            return standard_error

        except Exception as e:
            logger.critical(f"Error handler failed: {e}")
            return self._create_fallback_error()

    def _classify_error(
        self, error: Exception, context: Optional[Dict]
    ) -> StandardError:
        """Classify exception into standard error"""
        error_name = error.__class__.__name__
        error_message = str(error)

        # Authentication errors
        if (
            "authentication" in error_message.lower()
            or "unauthorized" in error_message.lower()
        ):
            return ErrorResponseBuilder.authentication_error(error_message)

        # Rate limiting errors
        if (
            "rate limit" in error_message.lower()
            or "too many requests" in error_message.lower()
        ):
            return ErrorResponseBuilder.rate_limit_error()

        # Payment errors
        if any(
            keyword in error_message.lower()
            for keyword in ["payment", "insufficient", "balance"]
        ):
            return ErrorResponseBuilder.payment_error(error_message)

        # Database errors
        if any(
            keyword in error_name.lower()
            for keyword in ["database", "sql", "connection"]
        ):
            return ErrorResponseBuilder.database_error(error_message)

        # External API errors
        if any(
            keyword in error_message.lower()
            for keyword in ["api", "service", "timeout", "network"]
        ):
            service = context.get("service", "external") if context else "external"
            return ErrorResponseBuilder.external_api_error(service, error_message)

        # Validation errors
        if any(
            keyword in error_name.lower() for keyword in ["validation", "value", "type"]
        ):
            return ErrorResponseBuilder.validation_error(error_message)

        # Default to system error
        return StandardError(
            code=ErrorCodes.INTERNAL_ERROR,
            message=f"Unexpected error: {error_message}",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            user_message="An unexpected error occurred. Please try again.",
            details={"exception_type": error_name},
        )

    def _log_error(
        self,
        standard_error: StandardError,
        original_error: Exception,
        context: Optional[Dict],
    ):
        """Log error with appropriate level"""
        log_data = {
            "error_code": standard_error.code,
            "category": standard_error.category.value,
            "severity": standard_error.severity.value,
            "message": standard_error.message,
            "original_error": str(original_error),
            "context": context,
            "traceback": (
                traceback.format_exc()
                if standard_error.severity
                in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
                else None
            ),
        }

        if standard_error.severity == ErrorSeverity.CRITICAL:
            logger.critical(json.dumps(log_data))
        elif standard_error.severity == ErrorSeverity.HIGH:
            logger.error(json.dumps(log_data))
        elif standard_error.severity == ErrorSeverity.MEDIUM:
            logger.warning(json.dumps(log_data))
        else:
            logger.info(json.dumps(log_data))

    def _update_error_metrics(self, error: StandardError):
        """Update error metrics for monitoring"""
        error_key = f"{error.category.value}:{error.code}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

        # Alert on high error rates
        if self.error_counts[error_key] > 100:  # Threshold
            logger.warning(
                f"High error rate detected: {error_key} - {self.error_counts[error_key]} occurrences"
            )

    def _check_circuit_breaker(self, error: StandardError):
        """Implement circuit breaker pattern"""
        if error.category in [ErrorCategory.EXTERNAL_API, ErrorCategory.DATABASE]:
            service_key = (
                error.details.get("service", "unknown") if error.details else "unknown"
            )

            if service_key not in self.circuit_breakers:
                self.circuit_breakers[service_key] = {
                    "failures": 0,
                    "last_failure": None,
                    "state": "closed",  # closed, open, half-open
                }

            breaker = self.circuit_breakers[service_key]
            breaker["failures"] += 1
            breaker["last_failure"] = datetime.utcnow()

            # Open circuit after 5 failures
            if breaker["failures"] >= 5 and breaker["state"] == "closed":
                breaker["state"] = "open"
                logger.warning(f"Circuit breaker opened for service: {service_key}")

    def _create_fallback_error(self) -> StandardError:
        """Create fallback error when error handler fails"""
        return StandardError(
            code=ErrorCodes.INTERNAL_ERROR,
            message="Critical system error",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            user_message="System is experiencing issues. Please try again later.",
            recoverable=False,
        )

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_counts": self.error_counts.copy(),
            "circuit_breakers": self.circuit_breakers.copy(),
        }


# Telegram-specific error handling
async def telegram_error_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle Telegram bot errors"""
    error = context.error
    error_handler = ErrorHandler()

    # Create context for error handling
    error_context = {
        "user_id": update.effective_user.id if update.effective_user else None,
        "chat_id": update.effective_chat.id if update.effective_chat else None,
        "update_type": type(update).__name__,
        "service": "telegram",
    }

    # Handle error
    standard_error = error_handler.handle_error(error, error_context)

    # Send user-friendly message
    if update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ {standard_error.user_message}",
            )
        except Exception as e:
            logger.error(f"Failed to send error message to user: {e}")


# Global error handler instance
error_handler = ErrorHandler()


def handle_error(error: Exception, context: Optional[Dict] = None) -> StandardError:
    """Convenience function to handle errors"""
    return error_handler.handle_error(error, context)


def retry_on_error(config: RetryConfig = None):
    """Decorator for automatic retry on error"""
    if config is None:
        config = RetryConfig()

    def decorator(func):
        if asyncio.iscoroutinefunction(func):

            async def async_wrapper(*args, **kwargs):
                return await RetryHandler.retry_async(func, config, *args, **kwargs)

            return async_wrapper
        else:

            def sync_wrapper(*args, **kwargs):
                return RetryHandler.retry_sync(func, config, *args, **kwargs)

            return sync_wrapper

    return decorator
