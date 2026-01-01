"""
Enhanced idempotency service for preventing duplicate transactions and operations.
Provides comprehensive deduplication across financial operations, user actions, and API calls.
"""

import logging
import hashlib
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from contextlib import contextmanager
from utils.atomic_transactions import atomic_transaction
from utils.callback_utils import safe_answer_callback_query
from models import Transaction

logger = logging.getLogger(__name__)


class IdempotencyService:
    """
    Comprehensive idempotency service for preventing duplicate operations.
    Supports multiple idempotency types: user actions, financial operations, and API calls.
    """

    # Cache for recent operations (in-memory cache for performance)
    _operation_cache: Dict[str, datetime] = {}
    _cache_cleanup_interval = 3600  # 1 hour
    _last_cleanup = datetime.utcnow()

    @classmethod
    def _cleanup_cache(cls):
        """Clean up expired cache entries"""
        now = datetime.utcnow()
        if (now - cls._last_cleanup).total_seconds() > cls._cache_cleanup_interval:
            cutoff = now - timedelta(hours=2)
            cls._operation_cache = {
                k: v for k, v in cls._operation_cache.items() if v > cutoff
            }
            cls._last_cleanup = now

    @classmethod
    def generate_operation_key(
        cls,
        user_id: int,
        operation_type: str,
        operation_data: Dict[str, Any],
        context: Optional[str] = None,
    ) -> str:
        """
        Generate unique operation key for idempotency checking.

        Args:
            user_id: User performing the operation
            operation_type: Type of operation (wallet_credit, wallet_debit, escrow_payment, etc.)
            operation_data: Operation-specific data (amount, currency, escrow_id, etc.)
            context: Additional context (e.g., "button_click", "api_call")

        Returns:
            Unique idempotency key
        """
        key_data = {
            "user_id": user_id,
            "operation_type": operation_type,
            "context": context,
            **operation_data,
        }

        # Create deterministic hash of the operation data
        key_string = json.dumps(key_data, sort_keys=True)
        operation_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]

        return f"{operation_type}_{user_id}_{operation_hash}"

    @classmethod
    def generate_financial_operation_key(
        cls,
        user_id: int,
        operation_type: str,
        amount: float,
        currency: str = "USD",
        escrow_id: Optional[int] = None,
        reference: Optional[str] = None,
    ) -> str:
        """
        Generate idempotency key specifically for financial operations.

        Args:
            user_id: User ID
            operation_type: Financial operation type (credit, debit, cashout, etc.)
            amount: Amount involved
            currency: Currency
            escrow_id: Associated escrow ID if applicable
            reference: External reference (tx_hash, payment_id, etc.)

        Returns:
            Financial operation idempotency key
        """
        operation_data = {
            "amount": f"{amount:.8f}",  # Fixed precision for consistent hashing
            "currency": currency,
            "escrow_id": escrow_id,
            "reference": reference,
        }

        return cls.generate_operation_key(
            user_id, f"financial_{operation_type}", operation_data
        )

    @classmethod
    def generate_user_action_key(
        cls,
        user_id: int,
        action_type: str,
        callback_data: Optional[str] = None,
        message_data: Optional[Dict] = None,
    ) -> str:
        """
        Generate idempotency key for user interface actions.

        Args:
            user_id: User ID
            action_type: Type of action (button_click, form_submit, etc.)
            callback_data: Telegram callback data
            message_data: Additional message context

        Returns:
            User action idempotency key
        """
        operation_data = {
            "callback_data": callback_data,
            "message_data": message_data or {},
        }

        return cls.generate_operation_key(
            user_id, f"action_{action_type}", operation_data, "user_interface"
        )

    @classmethod
    def is_duplicate_operation(
        cls, idempotency_key: str, window_seconds: int = 60
    ) -> bool:
        """
        Check if operation with given key was recently processed.

        Args:
            idempotency_key: Unique operation key
            window_seconds: Time window to check for duplicates

        Returns:
            True if operation is duplicate, False otherwise
        """
        cls._cleanup_cache()

        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)

        # Check in-memory cache first (fastest)
        if idempotency_key in cls._operation_cache:
            last_operation = cls._operation_cache[idempotency_key]
            if last_operation > cutoff:
                logger.info(f"Duplicate operation detected (cache): {idempotency_key}")
                return True

        # Check database for persistence across restarts
        try:
            with atomic_transaction() as session:
                # Check if operation exists in recent transaction records

                # For financial operations, check transaction table
                if "financial_" in idempotency_key:
                    recent_transaction = (
                        session.query(Transaction)
                        .filter(
                            Transaction.tx_hash == idempotency_key,
                            Transaction.created_at >= cutoff,
                        )
                        .first()
                    )

                    if recent_transaction:
                        logger.info(
                            f"Duplicate financial operation detected (database): {idempotency_key}"
                        )
                        # Update cache for performance - safely extract datetime
                        created_at_value = getattr(
                            recent_transaction, "created_at", None
                        )
                        if created_at_value is not None:
                            cls._operation_cache[idempotency_key] = created_at_value
                        else:
                            cls._operation_cache[idempotency_key] = datetime.utcnow()
                        return True

                # For other operations, we could add a dedicated idempotency table
                # For now, use in-memory cache as primary protection

        except Exception as e:
            logger.error(f"Error checking database for duplicate operation: {e}")
            # Fail safe - if we can't check database, allow operation but log warning
            logger.warning(
                f"Cannot verify idempotency for {idempotency_key}, allowing operation"
            )

        return False

    @classmethod
    def register_operation(cls, idempotency_key: str) -> None:
        """
        Register that an operation with given key has been processed.

        Args:
            idempotency_key: Unique operation key
        """
        cls._operation_cache[idempotency_key] = datetime.utcnow()
        logger.debug(f"Registered operation: {idempotency_key}")

    @classmethod
    @contextmanager
    def idempotent_operation(cls, idempotency_key: str, window_seconds: int = 60):
        """
        Context manager for idempotent operations.

        Usage:
            with IdempotencyService.idempotent_operation("user_123_wallet_credit") as is_duplicate:
                if is_duplicate:
                    logger.info("Operation already processed")
                    return existing_result

                # Perform the operation
                result = perform_operation()
                return result

        Args:
            idempotency_key: Unique operation key
            window_seconds: Duplicate detection window

        Yields:
            Boolean indicating if operation is duplicate
        """
        is_duplicate = cls.is_duplicate_operation(idempotency_key, window_seconds)

        try:
            yield is_duplicate

            # Only register if operation was successful (no exception)
            if not is_duplicate:
                cls.register_operation(idempotency_key)

        except Exception as e:
            # Don't register failed operations
            logger.error(
                f"Operation failed, not registering idempotency key {idempotency_key}: {e}"
            )
            raise

    @classmethod
    def create_api_call_key(
        cls, api_provider: str, endpoint: str, parameters: Dict[str, Any]
    ) -> str:
        """
        Create idempotency key for external API calls.

        Args:
            api_provider: API provider name (binance, fincra, etc.)
            endpoint: API endpoint
            parameters: API call parameters

        Returns:
            API call idempotency key
        """
        key_data = {
            "provider": api_provider,
            "endpoint": endpoint,
            "parameters": parameters,
        }

        key_string = json.dumps(key_data, sort_keys=True)
        api_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]

        return f"api_{api_provider}_{api_hash}"

    @classmethod
    def prevent_rapid_clicks(
        cls, user_id: int, callback_data: str, cooldown_seconds: int = 3
    ) -> bool:
        """
        Prevent rapid button clicks that could trigger duplicate operations.

        Args:
            user_id: User ID
            callback_data: Telegram callback data
            cooldown_seconds: Minimum time between clicks

        Returns:
            True if click should be blocked (too rapid), False if allowed
        """
        click_key = cls.generate_user_action_key(user_id, "button_click", callback_data)

        return cls.is_duplicate_operation(click_key, cooldown_seconds)


