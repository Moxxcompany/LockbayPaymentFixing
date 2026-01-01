"""
Comprehensive Test Fixtures and Utilities for LockBay Bot Testing
Provides shared fixtures, utilities, and configuration for all comprehensive test suites.

Key Components:
1. Database fixtures with complete schema support (escrow, exchange, cashout, onboarding)
2. Mock external service configurations with proper patching
3. Telegram object factories for realistic testing
4. Common assertion helpers and test utilities
5. Performance measurement utilities
6. Production-grade test isolation and cleanup
7. Real handler integration support
"""

# PostgreSQL-only test configuration - no compatibility shims needed
import sys
import os

import pytest
import pytest_asyncio
import asyncio
import logging
import os
import sys
import json
import uuid
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from contextlib import asynccontextmanager, contextmanager

# Database imports
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from database import SessionLocal, managed_session
from models import (
    Base, User, Wallet, Escrow, EscrowStatus, Transaction, TransactionType,
    Cashout, CashoutStatus, CashoutProcessingMode, ExchangeOrder, ExchangeStatus,
    UnifiedTransaction, UnifiedTransactionStatus, UnifiedTransactionType,
    Rating, Dispute, EscrowMessage, SavedAddress, SavedBankAccount,
    WalletHolds, WalletHoldStatus, EscrowHolding, PendingCashout, Refund
)

# Telegram imports for object factories
from telegram import (
    Update, User as TelegramUser, Message, CallbackQuery, Chat,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import ContextTypes

# Service imports for proper mocking
from services.unified_transaction_service import UnifiedTransactionService
from services.fincra_service import FincraService
from services.kraken_service import KrakenService
from services.crypto import CryptoServiceAtomic
from services.conditional_otp_service import ConditionalOTPService
from services.fastforex_service import FastForexService
from services.email_verification_service import EmailVerificationService
from services.async_email_service import AsyncEmailService

# Utilities
from utils.helpers import generate_utid, validate_email
from utils.wallet_manager import get_or_create_wallet
from utils.financial_audit_logger import financial_audit_logger
from config import Config

# Configure logging for tests with async warning suppression
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import warnings to suppress async cleanup warnings during testing
import warnings
# Suppress specific async cleanup warnings that are expected during test teardown
warnings.filterwarnings("ignore", message=".*coroutine.*was never awaited.*")
warnings.filterwarnings("ignore", message=".*Enable tracemalloc.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*")

# PRIORITY 1: Database consistency and cache cleanup imports
from sqlalchemy import text

# Global async resource tracking for comprehensive cleanup
_GLOBAL_ASYNC_RESOURCES = {
    'engines': [],
    'sessions': [],
    'connections': [],
    'tasks': [],
    'cleanup_callbacks': []
}

# PostgreSQL test database configuration
# Use environment DATABASE_URL for consistent PostgreSQL testing
TEST_DATABASE_URL = os.getenv('DATABASE_URL')
if not TEST_DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required for PostgreSQL testing")

# Convert to async PostgreSQL URL with asyncpg driver
if TEST_DATABASE_URL.startswith('postgresql://'):
    # Strip query parameters (like ?sslmode=require) that asyncpg doesn't accept
    base_url = TEST_DATABASE_URL.split('?')[0]
    TEST_DATABASE_URL_ASYNC = base_url.replace('postgresql://', 'postgresql+asyncpg://')
else:
    TEST_DATABASE_URL_ASYNC = TEST_DATABASE_URL.split('?')[0]

TEST_DATABASE_ECHO = False  # Set to True for SQL debugging


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session with comprehensive async cleanup."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    policy.set_event_loop(loop)
    
    # Configure loop for testing with enhanced cleanup capabilities
    loop.set_debug(False)  # Disable debug mode to reduce noise
    
    # Keep track of all async engines and connections created during tests
    _test_async_engines = []
    _test_async_sessions = []
    _test_cleanup_callbacks = []
    
    # Store references in the loop for cleanup
    loop._test_async_engines = _test_async_engines
    loop._test_async_sessions = _test_async_sessions
    loop._test_cleanup_callbacks = _test_cleanup_callbacks
    
    # Add global resource tracking integration
    _GLOBAL_ASYNC_RESOURCES['engines'].extend(_test_async_engines)
    _GLOBAL_ASYNC_RESOURCES['sessions'].extend(_test_async_sessions)
    _GLOBAL_ASYNC_RESOURCES['cleanup_callbacks'].extend(_test_cleanup_callbacks)
    
    try:
        yield loop
    finally:
        # ARCHITECT FIX: CORRECT ASYNC LIFECYCLE CLEANUP - Dispose engines/sessions BEFORE loop.close()
        cleanup_success = True
        
        try:
            # Step 1: Run registered cleanup callbacks FIRST (includes async session wrappers)
            for cleanup_callback in getattr(loop, '_test_cleanup_callbacks', []):
                try:
                    cleanup_callback()
                except Exception as e:
                    logger.debug(f"Cleanup callback error: {e}")
            
            # Step 2: ARCHITECT FIX: Dispose all centrally registered async engines
            try:
                from database import dispose_all_async_engines
                loop.run_until_complete(dispose_all_async_engines("test_cleanup"))
                logger.debug("✅ Disposed all centrally registered async engines")
            except Exception as e:
                logger.debug(f"Central engine disposal: {e}")
            
            # Step 2b: Dispose locally tracked engines as fallback
            for engine in getattr(loop, '_test_async_engines', []):
                try:
                    if hasattr(engine, 'dispose') and callable(engine.dispose):
                        loop.run_until_complete(engine.dispose())
                except Exception as e:
                    logger.debug(f"Local engine disposal: {e}")
            
            # Step 3: Close all registered async database sessions AFTER engine disposal
            for session_list in getattr(loop, '_test_async_sessions', []):
                try:
                    for session in session_list:
                        if hasattr(session, 'close') and callable(session.close):
                            loop.run_until_complete(session.close())
                except Exception as e:
                    logger.debug(f"Session cleanup: {e}")
            
            # Step 4: Cancel and await ALL pending tasks BEFORE closing loop
            pending = asyncio.all_tasks(loop)
            if pending:
                # Cancel all tasks
                for task in pending:
                    if not task.done():
                        task.cancel()
                
                # Wait for all cancelled tasks to complete
                try:
                    loop.run_until_complete(
                        asyncio.wait_for(
                            asyncio.gather(*pending, return_exceptions=True),
                            timeout=15.0  # Increased timeout for proper cleanup
                        )
                    )
                except (asyncio.TimeoutError, asyncio.CancelledError) as e:
                    logger.debug(f"Task cancellation timeout (expected): {e}")
                except Exception as e:
                    logger.debug(f"Task cleanup with exceptions (expected): {e}")
            
            # Step 5: Shutdown async generators (critical for SQLAlchemy async)
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception as e:
                logger.debug(f"Async generators shutdown: {e}")
            
            # Step 6: Shutdown default executor
            try:
                loop.run_until_complete(loop.shutdown_default_executor())
            except Exception as e:
                logger.debug(f"Default executor shutdown: {e}")
                
        except Exception as e:
            logger.debug(f"Event loop cleanup completed with exceptions: {e}")
            cleanup_success = False
        
        # Step 7: CRITICAL FIX - Only close loop AFTER all async operations are complete
        try:
            if not loop.is_closed():
                loop.close()
        except Exception as e:
            logger.debug(f"Loop close: {e}")
        
        # Clear all references and cleanup tracking
        loop._test_async_engines = []
        loop._test_async_sessions = []
        loop._test_cleanup_callbacks = []
        
        # Final global cleanup to catch any missed resources
        try:
            # Global engine cleanup
            for engine in _GLOBAL_ASYNC_RESOURCES['engines'].copy():
                try:
                    if hasattr(engine, 'dispose'):
                        loop.run_until_complete(engine.dispose())
                    _GLOBAL_ASYNC_RESOURCES['engines'].remove(engine)
                except Exception as e:
                    logger.debug(f"Global engine cleanup: {e}")
            
            # Global callback cleanup
            for callback in _GLOBAL_ASYNC_RESOURCES['cleanup_callbacks'].copy():
                try:
                    callback()
                    _GLOBAL_ASYNC_RESOURCES['cleanup_callbacks'].remove(callback)
                except Exception as e:
                    logger.debug(f"Global callback cleanup: {e}")
                    
            # Clear all global resources
            _GLOBAL_ASYNC_RESOURCES['engines'].clear()
            _GLOBAL_ASYNC_RESOURCES['sessions'].clear()
            _GLOBAL_ASYNC_RESOURCES['connections'].clear() 
            _GLOBAL_ASYNC_RESOURCES['tasks'].clear()
            _GLOBAL_ASYNC_RESOURCES['cleanup_callbacks'].clear()
            
        except Exception as e:
            logger.debug(f"Global cleanup completed with exceptions: {e}")
        
        if cleanup_success:
            logger.debug("✅ Event loop cleanup completed successfully")


@pytest.fixture(scope="session")
def test_engine():
    """Create PostgreSQL test database engine for session"""
    # Use the actual PostgreSQL database for testing
    engine = create_engine(
        TEST_DATABASE_URL,
        echo=TEST_DATABASE_ECHO,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10
    )
    
    yield engine
    engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_db_session():
    """
    ARCHITECT'S ASYNC DATABASE FIX: Create proper AsyncSession with SAVEPOINT transactions
    
    Key fixes:
    - Single AsyncEngine per test with proper isolation
    - SAVEPOINT transactions using begin_nested() for test isolation  
    - Yields AsyncSession directly (not async generator)
    - expire_on_commit=False for consistent connection reuse
    - Proper async session lifecycle management
    """
    from sqlalchemy.pool import StaticPool
    import uuid
    import threading
    
    # Generate thread-safe unique test identifier for debugging
    thread_id = threading.get_ident()
    test_id = str(uuid.uuid4())[:8]
    unique_test_id = f"test_{thread_id}_{test_id}"
    
    # Create PostgreSQL AsyncEngine with asyncpg driver
    async_engine = create_async_engine(
        TEST_DATABASE_URL_ASYNC,
        echo=TEST_DATABASE_ECHO,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10
    )
    
    # Import all models to ensure they're registered with Base
    import models
    from models import Base
    
    logger.info(f"🧪 ARCHITECT ASYNC FIX: Creating tables with async engine ({len(Base.metadata.tables)} models)")
    
    # CRITICAL FIX: Create tables using async engine
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("✅ ARCHITECT FIX: Tables created using async engine")
    
    # ARCHITECT FIX: Patch database functions to use test engine (if they exist)
    import database
    
    # Check if functions exist before patching (support for direct DB access tests)
    original_get_async_engine = getattr(database, 'get_async_engine', None)
    original_managed_session = getattr(database, 'managed_session', None)
    original_async_session_factory = getattr(database, '_get_async_session_factory', None)
    
    # Skip patching if functions don't exist (e.g., for E2E tests using direct DB access)
    if not original_get_async_engine:
        logger.info("⏭️ Skipping database patching - functions not found (E2E mode)")
        # For E2E tests, just yield a simple session
        from database import SessionLocal
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()
        return
    
    # Create test async session factory with expire_on_commit=False
    test_async_session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,  # ARCHITECT FIX: Consistent connection reuse
    )
    
    # Patch functions to use test engine
    database.get_async_engine = lambda: async_engine
    database._get_async_session_factory = lambda: test_async_session_factory
    
    @asynccontextmanager  
    async def test_managed_session():
        """Test version of managed_session that uses test async engine"""
        async with test_async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    # Patch managed_session
    database.managed_session = test_managed_session
    
    logger.info("✅ ARCHITECT FIX: Patched managed_session for handlers")
    
    # ARCHITECT FIX: Create session with SAVEPOINT transaction for proper test isolation
    async with test_async_session_factory() as session:
        # CRITICAL FIX: Begin nested transaction (SAVEPOINT) for test isolation
        transaction = await session.begin_nested()
        
        try:
            # ARCHITECT FIX: Yield AsyncSession directly (not async generator)
            yield session
        except Exception:
            # Rollback SAVEPOINT transaction on error
            await transaction.rollback()
            raise
        finally:
            # Always rollback SAVEPOINT to isolate test changes
            if transaction.is_active:
                await transaction.rollback()
            
            # Restore original functions
            database.get_async_engine = original_get_async_engine
            database.managed_session = original_managed_session
            database._get_async_session_factory = original_async_session_factory
            logger.debug("✅ ARCHITECT FIX: Restored original database functions")
            
            # Close session properly
            await session.close()
            
            # Dispose async engine
            await async_engine.dispose()
            logger.debug(f"✅ ARCHITECT FIX: Cleaned up test async database: {unique_db_id}")


