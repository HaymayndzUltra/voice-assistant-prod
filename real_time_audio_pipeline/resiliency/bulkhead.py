"""
WP-07 Bulkhead Pattern
Resource isolation and fault containment to prevent cascading failures
"""

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from queue import Full, Queue
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

class IsolationStrategy(Enum):
    """Isolation strategies for bulkheads"""
    THREAD_POOL = "thread_pool"
    SEMAPHORE = "semaphore"
    QUEUE = "queue"
    ASYNC_SEMAPHORE = "async_semaphore"

@dataclass
class BulkheadConfig:
    """Configuration for bulkhead isolation"""
    name: str
    max_concurrent: int = 10          # Maximum concurrent operations
    max_queue_size: int = 100         # Maximum queue size for pending operations
    timeout: float = 30.0             # Operation timeout
    isolation_strategy: IsolationStrategy = IsolationStrategy.SEMAPHORE
    thread_pool_size: Optional[int] = None  # Custom thread pool size

@dataclass
class OperationResult:
    """Result of a bulkhead operation"""
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    duration: float = 0.0
    queue_time: float = 0.0
    timestamp: float = field(default_factory=time.time)

class BulkheadFullException(Exception):
    """Exception raised when bulkhead capacity is exceeded"""
    def __init__(self, message: str, queue_size: int, max_size: int):
        super().__init__(message)
        self.queue_size = queue_size
        self.max_size = max_size

class BulkheadTimeoutException(Exception):
    """Exception raised when operation times out in bulkhead"""
    def __init__(self, message: str, timeout: float):
        super().__init__(message)
        self.timeout = timeout