class FinancialIdempotency:
    """
    Specialized idempotency service for financial operations.
    Provides enhanced protection for critical financial transactions.
    """

    @classmethod
    def create_wallet_operation_key(
        cls,
        user_id: int,
        operation_type: str,
        amount: float,
        currency: str = "USD",
        escrow_id: Optional[int] = None,
    ) -> str:
        """Create idempotency key for wallet operations"""
        return IdempotencyService.generate_financial_operation_key(
            user_id, f"wallet_{operation_type}", amount, currency, escrow_id
        )

    @classmethod
    def create_cashout_key(
        cls, user_id: int, amount: float, destination: str, currency: str = "USD"
    ) -> str:
        """Create idempotency key for cashout operations"""
        operation_data = {
            "amount": f"{amount:.8f}",
            "currency": currency,
            "destination_hash": hashlib.sha256(destination.encode()).hexdigest()[:8],
        }

        return IdempotencyService.generate_operation_key(
            user_id, "cashout", operation_data, "financial"
        )

    @classmethod
    def create_deposit_processing_key(cls, tx_hash: str, escrow_id: str) -> str:
        """Create idempotency key for deposit processing"""
        key_data = {"tx_hash": tx_hash, "escrow_id": escrow_id}

        key_string = json.dumps(key_data, sort_keys=True)
        deposit_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]

        return f"deposit_processing_{deposit_hash}"

    @classmethod
    @contextmanager
    def protected_wallet_operation(
        cls,
        user_id: int,
        operation_type: str,
        amount: float,
        currency: str = "USD",
        escrow_id: Optional[int] = None,
    ):
        """Context manager for protected wallet operations"""
        idempotency_key = cls.create_wallet_operation_key(
            user_id, operation_type, amount, currency, escrow_id
        )

        with IdempotencyService.idempotent_operation(
            idempotency_key, window_seconds=300
        ) as is_duplicate:
            yield is_duplicate, idempotency_key


