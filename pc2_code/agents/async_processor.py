import zmq
from typing import Dict, Any, Optional
import yaml
import sys
import threading
from typing import Callable, Any, Dict, Optional
from functools import wraps
import time
import logging
import psutil
import torch
from datetime import datetime
from collections import deque, defaultdict
from pathlib import Path
import asyncio
from dataclasses import dataclass, field
import heapq
import threading


# Import path manager for containerization-friendly paths
import sys
from pathlib import Path

# Canonical import stack (TODO 1 compliance) - NO sys.path hacks
# project_root = Path(__file__).resolve().parent.parent.parent

# Canonical import stack (TODO 1 compliance)
from common.utils.env_standardizer import (
    get_mainpc_ip, get_pc2_ip, get_env, get_current_machine
)
from common.utils.path_manager import PathManager
from common.config_manager import get_service_url, get_redis_url
from common.core.base_agent import BaseAgent
from pc2_code.utils.pc2_error_publisher import create_pc2_error_publisher
from common.utils.log_setup import configure_logging

# Additional required imports
from pc2_code.utils.config_loader import load_config, parse_agent_args
# Migrated to unified config manager (replacing Pattern 5)
from common.config.unified_config_manager import Config
# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# Load configuration at the module level
config = Config.for_agent(__file__)

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
        
        # PC2 Error Bus Integration (Phase 1.3)
        self.error_publisher = create_pc2_error_publisher("async_processor")
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

@dataclass
class PriorityTask:
    """Task wrapper for priority queue."""
    priority: int
    task_id: int
    task_data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    
    def __lt__(self, other):
        # Lower priority number = higher priority
        if self.priority != other.priority:
            return self.priority < other.priority
        # If same priority, use task_id for FIFO ordering
        return self.task_id < other.task_id


class AsyncTaskQueue:
    """Async priority queue replacing manual deque management."""
    
    def __init__(self, max_size: int = MAX_QUEUE_SIZE):
        self.priority_queue = asyncio.PriorityQueue(maxsize=max_size)
        self.task_stats = defaultdict(lambda: {'success': 0, 'failed': 0, 'total_time': 0})
        self.task_counter = 0  # For FIFO ordering within same priority
        self._stats_lock = asyncio.Lock()
        
    async def add_task(self, task: Dict[str, Any], priority: str = 'medium'):
        """Add task to priority queue asynchronously."""
        priority_num = TASK_PRIORITIES.get(priority, TASK_PRIORITIES['medium'])
        
        self.task_counter += 1
        priority_task = PriorityTask(
            priority=priority_num,
            task_id=self.task_counter,
            task_data=task
        )
        
        try:
            await self.priority_queue.put(priority_task)
            return True
        except asyncio.QueueFull:
            # Queue is full, could not add task
            return False
        
    async def get_next_task(self) -> Optional[PriorityTask]:
        """Get next task based on priority asynchronously."""
        try:
            priority_task = await asyncio.wait_for(
                self.priority_queue.get(), 
                timeout=1.0  # 1 second timeout to allow health checks
            )
            return priority_task
        except asyncio.TimeoutError:
            return None
            
    def get_next_task_nowait(self) -> Optional[PriorityTask]:
        """Get next task without waiting (non-blocking)."""
        try:
            return self.priority_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None
        
    async def update_stats(self, task_type: str, success: bool, duration: float):
        """Update task statistics asynchronously."""
        async with self._stats_lock:
            stats = self.task_stats[task_type]
            if success:
                stats['success'] += 1
            else:
                stats['failed'] += 1
            stats['total_time'] += duration
    
    def get_stats(self):
        """Get current queue statistics."""
        return {
            'queue_size': self.priority_queue.qsize(),
            'max_size': self.priority_queue.maxsize,
            'tasks_processed': self.task_counter,
            'task_stats': dict(self.task_stats)
        }
        
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self.priority_queue.empty()
        
    def is_full(self) -> bool:
        """Check if queue is full."""
        return self.priority_queue.full()