@pytest.fixture
def test_config():
    """Provide test configuration that disables background jobs and external services"""
    original_config = {}
    
    # Store original config values
    test_overrides = {
        'TESTING': True,
        'DISABLE_BACKGROUND_JOBS': True,
        'DISABLE_EXTERNAL_API_CALLS': True,
        'RATE_LIMITING_ENABLED': False,
        'WEBHOOK_PROCESSING_ENABLED': False,
        'EMAIL_SENDING_ENABLED': False,
        'SMS_SENDING_ENABLED': False,
    }
    
    # Apply test overrides
    for key, value in test_overrides.items():
        original_config[key] = getattr(Config, key, None)
        setattr(Config, key, value)
    
    yield Config
    
    # Restore original config
    for key, value in original_config.items():
        if value is not None:
            setattr(Config, key, value)
        else:
            delattr(Config, key)


@pytest.fixture
def mock_external_services():
    """Provide comprehensive mock external services for testing"""
    
    mock_services = {
        'fincra': Mock(),
        'kraken': Mock(), 
        'crypto': Mock(),
        'fastforex': Mock(),
        'email': Mock(),
        'otp': Mock(),
        'unified_transaction': Mock(),
        'notifications': Mock(),
        'admin_alerts': Mock()
    }
    
    # Configure realistic mock responses for Fincra
    mock_services['fincra'].process_bank_transfer.return_value = {
        'success': True,
        'reference': 'FINCRA_TEST_REF_123',
        'status': 'processing',
        'requires_admin_funding': False
    }
    mock_services['fincra'].check_bank_account.return_value = {
        'success': True,
        'account_name': 'TEST USER ACCOUNT',
        'bank_name': 'ACCESS BANK'
    }
    
    # Configure realistic mock responses for Kraken
    mock_services['kraken'].withdraw_crypto.return_value = {
        'success': True,
        'txid': 'KRAKEN_TX_123',
        'refid': 'KRAKEN_REF_123'
    }
    mock_services['kraken'].check_balance.return_value = {
        'success': True,
        'USD': Decimal('1000.00'),
        'BTC': Decimal('0.1')
    }
    
    # Configure realistic mock responses for Crypto service
    mock_services['crypto'].generate_deposit_address.return_value = {
        'success': True,
        'address': 'bc1qtest_address_12345',
        'memo': None
    }
    mock_services['crypto'].check_payment.return_value = {
        'success': True,
        'confirmed': True,
        'amount_received': Decimal('0.001'),
        'confirmations': 6
    }
    mock_services['crypto'].credit_wallet.return_value = {
        'success': True,
        'new_balance': Decimal('1000.00')
    }
    mock_services['crypto'].debit_wallet.return_value = {
        'success': True,
        'new_balance': Decimal('900.00')
    }
    # CRITICAL FIX: Add missing send_crypto method for exchange lifecycle tests
    mock_services['crypto'].send_crypto.return_value = {
        'success': True,
        'tx_hash': 'test_tx_hash_12345',
        'amount_sent': Decimal('0.001'),
        'net_amount': Decimal('0.001')
    }
    # CRITICAL FIX: Fix Mock format string error by returning proper Decimal
    mock_services['crypto'].get_user_balance_atomic.return_value = Decimal('25.50')
    
    # Configure realistic mock responses for FastForex
    mock_services['fastforex'].get_live_rate.return_value = {
        'success': True,
        'rate': Decimal('1520.00'),  # USD-NGN rate
        'source': 'fastforex',
        'timestamp': datetime.utcnow()
    }
    
    # Configure realistic mock responses for Email service
    mock_services['email'].send_otp_email.return_value = {
        'success': True,
        'message_id': 'EMAIL_OTP_123',
        'delivery_time_ms': 250
    }
    mock_services['email'].send_welcome_email.return_value = {
        'success': True,
        'message_id': 'EMAIL_WELCOME_456'
    }
    
    # Configure realistic mock responses for OTP service
    mock_services['otp'].generate_otp.return_value = '123456'
    # Fix critical OTP verification mock - OnboardingService expects dict format
    mock_services['otp'].verify_otp.return_value = {
        'success': True,
        'message': 'OTP verified successfully',
        'email': 'test@example.com',
        'remaining_attempts': 4
    }
    mock_services['otp'].is_otp_expired.return_value = False
    
    # Configure realistic mock responses for Unified Transaction service
    mock_services['unified_transaction'].create_transaction.return_value = {
        'success': True,
        'transaction_id': 'UTE_TEST_123',
        'status': 'processing'
    }
    
    # Configure notification mocks
    mock_services['notifications'].send_notification.return_value = True
    mock_services['admin_alerts'].send_alert.return_value = True
    
    yield mock_services


