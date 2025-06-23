"""
Task Router Agent
- Routes tasks to appropriate models and services
- Implements Circuit Breaker pattern for resilient connections
- Manages communication with downstream services
- Advanced routing with Chain of Thought and Graph/Tree of Thought
"""
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
MAIN_PC_CODE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if MAIN_PC_CODE not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE)

import json
import logging
import zmq
import time
import threading
import msgpack  # For efficient message serialization
import heapq  # For priority queue
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from src.core.http_server import setup_health_check_server
from utils.config_parser import parse_agent_args
# Import service discovery and network utilities
from main_pc_code.utils.service_discovery_client import discover_service, get_service_address
from main_pc_code.utils.network_utils import load_network_config, get_current_machine

args = parse_agent_args()

# Configure logging
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'task_router.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('TaskRouter')

# Port and Host configuration from command line arguments
TASK_ROUTER_PORT = args.port if args.port else 8571
TASK_ROUTER_HEALTH_PORT = TASK_ROUTER_PORT + 1

# Downstream service connection parameters
COT_HOST = getattr(args, 'cot_host', None)
COT_PORT = getattr(args, 'cot_port', None)

GOT_TOT_HOST = getattr(args, 'got_tot_host', None)
GOT_TOT_PORT = getattr(args, 'got_tot_port', None)

# These will be determined dynamically through service discovery
EMR_HOST = None
EMR_PORT = None

TRANSLATOR_HOST = None
TRANSLATOR_PORT = None

# Circuit breaker configuration
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 3
CIRCUIT_BREAKER_RESET_TIMEOUT = 30
CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT = 5

class CircuitBreaker:
    """
    Circuit Breaker pattern implementation for resilient service connections.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit is tripped, requests fail fast
    - HALF_OPEN: Testing if service is back, allows one test request
    """
    
    # Circuit states
    CLOSED = 'closed'
    OPEN = 'open'
    HALF_OPEN = 'half_open'
    
    def __init__(self, name: str, failure_threshold: int = CIRCUIT_BREAKER_FAILURE_THRESHOLD, 
                 reset_timeout: int = CIRCUIT_BREAKER_RESET_TIMEOUT,
                 half_open_timeout: int = CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT):
        """Initialize the circuit breaker.
        
        Args:
            name: Name of the service protected by this circuit breaker
            failure_threshold: Number of consecutive failures before tripping
            reset_timeout: Seconds to wait before attempting reset
            half_open_timeout: Seconds to wait in half-open state before allowing another test
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_timeout = half_open_timeout
        
        self.state = self.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.last_success_time = time.time()
        self.last_test_time = 0
        self._lock = threading.Lock()
        
        logger.info(f"Circuit breaker initialized for {name}")
    
    def record_success(self):
        """Record a successful request."""
        with self._lock:
            if self.state == self.HALF_OPEN:
                # If we were testing the service and it succeeded, close the circuit
                logger.info(f"Circuit breaker for {self.name} reset after successful test request")
                self.state = self.CLOSED
                
            self.failure_count = 0
            self.last_success_time = time.time()
            self.last_test_time = 0
    
    def record_failure(self):
        """Record a failed request."""
        with self._lock:
            self.last_failure_time = time.time()
            
            if self.state == self.CLOSED:
                # Increment failure count in closed state
                self.failure_count += 1
                logger.debug(f"Circuit breaker for {self.name}: failure #{self.failure_count}")
                
                # Check if we need to trip the circuit
                if self.failure_count >= self.failure_threshold:
                    logger.warning(f"Circuit breaker for {self.name} tripped after {self.failure_count} failures")
                    self.state = self.OPEN
                    
            elif self.state == self.HALF_OPEN:
                # If test request failed, go back to open state
                logger.warning(f"Circuit breaker for {self.name} remains open after failed test request")
                self.state = self.OPEN
                self.last_test_time = time.time()
    
    def allow_request(self) -> bool:
        """Check if a request should be allowed through the circuit.
        
        Returns:
            True if request should be allowed, False if it should be rejected
        """
        with self._lock:
            now = time.time()
            
            if self.state == self.CLOSED:
                # In closed state, always allow requests
                return True
                
            elif self.state == self.OPEN:
                # Check if reset timeout has elapsed
                if now - self.last_failure_time >= self.reset_timeout:
                    # Transition to half-open state to test the service
                    logger.info(f"Circuit breaker for {self.name} transitioning to half-open state")
                    self.state = self.HALF_OPEN
                    self.last_test_time = now
                    return True
                else:
                    # Still in timeout period, reject request
                    return False
                    
            elif self.state == self.HALF_OPEN:
                # In half-open state, only allow one test request
                # If another request comes in while we're testing, reject it
                if now - self.last_test_time >= self.half_open_timeout:
                    self.last_test_time = now
                    return True
                else:
                    return False
            
            # Default case (shouldn't happen)
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the circuit breaker.
        
        Returns:
            Dictionary with circuit breaker status
        """
        with self._lock:
            return {
                'name': self.name,
                'state': self.state,
                'failure_count': self.failure_count,
                'last_failure_time': self.last_failure_time,
                'last_success_time': self.last_success_time,
                'last_test_time': self.last_test_time,
                'failure_threshold': self.failure_threshold,
                'reset_timeout': self.reset_timeout,
                'half_open_timeout': self.half_open_timeout
            }

