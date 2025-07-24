"""
Enhanced BaseAgent Class - Phase 1 Week 2 Optimization
Unified configuration, performance optimizations, and advanced features
"""

import sys
import os
import zmq
import json
import time
import logging
import threading
import uuid
import socket
from typing import Dict, Any, Optional, Union, List, Tuple
from datetime import datetime
from dataclasses import dataclass, field
import psutil

# Import the PathManager for consistent path resolution
from common.utils.path_manager import PathManager

# Import unified configuration manager
from common.core.unified_config_manager import UnifiedConfigManager, BaseAgentConfigMixin

# Import existing BaseAgent components
from common.core.base_agent import BaseAgent as OriginalBaseAgent
from common.utils.data_models import (
    SystemEvent, ErrorReport, ErrorSeverity, AgentRegistration
)
from common.utils.logger_util import get_json_logger
from common.env_helpers import get_env
from common.health.standardized_health import StandardizedHealthChecker, HealthStatus
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.error_bus.unified_error_handler import UnifiedErrorHandler, create_unified_error_handler
from common.utils.prometheus_exporter import create_agent_exporter, PrometheusExporter

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking for BaseAgent"""
    initialization_time: float = 0.0
    startup_time: float = 0.0
    request_count: int = 0
    error_count: int = 0
    response_times: List[float] = field(default_factory=list)
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    last_health_check: float = 0.0
    config_load_time: float = 0.0
    zmq_setup_time: float = 0.0
    
    def add_response_time(self, response_time: float):
        """Add a response time measurement"""
        self.response_times.append(response_time)
        # Keep only last 100 measurements to prevent memory growth
        if len(self.response_times) > 100:
            self.response_times.pop(0)
    
    def get_avg_response_time(self) -> float:
        """Get average response time"""
        return sum(self.response_times) / len(self.response_times) if self.response_times else 0.0
    
    def update_system_metrics(self):
        """Update system-level metrics"""
        try:
            process = psutil.Process()
            self.memory_usage_mb = process.memory_info().rss / 1024 / 1024
            self.cpu_usage_percent = process.cpu_percent()
        except Exception:
            pass  # Ignore errors in metric collection


class EnhancedErrorHandler:
    """Enhanced error handling with categorization and performance tracking"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.error_stats = {
            'CRITICAL': 0,
            'ERROR': 0,
            'WARNING': 0,
            'INFO': 0
        }
        self.error_history = []
        self.last_error_time = 0
        self._lock = threading.Lock()
    
    def report_error(self, error: Exception, context: Optional[Dict] = None, 
                    category: str = "GENERAL", severity: str = "ERROR"):
        """Enhanced error reporting with categorization"""
        with self._lock:
            error_entry = {
                'timestamp': time.time(),
                'agent': self.agent_name,
                'error': str(error),
                'type': type(error).__name__,
                'category': category,
                'severity': severity,
                'context': context or {}
            }
            
            # Update statistics
            self.error_stats[severity] = self.error_stats.get(severity, 0) + 1
            self.error_history.append(error_entry)
            self.last_error_time = error_entry['timestamp']
            
            # Keep only last 50 errors to prevent memory growth
            if len(self.error_history) > 50:
                self.error_history.pop(0)
            
            # Log the error
            log_level = getattr(logging, severity, logging.ERROR)
            logger.log(log_level, f"[{category}] {self.agent_name}: {error}", 
                      extra={'context': context})
            
            return error_entry
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get error handling statistics"""
        with self._lock:
            return {
                'total_errors': sum(self.error_stats.values()),
                'by_severity': self.error_stats.copy(),
                'last_error_time': self.last_error_time,
                'recent_errors': len([e for e in self.error_history 
                                    if time.time() - e['timestamp'] < 300])  # Last 5 minutes
            }


class ServiceDiscoveryClient:
    """Enhanced service discovery with automatic registration"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.registered_services = {}
        self.discovered_services = {}
        self.capabilities = []
        self.dependencies = []
        self._last_discovery = 0
        
    def register_service(self, capabilities: List[str], dependencies: List[str] = None):
        """Register service with capabilities and dependencies"""
        self.capabilities = capabilities
        self.dependencies = dependencies or []
        
        # TODO: Implement actual service registry integration
        self.registered_services[self.agent_name] = {
            'capabilities': capabilities,
            'dependencies': self.dependencies,
            'registered_at': time.time()
        }
    
    def is_registered(self, service_name: str) -> bool:
        """Check if a service is registered"""
        return service_name in self.registered_services
    
    def discover_services(self) -> Dict[str, Any]:
        """Discover available services"""
        # TODO: Implement actual service discovery
        return self.discovered_services


