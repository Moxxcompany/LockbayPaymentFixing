"""Real-time metrics dashboard and monitoring system"""

import logging
import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import psutil
import os

logger = logging.getLogger(__name__)


@dataclass
class MetricValue:
    """Individual metric value with timestamp"""

    value: float
    timestamp: datetime
    labels: Optional[Dict[str, str]] = None


@dataclass
class PerformanceMetrics:
    """System performance metrics"""

    cpu_usage: float
    memory_usage: float
    memory_total: int
    memory_available: int
    disk_usage: float
    disk_total: int
    disk_free: int
    load_average: List[float]
    process_count: int
    network_io: Dict[str, int]

    @classmethod
    def collect(cls) -> "PerformanceMetrics":
        """Collect current system metrics"""
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        network = psutil.net_io_counters()

        return cls(
            cpu_usage=psutil.cpu_percent(interval=1),
            memory_usage=memory.percent,
            memory_total=memory.total,
            memory_available=memory.available,
            disk_usage=disk.percent if disk.total > 0 else 0,
            disk_total=disk.total,
            disk_free=disk.free,
            load_average=(
                list(os.getloadavg()) if hasattr(os, "getloadavg") else [0, 0, 0]
            ),
            process_count=len(psutil.pids()),
            network_io={
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv,
            },
        )


@dataclass
class ApplicationMetrics:
    """Application-specific metrics"""

    active_users: int
    total_requests: int
    request_rate: float
    error_rate: float
    response_time_avg: float
    response_time_p95: float
    response_time_p99: float
    active_escrows: int
    completed_transactions: int
    wallet_balances_usd: float
    pending_cashouts: int
    database_connections: int
    cache_hit_rate: float
    queue_size: int


class MetricsCollector:
    """Comprehensive metrics collection system"""

    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self.metrics: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=retention_hours * 60)
        )  # 1 per minute
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.start_time = time.time()
        self.request_times: deque = deque(maxlen=1000)  # Last 1000 requests

    def increment_counter(
        self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None
    ):
        """Increment a counter metric"""
        key = self._build_key(name, labels)
        self.counters[key] += value

        # Record to time series
        self.metrics[key].append(
            MetricValue(
                value=self.counters[key], timestamp=datetime.now(), labels=labels
            )
        )

    def set_gauge(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ):
        """Set a gauge metric"""
        key = self._build_key(name, labels)
        self.gauges[key] = value

        # Record to time series
        self.metrics[key].append(
            MetricValue(value=value, timestamp=datetime.now(), labels=labels)
        )

    def record_histogram(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ):
        """Record a value to histogram"""
        key = self._build_key(name, labels)
        self.histograms[key].append(value)

        # Keep only recent values (last hour)
        cutoff_time = time.time() - 3600
        self.histograms[key] = [v for v in self.histograms[key] if v > cutoff_time]

    def record_request_time(self, duration_ms: float):
        """Record request processing time"""
        self.request_times.append(duration_ms)
        self.record_histogram("request_duration_ms", duration_ms)

    def _build_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Build metric key with labels"""
        if not labels:
            return name

        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> int:
        """Get current counter value"""
        key = self._build_key(name, labels)
        return self.counters.get(key, 0)

    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current gauge value"""
        key = self._build_key(name, labels)
        return self.gauges.get(key, 0.0)

    def get_histogram_stats(
        self, name: str, labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, float]:
        """Get histogram statistics"""
        key = self._build_key(name, labels)
        values = self.histograms.get(key, [])

        if not values:
            return {
                "count": 0,
                "avg": 0,
                "p50": 0,
                "p95": 0,
                "p99": 0,
                "min": 0,
                "max": 0,
            }

        sorted_values = sorted(values)
        count = len(sorted_values)

        return {
            "count": count,
            "avg": sum(sorted_values) / count,
            "p50": sorted_values[int(count * 0.5)],
            "p95": (
                sorted_values[int(count * 0.95)] if count > 20 else sorted_values[-1]
            ),
            "p99": (
                sorted_values[int(count * 0.99)] if count > 100 else sorted_values[-1]
            ),
            "min": sorted_values[0],
            "max": sorted_values[-1],
        }

    def get_request_rate(self, window_seconds: int = 60) -> float:
        """Get requests per second over time window"""
        cutoff_time = datetime.now() - timedelta(seconds=window_seconds)

        total_requests = 0
        for metric_name, metric_values in self.metrics.items():
            if "request" in metric_name.lower():
                recent_requests = [
                    m for m in metric_values if m.timestamp > cutoff_time
                ]
                total_requests += len(recent_requests)

        return total_requests / window_seconds if window_seconds > 0 else 0

    def get_error_rate(self, window_seconds: int = 60) -> float:
        """Get error rate over time window"""
        total_requests = self.get_counter("total_requests")
        error_requests = self.get_counter("error_requests")

        return (error_requests / total_requests * 100) if total_requests > 0 else 0

    def cleanup_old_metrics(self):
        """Remove old metrics beyond retention period"""
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)

        for metric_name in list(self.metrics.keys()):
            # Remove old values
            while (
                self.metrics[metric_name]
                and self.metrics[metric_name][0].timestamp < cutoff_time
            ):
                self.metrics[metric_name].popleft()

            # Remove empty metrics
            if not self.metrics[metric_name]:
                del self.metrics[metric_name]


