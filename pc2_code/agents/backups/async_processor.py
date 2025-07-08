import zmq
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


from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config

# Standard imports for PC2 agents
from pc2_code.utils.config_loader import load_config, parse_agent_args
from pc2_code.agents.error_bus_template import setup_error_reporting, report_error


# Load configuration at the module level
config = load_config()# Constants
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

class ResourceManager(BaseAgent):

    
    # Parse agent arguments
    _agent_args = parse_agent_args()def __init__(self, port: int = None):

        super().__init__(name="ResourceManager", port=port)

        self.start_time = time.time()

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

class AsyncProcessor:
    def __init__(self):
        self.context = zmq.Context()
        self.resource_manager = ResourceManager()
        self.task_queue = TaskQueue()
        self._setup_sockets()
        self._setup_logging()
        self._setup_health_monitoring()
        
    def _setup_sockets(self):
        # REP socket for receiving tasks and health checks
        self.pull_socket = self.context.socket(zmq.REP)
        self.pull_socket.bind(f"tcp://*:{PULL_PORT}")
        
        # Push socket for sending tasks
        self.push_socket = self.context.socket(zmq.PUSH)
        self.push_socket.bind(f"tcp://*:{PUSH_PORT}")
        
        # Health monitoring socket (PUB)
        self.health_socket = self.context.socket(zmq.PUB)
        self.health_socket.bind(f"tcp://*:{HEALTH_PORT}")
        
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
                    time.sleep(5)
                    
        thread = threading.Thread(target=monitor_health, daemon=True)
        thread.start()

    def _start_task_processor(self):
        """Start blocking loop to process tasks and health checks (like SimpleTestAgent)"""
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
            except Exception as e:
                self.logger.error(f"Task processing error: {str(e)}")
                success = False
                
            # Update task statistics
            duration = time.time() - start_time
            self.task_queue.update_stats(task_type, success, duration)

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
        self._start_task_processor()
        try:
            while True:
                time.sleep(1)  # Keep the main thread alive
        except KeyboardInterrupt:
            self.logger.info("Async Processor shutting down...")
        finally:
            self.pull_socket.close()
            self.push_socket.close()
            self.health_socket.close()

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



    def _get_health_status(self) -> dict:


        """Return health status information."""


        base_status = super()._get_health_status()


        # Add any additional health information specific to ResourceManager


        base_status.update({


            'service': 'ResourceManager',


            'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0,


            'additional_info': {}


        })


        return base_status



    def cleanup(self):


        """Clean up resources before shutdown."""


        logger.info("Cleaning up resources...")


        # Add specific cleanup code here


        super().cleanup()

def main():
    processor = AsyncProcessor()
    processor.run()



if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = ResourceManager()
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
