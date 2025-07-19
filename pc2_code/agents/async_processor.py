import zmq
from typing import Dict, Any, Optional
import yaml
import sys
import os
import threading
from typing import Callable, Any, Dict, List, Optional
from functools import wraps
import time
import logging
import psutil
import torch
from datetime import datetime
from collections import deque, defaultdict
import asyncio
from pathlib import Path
import json


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("pc2_code", "..")))
from common.utils.path_env import get_path, join_path, get_file_path
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
PUSH_PORT = 7102  # For fire-and-forget tasks
PULL_PORT = 7101  # For async task processing and health check
HEALTH_PORT = 7103  # For health monitoring
MAX_QUEUE_SIZE = 1000
HEALTH_CHECK_INTERVAL = 30  # seconds
TASK_PRIORITIES = {
    'high': 0,
    'medium': 1,
    'low': 2
}

# Setup logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logger = logging.getLogger("AsyncProcessor")

class ResourceManager:
    """
    ResourceManager: Monitors system resources for the AsyncProcessor.
    """
    
    def __init__(self):
        self.cpu_threshold = 80  # percentage
        self.memory_threshold = 80  # percentage
        self.gpu_threshold = 80  # percentage if available
        self.last_check = time.time()
        self.stats_history = deque(maxlen=100)
        
    def get_stats(self) -> Dict[str, Any]:
        """Get current resource statistics"""
        stats = {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'timestamp': time.time()
        }
        
        # Add GPU stats if available
        if torch.cuda.is_available():
            max_memory = torch.cuda.max_memory_allocated()
            if max_memory > 0:  # Prevent division by zero
                stats['gpu_memory_percent'] = torch.cuda.memory_allocated() / max_memory * 100
            else:
                stats['gpu_memory_percent'] = 0.0
            
        self.stats_history.append(stats)
        return stats
        
    def check_resources(self) -> bool:
        """Check if resources are available for processing"""
        stats = self.get_stats()
        
        if stats['cpu_percent'] > self.cpu_threshold:
            return False
            
        if stats['memory_percent'] > self.memory_threshold:
            return False
            
        if 'gpu_memory_percent' in stats and stats['gpu_memory_percent'] > self.gpu_threshold:
            return False
            
        return True

class TaskQueue:
    def __init__(self):
        self.queues = {
            'high': deque(maxlen=MAX_QUEUE_SIZE),
            'medium': deque(maxlen=MAX_QUEUE_SIZE),
            'low': deque(maxlen=MAX_QUEUE_SIZE)
        }
        self.task_stats = defaultdict(lambda: {'success': 0, 'failed': 0, 'total_time': 0})
        
    def add_task(self, task: Dict[str, Any], priority: str = 'medium'):
        """Add task to appropriate priority queue"""
        if priority not in self.queues:
            priority = 'medium'
        self.queues[priority].append(task)
        
    def get_next_task(self) -> Optional[Dict[str, Any]]:
        """Get next task based on priority"""
        for priority in ['high', 'medium', 'low']:
            if self.queues[priority]:
                return self.queues[priority].popleft()
        return None
        
    def update_stats(self, task_type: str, success: bool, duration: float):
        """Update task statistics"""
        stats = self.task_stats[task_type]
        stats['success' if success else 'failed'] += 1
        stats['total_time'] += duration
        
    def get_stats(self) -> Dict[str, Any]:
        """Get current queue statistics"""
        return {
            'queue_sizes': {p: len(q) for p, q in self.queues.items()},
            'task_stats': dict(self.task_stats)
        }

