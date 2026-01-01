"""
Unified Background Monitoring Jobs
Consolidates system monitoring, service health, and balance monitoring jobs
"""

import logging
from services.unified_monitoring import unified_monitoring_service

logger = logging.getLogger(__name__)

# ============ UNIFIED MONITORING JOBS ============


async def run_comprehensive_system_monitoring():
    """
    Run comprehensive system health monitoring
    Consolidates system, service, and security monitoring
    """
    try:
        logger.info("Starting comprehensive system monitoring check...")

        # Use the unified monitoring service for complete system check
        system_results = await unified_monitoring_service.run_full_system_check()

        status = system_results.get("overall_status", "unknown")
        alerts_sent = system_results.get("alerts_sent", [])

        logger.info(
            f"Comprehensive system monitoring completed - Status: {status}, Alerts sent: {len(alerts_sent)}"
        )

        return {
            "status": status,
            "alerts_sent": alerts_sent,
            "timestamp": system_results.get("timestamp"),
            "health_summary": system_results.get("health_results", {}).get(
                "summary", {}
            ),
            "security_status": system_results.get("security_results", {}).get(
                "status", "unknown"
            ),
        }

    except Exception as e:
        logger.error(f"Comprehensive system monitoring failed: {e}")

        # Send critical alert about monitoring failure
        try:
            await unified_monitoring_service.send_system_alert(
                {
                    "check_type": "comprehensive_monitoring",
                    "status": "critical",
                    "issues": [f"Comprehensive monitoring failure: {str(e)}"],
                    "severity": "high",
                }
            )
        except Exception as alert_error:
            logger.error(f"Failed to send monitoring failure alert: {alert_error}")

        raise


async def run_service_health_monitoring():
    """
    Run service health monitoring only (more frequent)
    Checks external API services: BlockBee, Fincra, Binance
    """
    try:
        logger.debug("Running service health monitoring...")

        # Run service health checks via unified monitoring
        service_results = await unified_monitoring_service.run_service_health_check()

        status = service_results.get("overall_status", "unknown")
        critical_services = service_results.get("critical_services", [])

        if critical_services:
            logger.warning(f"Critical services detected: {critical_services}")
        else:
            logger.debug(f"All services healthy - Status: {status}")

        return {
            "service_status": status,
            "critical_services": critical_services,
            "services": service_results.get("services", {}),
            "timestamp": service_results.get("timestamp"),
        }

    except Exception as e:
        logger.error(f"Service health monitoring failed: {e}")

        # Send alert about service monitoring failure
        try:
            await unified_monitoring_service.send_system_alert(
                {
                    "check_type": "service_monitoring",
                    "status": "critical",
                    "issues": [f"Service monitoring failure: {str(e)}"],
                    "severity": "high",
                }
            )
        except Exception as alert_error:
            logger.error(
                f"Failed to send service monitoring failure alert: {alert_error}"
            )

        raise


