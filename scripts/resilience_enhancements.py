#!/usr/bin/env python3
"""
Resilience Enhancements for Phase 3
Adds retry logic and circuit breaker patterns
"""

import time
import logging
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger('Resilience')

class CircuitState(Enum):
    """TODO: Add description for CircuitState."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    expected_exception: type = Exception

class CircuitBreaker:
    """Circuit breaker implementation"""

    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time = None
        self.success_count = 0

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker {self.name} entering HALF_OPEN state")
            else:
                raise Exception(f"Circuit breaker {self.name} is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.config.expected_exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if we should try to reset the circuit"""
        return (self.last_failure_time and
                time.time() - self.last_failure_time > self.config.recovery_timeout)

    def _on_success(self):
        """Handle successful call"""
        self.failures = 0
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 3:  # Require 3 successes to fully close
                self.state = CircuitState.CLOSED
                self.success_count = 0
                logger.info(f"Circuit breaker {self.name} is now CLOSED")

    def _on_failure(self):
        """Handle failed call"""
        self.failures += 1
        self.last_failure_time = time.time()
        self.success_count = 0

        if self.failures >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker {self.name} is now OPEN after {self.failures} failures")

class RetryConfig:
    """Configuration for retry logic"""
    def __init__(self, max_attempts: int = 3,
                 initial_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 jitter: bool = True):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

def retry_with_backoff(config: RetryConfig = RetryConfig()):
    """Decorator for retry with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt == config.max_attempts - 1:
                        logger.error(f"All {config.max_attempts} attempts failed for {func.__name__}")
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(
                        config.initial_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )

                    # Add jitter to prevent thundering herd
                    if config.jitter:
                        import random
                        delay *= (0.5 + random.random())

                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}, "
                                 f"retrying in {delay:.1f}s: {e}")
                    time.sleep(delay)

            raise last_exception
        return wrapper
    return decorator

class ResilientAgentLoader:
    """Enhanced agent loader with resilience features"""

    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_config = RetryConfig(max_attempts=3, initial_delay=2.0)

    def get_circuit_breaker(self, agent_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for agent"""
        if agent_name not in self.circuit_breakers:
            config = CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=60
            )
            self.circuit_breakers[agent_name] = CircuitBreaker(agent_name, config)
        return self.circuit_breakers[agent_name]

    @retry_with_backoff(RetryConfig(max_attempts=3))
    def load_agent_with_retry(self, agent_name: str, agent_config: Dict) -> bool:
        """Load agent with retry logic"""
        circuit_breaker = self.get_circuit_breaker(agent_name)

        def _load():
            # Simulate agent loading (would call actual loader)
            logger.info(f"Attempting to load {agent_name}")
            # This would be the actual loading logic
            return True

        return circuit_breaker.call(_load)

    def health_check_with_circuit_breaker(self, agent_name: str, health_url: str) -> bool:
        """Health check with circuit breaker protection"""
        circuit_breaker = self.get_circuit_breaker(f"{agent_name}_health")

        @retry_with_backoff(RetryConfig(max_attempts=5, initial_delay=1.0))
        def _check_health():
            # This would be actual health check
            logger.debug(f"Checking health of {agent_name} at {health_url}")
            return True

        try:
            return circuit_breaker.call(_check_health)
        except Exception as e:
            logger.error(f"Health check failed for {agent_name}: {e}")
            return False

class SelfHealingManager:
    """Manages self-healing behaviors"""

    def __init__(self):
        self.failed_agents: Dict[str, Dict] = {}
        self.restart_attempts: Dict[str, int] = {}
        self.max_restart_attempts = 3
        self.restart_delay = 30  # seconds

    def register_failure(self, agent_name: str, error: Exception):
        """Register an agent failure"""
        now = datetime.now()

        if agent_name not in self.failed_agents:
            self.failed_agents[agent_name] = {
                'first_failure': now,
                'last_failure': now,
                'failure_count': 1,
                'errors': [str(error)]
            }
        else:
            self.failed_agents[agent_name]['last_failure'] = now
            self.failed_agents[agent_name]['failure_count'] += 1
            self.failed_agents[agent_name]['errors'].append(str(error))

        logger.warning(f"Agent {agent_name} failed: {error}")

    def should_restart_agent(self, agent_name: str) -> bool:
        """Determine if agent should be restarted"""
        if agent_name not in self.failed_agents:
            return False

        attempts = self.restart_attempts.get(agent_name, 0)
        if attempts >= self.max_restart_attempts:
            logger.error(f"Agent {agent_name} exceeded max restart attempts")
            return False

        last_failure = self.failed_agents[agent_name]['last_failure']
        time_since_failure = (datetime.now() - last_failure).total_seconds()

        if time_since_failure > self.restart_delay:
            return True

        return False

    def record_restart(self, agent_name: str):
        """Record that an agent was restarted"""
        self.restart_attempts[agent_name] = self.restart_attempts.get(agent_name, 0) + 1
        logger.info(f"Restarting {agent_name} (attempt {self.restart_attempts[agent_name]})")

    def reset_agent_status(self, agent_name: str):
        """Reset agent status after successful recovery"""
        if agent_name in self.failed_agents:
            del self.failed_agents[agent_name]
        if agent_name in self.restart_attempts:
            del self.restart_attempts[agent_name]
        logger.info(f"Agent {agent_name} recovered successfully")

# Example integration with LazyLoader
def enhance_lazy_loader():
    """Example of how to integrate with LazyLoader"""

    # This would be added to LazyLoader class
    example_code = '''
    def __init__(self):
        # ... existing init code ...
        self.resilient_loader = ResilientAgentLoader()
        self.self_healing = SelfHealingManager()

    def _start_agent(self, agent_name: str, agent_config: Dict) -> bool:
        """Start agent with resilience features"""
        try:
            # Use resilient loader
            success = self.resilient_loader.load_agent_with_retry(
                agent_name, agent_config
            )

            if success:
                # Reset any failure status
                self.self_healing.reset_agent_status(agent_name)
                return True
            else:
                raise Exception("Agent failed to start")

        except Exception as e:
            # Register failure for self-healing
            self.self_healing.register_failure(agent_name, e)

            # Check if we should attempt restart
            if self.self_healing.should_restart_agent(agent_name):
                self.self_healing.record_restart(agent_name)
                # Queue for restart
                self._queue_agent_load(agent_name, "self_healing")

            return False
    '''

    return example_code

if __name__ == "__main__":
    # Test circuit breaker
    print("Testing Circuit Breaker...")

    cb_config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=5)
    cb = CircuitBreaker("test_service", cb_config)

    def failing_function():
        raise Exception("Service unavailable")

    # Test failures
    for i in range(5):
        try:
            cb.call(failing_function)
        except Exception as e:
            print(f"Call {i+1} failed: {e}")

    print(f"Circuit state: {cb.state.value}")

    # Test retry decorator
    print("\nTesting Retry Logic...")

    attempt_count = 0

    @retry_with_backoff(RetryConfig(max_attempts=3, initial_delay=0.5))
    def sometimes_failing():
        global attempt_count
        attempt_count += 1
        print(f"Attempt {attempt_count}")
        if attempt_count < 3:
            raise Exception("Temporary failure")
        return "Success!"

    try:
        result = sometimes_failing()
        print(f"Result: {result}")
    except Exception as e:
        print(f"Failed after retries: {e}")

    print("\nResilience enhancements ready for integration!")