class DatabaseMetricsCollector:
    """Collect database-specific metrics"""

    def __init__(self, database_url: str):
        self.database_url = database_url

    async def collect_db_metrics(self) -> Dict[str, Any]:
        """Collect database performance metrics"""
        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(self.database_url)

            with engine.connect() as conn:
                # Connection stats
                conn_result = conn.execute(
                    text(
                        """
                    SELECT count(*) as total_connections,
                           count(*) FILTER (WHERE state = 'active') as active_connections,
                           count(*) FILTER (WHERE state = 'idle') as idle_connections
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                """
                    )
                ).fetchone()

                # Database size
                size_result = conn.execute(
                    text(
                        """
                    SELECT pg_size_pretty(pg_database_size(current_database())) as database_size,
                           pg_database_size(current_database()) as database_size_bytes
                """
                    )
                ).fetchone()

                # Query performance
                slow_queries = conn.execute(
                    text(
                        """
                    SELECT query, calls, mean_time, max_time
                    FROM pg_stat_statements
                    WHERE mean_time > 100
                    ORDER BY mean_time DESC
                    LIMIT 10
                """
                    )
                ).fetchall()

                # Table statistics
                table_stats = conn.execute(
                    text(
                        """
                    SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del
                    FROM pg_stat_user_tables
                    ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC
                    LIMIT 10
                """
                    )
                ).fetchall()

                return {
                    "connections": {
                        "total": conn_result.total_connections,
                        "active": conn_result.active_connections,
                        "idle": conn_result.idle_connections,
                    },
                    "database_size": {
                        "human_readable": size_result.database_size,
                        "bytes": size_result.database_size_bytes,
                    },
                    "slow_queries": [
                        {
                            "query": (
                                q.query[:100] + "..." if len(q.query) > 100 else q.query
                            ),
                            "calls": q.calls,
                            "mean_time_ms": float(q.mean_time),
                            "max_time_ms": float(q.max_time),
                        }
                        for q in slow_queries
                    ],
                    "table_stats": [
                        {
                            "table": f"{t.schemaname}.{t.tablename}",
                            "inserts": t.n_tup_ins,
                            "updates": t.n_tup_upd,
                            "deletes": t.n_tup_del,
                            "total_operations": t.n_tup_ins + t.n_tup_upd + t.n_tup_del,
                        }
                        for t in table_stats
                    ],
                }

        except Exception as e:
            logger.error(f"Failed to collect database metrics: {e}")
            return {"error": str(e)}


