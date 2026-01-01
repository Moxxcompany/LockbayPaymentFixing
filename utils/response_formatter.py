"""Response formatting utilities for consistent API responses"""

import logging
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import json

from utils.error_handler import StandardError

logger = logging.getLogger(__name__)


class ResponseStatus(Enum):
    """Response status types"""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PARTIAL = "partial"


@dataclass
class StandardResponse:
    """Standard API response structure"""

    status: ResponseStatus
    message: str
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class PaginatedResponse:
    """Paginated response structure"""

    items: List[Any]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ResponseFormatter:
    """Utility class for formatting API responses"""

    @staticmethod
    def success(
        data: Any = None,
        message: str = "Operation successful",
        metadata: Optional[Dict] = None,
    ) -> StandardResponse:
        """Create success response"""
        return StandardResponse(
            status=ResponseStatus.SUCCESS, message=message, data=data, metadata=metadata
        )

    @staticmethod
    def error(error: StandardError, message: Optional[str] = None) -> StandardResponse:
        """Create error response from StandardError"""
        return StandardResponse(
            status=ResponseStatus.ERROR,
            message=message or error.user_message,
            error={
                "code": error.code,
                "category": error.category.value,
                "severity": error.severity.value,
                "details": error.details,
                "retry_after": error.retry_after,
                "recoverable": error.recoverable,
            },
        )

    @staticmethod
    def warning(
        data: Any = None,
        message: str = "Operation completed with warnings",
        warnings: Optional[List[str]] = None,
    ) -> StandardResponse:
        """Create warning response"""
        metadata = {"warnings": warnings} if warnings else None
        return StandardResponse(
            status=ResponseStatus.WARNING, message=message, data=data, metadata=metadata
        )

    @staticmethod
    def paginated(
        items: List[Any],
        total: int,
        page: int,
        per_page: int,
        message: str = "Data retrieved successfully",
    ) -> StandardResponse:
        """Create paginated response"""
        total_pages = (total + per_page - 1) // per_page

        pagination_data = PaginatedResponse(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

        return StandardResponse(
            status=ResponseStatus.SUCCESS,
            message=message,
            data=asdict(pagination_data),
            metadata={
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_items": total,
                    "items_per_page": per_page,
                }
            },
        )

    @staticmethod
    def partial(
        data: Any,
        message: str = "Operation partially completed",
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
    ) -> StandardResponse:
        """Create partial success response"""
        metadata = {}
        if errors:
            metadata["errors"] = errors
        if warnings:
            metadata["warnings"] = warnings

        return StandardResponse(
            status=ResponseStatus.PARTIAL,
            message=message,
            data=data,
            metadata=metadata if metadata else None,
        )

    @staticmethod
    def to_dict(response: StandardResponse) -> Dict[str, Any]:
        """Convert response to dictionary"""
        return asdict(response)

    @staticmethod
    def to_json(response: StandardResponse) -> str:
        """Convert response to JSON string"""
        return json.dumps(asdict(response), default=str, indent=2)


class TelegramResponseFormatter:
    """Specialized formatter for Telegram bot responses"""

    @staticmethod
    def format_error_message(error: StandardError) -> str:
        """Format error message for Telegram"""
        emoji_map = {
            "validation": "⚠️",
            "authentication": "🔐",
            "authorization": "🚫",
            "rate_limit": "⏰",
            "payment": "💳",
            "external_api": "🌐",
            "database": "💾",
            "system": "🔧",
            "business_logic": "📋",
        }

        emoji = emoji_map.get(error.category.value, "❌")
        message = f"{emoji} {error.user_message}"

        if error.retry_after:
            message += f"\n\n⏱️ Please try again in {error.retry_after} seconds."

        return message

    @staticmethod
    def format_success_message(data: Any, operation: str) -> str:
        """Format success message for Telegram"""
        base_message = f"✅ {operation} completed successfully!"

        if isinstance(data, dict):
            if "amount" in data and "currency" in data:
                base_message += f"\n💰 Amount: {data['amount']} {data['currency']}"

            if "transaction_id" in data:
                base_message += f"\n🆔 Transaction ID: {data['transaction_id']}"

            if "status" in data:
                base_message += f"\n📊 Status: {data['status']}"

        return base_message

    @staticmethod
    def format_warning_message(message: str, warnings: List[str]) -> str:
        """Format warning message for Telegram"""
        formatted = f"⚠️ {message}"

        if warnings:
            formatted += "\n\n📋 Warnings:"
            for warning in warnings:
                formatted += f"\n• {warning}"

        return formatted

    @staticmethod
    def format_list_response(
        items: List[Dict], title: str, item_formatter: Optional[callable] = None
    ) -> str:
        """Format list response for Telegram"""
        if not items:
            return f"📋 {title}\n\nNo items found."

        message = f"📋 {title} ({len(items)} items):\n\n"

        for i, item in enumerate(items[:10], 1):  # Limit to 10 items
            if item_formatter:
                formatted_item = item_formatter(item)
            else:
                formatted_item = f"Item {i}: {item.get('name', 'Unknown')}"

            message += f"{i}. {formatted_item}\n"

        if len(items) > 10:
            message += f"\n... and {len(items) - 10} more items"

        return message


class WebhookResponseFormatter:
    """Specialized formatter for webhook responses"""

    @staticmethod
    def success_response(
        message: str = "Webhook processed successfully",
    ) -> Dict[str, Any]:
        """Standard webhook success response"""
        return {
            "status": "success",
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def error_response(error: StandardError) -> Dict[str, Any]:
        """Standard webhook error response"""
        return {
            "status": "error",
            "error": {
                "code": error.code,
                "message": error.message,
                "category": error.category.value,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def validation_error_response(errors: List[str]) -> Dict[str, Any]:
        """Webhook validation error response"""
        return {
            "status": "error",
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": errors,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }


# Response formatter instances
response_formatter = ResponseFormatter()
telegram_formatter = TelegramResponseFormatter()
webhook_formatter = WebhookResponseFormatter()


def success_response(
    data: Any = None, message: str = "Operation successful"
) -> StandardResponse:
    """Convenience function for success response"""
    return response_formatter.success(data, message)


def error_response(error: StandardError) -> StandardResponse:
    """Convenience function for error response"""
    return response_formatter.error(error)


def format_telegram_error(error: StandardError) -> str:
    """Convenience function for Telegram error formatting"""
    return telegram_formatter.format_error_message(error)


def format_telegram_success(data: Any, operation: str) -> str:
    """Convenience function for Telegram success formatting"""
    return telegram_formatter.format_success_message(data, operation)
