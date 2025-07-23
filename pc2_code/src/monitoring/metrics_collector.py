#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Metrics Collector Agent
----------------------
Collects and aggregates performance metrics from all services and agents in the distributed voice assistant system.

Responsibilities:
- Collects CPU, memory, disk, and network usage metrics
- Tracks response times and throughput for all services
- Monitors system resource utilization
- Aggregates metrics from multiple sources
- Provides real-time performance analytics
- Stores historical metrics for trend analysis
- Generates performance reports and alerts

This agent uses ZMQ REP socket on port 5592 to receive commands and metrics requests,
and a PUB socket on port 5593 to broadcast metrics updates.
"""

import zmq
import json
import time
import logging
import sys
import os
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import threading
import datetime
from collections import defaultdict, deque
import psutil
import sqlite3


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, get_project_root())
from common.utils.path_manager import PathManager
# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import config parser utility with fallback
try:
from pc2_code.agents.utils.config_parser import parse_agent_args
from common.env_helpers import get_env
    except ImportError as e:
        print(f"Import error: {e}")
    _agent_args = parse_agent_args()
except ImportError:
    class DummyArgs:
        host = 'localhost'
    _agent_args = DummyArgs()

# Configure logging
log_file_path = PathManager.join_path("logs", "metrics_collector_agent.log")
log_directory = os.path.dirname(log_file_path)
os.makedirs(log_directory, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MetricsCollectorAgent")

# ZMQ ports
METRICS_COLLECTOR_PORT = 5592
METRICS_COLLECTOR_HEALTH_PORT = 5593

# Metrics constants
METRIC_TYPE_SYSTEM = "system"
METRIC_TYPE_SERVICE = "service"
METRIC_TYPE_CUSTOM = "custom"

class MetricPoint:
    """Class representing a single metric data point"""
    def __init__(self, metric_name: str, value: float, metric_type: str = METRIC_TYPE_CUSTOM, 
                 timestamp: float = None, tags: Dict[str, str] = None):
        self.metric_name = metric_name
        self.value = value
        self.metric_type = metric_type
        self.timestamp = timestamp if timestamp else time.time()
        self.tags = tags or {}
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "metric_type": self.metric_type,
            "timestamp": self.timestamp,
            "tags": self.tags
        }

class MetricsCollectorAgent:
    """Main metrics collector agent class"""
    def __init__(self, port=None):
        try:
            # Set up ports
            self.main_port = port if port else METRICS_COLLECTOR_PORT
            self.health_port = self.main_port + 1
            self.health_rep_port = self.main_port + 2  # 5594
            
            # Initialize ZMQ context and server socket
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://*:{self.main_port}")
            
            # Initialize PUB socket for metrics updates
            self.pub_socket = self.context.socket(zmq.PUB)
            self.pub_socket.bind(f"tcp://*:{self.health_port}")
            logger.info(f"MetricsCollectorAgent PUB socket bound to port {self.health_port}")
            
            # Initialize health REP socket
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.bind(f"tcp://*:{self.health_rep_port}")
            self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
            
            # Metrics storage
            self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
            self.current_metrics: Dict[str, float] = {}
            
            # Database setup
            self.db_path = Path(PathManager.join_path("data", "metrics.db"))
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(str(self.db_path))
            self._create_tables()
            
            # Collection settings
            self.collection_interval = 30  # seconds
            self.retention_days = 30
            
            # Monitoring threads
            self.collector_thread = threading.Thread(target=self.collect_metrics_loop, daemon=True)
            self.cleanup_thread = threading.Thread(target=self.cleanup_old_metrics_loop, daemon=True)
            self.running = True
            
            logger.info(f"MetricsCollectorAgent initialized on port {self.main_port}")
        except Exception as e:
            logger.error(f"Failed to initialize MetricsCollectorAgent: {str(e)}")
            raise

    def _create_tables(self):
        """Create necessary database tables"""
        cursor = self.conn.cursor()
        
        # Metrics table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY,
            metric_name TEXT NOT NULL,
            value REAL NOT NULL,
            metric_type TEXT NOT NULL,
            timestamp REAL NOT NULL,
            tags TEXT
        )
        ''')
        
        # Create index for faster queries
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_metrics_timestamp 
        ON metrics(timestamp)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_metrics_name 
        ON metrics(metric_name)
        ''')
        
        self.conn.commit()
        logger.info("Database tables created")

    def _health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            'status': 'success',
            'agent': 'MetricsCollectorAgent',
            'timestamp': datetime.datetime.now().isoformat(),
            'collector_thread_alive': self.collector_thread.is_alive() if hasattr(self, 'collector_thread') else False,
            'cleanup_thread_alive': self.cleanup_thread.is_alive() if hasattr(self, 'cleanup_thread') else False,
            'metrics_count': len(self.current_metrics),
            'port': self.main_port
        }

    def collect_system_metrics(self) -> Dict[str, float]:
        """Collect system-level metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            
            # Network metrics
            network = psutil.net_io_counters()
            
            metrics = {
                'cpu_percent': cpu_percent,
                'cpu_count': cpu_count,
                'cpu_freq_mhz': cpu_freq.current if cpu_freq else 0,
                'memory_percent': memory.percent,
                'memory_used_gb': memory.used / (1024**3),
                'memory_total_gb': memory.total / (1024**3),
                'disk_percent': disk.percent,
                'disk_used_gb': disk.used / (1024**3),
                'disk_total_gb': disk.total / (1024**3),
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv,
                'network_packets_sent': network.packets_sent,
                'network_packets_recv': network.packets_recv
            }
            
            return metrics
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {}

    def add_metric(self, metric_name: str, value: float, metric_type: str = METRIC_TYPE_CUSTOM, 
                   tags: Dict[str, str] = None) -> Dict[str, Any]:
        """Add a new metric data point"""
        try:
            metric = MetricPoint(metric_name, value, metric_type, time.time(), tags)
            
            # Store in memory
            self.metrics_history[metric_name].append(metric)
            self.current_metrics[metric_name] = value
            
            # Store in database
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO metrics (metric_name, value, metric_type, timestamp, tags)
            VALUES (?, ?, ?, ?, ?)
            ''', (metric_name, value, metric_type, metric.timestamp, json.dumps(tags or {})))
            self.conn.commit()
            
            # Publish metric update
            self.pub_socket.send_json({
                'type': 'metric_update',
                'metric': metric.to_dict()
            })
            
            logger.debug(f"Added metric: {metric_name} = {value}")
            return {'status': 'success', 'message': 'Metric added successfully'}
        except Exception as e:
            logger.error(f"Error adding metric: {e}")
            return {'status': 'error', 'message': str(e)}

    def get_metric(self, metric_name: str, hours: int = 24) -> Dict[str, Any]:
        """Get metric data for the specified time range"""
        try:
            if metric_name in self.metrics_history:
                # Get from memory
                history = list(self.metrics_history[metric_name])
                cutoff_time = time.time() - (hours * 3600)
                recent_metrics = [m for m in history if m.timestamp >= cutoff_time]
                
                return {
                    'status': 'success',
                    'metric_name': metric_name,
                    'current_value': self.current_metrics.get(metric_name),
                    'history': [m.to_dict() for m in recent_metrics],
                    'count': len(recent_metrics)
                }
            else:
                return {'status': 'error', 'message': f'Metric {metric_name} not found'}
        except Exception as e:
            logger.error(f"Error getting metric: {e}")
            return {'status': 'error', 'message': str(e)}

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics"""
        try:
            return {
                'status': 'success',
                'metrics': self.current_metrics.copy(),
                'count': len(self.current_metrics)
            }
        except Exception as e:
            logger.error(f"Error getting all metrics: {e}")
            return {'status': 'error', 'message': str(e)}

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics with statistics"""
        try:
            summary = {}
            for metric_name, history in self.metrics_history.items():
                if history:
                    values = [m.value for m in history]
                    summary[metric_name] = {
                        'current': self.current_metrics.get(metric_name),
                        'min': min(values),
                        'max': max(values),
                        'avg': sum(values) / len(values),
                        'count': len(values)
                    }
            
            return {
                'status': 'success',
                'summary': summary,
                'total_metrics': len(summary)
            }
        except Exception as e:
            logger.error(f"Error getting metrics summary: {e}")
            return {'status': 'error', 'message': str(e)}

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests"""
        action = request.get('action', '')
        
        if action == 'health_check':
            return self._health_check()
        elif action == 'add_metric':
            return self.add_metric(
                request.get('metric_name'),
                request.get('value'),
                request.get('metric_type', METRIC_TYPE_CUSTOM),
                request.get('tags')
            )
        elif action == 'get_metric':
            return self.get_metric(
                request.get('metric_name'),
                request.get('hours', 24)
            )
        elif action == 'get_all_metrics':
            return self.get_all_metrics()
        elif action == 'get_summary':
            return self.get_metrics_summary()
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}

    def _health_check_loop(self):
        """Health check loop for health REP socket"""
        logger.info(f"MetricsCollectorAgent health REP socket listening on port {self.health_rep_port}")
        while self.running:
            try:
                logger.debug("[HealthCheckLoop] Polling for health check requests...")
                if self.health_socket.poll(1000) == 0:
                    continue
                logger.debug("[HealthCheckLoop] Received poll event, waiting for message...")
                message = self.health_socket.recv_json()
                logger.info(f"[HealthCheckLoop] Received message: {message}")
                if message.get("action") == "health_check":
                    response = self._health_check()
                else:
                    response = {"status": "error", "error": "Invalid health check request"}
                self.health_socket.send_json(response)
                logger.info(f"[HealthCheckLoop] Sent response: {response}")
            except zmq.error.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    continue
                logger.error(f"ZMQ error in health check loop: {e}")
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")

    def run(self):
        """Start collecting metrics and handle requests"""
        logger.info(f"MetricsCollectorAgent starting on port {self.main_port}")
        
        # Start monitoring threads
        self.collector_thread.start()
        self.cleanup_thread.start()
        self.health_thread.start()
        
        try:
            while self.running:
                try:
                    # Wait for messages with timeout
                    if self.socket.poll(1000) == 0:
                        continue
                    
                    # Receive and process message
                    message = self.socket.recv_json()
                    logger.debug(f"Received request: {message}")
                    response = self.handle_request(message)
                    self.socket.send_json(response)
                    
                except zmq.error.ZMQError as e:
                    if e.errno == zmq.EAGAIN:
                        continue
                    logger.error(f"ZMQ error in main loop: {e}")
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            self.cleanup()

    def collect_metrics_loop(self):
        """Background thread for collecting system metrics"""
        logger.info("Starting metrics collection loop")
        while self.running:
            try:
                # Collect system metrics
                system_metrics = self.collect_system_metrics()
                for metric_name, value in system_metrics.items():
                    self.add_metric(metric_name, value, METRIC_TYPE_SYSTEM)
                
                time.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                time.sleep(self.collection_interval)

    def cleanup_old_metrics_loop(self):
        """Background thread for cleaning up old metrics"""
        logger.info("Starting metrics cleanup loop")
        while self.running:
            try:
                # Clean up old metrics from database
                cutoff_time = time.time() - (self.retention_days * 24 * 3600)
                cursor = self.conn.cursor()
                cursor.execute('DELETE FROM metrics WHERE timestamp < ?', (cutoff_time,))
                deleted_count = cursor.rowcount
                self.conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old metrics")
                
                # Run cleanup every hour
                time.sleep(3600)
            except Exception as e:
                logger.error(f"Error in metrics cleanup loop: {e}")
                time.sleep(3600)

    def cleanup(self):
        """Clean up resources before shutdown"""
        logger.info("Cleaning up MetricsCollectorAgent resources...")
        self.running = False
        
        if hasattr(self, 'collector_thread'):
            self.collector_thread.join(timeout=5)
        if hasattr(self, 'cleanup_thread'):
            self.cleanup_thread.join(timeout=5)
        if hasattr(self, 'health_thread'):
            self.health_thread.join(timeout=5)
        
        if hasattr(self, 'conn'):
            self.conn.close()
        
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'pub_socket'):
            self.pub_socket.close()
        if hasattr(self, 'health_socket'):
            self.health_socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        
        logger.info("Cleanup complete")

    def stop(self):
        """Stop the agent gracefully"""
        self.running = False

if __name__ == "__main__":
    # Create and run the Metrics Collector Agent
    agent = MetricsCollectorAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("Metrics Collector Agent interrupted")
    finally:
        agent.cleanup() 