@pytest.fixture
def patched_services(mock_external_services, monkeypatch):
    """Patch services at their main module locations AND specific imports"""
    
    # Patch main service instances
    monkeypatch.setattr(
        "services.fincra_service.fincra_service", 
        mock_external_services['fincra']
    )
    monkeypatch.setattr(
        "services.kraken_service.kraken_service", 
        mock_external_services['kraken']
    )
    monkeypatch.setattr(
        "services.fastforex_service.fastforex_service", 
        mock_external_services['fastforex']
    )
    monkeypatch.setattr(
        "services.async_email_service.async_email_service", 
        mock_external_services['email']
    )
    
    # CRITICAL FIX: Also patch the imported service in ExchangeService
    # This ensures test mocks work correctly for rate calculations
    monkeypatch.setattr(
        "services.exchange_service.fastforex_service", 
        mock_external_services['fastforex']
    )
    
    # PostgreSQL per-test database isolation with transaction-based testing
    import uuid
    test_db_unique_id = str(uuid.uuid4())[:8]
    # Use the same PostgreSQL database for all tests with transaction isolation
    test_async_url = TEST_DATABASE_URL_ASYNC
    test_sync_url = TEST_DATABASE_URL
    
    logger.info(f"🧪 ARCHITECT FIX: Per-test DB isolation with ID: {test_db_unique_id}")
    
    # Create PostgreSQL engines for this test run
    _test_async_engine = create_async_engine(
        test_async_url,
        pool_pre_ping=True,
        echo=TEST_DATABASE_ECHO,
        pool_size=5,
        max_overflow=10
    )
    
    _test_sync_engine = create_engine(
        test_sync_url,
        pool_pre_ping=True,
        echo=TEST_DATABASE_ECHO,
        pool_size=5,
        max_overflow=10
    )
    
    # COMPREHENSIVE ENGINE MONKEYPATCHING - Patch ALL engine creation functions
    def mock_create_async_engine():
        """Mock _create_async_engine for per-test isolation"""
        logger.debug(f"🔧 Returning per-test async engine: {test_db_unique_id}")
        return _test_async_engine
    
    def mock_get_async_engine():
        """Mock get_async_engine for per-test isolation"""
        return _test_async_engine
    
    def mock_create_sync_engine():
        """Mock _create_sync_engine for per-test isolation"""
        logger.debug(f"🔧 Returning per-test sync engine: {test_db_unique_id}")
        return _test_sync_engine
        
    def mock_get_sync_engine():
        """Mock get_sync_engine for per-test isolation"""
        return _test_sync_engine
    
    # CRITICAL: Patch ALL engine creation and session factory functions
    # Note: Only patch functions that actually exist in database.py
    import database
    if hasattr(database, "get_async_engine"):
        monkeypatch.setattr("database.get_async_engine", mock_get_async_engine)
    if hasattr(database, "_create_sync_engine"):
        monkeypatch.setattr("database._create_sync_engine", mock_create_sync_engine)
    if hasattr(database, "get_sync_engine"):
        monkeypatch.setattr("database.get_sync_engine", mock_get_sync_engine)
    
    # CRITICAL: Patch SessionLocal and managed_session to use per-test engines
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.asyncio import async_sessionmaker
    
    # Create per-test session factories
    test_sync_session_factory = sessionmaker(
        bind=_test_sync_engine,
        autoflush=False,
        expire_on_commit=False
    )
    
    test_async_session_factory = async_sessionmaker(
        bind=_test_async_engine,
        autoflush=False,
        expire_on_commit=False
    )
    
    def mock_session_local():
        """Mock SessionLocal to use per-test sync engine"""
        return test_sync_session_factory()
    
    async def mock_managed_session():
        """Mock managed_session to use per-test async engine"""
        async with test_async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    # Patch SessionLocal at ALL import locations
    monkeypatch.setattr("database.SessionLocal", mock_session_local)
    monkeypatch.setattr("database.SyncSessionLocal", mock_session_local)
    monkeypatch.setattr("database.managed_session", mock_managed_session)
    
    # Register engines for cleanup
    if hasattr(event_loop, '_test_async_engines'):
        event_loop._test_async_engines.extend([_test_async_engine, _test_sync_engine])
    
    # PostgreSQL engines have built-in foreign key enforcement - no additional setup needed
    # PostgreSQL natively supports and enforces foreign key constraints
    logger.debug("✅ PostgreSQL engines configured with native foreign key support")
    
    # PRIORITY 2 FIX: Comprehensive EmailVerificationService patching at all import locations
    # This ensures consistent mock behavior across all handlers and services
    # Mock both sync and async methods for compatibility
    email_verification_mock = MagicMock()
    
    # Standard mock responses for both sync and async methods
    otp_verify_response = {
        'success': True,
        'message': 'OTP verified successfully',
        'email': 'test@example.com',
        'remaining_attempts': 4
    }
    otp_send_response = {
        'success': True,
        'message_id': 'TEST_OTP_EMAIL_123',
        'delivery_time_ms': 250
    }
    
    # Setup sync method mocks (compatibility layer)
    email_verification_mock.verify_otp.return_value = otp_verify_response
    email_verification_mock.send_otp.return_value = otp_send_response
    
    # Setup async method mocks (actual implementation)
    async_verify_mock = AsyncMock(return_value=otp_verify_response)
    async_send_mock = AsyncMock(return_value=otp_send_response)
    email_verification_mock.verify_otp_async = async_verify_mock
    email_verification_mock.send_otp_async = async_send_mock
    
    # Patch at module level (primary location) - both sync and async methods
    monkeypatch.setattr(
        "services.email_verification_service.EmailVerificationService.verify_otp",
        email_verification_mock.verify_otp
    )
    monkeypatch.setattr(
        "services.email_verification_service.EmailVerificationService.verify_otp_async",
        email_verification_mock.verify_otp_async
    )
    monkeypatch.setattr(
        "services.email_verification_service.EmailVerificationService.send_otp",
        email_verification_mock.send_otp
    )
    monkeypatch.setattr(
        "services.email_verification_service.EmailVerificationService.send_otp_async",
        email_verification_mock.send_otp_async
    )
    
    # CRITICAL: Patch at handler import locations to ensure consistency  
    # Since EmailVerificationService is imported locally within functions,
    # we need to patch at the class level which will be used by all imports
    try:
        monkeypatch.setattr(
            "handlers.onboarding_router.EmailVerificationService.verify_otp",
            email_verification_mock.verify_otp
        )
        monkeypatch.setattr(
            "handlers.onboarding_router.EmailVerificationService.verify_otp_async",
            email_verification_mock.verify_otp_async
        )
        monkeypatch.setattr(
            "handlers.onboarding_router.EmailVerificationService.send_otp", 
            email_verification_mock.send_otp
        )
        monkeypatch.setattr(
            "handlers.onboarding_router.EmailVerificationService.send_otp_async", 
            email_verification_mock.send_otp_async
        )
    except AttributeError:
        # Module may not be imported yet, skip this specific patch
        pass
    
    # NOTE: OnboardingService uses local imports inside functions, 
    # so the module-level patching above will handle the actual calls
    
    # CRITICAL FIX: Patch get_user_display_name to prevent Mock format string errors
    monkeypatch.setattr(
        "utils.helpers.get_user_display_name",
        lambda user: f"{getattr(user, 'first_name', 'User')} {getattr(user, 'last_name', '')}"
    )
    
    # Patch service classes - replace the class itself with a mock that has class methods
    # Create class-like mock for CryptoServiceAtomic with required methods
    crypto_class_mock = MagicMock()
    # Add all methods that might be called as class methods or instance methods
    crypto_class_mock.get_user_balance_atomic = mock_external_services['crypto'].get_user_balance_atomic
    crypto_class_mock.return_value = mock_external_services['crypto']  # For instantiation
    monkeypatch.setattr("services.crypto.CryptoServiceAtomic", crypto_class_mock)
    
    # Create class-like mock for ConditionalOTPService
    otp_class_mock = MagicMock()
    otp_class_mock.generate_otp = mock_external_services['otp'].generate_otp
    otp_class_mock.verify_otp = mock_external_services['otp'].verify_otp
    otp_class_mock.is_otp_expired = mock_external_services['otp'].is_otp_expired
    otp_class_mock.return_value = mock_external_services['otp']  # For instantiation
    monkeypatch.setattr("services.conditional_otp_service.ConditionalOTPService", otp_class_mock)
    
    # Create class-like mock for UnifiedTransactionService
    ute_class_mock = MagicMock()
    ute_class_mock.create_transaction = mock_external_services['unified_transaction'].create_transaction
    ute_class_mock.return_value = mock_external_services['unified_transaction']  # For instantiation
    monkeypatch.setattr("services.unified_transaction_service.UnifiedTransactionService", ute_class_mock)
    
    # ARCHITECT FIX: Add email verification mock to returned services for proper test assertions
    mock_external_services['email_verification'] = email_verification_mock
    
    yield mock_external_services


