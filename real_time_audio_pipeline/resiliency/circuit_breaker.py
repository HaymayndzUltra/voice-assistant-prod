"""
WP-07 Circuit Breaker Implementation
Fault tolerance and resiliency patterns for agent communication
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failing, requests blocked
    HALF_OPEN = "half_open" # Testing if service recovered

class FailureType(Enum):
    """Types of failures to track"""
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    HTTP_ERROR = "http_error"
    VALIDATION_ERROR = "validation_error"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5          # Failures before opening
    success_threshold: int = 3          # Successes to close from half-open
    timeout_duration: float = 60.0     # Time to wait before half-open (seconds)
    request_timeout: float = 30.0      # Individual request timeout
    monitor_window: float = 300.0      # Rolling window for failure tracking
    half_open_max_calls: int = 10      # Max calls allowed in half-open state

@dataclass
class CallResult:
    """Result of a circuit breaker call"""
    success: bool
    response: Any = None
    error: Optional[Exception] = None
    failure_type: Optional[FailureType] = None
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)

class CircuitBreakerException(Exception):
    """Exception raised when circuit breaker is open"""
    def __init__(self, message: str, state: CircuitState, last_failure: Optional[Exception] = None):
        super().__init__(message)
        self.state = state
        self.last_failure = last_failure

class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance"""

    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()

        # State management
        self._state = CircuitState.CLOSED
        self._last_failure_time = 0.0
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0

        # Failure tracking
        self._recent_failures: List[CallResult] = []
        self._lock = threading.RLock()

        # Metrics
        self._metrics = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'circuit_opened_count': 0,
            'circuit_half_opened_count': 0,
            'circuit_closed_count': 0,
            'avg_response_time': 0.0,
            'failure_rate': 0.0
        }

        # Response times for average calculation
        self._response_times: List[float] = []

        logger.info(f"Circuit breaker '{name}' initialized with threshold {config.failure_threshold}")

    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)"""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)"""
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)"""
        return self._state == CircuitState.HALF_OPEN

    def _should_attempt_call(self) -> bool:
        """Determine if call should be attempted based on circuit state"""
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            elif self._state == CircuitState.OPEN:
                # Check if timeout period has elapsed
                if time.time() - self._last_failure_time >= self.config.timeout_duration:
                    self._transition_to_half_open()
                    return True
                return False

            elif self._state == CircuitState.HALF_OPEN:
                # Allow limited calls in half-open state
                return self._half_open_calls < self.config.half_open_max_calls

            return False

    def _transition_to_open(self, failure_result: CallResult):
        """Transition circuit to open state"""
        with self._lock:
            if self._state != CircuitState.OPEN:
                self._state
                self._state = CircuitState.OPEN
                self._last_failure_time = time.time()
                self._metrics['circuit_opened_count'] += 1

                logger.warning(f"Circuit breaker '{self.name}' opened due to {failure_result.failure_type} "
                             f"(failure count: {self._failure_count})")

    def _transition_to_half_open(self):
        """Transition circuit to half-open state"""
        with self._lock:
            if self._state == CircuitState.OPEN:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                self._success_count = 0
                self._metrics['circuit_half_opened_count'] += 1

                logger.info(f"Circuit breaker '{self.name}' transitioned to half-open")

    def _transition_to_closed(self):
        """Transition circuit to closed state"""
        with self._lock:
            if self._state != CircuitState.CLOSED:
                self._state
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                self._half_open_calls = 0
                self._metrics['circuit_closed_count'] += 1

                logger.info(f"Circuit breaker '{self.name}' closed (recovered)")

    def _record_success(self, result: CallResult):
        """Record successful call"""
        with self._lock:
            self._metrics['total_calls'] += 1
            self._metrics['successful_calls'] += 1
            self._response_times.append(result.duration)

            # Keep only recent response times
            if len(self._response_times) > 1000:
                self._response_times = self._response_times[-1000:]

            # Update average response time
            self._metrics['avg_response_time'] = sum(self._response_times) / len(self._response_times)

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._transition_to_closed()

            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = max(0, self._failure_count - 1)

    def _record_failure(self, result: CallResult):
        """Record failed call"""
        with self._lock:
            self._metrics['total_calls'] += 1
            self._metrics['failed_calls'] += 1

            # Add to recent failures list
            self._recent_failures.append(result)

            # Clean old failures outside monitoring window
            cutoff_time = time.time() - self.config.monitor_window
            self._recent_failures = [
                f for f in self._recent_failures
                if f.timestamp > cutoff_time
            ]

            # Update failure rate
            total_recent = len([f for f in self._recent_failures if f.timestamp > cutoff_time])
            if total_recent > 0:
                failed_recent = len([f for f in self._recent_failures if not f.success and f.timestamp > cutoff_time])
                self._metrics['failure_rate'] = failed_recent / total_recent

            self._failure_count += 1

            # Check if should open circuit
            if self._state == CircuitState.CLOSED and self._failure_count >= self.config.failure_threshold:
                self._transition_to_open(result)

            elif self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open state opens the circuit
                self._transition_to_open(result)

    def _classify_failure(self, error: Exception) -> FailureType:
        """Classify the type of failure"""
        error_type = type(error).__name__.lower()

        if 'timeout' in error_type or 'timeouterror' in error_type:
            return FailureType.TIMEOUT
        elif 'connection' in error_type or 'connect' in error_type:
            return FailureType.CONNECTION_ERROR
        elif 'http' in error_type or 'status' in error_type:
            return FailureType.HTTP_ERROR
        elif 'validation' in error_type or 'schema' in error_type:
            return FailureType.VALIDATION_ERROR
        elif 'rate' in error_type or 'limit' in error_type:
            return FailureType.RATE_LIMIT
        else:
            return FailureType.UNKNOWN

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection"""
        if not self._should_attempt_call():
            raise CircuitBreakerException(
                f"Circuit breaker '{self.name}' is {self._state.value}",
                self._state
            )

        start_time = time.time()

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.request_timeout
            )

            duration = time.time() - start_time
            call_result = CallResult(
                success=True,
                response=result,
                duration=duration
            )

            self._record_success(call_result)

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1

            return result

        except Exception as e:
            duration = time.time() - start_time
            failure_type = self._classify_failure(e)

            call_result = CallResult(
                success=False,
                error=e,
                failure_type=failure_type,
                duration=duration
            )

            self._record_failure(call_result)

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1

            raise

    def call_sync(self, func: Callable, *args, **kwargs) -> Any:
        """Execute sync function with circuit breaker protection"""
        if not self._should_attempt_call():
            raise CircuitBreakerException(
                f"Circuit breaker '{self.name}' is {self._state.value}",
                self._state
            )

        start_time = time.time()

        try:
            result = func(*args, **kwargs)

            duration = time.time() - start_time
            call_result = CallResult(
                success=True,
                response=result,
                duration=duration
            )

            self._record_success(call_result)

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1

            return result

        except Exception as e:
            duration = time.time() - start_time
            failure_type = self._classify_failure(e)

            call_result = CallResult(
                success=False,
                error=e,
                failure_type=failure_type,
                duration=duration
            )

            self._record_failure(call_result)

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1

            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        with self._lock:
            metrics = self._metrics.copy()
            metrics.update({
                'name': self.name,
                'state': self._state.value,
                'failure_count': self._failure_count,
                'success_count': self._success_count,
                'recent_failures': len(self._recent_failures),
                'last_failure_time': self._last_failure_time,
                'time_until_half_open': max(0, self.config.timeout_duration - (time.time() - self._last_failure_time)) if self._state == CircuitState.OPEN else 0,
                'config': {
                    'failure_threshold': self.config.failure_threshold,
                    'success_threshold': self.config.success_threshold,
                    'timeout_duration': self.config.timeout_duration,
                    'request_timeout': self.config.request_timeout
                }
            })
            return metrics

    def reset(self):
        """Reset circuit breaker to closed state"""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
            self._recent_failures.clear()
            self._last_failure_time = 0.0

            logger.info(f"Circuit breaker '{self.name}' manually reset")

