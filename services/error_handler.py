"""
Enhanced Error Handler with Monitoring Integration
Captures and alerts on critical system and service failures
"""

import logging
from datetime import datetime
from typing import Dict, Any
from services.alert_manager import alert_manager
from services.blockbee_service import BlockBeeAPIError

logger = logging.getLogger(__name__)


class MonitoringErrorHandler:
    """Enhanced error handler with monitoring and alerting"""

    def __init__(self):
        self.error_counts = {}
        self.last_error_times = {}

    async def handle_api_error(
        self, service_name: str, error: Exception, context: str = None
    ) -> None:
        """Handle API service errors with monitoring and alerting"""
        try:
            error_key = f"{service_name}_{context or 'general'}"

            # Track error occurrence
            self._record_error(error_key, str(error))

            # Determine if this is a critical failure
            is_critical = self._is_critical_error(service_name, error)

            if is_critical:
                # Send immediate alert for critical failures
                await self._send_critical_service_alert(service_name, error, context)

            # Log error with appropriate level
            if is_critical:
                logger.error(f"CRITICAL {service_name} API error in {context}: {error}")
            else:
                logger.warning(f"{service_name} API error in {context}: {error}")

        except Exception as alert_error:
            logger.error(f"Failed to handle API error alerting: {alert_error}")

    async def handle_database_error(
        self, error: Exception, query_context: str = None
    ) -> None:
        """Handle database errors with monitoring"""
        try:
            context = f"Database operation: {query_context or 'unknown'}"

            # Record database error
            self._record_error("database", str(error))

            # Database errors are always critical
            await alert_manager.send_system_alert(
                {
                    "check_type": "database_error",
                    "status": "critical",
                    "issues": [f"Database error in {context}: {str(error)}"],
                    "severity": "high",
                }
            )

            logger.error(f"CRITICAL database error in {context}: {error}")

        except Exception as alert_error:
            logger.error(f"Failed to handle database error alerting: {alert_error}")

    async def handle_cashout_error(
        self, error: Exception, cashout_id: int, service: str
    ) -> None:
        """Handle cashout processing errors"""
        try:
            context = f"Cashout {cashout_id} via {service or 'unknown'}"

            # Record cashout error
            self._record_error(f"cashout_{service}", str(error))

            # Cashout errors can be financial - treat as critical
            await alert_manager.send_system_alert(
                {
                    "check_type": "cashout_processing",
                    "status": "critical",
                    "issues": [
                        f"Cashout processing failed: {context} - {str(error)}"
                    ],
                    "severity": "high",
                }
            )

            logger.error(f"CRITICAL cashout error: {context} - {error}")

        except Exception as alert_error:
            logger.error(f"Failed to handle cashout error alerting: {alert_error}")

    async def handle_exchange_order_error(
        self, error: Exception, order_id: int, operation: str
    ) -> None:
        """Handle exchange order processing errors"""
        try:
            context = f"Exchange order {order_id} - {operation}"

            # Record exchange error
            self._record_error("exchange_orders", str(error))

            # Check if this is a critical service failure (like BlockBee 404)
            is_critical = self._is_critical_error("exchange", error)

            if is_critical:
                await alert_manager.send_service_failure_alert(
                    "exchange_processing",
                    [f"Exchange order processing failed: {context} - {str(error)}"],
                    "high",
                )
                logger.error(f"CRITICAL exchange order error: {context} - {error}")
            else:
                logger.warning(f"Exchange order error: {context} - {error}")

        except Exception as alert_error:
            logger.error(
                f"Failed to handle exchange order error alerting: {alert_error}"
            )

    def _record_error(self, error_type: str, error_message: str):
        """Record error occurrence for pattern analysis"""
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0

        self.error_counts[error_type] += 1
        self.last_error_times[error_type] = datetime.utcnow()

        # Reset counter if more than 1 hour since last error
        last_time = self.last_error_times.get(error_type)
        if last_time and (datetime.utcnow() - last_time).total_seconds() > 3600:
            self.error_counts[error_type] = 1

    def _is_critical_error(self, service_name: str, error: Exception) -> bool:
        """Determine if an error is critical and requires immediate alerting"""
        error_str = str(error).lower()

        # BlockBee specific critical errors
        if service_name in ["blockbee", "exchange"] and isinstance(
            error, BlockBeeAPIError
        ):
            if "404" in error_str and "callback not found" in error_str:
                return True  # This is the specific issue from logs
            if "500" in error_str or "timeout" in error_str:
                return True

        # Fincra critical errors
        if service_name == "fincra":
            if "unauthorized" in error_str or "authentication" in error_str:
                return True
            if "insufficient" in error_str and "balance" in error_str:
                return True

        # Binance critical errors
        if service_name == "binance":
            if "api key" in error_str or "signature" in error_str:
                return True
            if "insufficient" in error_str and "balance" in error_str:
                return True

        # General critical patterns
        critical_patterns = [
            "connection refused",
            "timeout",
            "network error",
            "database",
            "authentication failed",
            "unauthorized",
            "internal server error",
            "500",
            "service unavailable",
        ]

        return any(pattern in error_str for pattern in critical_patterns)

    async def _send_critical_service_alert(
        self, service_name: str, error: Exception, context: str
    ):
        """Send immediate alert for critical service failures"""
        try:
            error_message = str(error)

            # Enhanced error context for BlockBee 404 errors
            if "404" in error_message and "callback not found" in error_message:
                enhanced_message = "BlockBee API returning 404 errors - Callback/Address issues detected. This affects exchange order processing and deposit confirmations."
            else:
                enhanced_message = (
                    f"{service_name.upper()} service failure detected: {error_message}"
                )

            await alert_manager.send_service_failure_alert(
                service_name,
                [enhanced_message, f"Context: {context}" if context else ""],
                "high",
            )

        except Exception as e:
            logger.error(f"Failed to send critical service alert: {e}")

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors for monitoring"""
        return {
            "error_counts": self.error_counts.copy(),
            "last_error_times": {
                k: v.isoformat() for k, v in self.last_error_times.items()
            },
            "total_errors": sum(self.error_counts.values()),
        }


# Global instance
monitoring_error_handler = MonitoringErrorHandler()


# Convenience functions for easy integration
async def handle_api_error(service_name: str, error: Exception, context: str = None):
    """Handle API service error with monitoring"""
    await monitoring_error_handler.handle_api_error(service_name, error, context)


async def handle_database_error(error: Exception, query_context: str = None):
    """Handle database error with monitoring"""
    await monitoring_error_handler.handle_database_error(error, query_context)


async def handle_cashout_error(error: Exception, cashout_id: int, service: str):
    """Handle cashout error with monitoring"""
    await monitoring_error_handler.handle_cashout_error(
        error, cashout_id, service
    )


async def handle_exchange_order_error(error: Exception, order_id: int, operation: str):
    """Handle exchange order error with monitoring"""
    await monitoring_error_handler.handle_exchange_order_error(
        error, order_id, operation
    )