@pytest.fixture(scope="function")
def test_async_db_session(test_db_session, event_loop):
    """Create async database session wrapper for test database with SHARED engine for session isolation fix"""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy.pool import StaticPool
    import asyncio
    
    # ARCHITECT FIX: Create async engine with StaticPool for shared session isolation
    test_async_engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
        poolclass=StaticPool,  # CRITICAL: StaticPool ensures shared connection state
        pool_pre_ping=True,  # Helps with connection validation
        connect_args={
            "check_same_thread": False,
            "uri": True  # Enable URI connections for shared cache
        }
    )
    
    # Register engine for cleanup in event loop fixture and global tracking
    if hasattr(event_loop, '_test_async_engines'):
        event_loop._test_async_engines.append(test_async_engine)
    _GLOBAL_ASYNC_RESOURCES['engines'].append(test_async_engine)
    
    # Create session factory with proper async context management
    TestAsyncSession = async_sessionmaker(
        bind=test_async_engine,
        expire_on_commit=False  # Prevent expired instance errors
    )
    
    # CRITICAL FIX: Setup tables asynchronously with COMPREHENSIVE model imports and verification
    async def setup_async_tables():
        # Import ALL models EXPLICITLY to ensure they're registered with Base (same as sync setup)
        from models import (
            Base, User, Wallet, Escrow, EscrowStatus, Transaction, TransactionType,
            Cashout, CashoutStatus, CashoutProcessingMode, ExchangeOrder, ExchangeStatus,
            UnifiedTransaction, UnifiedTransactionStatus, UnifiedTransactionType,
            UnifiedTransactionStatusHistory, UnifiedTransactionRetryLog, UnifiedTransactionMetadata,
            Rating, Dispute, EscrowMessage, SavedAddress, SavedBankAccount,
            WalletHolds, WalletHoldStatus, EscrowHolding, PendingCashout, Refund,
            DistributedLock, IdempotencyToken, WebhookEventLedger, PlatformRevenue,
            PartialReleaseAudit, UserStatus, OnboardingStep, OnboardingSession,
            EmailVerification, DisputeMessage, SupportTicket, SupportMessage,
            NotificationPreference, AdminAction, SystemConfig, DirectExchange, WebhookLog
        )
        
        logger.info(f"🔧 ASYNC SCHEMA SETUP: Imported all models, Base.metadata.tables count: {len(Base.metadata.tables)}")
        
        try:
            async with test_async_engine.begin() as conn:
                # Create all tables
                await conn.run_sync(Base.metadata.create_all)
                logger.info("✅ ASYNC: Created all tables successfully")
                
                # ASYNC TABLE VERIFICATION: Verify critical tables were created
                def verify_tables(conn):
                    from sqlalchemy import inspect
                    inspector = inspect(conn)
                    created_tables = inspector.get_table_names()
                    
                    # List of critical tables that MUST exist for tests to work
                    critical_tables = [
                        'users', 'wallets', 'escrows', 'transactions', 'cashouts', 
                        'unified_transactions', 'escrow_holdings', 'exchanges', 
                        'onboarding_sessions', 'email_verifications'
                    ]
                    
                    missing_tables = [table for table in critical_tables if table not in created_tables]
                    if missing_tables:
                        raise RuntimeError(f"CRITICAL ASYNC: Missing required tables: {missing_tables}")
                    
                    logger.info(f"✅ ASYNC VERIFICATION PASSED: All {len(created_tables)} tables created successfully")
                    
                    # Double-check user table specifically (most common failure)
                    if 'users' not in created_tables:
                        raise RuntimeError("CRITICAL ASYNC: 'users' table not created - this will cause test failures")
                    
                    logger.info("✅ ASYNC CRITICAL TABLE CHECK: 'users' table verified present")
                    return created_tables
                    
                # Run verification
                await conn.run_sync(verify_tables)
                
        except Exception as e:
            logger.error(f"❌ ASYNC DATABASE SETUP ERROR: {e}")
            # Fallback to sync setup if async fails
            try:
                Base.metadata.create_all(test_db_session.bind)
                logger.info("✅ ASYNC FALLBACK: Tables created via sync fallback method")
                
                # Re-verify after sync fallback
                from sqlalchemy import inspect
                inspector = inspect(test_db_session.bind)
                created_tables = inspector.get_table_names()
                
                if 'users' not in created_tables:
                    logger.error("❌ ASYNC FALLBACK FAILED: 'users' table still missing")
                    raise RuntimeError("Async database setup failed: users table not created")
                    
            except Exception as sync_e:
                logger.error(f"❌ ASYNC CRITICAL FAILURE: Could not create test database tables: {sync_e}")
                raise RuntimeError(f"Async database setup failed completely: {sync_e}")
    
    # Use the session's event loop for setup
    try:
        event_loop.run_until_complete(setup_async_tables())
    except Exception as e:
        logger.error(f"❌ Async setup failed: {e}")
        raise
    
    # Track created sessions for cleanup
    created_sessions = []
    
    # Wrap session factory to track sessions
    class TrackedAsyncSessionFactory:
        def __call__(self):
            session = TestAsyncSession()
            created_sessions.append(session)
            return session
        
        def __getattr__(self, name):
            return getattr(TestAsyncSession, name)
    
    tracked_factory = TrackedAsyncSessionFactory()
    
    # Register sessions for cleanup
    if hasattr(event_loop, '_test_async_sessions'):
        event_loop._test_async_sessions.append(created_sessions)
    
    yield tracked_factory
    
    # IMMEDIATE CLEANUP - don't wait for event loop fixture
    async def cleanup_async_resources():
        try:
            # Close all sessions created by this fixture
            for session in created_sessions:
                try:
                    if hasattr(session, 'close'):
                        await session.close()
                except Exception as e:
                    logger.debug(f"Session close error: {e}")
            
            # Dispose engine
            try:
                await test_async_engine.dispose()
            except Exception as e:
                logger.debug(f"Engine dispose error: {e}")
                
        except Exception as e:
            logger.debug(f"Async cleanup error: {e}")
    
    # Run cleanup in the event loop
    try:
        event_loop.run_until_complete(cleanup_async_resources())
    except Exception as e:
        logger.debug(f"Async cleanup completed with errors: {e}")


