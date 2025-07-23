import zmq
from typing import Dict, Any, Optional
import yaml
import sys
import os
import json
import time
import psutil
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
from pathlib import Path
import numpy as np
from common.config_manager import get_service_ip, get_service_url, get_redis_url


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(PathManager.join_path("pc2_code", "..")))
from common.utils.path_manager import PathManager
# Add the project's pc2_code directory to the Python path
import sys
import os
from pathlib import Path
PC2_CODE_DIR = get_main_pc_code()
if PC2_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, PC2_CODE_DIR.as_posix())

from common.core.base_agent import BaseAgent
from pc2_code.utils.config_loader import load_config, parse_agent_args
from pc2_code.agents.utils.config_loader import Config
from pc2_code.agents.error_bus_template import setup_error_reporting, report_error

# Load configuration at the module level
config = Config().get_config()

# Constants
METRICS_PORT = 5619
HEALTH_PORT = 5620
BROADCAST_INTERVAL = 5  # seconds
METRICS_HISTORY_SIZE = 1000
ALERT_THRESHOLDS = {
    'cpu_percent': 80,
    'memory_percent': 85,
    'response_time': 2.0,  # seconds
    'error_rate': 0.05,    # 5%
    'queue_size': 100
}

# Setup logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logger = logging.getLogger("PerformanceMonitor")

class ResourceMonitor:
    """
    ResourceMonitor: Monitors system resources.
    """
    def __init__(self):
        self.cpu_history = deque(maxlen=METRICS_HISTORY_SIZE)
        self.memory_history = deque(maxlen=METRICS_HISTORY_SIZE)
        self.gpu_history = deque(maxlen=METRICS_HISTORY_SIZE)
        self.last_check = time.time()
        
    def get_stats(self) -> Dict[str, Any]:
        """Get current resource statistics"""
        stats = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'timestamp': time.time()
        }
        
        # Update histories
        self.cpu_history.append(stats['cpu_percent'])
        self.memory_history.append(stats['memory_percent'])
        
        return stats
        
    def get_averages(self) -> Dict[str, float]:
        """Calculate average resource usage"""
        return {
            'cpu_avg': np.mean(self.cpu_history) if self.cpu_history else 0,
            'memory_avg': np.mean(self.memory_history) if self.memory_history else 0
        }
        
    def check_resources(self) -> bool:
        """Check if resources are within acceptable limits"""
        stats = self.get_stats()
        return (stats['cpu_percent'] <= ALERT_THRESHOLDS['cpu_percent'] and
                stats['memory_percent'] <= ALERT_THRESHOLDS['memory_percent'])

