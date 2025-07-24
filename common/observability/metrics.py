"""
WP-09 Metrics Collection & Monitoring
Real-time metrics collection, aggregation, and alerting for comprehensive observability
"""

import asyncio
import time
import threading
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import statistics
import json

class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    SET = "set"

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class MetricValue:
    """Single metric value with metadata"""
    name: str
    value: Union[int, float]
    metric_type: MetricType
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "timestamp": self.timestamp,
            "tags": self.tags
        }

@dataclass
class Alert:
    """Metric alert definition"""
    name: str
    metric_name: str
    condition: str  # e.g., "> 100", "< 0.5"
    level: AlertLevel
    message: str
    cooldown: float = 300.0  # 5 minutes
    last_triggered: float = 0.0
    
    def should_trigger(self, value: float) -> bool:
        """Check if alert should trigger"""
        # Simple condition evaluation
        try:
            return eval(f"{value} {self.condition}")
        except:
            return False
    
    def can_trigger(self) -> bool:
        """Check if alert is out of cooldown"""
        return time.time() - self.last_triggered > self.cooldown

class MetricCollector:
    """Base metric collector interface"""
    
    def __init__(self, name: str):
        self.name = name
        self._tags = {}
    
    def add_tags(self, **tags):
        """Add default tags to all metrics"""
        self._tags.update(tags)
    
    def _create_metric(self, name: str, value: Union[int, float], 
                      metric_type: MetricType, **tags) -> MetricValue:
        """Create metric value with default tags"""
        all_tags = {**self._tags, **tags}
        return MetricValue(
            name=f"{self.name}.{name}",
            value=value,
            metric_type=metric_type,
            tags=all_tags
        )

class Counter(MetricCollector):
    """Counter metric - monotonically increasing"""
    
    def __init__(self, name: str):
        super().__init__(name)
        self._value = 0.0
        self._lock = threading.RLock()
    
    def increment(self, amount: float = 1.0, **tags) -> MetricValue:
        """Increment counter"""
        with self._lock:
            self._value += amount
            return self._create_metric("count", self._value, MetricType.COUNTER, **tags)
    
    def get_value(self) -> float:
        """Get current counter value"""
        with self._lock:
            return self._value
    
    def reset(self):
        """Reset counter to zero"""
        with self._lock:
            self._value = 0.0

class Gauge(MetricCollector):
    """Gauge metric - arbitrary value that can go up or down"""
    
    def __init__(self, name: str):
        super().__init__(name)
        self._value = 0.0
        self._lock = threading.RLock()
    
    def set(self, value: float, **tags) -> MetricValue:
        """Set gauge value"""
        with self._lock:
            self._value = value
            return self._create_metric("value", self._value, MetricType.GAUGE, **tags)
    
    def increment(self, amount: float = 1.0, **tags) -> MetricValue:
        """Increment gauge"""
        with self._lock:
            self._value += amount
            return self._create_metric("value", self._value, MetricType.GAUGE, **tags)
    
    def decrement(self, amount: float = 1.0, **tags) -> MetricValue:
        """Decrement gauge"""
        return self.increment(-amount, **tags)
    
    def get_value(self) -> float:
        """Get current gauge value"""
        with self._lock:
            return self._value

