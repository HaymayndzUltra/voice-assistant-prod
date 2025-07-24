"""
WP-07 Retry Mechanism
Advanced retry strategies with exponential backoff, jitter, and circuit breaker integration
"""

import asyncio
import time
import random
import logging
from typing import Dict, Any, Optional, Callable, Union, List, Type
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class RetryStrategy(Enum):
    """Retry strategy types"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    FIBONACCI = "fibonacci"

class JitterType(Enum):
    """Jitter types for retry delays"""
    NONE = "none"
    UNIFORM = "uniform"
    EXPONENTIAL = "exponential"
    DECORRELATED = "decorrelated"

@dataclass
class RetryConfig:
    """Configuration for retry mechanism"""
    max_attempts: int = 3
    base_delay: float = 1.0          # Base delay in seconds
    max_delay: float = 60.0          # Maximum delay between retries
    exponential_base: float = 2.0    # Base for exponential backoff
    jitter_type: JitterType = JitterType.UNIFORM
    jitter_max: float = 0.1          # Maximum jitter factor (0.0 to 1.0)
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    
    # Exceptions to retry on
    retryable_exceptions: List[Type[Exception]] = field(default_factory=lambda: [
        ConnectionError, TimeoutError, OSError
    ])
    
    # Exceptions to never retry
    non_retryable_exceptions: List[Type[Exception]] = field(default_factory=lambda: [
        ValueError, TypeError, KeyError
    ])
    
    # Custom retry condition function
    retry_condition: Optional[Callable[[Exception], bool]] = None

@dataclass
class RetryAttempt:
    """Information about a retry attempt"""
    attempt_number: int
    delay: float
    exception: Optional[Exception] = None
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0

class RetryExhaustedException(Exception):
    """Exception raised when all retry attempts are exhausted"""
    def __init__(self, message: str, attempts: List[RetryAttempt], last_exception: Exception):
        super().__init__(message)
        self.attempts = attempts
        self.last_exception = last_exception

class RetryDelayCalculator:
    """Calculate retry delays based on different strategies"""
    
    @staticmethod
    def exponential_backoff(attempt: int, base_delay: float, exponential_base: float, max_delay: float) -> float:
        """Calculate exponential backoff delay"""
        delay = base_delay * (exponential_base ** (attempt - 1))
        return min(delay, max_delay)
    
    @staticmethod
    def linear_backoff(attempt: int, base_delay: float, max_delay: float) -> float:
        """Calculate linear backoff delay"""
        delay = base_delay * attempt
        return min(delay, max_delay)
    
    @staticmethod
    def fixed_delay(attempt: int, base_delay: float) -> float:
        """Calculate fixed delay"""
        return base_delay
    
    @staticmethod
    def fibonacci(attempt: int, base_delay: float, max_delay: float) -> float:
        """Calculate Fibonacci sequence delay"""
        def fib(n):
            if n <= 1:
                return 1
            a, b = 1, 1
            for _ in range(2, n + 1):
                a, b = b, a + b
            return b
        
        delay = base_delay * fib(attempt)
        return min(delay, max_delay)
    
    @staticmethod
    def apply_jitter(delay: float, jitter_type: JitterType, jitter_max: float) -> float:
        """Apply jitter to delay"""
        if jitter_type == JitterType.NONE:
            return delay
        
        elif jitter_type == JitterType.UNIFORM:
            # Add uniform random jitter
            jitter = random.uniform(-jitter_max, jitter_max) * delay
            return max(0, delay + jitter)
        
        elif jitter_type == JitterType.EXPONENTIAL:
            # Exponential jitter
            jitter = random.expovariate(1.0 / (jitter_max * delay))
            return delay + jitter
        
        elif jitter_type == JitterType.DECORRELATED:
            # Decorrelated jitter
            jitter = random.uniform(0, jitter_max * delay)
            return delay + jitter
        
        return delay

class RetryManager:
    """Manages retry logic with various strategies"""
    
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
        self._delay_calculator = RetryDelayCalculator()
        
        # Metrics
        self._metrics = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'total_retry_attempts': 0,
            'avg_attempts_per_operation': 0.0,
            'avg_retry_delay': 0.0
        }
        
        logger.info(f"RetryManager initialized with max_attempts: {self.config.max_attempts}")
    
    def _should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if exception should be retried"""
        if attempt >= self.config.max_attempts:
            return False
        
        # Check custom retry condition first
        if self.config.retry_condition:
            return self.config.retry_condition(exception)
        
        # Check non-retryable exceptions
        for exc_type in self.config.non_retryable_exceptions:
            if isinstance(exception, exc_type):
                return False
        
        # Check retryable exceptions
        for exc_type in self.config.retryable_exceptions:
            if isinstance(exception, exc_type):
                return True
        
        # Default: retry for common network/temporary errors
        retryable_types = (ConnectionError, TimeoutError, OSError)
        return isinstance(exception, retryable_types)
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt"""
        if self.config.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self._delay_calculator.exponential_backoff(
                attempt, self.config.base_delay, 
                self.config.exponential_base, self.config.max_delay
            )
        elif self.config.retry_strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self._delay_calculator.linear_backoff(
                attempt, self.config.base_delay, self.config.max_delay
            )
        elif self.config.retry_strategy == RetryStrategy.FIXED_DELAY:
            delay = self._delay_calculator.fixed_delay(attempt, self.config.base_delay)
        elif self.config.retry_strategy == RetryStrategy.FIBONACCI:
            delay = self._delay_calculator.fibonacci(
                attempt, self.config.base_delay, self.config.max_delay
            )
        else:
            delay = self.config.base_delay
        
        # Apply jitter
        return self._delay_calculator.apply_jitter(
            delay, self.config.jitter_type, self.config.jitter_max
        )
    
    async def execute_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with retry logic"""
        attempts: List[RetryAttempt] = []
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Success - update metrics and return
                duration = time.time() - start_time
                self._update_success_metrics(attempts)
                
                if attempts:  # Log if there were previous failures
                    logger.info(f"Operation succeeded on attempt {attempt} after {len(attempts)} retries")
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                last_exception = e
                
                # Record attempt
                attempt_info = RetryAttempt(
                    attempt_number=attempt,
                    delay=0.0,  # Will be set below
                    exception=e,
                    duration=duration
                )
                attempts.append(attempt_info)
                
                # Check if should retry
                if not self._should_retry(e, attempt):
                    logger.warning(f"Not retrying {type(e).__name__} after attempt {attempt}")
                    break
                
                if attempt < self.config.max_attempts:
                    # Calculate and apply delay
                    delay = self._calculate_delay(attempt)
                    attempt_info.delay = delay
                    
                    logger.warning(f"Attempt {attempt} failed with {type(e).__name__}, "
                                 f"retrying in {delay:.2f}s: {str(e)}")
                    
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.config.max_attempts} attempts failed")
        
        # All attempts exhausted
        self._update_failure_metrics(attempts)
        
        raise RetryExhaustedException(
            f"All {self.config.max_attempts} retry attempts failed",
            attempts,
            last_exception
        )
    
    def execute_sync(self, func: Callable, *args, **kwargs) -> Any:
        """Execute sync function with retry logic"""
        attempts: List[RetryAttempt] = []
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # Success - update metrics and return
                duration = time.time() - start_time
                self._update_success_metrics(attempts)
                
                if attempts:  # Log if there were previous failures
                    logger.info(f"Operation succeeded on attempt {attempt} after {len(attempts)} retries")
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                last_exception = e
                
                # Record attempt
                attempt_info = RetryAttempt(
                    attempt_number=attempt,
                    delay=0.0,  # Will be set below
                    exception=e,
                    duration=duration
                )
                attempts.append(attempt_info)
                
                # Check if should retry
                if not self._should_retry(e, attempt):
                    logger.warning(f"Not retrying {type(e).__name__} after attempt {attempt}")
                    break
                
                if attempt < self.config.max_attempts:
                    # Calculate and apply delay
                    delay = self._calculate_delay(attempt)
                    attempt_info.delay = delay
                    
                    logger.warning(f"Attempt {attempt} failed with {type(e).__name__}, "
                                 f"retrying in {delay:.2f}s: {str(e)}")
                    
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.config.max_attempts} attempts failed")
        
        # All attempts exhausted
        self._update_failure_metrics(attempts)
        
        raise RetryExhaustedException(
            f"All {self.config.max_attempts} retry attempts failed",
            attempts,
            last_exception
        )
    
    def _update_success_metrics(self, attempts: List[RetryAttempt]):
        """Update metrics for successful operation"""
        self._metrics['total_operations'] += 1
        self._metrics['successful_operations'] += 1
        self._metrics['total_retry_attempts'] += len(attempts)
        
        # Update averages
        if self._metrics['total_operations'] > 0:
            self._metrics['avg_attempts_per_operation'] = (
                (self._metrics['successful_operations'] + self._metrics['failed_operations'] + 
                 self._metrics['total_retry_attempts']) / self._metrics['total_operations']
            )
        
        if attempts:
            avg_delay = sum(a.delay for a in attempts) / len(attempts)
            # Running average of delays
            current_avg = self._metrics['avg_retry_delay']
            self._metrics['avg_retry_delay'] = (current_avg + avg_delay) / 2
    
    def _update_failure_metrics(self, attempts: List[RetryAttempt]):
        """Update metrics for failed operation"""
        self._metrics['total_operations'] += 1
        self._metrics['failed_operations'] += 1
        self._metrics['total_retry_attempts'] += len(attempts)
        
        # Update averages
        if self._metrics['total_operations'] > 0:
            self._metrics['avg_attempts_per_operation'] = (
                (self._metrics['successful_operations'] + self._metrics['failed_operations'] + 
                 self._metrics['total_retry_attempts']) / self._metrics['total_operations']
            )
        
        if attempts:
            avg_delay = sum(a.delay for a in attempts) / len(attempts)
            # Running average of delays
            current_avg = self._metrics['avg_retry_delay']
            self._metrics['avg_retry_delay'] = (current_avg + avg_delay) / 2
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get retry manager metrics"""
        metrics = self._metrics.copy()
        metrics.update({
            'config': {
                'max_attempts': self.config.max_attempts,
                'base_delay': self.config.base_delay,
                'max_delay': self.config.max_delay,
                'retry_strategy': self.config.retry_strategy.value,
                'jitter_type': self.config.jitter_type.value
            }
        })
        return metrics

# Global retry manager
_default_retry_manager: Optional[RetryManager] = None

def get_retry_manager(config: RetryConfig = None) -> RetryManager:
    """Get default retry manager"""
    global _default_retry_manager
    if _default_retry_manager is None or config is not None:
        _default_retry_manager = RetryManager(config)
    return _default_retry_manager

# Convenience decorators
def retry(max_attempts: int = 3, 
          base_delay: float = 1.0,
          max_delay: float = 60.0,
          strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
          jitter: JitterType = JitterType.UNIFORM,
          retryable_exceptions: List[Type[Exception]] = None):
    """Decorator for applying retry logic to functions"""
    
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        retry_strategy=strategy,
        jitter_type=jitter,
        retryable_exceptions=retryable_exceptions or [ConnectionError, TimeoutError, OSError]
    )
    
    retry_manager = RetryManager(config)
    
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                return await retry_manager.execute_async(func, *args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                return retry_manager.execute_sync(func, *args, **kwargs)
            return sync_wrapper
    
    return decorator

# Integration with circuit breaker
def retry_with_circuit_breaker(retry_config: RetryConfig = None, 
                              circuit_breaker_name: str = None):
    """Decorator that combines retry logic with circuit breaker"""
    from .circuit_breaker import get_circuit_breaker, CircuitBreakerException
    
    retry_manager = RetryManager(retry_config or RetryConfig())
    
    def decorator(func):
        breaker_name = circuit_breaker_name or f"{func.__module__}.{func.__name__}"
        circuit_breaker = get_circuit_breaker(breaker_name)
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                async def protected_call():
                    return await circuit_breaker.call_async(func, *args, **kwargs)
                
                try:
                    return await retry_manager.execute_async(protected_call)
                except CircuitBreakerException:
                    # Don't retry if circuit breaker is open
                    raise
                
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                def protected_call():
                    return circuit_breaker.call_sync(func, *args, **kwargs)
                
                try:
                    return retry_manager.execute_sync(protected_call)
                except CircuitBreakerException:
                    # Don't retry if circuit breaker is open
                    raise
                
            return sync_wrapper
    
    return decorator 