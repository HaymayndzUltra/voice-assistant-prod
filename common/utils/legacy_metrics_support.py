#!/usr/bin/env python3
"""
Legacy Metrics Support for Non-BaseAgent Services
Provides Prometheus metrics integration for agents that don't inherit from BaseAgent.

This utility allows legacy agents to easily add metrics support through
environment variables and simple function calls.
"""

import os
import sys
import time
import logging
import threading
from typing import Dict, Any, Optional
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

# Import Prometheus exporter
from common.utils.prometheus_exporter import create_agent_exporter, PrometheusExporter

class LegacyMetricsWrapper:
    """
    Wrapper to add Prometheus metrics to legacy agents.
    
    Usage:
        # At the start of your legacy agent:
        from common.utils.legacy_metrics_support import LegacyMetricsWrapper
        
        metrics = LegacyMetricsWrapper.create_for_agent("MyLegacyAgent", port=7200)
        
        # Record metrics throughout your agent:
        metrics.record_request("process_data", "success", 0.5)
        metrics.record_error("connection_error")
        
        # At the end of your agent:
        metrics.cleanup()
    """
    
    def __init__(self, agent_name: str, agent_port: int, metrics_port: int = None):
        """
        Initialize legacy metrics wrapper.
        
        Args:
            agent_name: Name of the agent
            agent_port: Main port the agent runs on
            metrics_port: Port for metrics HTTP server (defaults to agent_port + 100)
        """
        self.agent_name = agent_name
        self.agent_port = agent_port
        self.metrics_port = metrics_port or (agent_port + 100)
        self.enabled = self._check_metrics_enabled()
        
        if self.enabled:
            self.prometheus_exporter = create_agent_exporter(
                agent_name=agent_name,
                agent_port=agent_port,
                enable_system_metrics=True
            )
            
            if self.prometheus_exporter:
                self._start_metrics_server()
                self.prometheus_exporter.set_health_status('starting')
                logging.info(f"Legacy metrics enabled for {agent_name} on port {self.metrics_port}")
            else:
                self.enabled = False
                logging.warning(f"Failed to create Prometheus exporter for {agent_name}")
        else:
            self.prometheus_exporter = None
            logging.info(f"Legacy metrics disabled for {agent_name}")
    
    def _check_metrics_enabled(self) -> bool:
        """Check if metrics are enabled via environment variable"""
        return os.getenv('ENABLE_PROMETHEUS_METRICS', 'true').lower() == 'true'
    
    def _start_metrics_server(self):
        """Start HTTP server for metrics endpoint"""
        class MetricsHandler(BaseHTTPRequestHandler):
            def __init__(self, metrics_wrapper):
                self.metrics_wrapper = metrics_wrapper
                super().__init__()
            
            def __call__(self, *args, **kwargs):
                # Create a closure that captures self.metrics_wrapper
                wrapper = self.metrics_wrapper
                
                class Handler(BaseHTTPRequestHandler):
                    def do_GET(self):
                        start_time = time.time()
                        
                        if self.path == '/metrics':
                            try:
                                if wrapper.prometheus_exporter:
                                    metrics_data = wrapper.prometheus_exporter.export_metrics()
                                    content_type = wrapper.prometheus_exporter.get_metrics_content_type()
                                    
                                    self.send_response(200)
                                    self.send_header('Content-type', content_type)
                                    self.end_headers()
                                    self.wfile.write(metrics_data.encode())
                                    
                                    # Record metrics request
                                    duration = time.time() - start_time
                                    wrapper.prometheus_exporter.record_request(
                                        method='GET',
                                        endpoint='/metrics',
                                        status='200',
                                        duration=duration
                                    )
                                else:
                                    self.send_error(503)
                            except Exception as e:
                                self.send_error(500)
                                if wrapper.prometheus_exporter:
                                    wrapper.prometheus_exporter.record_error('metrics_endpoint_error', 'error')
                        
                        elif self.path == '/health':
                            try:
                                health_data = {
                                    'status': 'ok',
                                    'agent': wrapper.agent_name,
                                    'port': wrapper.agent_port,
                                    'metrics_port': wrapper.metrics_port,
                                    'metrics_enabled': wrapper.enabled,
                                    'timestamp': time.time()
                                }
                                
                                self.send_response(200)
                                self.send_header('Content-type', 'application/json')
                                self.end_headers()
                                self.wfile.write(json.dumps(health_data).encode())
                                
                                if wrapper.prometheus_exporter:
                                    duration = time.time() - start_time
                                    wrapper.prometheus_exporter.record_request(
                                        method='GET',
                                        endpoint='/health',
                                        status='200',
                                        duration=duration
                                    )
                            except Exception as e:
                                self.send_error(500)
                        
                        else:
                            self.send_error(404)
                            if wrapper.prometheus_exporter:
                                duration = time.time() - start_time
                                wrapper.prometheus_exporter.record_request(
                                    method='GET',
                                    endpoint=self.path,
                                    status='404',
                                    duration=duration
                                )
                    
                    def log_message(self, format, *args):
                        # Suppress HTTP server logs
                        pass
                
                return Handler(*args, **kwargs)
        
        try:
            handler = MetricsHandler(self)
            self.http_server = HTTPServer(('0.0.0.0', self.metrics_port), handler)
            
            def serve():
                self.http_server.serve_forever()
            
            self.server_thread = threading.Thread(target=serve, daemon=True)
            self.server_thread.start()
            
            logging.info(f"Legacy metrics server started on port {self.metrics_port}")
            
        except OSError as e:
            logging.warning(f"Failed to start legacy metrics server on port {self.metrics_port}: {e}")
            self.enabled = False
    
    # Public API methods for legacy agents
    
    def record_request(self, endpoint: str, status: str, duration: float, method: str = 'process'):
        """Record a request/operation with its duration and status"""
        if self.enabled and self.prometheus_exporter:
            self.prometheus_exporter.record_request(method, endpoint, status, duration)
    
    def record_error(self, error_type: str, severity: str = 'error'):
        """Record an error occurrence"""
        if self.enabled and self.prometheus_exporter:
            self.prometheus_exporter.record_error(error_type, severity)
    
    def set_health_status(self, status: str):
        """Set the current health status"""
        if self.enabled and self.prometheus_exporter:
            self.prometheus_exporter.set_health_status(status)
    
    def set_active_connections(self, count: int):
        """Set the number of active connections"""
        if self.enabled and self.prometheus_exporter:
            self.prometheus_exporter.set_active_connections(count)
    
    def set_queue_size(self, queue_type: str, size: int):
        """Set the current queue size for a specific queue type"""
        if self.enabled and self.prometheus_exporter:
            self.prometheus_exporter.set_queue_size(queue_type, size)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current metrics"""
        if self.enabled and self.prometheus_exporter:
            return self.prometheus_exporter.get_metrics_summary()
        else:
            return {
                'agent_name': self.agent_name,
                'metrics_enabled': False,
                'error': 'Metrics not enabled or exporter not available'
            }
    
    def cleanup(self):
        """Cleanup resources"""
        if self.enabled and self.prometheus_exporter:
            self.prometheus_exporter.cleanup()
            logging.info(f"Legacy metrics cleaned up for {self.agent_name}")
        
        if hasattr(self, 'http_server'):
            try:
                self.http_server.shutdown()
                self.http_server.server_close()
            except:
                pass
    
    @staticmethod
    def create_for_agent(agent_name: str, port: int, metrics_port: int = None) -> 'LegacyMetricsWrapper':
        """
        Factory method to create a metrics wrapper for a legacy agent.
        
        Args:
            agent_name: Name of the agent
            port: Main port the agent runs on  
            metrics_port: Port for metrics HTTP server (optional)
        
        Returns:
            LegacyMetricsWrapper instance
        """
        return LegacyMetricsWrapper(agent_name, port, metrics_port)


# Utility functions for easy integration

def quick_metrics_setup(agent_name: str, port: int) -> Optional[LegacyMetricsWrapper]:
    """
    Quick setup function for legacy agents.
    
    Usage:
        from common.utils.legacy_metrics_support import quick_metrics_setup
        
        metrics = quick_metrics_setup("MyAgent", 7200)
        if metrics:
            metrics.set_health_status('healthy')
    
    Args:
        agent_name: Name of the agent
        port: Port the agent runs on
    
    Returns:
        LegacyMetricsWrapper instance or None if setup fails
    """
    try:
        return LegacyMetricsWrapper.create_for_agent(agent_name, port)
    except Exception as e:
        logging.error(f"Failed to setup metrics for {agent_name}: {e}")
        return None

def is_metrics_enabled() -> bool:
    """Check if metrics are enabled via environment variable"""
    return os.getenv('ENABLE_PROMETHEUS_METRICS', 'true').lower() == 'true'

# Example usage template for legacy agents
LEGACY_INTEGRATION_TEMPLATE = """
# Example integration for legacy agents:

import time
from common.utils.legacy_metrics_support import quick_metrics_setup

class MyLegacyAgent:
    def __init__(self, port=7200):
        self.port = port
        
        # Setup Prometheus metrics (if enabled)
        self.metrics = quick_metrics_setup("MyLegacyAgent", port)
        
        # Set initial health status
        if self.metrics:
            self.metrics.set_health_status('starting')
    
    def process_request(self, data):
        start_time = time.time()
        
        try:
            # Your existing processing logic here
            result = self._do_processing(data)
            
            # Record successful request
            if self.metrics:
                duration = time.time() - start_time
                self.metrics.record_request('process_request', 'success', duration)
            
            return result
            
        except Exception as e:
            # Record error
            if self.metrics:
                duration = time.time() - start_time
                self.metrics.record_request('process_request', 'error', duration)
                self.metrics.record_error('processing_error')
            
            raise
    
    def start(self):
        # Set healthy status when agent is ready
        if self.metrics:
            self.metrics.set_health_status('healthy')
    
    def cleanup(self):
        # Cleanup metrics on shutdown
        if self.metrics:
            self.metrics.cleanup()
""" 