class TaskRouter:
    """Routes tasks between different services and handles circuit breaking."""
    
    def __init__(self, test_ports: Optional[Tuple[int]] = None):
        """Initialize the Task Router Agent.
        
        Args:
            test_ports: Optional tuple of port numbers for testing
        """
        # Initialize dictionary attributes
        self.circuit_breakers = {}
        self.service_status = {}
        self.model_status = {}
        self.model_capabilities = {}
        self.running = True  # Add running flag
        
        # Initialize priority queue and batch processing
        self.task_queue = []  # Priority queue for tasks
        self.batch_buffer = {}  # Buffer for batching similar tasks
        self.batch_timestamps = {}  # Track when batches were started
        self.queue_lock = threading.Lock()  # Lock for thread-safe queue operations
        self.batch_lock = threading.Lock()  # Lock for thread-safe batch operations
        
        # Load configuration
        self._load_configuration()
        
        # Check if secure ZMQ is enabled
        self.secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"
        
        # Set default values for queue and batch parameters
        self.queue_max_size = getattr(self.config, 'queue_max_size', 100)
        self.batch_max_size = getattr(self.config, 'batch_max_size', 5)
        self.batch_timeout_ms = getattr(self.config, 'batch_timeout_ms', 200)
        
        logger.info(f"Task queue initialized with max_size={self.queue_max_size}, batch_max_size={self.batch_max_size}, batch_timeout_ms={self.batch_timeout_ms}")
        
        # Initialize ZMQ
        self._init_zmq(test_ports)
        
        # Initialize circuit breakers for all services
        self._init_circuit_breakers()
        
        # Start service status monitoring thread
        self._start_service_status_thread()
        
        # Start the task dispatcher thread
        self._start_task_dispatcher()
        
        # Set up health check server
        self._setup_health_check()
        
        logger.info("Task Router Agent initialized successfully")
    
    def _init_zmq(self, test_ports: Optional[Tuple[int]] = None):
        """Initialize ZMQ sockets with advanced routing capabilities."""
        try:
            self.context = zmq.Context()
            
            # Set up task router socket (REP)
            self.task_port = test_ports[0] if test_ports else TASK_ROUTER_PORT
            self.task_socket = self.context.socket(zmq.REP)
            self.task_socket.bind(f"tcp://*:{self.task_port}")
            logger.info(f"Task socket bound to port {self.task_port}")
            
            # Dynamically connect to downstream services based on provided arguments
            if COT_HOST and COT_PORT:
                self.cot_socket = self.context.socket(zmq.REQ)
                self.cot_socket.connect(f"tcp://{COT_HOST}:{COT_PORT}")
                logger.info(f"Connected to Chain of Thought service at tcp://{COT_HOST}:{COT_PORT}")
            
            if GOT_TOT_HOST and GOT_TOT_PORT:
                self.got_tot_socket = self.context.socket(zmq.REQ)
                self.got_tot_socket.connect(f"tcp://{GOT_TOT_HOST}:{GOT_TOT_PORT}")
                logger.info(f"Connected to Graph/Tree of Thought service at tcp://{GOT_TOT_HOST}:{GOT_TOT_PORT}")

            # Use service discovery to find and connect to EnhancedModelRouter
            self._connect_to_migrated_service("EnhancedModelRouter", "emr_socket")
            
            # Use service discovery to find and connect to ConsolidatedTranslator
            self._connect_to_migrated_service("ConsolidatedTranslator", "translator_socket")
            
        except Exception as e:
            logger.error(f"Error initializing ZMQ: {str(e)}")
            raise
    
    def _load_configuration(self):
        """Load configuration from files."""
        try:
            # Use the already loaded config dictionary
            self.config = args
            logger.info("Configuration loaded successfully")
            # Load model configuration - args is a Namespace object, not a dict
            self.model_config = getattr(args, 'model_config', {})
            logger.info(f"Loaded model configuration with {len(self.model_config.get('model_mapping', {})) if isinstance(self.model_config, dict) else 0} models")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self.config = {}
            self.model_config = {}
    
    def _init_circuit_breakers(self):
        """Initialize circuit breakers for all services."""
        # Create circuit breakers for migrated services (now on MainPC)
        self.circuit_breakers['emr'] = CircuitBreaker(
            name="EnhancedModelRouter",
            failure_threshold=CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            reset_timeout=CIRCUIT_BREAKER_RESET_TIMEOUT
        )
        
        self.circuit_breakers['translator'] = CircuitBreaker(
            name="ConsolidatedTranslator",
            failure_threshold=CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            reset_timeout=CIRCUIT_BREAKER_RESET_TIMEOUT
        )
        
        # Add circuit breakers for advanced routing
        self.circuit_breakers['cot'] = CircuitBreaker(
            name='Chain of Thought',
            failure_threshold=3,
            reset_timeout=30
        )
        
        self.circuit_breakers['got_tot'] = CircuitBreaker(
            name='Graph/Tree of Thought',
            failure_threshold=3,
            reset_timeout=30
        )
        
        logger.info(f"Initialized {len(self.circuit_breakers)} circuit breakers")
    
    def _start_service_status_thread(self):
        """Start service status monitoring thread."""
        # Start service status check thread
        self.status_thread = threading.Thread(target=self._service_status_loop)
        self.status_thread.daemon = True
        self.status_thread.start()
        logger.info("Service status thread started")
    
    def _service_status_loop(self):
        """Background thread for checking service status."""
        logger.info("Service status loop started")
        
        while self.running:
            try:
                # Check PC2 services
                self._check_pc2_services()
                
                # Sleep for a while
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in service status loop: {e}")
                time.sleep(5)  # Sleep for a short time before retrying
    
    def _check_pc2_services(self) -> Dict[str, bool]:
        """Check the status of services that were originally on PC2 but may now be on MainPC.
        
        Returns:
            Dictionary mapping service names to status (True=available, False=unavailable)
        """
        services = {}
        
        # Check Enhanced Model Router
        emr_status = self._check_service('emr')
        services['EnhancedModelRouter'] = emr_status
        
        # Check Consolidated Translator
        translator_status = self._check_service('translator')
        services['ConsolidatedTranslator'] = translator_status
        
        # Update service status
        self.service_status = services
        
        return services
    
    def _check_service(self, service_name: str) -> bool:
        """Check if a service is available.
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            True if service is available, False otherwise
        """
        # If circuit is open, don't even try
        if service_name in self.circuit_breakers and not self.circuit_breakers[service_name].allow_request():
            logger.debug(f"Circuit breaker for {service_name} is open, skipping health check")
            return False
        
        try:
            if service_name == 'emr':
                # Check if we need to (re)discover and connect to EnhancedModelRouter
                if not hasattr(self, 'emr_socket'):
                    self._connect_to_migrated_service("EnhancedModelRouter", "emr_socket")
                    if not hasattr(self, 'emr_socket'):
                        return False
                
                # Check Enhanced Model Router
                self.emr_socket.send_json({"action": "health_check"})
                response = self.emr_socket.recv_json()
                
                # Record success in circuit breaker
                if service_name in self.circuit_breakers:
                    self.circuit_breakers[service_name].record_success()
                
                return response.get('status') == 'ok'
                
            elif service_name == 'translator':
                # Check if we need to (re)discover and connect to ConsolidatedTranslator
                if not hasattr(self, 'translator_socket'):
                    self._connect_to_migrated_service("ConsolidatedTranslator", "translator_socket")
                    if not hasattr(self, 'translator_socket'):
                        return False
                    
                # Check Consolidated Translator
                self.translator_socket.send_json({"action": "health_check"})
                response = self.translator_socket.recv_json()
                
                # Record success in circuit breaker
                if service_name in self.circuit_breakers:
                    self.circuit_breakers[service_name].record_success()
                
                return response.get('status') == 'ok'
                
            else:
                logger.warning(f"Unknown service: {service_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking service {service_name}: {e}")
            
            # Record failure in circuit breaker
            if service_name in self.circuit_breakers:
                self.circuit_breakers[service_name].record_failure()
                
            return False
    
    def handle_message(self, message: Any) -> Dict[str, Any]:
        """Handle incoming messages.
        
        Args:
            message: The message to handle, expected to be a dictionary
            
        Returns:
            Response message dictionary
        """
        try:
            # Health check handler
            if isinstance(message, dict) and message.get("action") == "health_check":
                return {"status": "ok", "ready": True, "message": "TaskRouter healthy"}
            # Type check the message
            if not isinstance(message, dict):
                return {'status': 'error', 'message': 'Message must be a dictionary'}
                
            message_type = message.get('type')
            if message_type == 'task':
                # Process task
                task_data = message.get('data', {})
                task_priority = self._determine_task_priority(task_data)
                
                # Add task to the priority queue
                self._add_task_to_queue(task_data, task_priority)
                
                # Return immediate acknowledgment
                return {'status': 'queued', 'message': 'Task queued successfully', 'queue_size': len(self.task_queue)}
            elif message_type == 'health_check':
                # Handle health check
                return {'status': 'ok', 'message': 'TaskRouter is healthy'}
            elif message_type == 'queue_status':
                # Return queue status
                return self._get_queue_status()
            else:
                return {'status': 'error', 'message': 'Unknown message type'}
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _determine_task_priority(self, task: Dict[str, Any]) -> int:
        """
        Determine the priority of a task.
        Lower numbers indicate higher priority.
        
        Args:
            task: The task data dictionary
            
        Returns:
            int: Priority value (0-3, where 0 is highest)
        """
        # Check if task has explicit priority
        if 'priority' in task:
            priority_str = task['priority'].lower() if isinstance(task['priority'], str) else str(task['priority'])
            
            # Map string priorities to integer values
            if priority_str in ['critical', '0']:
                return 0
            elif priority_str in ['high', '1']:
                return 1
            elif priority_str in ['medium', '2']:
                return 2
            elif priority_str in ['low', '3']:
                return 3
            
            # Try to parse as integer
            try:
                priority = int(priority_str)
                # Clamp to valid range
                return max(0, min(3, priority))
            except ValueError:
                pass
        
        # Infer priority from task properties
        if task.get('is_urgent', False) or task.get('urgent', False):
            return 0
        if task.get('is_interactive', False) or task.get('user_waiting', False):
            return 1
        
        # Default to medium priority
        return 2
    
    def _add_task_to_queue(self, task: Dict[str, Any], priority: int) -> None:
        """
        Add a task to the priority queue.
        
        Args:
            task: The task data dictionary
            priority: Priority value (0-3, where 0 is highest)
        """
        with self.queue_lock:
            # Generate a unique task ID if not present
            if 'task_id' not in task:
                task['task_id'] = f"task_{int(time.time() * 1000)}_{len(self.task_queue)}"
            
            # Add timestamp for tracking
            task['queue_time'] = time.time()
            
            # Check if queue is at capacity
            if len(self.task_queue) >= self.queue_max_size:
                # Find and remove the lowest priority (highest number) task
                lowest_priority = -1
                lowest_idx = -1
                
                for idx, (p, _, _) in enumerate(self.task_queue):
                    if p > lowest_priority:
                        lowest_priority = p
                        lowest_idx = idx
                
                if lowest_priority > priority and lowest_idx >= 0:
                    # Remove the lowest priority task to make room
                    self.task_queue.pop(lowest_idx)
                    heapq.heapify(self.task_queue)
                    logger.warning(f"Queue full, dropped lower priority task to make room for priority {priority} task")
                else:
                    # Current task is lower priority than anything in the queue
                    logger.warning(f"Queue full, rejecting task with priority {priority}")
                    return
            
            # Use count to ensure FIFO ordering for tasks with the same priority
            count = len(self.task_queue)
            
            # Add to priority queue
            heapq.heappush(self.task_queue, (priority, count, task))
            logger.debug(f"Added task {task.get('task_id')} with priority {priority} to queue (size: {len(self.task_queue)})")
    
    def _get_queue_status(self) -> Dict[str, Any]:
        """
        Get the current status of the task queue and batch buffers.
        
        Returns:
            Dict containing queue statistics
        """
        with self.queue_lock:
            queue_size = len(self.task_queue)
            
            # Count tasks by priority
            priorities = {}
            for p, _, _ in self.task_queue:
                priorities[p] = priorities.get(p, 0) + 1
                
        with self.batch_lock:
            batch_sizes = {task_type: len(tasks) for task_type, tasks in self.batch_buffer.items()}
            
        return {
            'status': 'ok',
            'queue_size': queue_size,
            'queue_max_size': self.queue_max_size,
            'priorities': priorities,
            'batch_buffers': batch_sizes,
            'batch_max_size': self.batch_max_size,
            'batch_timeout_ms': self.batch_timeout_ms
        }
    
    def _start_task_dispatcher(self):
        """Start the task dispatcher thread that processes the queue."""
        self.dispatcher_thread = threading.Thread(target=self._dispatch_tasks_from_queue)
        self.dispatcher_thread.daemon = True
        self.dispatcher_thread.start()
        logger.info("Task dispatcher thread started")
    
    def _dispatch_tasks_from_queue(self):
        """
        Continuously dispatch tasks from the priority queue.
        Groups similar tasks into batches for efficient processing.
        """
        logger.info("Task dispatcher started")
        
        while self.running:
            try:
                # Process any batches that have reached timeout
                self._process_timed_out_batches()
                
                # Check if there are tasks in the queue
                with self.queue_lock:
                    if not self.task_queue:
                        # No tasks, sleep briefly and check again
                        time.sleep(0.01)  # 10ms
                        continue
                    
                    # Get the highest priority task
                    _, _, task = heapq.heappop(self.task_queue)
                
                # Determine the task type for batching
                task_type = self._get_task_type_for_batching(task)
                
                # Add to batch or process immediately
                if task_type and self._should_batch_task_type(task_type):
                    self._add_to_batch(task_type, task)
                else:
                    # Process this task individually
                    try:
                        response = self._process_task(task)
                        logger.debug(f"Processed individual task {task.get('task_id')}: {response.get('status', 'unknown')}")
                    except Exception as e:
                        logger.error(f"Error processing task {task.get('task_id')}: {e}")
                
            except Exception as e:
                logger.error(f"Error in task dispatcher: {e}")
                time.sleep(0.1)  # Sleep briefly to avoid tight error loop
    
    def _get_task_type_for_batching(self, task: Dict[str, Any]) -> str:
        """
        Determine the task type for batching purposes.
        
        Args:
            task: The task data dictionary
            
        Returns:
            str: Task type identifier for batching, or empty string if task shouldn't be batched
        """
        # Extract relevant information for grouping
        if 'model_type' in task:
            return f"model_{task['model_type']}"
        elif 'action' in task:
            return f"action_{task['action']}"
        elif 'command' in task:
            return f"command_{task['command']}"
        
        # Use classification to determine type
        routing_method = self.classify_task(task)
        if routing_method in ['basic', 'cot', 'got_tot']:
            return f"routing_{routing_method}"
            
        # Default - no batching
        return ""
    
    def _should_batch_task_type(self, task_type: str) -> bool:
        """
        Determine if this type of task should be batched.
        
        Args:
            task_type: The task type identifier
            
        Returns:
            bool: True if tasks of this type should be batched
        """
        # Only batch certain task types
        if task_type.startswith("model_"):
            # Most model requests can be batched
            return True
        elif task_type.startswith("routing_basic"):
            # Basic routing can be batched
            return True
        
        # Don't batch by default
        return False
    
    def _add_to_batch(self, task_type: str, task: Dict[str, Any]) -> None:
        """
        Add a task to the appropriate batch buffer.
        
        Args:
            task_type: The task type identifier
            task: The task data dictionary
        """
        with self.batch_lock:
            # Initialize batch if needed
            if task_type not in self.batch_buffer:
                self.batch_buffer[task_type] = []
                self.batch_timestamps[task_type] = time.time()
            
            # Add to batch
            self.batch_buffer[task_type].append(task)
            
            # Process batch if it's reached max size
            if len(self.batch_buffer[task_type]) >= self.batch_max_size:
                batch = self.batch_buffer[task_type]
                # Clear the batch
                self.batch_buffer[task_type] = []
                del self.batch_timestamps[task_type]
                
                # Release lock before processing
                self.batch_lock.release()
                try:
                    self._process_batch(task_type, batch)
                finally:
                    # Reacquire lock
                    self.batch_lock.acquire()
    
    def _process_timed_out_batches(self) -> None:
        """Process any batches that have exceeded their timeout."""
        now = time.time()
        timeout_secs = self.batch_timeout_ms / 1000.0
        
        with self.batch_lock:
            # Check each batch
            timed_out_types = []
            
            for task_type, timestamp in self.batch_timestamps.items():
                if now - timestamp > timeout_secs and self.batch_buffer[task_type]:
                    timed_out_types.append(task_type)
            
            # Process timed out batches
            for task_type in timed_out_types:
                batch = self.batch_buffer[task_type]
                # Clear the batch
                self.batch_buffer[task_type] = []
                del self.batch_timestamps[task_type]
                
                # Release lock before processing
                self.batch_lock.release()
                try:
                    if batch:  # Only process if there are tasks in the batch
                        logger.debug(f"Processing timed out batch of {len(batch)} tasks for {task_type}")
                        self._process_batch(task_type, batch)
                finally:
                    # Reacquire lock
                    self.batch_lock.acquire()
    
    def _process_batch(self, task_type: str, batch: List[Dict[str, Any]]) -> None:
        """
        Process a batch of similar tasks.
        
        Args:
            task_type: The task type identifier
            batch: List of task dictionaries
        """
        if not batch:
            return
            
        try:
            logger.info(f"Processing batch of {len(batch)} tasks of type {task_type}")
            
            # Different handling based on task type
            if task_type.startswith("model_"):
                model_type = task_type[6:]  # Remove "model_" prefix
                
                # Combine parameters into a batch request
                batch_request = {
                    "model_type": model_type,
                    "batch": True,
                    "requests": batch
                }
                
                # Route to appropriate model handler
                if model_type == 'emr':
                    response = self._route_to_emr(batch_request)
                elif model_type == 'translator':
                    response = self._route_to_translator(batch_request)
                else:
                    # Process individually if no batch handler
                    for task in batch:
                        self._process_task(task)
                    return
                    
                logger.debug(f"Batch processing result: {response.get('status', 'unknown')}")
                
            elif task_type.startswith("routing_"):
                routing_method = task_type[8:]  # Remove "routing_" prefix
                
                # Process each task individually for now
                # In the future, could implement batch processing for routers
                for task in batch:
                    self._process_task(task)
                    
            else:
                # Default: process individually
                for task in batch:
                    self._process_task(task)
                    
        except Exception as e:
            logger.error(f"Error processing batch of {task_type}: {e}")
            
            # On batch failure, try to process tasks individually
            try:
                logger.info(f"Attempting to process {len(batch)} tasks individually after batch failure")
                for task in batch:
                    try:
                        self._process_task(task)
                    except Exception as task_e:
                        logger.error(f"Error processing individual task after batch failure: {task_e}")
            except Exception as recovery_e:
                logger.error(f"Error during batch failure recovery: {recovery_e}")
    
    def _process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single task by routing it to the appropriate service.
        
        Args:
            task: The task data dictionary
            
        Returns:
            Dict: Response from the appropriate service
        """
        try:
            # Log task processing
            task_id = task.get('task_id', 'unknown')
            logger.debug(f"Processing task {task_id}")
            
            # Record task latency
            queue_time = task.get('queue_time', time.time())
            processing_delay = time.time() - queue_time
            if processing_delay > 1.0:  # Log if delay is over 1 second
                logger.info(f"Task {task_id} spent {processing_delay:.3f}s in queue")
            
            # Use the routing logic to determine the destination
            return self.route_task(task)
            
        except Exception as e:
            logger.error(f"Error processing task: {e}")
            return {
                'status': 'error',
                'message': f'Error processing task: {str(e)}'
            }

    def _handle_model_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle model routing requests.
        
        Args:
            request: Request dictionary containing model parameters
            
        Returns:
            Response dictionary with status and data
        """
        try:
            # Validate request
            model_type = request.get('model_type')
            if not model_type:
                return {
                    'status': 'error',
                    'error': 'Missing required field: model_type'
                }
            
            # Check if model type is supported
            if model_type not in self.model_capabilities:
                return {
                    'status': 'error',
                    'error': f'Unsupported model type: {model_type}'
                }
            
            # Get model capabilities
            capabilities = self.model_capabilities[model_type]
            
            # Validate required parameters
            required_params = capabilities.get('required_params', [])
            missing_params = [param for param in required_params if param not in request]
            if missing_params:
                return {
                    'status': 'error',
                    'error': f'Missing required parameters: {", ".join(missing_params)}'
                }
            
            # Route request based on model type
            if model_type == 'emr':
                return self._route_to_emr(request)
            elif model_type == 'translator':
                return self._route_to_translator(request)
            else:
                return {
                    'status': 'error',
                    'error': f'No routing handler for model type: {model_type}'
                }
                
        except Exception as e:
            logger.error(f"Error handling model request: {e}")
            return {
                'status': 'error',
                'error': f'Internal error: {str(e)}'
            }
    
    def _route_to_emr(self, request: Dict[str, Any], use_msgpack: bool = False) -> Dict[str, Any]:
        """Route request to Enhanced Model Router.
        
        Args:
            request: Request dictionary
            use_msgpack: Whether to use msgpack for serialization
            
        Returns:
            Response dictionary
        """
        try:
            # Get circuit breaker
            cb = self.circuit_breakers.get('emr')
            if not cb:
                return {
                    'status': 'error',
                    'error': 'EMR circuit breaker not initialized'
                }
            
            # Check if request is allowed
            if not cb.allow_request():
                return {
                    'status': 'error',
                    'error': 'EMR service is currently unavailable'
                }
            
            # Check if EMR socket exists (might not be connected yet)
            if not hasattr(self, 'emr_socket'):
                # Try to connect now
                self._connect_to_migrated_service("EnhancedModelRouter", "emr_socket")
                if not hasattr(self, 'emr_socket'):
                    cb.record_failure()
                    return {
                        'status': 'error',
                        'error': 'Failed to connect to EnhancedModelRouter'
                    }
            
            # Prepare request
            request_data = {
                'action': 'process',
                'model_type': request.get('model_type'),
                'parameters': request.get('parameters', {}),
                'options': request.get('options', {})
            }
            
            # Send request
            if use_msgpack:
                self.emr_socket.send(msgpack.packb(request_data))
                response = msgpack.unpackb(self.emr_socket.recv())
            else:
                self.emr_socket.send_json(request_data)
                response = self.emr_socket.recv_json()
            
            # Update circuit breaker
            if response.get('status') == 'ok':
                cb.record_success()
            else:
                cb.record_failure()
            
            return response
            
        except zmq.error.ZMQError as e:
            logger.error(f"ZMQ error routing to EMR: {e}")
            self.circuit_breakers['emr'].record_failure()
            return {
                'status': 'error',
                'error': f'Communication error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error routing to EMR: {e}")
            self.circuit_breakers['emr'].record_failure()
            return {
                'status': 'error',
                'error': f'Internal error: {str(e)}'
            }
    
    def _route_to_translator(self, request: Dict[str, Any], use_msgpack: bool = False) -> Dict[str, Any]:
        """Route a request to the Consolidated Translator.
        
        Args:
            request: Request dictionary
            use_msgpack: Whether to use msgpack serialization
            
        Returns:
            Response dictionary
        """
        # Check circuit breaker
        if not self.circuit_breakers['translator'].allow_request():
            logger.warning("Circuit breaker for Translator is open, rejecting request")
            return {
                'status': 'error',
                'error': 'Service unavailable (circuit open)'
            }
        
        try:
            # Check if Translator socket exists (might not be connected yet)
            if not hasattr(self, 'translator_socket'):
                # Try to connect now
                self._connect_to_migrated_service("ConsolidatedTranslator", "translator_socket")
                if not hasattr(self, 'translator_socket'):
                    self.circuit_breakers['translator'].record_failure()
                    return {
                        'status': 'error',
                        'error': 'Failed to connect to ConsolidatedTranslator'
                    }
                
            if use_msgpack:
                # Use msgpack serialization
                packed_request = msgpack.packb(request)
                self.translator_socket.send(packed_request)
                
                # Wait for response
                packed_response = self.translator_socket.recv()
                response = msgpack.unpackb(packed_response)
                
            else:
                # Use JSON serialization
                self.translator_socket.send_json(request)
                
                # Wait for response
                response = self.translator_socket.recv_json()
            
            # Record success in circuit breaker
            self.circuit_breakers['translator'].record_success()
            
            return response
            
        except Exception as e:
            logger.error(f"Error routing to Consolidated Translator: {e}")
            
            # Record failure in circuit breaker
            self.circuit_breakers['translator'].record_failure()
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _setup_health_check(self):
        """Set up the health check server."""
        try:
            setup_health_check_server(TASK_ROUTER_HEALTH_PORT)
            logger.info(f"Health check server started on port {TASK_ROUTER_HEALTH_PORT}")
        except Exception as e:
            logger.error(f"Failed to start health check server: {e}")
            raise
    
    def run(self):
        """Main run loop."""
        logger.info("Task Router Agent starting...")
        
        try:
            while self.running:
                try:
                    # Wait for request
                    request = self.task_socket.recv_json()
                    logger.debug(f"Received request: {request}")
                    
                    # Process request
                    response = self.handle_message(request)
                    
                    # Send response
                    self.task_socket.send_json(response)
                    
                except zmq.error.ZMQError as e:
                    logger.error(f"ZMQ error in run loop: {e}")
                    # Try to send an error response
                    try:
                        self.task_socket.send_json({
                            'status': 'error',
                            'error': str(e)
                        })
                    except:
                        pass
                    
                except Exception as e:
                    logger.error(f"Error in run loop: {e}")
                    # Try to send an error response
                    try:
                        self.task_socket.send_json({
                            'status': 'error',
                            'error': str(e)
                        })
                    except:
                        pass
                    
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
            
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up resources...")
        self.running = False
        
        # Stop service status thread
        if hasattr(self, 'status_thread'):
            self.status_thread.join(timeout=1)
            
        # Stop dispatcher thread
        if hasattr(self, 'dispatcher_thread'):
            self.dispatcher_thread.join(timeout=1)
        
        # Close ZMQ sockets
        if hasattr(self, 'task_socket'):
            self.task_socket.close()
        
        if hasattr(self, 'model_manager_socket'):
            self.model_manager_socket.close()
        
        if hasattr(self, 'emr_socket'):
            self.emr_socket.close()
        
        if hasattr(self, 'translator_socket'):
            self.translator_socket.close()
        
        # Close ZMQ context
        if hasattr(self, 'context'):
            self.context.term()
            
        # Stop HTTP health check server
        setup_health_check_server(TASK_ROUTER_HEALTH_PORT, stop=True)
        
        logger.info("Cleanup complete")

    def classify_task(self, task: Dict[str, Any]) -> str:
        """Classify task complexity and determine routing method.
        
        Args:
            task: Task dictionary containing request details
            
        Returns:
            str: Routing method ('basic', 'cot', or 'got_tot')
        """
        try:
            # Extract task details
            task_type = task.get('type', '')
            complexity = task.get('complexity', 0)
            steps = task.get('steps', 1)
            
            # Classification logic
            if complexity > 0.7 or steps > 3:
                return 'got_tot'
            elif complexity > 0.4 or steps > 1:
                return 'cot'
            else:
                return 'basic'
                
        except Exception as e:
            logger.error(f"Error classifying task: {str(e)}")
            return 'basic'  # Default to basic routing

    def route_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Route task to appropriate service based on classification.
        
        Args:
            task: Task dictionary containing request details
            
        Returns:
            Dict: Response from the appropriate service
        """
        try:
            # Classify task
            routing_method = self.classify_task(task)
            
            # Route based on classification
            if routing_method == 'got_tot':
                return self._route_to_got_tot(task)
            elif routing_method == 'cot':
                return self._route_to_cot(task)
            else:
                return self._route_to_emr(task)
                
        except Exception as e:
            logger.error(f"Error routing task: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error routing task: {str(e)}'
            }

    def _route_to_cot(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Route task to Chain of Thought service.
        
        Args:
            task: Task dictionary containing request details
            
        Returns:
            Dict: Response from Chain of Thought service
        """
        try:
            # Check circuit breaker
            if not self.circuit_breakers['cot'].allow_request():
                return {
                    'status': 'error',
                    'message': 'Chain of Thought service unavailable'
                }
            
            # Send request
            self.cot_socket.send_json(task)
            
            # Wait for response
            response = self.cot_socket.recv_json()
            
            # Update circuit breaker
            if response.get('status') == 'success':
                self.circuit_breakers['cot'].record_success()
            else:
                self.circuit_breakers['cot'].record_failure()
            
            return response
            
        except Exception as e:
            logger.error(f"Error routing to Chain of Thought: {str(e)}")
            self.circuit_breakers['cot'].record_failure()
            return {
                'status': 'error',
                'message': f'Error routing to Chain of Thought: {str(e)}'
            }

    def _route_to_got_tot(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Route task to Graph/Tree of Thought service.
        
        Args:
            task: Task dictionary containing request details
            
        Returns:
            Dict: Response from Graph/Tree of Thought service
        """
        try:
            # Check circuit breaker
            if not self.circuit_breakers['got_tot'].allow_request():
                return {
                    'status': 'error',
                    'message': 'Graph/Tree of Thought service unavailable'
                }
            
            # Send request
            self.got_tot_socket.send_json(task)
            
            # Wait for response
            response = self.got_tot_socket.recv_json()
            
            # Update circuit breaker
            if response.get('status') == 'success':
                self.circuit_breakers['got_tot'].record_success()
            else:
                self.circuit_breakers['got_tot'].record_failure()
            
            return response
            
        except Exception as e:
            logger.error(f"Error routing to Graph/Tree of Thought: {str(e)}")
            self.circuit_breakers['got_tot'].record_failure()
            return {
                'status': 'error',
                'message': f'Error routing to Graph/Tree of Thought: {str(e)}'
            }

    def _connect_to_migrated_service(self, service_name: str, socket_attr_name: str):
        """
        Connect to a service that might have been migrated from PC2 to MainPC.
        Uses service discovery to find the current location and connection details.
        
        Args:
            service_name: Name of the service to connect to
            socket_attr_name: Name of the attribute to store the socket in
        """
        try:
            # Try to discover the service via SystemDigitalTwin
            logger.info(f"Discovering {service_name} via service discovery...")
            discovery_response = discover_service(service_name)
            
            if discovery_response.get("status") == "SUCCESS" and "payload" in discovery_response:
                service_info = discovery_response.get("payload")
                service_ip = service_info.get("ip")
                service_port = service_info.get("port")
                service_location = service_info.get("location", "unknown")
                
                if service_ip and service_port:
                    # Create socket and set options
                    socket = self.context.socket(zmq.REQ)
                    socket.setsockopt(zmq.LINGER, 0)
                    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
                    
                    # Apply security if enabled
                    if self.secure_zmq:
                        try:
                            from main_pc_code.src.network.secure_zmq import configure_secure_client, start_auth
                            # Start auth if needed
                            start_auth()
                            # Configure socket with security
                            socket = configure_secure_client(socket)
                            logger.info(f"Applied secure ZMQ configuration to {service_name} connection")
                        except Exception as e:
                            logger.warning(f"Failed to configure secure ZMQ for {service_name}: {e}")
                    
                    # Connect to service
                    service_address = f"tcp://{service_ip}:{service_port}"
                    socket.connect(service_address)
                    
                    # Store socket in the specified attribute
                    setattr(self, socket_attr_name, socket)
                    
                    logger.info(f"Connected to {service_name} at {service_address} (location: {service_location})")
                else:
                    logger.error(f"Missing IP or port in {service_name} discovery response")
            else:
                logger.warning(f"Failed to discover {service_name}: {discovery_response.get('message', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error connecting to {service_name}: {e}")
            # Continue without failing - the circuit breaker will handle the missing connection

if __name__ == "__main__":
    # Create and run the task router agent
    router = TaskRouter()
    router.run() 