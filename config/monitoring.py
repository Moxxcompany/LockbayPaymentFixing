"""
Configuration settings for system monitoring and alerts
"""

import os
from datetime import timedelta


class MonitoringConfig:
    """Configuration for system monitoring services"""

    # System monitoring intervals
    SYSTEM_MONITOR_INTERVAL_MINUTES = int(
        os.getenv("SYSTEM_MONITOR_INTERVAL_MINUTES", "5")
    )
    SERVICE_HEALTH_CHECK_INTERVAL_MINUTES = int(
        os.getenv("SERVICE_HEALTH_CHECK_INTERVAL_MINUTES", "1")
    )

    # Database monitoring
    DB_CONNECTION_TIMEOUT_SECONDS = int(
        os.getenv("DB_CONNECTION_TIMEOUT_SECONDS", "30")
    )
    DB_QUERY_TIMEOUT_SECONDS = int(os.getenv("DB_QUERY_TIMEOUT_SECONDS", "10"))

    # Transaction monitoring thresholds
    HIGH_VALUE_TRANSACTION_THRESHOLD_USD = float(
        os.getenv("HIGH_VALUE_TRANSACTION_THRESHOLD_USD", "5000.0")
    )
    SUSPICIOUS_ACTIVITY_THRESHOLD = int(
        os.getenv("SUSPICIOUS_ACTIVITY_THRESHOLD", "10")
    )

    # API service monitoring
    API_TIMEOUT_SECONDS = int(os.getenv("API_TIMEOUT_SECONDS", "30"))
    API_RETRY_ATTEMPTS = int(os.getenv("API_RETRY_ATTEMPTS", "3"))

    # Alert cooldowns (to prevent spam)
    SERVICE_ALERT_COOLDOWN_MINUTES = int(
        os.getenv("SERVICE_ALERT_COOLDOWN_MINUTES", "15")
    )
    SYSTEM_ALERT_COOLDOWN_MINUTES = int(
        os.getenv("SYSTEM_ALERT_COOLDOWN_MINUTES", "30")
    )

    # Critical thresholds
    FAILED_API_CALLS_THRESHOLD = int(os.getenv("FAILED_API_CALLS_THRESHOLD", "5"))
    DATABASE_ERROR_THRESHOLD = int(os.getenv("DATABASE_ERROR_THRESHOLD", "3"))

    @classmethod
    def get_service_alert_cooldown(cls) -> timedelta:
        """Get service alert cooldown period"""
        return timedelta(minutes=cls.SERVICE_ALERT_COOLDOWN_MINUTES)

    @classmethod
    def get_system_alert_cooldown(cls) -> timedelta:
        """Get system alert cooldown period"""
        return timedelta(minutes=cls.SYSTEM_ALERT_COOLDOWN_MINUTES)
