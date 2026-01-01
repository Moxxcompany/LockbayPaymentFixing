"""
Batch Processing Service - Optimized background job processing
Implements batched processing instead of full set iteration for better performance
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Callable
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from models import User, Cashout, CashoutStatus, Wallet, Transaction
from database import SessionLocal

logger = logging.getLogger(__name__)


class BatchProcessingService:
    """Service for optimized batch processing of background jobs"""

    # Default batch configurations
    DEFAULT_BATCH_SIZE = 100
    DEFAULT_MAX_CONCURRENT = 10
    DEFAULT_TIMEOUT_SECONDS = 300

    @classmethod
    async def process_pending_cashouts_batched(
        cls,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    ) -> Dict[str, Any]:
        """
        Process pending cashouts in optimized batches instead of all at once
        Returns: {'processed': int, 'failed': int, 'batches': int, 'performance': dict}
        """
        start_time = datetime.utcnow()
        total_processed = 0
        total_failed = 0
        batch_count = 0

        try:
            # Get pending cashouts in batches
            async for batch in cls._get_pending_cashouts_batched(batch_size):
                if not batch:
                    break

                batch_count += 1
                logger.info(
                    f"Processing cashout batch {batch_count} with {len(batch)} items"
                )

                # Process batch concurrently
                semaphore = asyncio.Semaphore(max_concurrent)

                async def process_cashout_safe(cashout):
                    async with semaphore:
                        try:
                            # Import here to avoid circular dependency
                            from services.auto_cashout import (
                                AutoCashoutService,
                            )

                            result = (
                                await AutoCashoutService.create_cashout_request(
                                    cashout.user_id,
                                    cashout.amount,
                                    cashout.currency,
                                    cashout.cashout_type,
                                    cashout.destination,
                                )
                            )
                            return result["success"]
                        except Exception as e:
                            logger.error(
                                f"Error processing cashout {cashout.cashout_id}: {e}"
                            )
                            return False

                # Process batch
                tasks = [process_cashout_safe(w) for w in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Count results
                batch_processed = sum(1 for r in results if r is True)
                batch_failed = len(results) - batch_processed

                total_processed += batch_processed
                total_failed += batch_failed

                logger.info(
                    f"Batch {batch_count} completed: {batch_processed} processed, {batch_failed} failed"
                )

                # Small delay between batches to avoid overwhelming the system
                await asyncio.sleep(0.1)

            end_time = datetime.utcnow()
            duration_seconds = (end_time - start_time).total_seconds()

            logger.info(
                f"Batch processing completed: {total_processed} processed, {total_failed} failed in {batch_count} batches"
            )

            return {
                "processed": total_processed,
                "failed": total_failed,
                "batches": batch_count,
                "performance": {
                    "duration_seconds": duration_seconds,
                    "items_per_second": (
                        (total_processed + total_failed) / duration_seconds
                        if duration_seconds > 0
                        else 0
                    ),
                    "batch_size": batch_size,
                    "max_concurrent": max_concurrent,
                },
            }

        except Exception as e:
            logger.error(f"Error in batch processing pending cashouts: {e}")
            return {
                "processed": total_processed,
                "failed": total_failed,
                "error": str(e),
                "batches": batch_count,
            }

    @classmethod
    async def _get_pending_cashouts_batched(cls, batch_size: int):
        """Generator that yields batches of pending cashouts"""
        offset = 0

        while True:
            try:
                with SessionLocal() as session:
                    # Get batch of pending cashouts
                    cashouts = (
                        session.query(Cashout)
                        .filter(
                            Cashout.status.in_(
                                [
                                    CashoutStatus.PENDING.value,
                                    CashoutStatus.ADMIN_PENDING.value,
                                    CashoutStatus.OTP_PENDING.value,
                                ]
                            )
                        )
                        .order_by(Cashout.created_at)
                        .offset(offset)
                        .limit(batch_size)
                        .all()
                    )

                    if not cashouts:
                        break

                    yield cashouts
                    offset += batch_size

            except Exception as e:
                logger.error(f"Error getting cashout batch at offset {offset}: {e}")
                break

    @classmethod
    async def process_wallet_balance_checks_batched(
        cls, batch_size: int = DEFAULT_BATCH_SIZE
    ) -> Dict[str, Any]:
        """
        Process wallet balance integrity checks in batches
        Returns: {'checked': int, 'issues_found': int, 'fixes_applied': int}
        """
        start_time = datetime.utcnow()
        total_checked = 0
        total_issues = 0
        total_fixes = 0

        try:
            # Get wallets in batches
            offset = 0
            while True:
                with SessionLocal() as session:
                    wallets = (
                        session.query(Wallet)
                        .filter(Wallet.is_active)
                        .offset(offset)
                        .limit(batch_size)
                        .all()
                    )

                    if not wallets:
                        break

                    logger.info(
                        f"Checking batch of {len(wallets)} wallets starting at offset {offset}"
                    )

                    # Check each wallet in the batch
                    for wallet in wallets:
                        issues_found, fixes_applied = await cls._check_wallet_integrity(
                            wallet, session
                        )
                        total_issues += issues_found
                        total_fixes += fixes_applied

                    total_checked += len(wallets)
                    offset += batch_size

                    # Commit fixes for this batch
                    session.commit()

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            logger.info(
                f"Wallet batch processing completed: {total_checked} checked, {total_issues} issues, {total_fixes} fixes"
            )

            return {
                "checked": total_checked,
                "issues_found": total_issues,
                "fixes_applied": total_fixes,
                "performance": {
                    "duration_seconds": duration,
                    "wallets_per_second": (
                        total_checked / duration if duration > 0 else 0
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Error in batch wallet processing: {e}")
            return {
                "checked": total_checked,
                "issues_found": total_issues,
                "fixes_applied": total_fixes,
                "error": str(e),
            }

    @classmethod
    async def _check_wallet_integrity(
        cls, wallet: Wallet, session: Session
    ) -> tuple[int, int]:
        """
        Check individual wallet integrity and apply fixes
        Returns: (issues_found, fixes_applied)
        """
        issues_found = 0
        fixes_applied = 0

        try:
            # Use raw SQL query to get wallet values to avoid SQLAlchemy column issues
            wallet_data = session.execute(
                text(
                    "SELECT balance, frozen_balance, locked_balance FROM wallets WHERE id = :wallet_id"
                ),
                {"wallet_id": wallet.id},
            ).first()

            if not wallet_data:
                logger.warning(f"Wallet data not found for wallet {wallet.id}")
                return 0, 0

            balance_val = float(wallet_data[0] or 0)
            frozen_val = float(wallet_data[1] or 0)
            locked_val = float(wallet_data[2] or 0)

            # Check for negative balances
            if balance_val < 0:
                issues_found += 1
                logger.warning(f"Negative balance in wallet {wallet.id}: {balance_val}")

            if frozen_val < 0:
                issues_found += 1
                session.execute(
                    text("UPDATE wallets SET frozen_balance = 0 WHERE id = :wallet_id"),
                    {"wallet_id": wallet.id},
                )
                fixes_applied += 1
                logger.info(f"Fixed negative frozen balance in wallet {wallet.id}")

            if locked_val < 0:
                issues_found += 1
                session.execute(
                    text("UPDATE wallets SET locked_balance = 0 WHERE id = :wallet_id"),
                    {"wallet_id": wallet.id},
                )
                fixes_applied += 1
                logger.info(f"Fixed negative locked balance in wallet {wallet.id}")

            # Check if reserved funds exceed balance
            total_reserved = frozen_val + locked_val
            if total_reserved > balance_val:
                issues_found += 1
                logger.warning(
                    f"Reserved funds exceed balance in wallet {wallet.id}: {total_reserved} > {balance_val}"
                )

            return issues_found, fixes_applied

        except Exception as e:
            logger.error(f"Error checking wallet {wallet.id}: {e}")
            return 0, 0

    @classmethod
    async def process_user_statistics_batched(
        cls, batch_size: int = DEFAULT_BATCH_SIZE
    ) -> Dict[str, Any]:
        """
        Update user statistics in batches instead of all at once
        Returns: {'updated': int, 'batches': int, 'performance': dict}
        """
        start_time = datetime.utcnow()
        total_updated = 0
        batch_count = 0

        try:
            offset = 0
            while True:
                with SessionLocal() as session:
                    # Get batch of users
                    users = (
                        session.query(User)
                        .filter(User.status == "active")
                        .offset(offset)
                        .limit(batch_size)
                        .all()
                    )

                    if not users:
                        break

                    batch_count += 1
                    logger.info(
                        f"Updating statistics for batch {batch_count} with {len(users)} users"
                    )

                    # Update statistics for each user in batch
                    for user in users:
                        try:
                            # Calculate user statistics efficiently with single queries
                            total_trades = (
                                session.query(func.count(Transaction.id))
                                .filter(
                                    Transaction.user_id == user.id,
                                    Transaction.status == "completed",
                                )
                                .scalar()
                                or 0
                            )

                            (
                                session.query(func.sum(Transaction.amount))
                                .filter(
                                    Transaction.user_id == user.id,
                                    Transaction.status == "completed",
                                )
                                .scalar()
                                or 0
                            )

                            # Update user statistics using SQL
                            session.execute(
                                text(
                                    "UPDATE users SET total_trades = :trades WHERE id = :user_id"
                                ),
                                {"trades": total_trades, "user_id": user.id},
                            )

                        except Exception as e:
                            logger.error(
                                f"Error updating statistics for user {user.id}: {e}"
                            )
                            continue

                    # Commit batch
                    session.commit()
                    total_updated += len(users)
                    offset += batch_size

                    # Small delay between batches
                    await asyncio.sleep(0.05)

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            logger.info(
                f"User statistics batch processing completed: {total_updated} users updated in {batch_count} batches"
            )

            return {
                "updated": total_updated,
                "batches": batch_count,
                "performance": {
                    "duration_seconds": duration,
                    "users_per_second": total_updated / duration if duration > 0 else 0,
                    "batch_size": batch_size,
                },
            }

        except Exception as e:
            logger.error(f"Error in batch user statistics processing: {e}")
            return {"updated": total_updated, "batches": batch_count, "error": str(e)}

    @classmethod
    async def cleanup_old_records_batched(
        cls,
        table_name: str,
        date_column: str,
        retention_days: int,
        batch_size: int = 1000,
    ) -> Dict[str, Any]:
        """
        Clean up old records in batches to avoid long-running transactions
        Returns: {'deleted': int, 'batches': int, 'performance': dict}
        """
        start_time = datetime.utcnow()
        total_deleted = 0
        batch_count = 0

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            while True:
                with SessionLocal() as session:
                    # Use raw SQL for efficient batch deletion
                    delete_query = text(
                        f"""
                        DELETE FROM {table_name} 
                        WHERE {date_column} < :cutoff_date
                        AND id IN (
                            SELECT id FROM {table_name} 
                            WHERE {date_column} < :cutoff_date 
                            LIMIT :batch_size
                        )
                    """
                    )

                    result = session.execute(
                        delete_query,
                        {"cutoff_date": cutoff_date, "batch_size": batch_size},
                    )

                    deleted_count = getattr(result, "rowcount", 0)
                    session.commit()

                    if deleted_count == 0:
                        break

                    batch_count += 1
                    total_deleted += deleted_count

                    logger.info(
                        f"Batch {batch_count}: Deleted {deleted_count} old records from {table_name}"
                    )

                    # Small delay between batches
                    await asyncio.sleep(0.1)

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            logger.info(
                f"Cleanup completed: {total_deleted} records deleted from {table_name} in {batch_count} batches"
            )

            return {
                "deleted": total_deleted,
                "batches": batch_count,
                "table": table_name,
                "performance": {
                    "duration_seconds": duration,
                    "records_per_second": (
                        total_deleted / duration if duration > 0 else 0
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Error in batch cleanup for {table_name}: {e}")
            return {"deleted": total_deleted, "batches": batch_count, "error": str(e)}

    @classmethod
    async def execute_batch_operation(
        cls,
        operation_func: Callable,
        items: List[Any],
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
        delay_between_batches: float = 0.1,
    ) -> Dict[str, Any]:
        """
        Generic batch operation executor for any processing function
        Returns: {'processed': int, 'failed': int, 'batches': int}
        """
        total_processed = 0
        total_failed = 0
        batch_count = 0

        try:
            # Split items into batches
            for i in range(0, len(items), batch_size):
                batch = items[i : i + batch_size]
                batch_count += 1

                # Process batch with concurrency control
                semaphore = asyncio.Semaphore(max_concurrent)

                async def process_item_safe(item):
                    async with semaphore:
                        try:
                            await operation_func(item)
                            return True
                        except Exception as e:
                            logger.error(f"Error processing item: {e}")
                            return False

                # Execute batch
                tasks = [process_item_safe(item) for item in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Count results
                batch_processed = sum(1 for r in results if r is True)
                batch_failed = len(results) - batch_processed

                total_processed += batch_processed
                total_failed += batch_failed

                # Delay between batches
                if delay_between_batches > 0:
                    await asyncio.sleep(delay_between_batches)

            return {
                "processed": total_processed,
                "failed": total_failed,
                "batches": batch_count,
                "total_items": len(items),
            }

        except Exception as e:
            logger.error(f"Error in generic batch operation: {e}")
            return {
                "processed": total_processed,
                "failed": total_failed,
                "batches": batch_count,
                "error": str(e),
            }
