
"""
Unified Health Check Mixin for WP-07 Health Unification
Provides standardized health endpoints and response formats
"""

import time
import psutil
import zmq
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import threading

@dataclass
class HealthMetrics:
    """Standardized health metrics"""
    timestamp: str
    status: str  # "healthy", "degraded", "unhealthy"
    uptime_seconds: float
    cpu_percent: float
    memory_percent: float
    zmq_connections: int
    active_threads: int
    error_count: int
    last_error: Optional[str] = None
    dependencies_status: Optional[Dict[str, str]] = None
    custom_metrics: Optional[Dict[str, Any]] = None

@dataclass
class HealthCheckResponse:
    """Standardized health check response"""
    agent_name: str
    health_metrics: HealthMetrics
    version: str = "1.0"
    schema: str = "WP-07-unified-health"

class UnifiedHealthMixin:
    """
    Unified health check mixin that can be added to any agent
    Provides standardized health endpoints and monitoring
    """
    
    def __init_health_monitoring__(self, health_check_port: int = None):
        """Initialize health monitoring system"""
        self.health_start_time = time.time()
        self.health_error_count = 0
        self.health_last_error = None
        self.health_custom_metrics = {}
        self.health_dependencies = {}
        
        # Set health check port
        if health_check_port:
            self.health_check_port = health_check_port
        elif hasattr(self, 'port'):
            self.health_check_port = self.port + 1000  # Standard offset
        else:
            self.health_check_port = 8000  # Default fallback
        
        # Initialize health check ZMQ socket
        self._init_health_socket()
        
        # Start health monitoring thread
        self.health_thread = threading.Thread(
            target=self._health_monitor_loop,
            daemon=True
        )
        self.health_running = True
        self.health_thread.start()
    
    def _init_health_socket(self):
        """Initialize health check ZMQ socket"""
        try:
            self.health_context = zmq.Context()
            self.health_socket = self.health_context.socket(zmq.REP)
            self.health_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            self.health_socket.bind(f"tcp://*:{self.health_check_port}")
            print(f"Health endpoint initialized on port {self.health_check_port}")
        except Exception as e:
            print(f"Failed to initialize health socket: {e}")
            self.health_socket = None
    
    def _health_monitor_loop(self):
        """Main health monitoring loop"""
        while self.health_running:
            try:
                if self.health_socket:
                    # Wait for health check request
                    message = self.health_socket.recv_string(zmq.NOBLOCK)
                    
                    if message == "health_check":
                        response = self.get_health_status()
                        self.health_socket.send_json(response)
                    elif message == "detailed_health":
                        response = self.get_detailed_health_status()
                        self.health_socket.send_json(response)
                    else:
                        self.health_socket.send_string("Unknown health request")
                        
            except zmq.Again:
                # No message received, continue
                time.sleep(0.1)
            except Exception as e:
                self.health_error_count += 1
                self.health_last_error = str(e)
                time.sleep(1)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get basic health status"""
        try:
            metrics = self._collect_health_metrics()
            response = HealthCheckResponse(
                agent_name=getattr(self, 'name', self.__class__.__name__),
                health_metrics=metrics
            )
            return asdict(response)
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_detailed_health_status(self) -> Dict[str, Any]:
        """Get detailed health status with additional metrics"""
        basic_health = self.get_health_status()
        
        # Add detailed system information
        basic_health.update({
            "system_info": {
                "python_version": self._get_python_version(),
                "platform": self._get_platform_info(),
                "disk_usage": self._get_disk_usage(),
                "network_connections": self._get_network_connections()
            }
        })
        
        return basic_health
    
    def _collect_health_metrics(self) -> HealthMetrics:
        """Collect health metrics"""
        now = datetime.now()
        uptime = time.time() - self.health_start_time
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Process metrics
        process = psutil.Process()
        active_threads = process.num_threads()
        
        # ZMQ connections (simplified)
        zmq_connections = getattr(self, '_active_connections', 0)
        
        # Determine overall status
        status = self._determine_health_status(cpu_percent, memory_percent)
        
        return HealthMetrics(
            timestamp=now.isoformat(),
            status=status,
            uptime_seconds=uptime,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            zmq_connections=zmq_connections,
            active_threads=active_threads,
            error_count=self.health_error_count,
            last_error=self.health_last_error,
            dependencies_status=self.health_dependencies.copy(),
            custom_metrics=self.health_custom_metrics.copy()
        )
    
    def _determine_health_status(self, cpu_percent: float, memory_percent: float) -> str:
        """Determine overall health status"""
        if cpu_percent > 90 or memory_percent > 90:
            return "unhealthy"
        elif cpu_percent > 70 or memory_percent > 70:
            return "degraded"
        elif self.health_error_count > 10:
            return "degraded"
        else:
            return "healthy"
    
    def add_dependency_check(self, name: str, check_func):
        """Add a dependency health check"""
        try:
            result = check_func()
            self.health_dependencies[name] = "healthy" if result else "unhealthy"
        except Exception as e:
            self.health_dependencies[name] = f"error: {e}"
    
    def add_custom_metric(self, name: str, value: Any):
        """Add custom health metric"""
        self.health_custom_metrics[name] = value
    
    def record_error(self, error: str):
        """Record an error for health monitoring"""
        self.health_error_count += 1
        self.health_last_error = error
    
    def _get_python_version(self) -> str:
        """Get Python version"""
        import sys
        return sys.version
    
    def _get_platform_info(self) -> str:
        """Get platform information"""
        import platform
        return platform.platform()
    
    def _get_disk_usage(self) -> Dict[str, float]:
        """Get disk usage information"""
        usage = psutil.disk_usage('/')
        return {
            "total_gb": usage.total / (1024**3),
            "used_gb": usage.used / (1024**3),
            "free_gb": usage.free / (1024**3),
            "percent": (usage.used / usage.total) * 100
        }
    
    def _get_network_connections(self) -> int:
        """Get number of network connections"""
        try:
            connections = psutil.net_connections()
            return len(connections)
        except:
            return 0
    
    def shutdown_health_monitoring(self):
        """Shutdown health monitoring"""
        self.health_running = False
        if hasattr(self, 'health_thread'):
            self.health_thread.join(timeout=5)
        if hasattr(self, 'health_socket'):
            self.health_socket.close()
        if hasattr(self, 'health_context'):
            self.health_context.term()