class ApplicationMetricsCollector:
    """Collect application-specific business metrics"""

    def __init__(self, database_url: str):
        self.database_url = database_url

    async def collect_app_metrics(self) -> Dict[str, Any]:
        """Collect application business metrics"""
        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(self.database_url)

            with engine.connect() as conn:
                # User metrics
                user_metrics = conn.execute(
                    text(
                        """
                    SELECT 
                        COUNT(*) as total_users,
                        COUNT(*) FILTER (WHERE is_active = true) as active_users,
                        COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as new_users_24h,
                        COUNT(*) FILTER (WHERE last_activity > NOW() - INTERVAL '1 hour') as active_users_1h
                    FROM users
                """
                    )
                ).fetchone()

                # Escrow metrics
                escrow_metrics = conn.execute(
                    text(
                        """
                    SELECT 
                        COUNT(*) as total_escrows,
                        COUNT(*) FILTER (WHERE status = 'active') as active_escrows,
                        COUNT(*) FILTER (WHERE status = 'completed') as completed_escrows,
                        COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as new_escrows_24h,
                        COALESCE(SUM(amount) FILTER (WHERE status = 'active'), 0) as active_escrow_value
                    FROM escrows
                """
                    )
                ).fetchone()

                # Transaction metrics
                transaction_metrics = conn.execute(
                    text(
                        """
                    SELECT 
                        COUNT(*) as total_transactions,
                        COUNT(*) FILTER (WHERE status = 'completed') as completed_transactions,
                        COUNT(*) FILTER (WHERE status = 'pending') as pending_transactions,
                        COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as transactions_24h,
                        COALESCE(SUM(amount) FILTER (WHERE status = 'completed'), 0) as total_volume
                    FROM transactions
                """
                    )
                ).fetchone()

                # Wallet metrics
                wallet_metrics = conn.execute(
                    text(
                        """
                    SELECT 
                        COUNT(*) as total_wallets,
                        COUNT(*) FILTER (WHERE is_active = true) as active_wallets,
                        COALESCE(SUM(balance), 0) as total_balance_usd
                    FROM wallets
                    WHERE currency = 'USD'
                """
                    )
                ).fetchone()

                # Cashout metrics
                cashout_metrics = conn.execute(
                    text(
                        """
                    SELECT 
                        COUNT(*) FILTER (WHERE status = 'pending') as pending_cashouts,
                        COUNT(*) FILTER (WHERE status = 'processing') as processing_cashouts,
                        COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as cashouts_24h,
                        COALESCE(SUM(amount) FILTER (WHERE status = 'pending'), 0) as pending_cashout_amount
                    FROM cashouts
                """
                    )
                ).fetchone()

                return {
                    "users": {
                        "total": user_metrics.total_users,
                        "active": user_metrics.active_users,
                        "new_24h": user_metrics.new_users_24h,
                        "active_1h": user_metrics.active_users_1h,
                    },
                    "escrows": {
                        "total": escrow_metrics.total_escrows,
                        "active": escrow_metrics.active_escrows,
                        "completed": escrow_metrics.completed_escrows,
                        "new_24h": escrow_metrics.new_escrows_24h,
                        "active_value_usd": float(escrow_metrics.active_escrow_value),
                    },
                    "transactions": {
                        "total": transaction_metrics.total_transactions,
                        "completed": transaction_metrics.completed_transactions,
                        "pending": transaction_metrics.pending_transactions,
                        "transactions_24h": transaction_metrics.transactions_24h,
                        "total_volume_usd": float(transaction_metrics.total_volume),
                    },
                    "wallets": {
                        "total": wallet_metrics.total_wallets,
                        "active": wallet_metrics.active_wallets,
                        "total_balance_usd": float(wallet_metrics.total_balance_usd),
                    },
                    "cashouts": {
                        "pending": cashout_metrics.pending_cashouts,
                        "processing": cashout_metrics.processing_cashouts,
                        "cashouts_24h": cashout_metrics.cashouts_24h,
                        "pending_amount_usd": float(
                            cashout_metrics.pending_cashout_amount
                        ),
                    },
                }

        except Exception as e:
            logger.error(f"Failed to collect application metrics: {e}")
            return {"error": str(e)}


