"""
Telemetry and metrics implementation for Memory Fusion Hub.

This module provides:
- Prometheus metrics collection
- Performance monitoring
- Health metrics
- Custom histogram and counter definitions
"""

import time
import logging
from typing import Dict, Any, Optional
import asyncio
from contextlib import asynccontextmanager
from functools import wraps

from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, generate_latest
from prometheus_client import CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)


class Telemetry:
    """
    Prometheus metrics and telemetry collection for Memory Fusion Hub.
    
    Provides counters, histograms, and gauges for monitoring service
    performance, cache efficiency, and operational health.
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Initialize telemetry collection.
        
        Args:
            registry: Optional custom Prometheus registry
        """
        self.registry = registry or CollectorRegistry()
        
        # Service information
        self.service_info = Info(
            'mfh_service_info',
            'Memory Fusion Hub service information',
            registry=self.registry
        )
        self.service_info.info({
            'version': '1.0.0',
            'component': 'memory_fusion_hub'
        })
        
        # Request metrics
        self.requests_total = Counter(
            'mfh_requests_total',
            'Total number of requests processed',
            ['operation', 'status'],
            registry=self.registry
        )
        
        self.request_duration = Histogram(
            'mfh_request_duration_seconds',
            'Request duration in seconds',
            ['operation'],
            buckets=[0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0],
            registry=self.registry
        )
        
        # Cache metrics
        self.cache_hits = Counter(
            'mfh_cache_hits_total',
            'Total number of cache hits',
            registry=self.registry
        )
        
        self.cache_misses = Counter(
            'mfh_cache_misses_total',
            'Total number of cache misses',
            registry=self.registry
        )
        
        self.cache_operations = Counter(
            'mfh_cache_operations_total',
            'Total cache operations',
            ['operation'],  # get, put, evict
            registry=self.registry
        )
        
        # Repository metrics
        self.repository_operations = Counter(
            'mfh_repository_operations_total',
            'Total repository operations',
            ['operation', 'repository_type'],  # get, put, delete + sqlite, postgres
            registry=self.registry
        )
        
        self.repository_duration = Histogram(
            'mfh_repository_duration_seconds',
            'Repository operation duration in seconds',
            ['operation', 'repository_type'],
            buckets=[0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5],
            registry=self.registry
        )
        
        # Event log metrics
        self.events_published = Counter(
            'mfh_events_published_total',
            'Total events published to log',
            ['event_type'],
            registry=self.registry
        )
        
        self.event_log_size = Gauge(
            'mfh_event_log_size',
            'Current size of event log',
            registry=self.registry
        )
        
        # Circuit breaker metrics
        self.circuit_breaker_state = Gauge(
            'mfh_circuit_breaker_state',
            'Circuit breaker state (0=closed, 1=open, 2=half-open)',
            ['component'],
            registry=self.registry
        )
        
        self.circuit_breaker_failures = Counter(
            'mfh_circuit_breaker_failures_total',
            'Circuit breaker failure count',
            ['component'],
            registry=self.registry
        )
        
        # Memory and resource metrics
        self.active_connections = Gauge(
            'mfh_active_connections',
            'Number of active connections',
            ['connection_type'],  # redis, postgres, zmq, grpc
            registry=self.registry
        )
        
        self.memory_items_count = Gauge(
            'mfh_memory_items_count',
            'Number of memory items stored',
            ['item_type'],  # memory_item, session_data, knowledge_record
            registry=self.registry
        )
        
        # Performance metrics
        self.concurrent_requests = Gauge(
            'mfh_concurrent_requests',
            'Number of concurrent requests being processed',
            registry=self.registry
        )
        
        self.error_rate = Counter(
            'mfh_errors_total',
            'Total number of errors',
            ['error_type', 'component'],
            registry=self.registry
        )
        
        # Health metrics
        self.health_check_status = Gauge(
            'mfh_health_check_status',
            'Health check status (1=healthy, 0=unhealthy)',
            ['component'],
            registry=self.registry
        )
        
        self.last_health_check = Gauge(
            'mfh_last_health_check_timestamp',
            'Timestamp of last health check',
            ['component'],
            registry=self.registry
        )
        
    def record_request(self, operation: str, status: str = 'success') -> None:
        """
        Record a request metric.
        
        Args:
            operation: The operation performed (get, put, delete, etc.)
            status: Status of the operation (success, error, timeout)
        """
        self.requests_total.labels(operation=operation, status=status).inc()
    
    @asynccontextmanager
    async def time_operation(self, operation: str):
        """
        Context manager to time an operation.
        
        Args:
            operation: Name of the operation being timed
        """
        start_time = time.time()
        self.concurrent_requests.inc()
        
        try:
            yield
            self.record_request(operation, 'success')
        except Exception as _e:
            self.record_request(operation, 'error')
            self.record_error(str(type(_e).__name__), 'operation')
            raise
        finally:
            self.request_duration.labels(operation=operation).observe(time.time() - start_time)
            self.concurrent_requests.dec()
    
    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        self.cache_hits.inc()
        self.cache_operations.labels(operation='get').inc()
    
    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        self.cache_misses.inc()
        self.cache_operations.labels(operation='get').inc()
    
    def record_cache_put(self) -> None:
        """Record a cache put operation."""
        self.cache_operations.labels(operation='put').inc()
    
    def record_cache_evict(self) -> None:
        """Record a cache eviction."""
        self.cache_operations.labels(operation='evict').inc()
    
    def record_repository_operation(self, operation: str, repository_type: str, duration: float) -> None:
        """
        Record a repository operation.
        
        Args:
            operation: Operation type (get, put, delete)
            repository_type: Repository type (sqlite, postgres)
            duration: Operation duration in seconds
        """
        self.repository_operations.labels(
            operation=operation, 
            repository_type=repository_type
        ).inc()
        self.repository_duration.labels(
            operation=operation, 
            repository_type=repository_type
        ).observe(duration)
    
    def record_event_published(self, event_type: str) -> None:
        """
        Record an event publication.
        
        Args:
            event_type: Type of event (CREATE, UPDATE, DELETE, READ)
        """
        self.events_published.labels(event_type=event_type).inc()
    
    def update_event_log_size(self, size: int) -> None:
        """
        Update the current event log size.
        
        Args:
            size: Current number of events in the log
        """
        self.event_log_size.set(size)
    
    def record_circuit_breaker_state(self, component: str, state: int) -> None:
        """
        Record circuit breaker state.
        
        Args:
            component: Component name (repository, cache, etc.)
            state: State (0=closed, 1=open, 2=half-open)
        """
        self.circuit_breaker_state.labels(component=component).set(state)
    
    def record_circuit_breaker_failure(self, component: str) -> None:
        """
        Record a circuit breaker failure.
        
        Args:
            component: Component that failed
        """
        self.circuit_breaker_failures.labels(component=component).inc()
    
    def update_active_connections(self, connection_type: str, count: int) -> None:
        """
        Update active connection count.
        
        Args:
            connection_type: Type of connection (redis, postgres, zmq, grpc)
            count: Current connection count
        """
        self.active_connections.labels(connection_type=connection_type).set(count)
    
    def update_memory_items_count(self, item_type: str, count: int) -> None:
        """
        Update memory items count.
        
        Args:
            item_type: Type of memory item
            count: Current count
        """
        self.memory_items_count.labels(item_type=item_type).set(count)
    
    def record_error(self, error_type: str, component: str) -> None:
        """
        Record an error occurrence.
        
        Args:
            error_type: Type of error
            component: Component where error occurred
        """
        self.error_rate.labels(error_type=error_type, component=component).inc()
    
    def update_health_status(self, component: str, is_healthy: bool) -> None:
        """
        Update health check status.
        
        Args:
            component: Component name
            is_healthy: Whether the component is healthy
        """
        status = 1 if is_healthy else 0
        self.health_check_status.labels(component=component).set(status)
        self.last_health_check.labels(component=component).set(time.time())
    
    def get_cache_hit_rate(self) -> float:
        """
        Calculate cache hit rate.
        
        Returns:
            Cache hit rate as percentage (0.0 to 1.0)
        """
        try:
            hits = self.cache_hits._value.get()
            misses = self.cache_misses._value.get()
            total = hits + misses
            
            if total == 0:
                return 0.0
            
            return hits / total
        except Exception:
            return 0.0
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of key metrics.
        
        Returns:
            Dictionary with metric summaries
        """
        try:
            cache_hit_rate = self.get_cache_hit_rate()
            
            return {
                'requests_total': self.requests_total._value.get(),
                'cache_hits': self.cache_hits._value.get(),
                'cache_misses': self.cache_misses._value.get(),
                'cache_hit_rate': cache_hit_rate,
                'concurrent_requests': self.concurrent_requests._value.get(),
                'errors_total': self.error_rate._value.get(),
                'events_published': self.events_published._value.get(),
                'event_log_size': self.event_log_size._value.get(),
            }
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {}
    
    def export_metrics(self) -> str:
        """
        Export metrics in Prometheus format.
        
        Returns:
            Metrics in Prometheus text format
        """
        try:
            return generate_latest(self.registry).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
            return ""
    
    def get_content_type(self) -> str:
        """
        Get the content type for Prometheus metrics.
        
        Returns:
            Content type string
        """
        return CONTENT_TYPE_LATEST


def timed_operation(operation_name: str):
    """
    Decorator to automatically time and record operations.
    
    Args:
        operation_name: Name of the operation for metrics
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Try to find telemetry instance in args/kwargs or use global
            telemetry = None
            for arg in args:
                if hasattr(arg, 'metrics') and isinstance(arg.metrics, Telemetry):
                    telemetry = arg.metrics
                    break
            
            if telemetry:
                async with telemetry.time_operation(operation_name):
                    return await func(*args, **kwargs)
            else:
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For synchronous functions
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                # Record success if telemetry available
                return result
            except Exception:
                # Record error if telemetry available
                raise
            finally:
                _ = time.time() - start_time
                # Record duration if telemetry available
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# Global telemetry instance (can be overridden)
global_telemetry = Telemetry()


def get_telemetry() -> Telemetry:
    """Get the global telemetry instance."""
    return global_telemetry


def set_telemetry(telemetry: Telemetry) -> None:
    """Set the global telemetry instance."""
    global global_telemetry
    global_telemetry = telemetry