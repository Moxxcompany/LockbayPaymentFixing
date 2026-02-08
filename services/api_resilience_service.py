"""
API Resilience Service - Enhanced retry mechanisms and error recovery
Provides robust API calling with exponential backoff, circuit breaker patterns, and health monitoring
"""

import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import random
import json

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CIRCUIT_OPEN = "circuit_open"


@dataclass
class ApiEndpoint:
    """Configuration for API endpoint resilience"""

    name: str
    url: str
    timeout_seconds: int = 30
    max_retries: int = 3
    base_delay: float = 1.0  # Base delay for exponential backoff
    max_delay: float = 60.0  # Maximum delay between retries
    circuit_breaker_threshold: int = 5  # Failures before circuit opens
    circuit_breaker_timeout: int = 300  # Seconds to keep circuit open
    health_check_interval: int = 60  # Seconds between health checks


@dataclass
class CircuitBreakerState:
    """Circuit breaker state for API endpoints"""

    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    status: ServiceStatus = ServiceStatus.HEALTHY
    circuit_open_time: Optional[datetime] = None
    consecutive_successes: int = 0


class ApiResilienceService:
    """Service providing enhanced API resilience with retry, circuit breaker, and health monitoring"""

    def __init__(self):
        self.circuit_states: Dict[str, CircuitBreakerState] = {}
        self.health_check_task = None
        self.session: Optional[aiohttp.ClientSession] = None

        # Pre-configured endpoints
        self.endpoints = {
            "blockbee": ApiEndpoint(
                name="blockbee",
                url="https://api.blockbee.io",
                timeout_seconds=30,
                max_retries=3,
                circuit_breaker_threshold=5,
            ),
            "fastforex": ApiEndpoint(
                name="fastforex",
                url="https://api.fastforex.io",
                timeout_seconds=15,
                max_retries=2,
                circuit_breaker_threshold=3,
            ),
            "tatum": ApiEndpoint(
                name="tatum",
                url="https://api.tatum.io",
                timeout_seconds=15,
                max_retries=2,
                circuit_breaker_threshold=3,
            ),
            "binance": ApiEndpoint(
                name="binance",
                url="https://api.binance.com",
                timeout_seconds=20,
                max_retries=2,
                circuit_breaker_threshold=4,
            ),
            "fincra": ApiEndpoint(
                name="fincra",
                url="https://sandboxapi.fincra.com",
                timeout_seconds=25,
                max_retries=3,
                circuit_breaker_threshold=4,
            ),
        }

        # Initialize circuit breaker states
        for endpoint_name in self.endpoints:
            self.circuit_states[endpoint_name] = CircuitBreakerState()

    async def start_monitoring(self):
        """Start background health monitoring"""
        if self.health_check_task is None:
            # OPTIMIZED: Enhanced persistent HTTP session with performance tuning
            connector = aiohttp.TCPConnector(
                limit=200,  # Increased total connection pool size
                limit_per_host=20,  # Increased per-host connection limit
                keepalive_timeout=120,  # Extended keep-alive to 2 minutes
                enable_cleanup_closed=True,
                ttl_dns_cache=300,  # DNS cache for 5 minutes
                use_dns_cache=True,
                # TCP keepalive enabled by default in aiohttp
            )

            # OPTIMIZED: Intelligent timeout configuration
            timeout = aiohttp.ClientTimeout(
                total=60,  # Extended total timeout
                connect=10,  # Connection timeout
                sock_read=30,  # Socket read timeout
            )
            self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)

            self.health_check_task = asyncio.create_task(self._monitor_api_health())
            logger.info("API resilience monitoring started with connection pooling")

    async def stop_monitoring(self):
        """Stop monitoring and cleanup resources"""
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass

        if self.session:
            await self.session.close()
            self.session = None

        logger.info("API resilience monitoring stopped")

    async def _monitor_api_health(self):
        """Background task to monitor API endpoint health"""
        while True:
            try:
                for endpoint_name, endpoint in self.endpoints.items():
                    await self._check_endpoint_health(endpoint_name, endpoint)

            except Exception as e:
                logger.error(f"Error in API health monitoring: {e}")

            # Wait before next health check cycle
            await asyncio.sleep(60)

    async def _check_endpoint_health(self, endpoint_name: str, endpoint: ApiEndpoint):
        """Check health of specific API endpoint"""
        circuit_state = self.circuit_states[endpoint_name]

        # If circuit is open, check if it's time to try again
        if circuit_state.status == ServiceStatus.CIRCUIT_OPEN:
            if (
                circuit_state.circuit_open_time
                and datetime.utcnow() - circuit_state.circuit_open_time
                > timedelta(seconds=endpoint.circuit_breaker_timeout)
            ):

                circuit_state.status = ServiceStatus.DEGRADED
                circuit_state.circuit_open_time = None
                logger.info(
                    f"Circuit breaker for {endpoint_name} moved to half-open state"
                )

        # Perform health check if not in circuit open state
        if circuit_state.status != ServiceStatus.CIRCUIT_OPEN:
            try:
                # Simple health check - adapt per service
                health_url = self._get_health_check_url(endpoint_name)

                if health_url and self.session:
                    async with self.session.get(
                        health_url, timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            self._record_success(endpoint_name)
                        else:
                            self._record_failure(
                                endpoint_name,
                                f"Health check returned {response.status}",
                            )

            except Exception as e:
                self._record_failure(endpoint_name, f"Health check failed: {str(e)}")

    def _get_health_check_url(self, endpoint_name: str) -> Optional[str]:
        """Get appropriate health check URL for each service"""
        health_checks = {
            "blockbee": "https://api.blockbee.io/info/",
            "tatum": "https://api.tatum.io/v4/data/rate/symbol?symbol=BTC&basePair=USD",
            "fastforex": "https://api.fastforex.io/currencies",  # Lightweight endpoint
            "binance": "https://api.binance.com/api/v3/ping",
            "fincra": "https://api.fincra.com/auth/healthz",  # Basic health endpoint
            "brevo": "https://api.brevo.com/v3/account",  # Email service health
        }
        return health_checks.get(endpoint_name)

    async def make_resilient_request(
        self,
        endpoint_name: str,
        method: str,
        url: str,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        custom_retries: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Make API request with full resilience (retry, circuit breaker, backoff)"""

        if endpoint_name not in self.endpoints:
            raise ValueError(f"Unknown endpoint: {endpoint_name}")

        endpoint = self.endpoints[endpoint_name]
        circuit_state = self.circuit_states[endpoint_name]

        # Check circuit breaker
        if circuit_state.status == ServiceStatus.CIRCUIT_OPEN:
            raise Exception(
                f"Circuit breaker open for {endpoint_name} - service unavailable"
            )

        max_retries = (
            custom_retries if custom_retries is not None else endpoint.max_retries
        )
        last_exception = None

        for attempt in range(max_retries + 1):  # +1 for initial attempt
            try:
                # Calculate delay for this attempt (exponential backoff with jitter)
                if attempt > 0:
                    delay = min(
                        endpoint.base_delay
                        * (2 ** (attempt - 1)),  # Exponential backoff
                        endpoint.max_delay,
                    )
                    # Add jitter to prevent thundering herd
                    jitter = random.uniform(0.1, 0.3) * delay
                    await asyncio.sleep(delay + jitter)

                    logger.info(
                        f"Retrying {endpoint_name} request (attempt {attempt + 1}/{max_retries + 1})"
                    )

                # Make the request
                if not self.session:
                    await self.start_monitoring()

                timeout = aiohttp.ClientTimeout(total=endpoint.timeout_seconds)

                async with self.session.request(
                    method=method.upper(),
                    url=url,
                    headers=headers or {},
                    params=params,
                    json=json_data,
                    timeout=timeout,
                ) as response:

                    # Check for successful response
                    if 200 <= response.status < 300:
                        self._record_success(endpoint_name)

                        try:
                            result = await response.json()
                            return {
                                "success": True,
                                "data": result,
                                "status_code": response.status,
                                "attempt": attempt + 1,
                            }
                        except json.JSONDecodeError:
                            # Return text if not JSON
                            text = await response.text()
                            return {
                                "success": True,
                                "data": text,
                                "status_code": response.status,
                                "attempt": attempt + 1,
                            }

                    # Handle error responses
                    else:
                        error_text = await response.text()
                        error_msg = f"HTTP {response.status}: {error_text}"

                        # Don't retry on client errors (4xx), only server errors (5xx)
                        if 400 <= response.status < 500:
                            self._record_failure(endpoint_name, error_msg)
                            raise Exception(
                                f"Client error for {endpoint_name}: {error_msg}"
                            )

                        # Server error - will retry
                        last_exception = Exception(
                            f"Server error for {endpoint_name}: {error_msg}"
                        )
                        logger.warning(
                            f"Server error on attempt {attempt + 1}: {error_msg}"
                        )
                        continue

            except asyncio.TimeoutError:
                last_exception = Exception(
                    f"Timeout for {endpoint_name} after {endpoint.timeout_seconds}s"
                )
                logger.warning(f"Timeout on attempt {attempt + 1} for {endpoint_name}")
                continue

            except aiohttp.ClientError as e:
                last_exception = Exception(
                    f"Network error for {endpoint_name}: {str(e)}"
                )
                logger.warning(f"Network error on attempt {attempt + 1}: {str(e)}")
                continue

            except Exception as e:
                last_exception = e
                logger.warning(f"Unexpected error on attempt {attempt + 1}: {str(e)}")
                continue

        # All retries exhausted
        self._record_failure(endpoint_name, str(last_exception))

        return {
            "success": False,
            "error": str(last_exception),
            "attempts": max_retries + 1,
            "endpoint": endpoint_name,
        }

    def _record_success(self, endpoint_name: str):
        """Record successful API call"""
        circuit_state = self.circuit_states[endpoint_name]
        circuit_state.consecutive_successes += 1
        circuit_state.failure_count = 0  # Reset failure count

        # Restore to healthy if enough successes
        if (
            circuit_state.status == ServiceStatus.DEGRADED
            and circuit_state.consecutive_successes >= 3
        ):
            circuit_state.status = ServiceStatus.HEALTHY
            logger.info(f"Service {endpoint_name} restored to healthy status")

    def _record_failure(self, endpoint_name: str, error_message: str):
        """Record failed API call and update circuit breaker state"""
        circuit_state = self.circuit_states[endpoint_name]
        circuit_state.failure_count += 1
        circuit_state.last_failure_time = datetime.utcnow()
        circuit_state.consecutive_successes = 0

        endpoint = self.endpoints[endpoint_name]

        # Check if we should open the circuit breaker
        if circuit_state.failure_count >= endpoint.circuit_breaker_threshold:
            circuit_state.status = ServiceStatus.CIRCUIT_OPEN
            circuit_state.circuit_open_time = datetime.utcnow()

            logger.warning(
                f"Circuit breaker OPENED for {endpoint_name} after {circuit_state.failure_count} failures"
            )

            # Alert admin about circuit breaker
            asyncio.create_task(
                self._send_circuit_breaker_alert(endpoint_name, error_message)
            )

        elif circuit_state.failure_count >= endpoint.circuit_breaker_threshold // 2:
            circuit_state.status = ServiceStatus.DEGRADED
            logger.warning(
                f"Service {endpoint_name} marked as DEGRADED after {circuit_state.failure_count} failures"
            )

    async def _send_circuit_breaker_alert(self, endpoint_name: str, error_message: str):
        """Send alert when circuit breaker opens"""
        try:
            # Alert service handled via unified notification hub
            from config import Config
            from telegram import Bot

            bot_token = getattr(Config, "BOT_TOKEN", None)
            if not bot_token:
                logger.error("Bot token not available for circuit breaker alert")
                return
            Bot(bot_token)

            alert_message = f"""🚨 <b>Circuit Breaker Alert</b>

⚠️ <b>Service:</b> {endpoint_name.upper()}
🔴 <b>Status:</b> Circuit Breaker OPEN
📊 <b>Threshold:</b> Multiple failures detected

<b>Last Error:</b> {error_message[:200]}

🔄 <b>Recovery:</b> Automatic retry in 5 minutes
💡 <b>Impact:</b> {endpoint_name} requests temporarily blocked

<i>System will automatically recover when service is healthy</i>"""

            from services.consolidated_notification_service import (
                consolidated_notification_service as notification_hub,
            )

            await notification_hub.send_telegram_group_message(
                alert_message, parse_mode="HTML"
            )

        except Exception as e:
            logger.error(f"Failed to send circuit breaker alert: {e}")

    def get_service_status(self, endpoint_name: str) -> Dict[str, Any]:
        """Get current status of service"""
        if endpoint_name not in self.circuit_states:
            return {"status": "unknown", "error": "Service not monitored"}

        circuit_state = self.circuit_states[endpoint_name]
        endpoint = self.endpoints[endpoint_name]

        return {
            "endpoint": endpoint_name,
            "status": circuit_state.status.value,
            "failure_count": circuit_state.failure_count,
            "consecutive_successes": circuit_state.consecutive_successes,
            "last_failure": (
                circuit_state.last_failure_time.isoformat()
                if circuit_state.last_failure_time
                else None
            ),
            "circuit_open_time": (
                circuit_state.circuit_open_time.isoformat()
                if circuit_state.circuit_open_time
                else None
            ),
            "circuit_breaker_threshold": endpoint.circuit_breaker_threshold,
            "max_retries": endpoint.max_retries,
        }

    def get_all_service_status(self) -> Dict[str, Any]:
        """Get status of all monitored services"""
        return {
            endpoint_name: self.get_service_status(endpoint_name)
            for endpoint_name in self.endpoints
        }

    def force_circuit_reset(self, endpoint_name: str) -> bool:
        """Manually reset circuit breaker (admin function)"""
        if endpoint_name not in self.circuit_states:
            return False

        circuit_state = self.circuit_states[endpoint_name]
        circuit_state.failure_count = 0
        circuit_state.consecutive_successes = 0
        circuit_state.status = ServiceStatus.HEALTHY
        circuit_state.circuit_open_time = None
        circuit_state.last_failure_time = None

        logger.info(f"Circuit breaker manually reset for {endpoint_name}")
        return True


# Global instance
api_resilience_service = ApiResilienceService()
