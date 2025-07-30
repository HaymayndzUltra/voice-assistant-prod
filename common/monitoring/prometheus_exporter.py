#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prometheus Metrics Exporter - Phase 3.3

Enterprise-grade Prometheus metrics exporter for the AI System Monorepo.
Provides comprehensive metrics collection, custom metrics registration,
and integration with existing agent monitoring systems.

Part of Phase 3.3: Monitoring & Metrics Expansion - O3 Roadmap Implementation
"""

import time
import threading
import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Union
from pathlib import Path
import json

try:
    from prometheus_client import (
        Counter, Gauge, Histogram, Summary, Info, Enum,
        CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST,
        start_http_server, push_to_gateway, delete_from_gateway
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


@dataclass
class MetricConfig:
    """Configuration for individual metrics."""
    name: str
    help_text: str
    labels: List[str] = field(default_factory=list)
    buckets: List[float] = field(default_factory=list)  # For histograms
    namespace: str = "ai_system"
    subsystem: str = ""


class PrometheusExporter:
    """Comprehensive Prometheus metrics exporter for AI System Monorepo."""
    
    def __init__(self, namespace: str = "ai_system", port: int = 8000, 
                 registry: Optional[CollectorRegistry] = None):
        self.namespace = namespace
        self.port = port
        self.registry = registry or CollectorRegistry()
        self.logger = logging.getLogger("prometheus.exporter")
        
        if not PROMETHEUS_AVAILABLE:
            raise ImportError("Prometheus client is not available. Install with: pip install prometheus-client")
        
        # Metric storage
        self.counters: Dict[str, Counter] = {}
        self.gauges: Dict[str, Gauge] = {}
        self.histograms: Dict[str, Histogram] = {}
        self.summaries: Dict[str, Summary] = {}
        self.infos: Dict[str, Info] = {}
        self.enums: Dict[str, Enum] = {}
        
        # HTTP server for metrics endpoint
        self.http_server = None
        self.server_thread = None
        
        # Push gateway configuration
        self.push_gateway_url = None
        self.push_job_name = "ai_system_job"
        
        # Auto-collection
        self.auto_collectors: Dict[str, Callable] = {}
        self.collection_interval = 30  # seconds
        self.collection_thread = None
        self.collection_running = False
        
        # Initialize default metrics
        self._init_default_metrics()
    
    def _init_default_metrics(self):
        """Initialize default system metrics."""
        # Agent metrics
        self.register_counter(
            "agent_requests_total",
            "Total number of requests processed by agents",
            ["agent_name", "method", "status"]
        )
        
        self.register_gauge(
            "agent_active_connections",
            "Number of active connections per agent",
            ["agent_name", "connection_type"]
        )
        
        self.register_histogram(
            "agent_request_duration_seconds",
            "Time spent processing agent requests",
            ["agent_name", "method"],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
        )
        
        # Queue metrics
        self.register_gauge(
            "queue_size",
            "Current size of various queues",
            ["queue_name", "priority"]
        )
        
        self.register_counter(
            "queue_items_processed_total",
            "Total items processed from queues",
            ["queue_name", "status"]
        )
        
        # System resource metrics
        self.register_gauge(
            "system_cpu_usage_percent",
            "CPU usage percentage",
            ["agent_name"]
        )
        
        self.register_gauge(
            "system_memory_usage_bytes",
            "Memory usage in bytes",
            ["agent_name", "type"]
        )
        
        # Error metrics
        self.register_counter(
            "errors_total",
            "Total number of errors",
            ["agent_name", "error_type", "severity"]
        )
        
        # Backend metrics (for Phase 3.1 backends)
        self.register_counter(
            "backend_operations_total",
            "Total backend operations",
            ["backend_name", "operation", "status"]
        )
        
        self.register_histogram(
            "backend_operation_duration_seconds",
            "Backend operation duration",
            ["backend_name", "operation"],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
        )
        
        # Configuration metrics
        self.register_info(
            "config_info",
            "Configuration information",
            ["environment", "version"]
        )
    
    def register_counter(self, name: str, help_text: str, labels: List[str] = None) -> Counter:
        """Register a Counter metric."""
        labels = labels or []
        metric_name = f"{self.namespace}_{name}"
        
        if metric_name in self.counters:
            return self.counters[metric_name]
        
        counter = Counter(
            name=metric_name,
            documentation=help_text,
            labelnames=labels,
            registry=self.registry
        )
        
        self.counters[metric_name] = counter
        self.logger.debug(f"Registered counter: {metric_name}")
        return counter
    
    def register_gauge(self, name: str, help_text: str, labels: List[str] = None) -> Gauge:
        """Register a Gauge metric."""
        labels = labels or []
        metric_name = f"{self.namespace}_{name}"
        
        if metric_name in self.gauges:
            return self.gauges[metric_name]
        
        gauge = Gauge(
            name=metric_name,
            documentation=help_text,
            labelnames=labels,
            registry=self.registry
        )
        
        self.gauges[metric_name] = gauge
        self.logger.debug(f"Registered gauge: {metric_name}")
        return gauge
    
    def register_histogram(self, name: str, help_text: str, labels: List[str] = None, 
                          buckets: List[float] = None) -> Histogram:
        """Register a Histogram metric."""
        labels = labels or []
        metric_name = f"{self.namespace}_{name}"
        
        if metric_name in self.histograms:
            return self.histograms[metric_name]
        
        histogram = Histogram(
            name=metric_name,
            documentation=help_text,
            labelnames=labels,
            buckets=buckets,
            registry=self.registry
        )
        
        self.histograms[metric_name] = histogram
        self.logger.debug(f"Registered histogram: {metric_name}")
        return histogram
    
    def register_summary(self, name: str, help_text: str, labels: List[str] = None) -> Summary:
        """Register a Summary metric."""
        labels = labels or []
        metric_name = f"{self.namespace}_{name}"
        
        if metric_name in self.summaries:
            return self.summaries[metric_name]
        
        summary = Summary(
            name=metric_name,
            documentation=help_text,
            labelnames=labels,
            registry=self.registry
        )
        
        self.summaries[metric_name] = summary
        self.logger.debug(f"Registered summary: {metric_name}")
        return summary
    
    def register_info(self, name: str, help_text: str, labels: List[str] = None) -> Info:
        """Register an Info metric."""
        labels = labels or []
        metric_name = f"{self.namespace}_{name}"
        
        if metric_name in self.infos:
            return self.infos[metric_name]
        
        info = Info(
            name=metric_name,
            documentation=help_text,
            labelnames=labels,
            registry=self.registry
        )
        
        self.infos[metric_name] = info
        self.logger.debug(f"Registered info: {metric_name}")
        return info
    
    def register_enum(self, name: str, help_text: str, states: List[str], 
                     labels: List[str] = None) -> Enum:
        """Register an Enum metric."""
        labels = labels or []
        metric_name = f"{self.namespace}_{name}"
        
        if metric_name in self.enums:
            return self.enums[metric_name]
        
        enum = Enum(
            name=metric_name,
            documentation=help_text,
            labelnames=labels,
            states=states,
            registry=self.registry
        )
        
        self.enums[metric_name] = enum
        self.logger.debug(f"Registered enum: {metric_name}")
        return enum
    
    # Metric update methods
    def inc_counter(self, name: str, value: float = 1, labels: Dict[str, str] = None):
        """Increment a counter metric."""
        metric_name = f"{self.namespace}_{name}"
        if metric_name in self.counters:
            if labels:
                self.counters[metric_name].labels(**labels).inc(value)
            else:
                self.counters[metric_name].inc(value)
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric value."""
        metric_name = f"{self.namespace}_{name}"
        if metric_name in self.gauges:
            if labels:
                self.gauges[metric_name].labels(**labels).set(value)
            else:
                self.gauges[metric_name].set(value)
    
    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Observe a value in a histogram."""
        metric_name = f"{self.namespace}_{name}"
        if metric_name in self.histograms:
            if labels:
                self.histograms[metric_name].labels(**labels).observe(value)
            else:
                self.histograms[metric_name].observe(value)
    
    def observe_summary(self, name: str, value: float, labels: Dict[str, str] = None):
        """Observe a value in a summary."""
        metric_name = f"{self.namespace}_{name}"
        if metric_name in self.summaries:
            if labels:
                self.summaries[metric_name].labels(**labels).observe(value)
            else:
                self.summaries[metric_name].observe(value)
    
    def set_info(self, name: str, info_dict: Dict[str, str], labels: Dict[str, str] = None):
        """Set info metric."""
        metric_name = f"{self.namespace}_{name}"
        if metric_name in self.infos:
            if labels:
                self.infos[metric_name].labels(**labels).info(info_dict)
            else:
                self.infos[metric_name].info(info_dict)
    
    def set_enum(self, name: str, state: str, labels: Dict[str, str] = None):
        """Set enum metric state."""
        metric_name = f"{self.namespace}_{name}"
        if metric_name in self.enums:
            if labels:
                self.enums[metric_name].labels(**labels).state(state)
            else:
                self.enums[metric_name].state(state)
    
    # Context managers for timing
    @contextmanager
    def time_histogram(self, name: str, labels: Dict[str, str] = None):
        """Context manager for timing operations with histogram."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.observe_histogram(name, duration, labels)
    
    @contextmanager
    def time_summary(self, name: str, labels: Dict[str, str] = None):
        """Context manager for timing operations with summary."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.observe_summary(name, duration, labels)
    
    # HTTP server management
    def start_http_server(self, port: int = None) -> bool:
        """Start HTTP server for metrics endpoint."""
        port = port or self.port
        
        try:
            self.http_server = start_http_server(port, registry=self.registry)
            self.logger.info(f"Prometheus metrics server started on port {port}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start metrics server: {e}")
            return False
    
    def get_metrics_text(self) -> str:
        """Get metrics in Prometheus text format."""
        return generate_latest(self.registry).decode('utf-8')
    
    # Push gateway support
    def configure_push_gateway(self, gateway_url: str, job_name: str = None):
        """Configure push gateway for metrics."""
        self.push_gateway_url = gateway_url
        self.push_job_name = job_name or self.push_job_name
        self.logger.info(f"Configured push gateway: {gateway_url}")
    
    def push_metrics(self, grouping_key: Dict[str, str] = None) -> bool:
        """Push metrics to gateway."""
        if not self.push_gateway_url:
            self.logger.warning("Push gateway not configured")
            return False
        
        try:
            push_to_gateway(
                gateway=self.push_gateway_url,
                job=self.push_job_name,
                registry=self.registry,
                grouping_key=grouping_key or {}
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to push metrics: {e}")
            return False
    
    def delete_metrics(self, grouping_key: Dict[str, str] = None) -> bool:
        """Delete metrics from gateway."""
        if not self.push_gateway_url:
            self.logger.warning("Push gateway not configured")
            return False
        
        try:
            delete_from_gateway(
                gateway=self.push_gateway_url,
                job=self.push_job_name,
                grouping_key=grouping_key or {}
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete metrics: {e}")
            return False
    
    # Auto-collection system
    def register_auto_collector(self, name: str, collector_func: Callable):
        """Register function for automatic metric collection."""
        self.auto_collectors[name] = collector_func
        self.logger.debug(f"Registered auto-collector: {name}")
    
    def start_auto_collection(self, interval: int = None):
        """Start automatic metric collection."""
        self.collection_interval = interval or self.collection_interval
        self.collection_running = True
        
        def collection_loop():
            while self.collection_running:
                try:
                    for name, collector in self.auto_collectors.items():
                        try:
                            collector()
                        except Exception as e:
                            self.logger.error(f"Error in auto-collector {name}: {e}")
                    
                    time.sleep(self.collection_interval)
                except Exception as e:
                    self.logger.error(f"Error in collection loop: {e}")
                    time.sleep(5)
        
        self.collection_thread = threading.Thread(target=collection_loop, daemon=True)
        self.collection_thread.start()
        self.logger.info(f"Started auto-collection with {self.collection_interval}s interval")
    
    def stop_auto_collection(self):
        """Stop automatic metric collection."""
        self.collection_running = False
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        self.logger.info("Stopped auto-collection")
    
    # Integration helpers
    def collect_agent_metrics(self, agent_name: str, metrics_data: Dict[str, Any]):
        """Collect metrics from an agent."""
        # Request metrics
        if 'requests' in metrics_data:
            for method, stats in metrics_data['requests'].items():
                self.inc_counter('agent_requests_total', stats.get('count', 0), {
                    'agent_name': agent_name,
                    'method': method,
                    'status': 'success'
                })
                
                if 'duration' in stats:
                    self.observe_histogram('agent_request_duration_seconds', 
                                         stats['duration'], {
                        'agent_name': agent_name,
                        'method': method
                    })
        
        # Connection metrics
        if 'connections' in metrics_data:
            for conn_type, count in metrics_data['connections'].items():
                self.set_gauge('agent_active_connections', count, {
                    'agent_name': agent_name,
                    'connection_type': conn_type
                })
        
        # Resource metrics
        if 'resources' in metrics_data:
            resources = metrics_data['resources']
            if 'cpu_percent' in resources:
                self.set_gauge('system_cpu_usage_percent', resources['cpu_percent'], {
                    'agent_name': agent_name
                })
            
            if 'memory_bytes' in resources:
                self.set_gauge('system_memory_usage_bytes', resources['memory_bytes'], {
                    'agent_name': agent_name,
                    'type': 'used'
                })
        
        # Error metrics
        if 'errors' in metrics_data:
            for error_type, count in metrics_data['errors'].items():
                self.inc_counter('errors_total', count, {
                    'agent_name': agent_name,
                    'error_type': error_type,
                    'severity': 'error'
                })
    
    def collect_queue_metrics(self, queue_name: str, queue_stats: Dict[str, Any]):
        """Collect metrics from queue systems."""
        if 'queue_size' in queue_stats:
            self.set_gauge('queue_size', queue_stats['queue_size'], {
                'queue_name': queue_name,
                'priority': 'all'
            })
        
        if 'processed' in queue_stats:
            self.inc_counter('queue_items_processed_total', queue_stats['processed'], {
                'queue_name': queue_name,
                'status': 'success'
            })
    
    def collect_backend_metrics(self, backend_name: str, backend_stats: Dict[str, Any]):
        """Collect metrics from backend systems (Phase 3.1)."""
        if 'operations' in backend_stats:
            self.inc_counter('backend_operations_total', backend_stats['operations'], {
                'backend_name': backend_name,
                'operation': 'total',
                'status': 'success'
            })
        
        if 'avg_response_time' in backend_stats:
            self.observe_histogram('backend_operation_duration_seconds', 
                                 backend_stats['avg_response_time'], {
                'backend_name': backend_name,
                'operation': 'avg'
            })
    
    # Utility methods
    def export_metrics_to_file(self, file_path: Path):
        """Export current metrics to file."""
        try:
            with open(file_path, 'w') as f:
                f.write(self.get_metrics_text())
            self.logger.info(f"Exported metrics to {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to export metrics: {e}")
    
    def get_metric_families(self):
        """Get all metric families from registry."""
        return list(self.registry.collect())
    
    def clear_registry(self):
        """Clear all metrics from registry."""
        self.registry = CollectorRegistry()
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()
        self.summaries.clear()
        self.infos.clear()
        self.enums.clear()
        self.logger.info("Cleared metrics registry")
    
    def shutdown(self):
        """Shutdown the exporter and cleanup resources."""
        self.stop_auto_collection()
        
        if self.http_server:
            try:
                self.http_server.shutdown()
            except Exception as e:
                self.logger.warning(f"Error shutting down HTTP server: {e}")
        
        self.logger.info("Prometheus exporter shutdown complete")


# Global exporter instance
_global_exporter: Optional[PrometheusExporter] = None


def get_exporter(namespace: str = "ai_system", port: int = 8000) -> PrometheusExporter:
    """Get or create global Prometheus exporter."""
    global _global_exporter
    
    if _global_exporter is None:
        _global_exporter = PrometheusExporter(namespace=namespace, port=port)
    
    return _global_exporter


# Convenience functions
def inc_counter(name: str, value: float = 1, labels: Dict[str, str] = None):
    """Increment counter using global exporter."""
    get_exporter().inc_counter(name, value, labels)


def set_gauge(name: str, value: float, labels: Dict[str, str] = None):
    """Set gauge using global exporter."""
    get_exporter().set_gauge(name, value, labels)


def observe_histogram(name: str, value: float, labels: Dict[str, str] = None):
    """Observe histogram using global exporter."""
    get_exporter().observe_histogram(name, value, labels)


def time_operation(name: str, labels: Dict[str, str] = None):
    """Time operation using global exporter."""
    return get_exporter().time_histogram(name, labels)


# Integration decorators
def monitor_requests(agent_name: str, method_name: str = None):
    """Decorator to monitor agent requests."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            method = method_name or func.__name__
            labels = {'agent_name': agent_name, 'method': method}
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                inc_counter('agent_requests_total', 1, {**labels, 'status': 'success'})
                return result
            except Exception as e:
                inc_counter('agent_requests_total', 1, {**labels, 'status': 'error'})
                inc_counter('errors_total', 1, {
                    'agent_name': agent_name,
                    'error_type': type(e).__name__,
                    'severity': 'error'
                })
                raise
            finally:
                duration = time.time() - start_time
                observe_histogram('agent_request_duration_seconds', duration, {
                    'agent_name': agent_name,
                    'method': method
                })
        
        return wrapper
    return decorator
