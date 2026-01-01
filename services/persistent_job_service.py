#!/usr/bin/env python3
"""
Persistent Job Service
Database-backed job scheduling with outbox pattern and reliability guarantees
"""

import logging
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import croniter
import psutil
import os

from database import SessionLocal
from models import PersistentJob, JobExecution, JobStatus, JobPriority
from utils.atomic_transactions import atomic_transaction

logger = logging.getLogger(__name__)


@dataclass
class JobResult:
    """Job execution result"""

    success: bool
    result: Any = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    metadata: Optional[Dict] = None


class JobDefinition:
    """Job definition with handler and configuration"""

    def __init__(
        self,
        job_type: str,
        handler: Callable,
        schedule_type: str = "once",
        schedule_expression: Optional[str] = None,
        priority: str = JobPriority.NORMAL.value,
        max_retries: int = 3,
        retry_delay: int = 60,
        parameters: Optional[Dict] = None,
    ):
        self.job_type = job_type
        self.handler = handler
        self.schedule_type = schedule_type  # 'once', 'interval', 'cron'
        self.schedule_expression = schedule_expression
        self.priority = priority
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.parameters = parameters or {}


class PersistentJobService:
    """Database-backed job scheduler with distributed execution support"""

    def __init__(self, worker_id: Optional[str] = None):
        self.worker_id = worker_id or f"worker_{os.getpid()}_{uuid.uuid4().hex[:8]}"
        self.job_handlers: Dict[str, Callable] = {}
        self.running = False
        self.execution_loop_task = None
        self.lock_refresh_task = None
        self.cleanup_task = None

        # Configuration - Optimized for lower CPU usage
        self.poll_interval = 30  # Increased from 5 to 30 seconds to reduce polling
        self.lock_timeout = 300  # 5 minutes
        self.lock_refresh_interval = 120  # Increased from 60 to 120 seconds
        self.max_concurrent_jobs = 3  # Reduced from 5 to 3 for resource efficiency

        logger.info(
            f"Initialized persistent job service with worker ID: {self.worker_id}"
        )

    def register_handler(self, job_type: str, handler: Callable):
        """Register a job handler function"""
        self.job_handlers[job_type] = handler
        logger.info(f"Registered handler for job type: {job_type}")

    def schedule_job(
        self,
        job_type: str,
        run_at: datetime,
        parameters: Optional[Dict] = None,
        priority: str = JobPriority.NORMAL.value,
        max_retries: int = 3,
        job_group: Optional[str] = None,
    ) -> str:
        """Schedule a one-time job"""
        job_id = self._generate_job_id()

        try:
            with atomic_transaction() as session:
                job = PersistentJob(
                    job_id=job_id,
                    job_type=job_type,
                    handler_name=f"{job_type}_handler",
                    parameters=parameters,
                    priority=priority,
                    max_retries=max_retries,
                    schedule_type="once",
                    next_run_at=run_at,
                    job_group=job_group,
                    created_by=self.worker_id,
                )
                session.add(job)

                logger.info(f"Scheduled job {job_id} of type {job_type} for {run_at}")
                return job_id

        except Exception as e:
            logger.error(f"Error scheduling job: {e}")
            raise

    def schedule_recurring_job(
        self,
        job_type: str,
        schedule_expression: str,
        parameters: Optional[Dict] = None,
        priority: str = JobPriority.NORMAL.value,
        max_retries: int = 3,
        job_group: Optional[str] = None,
    ) -> str:
        """Schedule a recurring job with cron expression"""
        job_id = self._generate_job_id()

        try:
            # Calculate next run time from cron expression
            cron = croniter.croniter(schedule_expression, datetime.utcnow())
            next_run = cron.get_next(datetime)

            with atomic_transaction() as session:
                job = PersistentJob(
                    job_id=job_id,
                    job_type=job_type,
                    handler_name=f"{job_type}_handler",
                    parameters=parameters,
                    priority=priority,
                    max_retries=max_retries,
                    schedule_type="cron",
                    schedule_expression=schedule_expression,
                    next_run_at=next_run,
                    job_group=job_group,
                    created_by=self.worker_id,
                )
                session.add(job)

                logger.info(
                    f"Scheduled recurring job {job_id} of type {job_type} with cron '{schedule_expression}'"
                )
                return job_id

        except Exception as e:
            logger.error(f"Error scheduling recurring job: {e}")
            raise

    def schedule_interval_job(
        self,
        job_type: str,
        interval_seconds: int,
        parameters: Optional[Dict] = None,
        priority: str = JobPriority.NORMAL.value,
        max_retries: int = 3,
        job_group: Optional[str] = None,
    ) -> str:
        """Schedule a job to run at fixed intervals"""
        job_id = self._generate_job_id()

        try:
            next_run = datetime.utcnow() + timedelta(seconds=interval_seconds)

            with atomic_transaction() as session:
                job = PersistentJob(
                    job_id=job_id,
                    job_type=job_type,
                    handler_name=f"{job_type}_handler",
                    parameters=parameters,
                    priority=priority,
                    max_retries=max_retries,
                    schedule_type="interval",
                    schedule_expression=str(interval_seconds),
                    next_run_at=next_run,
                    job_group=job_group,
                    created_by=self.worker_id,
                )
                session.add(job)

                logger.info(
                    f"Scheduled interval job {job_id} of type {job_type} every {interval_seconds} seconds"
                )
                return job_id

        except Exception as e:
            logger.error(f"Error scheduling interval job: {e}")
            raise

    async def start(self):
        """Start the job execution service"""
        if self.running:
            logger.warning("Job service already running")
            return

        self.running = True
        logger.info(f"Starting persistent job service worker: {self.worker_id}")

        # Start background tasks
        self.execution_loop_task = asyncio.create_task(self._execution_loop())
        self.lock_refresh_task = asyncio.create_task(self._lock_refresh_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())

        # Wait for tasks to complete (they run indefinitely until stopped)
        try:
            await asyncio.gather(
                self.execution_loop_task, self.lock_refresh_task, self.cleanup_task
            )
        except asyncio.CancelledError:
            logger.info("Job service tasks cancelled")

    async def stop(self):
        """Stop the job execution service"""
        if not self.running:
            return

        logger.info("Stopping persistent job service")
        self.running = False

        # Cancel background tasks
        if self.execution_loop_task:
            self.execution_loop_task.cancel()
        if self.lock_refresh_task:
            self.lock_refresh_task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()

        # Release any held locks
        await self._release_all_locks()

        logger.info("Persistent job service stopped")

    async def _execution_loop(self):
        """Main execution loop for processing jobs"""
        while self.running:
            try:
                # Get available jobs
                available_jobs = await self._get_available_jobs()

                if not available_jobs:
                    await asyncio.sleep(self.poll_interval)
                    continue

                # Process jobs concurrently (up to max_concurrent_jobs)
                tasks = []
                for job in available_jobs[: self.max_concurrent_jobs]:
                    task = asyncio.create_task(self._execute_job(job))
                    tasks.append(task)

                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

                await asyncio.sleep(5)  # Increased from 1 to 5 seconds to reduce CPU usage

            except Exception as e:
                logger.error(f"Error in execution loop: {e}")
                await asyncio.sleep(self.poll_interval)

    async def _get_available_jobs(self) -> List[PersistentJob]:
        """Get jobs ready for execution"""
        try:
            with SessionLocal() as session:
                now = datetime.utcnow()

                # Get pending jobs that are ready to run and not locked
                jobs = (
                    session.query(PersistentJob)
                    .filter(
                        PersistentJob.status == JobStatus.PENDING.value,
                        PersistentJob.next_run_at <= now,
                        (PersistentJob.locked_by.is_(None))
                        | (PersistentJob.lock_expires_at <= now),
                    )
                    .order_by(
                        # Priority order: URGENT, HIGH, NORMAL, LOW
                        PersistentJob.priority.desc(),
                        PersistentJob.next_run_at.asc(),
                    )
                    .limit(self.max_concurrent_jobs * 2)
                    .all()
                )  # Get extra for filtering

                return jobs

        except Exception as e:
            logger.error(f"Error getting available jobs: {e}")
            return []

    async def _execute_job(self, job: PersistentJob) -> JobResult:
        """Execute a single job with locking and error handling"""
        execution_id = self._generate_execution_id()
        start_time = datetime.utcnow()

        try:
            # Acquire job lock
            if not await self._acquire_job_lock(job.job_id):
                logger.debug(f"Could not acquire lock for job {job.job_id}")
                return JobResult(success=False, error_message="Could not acquire lock")

            # Update job status to running
            with atomic_transaction() as session:
                job_db = (
                    session.query(PersistentJob)
                    .filter(PersistentJob.job_id == job.job_id)
                    .with_for_update()
                    .first()
                )

                if not job_db or job_db.status != JobStatus.PENDING.value:
                    logger.warning(f"Job {job.job_id} no longer pending")
                    return JobResult(
                        success=False, error_message="Job no longer pending"
                    )

                job_db.status = JobStatus.RUNNING.value
                job_db.started_at = start_time
                job_db.current_attempt += 1

            # Execute the job handler
            handler = self.job_handlers.get(job.job_type)
            if not handler:
                raise ValueError(f"No handler registered for job type: {job.job_type}")

            # Create execution record
            execution = JobExecution(
                execution_id=execution_id,
                job_id=job.job_id,
                attempt_number=job.current_attempt,
                worker_id=self.worker_id,
                started_at=start_time,
                parameters_used=job.parameters,
                environment_info=self._get_environment_info(),
            )

            # Execute the handler
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**(job.parameters or {}))
            else:
                result = handler(**(job.parameters or {}))

            # Job completed successfully
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Update job and execution records
            with atomic_transaction() as session:
                # Update job
                job_db = (
                    session.query(PersistentJob)
                    .filter(PersistentJob.job_id == job.job_id)
                    .first()
                )

                if job_db.schedule_type == "once":
                    job_db.status = JobStatus.COMPLETED.value
                    job_db.completed_at = end_time
                else:
                    # Schedule next run for recurring jobs
                    job_db.status = JobStatus.PENDING.value
                    job_db.next_run_at = self._calculate_next_run(job_db)
                    job_db.current_attempt = 0  # Reset attempt counter

                job_db.result = result
                job_db.locked_by = None
                job_db.locked_at = None
                job_db.lock_expires_at = None

                # Update execution record
                execution.status = "success"
                execution.completed_at = end_time
                execution.duration_ms = duration_ms
                execution.result = result
                session.add(execution)

            logger.info(f"Successfully executed job {job.job_id} in {duration_ms}ms")
            return JobResult(success=True, result=result, duration_ms=duration_ms)

        except Exception as e:
            # Job failed
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            error_msg = str(e)

            logger.error(f"Job {job.job_id} failed: {error_msg}")

            # Handle job failure and retries
            await self._handle_job_failure(
                job, error_msg, execution_id, start_time, end_time, duration_ms
            )

            return JobResult(
                success=False, error_message=error_msg, duration_ms=duration_ms
            )

        finally:
            # Always release the lock
            await self._release_job_lock(job.job_id)

    async def _handle_job_failure(
        self,
        job: PersistentJob,
        error_msg: str,
        execution_id: str,
        start_time: datetime,
        end_time: datetime,
        duration_ms: int,
    ):
        """Handle job failure with retry logic"""
        try:
            with atomic_transaction() as session:
                job_db = (
                    session.query(PersistentJob)
                    .filter(PersistentJob.job_id == job.job_id)
                    .first()
                )

                if job_db.current_attempt >= job_db.max_retries:
                    # Max retries reached, mark as failed
                    job_db.status = JobStatus.FAILED.value
                    job_db.failed_at = end_time
                    job_db.error_message = error_msg
                    status = "failed"
                else:
                    # Schedule retry
                    job_db.status = JobStatus.PENDING.value
                    job_db.next_run_at = datetime.utcnow() + timedelta(
                        seconds=job_db.retry_delay
                    )
                    status = "retry_scheduled"

                job_db.locked_by = None
                job_db.locked_at = None
                job_db.lock_expires_at = None

                # Create execution record
                execution = JobExecution(
                    execution_id=execution_id,
                    job_id=job.job_id,
                    attempt_number=job_db.current_attempt,
                    worker_id=self.worker_id,
                    started_at=start_time,
                    completed_at=end_time,
                    duration_ms=duration_ms,
                    status=status,
                    error_message=error_msg,
                    parameters_used=job.parameters,
                    environment_info=self._get_environment_info(),
                )
                session.add(execution)

        except Exception as e:
            logger.error(f"Error handling job failure: {e}")

    async def _acquire_job_lock(self, job_id: str) -> bool:
        """Acquire an exclusive lock on a job"""
        try:
            with atomic_transaction() as session:
                now = datetime.utcnow()
                lock_expires = now + timedelta(seconds=self.lock_timeout)

                # Try to acquire lock
                result = (
                    session.query(PersistentJob)
                    .filter(
                        PersistentJob.job_id == job_id,
                        (PersistentJob.locked_by.is_(None))
                        | (PersistentJob.lock_expires_at <= now),
                    )
                    .update(
                        {
                            "locked_by": self.worker_id,
                            "locked_at": now,
                            "lock_expires_at": lock_expires,
                        }
                    )
                )

                return result > 0

        except Exception as e:
            logger.error(f"Error acquiring job lock: {e}")
            return False

    async def _release_job_lock(self, job_id: str):
        """Release a job lock"""
        try:
            with atomic_transaction() as session:
                session.query(PersistentJob).filter(
                    PersistentJob.job_id == job_id,
                    PersistentJob.locked_by == self.worker_id,
                ).update(
                    {"locked_by": None, "locked_at": None, "lock_expires_at": None}
                )

        except Exception as e:
            logger.error(f"Error releasing job lock: {e}")

    async def _release_all_locks(self):
        """Release all locks held by this worker"""
        try:
            with atomic_transaction() as session:
                session.query(PersistentJob).filter(
                    PersistentJob.locked_by == self.worker_id
                ).update(
                    {"locked_by": None, "locked_at": None, "lock_expires_at": None}
                )

        except Exception as e:
            logger.error(f"Error releasing all locks: {e}")

    async def _lock_refresh_loop(self):
        """Periodically refresh locks to prevent timeout"""
        while self.running:
            try:
                await asyncio.sleep(self.lock_refresh_interval)

                with atomic_transaction() as session:
                    now = datetime.utcnow()
                    new_expires = now + timedelta(seconds=self.lock_timeout)

                    session.query(PersistentJob).filter(
                        PersistentJob.locked_by == self.worker_id,
                        PersistentJob.status == JobStatus.RUNNING.value,
                    ).update({"lock_expires_at": new_expires})

            except Exception as e:
                logger.error(f"Error refreshing locks: {e}")

    async def _cleanup_loop(self):
        """Periodic cleanup of old job records and expired locks"""
        cleanup_interval = 3600  # 1 hour

        while self.running:
            try:
                await asyncio.sleep(cleanup_interval)

                with atomic_transaction() as session:
                    now = datetime.utcnow()

                    # Clean up expired locks
                    expired_locks = (
                        session.query(PersistentJob)
                        .filter(
                            PersistentJob.locked_by.isnot(None),
                            PersistentJob.lock_expires_at <= now,
                        )
                        .update(
                            {
                                "locked_by": None,
                                "locked_at": None,
                                "lock_expires_at": None,
                                "status": JobStatus.PENDING.value,  # Reset to pending for retry
                            }
                        )
                    )

                    if expired_locks > 0:
                        logger.info(f"Cleaned up {expired_locks} expired job locks")

                    # Clean up old completed job executions (keep last 30 days)
                    cutoff_date = now - timedelta(days=30)
                    old_executions = (
                        session.query(JobExecution)
                        .filter(JobExecution.completed_at < cutoff_date)
                        .delete()
                    )

                    if old_executions > 0:
                        logger.info(
                            f"Cleaned up {old_executions} old job execution records"
                        )

            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    def _calculate_next_run(self, job: PersistentJob) -> datetime:
        """Calculate next run time for recurring jobs"""
        if job.schedule_type == "cron":
            cron = croniter.croniter(job.schedule_expression, datetime.utcnow())
            return cron.get_next(datetime)
        elif job.schedule_type == "interval":
            interval_seconds = int(job.schedule_expression)
            return datetime.utcnow() + timedelta(seconds=interval_seconds)
        else:
            raise ValueError(f"Unknown schedule type: {job.schedule_type}")

    def _generate_job_id(self) -> str:
        """Generate unique job ID"""
        return f"job_{uuid.uuid4().hex[:12]}"

    def _generate_execution_id(self) -> str:
        """Generate unique execution ID"""
        return f"exec_{uuid.uuid4().hex[:12]}"

    def _get_environment_info(self) -> Dict:
        """Get current environment information"""
        try:
            return {
                "worker_id": self.worker_id,
                "pid": os.getpid(),
                "cpu_count": psutil.cpu_count(),
                "memory_total_mb": psutil.virtual_memory().total // (1024 * 1024),
                "memory_available_mb": psutil.virtual_memory().available
                // (1024 * 1024),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception:
            return {"worker_id": self.worker_id, "pid": os.getpid()}

    # Job management methods
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job"""
        try:
            with atomic_transaction() as session:
                result = (
                    session.query(PersistentJob)
                    .filter(
                        PersistentJob.job_id == job_id,
                        PersistentJob.status.in_(
                            [JobStatus.PENDING.value, JobStatus.RETRYING.value]
                        ),
                    )
                    .update(
                        {
                            "status": JobStatus.CANCELLED.value,
                            "completed_at": datetime.utcnow(),
                        }
                    )
                )

                return result > 0

        except Exception as e:
            logger.error(f"Error cancelling job: {e}")
            return False

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get current job status and details"""
        try:
            with SessionLocal() as session:
                job = (
                    session.query(PersistentJob)
                    .filter(PersistentJob.job_id == job_id)
                    .first()
                )

                if not job:
                    return None

                return {
                    "job_id": job.job_id,
                    "job_type": job.job_type,
                    "status": job.status,
                    "current_attempt": job.current_attempt,
                    "max_retries": job.max_retries,
                    "next_run_at": (
                        job.next_run_at.isoformat() if job.next_run_at else None
                    ),
                    "created_at": job.created_at.isoformat(),
                    "last_run_at": (
                        job.last_run_at.isoformat() if job.last_run_at else None
                    ),
                    "error_message": job.error_message,
                }

        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return None


# Global instance
persistent_job_service = PersistentJobService()


# Convenience functions for backward compatibility
def schedule_job(job_type: str, run_at: datetime, **kwargs) -> str:
    """Schedule a one-time job"""
    return persistent_job_service.schedule_job(job_type, run_at, **kwargs)


def schedule_recurring_job(job_type: str, cron_expression: str, **kwargs) -> str:
    """Schedule a recurring job"""
    return persistent_job_service.schedule_recurring_job(
        job_type, cron_expression, **kwargs
    )


def schedule_interval_job(job_type: str, interval_seconds: int, **kwargs) -> str:
    """Schedule an interval job"""
    return persistent_job_service.schedule_interval_job(
        job_type, interval_seconds, **kwargs
    )