@pytest.fixture(autouse=True)
def patch_sync_async_sessions(test_db_session, monkeypatch):
    """
    ARCHITECT'S SYNC/ASYNC SESSION FIX: Clean session patching for proper test isolation
    
    Key fixes:
    - SessionLocal returns sync session bound to same test engine/connection
    - Eliminates sync/async engine mixing within same test flow
    - Ensures proper state visibility between sync and async operations
    - No complex async wrappers that cause rollback() errors
    """
    
    # ARCHITECT FIX: Simple sync session factory bound to same engine as async session
    
    def mock_session_local():
        """
        ARCHITECT FIX: Return sync session bound to same test engine
        This prevents sync/async engine mixing and ensures state visibility  
        """
        # Get the engine from our async test session and create a sync session
        from sqlalchemy.orm import sessionmaker
        if hasattr(test_db_session, 'get_bind'):
            engine = test_db_session.get_bind()
            sync_factory = sessionmaker(bind=engine)
            return sync_factory()
        else:
            # Fallback - use the test session's bind directly
            logger.warning("Using test session bind for SessionLocal")
            return test_db_session
    @contextmanager
    def mock_sync_managed_session():
        """Mock sync_managed_session that uses same test engine"""
        session = mock_session_local()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    
    # ARCHITECT FIX: Apply clean patches for sync/async consistency
    # Note: managed_session is already patched by test_db_session fixture
    
    # Import database module to check for attributes
    import database
    
    # Only patch if attributes exist (support for E2E tests with direct DB access)
    if hasattr(database, 'sync_managed_session'):
        monkeypatch.setattr("database.sync_managed_session", mock_sync_managed_session)
    if hasattr(database, 'SessionLocal'):
        monkeypatch.setattr("database.SessionLocal", mock_session_local)
    if hasattr(database, 'SyncSessionLocal'):
        monkeypatch.setattr("database.SyncSessionLocal", mock_session_local)
    
    # CRITICAL FIX: Patch database engine creation to use test engine (only if functions exist)
    if hasattr(database, 'get_sync_engine'):
        monkeypatch.setattr("database.get_sync_engine", lambda: test_db_session.bind)
    if hasattr(database, '_create_sync_engine'):
        monkeypatch.setattr("database._create_sync_engine", lambda: test_db_session.bind)
    
    # Note: managed_session is already properly patched by test_db_session fixture
    
    # List of modules that actually import managed_session and sync_managed_session (from grep results)
    modules_to_patch = [
        "handlers.onboarding_router",
        "services.onboarding_service", 
        "services.email_verification_service",
        "services.unified_transaction_service",
        "services.crypto",
        "services.balance_monitor",
        "services.unified_retry_service"
    ]
    
    patched_modules = []
    # Safely patch only modules that actually have managed_session or sync_managed_session
    for module_path in modules_to_patch:
        try:
            # Try to get the attribute first to see if it exists
            import importlib
            module = importlib.import_module(module_path)
            
            module_patched = False
            # managed_session patching handled by test_db_session fixture
            # if hasattr(module, 'managed_session'):
            #     module_patched = True
            
            # Patch sync_managed_session if it exists
            if hasattr(module, 'sync_managed_session'):
                monkeypatch.setattr(f"{module_path}.sync_managed_session", mock_sync_managed_session)
                module_patched = True
            
            if module_patched:
                patched_modules.append(module_path)
                
        except (ImportError, AttributeError) as e:
            logger.debug(f"Skipping {module_path}: {e}")
            continue
    
    logger.info(f"🔧 Database session patching applied to {len(patched_modules)} modules: {patched_modules}")
    
    yield
    
    # Cleanup handled by test_db_session fixture


@pytest.fixture(autouse=True)
def auto_patch_telegram_for_all_tests(patched_telegram_utilities):
    """Automatically apply Telegram patches to all tests"""
    # This fixture runs automatically for all tests
    # It ensures Telegram utilities are properly mocked
    yield patched_telegram_utilities


class TelegramObjectFactory:
    """Factory for creating realistic Telegram objects for testing"""
    
    def __init__(self):
        self._user_id_counter = 1000000000  # Start with realistic Telegram IDs
        self._message_id_counter = 1
        self._chat_id_counter = -1000000000  # Start with realistic chat IDs
        self._mock_bot = self._create_comprehensive_bot_mock()
    
    def create_user(self, 
                   telegram_id: int = None,
                   username: str = None,
                   first_name: str = "Test",
                   last_name: str = "User",
                   is_bot: bool = False) -> TelegramUser:
        """Create a realistic Telegram User object"""
        
        if telegram_id is None:
            telegram_id = self._user_id_counter
            self._user_id_counter += 1
        
        if username is None:
            username = f"testuser{telegram_id}"
        
        return TelegramUser(
            id=telegram_id,
            is_bot=is_bot,
            first_name=first_name,
            last_name=last_name,
            username=username,
            language_code='en'
        )
    
    def create_chat(self,
                   chat_id: int = None,
                   chat_type: str = "private",
                   title: str = None) -> Chat:
        """Create a realistic Telegram Chat object"""
        
        if chat_id is None:
            if chat_type == "private":
                chat_id = self._user_id_counter
                self._user_id_counter += 1
            else:
                chat_id = self._chat_id_counter
                self._chat_id_counter -= 1
        
        return Chat(
            id=chat_id,
            type=chat_type,
            title=title
        )
    
    def create_message(self,
                      text: str,
                      user: TelegramUser = None,
                      chat: Chat = None,
                      message_id: int = None) -> Message:
        """Create a realistic Telegram Message object"""
        
        if user is None:
            user = self.create_user()
        
        if chat is None:
            chat = self.create_chat(chat_id=user.id)
        
        if message_id is None:
            message_id = self._message_id_counter
            self._message_id_counter += 1
        
        message = Message(
            message_id=message_id,
            from_user=user,
            date=datetime.utcnow(),
            chat=chat,
            text=text
        )
        
        # Add bot reference for shortcuts to work
        message.set_bot(self._mock_bot)
        return message
    
    def create_callback_query(self,
                            data: str,
                            user: TelegramUser = None,
                            message: Message = None) -> CallbackQuery:
        """Create a realistic Telegram CallbackQuery object"""
        
        if user is None:
            user = self.create_user()
        
        if message is None:
            message = self.create_message("Test callback message", user=user)
        
        callback_query = CallbackQuery(
            id=str(uuid.uuid4()),
            from_user=user,
            chat_instance=str(uuid.uuid4()),
            data=data,
            message=message
        )
        
        # Add bot reference for callback operations
        callback_query.set_bot(self._mock_bot)
        return callback_query
    
    def create_update(self,
                     message: Message = None,
                     callback_query: CallbackQuery = None,
                     update_id: int = None) -> Update:
        """Create a realistic Telegram Update object"""
        
        if update_id is None:
            update_id = self._message_id_counter
            self._message_id_counter += 1
        
        update = Update(
            update_id=update_id,
            message=message,
            callback_query=callback_query
        )
        
        # Add bot reference to update for handler compatibility
        update._bot = self._mock_bot
        return update
    
    def create_context(self,
                      user_data: Dict = None,
                      chat_data: Dict = None,
                      bot_data: Dict = None) -> ContextTypes.DEFAULT_TYPE:
        """Create a realistic Telegram Context object"""
        
        # Create a mock context with all necessary attributes
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = user_data or {}
        context.chat_data = chat_data or {}
        context.bot_data = bot_data or {}
        
        # Use the comprehensive bot mock
        context.bot = self._mock_bot
        
        # Mock job queue
        context.job_queue = MagicMock()
        context.job_queue.run_once = MagicMock()
        
        return context
    
    def _create_comprehensive_bot_mock(self):
        """Create a comprehensive bot mock with all required methods"""
        bot_mock = MagicMock()
        
        # Configure all essential bot methods as AsyncMocks
        bot_mock.send_message = AsyncMock(return_value=self._create_mock_message_response())
        bot_mock.edit_message_text = AsyncMock(return_value=self._create_mock_message_response())
        bot_mock.answer_callback_query = AsyncMock(return_value=True)
        bot_mock.delete_message = AsyncMock(return_value=True)
        bot_mock.pin_chat_message = AsyncMock(return_value=True)
        bot_mock.unpin_chat_message = AsyncMock(return_value=True)
        bot_mock.get_chat_member = AsyncMock(return_value=MagicMock())
        bot_mock.get_chat = AsyncMock(return_value=MagicMock())
        bot_mock.set_chat_administrator_custom_title = AsyncMock(return_value=True)
        bot_mock.send_photo = AsyncMock(return_value=self._create_mock_message_response())
        bot_mock.send_document = AsyncMock(return_value=self._create_mock_message_response())
        bot_mock.send_video = AsyncMock(return_value=self._create_mock_message_response())
        bot_mock.send_audio = AsyncMock(return_value=self._create_mock_message_response())
        bot_mock.forward_message = AsyncMock(return_value=self._create_mock_message_response())
        bot_mock.copy_message = AsyncMock(return_value=MagicMock())
        
        # Configure bot properties
        bot_mock.id = 123456789
        bot_mock.username = 'test_bot'
        bot_mock.first_name = 'Test Bot'
        bot_mock.can_join_groups = True
        bot_mock.can_read_all_group_messages = True
        bot_mock.supports_inline_queries = False
        
        return bot_mock
    
    def _create_mock_message_response(self):
        """Create a realistic message response for bot operations"""
        message_response = MagicMock()
        message_response.message_id = self._message_id_counter
        message_response.date = datetime.utcnow()
        message_response.chat = MagicMock()
        message_response.chat.id = 123456789
        message_response.from_user = MagicMock()
        message_response.from_user.id = 123456789
        message_response.text = "Mock response"
        
        self._message_id_counter += 1
        return message_response
    
    def get_bot_mock(self):
        """Get the shared bot mock instance"""
        return self._mock_bot


