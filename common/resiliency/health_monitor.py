"""
WP-07 Health Monitoring System
Comprehensive health monitoring and metrics collection for resiliency patterns
"""

import asyncio
import time
import threading
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class MetricType(Enum):
    """Types of metrics to track"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

@dataclass
class HealthCheck:
    """Health check configuration"""
    name: str
    check_function: Callable[[], bool]
    timeout: float = 10.0
    interval: float = 30.0
    critical: bool = False  # If True, failure marks entire system unhealthy
    description: str = ""

@dataclass
class HealthCheckResult:
    """Result of a health check"""
    name: str
    status: HealthStatus
    message: str = ""
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0
    error: Optional[Exception] = None

@dataclass
class MetricValue:
    """A metric value with timestamp"""
    value: Union[int, float]
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)

class HealthMonitor:
    """Central health monitoring system"""
    
    def __init__(self, name: str = "system"):
        self.name = name
        self._health_checks: Dict[str, HealthCheck] = {}
        self._check_results: Dict[str, HealthCheckResult] = {}
        self._check_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Metrics storage
        self._metrics: Dict[str, Dict[str, Any]] = {
            'counters': defaultdict(int),
            'gauges': defaultdict(float),
            'histograms': defaultdict(list),
            'timers': defaultdict(list)
        }
        
        # System-wide health tracking
        self._overall_status = HealthStatus.UNKNOWN
        self._status_history = deque(maxlen=1000)
        
        # Monitoring control
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = threading.RLock()
        
        # Health thresholds
        self._thresholds = {
            'unhealthy_threshold': 0.5,    # % of critical checks failing
            'degraded_threshold': 0.2,     # % of any checks failing
            'recovery_time': 60.0,         # Time to recover from unhealthy
            'check_timeout': 10.0          # Default check timeout
        }
        
        logger.info(f"HealthMonitor '{name}' initialized")
    
    def register_health_check(self, health_check: HealthCheck):
        """Register a health check"""
        with self._lock:
            self._health_checks[health_check.name] = health_check
            self._check_results[health_check.name] = HealthCheckResult(
                name=health_check.name,
                status=HealthStatus.UNKNOWN,
                message="Not yet checked"
            )
            logger.info(f"Registered health check: {health_check.name}")
    
    def unregister_health_check(self, name: str):
        """Unregister a health check"""
        with self._lock:
            if name in self._health_checks:
                del self._health_checks[name]
                del self._check_results[name]
                if name in self._check_history:
                    del self._check_history[name]
                logger.info(f"Unregistered health check: {name}")
    
    async def run_health_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check"""
        if name not in self._health_checks:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message="Health check not found"
            )
        
        health_check = self._health_checks[name]
        start_time = time.time()
        
        try:
            # Run check with timeout
            result = await asyncio.wait_for(
                asyncio.create_task(self._run_check_async(health_check)),
                timeout=health_check.timeout
            )
            
            duration = time.time() - start_time
            
            if result:
                status = HealthStatus.HEALTHY
                message = "Check passed"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Check failed"
            
            check_result = HealthCheckResult(
                name=name,
                status=status,
                message=message,
                duration=duration
            )
            
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            check_result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check timed out after {health_check.timeout}s",
                duration=duration
            )
        
        except Exception as e:
            duration = time.time() - start_time
            check_result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed with error: {str(e)}",
                duration=duration,
                error=e
            )
        
        # Store result
        with self._lock:
            self._check_results[name] = check_result
            self._check_history[name].append(check_result)
        
        # Update metrics
        self.increment_counter('health_checks_total', labels={'check': name, 'status': check_result.status.value})
        self.record_timer('health_check_duration', check_result.duration, labels={'check': name})
        
        return check_result
    
    async def _run_check_async(self, health_check: HealthCheck) -> bool:
        """Run health check function asynchronously"""
        if asyncio.iscoroutinefunction(health_check.check_function):
            return await health_check.check_function()
        else:
            # Run sync function in executor
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, health_check.check_function)
    
    async def run_all_health_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks"""
        tasks = []
        
        for name in self._health_checks:
            task = asyncio.create_task(self.run_health_check(name))
            tasks.append((name, task))
        
        results = {}
        for name, task in tasks:
            try:
                result = await task
                results[name] = result
            except Exception as e:
                results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Unexpected error: {str(e)}",
                    error=e
                )
        
        # Update overall health
        self._update_overall_health(results)
        
        return results
    
    def _update_overall_health(self, results: Dict[str, HealthCheckResult]):
        """Update overall system health based on check results"""
        if not results:
            self._overall_status = HealthStatus.UNKNOWN
            return
        
        critical_checks = [r for r in results.values() if self._health_checks[r.name].critical]
        all_checks = list(results.values())
        
        # Count failures
        critical_failures = sum(1 for r in critical_checks if r.status == HealthStatus.UNHEALTHY)
        total_failures = sum(1 for r in all_checks if r.status == HealthStatus.UNHEALTHY)
        
        # Determine status
        if critical_checks and critical_failures > 0:
            # Any critical check failure = unhealthy
            self._overall_status = HealthStatus.UNHEALTHY
        elif len(all_checks) > 0:
            failure_rate = total_failures / len(all_checks)
            
            if failure_rate >= self._thresholds['unhealthy_threshold']:
                self._overall_status = HealthStatus.UNHEALTHY
            elif failure_rate >= self._thresholds['degraded_threshold']:
                self._overall_status = HealthStatus.DEGRADED
            else:
                self._overall_status = HealthStatus.HEALTHY
        else:
            self._overall_status = HealthStatus.UNKNOWN
        
        # Record status change
        self._status_history.append({
            'status': self._overall_status,
            'timestamp': time.time(),
            'critical_failures': critical_failures,
            'total_failures': total_failures,
            'total_checks': len(all_checks)
        })
        
        # Update metrics
        self.set_gauge('overall_health_status', 
                      {'healthy': 1, 'degraded': 0.5, 'unhealthy': 0, 'unknown': -1}[self._overall_status.value])
        self.set_gauge('total_health_checks', len(all_checks))
        self.set_gauge('failed_health_checks', total_failures)
        self.set_gauge('critical_failures', critical_failures)
    
    async def start_monitoring(self, interval: float = 30.0):
        """Start continuous health monitoring"""
        if self._running:
            logger.warning("Health monitoring already running")
            return
        
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop(interval))
        logger.info(f"Started health monitoring with {interval}s interval")
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        self._running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped health monitoring")
    
    async def _monitoring_loop(self, interval: float):
        """Main monitoring loop"""
        while self._running:
            try:
                await self.run_all_health_checks()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval)
    
    # Metrics methods
    def increment_counter(self, name: str, value: int = 1, labels: Dict[str, str] = None):
        """Increment a counter metric"""
        with self._lock:
            key = self._metric_key(name, labels)
            self._metrics['counters'][key] += value
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric value"""
        with self._lock:
            key = self._metric_key(name, labels)
            self._metrics['gauges'][key] = value
    
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram value"""
        with self._lock:
            key = self._metric_key(name, labels)
            self._metrics['histograms'][key].append(MetricValue(value, labels=labels or {}))
            
            # Keep only recent values
            if len(self._metrics['histograms'][key]) > 1000:
                self._metrics['histograms'][key] = self._metrics['histograms'][key][-1000:]
    
    def record_timer(self, name: str, duration: float, labels: Dict[str, str] = None):
        """Record a timer value (duration in seconds)"""
        with self._lock:
            key = self._metric_key(name, labels)
            self._metrics['timers'][key].append(MetricValue(duration, labels=labels or {}))
            
            # Keep only recent values
            if len(self._metrics['timers'][key]) > 1000:
                self._metrics['timers'][key] = self._metrics['timers'][key][-1000:]
    
    def _metric_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Create metric key with labels"""
        if not labels:
            return name
        
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        with self._lock:
            return {
                'name': self.name,
                'overall_status': self._overall_status.value,
                'timestamp': time.time(),
                'checks': {name: {
                    'status': result.status.value,
                    'message': result.message,
                    'last_check': result.timestamp,
                    'duration': result.duration,
                    'critical': self._health_checks[name].critical
                } for name, result in self._check_results.items()},
                'summary': {
                    'total_checks': len(self._check_results),
                    'healthy_checks': sum(1 for r in self._check_results.values() if r.status == HealthStatus.HEALTHY),
                    'degraded_checks': sum(1 for r in self._check_results.values() if r.status == HealthStatus.DEGRADED),
                    'unhealthy_checks': sum(1 for r in self._check_results.values() if r.status == HealthStatus.UNHEALTHY),
                    'unknown_checks': sum(1 for r in self._check_results.values() if r.status == HealthStatus.UNKNOWN)
                }
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics"""
        with self._lock:
            # Process histograms and timers for statistics
            processed_histograms = {}
            for key, values in self._metrics['histograms'].items():
                if values:
                    vals = [v.value for v in values]
                    processed_histograms[key] = {
                        'count': len(vals),
                        'sum': sum(vals),
                        'min': min(vals),
                        'max': max(vals),
                        'avg': sum(vals) / len(vals),
                        'p50': self._percentile(vals, 0.5),
                        'p95': self._percentile(vals, 0.95),
                        'p99': self._percentile(vals, 0.99)
                    }
            
            processed_timers = {}
            for key, values in self._metrics['timers'].items():
                if values:
                    vals = [v.value for v in values]
                    processed_timers[key] = {
                        'count': len(vals),
                        'sum': sum(vals),
                        'min': min(vals),
                        'max': max(vals),
                        'avg': sum(vals) / len(vals),
                        'p50': self._percentile(vals, 0.5),
                        'p95': self._percentile(vals, 0.95),
                        'p99': self._percentile(vals, 0.99)
                    }
            
            return {
                'counters': dict(self._metrics['counters']),
                'gauges': dict(self._metrics['gauges']),
                'histograms': processed_histograms,
                'timers': processed_timers
            }
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(percentile * (len(sorted_values) - 1))
        return sorted_values[index]
    
    def get_health_history(self, check_name: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get health check history"""
        if check_name:
            if check_name in self._check_history:
                history = list(self._check_history[check_name])[-limit:]
                return [
                    {
                        'timestamp': r.timestamp,
                        'status': r.status.value,
                        'message': r.message,
                        'duration': r.duration
                    }
                    for r in history
                ]
            return []
        else:
            # Return overall status history
            return list(self._status_history)[-limit:]

# Integration with resiliency components
class ResiliencyHealthMonitor(HealthMonitor):
    """Health monitor with built-in resiliency pattern monitoring"""
    
    def __init__(self, name: str = "resiliency"):
        super().__init__(name)
        self._auto_register_resiliency_checks()
    
    def _auto_register_resiliency_checks(self):
        """Auto-register health checks for resiliency components"""
        
        # Circuit breaker health check
        self.register_health_check(HealthCheck(
            name="circuit_breakers",
            check_function=self._check_circuit_breakers,
            timeout=5.0,
            interval=30.0,
            critical=True,
            description="Check circuit breaker health status"
        ))
        
        # Bulkhead health check
        self.register_health_check(HealthCheck(
            name="bulkheads",
            check_function=self._check_bulkheads,
            timeout=5.0,
            interval=30.0,
            critical=False,
            description="Check bulkhead isolation health"
        ))
        
        # Connection pool health check
        self.register_health_check(HealthCheck(
            name="connection_pools",
            check_function=self._check_connection_pools,
            timeout=10.0,
            interval=60.0,
            critical=False,
            description="Check connection pool health"
        ))
    
    def _check_circuit_breakers(self) -> bool:
        """Check health of all circuit breakers"""
        try:
            from .circuit_breaker import get_circuit_breaker_registry
            
            registry = get_circuit_breaker_registry()
            health_summary = registry.get_health_summary()
            
            # Consider healthy if < 50% of breakers are open
            open_ratio = health_summary['open_breakers'] / max(1, health_summary['total_breakers'])
            return open_ratio < 0.5
            
        except Exception as e:
            logger.warning(f"Error checking circuit breakers: {e}")
            return False
    
    def _check_bulkheads(self) -> bool:
        """Check health of all bulkheads"""
        try:
            from .bulkhead import get_bulkhead_registry
            
            registry = get_bulkhead_registry()
            health_statuses = registry.get_all_health_status()
            
            if not health_statuses:
                return True  # No bulkheads = healthy
            
            unhealthy_count = sum(1 for h in health_statuses.values() if h['health'] == 'unhealthy')
            return unhealthy_count == 0
            
        except Exception as e:
            logger.warning(f"Error checking bulkheads: {e}")
            return False
    
    def _check_connection_pools(self) -> bool:
        """Check health of connection pools"""
        try:
            # Check Redis pool
            from common.pools.redis_pool import get_redis_pool
            redis_pool = get_redis_pool()
            redis_stats = redis_pool.get_stats()
            
            # Consider healthy if error rate < 10%
            operations = redis_stats.get('operations', 0)
            errors = redis_stats.get('errors', 0)
            
            if operations > 0:
                error_rate = errors / operations
                return error_rate < 0.1
            
            return True  # No operations = healthy
            
        except Exception as e:
            logger.warning(f"Error checking connection pools: {e}")
            return False

# Global health monitor instance
_health_monitor: Optional[ResiliencyHealthMonitor] = None

def get_health_monitor() -> ResiliencyHealthMonitor:
    """Get global health monitor instance"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = ResiliencyHealthMonitor()
    return _health_monitor 