# Convenience decorators for common patterns
def idempotent_financial_operation(operation_type: str, window_seconds: int = 300):
    """
    Decorator for financial operations requiring idempotency protection.

    Usage:
        @idempotent_financial_operation("wallet_credit")
        def credit_wallet(user_id, amount, currency='USD', **kwargs):
            # Operation implementation
            pass
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract parameters for idempotency key
            user_id = kwargs.get("user_id") or (args[0] if args else None)
            amount = kwargs.get("amount") or (args[1] if len(args) > 1 else None)
            currency = kwargs.get("currency", "USD")
            escrow_id = kwargs.get("escrow_id")

            if not all([user_id is not None, amount is not None]):
                # If we can't create idempotency key, log warning and proceed
                logger.warning(f"Cannot create idempotency key for {func.__name__}")
                return func(*args, **kwargs)

            # Type assertions for proper typing with safe conversion
            try:
                user_id = int(user_id) if user_id is not None else 0
                amount = float(amount) if amount is not None else 0.0
            except (ValueError, TypeError) as e:
                logger.warning(f"Type conversion error for {func.__name__}: {e}")
                return func(*args, **kwargs)

            idempotency_key = IdempotencyService.generate_financial_operation_key(
                user_id, operation_type, amount, currency, escrow_id
            )

            with IdempotencyService.idempotent_operation(
                idempotency_key, window_seconds
            ) as is_duplicate:
                if is_duplicate:
                    logger.info(
                        f"Skipping duplicate {operation_type} operation for user {user_id}"
                    )
                    return True  # Return success for duplicate operations

                return func(*args, **kwargs)

        return wrapper

    return decorator


def prevent_rapid_actions(cooldown_seconds: int = 3):
    """
    Decorator to prevent rapid user actions (button clicks, form submissions).

    Usage:
        @prevent_rapid_actions(cooldown_seconds=5)
        async def handle_button_click(update, context):
            # Handler implementation
            pass
    """

    def decorator(func):
        async def wrapper(update, context, *args, **kwargs):
            if not update.effective_user:
                return await func(update, context, *args, **kwargs)

            user_id = update.effective_user.id
            callback_data = (
                getattr(update.callback_query, "data", "")
                if update.callback_query
                else ""
            )

            if IdempotencyService.prevent_rapid_clicks(
                user_id, callback_data, cooldown_seconds
            ):
                logger.info(f"Blocked rapid action for user {user_id}: {callback_data}")
                if update.callback_query:
                    await safe_answer_callback_query(
                        update.callback_query,
                        "⏳ Please wait...",
                        show_alert=False
                    )
                return

            return await func(update, context, *args, **kwargs)

        return wrapper

    return decorator
