"""
Task Router Agent
- Routes tasks to appropriate models and services
- Implements Circuit Breaker pattern for resilient connections
- Manages communication with downstream services
- Advanced routing with Chain of Thought and Graph/Tree of Thought
"""
import zmq
import json
import time
import logging
import threading
import sys
import os
import socket
import errno
import msgpack
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple
from src.core.http_server import setup_health_check_server

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

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load configuration from JSON
config_path = Path(__file__).parent.parent.parent / 'config' / 'system_config.json'
try:
    with open(config_path, encoding='utf-8', errors='replace') as f:
        config = json.load(f)
except Exception as e:
    logger.error(f"Error loading config: {e}")
    config = {}

# Port configuration from system_config.json
TASK_ROUTER_PORT = config.get('agents', {}).get('task_router', {}).get('port', 8570)
TASK_ROUTER_HEALTH_PORT = TASK_ROUTER_PORT + 1  # Health check port is main port + 1
MODEL_MANAGER_PORT = config.get('model_management', {}).get('manager', {}).get('port', 5556)
PC2_EMR_PORT = config.get('agents', {}).get('enhanced_model_router', {}).get('port', 5598)
PC2_TRANSLATOR_PORT = config.get('agents', {}).get('consolidated_translator', {}).get('port', 5563)

# Add new port configurations
COT_PORT = config.get('agents', {}).get('chain_of_thought', {}).get('port', 5612)
GOT_TOT_PORT = config.get('agents', {}).get('got_tot', {}).get('port', 5646)

# Host addresses - since we're on Main PC, use localhost
MODEL_MANAGER_HOST = 'localhost'
HEALTHMONITOR_HOST = 'localhost'
HEALTHMONITOR_PORT = config.get('agents', {}).get('health_monitor', {}).get('port', 5584)
# Since we're on Main PC, use localhost
PC2_IP = 'localhost'  # We're on Main PC

# Circuit breaker configuration
CIRCUIT_BREAKER_FAILURE_THRESHOLD = config.get('agents', {}).get('circuit_breaker', {}).get('failure_threshold', 3)
CIRCUIT_BREAKER_RESET_TIMEOUT = config.get('agents', {}).get('circuit_breaker', {}).get('reset_timeout', 30)
CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT = config.get('agents', {}).get('circuit_breaker', {}).get('half_open_timeout', 5)

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
        
        # Load configuration
        self._load_configuration()
        
        # Initialize ZMQ
        self._init_zmq(test_ports)
        
        # Initialize circuit breakers for all services
        self._init_circuit_breakers()
        
        # Start service status monitoring thread
        self._start_service_status_thread()
        
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
            
            # Set up Chain of Thought socket
            self.cot_socket = self.context.socket(zmq.REQ)
            self.cot_socket.connect(f"tcp://127.0.0.1:{COT_PORT}")
            logger.info(f"Connected to Chain of Thought service on port {COT_PORT}")
            
            # Set up Graph/Tree of Thought socket
            self.got_tot_socket = self.context.socket(zmq.REQ)
            self.got_tot_socket.connect(f"tcp://127.0.0.1:{GOT_TOT_PORT}")
            logger.info(f"Connected to Graph/Tree of Thought service on port {GOT_TOT_PORT}")
            
            # Removed connection to Model Manager since TaskRouter is now the replacement for it
            # No need for self-referential connection
            
            # Set up connection to Enhanced Model Router on PC2
            self.emr_socket = self.context.socket(zmq.REQ)
            self.emr_socket.setsockopt(zmq.LINGER, 0)
            self.emr_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            self.emr_socket.connect(f"tcp://{PC2_IP}:{PC2_EMR_PORT}")
            logger.info(f"Connected to Enhanced Model Router on {PC2_IP}:{PC2_EMR_PORT}")
            
            # Set up connection to Consolidated Translator on PC2
            self.translator_socket = self.context.socket(zmq.REQ)
            self.translator_socket.setsockopt(zmq.LINGER, 0)
            self.translator_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            self.translator_socket.connect(f"tcp://{PC2_IP}:{PC2_TRANSLATOR_PORT}")
            logger.info(f"Connected to Consolidated Translator on {PC2_IP}:{PC2_TRANSLATOR_PORT}")
            
        except Exception as e:
            logger.error(f"Error initializing ZMQ: {str(e)}")
            raise
    
    def _load_configuration(self):
        """Load configuration from files."""
        try:
            # Use the already loaded config dictionary
            self.config = config
            logger.info("Configuration loaded successfully")
            # Load model configuration
            self.model_config = self.config.get('model_config', {})
            logger.info(f"Loaded model configuration with {len(self.model_config.get('model_mapping', {}))} models")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self.config = {}
            self.model_config = {}
    
    def _init_circuit_breakers(self):
        """Initialize circuit breakers for all services."""
        # Create circuit breakers for PC2 services
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
        
        # Add new circuit breakers for advanced routing
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
        """Check the status of PC2 services.
        
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
                # Check Enhanced Model Router
                self.emr_socket.send_json({"action": "health_check"})
                response = self.emr_socket.recv_json()
                
                # Record success in circuit breaker
                if service_name in self.circuit_breakers:
                    self.circuit_breakers[service_name].record_success()
                
                return response.get('status') == 'ok'
                
            elif service_name == 'translator':
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
                return self._process_task(task_data)
            elif message_type == 'health_check':
                # Handle health check
                return {'status': 'ok', 'message': 'TaskRouter is healthy'}
            else:
                return {'status': 'error', 'message': 'Unknown message type'}
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return {'status': 'error', 'message': str(e)}
    
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

if __name__ == "__main__":
    # Create and run the task router agent
    router = TaskRouter()
    router.run() 