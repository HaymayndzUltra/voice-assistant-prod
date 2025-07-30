"""
Metrics Client

A flexible metrics collection client that gracefully handles the absence of 
Prometheus or other metrics collection systems. Provides a consistent API
regardless of whether the metrics backend is available.
"""

import os
import time
import logging
from typing import Any
from contextlib import contextmanager

# Configure logging
logger = logging.getLogger(__name__)

# Check if Prometheus client is available
PROMETHEUS_AVAILABLE = False
try:
    import prometheus_client
    from prometheus_client import Counter, Gauge, Histogram, Summary
    PROMETHEUS_AVAILABLE = True
    logger.info("Prometheus client library is available")
except ImportError:
    logger.warning("Prometheus client library not available, using dummy implementation")

# Feature flag for metrics
ENABLE_METRICS = os.environ.get("ENABLE_METRICS", "").lower() in ("true", "1", "yes")
ENABLE_PROMETHEUS = os.environ.get("ENABLE_PROMETHEUS", "").lower() in ("true", "1", "yes")

# Only enable Prometheus if both the library is available and the feature flag is enabled
USE_PROMETHEUS = PROMETHEUS_AVAILABLE and ENABLE_PROMETHEUS and ENABLE_METRICS

class DummyMetric:
    """
    A dummy metric implementation that provides the same interface as Prometheus metrics
    but doesn't actually do anything.
    """
    
    def __init__(self, name: str, documentation: str, **kwargs):
        """Initialize the dummy metric."""
        self.name = name
        self.documentation = documentation
        self.labels_dict = {}
        self.value = 0
        
    def inc(self, amount: float = 1, **kwargs):
        """Increment the metric."""
        self.value += amount
        
    def dec(self, amount: float = 1, **kwargs):
        """Decrement the metric."""
        self.value -= amount
        
    def set(self, value: float, **kwargs):
        """Set the metric value."""
        self.value = value
        
    def observe(self, value: float, **kwargs):
        """Observe a value (for histograms and summaries)."""
        self.value = value
        
    def labels(self, **kwargs):
        """Return a labeled version of this metric."""
        # Store the labels for debugging
        for key, value in kwargs.items():
            self.labels_dict[key] = value
        return self
    
    def time(self):
        """Return a context manager for timing code blocks."""
        @contextmanager
        def timer():
            start = time.time()
            try:
                yield
            finally:
                # Record the duration
                self.observe(time.time() - start)
        return timer()

