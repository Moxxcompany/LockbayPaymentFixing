"""Error handling and reliability features for withdrawal monitoring"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    reset_timeout: int = 300  # 5 minutes
    half_open_max_calls: int = 3


class CircuitBreakerState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, blocking calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker pattern for external service protection"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
        
    def should_allow_request(self) -> bool:
        """Check if request should be allowed based on circuit breaker state"""
        now = datetime.utcnow()
        
        if self.state == CircuitBreakerState.CLOSED:
            return True
            
        elif self.state == CircuitBreakerState.OPEN:
            # Check if enough time has passed to try again
            if (self.last_failure_time and 
                now - self.last_failure_time >= timedelta(seconds=self.config.reset_timeout)):
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_calls = 0
                logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
                return True
            return False
            
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return self.half_open_calls < self.config.half_open_max_calls
            
        return False
    
    def record_success(self):
        """Record successful operation"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            # Successful call in half-open state - reset to closed
            self.state = CircuitBreakerState.CLOSED
            self.failure_count = 0
            self.half_open_calls = 0
            logger.info(f"Circuit breaker {self.name} reset to CLOSED")
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def record_failure(self):
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            # Failure in half-open state - back to open
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker {self.name} back to OPEN after failure in HALF_OPEN")
        elif self.state == CircuitBreakerState.CLOSED:
            # Check if we should open the circuit
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.error(f"Circuit breaker {self.name} OPENED after {self.failure_count} failures")
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.half_open_calls += 1