class AsyncProcessor(BaseAgent):
    
    # Parse agent arguments
    _agent_args = parse_agent_args()
    
    def __init__(self, port: int = 7101, health_port: int = 8101):
        super().__init__(name="AsyncProcessor", port=port)
        self.logger = configure_logging(__name__)            # NEW (Δ-2) TODO 2 compliance
        self.error_publisher = create_pc2_error_publisher("async_processor")

        self._setup_sockets()
        self._start_health_check()
        self._init_thread = threading.Thread(
            target=self._initialize_background, daemon=True
        )
        self._init_thread.start()
        
        # Initialize components with async queue
        self.task_queue = AsyncTaskQueue()
        self.resource_manager = ResourceManager()
        self.start_time = time.time()
        self.context = None  # Using pool
        self.pull_socket = None
        self.push_socket = None
        self.health_socket = None
        self.running = False
        
        # Event loop for async operations
        self.event_loop = None
        self.processor_task = None
        
        # Load configuration
        self.config = load_config()
        
        # Set up error reporting
        # ✅ MODERNIZED: Using BaseAgent's UnifiedErrorHandler instead of custom error bus
        # Removed: from pc2_code.agents.error_bus_template import setup_error_reporting, report_error
        # Now using: self.report_error() method from BaseAgent
        
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
        """Setup logging - TODO 1/3 compliance: use configure_logging instead of basicConfig"""
        # logging.basicConfig removed per canonical import requirements
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
                    self.report_error("health_monitoring_error", str(e)
                    time.sleep(5)
                    
        thread = threading.Thread(target=monitor_health, daemon=True)
        thread.start()

    def _start_task_processor(self):
        """Start async task processor using asyncio."""
        def run_async_processor():
            # Create event loop for this thread
            self.event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.event_loop)
            
            try:
                # Start the async processor task
                self.processor_task = self.event_loop.create_task(self._async_process_loop()
                self.event_loop.run_until_complete(self.processor_task)
            except Exception as e:
                self.logger.error(f"Async processor error: {str(e)}")
                self.report_error("async_processor_error", str(e)
            finally:
                self.event_loop.close()
                    
        thread = threading.Thread(target=run_async_processor, daemon=True)
        thread.start()
        
    async def _async_process_loop(self):
        """Main async processing loop."""
        while self.running:
            try:
                # Process incoming requests (non-blocking check)
                try:
                    message = self.pull_socket.recv_json(zmq.NOBLOCK)
                    
                    # Health check handler
                    if message.get('action') == 'health_check':
                        self._handle_health_check(message)
                    else:
                        # Add to async queue for processing
                        priority = message.get('priority', 'medium')
                        await self.task_queue.add_task(message, priority)
                        
                        # Send immediate acknowledgment
                        self.pull_socket.send_json({
                            'status': 'queued',
                            'message': 'Task queued for processing'
                        })
                        
                except zmq.Again:
                    # No message available, continue to task processing
                    pass
                
                # Process queued tasks
                await self._process_queued_tasks()
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.01)
                
            except Exception as e:
                self.logger.error(f"Error in async process loop: {str(e)}")
                self.report_error("async_loop_error", str(e)
                await asyncio.sleep(1)
    
    async def _process_queued_tasks(self):
        """Process tasks from the async priority queue."""
        # Check resources before processing
        if not self.resource_manager.check_resources():
            return
            
        # Get next task with timeout
        priority_task = await self.task_queue.get_next_task()
        if priority_task is None:
            return
            
        task_data = priority_task.task_data
        task_type = task_data.get('type')
        data = task_data.get('data')
        
        if task_type and data:
            start_time = time.time()
            success = False
            
            try:
                # Process the task
                await self._handle_task_async(task_type, data)
                success = True
                self.logger.debug(f"Task {task_type} (ID: {priority_task.task_id}) processed successfully")
                
            except Exception as e:
                self.logger.error(f"Task processing error: {str(e)}")
                self.report_error("task_processing_error", str(e)
                
            # Update task statistics
            duration = time.time() - start_time
            await self.task_queue.update_stats(task_type, success, duration)

    def _process_task(self, message: Dict[str, Any]):
        """Process incoming task message"""
        task_type = message.get('type')
        data = message.get('data')
        message.get('priority', 'medium')
        
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
                self.report_error("task_processing_error", str(e)
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

    async def _handle_task_async(self, task_type: str, data: Any):
        """Handle specific task types asynchronously."""
        if task_type == 'logging':
            await self._handle_logging_async(data)
        elif task_type == 'analysis':
            await self._handle_analysis_async(data)
        elif task_type == 'memory':
            await self._handle_memory_async(data)
        elif task_type == 'batch_processing':
            await self._handle_batch_processing_async(data)
        elif task_type == 'model_inference':
            await self._handle_model_inference_async(data)
        else:
            self.logger.warning(f"Unknown task type: {task_type}")
            
    def _handle_task(self, task_type: str, data: Any):
        """Handle specific task types (legacy sync version)."""
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
        pass
    
    # Async versions of task handlers
    async def _handle_logging_async(self, log_data: Any):
        """Handle logging tasks asynchronously."""
        # Simulate async logging operation
        await asyncio.sleep(0.001)  # Small delay to simulate I/O
        self.logger.info(f"Async log task processed: {log_data}")
        
    async def _handle_analysis_async(self, analysis_data: Any):
        """Handle analysis tasks asynchronously."""
        # Simulate async analysis operation
        await asyncio.sleep(0.01)  # Simulate computation time
        self.logger.info(f"Async analysis task processed: {analysis_data}")
        
    async def _handle_memory_async(self, memory_data: Any):
        """Handle memory tasks asynchronously."""
        # Simulate async memory operation
        await asyncio.sleep(0.001)  # Small delay to simulate I/O
        self.logger.info(f"Async memory task processed: {memory_data}")
        
    async def _handle_batch_processing_async(self, batch_data: Any):
        """Handle batch processing tasks asynchronously."""
        # Simulate intensive async batch processing
        items = batch_data.get('items', [])
        batch_size = min(len(items), 10)  # Process up to 10 items at once
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            # Simulate batch processing
            await asyncio.sleep(0.05)  # Simulate processing time
            self.logger.info(f"Processed batch of {len(batch)} items")
            
    async def _handle_model_inference_async(self, inference_data: Any):
        """Handle model inference tasks asynchronously."""
        model_name = inference_data.get('model', 'default')
        input_data = inference_data.get('input', [])
        
        # Simulate async model inference
        await asyncio.sleep(0.1)  # Simulate model inference time
        
        result = {
            'model': model_name,
            'input_size': len(input_data) if isinstance(input_data, list) else 1,
            'processed_at': time.time()
        }
        
        self.logger.info(f"Model inference completed: {result}")

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
            self.report_error("health_check_error", str(e)
            error_response = {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self.pull_socket.send_json(error_response)

    def send_task(self, task_type: str, data: Any, priority: str = 'medium'):
        """Send a task to be processed asynchronously."""
        message = {
            'type': task_type,
            'data': data,
            'priority': priority,
            'timestamp': time.time()
        }
        self.push_socket.send_json(message)
        
    async def send_task_async(self, task_type: str, data: Any, priority: str = 'medium') -> bool:
        """Send a task directly to async queue (internal use)."""
        message = {
            'type': task_type,
            'data': data,
            'priority': priority,
            'timestamp': time.time()
        }
        return await self.task_queue.add_task(message, priority)

    def run(self):
        """Start the async processor."""
        self.logger.info("AsyncProcessor started with async priority queue")
        self.running = True
        
        try:
            # Start the task processor
            self._start_task_processor()
            
            # Keep the main thread alive and monitor
            while self.running:
                time.sleep(1)
                
                # Log queue status periodically
                if hasattr(self, 'task_queue'):
                    stats = self.task_queue.get_stats()
                    if stats['queue_size'] > 0:
                        self.logger.debug(f"Queue stats: {stats}")
                        
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
        logger.info("Cleaning up AsyncProcessor resources...")
        
        # Stop the async processor
        self.running = False
        
        # Cancel async tasks
        if self.processor_task and not self.processor_task.done():
            self.processor_task.cancel()
            
        # Close event loop if running
        if self.event_loop and not self.event_loop.is_closed():
            try:
                # Stop the event loop gracefully
                if self.event_loop.is_running():
                    self.event_loop.call_soon_threadsafe(self.event_loop.stop)
                    time.sleep(0.1)  # Give time for graceful shutdown
            except Exception as e:
                logger.warning(f"Error stopping event loop: {e}")
        
        # Close all sockets
        if hasattr(self, 'pull_socket') and self.pull_socket:
            self.pull_socket.close()
        if hasattr(self, 'push_socket') and self.push_socket:
            self.push_socket.close()
        if hasattr(self, 'health_socket') and self.health_socket:
            self.health_socket.close()
        # Clean up error reporting
        # ✅ MODERNIZED: Using BaseAgent's UnifiedErrorHandler instead of custom error bus
        # Removed: from pc2_code.agents.error_bus_template import cleanup_error_reporting
        # Now using: BaseAgent's cleanup() method
        
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
    config_path = Path(__file__).parent.parent.parent / "config" / "network_config.yaml"
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network config: {e}")
        # Default fallback values
        return {
            "main_pc_ip": get_mainpc_ip(),
            "pc2_ip": get_pc2_ip(),
            "bind_address": "0.0.0.0",
            "secure_zmq": False
        }

# Load both configurations
network_config = load_network_config()

# Get machine IPs from config
MAIN_PC_IP = get_mainpc_ip()
PC2_IP = network_config.get("pc2_ip", get_pc2_ip()
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