class EnhancedBaseAgent(OriginalBaseAgent, BaseAgentConfigMixin):
    """
    Enhanced BaseAgent with unified configuration, performance optimizations,
    and advanced features for Phase 1 Week 2
    """
    
    def __init__(self, *args, **kwargs):
        # Performance tracking
        init_start_time = time.time()
        
        # Enhanced initialization with performance monitoring
        self.performance_metrics = PerformanceMetrics()
        
        # Load configuration first with timing
        config_start = time.time()
        config_path = kwargs.get('config_path')
        self.config = self._load_unified_config(config_path)
        self.performance_metrics.config_load_time = time.time() - config_start
        
        # Apply config values to kwargs for BaseAgent compatibility
        if 'port' not in kwargs and 'port' in self.config:
            kwargs['port'] = self.config['port']
        if 'health_check_port' not in kwargs and 'health_check_port' in self.config:
            kwargs['health_check_port'] = self.config['health_check_port']
        
        # Initialize original BaseAgent
        super().__init__(*args, **kwargs)
        
        # Enhanced error handling
        self.error_handler = EnhancedErrorHandler(self.name)
        
        # Service discovery
        self.service_registry = ServiceDiscoveryClient(self.name)
        
        # Performance optimization flags
        self.optimization_enabled = self.config.get('enable_optimizations', True)
        self.metrics_enabled = self.config.get('enable_metrics', True)
        
        # Record initialization time
        self.performance_metrics.initialization_time = time.time() - init_start_time
        
        # Setup enhanced features
        self._setup_enhanced_features()
        
        logger.info(f"EnhancedBaseAgent {self.name} initialized in "
                   f"{self.performance_metrics.initialization_time:.4f}s")
    
    def _setup_enhanced_features(self):
        """Setup enhanced features and optimizations"""
        try:
            # Enhanced ZMQ setup with timing
            zmq_start = time.time()
            self._setup_zmq_sockets_optimized()
            self.performance_metrics.zmq_setup_time = time.time() - zmq_start
            
            # Register service capabilities
            self._register_service_capabilities()
            
            # Start performance monitoring if enabled
            if self.metrics_enabled:
                self._start_performance_monitoring()
            
        except Exception as e:
            self.error_handler.report_error(e, 
                context={'phase': 'enhanced_setup'},
                category='INITIALIZATION',
                severity='ERROR')
    
    def _setup_zmq_sockets_optimized(self):
        """Optimized ZMQ socket setup with connection pooling"""
        if self.optimization_enabled:
            # Use connection pooling and optimized socket options
            # TODO: Integrate with existing zmq_pool if available
            pass
    
    def _register_service_capabilities(self):
        """Register service capabilities for discovery"""
        # Determine capabilities based on agent type
        capabilities = []
        
        # Base capabilities
        capabilities.append('health_check')
        capabilities.append('error_reporting')
        
        # Agent-specific capabilities based on name/type
        agent_name_lower = self.name.lower()
        if 'memory' in agent_name_lower:
            capabilities.extend(['memory_management', 'data_storage'])
        elif 'model' in agent_name_lower:
            capabilities.extend(['ai_processing', 'model_management'])
        elif 'audio' in agent_name_lower:
            capabilities.extend(['audio_processing', 'media_handling'])
        elif 'vision' in agent_name_lower or 'face' in agent_name_lower:
            capabilities.extend(['vision_processing', 'image_analysis'])
        
        # Register with service discovery
        self.service_registry.register_service(capabilities)
    
    def _start_performance_monitoring(self):
        """Start background performance monitoring"""
        def monitor_performance():
            while self.running:
                try:
                    self.performance_metrics.update_system_metrics()
                    self.performance_metrics.last_health_check = time.time()
                    time.sleep(30)  # Update every 30 seconds
                except Exception as e:
                    self.error_handler.report_error(e,
                        context={'monitoring': 'performance'},
                        category='MONITORING',
                        severity='WARNING')
                    time.sleep(60)  # Back off on errors
        
        monitor_thread = threading.Thread(target=monitor_performance, daemon=True)
        monitor_thread.start()
    
    def report_error_enhanced(self, error: Exception, context: Optional[Dict] = None,
                            category: str = "GENERAL", severity: str = "ERROR"):
        """Enhanced error reporting with performance tracking"""
        error_entry = self.error_handler.report_error(error, context, category, severity)
        self.performance_metrics.error_count += 1
        return error_entry
    
    def process_request_with_timing(self, request_func, *args, **kwargs):
        """Process a request with automatic timing and metrics"""
        start_time = time.time()
        
        try:
            result = request_func(*args, **kwargs)
            
            # Record successful request
            response_time = time.time() - start_time
            self.performance_metrics.add_response_time(response_time)
            self.performance_metrics.request_count += 1
            
            return result
            
        except Exception as e:
            # Record failed request
            response_time = time.time() - start_time
            self.performance_metrics.add_response_time(response_time)
            self.performance_metrics.error_count += 1
            
            # Enhanced error reporting
            self.report_error_enhanced(e,
                context={
                    'request_function': request_func.__name__ if hasattr(request_func, '__name__') else str(request_func),
                    'response_time': response_time
                },
                category='REQUEST_PROCESSING',
                severity='ERROR')
            
            raise
    
    def get_health_status_enhanced(self) -> Dict[str, Any]:
        """Enhanced health status with performance metrics"""
        # Get base health status
        base_status = super()._get_health_status() if hasattr(super(), '_get_health_status') else {}
        
        # Add enhanced metrics
        enhanced_status = {
            'agent_name': self.name,
            'status': 'healthy' if self.running else 'stopped',
            'uptime': time.time() - self.start_time,
            'port': self.port,
            'health_check_port': getattr(self, 'health_check_port', None),
            
            # Performance metrics
            'performance': {
                'initialization_time': self.performance_metrics.initialization_time,
                'config_load_time': self.performance_metrics.config_load_time,
                'zmq_setup_time': self.performance_metrics.zmq_setup_time,
                'request_count': self.performance_metrics.request_count,
                'error_count': self.performance_metrics.error_count,
                'avg_response_time': self.performance_metrics.get_avg_response_time(),
                'memory_usage_mb': self.performance_metrics.memory_usage_mb,
                'cpu_usage_percent': self.performance_metrics.cpu_usage_percent
            },
            
            # Error statistics
            'error_stats': self.error_handler.get_statistics(),
            
            # Service information
            'service_info': {
                'capabilities': self.service_registry.capabilities,
                'dependencies': self.service_registry.dependencies,
                'registered': self.service_registry.is_registered(self.name)
            },
            
            # Configuration info
            'config_info': {
                'config_loaded': bool(self.config),
                'optimization_enabled': self.optimization_enabled,
                'metrics_enabled': self.metrics_enabled
            }
        }
        
        # Merge with base status
        enhanced_status.update(base_status)
        
        return enhanced_status
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get detailed performance report"""
        return {
            'agent_name': self.name,
            'timestamp': datetime.now().isoformat(),
            'metrics': {
                'initialization_time': self.performance_metrics.initialization_time,
                'config_load_time': self.performance_metrics.config_load_time,
                'zmq_setup_time': self.performance_metrics.zmq_setup_time,
                'uptime': time.time() - self.start_time,
                'request_count': self.performance_metrics.request_count,
                'error_count': self.performance_metrics.error_count,
                'error_rate': (self.performance_metrics.error_count / 
                             max(1, self.performance_metrics.request_count)) * 100,
                'avg_response_time': self.performance_metrics.get_avg_response_time(),
                'memory_usage_mb': self.performance_metrics.memory_usage_mb,
                'cpu_usage_percent': self.performance_metrics.cpu_usage_percent
            },
            'error_summary': self.error_handler.get_statistics(),
            'service_info': {
                'capabilities': self.service_registry.capabilities,
                'dependencies': self.service_registry.dependencies
            }
        }
    
    def graceful_shutdown_enhanced(self):
        """Enhanced shutdown with metrics preservation and cleanup optimization"""
        logger.info(f"Starting enhanced graceful shutdown for {self.name}")
        
        try:
            # Save final performance report
            if self.metrics_enabled:
                performance_report = self.get_performance_report()
                # TODO: Save to metrics storage
            
            # Call original graceful shutdown
            if hasattr(super(), 'graceful_shutdown'):
                super().graceful_shutdown()
            
            # Enhanced cleanup
            self.running = False
            
            # Cleanup enhanced components
            if hasattr(self, 'service_registry'):
                # TODO: Unregister from service discovery
                pass
            
            logger.info(f"Enhanced graceful shutdown completed for {self.name}")
            
        except Exception as e:
            self.error_handler.report_error(e,
                context={'phase': 'enhanced_shutdown'},
                category='SHUTDOWN',
                severity='WARNING')


# Convenience function to create enhanced agents
def create_enhanced_agent(agent_class, *args, **kwargs):
    """
    Create an enhanced agent instance with optimizations
    
    Args:
        agent_class: The agent class to enhance
        *args, **kwargs: Arguments for agent initialization
        
    Returns:
        Enhanced agent instance
    """
    # Create a dynamic class that inherits from both the agent class and EnhancedBaseAgent
    class EnhancedAgent(agent_class, EnhancedBaseAgent):
        def __init__(self, *args, **kwargs):
            # Initialize EnhancedBaseAgent first to set up optimizations
            EnhancedBaseAgent.__init__(self, *args, **kwargs)
            
            # Then initialize the specific agent class
            if hasattr(agent_class, '__init__'):
                agent_class.__init__(self, *args, **kwargs)
    
    return EnhancedAgent(*args, **kwargs) 