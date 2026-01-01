"""
SECURITY: Authentication Monitoring and Alerting System
Provides comprehensive monitoring of authentication events and security threats
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Security threat levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuthEventType(Enum):
    """Authentication event types"""

    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    ADMIN_ACCESS = "admin_access"
    ADMIN_DENIED = "admin_denied"
    SESSION_EXPIRED = "session_expired"
    LOCKOUT_TRIGGERED = "lockout_triggered"
    BRUTE_FORCE_DETECTED = "brute_force_detected"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


@dataclass
class AuthEvent:
    """Authentication event record"""

    event_type: AuthEventType
    user_id: int
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    threat_level: ThreatLevel = ThreatLevel.LOW
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class AuthenticationMonitor:
    """SECURITY: Comprehensive authentication monitoring system"""

    def __init__(self):
        self._events: List[AuthEvent] = []
        self._user_patterns: Dict[int, List[AuthEvent]] = {}
        self._threat_counters: Dict[ThreatLevel, int] = {
            level: 0 for level in ThreatLevel
        }
        self._alert_thresholds = {
            "failed_attempts_per_hour": 10,
            "admin_failures_per_hour": 3,
            "suspicious_ips_per_hour": 5,
            "brute_force_threshold": 20,
        }

    def record_event(self, event: AuthEvent):
        """Record authentication event and analyze for threats"""
        # Store event
        self._events.append(event)

        # Update user patterns
        if event.user_id not in self._user_patterns:
            self._user_patterns[event.user_id] = []
        self._user_patterns[event.user_id].append(event)

        # Update threat counters
        self._threat_counters[event.threat_level] += 1

        # Analyze for security threats
        self._analyze_security_threats(event)

        # Cleanup old events (keep 24 hours)
        self._cleanup_old_events()

        # Log event
        self._log_auth_event(event)

    def _analyze_security_threats(self, event: AuthEvent):
        """SECURITY: Analyze authentication patterns for threats"""
        user_id = event.user_id
        recent_events = self._get_recent_events(user_id, hours=1)

        # Check for brute force attacks
        failed_attempts = len(
            [e for e in recent_events if e.event_type == AuthEventType.LOGIN_FAILURE]
        )
        if failed_attempts >= self._alert_thresholds["brute_force_threshold"]:
            self._trigger_security_alert(
                ThreatLevel.CRITICAL,
                f"Brute force attack detected from user {user_id}",
                {
                    "user_id": user_id,
                    "failed_attempts": failed_attempts,
                    "timeframe": "1 hour",
                },
            )

        # Check for admin access patterns
        if event.event_type == AuthEventType.ADMIN_DENIED:
            admin_failures = len(
                [e for e in recent_events if e.event_type == AuthEventType.ADMIN_DENIED]
            )
            if admin_failures >= self._alert_thresholds["admin_failures_per_hour"]:
                self._trigger_security_alert(
                    ThreatLevel.HIGH,
                    f"Multiple admin access attempts from user {user_id}",
                    {
                        "user_id": user_id,
                        "admin_failures": admin_failures,
                        "timeframe": "1 hour",
                    },
                )

        # Check for IP-based suspicious activity
        if event.ip_address:
            ip_events = self._get_recent_events_by_ip(event.ip_address, hours=1)
            unique_users = len(set(e.user_id for e in ip_events))
            if unique_users >= self._alert_thresholds["suspicious_ips_per_hour"]:
                self._trigger_security_alert(
                    ThreatLevel.MEDIUM,
                    f"Suspicious activity from IP {event.ip_address}",
                    {
                        "ip_address": event.ip_address,
                        "unique_users": unique_users,
                        "timeframe": "1 hour",
                    },
                )

    def _get_recent_events(self, user_id: int, hours: int = 24) -> List[AuthEvent]:
        """Get recent events for a specific user"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [
            e for e in self._user_patterns.get(user_id, []) if e.timestamp >= cutoff
        ]

    def _get_recent_events_by_ip(
        self, ip_address: str, hours: int = 1
    ) -> List[AuthEvent]:
        """Get recent events from a specific IP address"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [
            e
            for e in self._events
            if e.ip_address == ip_address and e.timestamp >= cutoff
        ]

    def _trigger_security_alert(self, level: ThreatLevel, message: str, details: Dict):
        """Trigger security alert"""
        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.value,
            "message": message,
            "details": details,
        }

        logger.critical(
            f"SECURITY ALERT [{level.value.upper()}]: {message} - {details}"
        )

        # In production, this would integrate with alerting systems
        # For now, we log critical alerts
        if level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            logger.critical(
                f"IMMEDIATE ATTENTION REQUIRED: {json.dumps(alert, indent=2)}"
            )

    def _cleanup_old_events(self):
        """Cleanup events older than 24 hours"""
        cutoff = datetime.utcnow() - timedelta(hours=24)

        # Cleanup main events list
        self._events = [e for e in self._events if e.timestamp >= cutoff]

        # Cleanup user patterns
        for user_id in list(self._user_patterns.keys()):
            self._user_patterns[user_id] = [
                e for e in self._user_patterns[user_id] if e.timestamp >= cutoff
            ]
            if not self._user_patterns[user_id]:
                del self._user_patterns[user_id]

    def _log_auth_event(self, event: AuthEvent):
        """Log authentication event"""
        log_data = {
            "event_type": event.event_type.value,
            "user_id": event.user_id,
            "timestamp": event.timestamp.isoformat(),
            "threat_level": event.threat_level.value,
            "details": event.details,
        }

        if event.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            logger.warning(f"High-risk auth event: {json.dumps(log_data)}")
        else:
            logger.info(f"Auth event: {event.event_type.value} - User {event.user_id}")

    def get_security_summary(self) -> Dict:
        """Get security monitoring summary"""
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)
        last_24h = now - timedelta(hours=24)

        recent_events = [e for e in self._events if e.timestamp >= last_hour]
        daily_events = [e for e in self._events if e.timestamp >= last_24h]

        return {
            "monitoring_period": "24 hours",
            "total_events_24h": len(daily_events),
            "events_last_hour": len(recent_events),
            "threat_levels_24h": {
                level.value: len([e for e in daily_events if e.threat_level == level])
                for level in ThreatLevel
            },
            "failed_logins_24h": len(
                [e for e in daily_events if e.event_type == AuthEventType.LOGIN_FAILURE]
            ),
            "admin_access_attempts_24h": len(
                [
                    e
                    for e in daily_events
                    if e.event_type
                    in [AuthEventType.ADMIN_ACCESS, AuthEventType.ADMIN_DENIED]
                ]
            ),
            "unique_users_24h": len(set(e.user_id for e in daily_events)),
            "lockouts_24h": len(
                [
                    e
                    for e in daily_events
                    if e.event_type == AuthEventType.LOCKOUT_TRIGGERED
                ]
            ),
        }


# Global instance
auth_monitor = AuthenticationMonitor()


def record_auth_event(
    event_type: AuthEventType,
    user_id: int,
    threat_level: ThreatLevel = ThreatLevel.LOW,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict] = None,
):
    """Record authentication event"""
    event = AuthEvent(
        event_type=event_type,
        user_id=user_id,
        timestamp=datetime.utcnow(),
        ip_address=ip_address,
        user_agent=user_agent,
        threat_level=threat_level,
        details=details or {},
    )
    auth_monitor.record_event(event)


def get_security_summary() -> Dict:
    """Get security monitoring summary"""
    return auth_monitor.get_security_summary()