class Bulkhead:
    """Bulkhead implementation for resource isolation"""

    def __init__(self, config: BulkheadConfig):
        self.config = config
        self.name = config.name

        # Choose isolation mechanism
        if config.isolation_strategy == IsolationStrategy.THREAD_POOL:
            self._thread_pool = ThreadPoolExecutor(
                max_workers=config.thread_pool_size or config.max_concurrent,
                thread_name_prefix=f"bulkhead-{config.name}"
            )
            self._semaphore = None
            self._async_semaphore = None
            self._queue = None

        elif config.isolation_strategy == IsolationStrategy.SEMAPHORE:
            self._semaphore = threading.Semaphore(config.max_concurrent)
            self._thread_pool = None
            self._async_semaphore = None
            self._queue = None

        elif config.isolation_strategy == IsolationStrategy.ASYNC_SEMAPHORE:
            self._async_semaphore = asyncio.Semaphore(config.max_concurrent)
            self._semaphore = None
            self._thread_pool = None
            self._queue = None

        elif config.isolation_strategy == IsolationStrategy.QUEUE:
            self._queue = Queue(maxsize=config.max_queue_size)
            self._thread_pool = ThreadPoolExecutor(
                max_workers=config.max_concurrent,
                thread_name_prefix=f"bulkhead-queue-{config.name}"
            )
            self._semaphore = None
            self._async_semaphore = None

        # Metrics
        self._metrics = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'timeout_operations': 0,
            'rejected_operations': 0,
            'concurrent_operations': 0,
            'max_concurrent_reached': 0,
            'avg_execution_time': 0.0,
            'avg_queue_time': 0.0,
            'queue_size': 0
        }

        self._execution_times: List[float] = []
        self._queue_times: List[float] = []
        self._lock = threading.RLock()

        logger.info(f"Bulkhead '{self.name}' initialized with {config.isolation_strategy.value} "
                   f"strategy, max_concurrent: {config.max_concurrent}")

    async def execute_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with bulkhead isolation"""
        start_time = time.time()
        queue_start = start_time

        try:
            if self.config.isolation_strategy == IsolationStrategy.ASYNC_SEMAPHORE:
                return await self._execute_with_async_semaphore(func, args, kwargs, queue_start)

            elif self.config.isolation_strategy == IsolationStrategy.THREAD_POOL:
                return await self._execute_with_thread_pool_async(func, args, kwargs, queue_start)

            elif self.config.isolation_strategy == IsolationStrategy.QUEUE:
                return await self._execute_with_queue_async(func, args, kwargs, queue_start)

            else:
                # Fallback to direct execution
                result = await func(*args, **kwargs)
                self._record_success(time.time() - start_time, 0)
                return result

        except Exception as e:
            self._record_failure(e)
            raise

    def execute_sync(self, func: Callable, *args, **kwargs) -> Any:
        """Execute sync function with bulkhead isolation"""
        start_time = time.time()
        queue_start = start_time

        try:
            if self.config.isolation_strategy == IsolationStrategy.SEMAPHORE:
                return self._execute_with_semaphore(func, args, kwargs, queue_start)

            elif self.config.isolation_strategy == IsolationStrategy.THREAD_POOL:
                return self._execute_with_thread_pool_sync(func, args, kwargs, queue_start)

            elif self.config.isolation_strategy == IsolationStrategy.QUEUE:
                return self._execute_with_queue_sync(func, args, kwargs, queue_start)

            else:
                # Fallback to direct execution
                result = func(*args, **kwargs)
                self._record_success(time.time() - start_time, 0)
                return result

        except Exception as e:
            self._record_failure(e)
            raise

    async def _execute_with_async_semaphore(self, func: Callable, args: tuple, kwargs: dict, queue_start: float) -> Any:
        """Execute with async semaphore isolation"""
        try:
            # Wait for semaphore with timeout
            await asyncio.wait_for(
                self._async_semaphore.acquire(),
                timeout=self.config.timeout
            )
        except asyncio.TimeoutError:
            self._record_timeout()
            raise BulkheadTimeoutException(
                f"Timeout waiting for semaphore in bulkhead '{self.name}'",
                self.config.timeout
            )

        queue_time = time.time() - queue_start
        execution_start = time.time()

        try:
            with self._lock:
                self._metrics['concurrent_operations'] += 1
                if self._metrics['concurrent_operations'] > self._metrics['max_concurrent_reached']:
                    self._metrics['max_concurrent_reached'] = self._metrics['concurrent_operations']

            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )

            execution_time = time.time() - execution_start
            self._record_success(execution_time, queue_time)

            return result

        except asyncio.TimeoutError:
            self._record_timeout()
            raise BulkheadTimeoutException(
                f"Operation timeout in bulkhead '{self.name}'",
                self.config.timeout
            )
        finally:
            with self._lock:
                self._metrics['concurrent_operations'] -= 1
            self._async_semaphore.release()

    def _execute_with_semaphore(self, func: Callable, args: tuple, kwargs: dict, queue_start: float) -> Any:
        """Execute with semaphore isolation"""
        # Try to acquire semaphore with timeout
        if not self._semaphore.acquire(timeout=self.config.timeout):
            self._record_timeout()
            raise BulkheadTimeoutException(
                f"Timeout waiting for semaphore in bulkhead '{self.name}'",
                self.config.timeout
            )

        queue_time = time.time() - queue_start
        execution_start = time.time()

        try:
            with self._lock:
                self._metrics['concurrent_operations'] += 1
                if self._metrics['concurrent_operations'] > self._metrics['max_concurrent_reached']:
                    self._metrics['max_concurrent_reached'] = self._metrics['concurrent_operations']

            result = func(*args, **kwargs)

            execution_time = time.time() - execution_start
            self._record_success(execution_time, queue_time)

            return result

        finally:
            with self._lock:
                self._metrics['concurrent_operations'] -= 1
            self._semaphore.release()

    async def _execute_with_thread_pool_async(self, func: Callable, args: tuple, kwargs: dict, queue_start: float) -> Any:
        """Execute with thread pool isolation (async wrapper)"""
        loop = asyncio.get_event_loop()

        def wrapped_func():
            return self._execute_with_thread_pool_sync(func, args, kwargs, queue_start)

        return await loop.run_in_executor(None, wrapped_func)

    def _execute_with_thread_pool_sync(self, func: Callable, args: tuple, kwargs: dict, queue_start: float) -> Any:
        """Execute with thread pool isolation"""
        future = self._thread_pool.submit(func, *args, **kwargs)

        queue_time = time.time() - queue_start
        execution_start = time.time()

        try:
            result = future.result(timeout=self.config.timeout)
            execution_time = time.time() - execution_start
            self._record_success(execution_time, queue_time)
            return result

        except Exception as e:
            if isinstance(e, TimeoutError):
                self._record_timeout()
                raise BulkheadTimeoutException(
                    f"Operation timeout in bulkhead '{self.name}'",
                    self.config.timeout
                )
            else:
                self._record_failure(e)
                raise

    async def _execute_with_queue_async(self, func: Callable, args: tuple, kwargs: dict, queue_start: float) -> Any:
        """Execute with queue isolation (async)"""
        # Submit to queue
        result_future = asyncio.Future()

        def execute_and_set_result():
            try:
                result = func(*args, **kwargs)
                if not result_future.cancelled():
                    result_future.set_result(result)
            except Exception as e:
                if not result_future.cancelled():
                    result_future.set_exception(e)

        try:
            self._queue.put_nowait(execute_and_set_result)
        except Full:
            self._record_rejection()
            raise BulkheadFullException(
                f"Queue full in bulkhead '{self.name}'",
                self._queue.qsize(),
                self.config.max_queue_size
            )

        with self._lock:
            self._metrics['queue_size'] = self._queue.qsize()

        try:
            result = await asyncio.wait_for(result_future, timeout=self.config.timeout)
            queue_time = time.time() - queue_start
            self._record_success(0, queue_time)  # Execution time tracked separately
            return result

        except asyncio.TimeoutError:
            result_future.cancel()
            self._record_timeout()
            raise BulkheadTimeoutException(
                f"Operation timeout in bulkhead '{self.name}'",
                self.config.timeout
            )

    def _execute_with_queue_sync(self, func: Callable, args: tuple, kwargs: dict, queue_start: float) -> Any:
        """Execute with queue isolation (sync)"""
        # Submit to queue
        future = self._thread_pool.submit(func, *args, **kwargs)

        with self._lock:
            self._metrics['queue_size'] = self._queue.qsize()

        try:
            result = future.result(timeout=self.config.timeout)
            queue_time = time.time() - queue_start
            self._record_success(0, queue_time)  # Execution time tracked separately
            return result

        except Exception as e:
            if isinstance(e, TimeoutError):
                self._record_timeout()
                raise BulkheadTimeoutException(
                    f"Operation timeout in bulkhead '{self.name}'",
                    self.config.timeout
                )
            else:
                self._record_failure(e)
                raise

    def _record_success(self, execution_time: float, queue_time: float):
        """Record successful operation"""
        with self._lock:
            self._metrics['total_operations'] += 1
            self._metrics['successful_operations'] += 1

            self._execution_times.append(execution_time)
            self._queue_times.append(queue_time)

            # Keep only recent times for average calculation
            if len(self._execution_times) > 1000:
                self._execution_times = self._execution_times[-1000:]
            if len(self._queue_times) > 1000:
                self._queue_times = self._queue_times[-1000:]

            # Update averages
            if self._execution_times:
                self._metrics['avg_execution_time'] = sum(self._execution_times) / len(self._execution_times)
            if self._queue_times:
                self._metrics['avg_queue_time'] = sum(self._queue_times) / len(self._queue_times)

    def _record_failure(self, error: Exception):
        """Record failed operation"""
        with self._lock:
            self._metrics['total_operations'] += 1
            self._metrics['failed_operations'] += 1

    def _record_timeout(self):
        """Record timeout operation"""
        with self._lock:
            self._metrics['total_operations'] += 1
            self._metrics['timeout_operations'] += 1

    def _record_rejection(self):
        """Record rejected operation"""
        with self._lock:
            self._metrics['rejected_operations'] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get bulkhead metrics"""
        with self._lock:
            metrics = self._metrics.copy()
            metrics.update({
                'name': self.name,
                'isolation_strategy': self.config.isolation_strategy.value,
                'max_concurrent': self.config.max_concurrent,
                'max_queue_size': self.config.max_queue_size,
                'current_queue_size': self._queue.qsize() if self._queue else 0,
                'success_rate': (
                    self._metrics['successful_operations'] / self._metrics['total_operations']
                    if self._metrics['total_operations'] > 0 else 0
                ),
                'timeout_rate': (
                    self._metrics['timeout_operations'] / self._metrics['total_operations']
                    if self._metrics['total_operations'] > 0 else 0
                ),
                'rejection_rate': (
                    self._metrics['rejected_operations'] / (self._metrics['total_operations'] + self._metrics['rejected_operations'])
                    if (self._metrics['total_operations'] + self._metrics['rejected_operations']) > 0 else 0
                )
            })
            return metrics

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of bulkhead"""
        metrics = self.get_metrics()

        # Determine health based on metrics
        success_rate = metrics['success_rate']
        timeout_rate = metrics['timeout_rate']
        rejection_rate = metrics['rejection_rate']

        if success_rate > 0.9 and timeout_rate < 0.05 and rejection_rate < 0.01:
            health = "healthy"
        elif success_rate > 0.7 and timeout_rate < 0.15 and rejection_rate < 0.05:
            health = "degraded"
        else:
            health = "unhealthy"

        return {
            'name': self.name,
            'health': health,
            'success_rate': success_rate,
            'timeout_rate': timeout_rate,
            'rejection_rate': rejection_rate,
            'concurrent_operations': metrics['concurrent_operations'],
            'queue_size': metrics['current_queue_size']
        }

    def close(self):
        """Close bulkhead and cleanup resources"""
        if self._thread_pool:
            self._thread_pool.shutdown(wait=True)

        logger.info(f"Bulkhead '{self.name}' closed")

class BulkheadRegistry:
    """Registry for managing multiple bulkheads"""

    def __init__(self):
        self._bulkheads: Dict[str, Bulkhead] = {}
        self._lock = threading.RLock()

    def get_or_create(self, config: BulkheadConfig) -> Bulkhead:
        """Get existing bulkhead or create new one"""
        with self._lock:
            if config.name not in self._bulkheads:
                self._bulkheads[config.name] = Bulkhead(config)
                logger.info(f"Created bulkhead: {config.name}")

            return self._bulkheads[config.name]

    def get(self, name: str) -> Optional[Bulkhead]:
        """Get bulkhead by name"""
        return self._bulkheads.get(name)

    def list_bulkheads(self) -> List[str]:
        """List all bulkhead names"""
        return list(self._bulkheads.keys())

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all bulkheads"""
        return {name: bulkhead.get_metrics() for name, bulkhead in self._bulkheads.items()}

    def get_all_health_status(self) -> Dict[str, Dict[str, Any]]:
        """Get health status for all bulkheads"""
        return {name: bulkhead.get_health_status() for name, bulkhead in self._bulkheads.items()}

    def close_all(self):
        """Close all bulkheads"""
        with self._lock:
            for bulkhead in self._bulkheads.values():
                bulkhead.close()
            self._bulkheads.clear()
            logger.info("Closed all bulkheads")

