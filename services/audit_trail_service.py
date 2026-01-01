"""
Audit Trail Service - Enhanced audit logging and reason capture
Ensures consistent reason capture for manual approvals and comprehensive audit trails
"""

import logging
from datetime import datetime
from typing import Dict, Any, List

from models import AuditLog, User, Cashout
from database import SessionLocal

logger = logging.getLogger(__name__)


class AuditTrailService:
    """Service for comprehensive audit trail management and reason capture"""

    # Event categories for better organization
    EVENT_CATEGORIES = {
        "cashout": "cashout_management",
        "admin_action": "admin_operations",
        "security": "security_events",
        "system": "system_operations",
        "user_action": "user_operations",
        "approval": "approval_workflow",
        "error": "error_handling",
    }

    # Severity levels
    SEVERITY_LEVELS = {
        "info": "low",
        "warning": "medium",
        "error": "high",
        "critical": "critical",
    }

    @classmethod
    async def log_admin_approval(
        cls,
        admin_id: int,
        cashout_id: str,
        approval_type: str,  # 'first', 'second', 'single'
        decision: str,  # 'approved', 'rejected'
        reason: str,
        additional_context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Log admin approval decisions with comprehensive reason capture
        Returns: {'logged': bool, 'audit_id': int, 'error': str}
        """
        try:
            with SessionLocal() as session:
                # Get cashout and admin details
                cashout = (
                    session.query(Cashout)
                    .filter(Cashout.cashout_id == cashout_id)
                    .first()
                )

                admin = session.query(User).filter(User.id == admin_id).first()

                if not cashout:
                    return {"logged": False, "error": "Cashout not found"}

                if not admin:
                    return {"logged": False, "error": "Admin not found"}

                # Prepare audit data
                audit_data = {
                    "cashout_id": cashout_id,
                    "admin_id": admin_id,
                    "admin_username": admin.username,
                    "approval_type": approval_type,
                    "decision": decision,
                    "reason": reason,
                    "cashout_amount": float(cashout.amount),
                    "cashout_currency": cashout.currency,
                    "cashout_type": cashout.cashout_type,
                    "cashout_status_before": cashout.status,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                # Add additional context
                if additional_context:
                    audit_data.update(additional_context)

                # Create detailed audit log
                audit_log = AuditLog(
                    user_id=cashout.user_id,  # The user whose cashout is being reviewed
                    event_type=f"admin_{decision}",
                    event_category=cls.EVENT_CATEGORIES["approval"],
                    entity_type="cashout",
                    entity_id=cashout_id,
                    description=f"Admin {approval_type} approval: {decision} - {reason}",
                    before_data={
                        "cashout_status": cashout.status,
                        "admin_approved": cashout.admin_approved,
                    },
                    after_data=audit_data,
                    severity=(
                        cls.SEVERITY_LEVELS["warning"]
                        if decision == "rejected"
                        else cls.SEVERITY_LEVELS["info"]
                    ),
                    ip_address=(
                        additional_context.get("ip_address")
                        if additional_context
                        else None
                    ),
                    user_agent=(
                        additional_context.get("user_agent")
                        if additional_context
                        else None
                    ),
                )

                session.add(audit_log)
                session.commit()

                logger.info(
                    f"Logged admin approval: {admin_id} {decision} cashout {cashout_id}"
                )

                return {
                    "logged": True,
                    "audit_id": audit_log.id,
                    "event_type": audit_log.event_type,
                }

        except Exception as e:
            logger.error(f"Error logging admin approval: {e}")
            return {"logged": False, "error": str(e)}

    @classmethod
    async def log_cashout_lifecycle_event(
        cls,
        cashout_id: str,
        event_type: str,
        event_description: str,
        triggered_by: int = None,  # User ID who triggered the event
        before_state: Dict[str, Any] = None,
        after_state: Dict[str, Any] = None,
        severity: str = "info",
        additional_data: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Log comprehensive cashout lifecycle events
        Returns: {'logged': bool, 'audit_id': int}
        """
        try:
            with SessionLocal() as session:
                cashout = (
                    session.query(Cashout)
                    .filter(Cashout.cashout_id == cashout_id)
                    .first()
                )

                if not cashout:
                    return {"logged": False, "error": "Cashout not found"}

                # Prepare comprehensive event data
                event_data = {
                    "cashout_id": cashout_id,
                    "cashout_amount": float(cashout.amount),
                    "cashout_currency": cashout.currency,
                    "cashout_type": cashout.cashout_type,
                    "current_status": cashout.status,
                    "event_timestamp": datetime.utcnow().isoformat(),
                    "triggered_by_user": triggered_by,
                }

                if additional_data:
                    event_data.update(additional_data)

                # Create audit log
                audit_log = AuditLog(
                    user_id=cashout.user_id,
                    event_type=event_type,
                    event_category=cls.EVENT_CATEGORIES["cashout"],
                    entity_type="cashout",
                    entity_id=cashout_id,
                    description=event_description,
                    before_data=before_state,
                    after_data=event_data,
                    severity=cls.SEVERITY_LEVELS.get(severity, "low"),
                )

                session.add(audit_log)
                session.commit()

                return {"logged": True, "audit_id": audit_log.id}

        except Exception as e:
            logger.error(f"Error logging cashout lifecycle event: {e}")
            return {"logged": False, "error": str(e)}

    @classmethod
    async def log_security_event(
        cls,
        event_type: str,
        description: str,
        user_id: int = None,
        entity_type: str = None,
        entity_id: str = None,
        risk_score: float = 0.0,
        ip_address: str = None,
        user_agent: str = None,
        additional_data: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Log security-related events with enhanced context
        Returns: {'logged': bool, 'audit_id': int}
        """
        try:
            with SessionLocal() as session:
                # Determine severity based on risk score
                if risk_score >= 0.8:
                    severity = "critical"
                elif risk_score >= 0.6:
                    severity = "high"
                elif risk_score >= 0.3:
                    severity = "medium"
                else:
                    severity = "low"

                security_data = {
                    "risk_score": risk_score,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                if additional_data:
                    security_data.update(additional_data)

                audit_log = AuditLog(
                    user_id=user_id,
                    event_type=event_type,
                    event_category=cls.EVENT_CATEGORIES["security"],
                    entity_type=entity_type or "security_event",
                    entity_id=entity_id,
                    description=description,
                    after_data=security_data,
                    risk_score=risk_score,
                    severity=severity,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

                session.add(audit_log)
                session.commit()

                logger.info(f"Logged security event: {event_type} (risk: {risk_score})")

                return {"logged": True, "audit_id": audit_log.id, "severity": severity}

        except Exception as e:
            logger.error(f"Error logging security event: {e}")
            return {"logged": False, "error": str(e)}

    @classmethod
    async def log_system_event(
        cls,
        event_type: str,
        description: str,
        component: str,
        severity: str = "info",
        error_details: str = None,
        performance_metrics: Dict[str, Any] = None,
        additional_data: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Log system-level events and errors
        Returns: {'logged': bool, 'audit_id': int}
        """
        try:
            with SessionLocal() as session:
                system_data = {
                    "component": component,
                    "timestamp": datetime.utcnow().isoformat(),
                    "error_details": error_details,
                    "performance_metrics": performance_metrics,
                }

                if additional_data:
                    system_data.update(additional_data)

                audit_log = AuditLog(
                    user_id=None,  # System events don't have a specific user
                    event_type=event_type,
                    event_category=cls.EVENT_CATEGORIES["system"],
                    entity_type="system",
                    entity_id=component,
                    description=description,
                    after_data=system_data,
                    severity=cls.SEVERITY_LEVELS.get(severity, "low"),
                )

                session.add(audit_log)
                session.commit()

                return {"logged": True, "audit_id": audit_log.id}

        except Exception as e:
            logger.error(f"Error logging system event: {e}")
            return {"logged": False, "error": str(e)}

    @classmethod
    def get_audit_trail(
        cls,
        entity_type: str = None,
        entity_id: str = None,
        user_id: int = None,
        event_category: str = None,
        severity: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Retrieve audit trail with filtering options
        Returns: {'audit_logs': list, 'total_count': int, 'filters_applied': dict}
        """
        try:
            with SessionLocal() as session:
                query = session.query(AuditLog)

                # Apply filters
                filters_applied = {}

                if entity_type:
                    query = query.filter(AuditLog.entity_type == entity_type)
                    filters_applied["entity_type"] = entity_type

                if entity_id:
                    query = query.filter(AuditLog.entity_id == entity_id)
                    filters_applied["entity_id"] = entity_id

                if user_id:
                    query = query.filter(AuditLog.user_id == user_id)
                    filters_applied["user_id"] = user_id

                if event_category:
                    query = query.filter(AuditLog.event_category == event_category)
                    filters_applied["event_category"] = event_category

                if severity:
                    query = query.filter(AuditLog.severity == severity)
                    filters_applied["severity"] = severity

                # Get total count before applying limit/offset
                total_count = query.count()

                # Apply pagination and ordering
                audit_logs = (
                    query.order_by(AuditLog.created_at.desc())
                    .offset(offset)
                    .limit(limit)
                    .all()
                )

                # Format results
                formatted_logs = []
                for log in audit_logs:
                    formatted_logs.append(
                        {
                            "id": log.id,
                            "user_id": log.user_id,
                            "event_type": log.event_type,
                            "event_category": log.event_category,
                            "entity_type": log.entity_type,
                            "entity_id": log.entity_id,
                            "description": log.description,
                            "severity": log.severity,
                            "risk_score": log.risk_score,
                            "created_at": log.created_at,
                            "before_data": log.before_data,
                            "after_data": log.after_data,
                            "ip_address": log.ip_address,
                        }
                    )

                return {
                    "audit_logs": formatted_logs,
                    "total_count": total_count,
                    "filters_applied": filters_applied,
                    "page_info": {
                        "limit": limit,
                        "offset": offset,
                        "returned_count": len(formatted_logs),
                    },
                }

        except Exception as e:
            logger.error(f"Error retrieving audit trail: {e}")
            return {"audit_logs": [], "total_count": 0, "error": str(e)}

    @classmethod
    async def generate_audit_summary_report(
        cls,
        start_date: datetime,
        end_date: datetime,
        include_categories: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive audit summary report
        Returns: {'summary': dict, 'top_events': list, 'statistics': dict}
        """
        try:
            with SessionLocal() as session:
                # Base query for date range
                query = session.query(AuditLog).filter(
                    AuditLog.created_at >= start_date, AuditLog.created_at <= end_date
                )

                # Apply category filter if specified
                if include_categories:
                    query = query.filter(
                        AuditLog.event_category.in_(include_categories)
                    )

                # Get all logs in the period
                audit_logs = query.all()

                # Generate statistics
                statistics = {
                    "total_events": len(audit_logs),
                    "events_by_category": {},
                    "events_by_severity": {},
                    "events_by_type": {},
                    "unique_users": set(),
                    "high_risk_events": 0,
                }

                # Analyze logs
                for log in audit_logs:
                    # Count by category
                    category = log.event_category
                    statistics["events_by_category"][category] = (
                        statistics["events_by_category"].get(category, 0) + 1
                    )

                    # Count by severity
                    severity = log.severity
                    statistics["events_by_severity"][severity] = (
                        statistics["events_by_severity"].get(severity, 0) + 1
                    )

                    # Count by event type
                    event_type = log.event_type
                    statistics["events_by_type"][event_type] = (
                        statistics["events_by_type"].get(event_type, 0) + 1
                    )

                    # Track unique users
                    if log.user_id:
                        statistics["unique_users"].add(log.user_id)

                    # Count high-risk events
                    if log.risk_score and log.risk_score >= 0.7:
                        statistics["high_risk_events"] += 1

                # Convert set to count
                statistics["unique_users"] = len(statistics["unique_users"])

                # Get top events (most frequent)
                top_events = [
                    {"event_type": event_type, "count": count}
                    for event_type, count in sorted(
                        statistics["events_by_type"].items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:10]
                ]

                # Generate summary
                summary = {
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "duration_days": (end_date - start_date).days,
                    },
                    "overview": {
                        "total_events": statistics["total_events"],
                        "unique_users": statistics["unique_users"],
                        "high_risk_events": statistics["high_risk_events"],
                        "categories_covered": len(statistics["events_by_category"]),
                    },
                    "health_indicators": {
                        "critical_events": statistics["events_by_severity"].get(
                            "critical", 0
                        ),
                        "error_events": statistics["events_by_severity"].get("high", 0),
                        "security_events": statistics["events_by_category"].get(
                            "security_events", 0
                        ),
                    },
                }

                return {
                    "summary": summary,
                    "top_events": top_events,
                    "statistics": statistics,
                    "generated_at": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            logger.error(f"Error generating audit summary report: {e}")
            return {"summary": {}, "top_events": [], "statistics": {}, "error": str(e)}
