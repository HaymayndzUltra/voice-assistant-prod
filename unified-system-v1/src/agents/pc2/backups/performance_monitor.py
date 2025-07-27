import zmq
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


from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config

# Standard imports for PC2 agents
from pc2_code.utils.config_loader import load_config, parse_agent_args
from src.agents.pc2.error_bus_template import setup_error_reporting, report_error


# Load configuration at the module level
config = load_config()# Constants
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

class ResourceMonitor(BaseAgent):
    
    # Parse agent arguments
    _agent_args = parse_agent_args()def __init__(self):
         super().__init__(name="ResourceMonitor", port=None)
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

class PerformanceMonitor:
    def __init__(self):
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
                logging.FileHandler(LOG_DIR / str(PathManager.get_logs_dir() / "performance_monitor.log")),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('PerformanceMonitor')
        
    def _setup_zmq(self):
        """Setup ZMQ sockets for metrics and health monitoring"""
        self.context = zmq.Context()
        
        # Metrics publisher
        self.metrics_socket = self.context.socket(zmq.PUB)
        self.metrics_socket.bind(f"tcp://*:{METRICS_PORT}")
        
        # Health publisher
        self.health_socket = self.context.socket(zmq.PUB)
        self.health_socket.bind(f"tcp://*:{HEALTH_PORT}")
        
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
            
        return {
            'timestamp': datetime.now().isoformat(),
            'status': 'ok' if resources_ok and all(s['status'] == 'ok' for s in services_health.values()) else 'degraded',
            'resources': {
                'status': 'ok' if resources_ok else 'degraded',
                'stats': metrics['resources']
            },
            'services': services_health
        }
        
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
        
    def run(self):
        """Run the performance monitor"""
        self.logger.info("Performance Monitor started")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Performance Monitor shutting down...")

class PerformanceMonitorHealth:
    def __init__(self, port=7103):
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.running = True
    def start(self):
        print(f"Starting PerformanceMonitorHealth on port {self.port}")
        self.socket.bind(f"tcp://*:{self.port}")
        while self.running:
            try:
                request = self.socket.recv_json()
                if request.get('action') == 'health_check':
                    response = {'status': 'ok', 'service': 'PerformanceMonitor', 'port': self.port, 'timestamp': time.time()}
                else:
                    response = {'status': 'unknown_action', 'message': f"Unknown action: {request.get('action', 'none')}"}
                self.socket.send_json(response)
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)
    def stop(self):
        self.running = False
        self.socket.close()
        self.context.term()


    def cleanup(self):

        """Clean up resources before shutdown."""

        logger.info("Cleaning up resources...")

        # Add specific cleanup code here

        super().cleanup()

def main():
    monitor = PerformanceMonitor()
    monitor.run()



if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = ResourceMonitor()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()