class MetricsDashboard:
    """Real-time metrics dashboard"""

    def __init__(self, database_url: str):
        self.metrics_collector = MetricsCollector()
        self.db_metrics_collector = DatabaseMetricsCollector(database_url)
        self.app_metrics_collector = ApplicationMetricsCollector(database_url)
        self.is_running = False

    async def start_collection(self, interval_seconds: int = 60):
        """Start background metrics collection"""
        self.is_running = True

        while self.is_running:
            try:
                await self.collect_all_metrics()
                await asyncio.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(interval_seconds)

    def stop_collection(self):
        """Stop metrics collection"""
        self.is_running = False

    async def collect_all_metrics(self):
        """Collect all types of metrics"""
        datetime.now()

        # System metrics
        system_metrics = PerformanceMetrics.collect()
        self.metrics_collector.set_gauge("cpu_usage_percent", system_metrics.cpu_usage)
        self.metrics_collector.set_gauge(
            "memory_usage_percent", system_metrics.memory_usage
        )
        self.metrics_collector.set_gauge(
            "disk_usage_percent", system_metrics.disk_usage
        )

        # Database metrics
        db_metrics = await self.db_metrics_collector.collect_db_metrics()
        if "error" not in db_metrics:
            self.metrics_collector.set_gauge(
                "db_connections_total", db_metrics["connections"]["total"]
            )
            self.metrics_collector.set_gauge(
                "db_connections_active", db_metrics["connections"]["active"]
            )

        # Application metrics
        app_metrics = await self.app_metrics_collector.collect_app_metrics()
        if "error" not in app_metrics:
            self.metrics_collector.set_gauge(
                "users_active", app_metrics["users"]["active"]
            )
            self.metrics_collector.set_gauge(
                "escrows_active", app_metrics["escrows"]["active"]
            )
            self.metrics_collector.set_gauge(
                "cashouts_pending", app_metrics["cashouts"]["pending"]
            )

        # Cleanup old metrics
        self.metrics_collector.cleanup_old_metrics()

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        system_metrics = PerformanceMetrics.collect()

        return {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": time.time() - self.metrics_collector.start_time,
            "system": asdict(system_metrics),
            "application": {
                "total_requests": self.metrics_collector.get_counter("total_requests"),
                "error_requests": self.metrics_collector.get_counter("error_requests"),
                "request_rate_per_second": self.metrics_collector.get_request_rate(),
                "error_rate_percent": self.metrics_collector.get_error_rate(),
                "response_time_stats": self.metrics_collector.get_histogram_stats(
                    "request_duration_ms"
                ),
            },
            "counters": dict(self.metrics_collector.counters),
            "gauges": dict(self.metrics_collector.gauges),
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Get system health status"""
        system_metrics = PerformanceMetrics.collect()

        # Health thresholds
        cpu_threshold = 80
        memory_threshold = 85
        disk_threshold = 90

        health_status = "healthy"
        issues = []

        if system_metrics.cpu_usage > cpu_threshold:
            health_status = "degraded"
            issues.append(f"High CPU usage: {system_metrics.cpu_usage:.1f}%")

        if system_metrics.memory_usage > memory_threshold:
            health_status = "degraded"
            issues.append(f"High memory usage: {system_metrics.memory_usage:.1f}%")

        if system_metrics.disk_usage > disk_threshold:
            health_status = "critical"
            issues.append(f"High disk usage: {system_metrics.disk_usage:.1f}%")

        return {
            "status": health_status,
            "issues": issues,
            "metrics": {
                "cpu_usage": system_metrics.cpu_usage,
                "memory_usage": system_metrics.memory_usage,
                "disk_usage": system_metrics.disk_usage,
            },
        }


# Global metrics dashboard
metrics_dashboard = None


def initialize_metrics_dashboard(database_url: str):
    """Initialize global metrics dashboard"""
    global metrics_dashboard
    metrics_dashboard = MetricsDashboard(database_url)


def get_metrics_dashboard() -> Optional[MetricsDashboard]:
    """Get global metrics dashboard instance"""
    return metrics_dashboard


# Convenience functions for recording metrics
def record_request():
    """Record a request"""
    if metrics_dashboard:
        metrics_dashboard.metrics_collector.increment_counter("total_requests")


def record_error():
    """Record an error"""
    if metrics_dashboard:
        metrics_dashboard.metrics_collector.increment_counter("error_requests")


def record_response_time(duration_ms: float):
    """Record response time"""
    if metrics_dashboard:
        metrics_dashboard.metrics_collector.record_request_time(duration_ms)
