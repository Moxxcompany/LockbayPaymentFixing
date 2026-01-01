#!/usr/bin/env python3
"""
Security Monitoring Service
Comprehensive security monitoring, threat detection, and audit logging
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import ipaddress
from decimal import Decimal

from sqlalchemy import func
from database import SessionLocal
from models import (
    SecurityAlert,
    AuditLog,
    User,
    Transaction,
    Cashout,
)
from utils.atomic_transactions import atomic_transaction
from services.consolidated_notification_service import (
    consolidated_notification_service as NotificationService,
)

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventType(Enum):
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    MULTIPLE_LOGIN_FAILURES = "multiple_login_failures"

    # Financial events
    LARGE_TRANSACTION = "large_transaction"
    RAPID_TRANSACTIONS = "rapid_transactions"
    UNUSUAL_CASHOUT = "unusual_cashout"

    # System events
    WEBHOOK_TAMPERING = "webhook_tampering"
    API_ABUSE = "api_abuse"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    # Suspicious behavior
    IP_REPUTATION = "ip_reputation"
    GEOLOCATION_ANOMALY = "geolocation_anomaly"
    DEVICE_FINGERPRINT_CHANGE = "device_fingerprint_change"


@dataclass
class SecurityEvent:
    """Security event for analysis"""

    event_type: SecurityEventType
    user_id: Optional[int]
    severity: ThreatLevel
    description: str
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[Dict] = None
    timestamp: Optional[datetime] = None


@dataclass
class ThreatAssessment:
    """Threat assessment result"""

    risk_score: float  # 0-100
    threat_level: ThreatLevel
    recommended_actions: List[str]
    automated_actions: List[str]
    evidence: List[str]


class SecurityMonitoringService:
    """Comprehensive security monitoring and threat detection"""

    def __init__(self):
        self.notification_service = NotificationService

        # Risk scoring thresholds
        self.risk_thresholds = {
            ThreatLevel.LOW: 25.0,
            ThreatLevel.MEDIUM: 50.0,
            ThreatLevel.HIGH: 75.0,
            ThreatLevel.CRITICAL: 90.0,
        }

        # ADAPTIVE SECURITY: Legacy fallback thresholds only
        self.fallback_thresholds = {
            "large_transaction": Decimal("1000.00"),  # Fallback only
            "large_cashout": Decimal("500.00"),   # Fallback only
            "rapid_transaction_count": 5,            # Fallback only
            "rapid_transaction_window": 300,         # Fallback only
        }

        # Known malicious IP ranges (placeholder)
        self.malicious_ip_ranges = [
            # Add known malicious IP ranges here
        ]

        logger.info("Security monitoring service initialized")

    async def log_security_event(self, event: SecurityEvent) -> str:
        """Log a security event and perform threat assessment"""
        try:
            # Perform threat assessment
            assessment = await self._assess_threat(event)

            # Create security alert if significant
            alert_id = None
            if assessment.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                alert_id = await self._create_security_alert(event, assessment)

            # Log audit event
            await self._log_audit_event(event, assessment)

            # Execute automated actions
            if assessment.automated_actions:
                await self._execute_automated_actions(
                    event, assessment.automated_actions
                )

            # Send notifications for critical events
            if assessment.threat_level == ThreatLevel.CRITICAL:
                await self._send_critical_security_notification(event, assessment)

            logger.info(
                f"Security event logged: {event.event_type.value} - Risk: {assessment.risk_score}"
            )
            return alert_id or f"audit_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        except Exception as e:
            logger.error(f"Error logging security event: {e}")
            raise

    async def _assess_threat(self, event: SecurityEvent) -> ThreatAssessment:
        """Perform comprehensive threat assessment"""
        risk_score = 0.0
        evidence = []
        recommended_actions = []
        automated_actions = []

        # Base risk score by event type
        base_scores = {
            SecurityEventType.LOGIN_FAILED: 10.0,
            SecurityEventType.MULTIPLE_LOGIN_FAILURES: 60.0,
            SecurityEventType.LARGE_TRANSACTION: 30.0,
            SecurityEventType.RAPID_TRANSACTIONS: 50.0,
            SecurityEventType.UNUSUAL_CASHOUT: 40.0,
            SecurityEventType.WEBHOOK_TAMPERING: 80.0,
            SecurityEventType.API_ABUSE: 70.0,
            SecurityEventType.IP_REPUTATION: 85.0,
            SecurityEventType.GEOLOCATION_ANOMALY: 35.0,
        }

        risk_score += base_scores.get(event.event_type, 20.0)
        evidence.append(f"Event type: {event.event_type.value}")

        # IP reputation check
        if event.source_ip:
            ip_risk = await self._check_ip_reputation(event.source_ip)
            risk_score += ip_risk
            if ip_risk > 30:
                evidence.append(f"High-risk IP: {event.source_ip}")
                recommended_actions.append("Block IP address")

        # User behavior analysis
        if event.user_id:
            user_risk = await self._analyze_user_behavior(
                event.user_id, event.event_type
            )
            risk_score += user_risk
            if user_risk > 20:
                evidence.append("Suspicious user behavior pattern")
                recommended_actions.append("Enhanced monitoring for user")

        # Financial transaction analysis
        if event.event_type in [
            SecurityEventType.LARGE_TRANSACTION,
            SecurityEventType.RAPID_TRANSACTIONS,
        ]:
            financial_risk = await self._analyze_financial_patterns(event)
            risk_score += financial_risk
            if financial_risk > 25:
                evidence.append("Unusual financial activity pattern")
                recommended_actions.append("Manual review of transactions")

        # Determine threat level and actions
        if risk_score >= self.risk_thresholds[ThreatLevel.CRITICAL]:
            threat_level = ThreatLevel.CRITICAL
            automated_actions.extend(["rate_limit", "enhanced_verification"])
            recommended_actions.append("Immediate manual review")
        elif risk_score >= self.risk_thresholds[ThreatLevel.HIGH]:
            threat_level = ThreatLevel.HIGH
            automated_actions.append("rate_limit")
            recommended_actions.append("Review within 1 hour")
        elif risk_score >= self.risk_thresholds[ThreatLevel.MEDIUM]:
            threat_level = ThreatLevel.MEDIUM
            recommended_actions.append("Review within 24 hours")
        else:
            threat_level = ThreatLevel.LOW

        return ThreatAssessment(
            risk_score=min(risk_score, 100.0),  # Cap at 100
            threat_level=threat_level,
            recommended_actions=recommended_actions,
            automated_actions=automated_actions,
            evidence=evidence,
        )

    async def _check_ip_reputation(self, ip_address: str) -> float:
        """Check IP address reputation and return risk score"""
        try:
            ip = ipaddress.ip_address(ip_address)

            # Check against known malicious ranges
            for malicious_range in self.malicious_ip_ranges:
                if ip in ipaddress.ip_network(malicious_range):
                    return 50.0

            # Check for private/internal IPs (lower risk)
            if ip.is_private or ip.is_loopback:
                return 0.0

            # Check recent failed attempts from this IP
            with SessionLocal() as session:
                recent_failures = (
                    session.query(AuditLog)
                    .filter(
                        AuditLog.ip_address == ip_address,
                        AuditLog.event_type.in_(["login_failed", "api_abuse"]),
                        AuditLog.created_at >= datetime.utcnow() - timedelta(hours=24),
                    )
                    .count()
                )

                if recent_failures > 10:
                    return 40.0
                elif recent_failures > 5:
                    return 25.0
                elif recent_failures > 0:
                    return 10.0

            return 0.0

        except Exception as e:
            logger.error(f"Error checking IP reputation: {e}")
            return 15.0  # Default moderate risk for unknown IPs

    async def _analyze_user_behavior(
        self, user_id: int, event_type: SecurityEventType
    ) -> float:
        """Analyze user behavior patterns for anomalies"""
        try:
            risk_score = 0.0

            with SessionLocal() as session:
                # Check for rapid consecutive events
                recent_events = (
                    session.query(AuditLog)
                    .filter(
                        AuditLog.user_id == user_id,
                        AuditLog.created_at
                        >= datetime.utcnow() - timedelta(minutes=15),
                    )
                    .count()
                )

                if recent_events > 20:
                    risk_score += 30.0
                elif recent_events > 10:
                    risk_score += 15.0

                # Check for unusual activity times
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    # Check if current activity is outside normal hours
                    current_hour = datetime.utcnow().hour
                    if current_hour < 6 or current_hour > 23:  # Unusual hours
                        risk_score += 10.0

                    # Check account age
                    account_age = (datetime.utcnow() - user.created_at).days
                    if account_age < 7:  # New account
                        risk_score += 15.0

                # Check for multiple failed attempts
                if event_type == SecurityEventType.LOGIN_FAILED:
                    failed_attempts = (
                        session.query(AuditLog)
                        .filter(
                            AuditLog.user_id == user_id,
                            AuditLog.event_type == "login_failed",
                            AuditLog.created_at
                            >= datetime.utcnow() - timedelta(hours=1),
                        )
                        .count()
                    )

                    risk_score += min(failed_attempts * 10, 50)  # Cap at 50

            return risk_score

        except Exception as e:
            logger.error(f"Error analyzing user behavior: {e}")
            return 0.0

    async def _analyze_financial_patterns(self, event: SecurityEvent) -> float:
        """Analyze financial transaction patterns"""
        try:
            risk_score = 0.0

            if not event.user_id:
                return 0.0

            with SessionLocal() as session:
                # Check transaction velocity
                recent_transactions = (
                    session.query(Transaction)
                    .filter(
                        Transaction.user_id == event.user_id,
                        Transaction.created_at
                        >= datetime.utcnow()
                        - timedelta(
                            minutes=self.fallback_thresholds[
                                "rapid_transaction_window"
                            ]
                        ),
                    )
                    .count()
                )

                if (
                    recent_transactions
                    > self.fallback_thresholds["rapid_transaction_count"]
                ):
                    risk_score += 25.0

                # Check transaction amounts
                if event.metadata and "amount" in event.metadata:
                    amount = Decimal(str(event.metadata["amount"]))

                    # Check against user's normal transaction patterns
                    avg_transaction = session.query(
                        func.avg(Transaction.amount)
                    ).filter(
                        Transaction.user_id == event.user_id,
                        Transaction.created_at
                        >= datetime.utcnow() - timedelta(days=30),
                    ).scalar() or Decimal(
                        "0"
                    )

                    if (
                        avg_transaction > 0 and amount > avg_transaction * 5
                    ):  # 5x normal
                        risk_score += 20.0

                    # Check absolute thresholds
                    if amount > self.fallback_thresholds["large_transaction"]:
                        risk_score += 15.0

                # Check cashout patterns
                recent_cashouts = (
                    session.query(Cashout)
                    .filter(
                        Cashout.user_id == event.user_id,
                        Cashout.created_at
                        >= datetime.utcnow() - timedelta(hours=24),
                    )
                    .count()
                )

                if recent_cashouts > 3:
                    risk_score += 20.0

            return risk_score

        except Exception as e:
            logger.error(f"Error analyzing financial patterns: {e}")
            return 0.0

    async def _create_security_alert(
        self, event: SecurityEvent, assessment: ThreatAssessment
    ) -> str:
        """Create a security alert record"""
        try:
            with atomic_transaction() as session:
                alert_id = f"alert_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{event.event_type.value[:10]}"

                alert = SecurityAlert(
                    alert_id=alert_id,
                    alert_type=event.event_type.value,
                    severity=assessment.threat_level.value,
                    category=self._get_event_category(event.event_type),
                    description=event.description,
                    source_ip=event.source_ip,
                    user_id=event.user_id,
                    affected_entity_type=self._get_affected_entity_type(event),
                    affected_entity_id=str(event.user_id) if event.user_id else None,
                    event_data=event.metadata,
                    user_agent=event.user_agent,
                    risk_score=assessment.risk_score,
                    automated_action=(
                        ", ".join(assessment.automated_actions)
                        if assessment.automated_actions
                        else None
                    ),
                    status="new",
                )

                session.add(alert)
                logger.info(f"Created security alert: {alert_id}")
                return alert_id

        except Exception as e:
            logger.error(f"Error creating security alert: {e}")
            raise

    async def _log_audit_event(
        self, event: SecurityEvent, assessment: ThreatAssessment
    ):
        """Create audit log entry"""
        try:
            with atomic_transaction() as session:
                audit_log = AuditLog(
                    user_id=event.user_id,
                    event_type=event.event_type.value,
                    event_category=self._get_event_category(event.event_type),
                    description=event.description,
                    entity_type=self._get_affected_entity_type(event),
                    entity_id=str(event.user_id) if event.user_id else None,
                    ip_address=event.source_ip,
                    user_agent=event.user_agent,
                    audit_metadata=event.metadata,
                    risk_score=assessment.risk_score,
                    severity=assessment.threat_level.value,
                )

                session.add(audit_log)

        except Exception as e:
            logger.error(f"Error logging audit event: {e}")

    async def _execute_automated_actions(
        self, event: SecurityEvent, actions: List[str]
    ):
        """Execute automated security actions"""
        try:
            for action in actions:
                if action == "rate_limit":
                    await self._apply_rate_limit(event.source_ip, event.user_id)
                elif action == "enhanced_verification":
                    await self._require_enhanced_verification(event.user_id)
                elif action == "block_ip":
                    await self._block_ip_address(event.source_ip)

                logger.info(f"Executed automated action: {action}")

        except Exception as e:
            logger.error(f"Error executing automated actions: {e}")

    async def _apply_rate_limit(
        self, ip_address: Optional[str], user_id: Optional[int]
    ):
        """Apply rate limiting"""
        # Placeholder implementation
        logger.info(f"Applied rate limit - IP: {ip_address}, User: {user_id}")

    async def _require_enhanced_verification(self, user_id: Optional[int]):
        """Require enhanced verification for user"""
        if not user_id:
            return

        # Placeholder implementation - could update user security settings
        logger.info(f"Enhanced verification required for user: {user_id}")

    async def _block_ip_address(self, ip_address: Optional[str]):
        """Block IP address"""
        if not ip_address:
            return

        # Placeholder implementation
        logger.info(f"IP address blocked: {ip_address}")

    def _get_event_category(self, event_type: SecurityEventType) -> str:
        """Get category for event type"""
        auth_events = [
            SecurityEventType.LOGIN_SUCCESS,
            SecurityEventType.LOGIN_FAILED,
            SecurityEventType.MULTIPLE_LOGIN_FAILURES,
        ]
        financial_events = [
            SecurityEventType.LARGE_TRANSACTION,
            SecurityEventType.RAPID_TRANSACTIONS,
            SecurityEventType.UNUSUAL_CASHOUT,
        ]
        system_events = [
            SecurityEventType.WEBHOOK_TAMPERING,
            SecurityEventType.API_ABUSE,
            SecurityEventType.RATE_LIMIT_EXCEEDED,
        ]

        if event_type in auth_events:
            return "authentication"
        elif event_type in financial_events:
            return "financial"
        elif event_type in system_events:
            return "system"
        else:
            return "security"

    def _get_affected_entity_type(self, event: SecurityEvent) -> Optional[str]:
        """Get affected entity type from event"""
        if event.user_id:
            return "user"
        return None

    async def _send_critical_security_notification(
        self, event: SecurityEvent, assessment: ThreatAssessment
    ):
        """Send notification for critical security events"""
        try:
            message = "🚨 CRITICAL SECURITY ALERT\n\n"
            message += f"Event: {event.event_type.value}\n"
            message += f"Risk Score: {assessment.risk_score:.1f}\n"
            message += f"Description: {event.description}\n"

            if event.source_ip:
                message += f"Source IP: {event.source_ip}\n"
            if event.user_id:
                message += f"User ID: {event.user_id}\n"

            message += "\nEvidence:\n"
            for evidence in assessment.evidence:
                message += f"• {evidence}\n"

            message += "\nRecommended Actions:\n"
            for action in assessment.recommended_actions:
                message += f"• {action}\n"

            await self.notification_service.notify_all_admins(message=message)

        except Exception as e:
            logger.error(f"Error sending critical security notification: {e}")

    # Convenience methods for common security events
    async def log_login_attempt(
        self, user_id: Optional[int], success: bool, ip_address: str, user_agent: str
    ) -> str:
        """Log login attempt"""
        event_type = (
            SecurityEventType.LOGIN_SUCCESS
            if success
            else SecurityEventType.LOGIN_FAILED
        )
        description = f"Login {'successful' if success else 'failed'} for user {user_id or 'unknown'}"

        event = SecurityEvent(
            event_type=event_type,
            user_id=user_id,
            severity=ThreatLevel.LOW if success else ThreatLevel.MEDIUM,
            description=description,
            source_ip=ip_address,
            user_agent=user_agent,
            metadata={"success": success},
        )

        return await self.log_security_event(event)

    async def log_financial_transaction(
        self,
        user_id: int,
        transaction_type: str,
        amount: Decimal,
        currency: str,
        ip_address: Optional[str] = None,
    ) -> str:
        """Log financial transaction for monitoring"""
        # Determine if this is a large transaction
        is_large = amount >= self.fallback_thresholds["large_transaction"]
        event_type = (
            SecurityEventType.LARGE_TRANSACTION
            if is_large
            else SecurityEventType.LOGIN_SUCCESS
        )

        description = f"{transaction_type} transaction: {amount} {currency}"

        event = SecurityEvent(
            event_type=event_type,
            user_id=user_id,
            severity=ThreatLevel.MEDIUM if is_large else ThreatLevel.LOW,
            description=description,
            source_ip=ip_address,
            metadata={
                "transaction_type": transaction_type,
                "amount": str(amount),
                "currency": currency,
                "is_large": is_large,
            },
        )

        return await self.log_security_event(event)

    async def log_webhook_event(
        self,
        provider: str,
        signature_valid: bool,
        ip_address: str,
        suspicious: bool = False,
    ) -> str:
        """Log webhook security event"""
        if not signature_valid or suspicious:
            event_type = SecurityEventType.WEBHOOK_TAMPERING
            severity = ThreatLevel.HIGH
            description = f"Suspicious webhook from {provider} - Invalid signature or suspicious patterns"
        else:
            event_type = SecurityEventType.LOGIN_SUCCESS  # Normal webhook
            severity = ThreatLevel.LOW
            description = f"Valid webhook received from {provider}"

        event = SecurityEvent(
            event_type=event_type,
            user_id=None,
            severity=severity,
            description=description,
            source_ip=ip_address,
            metadata={
                "provider": provider,
                "signature_valid": signature_valid,
                "suspicious": suspicious,
            },
        )

        return await self.log_security_event(event)


# Global instance
security_monitoring_service = SecurityMonitoringService()


# Convenience functions
async def log_security_event(event_type: SecurityEventType, **kwargs) -> str:
    """Log a security event"""
    event = SecurityEvent(event_type=event_type, **kwargs)
    return await security_monitoring_service.log_security_event(event)


async def log_login_attempt(
    user_id: Optional[int], success: bool, ip_address: str, user_agent: str
) -> str:
    """Log login attempt"""
    return await security_monitoring_service.log_login_attempt(
        user_id, success, ip_address, user_agent
    )
