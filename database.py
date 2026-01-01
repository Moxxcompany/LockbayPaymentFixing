"""
Database Configuration and Session Management
============================================

This module provides the main database engine, session factory, and table creation
functionality for the LockBay Telegram Escrow Bot.
"""

import logging
from contextlib import contextmanager, asynccontextmanager
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError
from config import Config
from models import Base

logger = logging.getLogger(__name__)

# Register User timestamp validator immediately after importing models
# This ensures timezone-aware datetimes are automatically converted to naive
try:
    from utils.user_timestamp_validator import register_user_timestamp_validator
    register_user_timestamp_validator()
    logger.info("✅ USER_TIMESTAMP_VALIDATOR: Registered at module import - timezone safety enabled globally")
except Exception as validator_error:
    logger.warning(f"⚠️ USER_TIMESTAMP_VALIDATOR: Registration failed: {validator_error}")
    # Non-critical - continue initialization

# Database engine with connection pooling
if not Config.DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# OPTIMIZED FOR RAILWAY POSTGRESQL: Conservative connection pool
# Railway Hobby plan supports ~50 connections, need to account for BOTH sync+async pools
# Sync pool: 7 base + 15 overflow = 22 max
# Async pool: 7 base + 15 overflow = 22 max
# Total: 44 connections max (safely under 50 limit with headroom for admin queries)
# Combined with 4-minute keep-alive job to maintain database warmth
engine = create_engine(
    Config.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=7,           # Sync base pool for Railway PostgreSQL
    max_overflow=15,       # Sync burst capacity for Railway PostgreSQL
    pool_pre_ping=True,    # Validate connections before use
    pool_recycle=3600,     # Recycle connections every hour
    pool_timeout=30,       # Wait max 30 seconds for connection during bursts
    echo=False,            # Set to True for SQL logging in development
    # OPTIMIZED: Added connection monitoring and timeouts
    connect_args={
        "connect_timeout": 10,  # Fail fast on slow connections
        "application_name": "lockbay_telegram_bot",  # For monitoring in pg_stat_activity
    }
)

# Async database engine with connection pooling
# CRITICAL FIX: Convert sslmode parameter for asyncpg compatibility
async_database_url = Config.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://')
# asyncpg uses 'ssl' instead of 'sslmode' parameter
async_database_url = async_database_url.replace('sslmode=require', 'ssl=require')
async_database_url = async_database_url.replace('sslmode=prefer', 'ssl=prefer')
async_database_url = async_database_url.replace('sslmode=disable', 'ssl=disable')
# OPTIMIZED FOR RAILWAY POSTGRESQL: Conservative async connection pool
# Railway Hobby plan supports ~50 connections, need to account for BOTH sync+async pools
# Sync pool: 7 base + 15 overflow = 22 max
# Async pool: 7 base + 15 overflow = 22 max
# Total: 44 connections max (safely under 50 limit with headroom for admin queries)
# Combined with 4-minute keep-alive job to maintain database warmth
async_engine = create_async_engine(
    async_database_url,
    pool_size=7,           # Async base pool for Railway PostgreSQL
    max_overflow=15,       # Async burst capacity for Railway PostgreSQL
    pool_pre_ping=True,    # Validate connections before use
    pool_recycle=3600,     # Recycle connections every hour
    pool_timeout=30,       # Wait max 30 seconds for connection during bursts
    echo=False,            # Disable SQL logging (set DEBUG=true to enable)
    echo_pool=False,       # Disable connection pool logging
    # OPTIMIZED: Added connection monitoring and timeouts
    connect_args={
        "server_settings": {
            "application_name": "lockbay_telegram_bot_async",  # For monitoring in pg_stat_activity
        },
        "timeout": 10,  # Connection timeout
        "command_timeout": 30,  # Command execution timeout
    }
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Sync session factory for compatibility
SyncSessionLocal = SessionLocal

# Async session factory (FIXED - now uses proper async sessions)
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False  # CRITICAL: Prevent greenlet errors in background tasks
)