class MetricsClient:
    """
    A metrics client that provides a consistent API for collecting metrics,
    regardless of whether the metrics backend is available.
    """
    
    def __init__(self):
        """Initialize the metrics client."""
        self.enabled = ENABLE_METRICS
        self.use_prometheus = USE_PROMETHEUS
        self.metrics = {}
        
        # Create registry if using Prometheus
        if self.use_prometheus:
            try:
                self.registry = prometheus_client.CollectorRegistry()
                logger.info("Prometheus registry created")
            except Exception as e:
                logger.error(f"Failed to create Prometheus registry: {e}")
                self.use_prometheus = False
        
        # Log configuration
        if self.enabled:
            if self.use_prometheus:
                logger.info("Metrics collection enabled with Prometheus backend")
            else:
                logger.info("Metrics collection enabled with dummy backend")
        else:
            logger.info("Metrics collection disabled")
    
    def _create_or_get_metric(self, metric_type: str, name: str, documentation: str, **kwargs) -> Any:
        """
        Create a new metric or return an existing one.
        
        Args:
            metric_type: Type of metric (counter, gauge, histogram, summary)
            name: Name of the metric
            documentation: Documentation string for the metric
            **kwargs: Additional arguments for the metric
            
        Returns:
            The metric object
        """
        # If metrics are disabled, return a dummy metric
        if not self.enabled:
            return DummyMetric(name, documentation)
        
        # Check if the metric already exists
        metric_key = f"{metric_type}:{name}"
        if metric_key in self.metrics:
            return self.metrics[metric_key]
        
        # Create the metric
        if self.use_prometheus:
            try:
                if metric_type == "counter":
                    metric = Counter(name, documentation, registry=self.registry, **kwargs)
                elif metric_type == "gauge":
                    metric = Gauge(name, documentation, registry=self.registry, **kwargs)
                elif metric_type == "histogram":
                    metric = Histogram(name, documentation, registry=self.registry, **kwargs)
                elif metric_type == "summary":
                    metric = Summary(name, documentation, registry=self.registry, **kwargs)
                else:
                    logger.error(f"Unknown metric type: {metric_type}")
                    return DummyMetric(name, documentation)
            except Exception as e:
                logger.error(f"Failed to create Prometheus metric {name}: {e}")
                metric = DummyMetric(name, documentation)
        else:
            metric = DummyMetric(name, documentation)
        
        # Store the metric
        self.metrics[metric_key] = metric
        return metric
    
    def counter(self, name: str, documentation: str, **kwargs) -> Any:
        """
        Create a counter metric.
        
        Args:
            name: Name of the metric
            documentation: Documentation string for the metric
            **kwargs: Additional arguments for the metric
            
        Returns:
            Counter metric
        """
        return self._create_or_get_metric("counter", name, documentation, **kwargs)
    
    def gauge(self, name: str, documentation: str, **kwargs) -> Any:
        """
        Create a gauge metric.
        
        Args:
            name: Name of the metric
            documentation: Documentation string for the metric
            **kwargs: Additional arguments for the metric
            
        Returns:
            Gauge metric
        """
        return self._create_or_get_metric("gauge", name, documentation, **kwargs)
    
    def histogram(self, name: str, documentation: str, **kwargs) -> Any:
        """
        Create a histogram metric.
        
        Args:
            name: Name of the metric
            documentation: Documentation string for the metric
            **kwargs: Additional arguments for the metric
            
        Returns:
            Histogram metric
        """
        return self._create_or_get_metric("histogram", name, documentation, **kwargs)
    
    def summary(self, name: str, documentation: str, **kwargs) -> Any:
        """
        Create a summary metric.
        
        Args:
            name: Name of the metric
            documentation: Documentation string for the metric
            **kwargs: Additional arguments for the metric
            
        Returns:
            Summary metric
        """
        return self._create_or_get_metric("summary", name, documentation, **kwargs)
    
    def start_http_server(self, port: int = 8000, addr: str = "0.0.0.0") -> bool:
        """
        Start an HTTP server to expose metrics.
        
        Args:
            port: Port to listen on
            addr: Address to bind to
            
        Returns:
            True if the server was started, False otherwise
        """
        if not self.enabled or not self.use_prometheus:
            logger.warning("Cannot start metrics HTTP server: metrics or Prometheus not enabled")
            return False
        
        try:
            prometheus_client.start_http_server(port, addr, self.registry)
            logger.info(f"Metrics HTTP server started on {addr}:{port}")
            return True
        except Exception as e:
            logger.error(f"Failed to start metrics HTTP server: {e}")
            return False
    
    def push_to_gateway(self, gateway: str, job: str, **kwargs) -> bool:
        """
        Push metrics to a Prometheus Pushgateway.
        
        Args:
            gateway: Address of the Pushgateway
            job: Job name
            **kwargs: Additional arguments for the push
            
        Returns:
            True if the push was successful, False otherwise
        """
        if not self.enabled or not self.use_prometheus:
            logger.warning("Cannot push to gateway: metrics or Prometheus not enabled")
            return False
        
        try:
            prometheus_client.push_to_gateway(gateway, job, self.registry, **kwargs)
            logger.info(f"Metrics pushed to gateway {gateway} for job {job}")
            return True
        except Exception as e:
            logger.error(f"Failed to push metrics to gateway {gateway}: {e}")
            return False

# Singleton instance
_metrics_client = None

def get_metrics_client() -> MetricsClient:
    """
    Get the singleton instance of the metrics client.
    
    Returns:
        MetricsClient instance
    """
    global _metrics_client
    if _metrics_client is None:
        _metrics_client = MetricsClient()
    return _metrics_client

# Convenience functions
def counter(name: str, documentation: str, **kwargs) -> Any:
    """Create a counter metric."""
    return get_metrics_client().counter(name, documentation, **kwargs)

def gauge(name: str, documentation: str, **kwargs) -> Any:
    """Create a gauge metric."""
    return get_metrics_client().gauge(name, documentation, **kwargs)

def histogram(name: str, documentation: str, **kwargs) -> Any:
    """Create a histogram metric."""
    return get_metrics_client().histogram(name, documentation, **kwargs)

def summary(name: str, documentation: str, **kwargs) -> Any:
    """Create a summary metric."""
    return get_metrics_client().summary(name, documentation, **kwargs)

def start_http_server(port: int = 8000, addr: str = "0.0.0.0") -> bool:
    """Start an HTTP server to expose metrics."""
    return get_metrics_client().start_http_server(port, addr)

def push_to_gateway(gateway: str, job: str, **kwargs) -> bool:
    """Push metrics to a Prometheus Pushgateway."""
    return get_metrics_client().push_to_gateway(gateway, job, **kwargs)

@contextmanager
def timer(name: str, documentation: str, **kwargs):
    """
    Context manager for timing code blocks.
    
    Args:
        name: Name of the metric
        documentation: Documentation string for the metric
        **kwargs: Additional arguments for the metric
    """
    metric = get_metrics_client().summary(name, documentation, **kwargs)
    with metric.time():
        yield 