class PerformanceMonitor(BaseAgent):
    
    # Parse agent arguments
    _agent_args = parse_agent_args()
    
    def __init__(self, port: int = 7103):
        super().__init__(name="PerformanceMonitor", port=port)
        self.start_time = time.time()
        
        # Load configuration
        self.config = load_config()
        
        # Set up error reporting
        self.error_bus = setup_error_reporting(self)
        
        # Set up components
        self._setup_logging()
        self._setup_zmq()
        self._setup_metrics()
        self.resource_monitor = ResourceMonitor()
        self._start_monitoring()
        
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_DIR / 'performance_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('PerformanceMonitor')
        
    def _setup_zmq(self):
        """Setup ZMQ sockets for metrics and health monitoring"""
        self.context = None  # Using pool
        
        # Get port values from config or use defaults
        metrics_port = self.config.get("ports", {}).get("performance_metrics", METRICS_PORT)
        health_port = self.config.get("ports", {}).get("performance_health", HEALTH_PORT)
        
        # Metrics publisher
        self.metrics_socket = self.context.socket(zmq.PUB)
        self.metrics_socket.bind(f"tcp://*:{metrics_port}")
        
        # Health publisher
        self.health_socket = self.context.socket(zmq.PUB)
        self.health_socket.bind(f"tcp://*:{health_port}")
        
        self.logger.info(f"Performance Monitor sockets initialized on ports: {metrics_port}, {health_port}")
        
    def _setup_metrics(self):
        """Initialize metrics tracking"""
        self.metrics = {
            'response_times': defaultdict(list),
            'error_counts': defaultdict(int),
            'request_counts': defaultdict(int),
            'queue_sizes': defaultdict(list),
            'throughput': defaultdict(list)
        }
        
        self.alerts = []
        self.last_metrics_time = time.time()
        
    def _start_monitoring(self):
        """Start monitoring threads"""
        # Metrics broadcasting thread
        self.metrics_thread = threading.Thread(
            target=self._broadcast_metrics,
            daemon=True
        )
        self.metrics_thread.start()
        
        # Health monitoring thread
        self.health_thread = threading.Thread(
            target=self._monitor_health,
            daemon=True
        )
        self.health_thread.start()
        
    def _broadcast_metrics(self):
        """Broadcast metrics to subscribers"""
        while True:
            try:
                metrics = self._calculate_metrics()
                self.metrics_socket.send_json(metrics)
                time.sleep(BROADCAST_INTERVAL)
            except Exception as e:
                self.logger.error(f"Error broadcasting metrics: {str(e)}")
                if self.error_bus:
                    report_error(self.error_bus, "metrics_broadcast_error", str(e))
                time.sleep(5)
                
    def _monitor_health(self):
        """Monitor system health"""
        while True:
            try:
                health_status = self._get_health_status()
                self.health_socket.send_json(health_status)
                time.sleep(BROADCAST_INTERVAL)
            except Exception as e:
                self.logger.error(f"Error monitoring health: {str(e)}")
                if self.error_bus:
                    report_error(self.error_bus, "health_monitoring_error", str(e))
                time.sleep(5)
                
    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate current performance metrics"""
        current_time = time.time()
        time_diff = current_time - self.last_metrics_time
        
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'resources': self.resource_monitor.get_stats(),
            'averages': self.resource_monitor.get_averages(),
            'services': {}
        }
        
        # Calculate service-specific metrics
        for service in self.metrics['response_times'].keys():
            service_metrics = {
                'response_time': {
                    'current': np.mean(self.metrics['response_times'][service][-10:]) if self.metrics['response_times'][service] else 0,
                    'average': np.mean(self.metrics['response_times'][service]) if self.metrics['response_times'][service] else 0
                },
                'error_rate': self.metrics['error_counts'][service] / max(1, self.metrics['request_counts'][service]),
                'throughput': len(self.metrics['throughput'][service]) / time_diff if time_diff > 0 else 0,
                'queue_size': np.mean(self.metrics['queue_sizes'][service][-10:]) if self.metrics['queue_sizes'][service] else 0
            }
            metrics['services'][service] = service_metrics
            
        self.last_metrics_time = current_time
        return metrics
        
    def _get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        metrics = self._calculate_metrics()
        resources_ok = self.resource_monitor.check_resources()
        
        # Check service health
        services_health = {}
        for service, service_metrics in metrics['services'].items():
            service_health = {
                'status': 'ok',
                'alerts': []
            }
            
            # Check response time
            if service_metrics['response_time']['current'] > ALERT_THRESHOLDS['response_time']:
                service_health['status'] = 'degraded'
                service_health['alerts'].append('High response time')
                
            # Check error rate
            if service_metrics['error_rate'] > ALERT_THRESHOLDS['error_rate']:
                service_health['status'] = 'degraded'
                service_health['alerts'].append('High error rate')
                
            # Check queue size
            if service_metrics['queue_size'] > ALERT_THRESHOLDS['queue_size']:
                service_health['status'] = 'degraded'
                service_health['alerts'].append('Large queue size')
                
            services_health[service] = service_health
            
        base_status = {
            'timestamp': datetime.now().isoformat(),
            'status': 'ok' if resources_ok and all(s['status'] == 'ok' for s in services_health.values()) else 'degraded',
            'resources': {
                'status': 'ok' if resources_ok else 'degraded',
                'stats': metrics['resources']
            },
            'services': services_health
        }
        base_status.update({
            'service': 'PerformanceMonitor',
            'uptime': time.time() - self.start_time
        })
        return base_status
        
    def log_metric(self, service: str, metric_type: str, value: Any) -> None:
        """Log a performance metric"""
        try:
            if metric_type == 'response_time':
                self.metrics['response_times'][service].append(value)
            elif metric_type == 'error':
                self.metrics['error_counts'][service] += 1
            elif metric_type == 'request':
                self.metrics['request_counts'][service] += 1
            elif metric_type == 'queue_size':
                self.metrics['queue_sizes'][service].append(value)
            elif metric_type == 'throughput':
                self.metrics['throughput'][service].append(value)
                
            # Trim old metrics
            for key in ['response_times', 'queue_sizes', 'throughput']:
                if len(self.metrics[key][service]) > METRICS_HISTORY_SIZE:
                    self.metrics[key][service] = self.metrics[key][service][-METRICS_HISTORY_SIZE:]
                    
        except Exception as e:
            self.logger.error(f"Error logging metric: {str(e)}")
            if self.error_bus:
                report_error(self.error_bus, "metric_logging_error", str(e))
            
    def get_service_metrics(self, service: str) -> Dict[str, Any]:
        """Get metrics for a specific service"""
        try:
            return {
                'response_time': {
                    'current': np.mean(self.metrics['response_times'][service][-10:]) if self.metrics['response_times'][service] else 0,
                    'average': np.mean(self.metrics['response_times'][service]) if self.metrics['response_times'][service] else 0
                },
                'error_rate': self.metrics['error_counts'][service] / max(1, self.metrics['request_counts'][service]),
                'throughput': len(self.metrics['throughput'][service]) / (time.time() - self.last_metrics_time) if self.last_metrics_time else 0,
                'queue_size': np.mean(self.metrics['queue_sizes'][service][-10:]) if self.metrics['queue_sizes'][service] else 0
            }
        except Exception as e:
            self.logger.error(f"Error getting service metrics: {str(e)}")
            if self.error_bus:
                report_error(self.error_bus, "service_metrics_error", str(e))
            return {}
            
    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get current performance alerts"""
        alerts = []
        metrics = self._calculate_metrics()
        
        # Check resource alerts
        if not self.resource_monitor.check_resources():
            alerts.append({
                'type': 'resource',
                'level': 'warning',
                'message': 'High resource usage detected',
                'details': metrics['resources']
            })
            
        # Check service alerts
        for service, service_metrics in metrics['services'].items():
            if service_metrics['response_time']['current'] > ALERT_THRESHOLDS['response_time']:
                alerts.append({
                    'type': 'service',
                    'service': service,
                    'level': 'warning',
                    'message': 'High response time',
                    'details': service_metrics['response_time']
                })
                
            if service_metrics['error_rate'] > ALERT_THRESHOLDS['error_rate']:
                alerts.append({
                    'type': 'service',
                    'service': service,
                    'level': 'error',
                    'message': 'High error rate',
                    'details': {'error_rate': service_metrics['error_rate']}
                })
                
        return alerts
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests"""
        action = request.get("action", "")
        
        if action in ["ping", "health", "health_check"]:
            return self._get_health_status()
            
        elif action == "get_metrics":
            service = request.get("service")
            if service:
                return {"status": "success", "metrics": self.get_service_metrics(service)}
            else:
                return {"status": "success", "metrics": self._calculate_metrics()}
                
        elif action == "get_alerts":
            return {"status": "success", "alerts": self.get_alerts()}
            
        elif action == "log_metric":
            service = request.get("service")
            metric_type = request.get("metric_type")
            value = request.get("value")
            
            if not service or not metric_type or value is None:
                return {"status": "error", "message": "Missing required parameters"}
                
            self.log_metric(service, metric_type, value)
            return {"status": "success", "message": "Metric logged"}
            
        return {"status": "error", "message": f"Unknown action: {action}"}
        
    def run(self):
        """Run the performance monitor"""
        self.logger.info("Performance Monitor started")
        try:
            super().run()  # Use BaseAgent's request loop
        except KeyboardInterrupt:
            self.logger.info("Performance Monitor shutting down...")
        finally:
            self.cleanup()

    def health_check(self):
        """Return the health status of the agent"""
        return self._get_health_status()

    def cleanup(self):
        """Clean up resources before shutdown."""
        self.logger.info("Cleaning up resources...")
        
        # Close all sockets
        if hasattr(self, 'metrics_socket'):
            self.metrics_
        if hasattr(self, 'health_socket'):
            self.health_
        # Clean up error reporting
        if hasattr(self, 'error_bus') and self.error_bus:
            from pc2_code.agents.error_bus_template import cleanup_error_reporting
            cleanup_error_reporting(self.error_bus)
        
        # Call parent cleanup
        super().cleanup()

def main():
    agent = None
    try:
        agent = PerformanceMonitor()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback

        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()

# Load network configuration
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = PathManager.join_path("config", "network_config.yaml")
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network config: {e}")
        # Default fallback values
        return {
            "main_pc_ip": get_service_ip("mainpc"),
            "pc2_ip": get_service_ip("pc2"),
            "bind_address": "0.0.0.0",
            "secure_zmq": False
        }

# Load both configurations
network_config = load_network_config()

# Get machine IPs from config
MAIN_PC_IP = network_config.get("main_pc_ip", get_service_ip("mainpc"))
PC2_IP = network_config.get("pc2_ip", get_service_ip("pc2"))
BIND_ADDRESS = network_config.get("bind_address", "0.0.0.0")

if __name__ == "__main__":
    main()