class WithdrawalErrorHandler:
    """Comprehensive error handling for withdrawal operations"""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.rate_limiters: Dict[str, Dict] = {}
        
        # Initialize circuit breakers for external services
        self._initialize_circuit_breakers()
    
    def _initialize_circuit_breakers(self):
        """Initialize circuit breakers for external services"""
        services = ['kraken', 'telegram', 'email']
        
        for service in services:
            config = CircuitBreakerConfig(
                failure_threshold=5,
                reset_timeout=300,  # 5 minutes
                half_open_max_calls=3
            )
            self.circuit_breakers[service] = CircuitBreaker(service, config)
    
    async def with_retry_and_circuit_breaker(
        self,
        operation: Callable,
        service_name: str,
        retry_config: Optional[RetryConfig] = None,
        error_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute operation with retry logic and circuit breaker protection"""
        
        if retry_config is None:
            retry_config = RetryConfig()
        
        circuit_breaker = self.circuit_breakers.get(service_name)
        if not circuit_breaker:
            logger.warning(f"No circuit breaker configured for service: {service_name}")
        
        # Check circuit breaker
        if circuit_breaker and not circuit_breaker.should_allow_request():
            return {
                'success': False,
                'error': f'Circuit breaker OPEN for {service_name}',
                'error_type': 'circuit_breaker_open',
                'severity': ErrorSeverity.HIGH.value
            }
        
        # Check rate limiting
        if not self._check_rate_limit(service_name):
            return {
                'success': False,
                'error': f'Rate limit exceeded for {service_name}',
                'error_type': 'rate_limit_exceeded',
                'severity': ErrorSeverity.MEDIUM.value
            }
        
        last_exception = None
        
        for attempt in range(retry_config.max_retries + 1):
            try:
                # Execute the operation
                result = await operation()
                
                # Record success
                if circuit_breaker:
                    circuit_breaker.record_success()
                
                # Reset rate limiting on success
                self._record_successful_call(service_name)
                
                return {
                    'success': True,
                    'result': result,
                    'attempts': attempt + 1
                }
                
            except Exception as e:
                last_exception = e
                
                # Record failure
                if circuit_breaker:
                    circuit_breaker.record_failure()
                
                self._record_failed_call(service_name)
                
                # Log the error
                severity = self._determine_error_severity(e)
                self._log_error(e, service_name, attempt + 1, severity, error_context)
                
                # Don't retry on last attempt
                if attempt >= retry_config.max_retries:
                    break
                
                # Calculate delay with exponential backoff
                delay = self._calculate_retry_delay(attempt, retry_config)
                logger.info(f"Retrying {service_name} operation in {delay:.2f} seconds (attempt {attempt + 2}/{retry_config.max_retries + 1})")
                
                await asyncio.sleep(delay)
        
        # All retries exhausted
        return {
            'success': False,
            'error': str(last_exception),
            'error_type': type(last_exception).__name__,
            'severity': self._determine_error_severity(last_exception).value,
            'attempts': retry_config.max_retries + 1
        }
    
    def _calculate_retry_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay for retry with exponential backoff and jitter"""
        delay = config.base_delay * (config.exponential_base ** attempt)
        delay = min(delay, config.max_delay)
        
        if config.jitter:
            # Add random jitter (±25%)
            import random
            jitter = delay * 0.25 * (2 * random.random() - 1)
            delay += jitter
        
        return max(delay, 0.1)  # Minimum 100ms
    
    def _determine_error_severity(self, exception: Exception) -> ErrorSeverity:
        """Determine error severity based on exception type"""
        error_type = type(exception).__name__
        
        # Critical errors
        if error_type in ['DatabaseError', 'ConnectionError', 'AuthenticationError']:
            return ErrorSeverity.CRITICAL
        
        # High priority errors
        if error_type in ['TimeoutError', 'HTTPError', 'APIError']:
            return ErrorSeverity.HIGH
        
        # Medium priority errors
        if error_type in ['ValidationError', 'ValueError', 'KeyError']:
            return ErrorSeverity.MEDIUM
        
        # Default to low priority
        return ErrorSeverity.LOW
    
    def _log_error(
        self,
        exception: Exception,
        service_name: str,
        attempt: int,
        severity: ErrorSeverity,
        context: Optional[Dict] = None
    ):
        """Log error with appropriate level based on severity"""
        context_str = f" Context: {context}" if context else ""
        message = f"{service_name} error (attempt {attempt}): {str(exception)}{context_str}"
        
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(message, exc_info=True)
        elif severity == ErrorSeverity.HIGH:
            logger.error(message, exc_info=True)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(message)
        else:
            logger.info(message)
    
    def _check_rate_limit(self, service_name: str) -> bool:
        """Check if service is within rate limits"""
        now = datetime.utcnow()
        
        if service_name not in self.rate_limiters:
            self.rate_limiters[service_name] = {
                'calls': [],
                'window_seconds': 60,
                'max_calls': 60  # 60 calls per minute default
            }
        
        limiter = self.rate_limiters[service_name]
        window_start = now - timedelta(seconds=limiter['window_seconds'])
        
        # Remove old calls
        limiter['calls'] = [call_time for call_time in limiter['calls'] if call_time > window_start]
        
        # Check if we can make another call
        return len(limiter['calls']) < limiter['max_calls']
    
    def _record_successful_call(self, service_name: str):
        """Record successful API call for rate limiting"""
        if service_name in self.rate_limiters:
            self.rate_limiters[service_name]['calls'].append(datetime.utcnow())
    
    def _record_failed_call(self, service_name: str):
        """Record failed API call for rate limiting"""
        # For now, we still count failed calls towards rate limiting
        # to avoid overwhelming external services during outages
        self._record_successful_call(service_name)
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get status of all circuit breakers"""
        status = {}
        for name, breaker in self.circuit_breakers.items():
            status[name] = {
                'state': breaker.state.value,
                'failure_count': breaker.failure_count,
                'last_failure': breaker.last_failure_time.isoformat() if breaker.last_failure_time else None,
                'half_open_calls': breaker.half_open_calls if breaker.state == CircuitBreakerState.HALF_OPEN else None
            }
        return status
    
    def get_rate_limiting_status(self) -> Dict[str, Any]:
        """Get rate limiting status for all services"""
        now = datetime.utcnow()
        status = {}
        
        for service_name, limiter in self.rate_limiters.items():
            window_start = now - timedelta(seconds=limiter['window_seconds'])
            recent_calls = [call for call in limiter['calls'] if call > window_start]
            
            status[service_name] = {
                'calls_in_window': len(recent_calls),
                'max_calls': limiter['max_calls'],
                'window_seconds': limiter['window_seconds'],
                'available_calls': limiter['max_calls'] - len(recent_calls)
            }
        
        return status
    
    def reset_circuit_breaker(self, service_name: str) -> bool:
        """Manually reset a circuit breaker (for admin use)"""
        if service_name in self.circuit_breakers:
            breaker = self.circuit_breakers[service_name]
            breaker.state = CircuitBreakerState.CLOSED
            breaker.failure_count = 0
            breaker.half_open_calls = 0
            breaker.last_failure_time = None
            logger.info(f"Circuit breaker {service_name} manually reset")
            return True
        return False


# Global instance
error_handler = WithdrawalErrorHandler()