@asynccontextmanager
async def get_async_session():
    """
    Async context manager for database sessions in Telegram handlers.
    
    PERFORMANCE: Use this instead of SyncSessionLocal() in async handlers
    to prevent event loop blocking (200-500ms → <50ms improvement).
    
    Usage:
        async def button_callback(update, context):
            # ✅ Answer callback FIRST (instant feedback)
            await update.callback_query.answer("⏳ Processing...")
            
            # ✅ Use async session (non-blocking)
            async with get_async_session() as session:
                result = await session.execute(select(User).where(...))
                user = result.scalar_one_or_none()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def create_tables():
    """Create all database tables if they don't exist"""
    try:
        logger.info("🏗️ Creating database tables (if they don't exist)...")
        
        # CRITICAL FIX: Import all models to register them with Base.metadata
        # This ensures all table definitions are available for creation
        from models import (
            User, Wallet, Escrow, Transaction, Cashout, Refund, EscrowRefundOperation, DistributedLock,
            IdempotencyToken, WebhookEventLedger, PaymentAddress, NotificationQueue,
            AuditLog, SystemConfig, UserSession, SavedAddress, SavedBankAccount,
            EmailVerification, PendingCashout, ExchangeOrder, IdempotencyKey,
            EscrowMessage, Dispute, DisputeMessage, UnifiedTransaction, Rating,
            UnifiedTransactionStatusHistory, UnifiedTransactionRetryLog, EscrowHolding,
            SecurityAudit, SupportTicket, SupportMessage, OutboxEvent, AdminActionToken,
            InboxWebhook, SagaStep, WalletHolds, TransactionEngineEvent, AuditEvent,
            InternalWallet, BalanceAuditLog, WalletBalanceSnapshot, BalanceReconciliationLog,
            OnboardingSession, UserContact, NotificationActivity, NotificationPreference,
            CryptoDeposit, UserAchievement, UserStreakTracking,
            AdminOperationOverride, BalanceProtectionLog, PartnerApplication
        )
        
        # Create a fresh engine specifically for table creation to avoid transaction conflicts
        from sqlalchemy import create_engine
        from sqlalchemy.exc import ProgrammingError
        if not Config.DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is required")
        fresh_engine = create_engine(Config.DATABASE_URL, pool_pre_ping=True)
        
        # Log how many tables are registered
        logger.info(f"📊 Found {len(Base.metadata.tables)} table models to create")
        
        try:
            # Use checkfirst=True to only create tables that don't exist
            Base.metadata.create_all(bind=fresh_engine, checkfirst=True)
        except ProgrammingError as e:
            # Handle cases where indexes already exist (this is normal and expected)
            if "already exists" in str(e):
                logger.info(f"⚠️ Some database objects already exist (this is normal): {e}")
            else:
                raise  # Re-raise if it's a different error
        
        # Log which tables were created/verified
        from sqlalchemy import inspect
        inspector = inspect(fresh_engine)
        existing_tables = inspector.get_table_names()
        
        logger.info(f"✅ Database schema verified: {len(existing_tables)} tables available")
        logger.info(f"📋 Tables: {', '.join(sorted(existing_tables))}")
        
        # Clean up the fresh engine
        fresh_engine.dispose()
        
        return True
    except Exception as e:
        # Only treat as error if it's not about existing objects
        if "already exists" not in str(e):
            logger.error(f"❌ Failed to create database tables: {e}")
            import traceback
            logger.error(f"❌ Full error: {traceback.format_exc()}")
            return False
        else:
            logger.info("✅ Database initialization completed (some objects already existed)")
            return True


def get_session() -> Session:
    """Get a new database session"""
    return SessionLocal()


@contextmanager
def managed_session():
    """Sync context manager for database sessions"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


@asynccontextmanager
async def async_managed_session():
    """Async context manager for database sessions"""
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception as e:
        logger.error(f"Database session error: {e}")
        await session.rollback()
        raise
    finally:
        await session.close()


# Alias for compatibility
sync_managed_session = managed_session


def get_db_session():
    """Get a database session (compatibility function)"""
    return SessionLocal()


def get_sync_db_session():
    """Get a synchronous database session (compatibility function)"""
    return SessionLocal()


def test_connection():
    """Test database connection"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info("✅ Database connection test successful")
            return True
    except Exception as e:
        logger.error(f"❌ Database connection test failed: {e}")
        return False


# PostgreSQL connection management
# Note: PostgreSQL handles foreign keys and constraints natively - no additional setup needed


def get_pool_stats():
    """
    Get connection pool statistics for monitoring and debugging
    
    Returns dict with:
    - sync_pool_size: Current sync pool size
    - sync_checked_out: Checked out sync connections
    - sync_overflow: Overflow sync connections
    - async_pool_size: Current async pool size (estimated)
    - async_checked_out: Checked out async connections (estimated)
    - total_connections: Total estimated active connections
    """
    stats = {}
    
    try:
        # Sync pool stats
        sync_pool = engine.pool
        stats['sync_pool_size'] = sync_pool.size()  # type: ignore[attr-defined]
        stats['sync_checked_out'] = sync_pool.checkedout()  # type: ignore[attr-defined]
        stats['sync_overflow'] = sync_pool.overflow()  # type: ignore[attr-defined]
        
        # Async pool stats (async pool doesn't expose same stats directly)
        # We can get approximate stats from the pool object
        async_pool = async_engine.pool
        if hasattr(async_pool, 'size'):
            stats['async_pool_size'] = async_pool.size()  # type: ignore[attr-defined]
        else:
            stats['async_pool_size'] = 'N/A'
            
        if hasattr(async_pool, 'checkedout'):
            stats['async_checked_out'] = async_pool.checkedout()  # type: ignore[attr-defined]
        else:
            stats['async_checked_out'] = 'N/A'
        
        # Calculate total
        total = 0
        if isinstance(stats['sync_checked_out'], int):
            total += stats['sync_checked_out']
        if isinstance(stats['async_checked_out'], int):
            total += stats['async_checked_out']
        stats['total_connections'] = total
        
        logger.debug(
            f"📊 POOL_STATS: Sync({stats['sync_checked_out']}/{stats['sync_pool_size']}+{stats['sync_overflow']}) "
            f"Async({stats['async_checked_out']}/{stats['async_pool_size']}) "
            f"Total: {stats['total_connections']}"
        )
        
    except Exception as e:
        logger.error(f"❌ Error getting pool stats: {e}")
        stats['error'] = str(e)
    
    return stats


# Note: engine_connect ping removed to prevent SAWarning conflicts with pool_pre_ping=True
# The pool_pre_ping=True setting already handles connection testing automatically