async def run_balance_monitoring():
    """
    Run unified balance monitoring for all payment providers
    Checks Fincra and Binance balances with enhanced alerting
    """
    try:
        logger.debug("Running unified balance monitoring...")

        # Use the unified monitoring service for balance monitoring
        # Use BalanceGuard unified monitoring system
        from services.balance_guard import monitor_all_balances
        balance_results = await monitor_all_balances()

        status = balance_results.get("status", "unknown")
        alerts_sent = balance_results.get("alerts_sent", [])

        if alerts_sent:
            logger.warning(f"Balance alerts sent for: {', '.join(alerts_sent)}")
        else:
            logger.info("All balance checks completed - no alerts needed")

        return {
            "status": status,
            "alerts_sent": alerts_sent,
            "results": balance_results.get("results", {}),
            "timestamp": balance_results.get("timestamp"),
        }

    except Exception as e:
        logger.error(f"Balance monitoring failed: {e}")

        # Alert about balance monitoring failure via unified system
        try:
            await unified_monitoring_service.send_system_alert(
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


# ============ LEGACY COMPATIBILITY JOBS ============
# These maintain backward compatibility with existing scheduler configurations


async def run_system_monitoring():
    """Legacy compatibility wrapper for comprehensive system monitoring"""
    return await run_comprehensive_system_monitoring()


async def check_fincra_balance():
    """
    Legacy compatibility: Check Fincra balance only
    Maintained for backward compatibility with existing scheduler configs
    """
    try:
        logger.info("Starting Fincra balance monitoring check...")

        # Run the unified balance monitoring and extract Fincra results
        balance_results = await run_balance_monitoring()

        # Extract Fincra-specific results for legacy compatibility
        fincra_data = balance_results.get("results", {}).get("fincra", {})
        status = fincra_data.get("status", "unknown")
        balance_formatted = fincra_data.get("formatted_balance", "Unknown")

        if status == "low_balance_alert_sent":
            logger.warning(
                f"LOW BALANCE ALERT SENT - Fincra balance: {balance_formatted}"
            )
        elif status == "low_balance_cooldown":
            logger.info(
                f"Low balance detected but in cooldown period - Balance: {balance_formatted}"
            )
        elif status == "balance_healthy":
            logger.info(f"Fincra balance healthy - Balance: {balance_formatted}")
        elif status == "error":
            logger.error(
                f"Error checking Fincra balance: {fincra_data.get('message', 'Unknown error')}"
            )
        elif status == "service_unavailable":
            logger.info("Fincra service not configured - skipping balance check")

        return {
            "status": status,
            "message": fincra_data.get("message", ""),
            "formatted_balance": balance_formatted,
            "timestamp": balance_results.get("timestamp"),
        }

    except Exception as e:
        logger.error(f"Error in Fincra balance monitoring job: {e}")
        return {"status": "job_error", "message": str(e), "timestamp": None}


async def check_binance_balance():
    """
    Legacy compatibility: Check Binance USDT balance only
    Maintained for backward compatibility with existing scheduler configs
    """
    try:
        logger.info("Starting Binance balance monitoring check...")

        # Run the unified balance monitoring and extract Binance results
        balance_results = await run_balance_monitoring()

        # Extract Binance-specific results for legacy compatibility
        binance_data = balance_results.get("results", {}).get("binance", {})
        status = binance_data.get("status", "unknown")
        balance_formatted = binance_data.get("formatted_balance", "Unknown")

        if status == "low_balance_alert_sent":
            logger.warning(
                f"LOW BALANCE ALERT SENT - Binance USDT balance: {balance_formatted}"
            )
        elif status == "low_balance_cooldown":
            logger.info(
                f"Low USDT balance detected but in cooldown period - Balance: {balance_formatted}"
            )
        elif status == "balance_healthy":
            logger.info(f"Binance USDT balance healthy - Balance: {balance_formatted}")
        elif status == "service_unavailable":
            logger.info("Binance service not configured - skipping balance check")
        elif status == "error":
            logger.error(
                f"Error checking Binance balance: {binance_data.get('message', 'Unknown error')}"
            )

        return {
            "status": status,
            "message": binance_data.get("message", ""),
            "formatted_balance": balance_formatted,
            "timestamp": balance_results.get("timestamp"),
        }

    except Exception as e:
        logger.error(f"Error in Binance balance monitoring job: {e}")
        return {"status": "job_error", "message": str(e), "timestamp": None}


async def check_all_balances():
    """
    Legacy compatibility: Check both Fincra and Binance balances
    Maintained for backward compatibility with existing scheduler configs
    """
    try:
        logger.info("Starting unified balance monitoring check (Fincra + Binance)...")

        # Use the unified balance monitoring directly
        result = await run_balance_monitoring()

        alerts_sent = result.get("alerts_sent", [])
        timestamp = result.get("timestamp", "Unknown")

        if alerts_sent:
            logger.warning(
                f"LOW BALANCE ALERTS SENT for: {', '.join(alerts_sent)} at {timestamp}"
            )
        else:
            logger.info(
                f"All balance checks completed - no alerts needed at {timestamp}"
            )

        # Log individual service statuses for debugging (legacy format)
        if result.get("results", {}).get("fincra"):
            fincra_status = result["results"]["fincra"].get("status", "unknown")
            fincra_balance = result["results"]["fincra"].get(
                "formatted_balance", "Unknown"
            )
            logger.info(f"Fincra: {fincra_status} - {fincra_balance}")

        if result.get("results", {}).get("binance"):
            binance_status = result["results"]["binance"].get("status", "unknown")
            binance_balance = result["results"]["binance"].get(
                "formatted_balance", "Unknown"
            )
            logger.info(f"Binance: {binance_status} - {binance_balance}")

        # Return legacy-compatible format
        return {
            "alerts_sent": alerts_sent,
            "timestamp": timestamp,
            "fincra": result.get("results", {}).get("fincra", {}),
            "binance": result.get("results", {}).get("binance", {}),
        }

    except Exception as e:
        logger.error(f"Error in unified balance monitoring job: {e}")
        return {
            "status": "job_error",
            "message": str(e),
            "alerts_sent": [],
            "timestamp": None,
        }


# ============ HEALTH CHECK JOBS ============


async def run_quick_health_check():
    """
    Quick health check for frequent monitoring
    Returns basic system status without full diagnostics
    """
    try:
        logger.debug("Running quick health check...")

        # Get health summary from unified monitoring
        health_summary = await unified_monitoring_service.get_health_summary()

        status = health_summary.get("status", "unknown")
        issues = health_summary.get("issues", [])

        if issues:
            logger.debug(f"Health check found {len(issues)} issues: {issues}")

        return {
            "status": status,
            "issues_count": len(issues),
            "issues": issues[:3],  # Only return first 3 for quick check
            "timestamp": health_summary.get("timestamp"),
        }

    except Exception as e:
        logger.error(f"Quick health check failed: {e}")
        return {
            "status": "error",
            "issues_count": 1,
            "issues": [f"Health check failed: {str(e)}"],
            "timestamp": None,
        }


# ============ CONSOLIDATED UTILITIES ============


async def get_monitoring_status():
    """
    Get current status of all monitoring systems
    Useful for debugging and admin dashboards
    """
    try:
        # Get comprehensive status from unified monitoring
        health_data = await unified_monitoring_service.get_comprehensive_health()

        return {
            "overall_status": health_data.get("status"),
            "components": health_data.get("components", {}),
            "summary": health_data.get("summary", {}),
            "issues": health_data.get("issues", []),
            "timestamp": health_data.get("timestamp"),
            "monitoring_service": "unified_monitoring_service",
        }

    except Exception as e:
        logger.error(f"Failed to get monitoring status: {e}")
        return {
            "overall_status": "error",
            "error": str(e),
            "timestamp": None,
            "monitoring_service": "unified_monitoring_service",
        }


# ============ PING CHECK ============


async def ping_monitoring_system():
    """Simple ping to verify monitoring system is responding"""
    try:
        ping_result = await unified_monitoring_service.ping_check()
        logger.debug("Monitoring system ping successful")
        return ping_result

    except Exception as e:
        logger.error(f"Monitoring system ping failed: {e}")
        return {"status": "error", "error": str(e), "timestamp": None}


# ============ EXPORT FOR SCHEDULER ============

# Export the main job functions for use by the scheduler
__all__ = [
    # Primary unified jobs
    "run_comprehensive_system_monitoring",
    "run_service_health_monitoring",
    "run_balance_monitoring",
    "run_quick_health_check",
    # Legacy compatibility jobs
    "run_system_monitoring",
    "check_fincra_balance",
    "check_binance_balance",
    "check_all_balances",
    # Utilities
    "get_monitoring_status",
    "ping_monitoring_system",
]