class Histogram(MetricCollector):
    """Histogram metric - distribution of values"""
    
    def __init__(self, name: str, buckets: List[float] = None):
        super().__init__(name)
        self.buckets = buckets or [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, float('inf')]
        
        self._values = deque(maxlen=10000)  # Keep last 10k values
        self._bucket_counts = defaultdict(int)
        self._count = 0
        self._sum = 0.0
        self._lock = threading.RLock()
    
    def observe(self, value: float, **tags) -> List[MetricValue]:
        """Record observation"""
        with self._lock:
            self._values.append(value)
            self._count += 1
            self._sum += value
            
            # Update bucket counts
            for bucket in self.buckets:
                if value <= bucket:
                    self._bucket_counts[bucket] += 1
            
            # Return multiple metrics
            metrics = []
            
            # Count metric
            metrics.append(self._create_metric("count", self._count, MetricType.HISTOGRAM, **tags))
            
            # Sum metric
            metrics.append(self._create_metric("sum", self._sum, MetricType.HISTOGRAM, **tags))
            
            # Bucket metrics
            for bucket, count in self._bucket_counts.items():
                bucket_tags = {**tags, "le": str(bucket)}
                metrics.append(self._create_metric("bucket", count, MetricType.HISTOGRAM, **bucket_tags))
            
            return metrics
    
    def get_statistics(self) -> Dict[str, float]:
        """Get histogram statistics"""
        with self._lock:
            if not self._values:
                return {}
            
            values = list(self._values)
            return {
                "count": len(values),
                "sum": sum(values),
                "min": min(values),
                "max": max(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "p95": statistics.quantiles(values, n=20)[18] if len(values) >= 20 else max(values),
                "p99": statistics.quantiles(values, n=100)[98] if len(values) >= 100 else max(values)
            }

class Timer(MetricCollector):
    """Timer metric - measures duration"""
    
    def __init__(self, name: str):
        super().__init__(name)
        self._histogram = Histogram(f"{name}_duration")
        self._active_timers = {}
        self._lock = threading.RLock()
    
    def start(self, timer_id: str = None) -> str:
        """Start timer"""
        timer_id = timer_id or str(time.time())
        with self._lock:
            self._active_timers[timer_id] = time.time()
        return timer_id
    
    def stop(self, timer_id: str, **tags) -> List[MetricValue]:
        """Stop timer and record duration"""
        with self._lock:
            if timer_id not in self._active_timers:
                return []
            
            start_time = self._active_timers.pop(timer_id)
            duration = time.time() - start_time
            
            return self._histogram.observe(duration, **tags)
    
    def time_context(self, **tags):
        """Context manager for timing"""
        return TimerContext(self, **tags)
    
    def get_statistics(self) -> Dict[str, float]:
        """Get timer statistics"""
        return self._histogram.get_statistics()

class TimerContext:
    """Context manager for timer"""
    
    def __init__(self, timer: Timer, **tags):
        self.timer = timer
        self.tags = tags
        self.timer_id = None
    
    def __enter__(self):
        self.timer_id = self.timer.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.timer_id:
            self.timer.stop(self.timer_id, **self.tags)

class MetricsRegistry:
    """Central registry for metrics"""
    
    def __init__(self):
        self._metrics: Dict[str, MetricCollector] = {}
        self._alerts: Dict[str, Alert] = {}
        self._subscribers: List[Callable[[MetricValue], None]] = []
        self._lock = threading.RLock()
        
        # Built-in system metrics
        self._setup_system_metrics()
    
    def _setup_system_metrics(self):
        """Setup built-in system metrics"""
        self.counter("system.requests")
        self.counter("system.errors")
        self.gauge("system.active_connections")
        self.timer("system.response_time")
        self.histogram("system.memory_usage")
    
    def counter(self, name: str) -> Counter:
        """Get or create counter"""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Counter(name)
            metric = self._metrics[name]
            if not isinstance(metric, Counter):
                raise ValueError(f"Metric {name} is not a counter")
            return metric
    
    def gauge(self, name: str) -> Gauge:
        """Get or create gauge"""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Gauge(name)
            metric = self._metrics[name]
            if not isinstance(metric, Gauge):
                raise ValueError(f"Metric {name} is not a gauge")
            return metric
    
    def histogram(self, name: str, buckets: List[float] = None) -> Histogram:
        """Get or create histogram"""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Histogram(name, buckets)
            metric = self._metrics[name]
            if not isinstance(metric, Histogram):
                raise ValueError(f"Metric {name} is not a histogram")
            return metric
    
    def timer(self, name: str) -> Timer:
        """Get or create timer"""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Timer(name)
            metric = self._metrics[name]
            if not isinstance(metric, Timer):
                raise ValueError(f"Metric {name} is not a timer")
            return metric
    
    def record_metric(self, metric: MetricValue):
        """Record metric value and check alerts"""
        # Notify subscribers
        for subscriber in self._subscribers:
            try:
                subscriber(metric)
            except Exception as e:
                print(f"Metric subscriber error: {e}")
        
        # Check alerts
        self._check_alerts(metric)
    
    def add_alert(self, alert: Alert):
        """Add metric alert"""
        with self._lock:
            self._alerts[alert.name] = alert
    
    def remove_alert(self, alert_name: str):
        """Remove metric alert"""
        with self._lock:
            self._alerts.pop(alert_name, None)
    
    def _check_alerts(self, metric: MetricValue):
        """Check if metric triggers any alerts"""
        for alert in self._alerts.values():
            if (alert.metric_name == metric.name and 
                alert.can_trigger() and 
                alert.should_trigger(metric.value)):
                
                alert.last_triggered = time.time()
                self._trigger_alert(alert, metric)
    
    def _trigger_alert(self, alert: Alert, metric: MetricValue):
        """Trigger alert"""
        print(f"ALERT [{alert.level.value.upper()}] {alert.name}: {alert.message} (Value: {metric.value})")
        # In production, send to alerting system
    
    def subscribe(self, callback: Callable[[MetricValue], None]):
        """Subscribe to metric updates"""
        self._subscribers.append(callback)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metric values"""
        result = {}
        
        with self._lock:
            for name, metric in self._metrics.items():
                if isinstance(metric, Counter):
                    result[name] = {"type": "counter", "value": metric.get_value()}
                elif isinstance(metric, Gauge):
                    result[name] = {"type": "gauge", "value": metric.get_value()}
                elif isinstance(metric, (Histogram, Timer)):
                    result[name] = {"type": metric.__class__.__name__.lower(), "stats": metric.get_statistics()}
        
        return result

class MetricsCollector:
    """Automatic metrics collection for common patterns"""
    
    def __init__(self, registry: MetricsRegistry):
        self.registry = registry
    
    def collect_request_metrics(self, endpoint: str, method: str, status_code: int, duration: float):
        """Collect HTTP request metrics"""
        tags = {"endpoint": endpoint, "method": method, "status": str(status_code)}
        
        # Request counter
        self.registry.counter("http.requests").increment(**tags)
        
        # Response time
        timer = self.registry.timer("http.response_time")
        timer._histogram.observe(duration, **tags)
        
        # Error counter
        if status_code >= 400:
            self.registry.counter("http.errors").increment(**tags)
    
    def collect_database_metrics(self, operation: str, table: str, duration: float, success: bool):
        """Collect database operation metrics"""
        tags = {"operation": operation, "table": table, "success": str(success)}
        
        # Query counter
        self.registry.counter("db.queries").increment(**tags)
        
        # Query duration
        timer = self.registry.timer("db.query_time")
        timer._histogram.observe(duration, **tags)
        
        # Error counter
        if not success:
            self.registry.counter("db.errors").increment(**tags)
    
    def collect_agent_metrics(self, agent_id: str, operation: str, duration: float, success: bool):
        """Collect agent operation metrics"""
        tags = {"agent_id": agent_id, "operation": operation, "success": str(success)}
        
        # Operation counter
        self.registry.counter("agent.operations").increment(**tags)
        
        # Operation duration
        timer = self.registry.timer("agent.operation_time")
        timer._histogram.observe(duration, **tags)
        
        # Error counter
        if not success:
            self.registry.counter("agent.errors").increment(**tags)

class MetricsExporter:
    """Export metrics to external systems"""
    
    def __init__(self, registry: MetricsRegistry):
        self.registry = registry
        self._export_tasks = []
    
    def start_prometheus_exporter(self, host: str = "0.0.0.0", port: int = 8080):
        """Start Prometheus metrics exporter"""
        task = asyncio.create_task(self._prometheus_server(host, port))
        self._export_tasks.append(task)
        return task
    
    async def _prometheus_server(self, host: str, port: int):
        """Simple Prometheus metrics server"""
        try:
            from aiohttp import web
            
            async def metrics_handler(request):
                metrics = self.registry.get_all_metrics()
                prometheus_format = self._convert_to_prometheus(metrics)
                return web.Response(text=prometheus_format, content_type="text/plain")
            
            app = web.Application()
            app.router.add_get("/metrics", metrics_handler)
            
            runner = web.AppRunner(app)
            await runner.setup()
            
            site = web.TCPSite(runner, host, port)
            await site.start()
            
            print(f"Prometheus metrics server started on {host}:{port}/metrics")
            
            # Keep running
            while True:
                await asyncio.sleep(3600)  # Sleep for 1 hour
                
        except ImportError:
            print("aiohttp not available for Prometheus exporter")
        except Exception as e:
            print(f"Prometheus exporter error: {e}")
    
    def _convert_to_prometheus(self, metrics: Dict[str, Any]) -> str:
        """Convert metrics to Prometheus format"""
        lines = []
        
        for name, data in metrics.items():
            metric_type = data["type"]
            
            if metric_type == "counter":
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name} {data['value']}")
            
            elif metric_type == "gauge":
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name} {data['value']}")
            
            elif metric_type in ["histogram", "timer"]:
                stats = data["stats"]
                lines.append(f"# TYPE {name} histogram")
                
                for stat_name, stat_value in stats.items():
                    lines.append(f"{name}_{stat_name} {stat_value}")
        
        return "\n".join(lines) + "\n"
    
    async def export_to_file(self, file_path: str, interval: float = 60.0):
        """Export metrics to file periodically"""
        while True:
            try:
                metrics = self.registry.get_all_metrics()
                
                with open(file_path, 'w') as f:
                    json.dump({
                        "timestamp": time.time(),
                        "metrics": metrics
                    }, f, indent=2)
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                print(f"File export error: {e}")
                await asyncio.sleep(interval)

# Global metrics registry
_metrics_registry: Optional[MetricsRegistry] = None

def get_metrics_registry() -> MetricsRegistry:
    """Get global metrics registry"""
    global _metrics_registry
    if _metrics_registry is None:
        _metrics_registry = MetricsRegistry()
    return _metrics_registry

# Convenience functions
def counter(name: str) -> Counter:
    """Get counter metric"""
    return get_metrics_registry().counter(name)

def gauge(name: str) -> Gauge:
    """Get gauge metric"""
    return get_metrics_registry().gauge(name)

def histogram(name: str, buckets: List[float] = None) -> Histogram:
    """Get histogram metric"""
    return get_metrics_registry().histogram(name, buckets)

def timer(name: str) -> Timer:
    """Get timer metric"""
    return get_metrics_registry().timer(name)

def time_operation(name: str, **tags):
    """Context manager for timing operations"""
    return timer(name).time_context(**tags)

# Decorators for automatic metrics
def measure_time(metric_name: str = None, tags: Dict[str, str] = None):
    """Decorator to measure function execution time"""
    
    def decorator(func):
        import functools
        
        name = metric_name or f"function.{func.__module__}.{func.__name__}"
        func_tags = tags or {}
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            timer_metric = timer(name)
            
            with timer_metric.time_context(**func_tags):
                return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            timer_metric = timer(name)
            
            with timer_metric.time_context(**func_tags):
                return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def count_calls(metric_name: str = None, tags: Dict[str, str] = None):
    """Decorator to count function calls"""
    
    def decorator(func):
        import functools
        
        name = metric_name or f"calls.{func.__module__}.{func.__name__}"
        func_tags = tags or {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            counter_metric = counter(name)
            counter_metric.increment(**func_tags)
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator

def measure_errors(metric_name: str = None, tags: Dict[str, str] = None):
    """Decorator to measure function errors"""
    
    def decorator(func):
        import functools
        
        name = metric_name or f"errors.{func.__module__}.{func.__name__}"
        func_tags = tags or {}
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_counter = counter(name)
                error_tags = {**func_tags, "error_type": type(e).__name__}
                error_counter.increment(**error_tags)
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_counter = counter(name)
                error_tags = {**func_tags, "error_type": type(e).__name__}
                error_counter.increment(**error_tags)
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator 