#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Common Monitoring Package

Enterprise-grade monitoring and metrics collection for the AI System Monorepo.
Provides Prometheus integration, custom metrics, dashboard support, and health monitoring.

Part of Phase 3.3: Monitoring & Metrics Expansion - O3 Roadmap Implementation
Extended in Phase 4.2: Enhanced Agent Factory and Lifecycle Management
"""

# Prometheus integration (optional)
try:
    from .prometheus_exporter import (
        PrometheusExporter,
        MetricConfig,
        get_exporter,
        inc_counter,
        set_gauge,
        observe_histogram,
        time_operation,
        monitor_requests
    )
    PROMETHEUS_AVAILABLE = True
    
    __prometheus_exports = [
        "PrometheusExporter",
        "MetricConfig",
        "get_exporter",
        "inc_counter",
        "set_gauge", 
        "observe_histogram",
        "time_operation",
        "monitor_requests"
    ]
except ImportError:
    PROMETHEUS_AVAILABLE = False
    __prometheus_exports = []

# Health Monitoring (Phase 4.2)
try:
    from .health_monitor import (
        HealthMonitor,
        HealthStatus,
        HealthChecker,
        BasicHealthChecker,
        ResourceHealthChecker,
        RecoveryStrategy,
        RestartRecoveryStrategy,
        get_health_monitor,
        register_agent_health_monitoring,
        start_health_monitoring,
        stop_health_monitoring
    )
    HEALTH_MONITORING_AVAILABLE = True
    
    __health_exports = [
        "HealthMonitor",
        "HealthStatus",
        "HealthChecker",
        "BasicHealthChecker",
        "ResourceHealthChecker", 
        "RecoveryStrategy",
        "RestartRecoveryStrategy",
        "get_health_monitor",
        "register_agent_health_monitoring",
        "start_health_monitoring",
        "stop_health_monitoring"
    ]
except ImportError:
    HEALTH_MONITORING_AVAILABLE = False
    __health_exports = []

__all__ = [
    # Availability flags
    "PROMETHEUS_AVAILABLE",
    "HEALTH_MONITORING_AVAILABLE"
] + __prometheus_exports + __health_exports

# Version info
__version__ = "4.2.0"
__phase__ = "Phase 4.2: Enhanced Agent Factory and Lifecycle Management"

# Monitoring recommendations
MONITORING_RECOMMENDATIONS = {
    "development": {
        "metrics_enabled": True,
        "http_server": True,
        "push_gateway": False,
        "collection_interval": 60
    },
    "staging": {
        "metrics_enabled": True,
        "http_server": True,
        "push_gateway": True,
        "collection_interval": 30
    },
    "production": {
        "metrics_enabled": True,
        "http_server": True,
        "push_gateway": True,
        "collection_interval": 15
    }
}


def get_monitoring_config(environment: str = "development") -> dict:
    """Get recommended monitoring configuration for environment."""
    return MONITORING_RECOMMENDATIONS.get(environment, MONITORING_RECOMMENDATIONS["development"])


def setup_monitoring(environment: str = "development", **kwargs) -> 'PrometheusExporter':
    """Setup monitoring with recommended configuration."""
    if not PROMETHEUS_AVAILABLE:
        raise ImportError("Prometheus monitoring not available. Install with: pip install prometheus-client")
    
    config = get_monitoring_config(environment)
    config.update(kwargs)
    
    exporter = get_exporter()
    
    if config.get("http_server", True):
        port = config.get("port", 8000)
        exporter.start_http_server(port)
    
    if config.get("push_gateway", False):
        gateway_url = config.get("gateway_url")
        if gateway_url:
            exporter.configure_push_gateway(gateway_url)
    
    if config.get("auto_collection", True):
        interval = config.get("collection_interval", 30)
        exporter.start_auto_collection(interval)
    
    return exporter