class AsyncProcessor(BaseAgent):
    
    # Parse agent arguments
    _agent_args = parse_agent_args()
    
    def __init__(self, port: int = 7101):
        super().__init__(name="AsyncProcessor", port=port)
        self.start_time = time.time()
        self.context = zmq.Context()
        self.resource_manager = ResourceManager()
        self.task_queue = TaskQueue()
        
        # Load configuration
        self.config = load_config()
        
        # Set up error reporting
        self.error_bus = setup_error_reporting(self)
        
        # Set up components
        self._setup_sockets()
        self._setup_logging()
        self._setup_health_monitoring()
        self._start_task_processor()
        
    def _setup_sockets(self):
        # Get port values from config or use defaults
        pull_port = self.config.get("ports", {}).get("async_processor_pull", PULL_PORT)
        push_port = self.config.get("ports", {}).get("async_processor_push", PUSH_PORT)
        health_port = self.config.get("ports", {}).get("async_processor_health", HEALTH_PORT)
        
        # REP socket for receiving tasks and health checks
        self.pull_socket = self.context.socket(zmq.REP)
        self.pull_socket.bind(f"tcp://*:{pull_port}")
        
        # Push socket for sending tasks
        self.push_socket = self.context.socket(zmq.PUSH)
        self.push_socket.bind(f"tcp://*:{push_port}")
        
        # Health monitoring socket (PUB)
        self.health_socket = self.context.socket(zmq.PUB)
        self.health_socket.bind(f"tcp://*:{health_port}")
        
        logger.info(f"AsyncProcessor sockets initialized on ports: {pull_port}, {push_port}, {health_port}")
        
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_DIR / 'async_processor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('AsyncProcessor')
        
    def _setup_health_monitoring(self):
        """Setup health monitoring thread"""
        def monitor_health():
            while True:
                try:
                    stats = self.resource_manager.get_stats()
                    queue_stats = self.task_queue.get_stats()
                    health_status = {
                        'status': 'ok' if self.resource_manager.check_resources() else 'degraded',
                        'stats': stats,
                        'queue_stats': queue_stats,
                        'timestamp': datetime.now().isoformat()
                    }
                    self.health_socket.send_json(health_status)
                    time.sleep(HEALTH_CHECK_INTERVAL)
                except Exception as e:
                    self.logger.error(f"Health monitoring error: {str(e)}")
                    if self.error_bus:
                        report_error(self.error_bus, "health_monitoring_error", str(e))
                    time.sleep(5)
                    
        thread = threading.Thread(target=monitor_health, daemon=True)
        thread.start()

    def _start_task_processor(self):
        """Start blocking loop to process tasks and health checks"""
        def process_requests():
            while True:
                try:
                    message = self.pull_socket.recv_json()
                    # Health check handler
                    if message.get('action') == 'health_check':
                        self._handle_health_check(message)
                    else:
                        self._process_task(message)
                except Exception as e:
                    self.logger.error(f"Error processing request: {str(e)}")
                    if self.error_bus:
                        report_error(self.error_bus, "request_processing_error", str(e))
                    time.sleep(1)
                    
        thread = threading.Thread(target=process_requests, daemon=True)
        thread.start()

    def _process_task(self, message: Dict[str, Any]):
        """Process incoming task message"""
        task_type = message.get('type')
        data = message.get('data')
        priority = message.get('priority', 'medium')
        
        if task_type and data:
            start_time = time.time()
            try:
                # Process the task asynchronously
                self._handle_task(task_type, data)
                success = True
                
                # Send success response
                self.pull_socket.send_json({
                    'status': 'success',
                    'message': f'Task {task_type} processed successfully'
                })
            except Exception as e:
                self.logger.error(f"Task processing error: {str(e)}")
                if self.error_bus:
                    report_error(self.error_bus, "task_processing_error", str(e))
                success = False
                
                # Send error response
                self.pull_socket.send_json({
                    'status': 'error',
                    'error': str(e)
                })
                
            # Update task statistics
            duration = time.time() - start_time
            self.task_queue.update_stats(task_type, success, duration)
        else:
            # Handle invalid task format
            self.pull_socket.send_json({
                'status': 'error',
                'error': 'Invalid task format. Required fields: type, data'
            })

    def _handle_task(self, task_type: str, data: Any):
        """Handle specific task types"""
        if task_type == 'logging':
            self._handle_logging(data)
        elif task_type == 'analysis':
            self._handle_analysis(data)
        elif task_type == 'memory':
            self._handle_memory(data)
        else:
            self.logger.warning(f"Unknown task type: {task_type}")
            raise ValueError(f"Unknown task type: {task_type}")

    def _handle_logging(self, log_data: Any):
        """Handle logging tasks"""
        self.logger.info(f"Processing log data: {log_data}")

    def _handle_analysis(self, analysis_data: Any):
        """Handle analysis tasks"""
        self.logger.info(f"Processing analysis data: {analysis_data}")

    def _handle_memory(self, memory_data: Any):
        """Handle memory tasks"""
        self.logger.info(f"Processing memory data: {memory_data}")

    def _handle_health_check(self, request: Dict[str, Any]):
        """Handle health check requests"""
        try:
            stats = self.resource_manager.get_stats()
            queue_stats = self.task_queue.get_stats()
            health_status = {
                'status': 'ok' if self.resource_manager.check_resources() else 'degraded',
                'service': 'AsyncProcessor',
                'stats': stats,
                'queue_stats': queue_stats,
                'timestamp': datetime.now().isoformat()
            }
            self.pull_socket.send_json(health_status)
        except Exception as e:
            self.logger.error(f"Error handling health check: {str(e)}")
            if self.error_bus:
                report_error(self.error_bus, "health_check_error", str(e))
            error_response = {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self.pull_socket.send_json(error_response)

    def send_task(self, task_type: str, data: Any, priority: str = 'medium'):
        """Send a task to be processed asynchronously"""
        message = {
            'type': task_type,
            'data': data,
            'priority': priority,
            'timestamp': time.time()
        }
        self.push_socket.send_json(message)

    def run(self):
        """Start the async processor"""
        self.logger.info("Async Processor started")
        try:
            while True:
                time.sleep(1)  # Keep the main thread alive
        except KeyboardInterrupt:
            self.logger.info("Async Processor shutting down...")
        finally:
            self.cleanup()

    def _get_health_status(self):
        base_status = super()._get_health_status()
        base_status.update({
            'service': 'AsyncProcessor',
            'uptime': time.time() - self.start_time,
            'queue_stats': self.task_queue.get_stats(),
            'resources': self.resource_manager.get_stats()
        })
        return base_status
    
    def health_check(self):
        """Return the health status of the agent"""
        return self._get_health_status()

    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info("Cleaning up resources...")
        
        # Close all sockets
        if hasattr(self, 'pull_socket'):
            self.pull_socket.close()
        
        if hasattr(self, 'push_socket'):
            self.push_socket.close()
            
        if hasattr(self, 'health_socket'):
            self.health_socket.close()
            
        # Clean up error reporting
        if hasattr(self, 'error_bus') and self.error_bus:
            from pc2_code.agents.error_bus_template import cleanup_error_reporting
            cleanup_error_reporting(self.error_bus)
        
        # Call parent cleanup
        super().cleanup()

def async_task(task_type: str, priority: str = 'medium'):
    """
    Decorator to make a function run asynchronously
    
    Args:
        task_type: Type of task to process
        priority: Task priority (high, medium, low)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get the async processor instance
            processor = AsyncProcessor()
            
            # Get the function arguments
            data = {
                'args': args,
                'kwargs': kwargs
            }
            
            # Send the task to be processed asynchronously
            processor.send_task(task_type, data, priority)
            
            # Return immediately
            return None
        
        return wrapper
    
    return decorator

def main():
    agent = None
    try:
        agent = AsyncProcessor()
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
    config_path = join_path("config", "network_config.yaml")
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network config: {e}")
        # Default fallback values
        return {
            "main_pc_ip": "192.168.100.16",
            "pc2_ip": "192.168.100.17",
            "bind_address": "0.0.0.0",
            "secure_zmq": False
        }

# Load both configurations
network_config = load_network_config()

# Get machine IPs from config
MAIN_PC_IP = network_config.get("main_pc_ip", "192.168.100.16")
PC2_IP = network_config.get("pc2_ip", "192.168.100.17")
BIND_ADDRESS = network_config.get("bind_address", "0.0.0.0")

if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = AsyncProcessor()
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