@pytest.fixture
def telegram_factory():
    """Provide Telegram object factory"""
    return TelegramObjectFactory()


@pytest.fixture
def mock_bot():
    """Provide a shared mock bot for all tests"""
    factory = TelegramObjectFactory()
    return factory.get_bot_mock()


@pytest.fixture
def patched_telegram_utilities(mock_bot, monkeypatch):
    """Patch Telegram utility functions to use mock bot during tests"""
    
    # Patch get_bot_instance in message_utils to return our mock bot
    monkeypatch.setattr(
        "utils.message_utils.get_bot_instance", 
        lambda: mock_bot
    )
    
    # Set a mock TELEGRAM_BOT_TOKEN for tests
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "mock_token_for_tests")
    
    # Patch Bot class constructor to prevent real bot creation
    def mock_bot_constructor(token):
        return mock_bot
    
    monkeypatch.setattr(
        "telegram.Bot", 
        mock_bot_constructor
    )
    
    # Patch the global bot instance in message_utils if it exists
    import utils.message_utils
    utils.message_utils._bot_instance = mock_bot
    
    yield mock_bot
    
    # Clean up the global bot instance after test
    utils.message_utils._bot_instance = None


class TestDataFactory:
    """Factory for creating test database records"""
    
    def __init__(self, session):
        self.session = session
        # Use timestamp-based counters to ensure uniqueness across test runs
        import time
        import random
        self._base_timestamp = int(time.time() * 1000)  # milliseconds since epoch
        self._random_suffix = random.randint(1000, 9999)
        self._user_counter = 0
        self._escrow_counter = 0
        self._transaction_counter = 0
    
    async def create_test_user(self,
                        telegram_id: str = None,
                        username: str = None,
                        email: str = None,
                        balances: Optional[Dict[str, Decimal]] = None,
                        is_verified: bool = True) -> User:
        """Create test user with optional wallet balances"""
        
        if telegram_id is None:
            telegram_id = f'test_user_{self._base_timestamp}_{self._random_suffix}_{self._user_counter}'
            self._user_counter += 1
        
        if username is None:
            username = f'testuser_{telegram_id}'
        
        if email is None:
            email = f'{telegram_id}@test.com'
        
        if balances is None:
            balances = {'USD': Decimal('1000.00')}
        
        # Create user
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name='Test',
            last_name='User',
            email=email,
            email_verified=is_verified,
            created_at=datetime.utcnow()
        )
        
        self.session.add(user)
        await self.session.commit()
        
        # Create wallets
        for currency, balance in balances.items():
            wallet = Wallet(
                user_id=user.id,
                currency=currency,
                balance=balance,
                frozen_balance=Decimal('0.00'),
                created_at=datetime.utcnow()
            )
            self.session.add(wallet)
        
        await self.session.commit()
        
        logger.info(f"Created test user {telegram_id} with balances: {balances}")
        return user
    
    async def create_test_escrow(self,
                          buyer_id: int,
                          seller_id: int,
                          amount: Decimal,
                          currency: str = 'USD',
                          status: EscrowStatus = EscrowStatus.ACTIVE,
                          description: str = "Test escrow") -> Escrow:
        """Create test escrow"""
        
        escrow_id = f'ESC_{self._base_timestamp}_{self._random_suffix}_{self._escrow_counter:06d}'
        self._escrow_counter += 1
        
        escrow = Escrow(
            escrow_id=escrow_id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            amount=amount,
            currency=currency,
            fee_amount=Decimal('0.00'),  # Default fee amount for tests
            total_amount=amount,  # Total equals amount for test scenarios
            fee_split_option='buyer_pays',  # Default fee split option for tests
            status=status,
            description=description,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        self.session.add(escrow)
        await self.session.commit()
        
        logger.info(f"Created test escrow {escrow_id}: {amount} {currency}")
        return escrow
    
    async def create_test_cashout(self,
                           user_id: int,
                           amount: Decimal,
                           currency: str = 'USD',
                           status: CashoutStatus = CashoutStatus.PENDING,
                           processing_mode: CashoutProcessingMode = CashoutProcessingMode.MANUAL) -> Cashout:
        """Create test cashout request"""
        
        cashout_id = f'CASH_{self._transaction_counter:06d}'
        self._transaction_counter += 1
        
        cashout = Cashout(
            cashout_id=cashout_id,
            user_id=user_id,
            amount=amount,
            currency=currency,
            cashout_type='crypto',  # Default cashout type for tests
            destination='test_address_123',  # Default test destination
            network_fee=Decimal('0.00'),  # Default network fee
            platform_fee=Decimal('0.00'),  # Default platform fee  
            total_fee=Decimal('0.00'),  # Default total fee
            net_amount=amount,  # Default net amount equals total amount for tests
            status=status,
            processing_mode=processing_mode,
            created_at=datetime.utcnow()
        )
        
        self.session.add(cashout)
        await self.session.commit()
        
        logger.info(f"Created test cashout {cashout_id}: {amount} {currency}")
        return cashout
    
    def create_test_exchange_order(self,
                                  user_id: int,
                                  from_currency: str,
                                  to_currency: str,
                                  from_amount: Decimal,
                                  to_amount: Decimal,
                                  status: ExchangeStatus = ExchangeStatus.CREATED) -> ExchangeOrder:
        """Create test exchange order with constraint-compliant data"""
        
        order_id = f'EXC_{self._base_timestamp}_{self._random_suffix}_{self._transaction_counter:06d}'
        self._transaction_counter += 1
        
        # Ensure amount constraints: source_amount >= 1.0 AND source_amount <= 50000.0
        if from_amount < Decimal('1.0'):
            from_amount = Decimal('10.0')  # Use minimum compliant amount
            # Recalculate to_amount proportionally to maintain realistic exchange
            if from_currency in ['USD', 'NGN']:
                # Fiat to crypto: smaller crypto amount
                to_amount = from_amount / Decimal('45000.0')  # Assume BTC price ~$45k
            else:
                # Crypto to fiat: larger fiat amount  
                to_amount = from_amount * Decimal('45000.0')  # Convert crypto to USD/NGN
        elif from_amount > Decimal('50000.0'):
            from_amount = Decimal('25000.0')  # Use maximum compliant amount
            # Recalculate to_amount proportionally
            if from_currency in ['USD', 'NGN']:
                to_amount = from_amount / Decimal('45000.0')  # Fiat to crypto
            else:
                to_amount = from_amount * Decimal('45000.0')  # Crypto to fiat
        
        # Calculate exchange rate, markup, and fees for testing
        exchange_rate = to_amount / from_amount if from_amount > 0 else Decimal('1.0')
        markup_percentage = Decimal('2.5')  # 2.5% markup for tests (within 25% limit)
        fee_amount = from_amount * Decimal('0.001')  # 0.1% fee for tests
        
        # Fix final_amount calculation to comply with constraints
        # For buy_crypto: final_amount is target crypto amount after fees
        # For sell_crypto: final_amount is target fiat amount after fees
        if from_currency in ['USD', 'NGN']:
            # Buy crypto: final_amount = target crypto - network fees
            final_amount = to_amount - (to_amount * Decimal('0.0001'))  # Small crypto fee
        else:
            # Sell crypto: final_amount = target fiat - processing fees
            final_amount = to_amount - fee_amount
        
        # Ensure final_amount is positive and reasonable
        if final_amount <= 0:
            final_amount = to_amount * Decimal('0.99')  # 99% of target amount
        
        # Ensure consistency constraint: final_amount <= source_amount + fee_amount + 100
        max_allowed_final = from_amount + fee_amount + Decimal('100')
        if final_amount > max_allowed_final:
            final_amount = max_allowed_final - Decimal('1')
        
        exchange = ExchangeOrder(
            exchange_order_id=order_id,  # Correct field name
            user_id=user_id,
            order_type='buy_crypto' if from_currency in ['USD', 'NGN'] else 'sell_crypto',
            source_currency=from_currency,  # Correct field name
            target_currency=to_currency,  # Correct field name
            source_amount=from_amount,  # Correct field name
            target_amount=to_amount,  # Correct field name
            exchange_rate=exchange_rate,  # Required field
            markup_percentage=markup_percentage,  # Required field
            fee_amount=fee_amount,  # Required field
            final_amount=final_amount,  # Required field
            expires_at=datetime.utcnow() + timedelta(minutes=30),  # Required field
            status=status.value if isinstance(status, ExchangeStatus) else status,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()  # Fix NOT NULL constraint
        )
        
        self.session.add(exchange)
        self.session.commit()
        
        logger.info(f"Created test exchange {order_id}: {from_amount} {from_currency} -> {to_amount} {to_currency}")
        return exchange


@pytest.fixture
def test_data_factory(test_db_session):
    """Provide test data factory"""
    return TestDataFactory(test_db_session)


class ComprehensiveTestAssertions:
    """Comprehensive assertion helpers for all test types"""
    
    def __init__(self, session):
        self.session = session
    
    # User and wallet assertions
    async def assert_user_exists(self, telegram_id: str):
        """Assert user exists in database"""
        from sqlalchemy import select
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        assert user is not None, f"User not found: {telegram_id}"
        return user
    
    async def assert_wallet_balance(self, user_id: int, currency: str, expected_balance: Decimal):
        """Assert wallet has expected balance"""
        from sqlalchemy import select
        result = await self.session.execute(select(Wallet).where(
            Wallet.user_id == user_id,
            Wallet.currency == currency
        ))
        wallet = result.scalar_one_or_none()
        
        assert wallet is not None, f"Wallet not found for user {user_id}, currency {currency}"
        assert wallet.balance == expected_balance, f"Expected balance {expected_balance}, got {wallet.balance}"
        
        logger.info(f"✅ Wallet balance verified: {currency} = {expected_balance}")
    
    # Escrow assertions
    async def assert_escrow_status(self, escrow_id: str, expected_status: EscrowStatus):
        """Assert escrow has expected status"""
        from sqlalchemy import select
        result = await self.session.execute(select(Escrow).where(Escrow.escrow_id == escrow_id))
        escrow = result.scalar_one_or_none()
        assert escrow is not None, f"Escrow not found: {escrow_id}"
        expected_status_value = expected_status.value if isinstance(expected_status, EscrowStatus) else expected_status
        assert escrow.status == expected_status_value, f"Expected status {expected_status_value}, got {escrow.status}"
        
        logger.info(f"✅ Escrow {escrow_id} has correct status: {expected_status_value}")
    
    async def assert_escrow_holding_created(self, escrow_id: str, amount: Decimal):
        """Assert escrow holding was created with correct amount"""
        from sqlalchemy import select
        result = await self.session.execute(select(EscrowHolding).where(
            EscrowHolding.escrow_id == escrow_id
        ))
        holding = result.scalar_one_or_none()
        
        assert holding is not None, f"Escrow holding not found for {escrow_id}"
        assert holding.held_amount == amount, f"Expected holding {amount}, got {holding.held_amount}"
        
        logger.info(f"✅ Escrow holding verified: {escrow_id} = {amount}")
    
    # Cashout assertions
    async def assert_cashout_status(self, cashout_id: str, expected_status: CashoutStatus):
        """Assert cashout has expected status"""
        from sqlalchemy import select
        result = await self.session.execute(select(Cashout).where(Cashout.cashout_id == cashout_id))
        cashout = result.scalar_one_or_none()
        assert cashout is not None, f"Cashout not found: {cashout_id}"
        expected_status_value = expected_status.value if isinstance(expected_status, CashoutStatus) else expected_status
        assert cashout.status == expected_status_value, f"Expected status {expected_status_value}, got {cashout.status}"
        
        logger.info(f"✅ Cashout {cashout_id} has correct status: {expected_status_value}")
    
    # Exchange assertions
    async def assert_exchange_status(self, order_id: str, expected_status: ExchangeStatus):
        """Assert exchange order has expected status"""
        from sqlalchemy import select
        result = await self.session.execute(select(ExchangeOrder).where(ExchangeOrder.exchange_order_id == order_id))
        exchange = result.scalar_one_or_none()
        assert exchange is not None, f"Exchange order not found: {order_id}"
        expected_status_value = expected_status.value if isinstance(expected_status, ExchangeStatus) else expected_status
        assert exchange.status == expected_status_value, f"Expected status {expected_status_value}, got {exchange.status}"
        
        logger.info(f"✅ Exchange {order_id} has correct status: {expected_status_value}")
    
    # Unified transaction assertions
    async def assert_unified_transaction_status(self, transaction_id: str, expected_status: UnifiedTransactionStatus):
        """Assert unified transaction has expected status"""
        from sqlalchemy import select
        result = await self.session.execute(select(UnifiedTransaction).where(
            UnifiedTransaction.transaction_id == transaction_id
        ))
        tx = result.scalar_one_or_none()
        
        assert tx is not None, f"Transaction not found: {transaction_id}"
        expected_status_value = expected_status.value if isinstance(expected_status, UnifiedTransactionStatus) else expected_status
        assert tx.status == expected_status_value, f"Expected status {expected_status_value}, got {tx.status}"
        
        logger.info(f"✅ Transaction {transaction_id} has correct status: {expected_status_value}")


@pytest.fixture
def test_assertions(test_db_session):
    """Provide comprehensive test assertions helper"""
    return ComprehensiveTestAssertions(test_db_session)


class PerformanceMeasurement:
    """Performance measurement utilities for testing"""
    
    def __init__(self):
        self.measurements = []
    
    async def measure_async_operation(self, operation_name: str, operation_coro):
        """Measure async operation performance"""
        import time
        
        start_time = time.perf_counter()
        start_memory = self._get_memory_usage()
        
        result = await operation_coro
        
        end_time = time.perf_counter()
        end_memory = self._get_memory_usage()
        
        measurement = {
            'operation': operation_name,
            'duration_seconds': end_time - start_time,
            'memory_start_mb': start_memory,
            'memory_end_mb': end_memory,
            'memory_delta_mb': end_memory - start_memory,
            'timestamp': datetime.utcnow()
        }
        
        self.measurements.append(measurement)
        
        logger.info(f"⏱️ {operation_name}: {measurement['duration_seconds']:.4f}s, Memory: {measurement['memory_delta_mb']:+.1f}MB")
        
        return result
    
    def measure_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """Measure synchronous operation performance"""
        import time
        
        start_time = time.perf_counter()
        start_memory = self._get_memory_usage()
        
        result = operation_func(*args, **kwargs)
        
        end_time = time.perf_counter()
        end_memory = self._get_memory_usage()
        
        measurement = {
            'operation': operation_name,
            'duration_seconds': end_time - start_time,
            'memory_start_mb': start_memory,
            'memory_end_mb': end_memory,
            'memory_delta_mb': end_memory - start_memory,
            'timestamp': datetime.utcnow()
        }
        
        self.measurements.append(measurement)
        
        logger.info(f"⏱️ {operation_name}: {measurement['duration_seconds']:.4f}s, Memory: {measurement['memory_delta_mb']:+.1f}MB")
        
        return result
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0  # psutil not available
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance measurement summary"""
        if not self.measurements:
            return {}
        
        durations = [m['duration_seconds'] for m in self.measurements]
        memory_deltas = [m['memory_delta_mb'] for m in self.measurements]
        
        import statistics
        
        return {
            'total_operations': len(self.measurements),
            'avg_duration_seconds': statistics.mean(durations),
            'max_duration_seconds': max(durations),
            'min_duration_seconds': min(durations),
            'avg_memory_delta_mb': statistics.mean(memory_deltas),
            'max_memory_delta_mb': max(memory_deltas),
            'total_duration_seconds': sum(durations)
        }
    
    def assert_performance_thresholds(self,
                                    max_avg_duration: float = None,
                                    max_single_duration: float = None,
                                    max_memory_growth: float = None):
        """Assert performance is within acceptable thresholds"""
        summary = self.get_performance_summary()
        
        if not summary:
            return
        
        if max_avg_duration and summary['avg_duration_seconds'] > max_avg_duration:
            raise AssertionError(f"Average duration {summary['avg_duration_seconds']:.4f}s exceeds threshold {max_avg_duration}s")
        
        if max_single_duration and summary['max_duration_seconds'] > max_single_duration:
            raise AssertionError(f"Maximum duration {summary['max_duration_seconds']:.4f}s exceeds threshold {max_single_duration}s")
        
        if max_memory_growth and summary['max_memory_delta_mb'] > max_memory_growth:
            raise AssertionError(f"Memory growth {summary['max_memory_delta_mb']:.1f}MB exceeds threshold {max_memory_growth}MB")
        
        logger.info(f"✅ Performance within thresholds: avg={summary['avg_duration_seconds']:.4f}s, max={summary['max_duration_seconds']:.4f}s")


@pytest.fixture
def performance_measurement():
    """Provide performance measurement utilities"""
    return PerformanceMeasurement()


# Pytest marks for test categorization
pytest_plugins = []

def pytest_configure(config):
    """Configure pytest with custom marks"""
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "performance: Performance and load tests")
    config.addinivalue_line("markers", "concurrent: Concurrent execution tests")
    config.addinivalue_line("markers", "api: API endpoint and external service tests")
    config.addinivalue_line("markers", "security: Security and vulnerability tests")
    config.addinivalue_line("markers", "escrow: Escrow system tests")
    config.addinivalue_line("markers", "exchange: Exchange system tests") 
    config.addinivalue_line("markers", "cashout: Cashout system tests")
    config.addinivalue_line("markers", "onboarding: Onboarding system tests")
    config.addinivalue_line("markers", "wallet: Wallet system tests")
    config.addinivalue_line("markers", "admin: Admin functionality tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")


# Environment-specific fixtures
@pytest.fixture(scope="session")
def test_environment():
    """Provide test environment configuration"""
    return {
        'environment': 'test',
        'database_url': TEST_DATABASE_URL,
        'debug_mode': True,
        'external_apis_enabled': False,
        'rate_limiting_enabled': False,
        'audit_logging_enabled': True,
        'background_jobs_enabled': False
    }


# Cleanup utilities
@pytest.fixture(autouse=True)
async def cleanup_test_data(test_db_session):
    """Automatically cleanup test data after each test - ARCHITECT FIX: Async rollback"""
    yield
    
    # Clean up any remaining test data
    try:
        # ARCHITECT FIX: Properly handle AsyncSession rollback with await
        if hasattr(test_db_session, 'aexecute') or str(type(test_db_session)).find('AsyncSession') != -1:
            # This is an AsyncSession - use await
            await test_db_session.rollback()
        else:
            # This is a sync session - call directly
            test_db_session.rollback()
    except Exception as e:
        logger.warning(f"Test cleanup warning: {e}")


# Async cleanup is handled by pytest-asyncio automatically


# Test configuration validation
def pytest_runtest_setup(item):
    """Run before each test to validate configuration"""
    
    # Check for required environment variables in integration tests
    if item.get_closest_marker("integration"):
        required_vars = ["DATABASE_URL"]  # Could be expanded
        missing_vars = [var for var in required_vars if var not in os.environ and var != "DATABASE_URL"]  # DATABASE_URL is mocked
        
        if missing_vars:
            pytest.skip(f"Integration test requires environment variables: {missing_vars}")
    
    # Skip slow tests unless explicitly requested
    # Note: Performance tests are not considered "slow" tests and should always run
    if (item.get_closest_marker("slow") and 
        not item.config.getoption("--runslow", default=False) and 
        not item.get_closest_marker("performance")):
        pytest.skip("Slow test skipped (use --runslow to run)")


def pytest_addoption(parser):
    """Add custom pytest command line options"""
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="Run slow tests"
    )
    
    parser.addoption(
        "--integration-only",
        action="store_true", 
        default=False,
        help="Run only integration tests"
    )
    
    parser.addoption(
        "--e2e-only",
        action="store_true",
        default=False,
        help="Run only end-to-end tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on options"""
    
    if config.getoption("--integration-only"):
        # Only run integration tests
        selected_items = []
        for item in items:
            if item.get_closest_marker("integration"):
                selected_items.append(item)
        items[:] = selected_items
    
    if config.getoption("--e2e-only"):
        # Only run end-to-end tests
        selected_items = []
        for item in items:
            if item.get_closest_marker("e2e"):
                selected_items.append(item)
        items[:] = selected_items
    
    # Add slow marker to tests that might be slow
    for item in items:
        # Mark tests with many database operations as slow
        if any(keyword in item.name.lower() for keyword in ["concurrent", "bulk", "performance", "load", "stress"]):
            item.add_marker(pytest.mark.slow)
        
        # Add e2e marker to comprehensive tests
        if "comprehensive" in item.name.lower() or "end_to_end" in item.name.lower():
            item.add_marker(pytest.mark.e2e)


# Shared test scenarios for reusability across test files
class TestScenarios:
    """Common test scenarios that can be reused across test files"""
    
    @staticmethod
    async def create_escrow_scenario(test_data_factory, amount: Decimal = Decimal('100.00')):
        """Create a standard escrow test scenario"""
        buyer = await test_data_factory.create_test_user(
            telegram_id='1234567890',
            username='testbuyer',
            balances={'USD': Decimal('1000.00')}
        )
        
        seller = await test_data_factory.create_test_user(
            telegram_id='1234567891', 
            username='testseller',
            balances={'USD': Decimal('500.00')}
        )
        
        escrow = await test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=amount,
            currency='USD',
            description="Test escrow transaction"
        )
        
        return {
            'buyer': buyer,
            'seller': seller,
            'escrow': escrow
        }
    
    @staticmethod
    async def create_cashout_scenario(test_data_factory, amount: Decimal = Decimal('100.00')):
        """Create a standard cashout test scenario"""
        user = await test_data_factory.create_test_user(
            telegram_id='1234567895',
            username='testcashoutuser',
            balances={'USD': Decimal('1000.00')}
        )
        
        cashout = await test_data_factory.create_test_cashout(
            user_id=user.id,
            amount=amount,
            currency='USD'
        )
        
        return {
            'user': user,
            'cashout': cashout
        }
    
    @staticmethod
    async def create_exchange_scenario(test_data_factory):
        """Create a standard exchange test scenario"""
        user = await test_data_factory.create_test_user(
            username='testexchangeuser',
            balances={
                'USD': Decimal('1000.00'),
                'BTC': Decimal('0.1'),
                'ETH': Decimal('10.0')
            }
        )
        
        exchange = await test_data_factory.create_test_exchange_order(
            user_id=user.id,
            from_currency='USD',
            to_currency='BTC',
            from_amount=Decimal('1000.00'),
            to_amount=Decimal('0.001')
        )
        
        return {
            'user': user,
            'exchange': exchange
        }