class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers"""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()

    def get_or_create(self, name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        """Get existing circuit breaker or create new one"""
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name, config)
                logger.info(f"Created circuit breaker: {name}")

            return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name"""
        return self._breakers.get(name)

    def list_breakers(self) -> List[str]:
        """List all circuit breaker names"""
        return list(self._breakers.keys())

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers"""
        return {name: breaker.get_metrics() for name, breaker in self._breakers.items()}

    def reset_all(self):
        """Reset all circuit breakers"""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()
            logger.info("Reset all circuit breakers")

    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary"""
        total_breakers = len(self._breakers)
        open_breakers = sum(1 for b in self._breakers.values() if b.is_open)
        half_open_breakers = sum(1 for b in self._breakers.values() if b.is_half_open)

        return {
            'total_breakers': total_breakers,
            'healthy_breakers': total_breakers - open_breakers - half_open_breakers,
            'open_breakers': open_breakers,
            'half_open_breakers': half_open_breakers,
            'overall_health': 'healthy' if open_breakers == 0 else 'degraded' if open_breakers < total_breakers else 'unhealthy'
        }

# Global circuit breaker registry
_circuit_breaker_registry: Optional[CircuitBreakerRegistry] = None

def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get global circuit breaker registry"""
    global _circuit_breaker_registry
    if _circuit_breaker_registry is None:
        _circuit_breaker_registry = CircuitBreakerRegistry()
    return _circuit_breaker_registry

def get_circuit_breaker(name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
    """Get or create circuit breaker by name"""
    registry = get_circuit_breaker_registry()
    return registry.get_or_create(name, config)

# Convenience decorators
def circuit_breaker(name: Optional[str] = None, config: CircuitBreakerConfig = None):
    """Decorator for applying circuit breaker to functions"""
    def decorator(func):
        breaker_name = name or f"{func.__module__}.{func.__name__}"
        breaker = get_circuit_breaker(breaker_name, config)

        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                return await breaker.call_async(func, *args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                return breaker.call_sync(func, *args, **kwargs)
            return sync_wrapper

    return decorator
