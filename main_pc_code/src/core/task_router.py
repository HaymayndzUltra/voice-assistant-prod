"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

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
from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.src.core.http_server import setup_health_check_server
from main_pc_code.utils.config_loader import load_config
# Import service discovery and network utilities
from main_pc_code.utils.service_discovery_client import discover_service, get_service_address
from main_pc_code.utils.network_utils import load_network_config, get_current_machine
from main_pc_code.src.network.secure_zmq import configure_secure_client, configure_secure_server
import pickle
from main_pc_code.src.memory.zmq_encoding_utils import safe_encode_json, safe_decode_json
import psutil
from datetime import datetime

# Module-level configuration loading
config = load_config()

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

# === ALL CONFIGURATION FROM config ===
DEFAULT_PORT = int(os.environ.get("TASK_ROUTER_PORT", "7000"))  # Default port if not specified in config
TASK_ROUTER_PORT = config.get("port", DEFAULT_PORT)
TASK_ROUTER_HEALTH_PORT = TASK_ROUTER_PORT + 1
CRIT_BREAK_FAIL = config.get("circuit_breaker_failure_threshold", 3)
CRIT_BREAK_RESET = config.get("circuit_breaker_reset_timeout", 30)
CRIT_BREAK_HALF_OPEN = config.get("circuit_breaker_half_open_timeout", 5)
INTERRUPT_PORT = config.get("interrupt_port", 5576)

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
    
    def __init__(self, name: str, failure_threshold: int = CRIT_BREAK_FAIL, 
                 reset_timeout: int = CRIT_BREAK_RESET,
                 half_open_timeout: int = CRIT_BREAK_HALF_OPEN):
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

