"""
Idempotency protection for payment operations
Prevents duplicate processing from retries, webhooks, user double-clicks
"""

import logging
from typing import Callable
from functools import wraps
from datetime import datetime, timedelta
from database import SessionLocal

logger = logging.getLogger(__name__)


def idempotent_operation(key: str, scope: str = "default", ttl_hours: int = 24):
    """
    Decorator to make operations idempotent

    Args:
        key: Unique identifier for the operation
        scope: Operation category (payment, webhook, etc.)
        ttl_hours: How long to cache results
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            session = SessionLocal()
            try:
                # Import here to avoid circular imports
                from models import IdempotencyKey
                
                # Check if operation already exists
                existing = (
                    session.query(IdempotencyKey)
                    .filter(
                        IdempotencyKey.idempotency_key == key,
                        IdempotencyKey.scope == scope,
                    )
                    .first()
                )

                if existing:
                    if existing.is_expired(ttl_hours):
                        # Expired - delete and continue
                        session.delete(existing)
                        session.commit()
                    elif existing.status == "completed":
                        # Already completed - return success
                        logger.info(f"Idempotent operation {key} already completed")
                        return {
                            "success": True,
                            "idempotent": True,
                            "message": "Operation already completed",
                        }
                    elif existing.status == "in_progress":
                        # In progress - check staleness
                        if existing.created_at < datetime.utcnow() - timedelta(
                            minutes=10
                        ):
                            # Stale - allow retry
                            session.delete(existing)
                            session.commit()
                        else:
                            # Recent - reject duplicate
                            logger.warning(f"Duplicate operation attempted: {key}")
                            return {
                                "success": False,
                                "error": "Operation already in progress",
                            }

                # Import here to avoid circular imports
                from models import IdempotencyKey
                
                # Create new idempotency record
                idem_key = IdempotencyKey(
                    idempotency_key=key, scope=scope, status="in_progress"
                )
                session.add(idem_key)
                session.commit()

                try:
                    # Execute the operation
                    result = await func(*args, **kwargs)

                    # Mark as completed
                    idem_key.status = "completed"
                    idem_key.completed_at = datetime.utcnow()
                    if isinstance(result, dict):
                        idem_key.result_hash = str(hash(str(result)))
                    session.commit()

                    logger.info(f"Idempotent operation {key} completed successfully")
                    return result

                except Exception as e:
                    # Mark as failed
                    idem_key.status = "failed"
                    idem_key.completed_at = datetime.utcnow()
                    session.commit()
                    raise e

            except Exception as e:
                session.rollback()
                logger.error(f"Error in idempotent operation {key}: {e}")
                raise e
            finally:
                session.close()

        return wrapper

    return decorator


def generate_payment_key(
    user_id: int, amount: float, currency: str, operation: str
) -> str:
    """Generate deterministic key for payment operations"""
    return f"payment_{operation}_{user_id}_{amount}_{currency}_{int(datetime.utcnow().timestamp() // 300)}"


def generate_webhook_key(provider: str, external_id: str, event_type: str) -> str:
    """Generate deterministic key for webhook operations"""
    return f"webhook_{provider}_{event_type}_{external_id}"


def generate_escrow_key(escrow_id: str, operation: str, stage: str = None) -> str:
    """Generate deterministic key for escrow operations"""
    stage_suffix = f"_{stage}" if stage else ""
    return f"escrow_{operation}_{escrow_id}{stage_suffix}"


async def cleanup_expired_keys(hours_old: int = 24):
    """Cleanup expired idempotency keys (background job)"""
    from models import IdempotencyKey
    
    session = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours_old)
        deleted = (
            session.query(IdempotencyKey)
            .filter(IdempotencyKey.created_at < cutoff)
            .delete()
        )
        session.commit()
        logger.info(f"Cleaned up {deleted} expired idempotency keys")
        return deleted
    except Exception as e:
        session.rollback()
        logger.error(f"Error cleaning up idempotency keys: {e}")
        return 0
    finally:
        session.close()