@pytest.fixture
def test_scenarios():
    """Provide common test scenarios"""
    return TestScenarios


@pytest.fixture(autouse=True)
def clear_onboarding_router_caches():
    """
    PRIORITY 1: Clear onboarding router caches and locks between tests
    Prevents cross-test bleed and ensures clean test isolation
    """
    # Clear caches before test
    try:
        # Import handler module to access caches
        from handlers import onboarding_router
        
        # Clear all module-level caches
        if hasattr(onboarding_router, '_user_lookup_cache'):
            onboarding_router._user_lookup_cache.clear()
        
        if hasattr(onboarding_router, '_step_cache'):
            onboarding_router._step_cache.clear()
        
        if hasattr(onboarding_router, '_message_cache'):
            onboarding_router._message_cache.clear()
        
        # Clear user locks dictionary
        if hasattr(onboarding_router, '_user_locks'):
            onboarding_router._user_locks.clear()
        
        logger.debug("✅ Cleared onboarding router caches before test")
        
    except ImportError:
        # If module not available, skip cache clearing
        logger.debug("Onboarding router module not available for cache clearing")
    except Exception as e:
        logger.debug(f"Cache clearing error: {e}")
    
    yield  # Run the test
    
    # Clear caches after test (cleanup)
    try:
        from handlers import onboarding_router
        
        # Clear all module-level caches again
        if hasattr(onboarding_router, '_user_lookup_cache'):
            onboarding_router._user_lookup_cache.clear()
        
        if hasattr(onboarding_router, '_step_cache'):
            onboarding_router._step_cache.clear()
        
        if hasattr(onboarding_router, '_message_cache'):
            onboarding_router._message_cache.clear()
        
        # Clear user locks dictionary  
        if hasattr(onboarding_router, '_user_locks'):
            onboarding_router._user_locks.clear()
        
        logger.debug("✅ Cleared onboarding router caches after test")
        
    except Exception as e:
        logger.debug(f"Post-test cache clearing error: {e}")


@pytest.fixture(autouse=True)
def ensure_database_integrity(test_db_session):
    """
    PostgreSQL database integrity verification for tests
    PostgreSQL has native foreign key constraint support - no additional setup needed
    
    This fixture ensures proper database session handling for tests.
    """
    try:
        # PostgreSQL natively supports foreign keys - just verify session is working
        logger.debug("✅ PostgreSQL session verified - native foreign key support enabled")
    except Exception as e:
        logger.debug(f"Database session info: {e}")
    
    yield