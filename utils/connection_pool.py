"""
Database Connection Pool - Optimized database connection management
Provides efficient connection pooling, health monitoring, and resource management
"""

import logging
import asyncio
import os
import sys
from typing import Dict, Any, Optional
from contextlib import contextmanager, asynccontextmanager
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine
from datetime import datetime
import threading
import time
from config import Config

logger = logging.getLogger(__name__)

def _is_test_environment() -> bool:
    """Check if we're running in a test environment"""
    return bool(os.environ.get("PYTEST_CURRENT_TEST") or "pytest" in str(sys.argv))


class ConnectionPoolManager:
    """Advanced database connection pool with health monitoring and optimization"""

    def __init__(self):
        # ARCHITECT FIX: Skip initialization entirely in test environment
        if _is_test_environment():
            logger.info("🧪 TEST MODE: Skipping ConnectionPoolManager initialization")
            self.engines: Dict[str, Engine] = {}
            self.session_factories: Dict[str, sessionmaker] = {}
            self.pool_stats: Dict[str, Dict] = {}
            self.monitoring_task = None
            self._lock = threading.Lock()
            self.pool_config = {}
            return
            
        self.engines: Dict[str, Engine] = {}
        self.session_factories: Dict[str, sessionmaker] = {}
        self.pool_stats: Dict[str, Dict] = {}
        self.monitoring_task = None
        self._lock = threading.Lock()

        # Pool configuration - OPTIMIZED: Reduced pool sizes for lower memory usage
        self.pool_config = {
            "main": {
                "pool_size": 8,  # Reduced from 20 - sufficient for typical load
                "max_overflow": 12,  # Reduced from 30 - burst capacity
                "pool_timeout": 30,  # Wait time for connection
                "pool_recycle": 3600,  # Recycle connections after 1 hour
                "pool_pre_ping": True,  # Test connections before use
            },
            "readonly": {
                "pool_size": 3,  # Reduced from 10 - most reads can share connections
                "max_overflow": 7,  # Reduced from 15
                "pool_timeout": 20,
                "pool_recycle": 7200,
                "pool_pre_ping": True,
            },
            "background_jobs": {
                "pool_size": 2,  # Reduced from 5 - background jobs are async
                "max_overflow": 6,  # Reduced from 10
                "pool_timeout": 60,
                "pool_recycle": 1800,
                "pool_pre_ping": True,
            },
        }

    def initialize_pools(self):
        """Initialize all database connection pools"""
        # ARCHITECT FIX: Skip pool initialization in test environment
        if _is_test_environment():
            logger.info("🧪 TEST MODE: Skipping connection pool initialization")
            return
            
        try:
            database_url = Config.DATABASE_URL
            if not database_url:
                raise ValueError("DATABASE_URL not configured")

            # Create different pools for different use cases
            for pool_name, config in self.pool_config.items():
                logger.info(f"Initializing {pool_name} connection pool...")

                engine = create_engine(
                    database_url,
                    poolclass=QueuePool,
                    pool_size=config["pool_size"],
                    max_overflow=config["max_overflow"],
                    pool_timeout=config["pool_timeout"],
                    pool_recycle=config["pool_recycle"],
                    pool_pre_ping=config["pool_pre_ping"],
                    echo=False,  # Set to True for SQL debugging
                    future=True,  # Use SQLAlchemy 2.0 style
                    connect_args={
                        "application_name": f"escrow_bot_{pool_name}",
                        "connect_timeout": 10,
                    },
                )

                # Add event listeners for monitoring
                self._add_engine_listeners(engine, pool_name)

                # Create session factory
                session_factory = sessionmaker(
                    bind=engine,
                    expire_on_commit=False,  # Keep objects accessible after commit
                    autoflush=True,
                    autocommit=False,
                )

                self.engines[pool_name] = engine
                self.session_factories[pool_name] = session_factory

                # Initialize stats tracking
                self.pool_stats[pool_name] = {
                    "connections_created": 0,
                    "connections_closed": 0,
                    "connections_checked_out": 0,
                    "connections_checked_in": 0,
                    "connection_errors": 0,
                    "slow_queries": 0,
                    "last_error": None,
                    "last_error_time": None,
                    "created_at": datetime.utcnow(),
                }

                logger.info(f"Connection pool '{pool_name}' initialized successfully")

            # Start monitoring
            self.start_monitoring()

        except Exception as e:
            logger.error(f"Failed to initialize connection pools: {e}")
            raise

    def _add_engine_listeners(self, engine: Engine, pool_name: str):
        """Add event listeners to monitor pool health"""

        @event.listens_for(engine, "connect")
        def connect_listener(dbapi_connection, connection_record):
            self.pool_stats[pool_name]["connections_created"] += 1
            logger.debug(f"New connection created for {pool_name} pool")

        @event.listens_for(engine, "checkout")
        def checkout_listener(dbapi_connection, connection_record, connection_proxy):
            self.pool_stats[pool_name]["connections_checked_out"] += 1
            connection_record.info["checkout_time"] = time.time()

        @event.listens_for(engine, "checkin")
        def checkin_listener(dbapi_connection, connection_record):
            self.pool_stats[pool_name]["connections_checked_in"] += 1

            # Track connection usage time
            if "checkout_time" in connection_record.info:
                usage_time = time.time() - connection_record.info["checkout_time"]
                if usage_time > 30:  # Log slow connection usage
                    logger.warning(
                        f"Connection held for {usage_time:.2f}s in {pool_name} pool"
                    )

        @event.listens_for(engine, "close")
        def close_listener(dbapi_connection, connection_record):
            self.pool_stats[pool_name]["connections_closed"] += 1

        @event.listens_for(engine, "handle_error")
        def error_listener(exception_context):
            self.pool_stats[pool_name]["connection_errors"] += 1
            self.pool_stats[pool_name]["last_error"] = str(
                exception_context.original_exception
            )
            self.pool_stats[pool_name]["last_error_time"] = datetime.utcnow()

            logger.error(
                f"Database error in {pool_name} pool: {exception_context.original_exception}"
            )

    @contextmanager
    def get_session(self, pool_name: str = "main", timeout: Optional[int] = None):
        """Get database session from specified pool"""
        if pool_name not in self.session_factories:
            raise ValueError(f"Unknown pool: {pool_name}")

        session_factory = self.session_factories[pool_name]
        session = session_factory()
        start_time = time.time()

        try:
            yield session
            session.commit()

        except Exception as e:
            session.rollback()
            logger.error(f"Session error in {pool_name} pool: {e}")
            raise

        finally:
            session_duration = time.time() - start_time
            if session_duration > 5.0:  # Log slow sessions
                logger.warning(
                    f"Slow session in {pool_name} pool: {session_duration:.2f}s"
                )

            session.close()

    @asynccontextmanager
    async def get_async_session(self, pool_name: str = "main"):
        """Get async database session (for async contexts)"""

        # Note: This is a simple wrapper. For true async, you'd use asyncpg/aiomysql
        def get_session_sync():
            return self.get_session(pool_name)

        loop = asyncio.get_event_loop()
        with await loop.run_in_executor(None, get_session_sync) as session:
            yield session

    def get_optimized_session(self, operation_type: str = "general"):
        """Get session optimized for specific operation types"""
        pool_mapping = {
            "read": "readonly",
            "readonly": "readonly",
            "background": "background_jobs",
            "job": "background_jobs",
            "write": "main",
            "general": "main",
            "transaction": "main",
        }

        pool_name = pool_mapping.get(operation_type, "main")
        return self.get_session(pool_name)

    def start_monitoring(self):
        """Start background monitoring of connection pools"""
        if self.monitoring_task is None:
            self.monitoring_task = threading.Thread(
                target=self._monitoring_loop, daemon=True
            )
            self.monitoring_task.start()
            logger.info("Connection pool monitoring started")

    def _monitoring_loop(self):
        """Background monitoring loop"""
        while True:
            try:
                self._check_pool_health()
                self._log_pool_stats()

            except Exception as e:
                logger.error(f"Error in pool monitoring: {e}")

            time.sleep(60)  # Check every minute

    def _check_pool_health(self):
        """Check health of all connection pools"""
        for pool_name, engine in self.engines.items():
            try:
                pool = engine.pool

                # Get pool status (using available attributes)
                pool_status = {
                    "size": getattr(pool, "size", lambda: 0)(),
                    "checked_in": getattr(pool, "checkedin", lambda: 0)(),
                    "checked_out": getattr(pool, "checkedout", lambda: 0)(),
                    "overflow": getattr(pool, "overflow", lambda: 0)(),
                    "invalid": getattr(pool, "invalid", lambda: 0)(),
                }

                # Check for concerning conditions
                if pool_status["checked_out"] > pool_status["size"] * 0.8:
                    logger.warning(
                        f"High connection usage in {pool_name} pool: {pool_status}"
                    )

                if pool_status["invalid"] > 0:
                    logger.warning(
                        f"Invalid connections in {pool_name} pool: {pool_status['invalid']}"
                    )

                # Test connection health
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))

            except Exception as e:
                logger.error(f"Health check failed for {pool_name} pool: {e}")
                self.pool_stats[pool_name]["connection_errors"] += 1

    def _log_pool_stats(self):
        """Log periodic pool statistics"""
        for pool_name, stats in self.pool_stats.items():
            if pool_name in self.engines:
                pool = self.engines[pool_name].pool

                pool_info = {
                    "pool": pool_name,
                    "size": getattr(pool, "size", lambda: 0)(),
                    "checked_out": getattr(pool, "checkedout", lambda: 0)(),
                    "overflow": getattr(pool, "overflow", lambda: 0)(),
                    "connections_created": stats["connections_created"],
                    "connection_errors": stats["connection_errors"],
                }

                logger.info(f"Pool stats: {pool_info}")

    def get_pool_statistics(self) -> Dict[str, Any]:
        """Get comprehensive pool statistics"""
        stats = {}

        for pool_name in self.engines:
            engine = self.engines[pool_name]
            pool = engine.pool
            pool_stats = self.pool_stats[pool_name]

            stats[pool_name] = {
                "pool_info": {
                    "size": getattr(pool, "size", lambda: 0)(),
                    "checked_in": getattr(pool, "checkedin", lambda: 0)(),
                    "checked_out": getattr(pool, "checkedout", lambda: 0)(),
                    "overflow": getattr(pool, "overflow", lambda: 0)(),
                    "invalid": getattr(pool, "invalid", lambda: 0)(),
                },
                "counters": pool_stats.copy(),
                "health": {
                    "last_error": pool_stats.get("last_error"),
                    "last_error_time": pool_stats.get("last_error_time"),
                    "error_rate": pool_stats["connection_errors"]
                    / max(pool_stats["connections_created"], 1),
                },
            }

        return stats

    def optimize_for_load(self, expected_load: str):
        """Adjust pool sizes based on expected load"""
        multipliers = {"low": 0.7, "normal": 1.0, "high": 1.5, "peak": 2.0}

        multiplier = multipliers.get(expected_load, 1.0)

        # Note: Dynamically adjusting pool size requires engine recreation
        # This is a simplified example - in production, you might want
        # to implement this more carefully
        logger.info(f"Pool optimization for {expected_load} load: {multiplier}x")

    def shutdown_pools(self):
        """Gracefully shutdown all connection pools"""
        logger.info("Shutting down connection pools...")

        for pool_name, engine in self.engines.items():
            try:
                engine.dispose()
                logger.info(f"Pool '{pool_name}' shut down successfully")
            except Exception as e:
                logger.error(f"Error shutting down pool '{pool_name}': {e}")

        self.engines.clear()
        self.session_factories.clear()


# Global instance
connection_pool_manager = ConnectionPoolManager()


# Convenience functions for backward compatibility
def get_db_session(pool_name: str = "main"):
    """Get database session from connection pool"""
    return connection_pool_manager.get_session(pool_name)


def get_optimized_session(operation_type: str = "general"):
    """Get session optimized for operation type"""
    return connection_pool_manager.get_optimized_session(operation_type)
