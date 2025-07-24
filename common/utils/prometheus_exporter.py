#!/usr/bin/env python3
"""
Prometheus Exporter for AI Agent System
Standardized metrics collection and export for all agents.

This module provides a comprehensive metrics system for monitoring
agent performance, health, and resource utilization across the
distributed MainPC-PC2 architecture.
"""

import time
import threading
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import psutil
import socket

try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Info, Enum,
        generate_latest, CollectorRegistry, 
        CONTENT_TYPE_LATEST, REGISTRY
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Fallback classes for when prometheus_client is not available
    class MockMetric:
        def __init__(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
        def info(self, *args, **kwargs): pass
        def state(self, *args, **kwargs): pass
    
    Counter = Histogram = Gauge = Info = Enum = MockMetric


class PrometheusExporter:
    """
    Standardized metrics exporter for all agents in the AI system.
    
    Provides comprehensive monitoring capabilities including:
    - Request/response metrics
    - Performance and latency tracking
    - Resource utilization monitoring
    - Health status reporting
    - Custom agent-specific metrics
    """
    
    def __init__(self, agent_name: str, agent_port: int, enable_system_metrics: bool = True):
        """
        Initialize Prometheus exporter for an agent.
        
        Args:
            agent_name: Name of the agent (e.g., 'PC2HealthReportAgent')
            agent_port: Port the agent is running on
            enable_system_metrics: Whether to collect system resource metrics
        """
        self.agent_name = agent_name
        self.agent_port = agent_port
        self.enable_system_metrics = enable_system_metrics
        self.start_time = time.time()
        
        # Create custom registry for this agent
        self.registry = CollectorRegistry()
        
        # Initialize core metrics
        self._init_core_metrics()
        
        # Initialize system metrics if enabled
        if self.enable_system_metrics:
            self._init_system_metrics()
        
        # Start background metrics collection
        self._start_metrics_collection()
        
        # Agent metadata
        try:
            self.agent_info.info({
                'agent_name': agent_name,
                'agent_port': str(agent_port),
                'hostname': socket.gethostname(),
                'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
                'prometheus_available': str(PROMETHEUS_AVAILABLE)
            })
        except Exception as e:
            logging.warning(f"Could not set agent info: {e}")
    
    def _init_core_metrics(self):
        """Initialize core agent metrics"""
        # Request metrics
        self.request_count = Counter(
            'agent_requests_total',
            'Total requests handled by the agent',
            ['agent', 'method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.request_duration = Histogram(
            'agent_request_duration_seconds',
            'Request processing duration in seconds',
            ['agent', 'method', 'endpoint'],
            registry=self.registry
        )
        
        # Health and status metrics
        self.health_status = Enum(
            'agent_health_status',
            'Current health status of the agent',
            ['agent'],
            states=['healthy', 'unhealthy', 'unknown', 'starting', 'stopping'],
            registry=self.registry
        )
        
        self.uptime_seconds = Gauge(
            'agent_uptime_seconds',
            'Agent uptime in seconds',
            ['agent'],
            registry=self.registry
        )
        
        # Error tracking
        self.error_count = Counter(
            'agent_errors_total',
            'Total errors encountered by the agent',
            ['agent', 'error_type', 'severity'],
            registry=self.registry
        )
        
        # Performance metrics
        self.active_connections = Gauge(
            'agent_active_connections',
            'Number of active connections',
            ['agent'],
            registry=self.registry
        )
        
        self.queue_size = Gauge(
            'agent_queue_size',
            'Current queue size',
            ['agent', 'queue_type'],
            registry=self.registry
        )
        
        # Agent metadata
        self.agent_info = Info(
            'agent_info',
            'Information about the agent',
            registry=self.registry
        )
        
        # Initialize status
        self.health_status.labels(agent=self.agent_name).state('starting')
    
    def _init_system_metrics(self):
        """Initialize system resource metrics"""
        # CPU metrics
        self.cpu_usage_percent = Gauge(
            'agent_cpu_usage_percent',
            'CPU usage percentage for the agent process',
            ['agent'],
            registry=self.registry
        )
        
        # Memory metrics
        self.memory_usage_bytes = Gauge(
            'agent_memory_usage_bytes',
            'Memory usage in bytes',
            ['agent', 'type'],
            registry=self.registry
        )
        
        # Disk I/O metrics
        self.disk_io_bytes = Counter(
            'agent_disk_io_bytes_total',
            'Total disk I/O in bytes',
            ['agent', 'direction'],
            registry=self.registry
        )
        
        # Network metrics
        self.network_bytes = Counter(
            'agent_network_bytes_total',
            'Total network traffic in bytes',
            ['agent', 'direction'],
            registry=self.registry
        )
        
        # File descriptor usage
        self.open_file_descriptors = Gauge(
            'agent_open_file_descriptors',
            'Number of open file descriptors',
            ['agent'],
            registry=self.registry
        )
    
    def _start_metrics_collection(self):
        """Start background thread for continuous metrics collection"""
        def metrics_collector():
            while True:
                try:
                    # Update uptime
                    current_uptime = time.time() - self.start_time
                    self.uptime_seconds.labels(agent=self.agent_name).set(current_uptime)
                    
                    # Update system metrics if enabled
                    if self.enable_system_metrics:
                        self._update_system_metrics()
                    
                    # Sleep for 30 seconds before next collection
                    time.sleep(30)
                    
                except Exception as e:
                    # Log error but continue metrics collection
                    logging.error(f"Error in metrics collection: {e}")
                    time.sleep(30)
        
        self.metrics_thread = threading.Thread(target=metrics_collector, daemon=True)
        self.metrics_thread.start()
    
    def _update_system_metrics(self):
        """Update system resource metrics"""
        try:
            # Get current process
            process = psutil.Process()
            
            # CPU usage
            cpu_percent = process.cpu_percent()
            self.cpu_usage_percent.labels(agent=self.agent_name).set(cpu_percent)
            
            # Memory usage
            memory_info = process.memory_info()
            self.memory_usage_bytes.labels(agent=self.agent_name, type='rss').set(memory_info.rss)
            self.memory_usage_bytes.labels(agent=self.agent_name, type='vms').set(memory_info.vms)
            
            # I/O counters (if available)
            try:
                io_counters = process.io_counters()
                self.disk_io_bytes.labels(agent=self.agent_name, direction='read')._value._value = io_counters.read_bytes
                self.disk_io_bytes.labels(agent=self.agent_name, direction='write')._value._value = io_counters.write_bytes
            except (AttributeError, psutil.AccessDenied):
                pass  # I/O counters not available on all platforms
            
            # File descriptors
            try:
                num_fds = process.num_fds() if hasattr(process, 'num_fds') else len(process.open_files())
                self.open_file_descriptors.labels(agent=self.agent_name).set(num_fds)
            except (AttributeError, psutil.AccessDenied):
                pass
            
        except psutil.NoSuchProcess:
            # Process might have been terminated
            pass
        except Exception as e:
            logging.error(f"Error updating system metrics: {e}")
    
    # Public API methods for agent instrumentation
    
    def record_request(self, method: str, endpoint: str, status: str, duration: float):
        """
        Record a request with its duration and status.
        
        Args:
            method: HTTP method or action type (GET, POST, health_check, etc.)
            endpoint: Endpoint or operation name
            status: Status code or result (200, error, success, etc.)
            duration: Processing duration in seconds
        """
        self.request_count.labels(
            agent=self.agent_name,
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()
        
        self.request_duration.labels(
            agent=self.agent_name,
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_error(self, error_type: str, severity: str = 'error'):
        """
        Record an error occurrence.
        
        Args:
            error_type: Type of error (connection_error, validation_error, etc.)
            severity: Severity level (debug, info, warning, error, critical)
        """
        self.error_count.labels(
            agent=self.agent_name,
            error_type=error_type,
            severity=severity
        ).inc()
    
    def set_health_status(self, status: str):
        """
        Set the current health status.
        
        Args:
            status: Health status (healthy, unhealthy, unknown, starting, stopping)
        """
        if status in ['healthy', 'unhealthy', 'unknown', 'starting', 'stopping']:
            self.health_status.labels(agent=self.agent_name).state(status)
    
    def set_active_connections(self, count: int):
        """Set the number of active connections"""
        self.active_connections.labels(agent=self.agent_name).set(count)
    
    def set_queue_size(self, queue_type: str, size: int):
        """Set the current queue size for a specific queue type"""
        self.queue_size.labels(agent=self.agent_name, queue_type=queue_type).set(size)
    
    def create_custom_counter(self, name: str, description: str, labels: List[str] = None) -> Counter:
        """Create a custom counter metric for agent-specific monitoring"""
        return Counter(
            f'agent_{name}_total',
            description,
            ['agent'] + (labels or []),
            registry=self.registry
        )
    
    def create_custom_gauge(self, name: str, description: str, labels: List[str] = None) -> Gauge:
        """Create a custom gauge metric for agent-specific monitoring"""
        return Gauge(
            f'agent_{name}',
            description,
            ['agent'] + (labels or []),
            registry=self.registry
        )
    
    def create_custom_histogram(self, name: str, description: str, labels: List[str] = None) -> Histogram:
        """Create a custom histogram metric for agent-specific monitoring"""
        return Histogram(
            f'agent_{name}_seconds',
            description,
            ['agent'] + (labels or []),
            registry=self.registry
        )
    
    def export_metrics(self) -> str:
        """
        Generate metrics in Prometheus format.
        
        Returns:
            Metrics data in Prometheus exposition format
        """
        if not PROMETHEUS_AVAILABLE:
            return "# Prometheus client not available\n"
        
        try:
            return generate_latest(self.registry)
        except Exception as e:
            logging.error(f"Error generating metrics: {e}")
            return f"# Error generating metrics: {e}\n"
    
    def get_metrics_content_type(self) -> str:
        """Get the content type for metrics response"""
        return CONTENT_TYPE_LATEST if PROMETHEUS_AVAILABLE else 'text/plain'
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current metrics for debugging/monitoring.
        
        Returns:
            Dictionary containing current metric values
        """
        try:
            uptime = time.time() - self.start_time
            
            summary = {
                'agent_name': self.agent_name,
                'agent_port': self.agent_port,
                'uptime_seconds': uptime,
                'prometheus_available': PROMETHEUS_AVAILABLE,
                'metrics_enabled': True,
                'system_metrics_enabled': self.enable_system_metrics,
                'timestamp': datetime.now().isoformat()
            }
            
            # Add system metrics if available
            if self.enable_system_metrics:
                try:
                    process = psutil.Process()
                    summary.update({
                        'cpu_percent': process.cpu_percent(),
                        'memory_rss_mb': process.memory_info().rss / 1024 / 1024,
                        'memory_vms_mb': process.memory_info().vms / 1024 / 1024,
                    })
                except:
                    pass
            
            return summary
            
        except Exception as e:
            return {
                'error': f"Error generating metrics summary: {e}",
                'agent_name': self.agent_name,
                'timestamp': datetime.now().isoformat()
            }
    
    def cleanup(self):
        """Cleanup resources and set final status"""
        self.set_health_status('stopping')
        # The metrics thread will naturally terminate when the process exits


# Utility functions for easy integration

def create_agent_exporter(agent_name: str, agent_port: int, **kwargs) -> Optional[PrometheusExporter]:
    """
    Factory function to create a PrometheusExporter for an agent.
    
    Args:
        agent_name: Name of the agent
        agent_port: Port the agent is running on
        **kwargs: Additional configuration options
    
    Returns:
        PrometheusExporter instance or None if creation fails
    """
    try:
        return PrometheusExporter(agent_name, agent_port, **kwargs)
    except Exception as e:
        logging.error(f"Failed to create Prometheus exporter for {agent_name}: {e}")
        return None

def is_prometheus_available() -> bool:
    """Check if Prometheus client library is available"""
    return PROMETHEUS_AVAILABLE 