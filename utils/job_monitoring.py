"""
Background Job Monitoring System
Monitors APScheduler jobs for timeouts and performance issues
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class JobExecution:
    """Represents a job execution record"""
    job_id: str
    job_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    status: str = "running"  # running, completed, failed, timeout
    error_message: Optional[str] = None

class JobMonitor:
    """
    Monitors background jobs for performance and timeout issues
    """
    
    def __init__(self):
        # Track job executions
        self._job_executions: Dict[str, JobExecution] = {}
        self._job_history: List[JobExecution] = []
        
        # Configuration
        self._default_timeout = timedelta(minutes=5)  # Default job timeout
        self._job_timeouts = {
            'exchange_monitor': timedelta(minutes=3),
            'fincra_monitor': timedelta(minutes=2),
            'balance_monitor': timedelta(minutes=1),
            'deposit_monitor': timedelta(minutes=3),
            'cashout_processor': timedelta(minutes=5),
            'daily_report': timedelta(minutes=10),
        }
        
        # Alert thresholds
        self._failure_rate_threshold = 0.2  # 20% failure rate triggers alert
        self._avg_duration_threshold = 30.0  # 30 seconds average duration
        
        # Start monitoring task
        asyncio.create_task(self._monitoring_task())
    
    def job_started(self, job_id: str, job_name: str):
        """Record job start"""
        execution = JobExecution(
            job_id=job_id,
            job_name=job_name,
            started_at=datetime.now(),
            status="running"
        )
        
        self._job_executions[job_id] = execution
        logger.debug(f"Job started: {job_name} ({job_id})")
    
    def job_completed(self, job_id: str, success: bool = True, error_message: str = None):
        """Record job completion"""
        if job_id not in self._job_executions:
            logger.warning(f"Job completion recorded for unknown job: {job_id}")
            return
        
        execution = self._job_executions[job_id]
        execution.completed_at = datetime.now()
        execution.duration = (execution.completed_at - execution.started_at).total_seconds()
        execution.status = "completed" if success else "failed"
        execution.error_message = error_message
        
        # Move to history
        self._job_history.append(execution)
        del self._job_executions[job_id]
        
        # Check for performance issues
        self._check_job_performance(execution)
        
        logger.debug(f"Job completed: {execution.job_name} ({execution.duration:.2f}s)")
    
    def _check_job_performance(self, execution: JobExecution):
        """Check individual job performance for issues"""
        
        # Check timeout
        job_timeout = self._job_timeouts.get(execution.job_name, self._default_timeout)
        if execution.duration and execution.duration > job_timeout.total_seconds():
            logger.warning(
                f"⚠️ Job timeout warning: {execution.job_name} took {execution.duration:.2f}s "
                f"(threshold: {job_timeout.total_seconds()}s)"
            )
            self._trigger_job_alert(
                job_name=execution.job_name,
                alert_type="timeout_warning",
                message=f"Job exceeded expected duration: {execution.duration:.2f}s",
                context={"duration": execution.duration, "threshold": job_timeout.total_seconds()}
            )
        
        # Check for failures
        if execution.status == "failed":
            logger.error(f"❌ Job failed: {execution.job_name} - {execution.error_message}")
            self._trigger_job_alert(
                job_name=execution.job_name,
                alert_type="job_failure",
                message=f"Job failed: {execution.error_message}",
                context={"error": execution.error_message}
            )
    
    async def _monitoring_task(self):
        """Background monitoring task"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._check_running_jobs()
                await self._analyze_job_patterns()
                await self._cleanup_history()
            except Exception as e:
                logger.error(f"Error in job monitoring task: {e}")
    
    async def _check_running_jobs(self):
        """Check for stuck/long-running jobs"""
        current_time = datetime.now()
        
        for job_id, execution in list(self._job_executions.items()):
            runtime = (current_time - execution.started_at).total_seconds()
            job_timeout = self._job_timeouts.get(execution.job_name, self._default_timeout)
            
            if runtime > job_timeout.total_seconds():
                logger.critical(
                    f"🚨 Job timeout detected: {execution.job_name} has been running for {runtime:.2f}s"
                )
                
                # Mark as timeout and move to history
                execution.completed_at = current_time
                execution.duration = runtime
                execution.status = "timeout"
                execution.error_message = f"Job exceeded timeout ({job_timeout.total_seconds()}s)"
                
                self._job_history.append(execution)
                del self._job_executions[job_id]
                
                # Trigger high-priority alert
                self._trigger_job_alert(
                    job_name=execution.job_name,
                    alert_type="job_timeout",
                    message=f"Job timed out after {runtime:.2f}s",
                    context={"runtime": runtime, "timeout": job_timeout.total_seconds()},
                    severity="high"
                )
    
    async def _analyze_job_patterns(self):
        """Analyze job execution patterns for systemic issues"""
        
        # Analyze last hour of job history
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_jobs = [
            job for job in self._job_history
            if job.started_at > one_hour_ago
        ]
        
        if len(recent_jobs) < 5:  # Not enough data
            return
        
        # Group by job name
        jobs_by_name = defaultdict(list)
        for job in recent_jobs:
            jobs_by_name[job.job_name].append(job)
        
        # Analyze each job type
        for job_name, executions in jobs_by_name.items():
            if len(executions) < 3:  # Need at least 3 executions
                continue
            
            # Calculate failure rate
            failures = [job for job in executions if job.status in ['failed', 'timeout']]
            failure_rate = len(failures) / len(executions)
            
            if failure_rate > self._failure_rate_threshold:
                self._trigger_job_alert(
                    job_name=job_name,
                    alert_type="high_failure_rate",
                    message=f"High failure rate detected: {failure_rate:.1%} ({len(failures)}/{len(executions)})",
                    context={"failure_rate": failure_rate, "failures": len(failures), "total": len(executions)},
                    severity="high"
                )
            
            # Calculate average duration
            successful_jobs = [job for job in executions if job.status == 'completed' and job.duration]
            if successful_jobs:
                avg_duration = sum(job.duration for job in successful_jobs) / len(successful_jobs)
                
                if avg_duration > self._avg_duration_threshold:
                    self._trigger_job_alert(
                        job_name=job_name,
                        alert_type="slow_performance",
                        message=f"Slow job performance: average {avg_duration:.2f}s",
                        context={"avg_duration": avg_duration, "threshold": self._avg_duration_threshold},
                        severity="medium"
                    )
    
    def _trigger_job_alert(self, job_name: str, alert_type: str, message: str, 
                          context: Dict = None, severity: str = "medium"):
        """Trigger alert for job issues"""
        
        alert_message = f"Job Alert ({severity.upper()}): {job_name} - {message}"
        
        if severity == "high":
            logger.critical(f"🚨 {alert_message}")
        elif severity == "medium":
            logger.warning(f"⚠️ {alert_message}")
        else:
            logger.info(f"ℹ️ {alert_message}")
        
        # Here you could integrate with external alerting systems:
        # - Send to admin alert system
        # - Integrate with monitoring tools
        # - Send notifications to admin chat
        
        # Integration with admin alert system
        try:
            from utils.admin_alert_system import admin_alert_system
            asyncio.create_task(
                admin_alert_system.log_suspicious_activity(
                    user_id=0,  # System user
                    activity_type=f"job_alert_{alert_type}",
                    details={
                        "job_name": job_name,
                        "message": message,
                        "severity": severity,
                        **(context or {})
                    }
                )
            )
        except Exception as e:
            logger.debug(f"Could not integrate with admin alert system: {e}")
    
    async def _cleanup_history(self):
        """Clean up old job history"""
        # Keep only last 24 hours of history
        cutoff_time = datetime.now() - timedelta(hours=24)
        self._job_history = [
            job for job in self._job_history
            if job.started_at > cutoff_time
        ]
    
    def get_job_statistics(self, hours: int = 1) -> Dict:
        """Get job execution statistics"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_jobs = [
            job for job in self._job_history
            if job.started_at > cutoff_time
        ]
        
        if not recent_jobs:
            return {"message": "No job data available"}
        
        # Calculate statistics
        total_jobs = len(recent_jobs)
        successful_jobs = len([job for job in recent_jobs if job.status == 'completed'])
        failed_jobs = len([job for job in recent_jobs if job.status in ['failed', 'timeout']])
        
        # Average duration for successful jobs
        successful_durations = [job.duration for job in recent_jobs if job.status == 'completed' and job.duration]
        avg_duration = sum(successful_durations) / len(successful_durations) if successful_durations else 0
        
        # Group by job name
        jobs_by_name = defaultdict(int)
        for job in recent_jobs:
            jobs_by_name[job.job_name] += 1
        
        return {
            "period_hours": hours,
            "total_jobs": total_jobs,
            "successful_jobs": successful_jobs,
            "failed_jobs": failed_jobs,
            "success_rate": successful_jobs / total_jobs if total_jobs > 0 else 0,
            "average_duration_seconds": avg_duration,
            "jobs_by_name": dict(jobs_by_name),
            "currently_running": len(self._job_executions)
        }

# Global job monitor instance
job_monitor = JobMonitor()

def monitor_job(job_name: str):
    """Decorator to monitor job execution"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            import uuid
            job_id = str(uuid.uuid4())
            
            job_monitor.job_started(job_id, job_name)
            
            try:
                result = await func(*args, **kwargs)
                job_monitor.job_completed(job_id, success=True)
                return result
            except Exception as e:
                job_monitor.job_completed(job_id, success=False, error_message=str(e))
                raise
        
        return wrapper
    return decorator