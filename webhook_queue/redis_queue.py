"""Replit Key-Value Store based message queue system for background job processing"""

import logging
import asyncio
import json
import uuid
import time
from typing import Any, Dict, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import inspect
from concurrent.futures import ThreadPoolExecutor
import traceback

# Import Replit Key-Value Store
try:
    from replit import db
    KV_AVAILABLE = True
except ImportError:
    KV_AVAILABLE = False
    db = None

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job execution status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class Priority(Enum):
    """Job priority levels"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Job:
    """Job definition for queue processing"""

    id: str
    queue_name: str
    func_name: str
    args: List[Any]
    kwargs: Dict[str, Any]
    priority: Priority
    max_retries: int
    retry_count: int
    created_at: datetime
    scheduled_for: Optional[datetime]
    status: JobStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for serialization"""
        return {
            "id": self.id,
            "queue_name": self.queue_name,
            "func_name": self.func_name,
            "args": self.args,
            "kwargs": self.kwargs,
            "priority": self.priority.value,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat(),
            "scheduled_for": (
                self.scheduled_for.isoformat() if self.scheduled_for else None
            ),
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        """Create job from dictionary"""
        return cls(
            id=data["id"],
            queue_name=data["queue_name"],
            func_name=data["func_name"],
            args=data["args"],
            kwargs=data["kwargs"],
            priority=Priority(data["priority"]),
            max_retries=data["max_retries"],
            retry_count=data["retry_count"],
            created_at=datetime.fromisoformat(data["created_at"]),
            scheduled_for=(
                datetime.fromisoformat(data["scheduled_for"])
                if data["scheduled_for"]
                else None
            ),
            status=JobStatus(data["status"]),
            result=data.get("result"),
            error=data.get("error"),
            metadata=data.get("metadata", {}),
        )


class QueueConfig:
    """Queue configuration"""

    def __init__(self):
        # Keep Redis config for backward compatibility but not used
        self.redis_url = "redis://localhost:6379/1"  # Different DB from cache
        self.default_queue = "default"
        self.max_workers = 4
        self.poll_interval = 1.0
        self.job_timeout = 300  # 5 minutes
        self.retry_delays = [60, 300, 900, 3600]  # 1m, 5m, 15m, 1h
        self.dead_letter_queue = "dead_letter"
        self.metrics_enabled = True
        self.queue_prefix = "queue:"


class ReplitQueue:
    """Replit Key-Value Store based message queue with comprehensive job management"""

    def __init__(self, config: Optional[QueueConfig] = None):
        self.config = config or QueueConfig()
        self.kv_store = db
        self.is_connected = KV_AVAILABLE
        self.workers: Dict[str, asyncio.Task] = {}
        self.is_running = False
        self.registered_functions: Dict[str, Callable] = {}
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_workers)

        # Queue metrics
        self.metrics = {
            "jobs_processed": 0,
            "jobs_failed": 0,
            "jobs_retried": 0,
            "processing_time_total": 0.0,
            "queue_sizes": {},
        }

    async def connect(self):
        """Connect to Replit Key-Value Store"""
        try:
            if not KV_AVAILABLE:
                logger.error("❌ Replit Key-Value Store not available - replit library not installed")
                self.is_connected = False
                raise RuntimeError("Key-Value Store not available")
            
            if self.kv_store is None:
                logger.error("❌ Replit Key-Value Store not initialized")
                self.is_connected = False
                raise RuntimeError("Key-Value Store not initialized")
            
            # Test Key-Value Store connectivity
            test_key = f"{self.config.queue_prefix}health_check_test"
            test_data = {"test": True, "timestamp": time.time()}
            await asyncio.to_thread(self.kv_store.__setitem__, test_key, json.dumps(test_data))
            retrieved_data = await asyncio.to_thread(self.kv_store.get, test_key)
            
            if retrieved_data:
                await asyncio.to_thread(self.kv_store.__delitem__, test_key)  # Clean up test key
                self.is_connected = True
                logger.info("✅ Replit Key-Value Store queue connected successfully")
            else:
                logger.error("❌ Key-Value Store connectivity test failed")
                self.is_connected = False
                raise RuntimeError("Key-Value Store connectivity test failed")
                
        except Exception as e:
            logger.error(f"Key-Value Store queue connection failed: {e}")
            self.is_connected = False
            raise

    async def disconnect(self):
        """Disconnect from Key-Value Store and cleanup"""
        self.is_running = False

        # Wait for workers to finish
        if self.workers:
            await asyncio.gather(*self.workers.values(), return_exceptions=True)

        # Shutdown executor
        self.executor.shutdown(wait=True)

        self.is_connected = False
        logger.info("Key-Value Store queue disconnected")

    def register_function(self, name: str, func: Callable):
        """Register function for job execution"""
        self.registered_functions[name] = func
        logger.info(f"Registered function: {name}")

    def task(
        self,
        queue: str = None,
        priority: Priority = Priority.NORMAL,
        max_retries: int = 3,
    ):
        """Decorator to register task functions"""

        def decorator(func):
            func_name = f"{func.__module__}.{func.__name__}"
            self.register_function(func_name, func)

            async def enqueue_wrapper(*args, **kwargs):
                return await self.enqueue(
                    func_name=func_name,
                    args=args,
                    kwargs=kwargs,
                    queue=queue or self.config.default_queue,
                    priority=priority,
                    max_retries=max_retries,
                )

            # Add enqueue method to function
            func.enqueue = enqueue_wrapper
            func.delay = enqueue_wrapper  # Celery-style alias

            return func

        return decorator

    async def enqueue(
        self,
        func_name: str,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        queue: str = None,
        priority: Priority = Priority.NORMAL,
        max_retries: int = 3,
        delay: Optional[timedelta] = None,
    ) -> str:
        """Enqueue a job for processing"""
        if not self.is_connected:
            raise RuntimeError("Queue not connected to Key-Value Store")

        job = Job(
            id=str(uuid.uuid4()),
            queue_name=queue or self.config.default_queue,
            func_name=func_name,
            args=args or [],
            kwargs=kwargs or {},
            priority=priority,
            max_retries=max_retries,
            retry_count=0,
            created_at=datetime.now(),
            scheduled_for=datetime.now() + delay if delay else None,
            status=JobStatus.PENDING,
        )

        # Store job data
        job_key = f"job:{job.id}"
        job_data = {
            "job_info": job.to_dict(),
            "expires_at": time.time() + 86400,  # 24 hour TTL
            "created_at": time.time()
        }
        await asyncio.to_thread(self.kv_store.__setitem__, job_key, json.dumps(job_data, default=str))

        # Add to appropriate queue based on schedule
        if job.scheduled_for and job.scheduled_for > datetime.now():
            # Delayed job - add to scheduled queue
            scheduled_key = "scheduled_jobs"
            scheduled_data = await asyncio.to_thread(self.kv_store.get, scheduled_key, "{}")
            scheduled_jobs = json.loads(scheduled_data)
            scheduled_jobs[job.id] = job.scheduled_for.timestamp()
            await asyncio.to_thread(self.kv_store.__setitem__, scheduled_key, json.dumps(scheduled_jobs))
        else:
            # Immediate job - add to priority queue
            queue_key = f"{self.config.queue_prefix}{job.queue_name}:{priority.value}"
            queue_data = await asyncio.to_thread(self.kv_store.get, queue_key, "[]")
            queue_jobs = json.loads(queue_data)
            queue_jobs.insert(0, job.id)  # Add to front (FIFO)
            await asyncio.to_thread(self.kv_store.__setitem__, queue_key, json.dumps(queue_jobs))

        logger.info(f"Enqueued job {job.id} in queue {job.queue_name}")
        return job.id

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        if not self.is_connected:
            return None

        job_key = f"job:{job_id}"
        job_data = await asyncio.to_thread(self.kv_store.get, job_key)

        if job_data:
            try:
                job_entry = json.loads(job_data)
                
                # Check if job has expired
                if "expires_at" in job_entry and time.time() > job_entry["expires_at"]:
                    # Job expired, remove it
                    await asyncio.to_thread(self.kv_store.__delitem__, job_key)
                    return None
                
                job_dict = job_entry["job_info"]
                return Job.from_dict(job_dict)
            except Exception as e:
                logger.error(f"Failed to deserialize job {job_id}: {e}")

        return None

    async def update_job(self, job: Job):
        """Update job in Key-Value Store"""
        if not self.is_connected:
            return

        job_key = f"job:{job.id}"
        job_data = {
            "job_info": job.to_dict(),
            "expires_at": time.time() + 86400,  # 24 hour TTL
            "updated_at": time.time()
        }
        await asyncio.to_thread(self.kv_store.__setitem__, job_key, json.dumps(job_data, default=str))

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job"""
        job = await self.get_job(job_id)
        if not job or job.status != JobStatus.PENDING:
            return False

        job.status = JobStatus.CANCELLED
        await self.update_job(job)

        # Remove from queues
        for priority in Priority:
            queue_key = f"{self.config.queue_prefix}{job.queue_name}:{priority.value}"
            queue_data = await asyncio.to_thread(self.kv_store.get, queue_key, "[]")
            queue_jobs = json.loads(queue_data)
            if job_id in queue_jobs:
                queue_jobs.remove(job_id)
                await asyncio.to_thread(self.kv_store.__setitem__, queue_key, json.dumps(queue_jobs))

        # Remove from scheduled jobs
        scheduled_key = "scheduled_jobs"
        scheduled_data = await asyncio.to_thread(self.kv_store.get, scheduled_key, "{}")
        scheduled_jobs = json.loads(scheduled_data)
        if job_id in scheduled_jobs:
            del scheduled_jobs[job_id]
            await asyncio.to_thread(self.kv_store.__setitem__, scheduled_key, json.dumps(scheduled_jobs))

        logger.info(f"Cancelled job {job_id}")
        return True

    async def retry_job(self, job: Job):
        """Retry a failed job"""
        if job.retry_count >= job.max_retries:
            # Move to dead letter queue
            dlq_key = f"{self.config.queue_prefix}{self.config.dead_letter_queue}"
            dlq_data = await asyncio.to_thread(self.kv_store.get, dlq_key, "[]")
            dlq_jobs = json.loads(dlq_data)
            dlq_jobs.insert(0, job.id)
            await asyncio.to_thread(self.kv_store.__setitem__, dlq_key, json.dumps(dlq_jobs))
            
            job.status = JobStatus.FAILED
            await self.update_job(job)
            logger.error(
                f"Job {job.id} moved to dead letter queue after {job.retry_count} retries"
            )
            return

        # Calculate retry delay
        delay_index = min(job.retry_count, len(self.config.retry_delays) - 1)
        delay_seconds = self.config.retry_delays[delay_index]

        job.retry_count += 1
        job.status = JobStatus.RETRYING
        job.scheduled_for = datetime.now() + timedelta(seconds=delay_seconds)

        await self.update_job(job)

        # Schedule for retry
        scheduled_key = "scheduled_jobs"
        scheduled_data = await asyncio.to_thread(self.kv_store.get, scheduled_key, "{}")
        scheduled_jobs = json.loads(scheduled_data)
        scheduled_jobs[job.id] = job.scheduled_for.timestamp()
        await asyncio.to_thread(self.kv_store.__setitem__, scheduled_key, json.dumps(scheduled_jobs))

        self.metrics["jobs_retried"] += 1
        logger.info(
            f"Scheduled job {job.id} for retry {job.retry_count}/{job.max_retries} in {delay_seconds}s"
        )

    async def process_scheduled_jobs(self):
        """Move scheduled jobs to active queues when due"""
        if not self.is_connected:
            return

        now = time.time()

        # Get scheduled jobs
        scheduled_key = "scheduled_jobs"
        scheduled_data = await asyncio.to_thread(self.kv_store.get, scheduled_key, "{}")
        scheduled_jobs = json.loads(scheduled_data)
        
        # Find jobs that are due
        due_job_ids = []
        for job_id, scheduled_time in scheduled_jobs.items():
            if scheduled_time <= now:
                due_job_ids.append(job_id)

        for job_id in due_job_ids:
            job = await self.get_job(job_id)
            if job and job.status in [JobStatus.PENDING, JobStatus.RETRYING]:
                # Move to active queue
                queue_key = f"{self.config.queue_prefix}{job.queue_name}:{job.priority.value}"
                queue_data = await asyncio.to_thread(self.kv_store.get, queue_key, "[]")
                queue_jobs = json.loads(queue_data)
                queue_jobs.insert(0, job.id)
                await asyncio.to_thread(self.kv_store.__setitem__, queue_key, json.dumps(queue_jobs))

                # Remove from scheduled queue
                del scheduled_jobs[job_id]

                job.status = JobStatus.PENDING
                await self.update_job(job)
        
        # Update scheduled jobs
        if due_job_ids:
            await asyncio.to_thread(self.kv_store.__setitem__, scheduled_key, json.dumps(scheduled_jobs))

    async def get_next_job(self, queue_names: List[str]) -> Optional[Job]:
        """Get next job from priority queues with atomic status-based dequeue"""
        if not self.is_connected:
            return None

        # Check queues in priority order (high to low)
        for priority in sorted(Priority, key=lambda p: p.value, reverse=True):
            for queue_name in queue_names:
                queue_key = f"{self.config.queue_prefix}{queue_name}:{priority.value}"
                
                # Atomic dequeue: use job status as the lock
                max_attempts = 5
                
                for attempt in range(max_attempts):
                    queue_data = await asyncio.to_thread(self.kv_store.get, queue_key, "[]")
                    queue_jobs = json.loads(queue_data)

                    if not queue_jobs:
                        break  # Queue empty, try next queue
                    
                    # Pop job from end (FIFO)
                    job_id = queue_jobs.pop()
                    # Immediately save the modified queue (remove job from queue list)
                    await asyncio.to_thread(self.kv_store.__setitem__, queue_key, json.dumps(queue_jobs))
                    
                    # Now try to claim the job by changing its status atomically
                    job = await self.get_job(job_id)
                    if not job:
                        # Job doesn't exist, skip it
                        continue
                    
                    # ATOMIC CHECK: Only process if status is PENDING
                    # This prevents double-processing even if two workers popped the same job
                    if job.status == JobStatus.PENDING:
                        # Claim the job by updating status
                        job_key = f"job:{job.id}"  # FIXED: Remove queue_prefix to match storage key
                        job_data = await asyncio.to_thread(self.kv_store.get, job_key)
                        if job_data:
                            job_dict = json.loads(job_data)
                            # Double-check status hasn't changed (status is in job_info dict)
                            if job_dict.get('job_info', {}).get('status') == JobStatus.PENDING.value:
                                # Update to PROCESSING atomically
                                job_dict['job_info']['status'] = JobStatus.PROCESSING.value
                                await asyncio.to_thread(self.kv_store.__setitem__, job_key, json.dumps(job_dict))
                                job.status = JobStatus.PROCESSING
                                logger.debug(f"✅ Claimed job {job.id} for processing")
                                return job
                            else:
                                logger.debug(f"⚠️ Job {job.id} status changed during claim, skipping")
                                continue
                    else:
                        # Job already claimed by another worker
                        logger.debug(f"⚠️ Job {job.id} already claimed (status: {job.status}), skipping")
                        continue

        return None

    async def execute_job(self, job: Job) -> bool:
        """Execute a job"""
        start_time = datetime.now()

        try:
            # Get registered function
            if job.func_name not in self.registered_functions:
                raise ValueError(f"Function {job.func_name} not registered")

            func = self.registered_functions[job.func_name]

            # Execute function
            if inspect.iscoroutinefunction(func):
                result = await func(*job.args, **job.kwargs)
            else:
                # Run sync function in thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor, func, *job.args, **job.kwargs
                )

            # Update job with result
            job.status = JobStatus.COMPLETED
            job.result = result
            await self.update_job(job)

            # Update metrics
            execution_time = (datetime.now() - start_time).total_seconds()
            self.metrics["jobs_processed"] += 1
            self.metrics["processing_time_total"] += execution_time

            logger.info(f"Job {job.id} completed successfully in {execution_time:.2f}s")
            return True

        except Exception as e:
            error_msg = f"Job execution failed: {str(e)}\n{traceback.format_exc()}"
            job.error = error_msg

            logger.error(f"Job {job.id} failed: {e}")

            # Retry or fail
            await self.retry_job(job)
            self.metrics["jobs_failed"] += 1

            return False

    async def worker(self, worker_id: str, queue_names: List[str]):
        """Worker process for job execution"""
        logger.info(f"Worker {worker_id} started for queues: {queue_names}")

        while self.is_running:
            try:
                # Process scheduled jobs
                await self.process_scheduled_jobs()

                # Get next job
                job = await self.get_next_job(queue_names)

                if job:
                    logger.info(f"Worker {worker_id} processing job {job.id}")
                    await self.execute_job(job)
                else:
                    # No jobs available, wait
                    await asyncio.sleep(self.config.poll_interval)

            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(self.config.poll_interval)

        logger.info(f"Worker {worker_id} stopped")

    async def start_workers(self, queue_names: List[str] = None):
        """Start background workers"""
        if self.is_running:
            return

        queue_names = queue_names or [self.config.default_queue]
        self.is_running = True

        # Start workers
        for i in range(self.config.max_workers):
            worker_id = f"worker_{i}"
            task = asyncio.create_task(self.worker(worker_id, queue_names))
            self.workers[worker_id] = task

        logger.info(f"Started {len(self.workers)} workers for queues: {queue_names}")

    async def stop_workers(self):
        """Stop all workers"""
        self.is_running = False

        if self.workers:
            await asyncio.gather(*self.workers.values(), return_exceptions=True)
            self.workers.clear()

        logger.info("All workers stopped")

    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        if not self.is_connected:
            return {}

        stats = {
            "queues": {},
            "scheduled_jobs": 0,
            "dead_letter_queue": 0,
            "total_jobs": 0,
        }

        try:
            # Get queue sizes
            queue_prefix = self.config.queue_prefix
            for key in list(await asyncio.to_thread(list, self.kv_store.keys())):
                if key.startswith(queue_prefix):
                    queue_data = await asyncio.to_thread(self.kv_store.get, key, "[]")
                    queue_jobs = json.loads(queue_data)
                    size = len(queue_jobs)
                    stats["queues"][key] = size
                    stats["total_jobs"] += size

            # Scheduled jobs
            scheduled_data = await asyncio.to_thread(self.kv_store.get, "scheduled_jobs", "{}")
            scheduled_jobs = json.loads(scheduled_data)
            stats["scheduled_jobs"] = len(scheduled_jobs)

            # Dead letter queue
            dlq_key = f"{self.config.queue_prefix}{self.config.dead_letter_queue}"
            dlq_data = await asyncio.to_thread(self.kv_store.get, dlq_key, "[]")
            dlq_jobs = json.loads(dlq_data)
            stats["dead_letter_queue"] = len(dlq_jobs)

        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")

        # Add runtime metrics
        stats["metrics"] = self.metrics.copy()

        return stats

    async def health_check(self) -> Dict[str, Any]:
        """Check queue system health"""
        try:
            if not self.is_connected:
                return {"status": "error", "error": "Not connected to Key-Value Store"}

            # Test Key-Value Store connection
            test_key = f"{self.config.queue_prefix}health_test"
            await asyncio.to_thread(self.kv_store.__setitem__, test_key, json.dumps({"test": True}))
            test_data = await asyncio.to_thread(self.kv_store.get, test_key)
            if test_data:
                await asyncio.to_thread(self.kv_store.__delitem__, test_key)

            # Check worker status
            active_workers = len([w for w in self.workers.values() if not w.done()])

            # Get queue stats
            stats = await self.get_queue_stats()

            return {
                "status": "healthy",
                "active_workers": active_workers,
                "total_workers": len(self.workers),
                "queue_stats": stats,
                "is_running": self.is_running,
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}


# Global queue instance
replit_queue = ReplitQueue()

# Backward compatibility alias
redis_queue = replit_queue


async def initialize_queue():
    """Initialize Replit Key-Value Store queue system"""
    await replit_queue.connect()
    await replit_queue.start_workers()


async def cleanup_queue():
    """Cleanup queue system"""
    await replit_queue.stop_workers()
    await replit_queue.disconnect()


# Convenience decorators
def task(queue: str = None, priority: Priority = Priority.NORMAL, max_retries: int = 3):
    """Decorator for creating background tasks"""
    return replit_queue.task(queue, priority, max_retries)


# Example usage functions
@task(queue="email", priority=Priority.HIGH, max_retries=5)
async def send_email_task(to_email: str, subject: str, content: str):
    """Example email sending task"""
    # Simulate email sending
    await asyncio.sleep(2)
    logger.info(f"Email sent to {to_email}: {subject}")
    return {"status": "sent", "to": to_email}


@task(queue="notifications", priority=Priority.NORMAL)
async def send_notification_task(user_id: int, message: str):
    """Example notification task"""
    await asyncio.sleep(1)
    logger.info(f"Notification sent to user {user_id}: {message}")
    return {"status": "sent", "user_id": user_id}