# Global bulkhead registry
_bulkhead_registry: Optional[BulkheadRegistry] = None

def get_bulkhead_registry() -> BulkheadRegistry:
    """Get global bulkhead registry"""
    global _bulkhead_registry
    if _bulkhead_registry is None:
        _bulkhead_registry = BulkheadRegistry()
    return _bulkhead_registry

def get_bulkhead(name: str,
                max_concurrent: int = 10,
                max_queue_size: int = 100,
                timeout: float = 30.0,
                isolation_strategy: IsolationStrategy = IsolationStrategy.SEMAPHORE) -> Bulkhead:
    """Get or create bulkhead by name"""
    config = BulkheadConfig(
        name=name,
        max_concurrent=max_concurrent,
        max_queue_size=max_queue_size,
        timeout=timeout,
        isolation_strategy=isolation_strategy
    )

    registry = get_bulkhead_registry()
    return registry.get_or_create(config)

# Convenience decorators
def bulkhead(name: Optional[str] = None,
            max_concurrent: int = 10,
            max_queue_size: int = 100,
            timeout: float = 30.0,
            isolation_strategy: IsolationStrategy = IsolationStrategy.SEMAPHORE):
    """Decorator for applying bulkhead isolation to functions"""

    def decorator(func):
        bulkhead_name = name or f"{func.__module__}.{func.__name__}"
        bulkhead_instance = get_bulkhead(
            bulkhead_name, max_concurrent, max_queue_size, timeout, isolation_strategy
        )

        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                return await bulkhead_instance.execute_async(func, *args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                return bulkhead_instance.execute_sync(func, *args, **kwargs)
            return sync_wrapper

    return decorator