class TaskRouter(BaseAgent):
    """Routes tasks between different services and handles circuit breaking."""

    def __init__(self, **kwargs):
        # === CONFIGURATION FROM config ===
        self.port = config.get("port", DEFAULT_PORT)
        self.name = config.get("name", 'TaskRouter')
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(name=self.name, port=self.port)
        
        self.circuit_breakers = {}
        self.service_status = {}
        self.running = True
        self.interrupt_flag = threading.Event()

        self.task_queue = []  # Priority queue
        self.queue_lock = threading.Lock()

        self._load_configuration()

        self.secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"
        self.queue_max_size = self.config.get('queue_max_size', 100)

        self.context = zmq.Context()
        self.task_socket = None
        self.cot_socket = None
        self.got_tot_socket = None
        self.interrupt_socket = None

        self._init_zmq(kwargs.get('test_ports'))
        self._init_circuit_breakers()

        self.dispatcher_thread = None
        self.interrupt_thread = None
        self._start_threads()

        self._setup_health_check()
        logger.info("Task Router Agent initialized successfully")

    def _load_configuration(self):
        """Load configuration from command-line arguments."""
        try:
            self.config = vars(config)
            logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self.config = {}

    def _init_zmq(self, test_ports: Optional[Tuple[int]] = None):
        """Initialize ZMQ sockets."""
        # REP socket for incoming tasks
        self.task_port = test_ports[0] if test_ports else self.port
        self.task_socket = self.context.socket(zmq.REP)
        
        if self.secure_zmq:
            self.task_socket = configure_secure_server(self.task_socket)
        
        self.task_socket.bind(f"tcp://*:{self.task_port}")
        logger.info(f"Task router listening on port {self.task_port}")
        
        # Initialize interrupt socket
        self.interrupt_socket = self.context.socket(zmq.SUB)
        if self.secure_zmq:
            self.interrupt_socket = configure_secure_client(self.interrupt_socket)
        self.interrupt_socket.connect(f"tcp://localhost:{INTERRUPT_PORT}")
        self.interrupt_socket.setsockopt(zmq.SUBSCRIBE, b"")
        logger.info(f"Connected to interrupt service on port {INTERRUPT_PORT}")
        
        # Initialize service connection sockets using service discovery
        self._connect_to_service("ChainOfThoughtAgent", "cot_socket")
        self._connect_to_service("GOT_TOTAgent", "got_tot_socket")
        
        logger.info("ZMQ sockets initialized")

    def _connect_to_service(self, service_name: str, socket_attr: str):
        """Connect to a service using service discovery.
        
        Args:
            service_name: Name of the service to connect to
            socket_attr: Name of the attribute to store the socket in
        """
        try:
            service_info = discover_service(service_name)
            
            if service_info and service_info.get("status") == "SUCCESS":
                service_payload = service_info.get("payload", {})
                service_ip = service_payload.get("ip", "localhost")
                service_port = service_payload.get("port")
                
                if service_port:
                    service_address = f"tcp://{service_ip}:{service_port}"
                    logger.info(f"Discovered {service_name} at {service_address}")
                    
                    # Create socket and connect
                    socket = self.context.socket(zmq.REQ)
                    if self.secure_zmq:
                        socket = configure_secure_client(socket)
                    socket.connect(service_address)
                    
                    # Store socket in the specified attribute
                    setattr(self, socket_attr, socket)
                    logger.info(f"Connected to {service_name}")
                else:
                    logger.error(f"No port information found for {service_name}")
            else:
                logger.error(f"Failed to discover {service_name}")
        except Exception as e:
            logger.error(f"Error connecting to {service_name}: {e}")

    def _init_circuit_breakers(self):
        """Initialize circuit breakers for all services."""
        services = ['cot', 'got_tot']
        for service in services:
            self.circuit_breakers[service] = CircuitBreaker(name=service)
        logger.info(f"Initialized {len(self.circuit_breakers)} circuit breakers")

    def _start_threads(self):
        """Start the dispatcher and interrupt threads."""
        self.dispatcher_thread = threading.Thread(target=self._dispatch_loop, daemon=True)
        self.dispatcher_thread.start()
        
        self.interrupt_thread = threading.Thread(target=self._listen_for_interrupts, daemon=True)
        self.interrupt_thread.start()

    def _listen_for_interrupts(self):
        """Listen for interrupt signals."""
        logger.info("Starting interrupt listener thread")
        while self.running:
            try:
                # Check for interrupt signals
                msg = self.interrupt_socket.recv(flags=zmq.NOBLOCK)
                data = pickle.loads(msg)
                
                if data.get('type') == 'interrupt':
                    logger.info("Received interrupt signal")
                    self.interrupt_flag.set()
                    self._clear_queues()
            except zmq.Again:
                # No message available
                time.sleep(0.05)
            except Exception as e:
                logger.error(f"Error in interrupt listener: {e}")
                time.sleep(1)  # Avoid tight loop on error

    def _clear_queues(self):
        """Clear all task queues when interrupted."""
        with self.queue_lock:
            logger.info(f"Clearing task queue (size: {len(self.task_queue)})")
            self.task_queue.clear()
            # Reset any processing state
            # Add any other queue clearing logic here

    def _dispatch_loop(self):
        """Main loop for dispatching tasks from the queue."""
        while self.running:
            try:
                with self.queue_lock:
                    if not self.task_queue:
                        time.sleep(0.05)
                        continue
                    priority, task_id, task = heapq.heappop(self.task_queue)

                if self.interrupt_flag.is_set():
                    logger.warning(f"Interrupt active, dropping task {task_id}")
                    continue

                self._process_task(task)
            except IndexError:
                time.sleep(0.05)
            except Exception as e:
                logger.error(f"Exception in dispatcher loop: {e}", exc_info=True)
                time.sleep(1)

    def _process_task(self, task: Dict[str, Any]):
        """Process a single task from the queue."""
        if self.interrupt_flag.is_set():
            logger.warning("Interrupt flag is set. Dropping task.")
            # Optionally send a response indicating interruption
            return

        task_type = task.get('task_type')
        if task_type == 'cot':
            self._route_to_cot(task)
        elif task_type == 'got_tot':
            self._route_to_got_tot(task)
        else:
            logger.warning(f"Unknown task type: {task_type}")

    def _route_to_cot(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Route a task to the Chain of Thought agent."""
        if self.cot_socket is None:
            # Try to reconnect if socket is not available
            self._connect_to_service("ChainOfThoughtAgent", "cot_socket")
            if self.cot_socket is None:
                return {"status": "error", "message": "ChainOfThoughtAgent not available"}
        
        try:
            # Check for interrupt before sending
            if self.interrupt_flag.is_set():
                self.interrupt_flag.clear()
                return {"status": "interrupted", "message": "Task was interrupted"}
                
            # Send the task
            self.cot_socket.send_json(task)
            
            # Set up poller for timeout
            poller = zmq.Poller()
            poller.register(self.cot_socket, zmq.POLLIN)
            
            # Wait for response with timeout
            if poller.poll(10000):  # 10 second timeout
                response = self.cot_socket.recv_json()
                return response
            else:
                logger.error("Timeout waiting for ChainOfThoughtAgent response")
                return {"status": "error", "message": "Timeout waiting for response"}
                
        except Exception as e:
            logger.error(f"Error routing to ChainOfThoughtAgent: {e}")
            return {"status": "error", "message": str(e)}

    def _route_to_got_tot(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Route a task to the Graph/Tree of Thought agent."""
        if self.got_tot_socket is None:
            # Try to reconnect if socket is not available
            self._connect_to_service("GOT_TOTAgent", "got_tot_socket")
            if self.got_tot_socket is None:
                return {"status": "error", "message": "GOT_TOTAgent not available"}
        
        try:
            # Check for interrupt before sending
            if self.interrupt_flag.is_set():
                self.interrupt_flag.clear()
                return {"status": "interrupted", "message": "Task was interrupted"}
                
            # Send the task
            self.got_tot_socket.send_json(task)
            
            # Set up poller for timeout
            poller = zmq.Poller()
            poller.register(self.got_tot_socket, zmq.POLLIN)
            
            # Wait for response with timeout
            if poller.poll(30000):  # 30 second timeout (longer for complex reasoning)
                response = self.got_tot_socket.recv_json()
                return response
            else:
                logger.error("Timeout waiting for GOT_TOTAgent response")
                return {"status": "error", "message": "Timeout waiting for response"}
                
        except Exception as e:
            logger.error(f"Error routing to GOT_TOTAgent: {e}")
            return {"status": "error", "message": str(e)}

    def _enqueue_task(self, task: Dict[str, Any]) -> bool:
        """Add a task to the priority queue."""
        with self.queue_lock:
            if len(self.task_queue) >= self.queue_max_size:
                logger.warning("Task queue is full. Rejecting new task.")
                return False
            priority = task.get('priority', 10)
            task_id = task.get('id', f"task_{time.time()}")
            heapq.heappush(self.task_queue, (priority, task_id, task))
            logger.info(f"Task {task_id} enqueued with priority {priority}.")
            return True

    def _setup_health_check(self):
        """Set up the health check server."""
        try:
            # Create health check socket
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            bind_address = config.get("bind_address", 'localhost')
            self.health_socket.bind(f"tcp://{bind_address}:{TASK_ROUTER_HEALTH_PORT}")
            logger.info(f"Health check socket bound to port {TASK_ROUTER_HEALTH_PORT}")
            
            # Start health check thread
            self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
            self.health_thread.start()
            logger.info("Health check thread started")
        except Exception as e:
            logger.error(f"Failed to start health check server: {e}")
    
    def _health_check_loop(self):
        """Background loop to handle health check requests."""
        logger.info("Health check loop started")
        
        while self.running:
            try:
                # Check for health check requests with timeout
                if self.health_socket.poll(100, zmq.POLLIN):
                    # Receive request (don't care about content)
                    _ = self.health_socket.recv()
                    
                    # Get health data
                    health_data = self._get_health_status()
                    
                    # Send response
                    self.health_socket.send_json(health_data)
                    
                time.sleep(0.1)  # Small sleep to prevent CPU hogging
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(1)  # Sleep longer on error
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        circuit_status = {name: cb.get_status() for name, cb in self.circuit_breakers.items()}
        
        return {
            "agent": self.name,
            "status": "ok",
            "timestamp": time.time(),
            "queue_size": len(self.task_queue),
            "interrupt_active": self.interrupt_flag.is_set(),
            "circuit_breakers": circuit_status
        }

    def run(self):
        """Main loop to receive and route tasks."""
        logger.info("Task Router is running...")
        try:
            while self.running:
                if self.interrupt_flag.is_set():
                    # If interrupted, wait a bit before resetting
                    time.sleep(1)
                    self.interrupt_flag.clear()
                    logger.info("Interrupt flag cleared. Resuming normal operations.")

                try:
                    message = self.task_socket.recv_json(flags=zmq.NOBLOCK)
                    logger.info(f"Received task: {message}")
                    
                    # Basic validation
                    if 'task_type' not in message or 'payload' not in message:
                        self.task_socket.send_json({'status': 'error', 'message': 'Invalid task format'})
                        continue
                    
                    # Enqueue the task
                    self._enqueue_task(message)
                    
                    # Acknowledge receipt of the task
                    self.task_socket.send_json({'status': 'ok', 'message': 'Task enqueued'})
                    
                except zmq.Again:
                    time.sleep(0.01)  # Avoid busy-waiting
                except zmq.ZMQError as e:
                    if e.errno == zmq.ETERM:
                        break  # Context terminated, exit loop
                    logger.error(f"ZMQ error in main loop: {e}")
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    try:
                        self.task_socket.send_json({'status': 'error', 'message': str(e)})
                    except zmq.ZMQError:
                        pass  # Socket might be closed
        finally:
            self._shutdown()

    def _shutdown(self):
        """Clean up resources."""
        logger.info("Shutting down Task Router")
        self.running = False
        
        # Close all sockets
        if hasattr(self, 'task_socket') and self.task_socket:
            self.task_socket.close()
            
        if hasattr(self, 'cot_socket') and self.cot_socket:
            self.cot_socket.close()
            
        if hasattr(self, 'got_tot_socket') and self.got_tot_socket:
            self.got_tot_socket.close()
            
        if hasattr(self, 'interrupt_socket') and self.interrupt_socket:
            self.interrupt_socket.close()
            
        if hasattr(self, 'health_socket') and self.health_socket:
            self.health_socket.close()
            
        # Wait for threads to finish
        if hasattr(self, 'health_thread') and self.health_thread.is_alive():
            self.health_thread.join(timeout=2.0)
            logger.info("Health thread joined")
        
        # Terminate ZMQ context
        if hasattr(self, 'context') and self.context:
            self.context.term()
            
        logger.info("Task Router shut down successfully")


    def health_check(self):
        '''
        Performs a health check on the agent, returning a dictionary with its status.
        '''
        try:
            # Basic health check logic
            is_healthy = True # Assume healthy unless a check fails
            
            # TODO: Add agent-specific health checks here.
            # For example, check if a required connection is alive.
            # if not self.some_service_connection.is_alive():
            #     is_healthy = False

            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else -1,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {} # Placeholder for agent-specific data
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            return {
                "status": "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "error": f"Health check failed with exception: {str(e)}"
            }

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = TaskRouter()
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