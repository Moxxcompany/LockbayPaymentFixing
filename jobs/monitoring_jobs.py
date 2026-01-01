"""
Monitoring Jobs for System and Service Health
"""

import logging
from services.unified_monitoring import unified_monitoring_service
from services.alert_manager import alert_manager

logger = logging.getLogger(__name__)


async def run_system_monitoring():
    """Run comprehensive system health monitoring"""
    try:
        logger.info("Starting system monitoring check...")

        # Run comprehensive health checks via unified monitoring
        monitoring_results = (
            await unified_monitoring_service.run_comprehensive_system_check()
        )

        # Send alerts if needed
        alerts_sent = await unified_monitoring_service.process_monitoring_alerts(
            monitoring_results
        )

        # Handle both int and dict returns from alerts_sent
        if isinstance(alerts_sent, dict):
            total_alerts = sum(alerts_sent.values())
        else:
            total_alerts = alerts_sent or 0
            
        logger.info(
            f"System monitoring completed - Alerts sent: {total_alerts}"
        )

        return {
            "system_status": monitoring_results.get("overall_status", "unknown"),
            "service_status": monitoring_results.get("service_status", "unknown"),
            "alerts_sent": alerts_sent,
        }

    except Exception as e:
        logger.error(f"System monitoring failed: {e}")

        # Send critical alert about monitoring failure
        try:
            await unified_monitoring_service.send_system_alert(
                title="Monitoring System Failure",
                message=f"Monitoring system failure: {str(e)}",
                priority="high"
            )
        except Exception as alert_error:
            logger.error(f"Failed to send monitoring failure alert: {alert_error}")

        raise


async def run_service_health_monitoring():
    """Run service health monitoring only (more frequent)"""
    try:
        logger.debug("Running service health check...")

        # Run service health checks via unified monitoring  
        service_results = await unified_monitoring_service.run_service_health_check()

        # Send alerts for critical service issues
        if service_results.get("overall_status") in ["critical"]:
            for service_name, service_result in service_results.get(
                "services", {}
            ).items():
                if service_result.get("status") in ["unhealthy", "error"]:
                    severity = "high"
                    await alert_manager.send_service_failure_alert(
                        service_name, service_result.get("errors", []), severity
                    )

        return {
            "service_status": service_results.get("overall_status"),
            "critical_services": [
                name
                for name, result in service_results.get("services", {}).items()
                if result.get("status") in ["unhealthy", "error"]
            ],
        }

    except Exception as e:
        logger.error(f"Service health monitoring failed: {e}")
        raise


async def run_balance_monitoring():
    """Run balance monitoring with enhanced alerting using BalanceGuard"""
    try:
        logger.debug("Running balance monitoring...")

        # Use BalanceGuard unified monitoring system
        from services.balance_guard import monitor_all_balances

        # Check all balances using BalanceGuard
        balance_results = await monitor_all_balances()

        # Extract alert information from BalanceGuard results
        alerts_sent = balance_results.get("alerts_sent", [])
        status = balance_results.get("status", "completed")

        logger.info(f"Balance monitoring completed - Status: {status}, Alerts: {len(alerts_sent)}")

        return {
            "status": status,
            "alerts_sent": alerts_sent,
            "results": balance_results,
        }

    except Exception as e:
        logger.error(f"Balance monitoring failed: {e}")

        # Alert about balance monitoring failure
        try:
            await alert_manager.send_system_alert(
                {
                    "check_type": "balance_monitoring",
                    "status": "critical",
                    "issues": [f"Balance monitoring failure: {str(e)}"],
                    "severity": "high",
                }
            )
        except Exception as alert_error:
            logger.error(
                f"Failed to send balance monitoring failure alert: {alert_error}"
            )

        raise
