"""
Base Agent Class with Proper Initialization and Health Check Patterns
"""
import sys
import os
import zmq
import json
import time
import logging
import threading
import uuid
import socket
from typing import Dict, Any, cast, Optional, Union, List, Tuple, TypeVar, cast
from datetime import datetime
from abc import ABC, abstractmethod

# Import the PathManager for consistent path resolution
from utils.path_manager import PathManager

# Now that the path is set, we can use absolute imports
from main_pc_code.utils.config_loader import parse_agent_args
from common.utils.data_models import (
    SystemEvent, ErrorReport, ErrorSeverity, AgentRegistration
)

# Use centralized JSON logger
from common.utils.logger_util import get_json_logger

# Configure logger
logger = logging.getLogger(__name__)

# Type variables for better type hinting
T = TypeVar('T')

class BaseAgent:
    """Base class for all agents with proper initialization and health check patterns."""
    
    def __init__(self, *args, **kwargs):
        # Set up project root using PathManager
        project_root = str(PathManager.get_project_root())
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
            
        self.args = parse_agent_args()
        self.name = kwargs.get('name') or self.__class__.__name__
        
        # Safe port handling with proper type conversion
        port = kwargs.get('port')
        if port is not None:
            try:
                self.port = int(port)
            except (ValueError, TypeError):
                logger.warning(f"Invalid port value: {port}, using default")
                self.port = self._find_available_port()
        else:
            self.port = self._find_available_port()
        
        # Prioritize health_check_port from kwargs, then from config, then fallback to port+1
        # with safe type conversion
        config = getattr(self, 'config', {}) or {}
        health_check_port = kwargs.get('health_check_port') or config.get('health_check_port')
        
        if health_check_port is not None:
            try:
                self.health_check_port = int(health_check_port)
            except (ValueError, TypeError):
                logger.warning(f"Invalid health_check_port value: {health_check_port}, using port+1")
                self.health_check_port = self.port + 1
        else:
            self.health_check_port = self.port + 1
        
        self.context = zmq.Context()
        self.strict_port = kwargs.get('strict_port', True)  # If True, do not auto-switch ports on bind failure
        
        # Initialize state
        self.running = True
        self.is_initialized = threading.Event()
        self.initialization_error = None
        self.start_time = time.time()
        
        # Set up logging directory using PathManager
        self._setup_logging()
        
        # Initialize sockets with proper error handling
        self._init_sockets()
        
        # Start health check thread immediately
        self._start_health_check()
        
        # Start initialization in background
        self._start_initialization()
        
        # Get agent capabilities for registration
        self.capabilities = kwargs.get('capabilities', self._get_default_capabilities())
        
        # Set up auto-registration with SystemDigitalTwin
        self._register_with_digital_twin()
        
        logger.info(f"{self.name} initialized on port {self.port} (health check: {self.health_check_port})")
    
    def _setup_logging(self):
        """Configure per-agent JSON structured logging."""
        logs_dir = PathManager.get_logs_dir()
        logs_dir.mkdir(parents=True, exist_ok=True)

        agent_log_file = logs_dir / f"{self.name.lower()}.log"

        # Replace existing handlers with JSON handlers only once
        self.logger = get_json_logger(self.name, logfile=str(agent_log_file))

        # Attach agent_name attribute to records automatically via LoggerAdapter
        self.logger = logging.LoggerAdapter(self.logger, extra={"agent_name": self.name})

        self.logger.info(f"Initialized JSON logging -> {agent_log_file}")
    
    def _find_available_port(self, start_port: int = 5000, max_attempts: int = 100) -> int:
        """Find an available port starting from start_port.
        
        Args:
            start_port: The port to start searching from
            max_attempts: Maximum number of ports to try
            
        Returns:
            An available port number
            
        Raises:
            RuntimeError: If no available ports are found
        """
        import socket
        
        for port in range(start_port, start_port + max_attempts):
            try:
                # Try to bind to the port
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('localhost', port))
                sock.close()
                return port
            except OSError:
                continue
                
        raise RuntimeError(f"No available ports found in range {start_port}-{start_port + max_attempts}")
    
    def _init_sockets(self):
        """Initialize ZMQ sockets with retry logic."""
        max_retries = 5  # Increased from 3 to 5 for more robustness
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                self.logger.debug(f"BaseAgent._init_sockets: Attempt {attempt+1} binding main socket to port {self.port}")
                
                # Main socket for agent communication
                if hasattr(self, 'socket') and self.socket:
                    try:
                        self.socket.close()
                    except Exception as e:
                        logger.warning(f"Error closing existing socket: {e}")
                
                self.socket = self.context.socket(zmq.REP)
                self.socket.setsockopt(zmq.LINGER, 0)
                self.socket.setsockopt(zmq.RCVTIMEO, 5000)  # Increased timeout for better reliability
                self.socket.bind(f"tcp://*:{self.port}")
                logger.debug(f"BaseAgent._init_sockets: Main socket bound to port {self.port}")
                
                # Health check socket (use a separate context for thread safety)
                if hasattr(self, 'health_context') and self.health_context:
                    try:
                        self.health_context.term()
                    except Exception as e:
                        logger.warning(f"Error terminating existing health context: {e}")
                
                if hasattr(self, 'health_socket') and self.health_socket:
                    try:
                        self.health_socket.close()
                    except Exception as e:
                        logger.warning(f"Error closing existing health socket: {e}")
                
                self.health_context = zmq.Context()
                self.health_socket = self.health_context.socket(zmq.REP)
                self.health_socket.setsockopt(zmq.LINGER, 0)
                self.health_socket.setsockopt(zmq.RCVTIMEO, 5000)  # Increased timeout
                self.health_socket.bind(f"tcp://*:{self.health_check_port}")
                logger.debug(f"BaseAgent._init_sockets: Health socket bound to port {self.health_check_port}")
                
                logger.info(f"{self.name} successfully bound to ports {self.port} and {self.health_check_port}")
                return
            except zmq.error.ZMQError as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed to initialize sockets: {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    
                    if self.strict_port:
                        logger.warning(f"Strict port mode enabled, will retry with same ports")
                        continue  # retry same port without changing
                    
                    # Try a new port automatically unless strict
                    old_port = self.port
                    self.port = self._find_available_port(self.port + 1)
                    logger.info(f"Auto-switching main port from {old_port} to {self.port}")
                    
                    # Only auto-increment health_check_port if it was originally using the default port+1 pattern
                    # If it was explicitly set in config, keep that value
                    config = getattr(self, 'config', {}) or {}
                    if not config.get('health_check_port') and self.health_check_port == old_port + 1:
                        self.health_check_port = self.port + 1
                        logger.info(f"Auto-switching health check port to {self.health_check_port}")
                else:
                    logger.error(f"Failed to initialize sockets after {max_retries} attempts")
                    self.cleanup()
                    raise
    
    def _start_health_check(self):
        """Start health check thread."""
        self.health_thread = threading.Thread(target=self._health_check_loop)
        self.health_thread.daemon = True
        self.health_thread.start()
    
    def _start_initialization(self):
        """Start initialization in background thread."""
        init_thread = threading.Thread(target=self._perform_initialization)
        init_thread.daemon = True
        init_thread.start()
    
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            self.initialization_error = str(e)
            raise
        finally:
            self.is_initialized.set()
    
    def _health_check_loop(self):
        """Health check loop that handles incoming health check requests."""
        logger.info(f"{self.name} health check loop started")
        while self.running:
            try:
                if not hasattr(self, 'health_socket') or self.health_socket is None:
                    logger.warning("Health socket not initialized, waiting...")
                    time.sleep(1)
                    continue
                    
                # Check for health check requests with proper error handling
                try:
                    if self.health_socket.poll(timeout=1000) != 0:
                        try:
                            message = self.health_socket.recv()
                            logger.debug(f"{self.name} health check loop received message: {message}")
                        except zmq.error.Again:
                            # Timeout on receive, continue loop
                            continue
                        except Exception as e:
                            logger.error(f"Error receiving health check message: {e}")
                            continue
                            
                        try:
                            # Try to parse as JSON, but also accept plain text requests
                            try:
                                request = json.loads(message.decode())
                                logger.debug(f"{self.name} received health check request: {request}")
                            except (json.JSONDecodeError, UnicodeDecodeError):
                                # If not valid JSON, treat as simple health check
                                request = {"action": "health_check"}
                                
                            # Get health status and send response
                            response = self._get_health_status()
                            self.health_socket.send_json(response)
                            logger.debug(f"{self.name} sent health check response: {response}")
                        except Exception as e:
                            logger.error(f"Error processing health check: {e}")
                            # Try to send error response
                            try:
                                self.health_socket.send_json({
                                    "status": "error",
                                    "error": str(e)
                                })
                            except Exception:
                                pass
                except zmq.error.ZMQError as e:
                    logger.error(f"{self.name} ZMQ error in health check poll: {e}")
                    time.sleep(1)
            except Exception as e:
                logger.error(f"{self.name} error in health check loop: {e}")
                time.sleep(1)
                
            # Sleep briefly to avoid CPU hogging
            time.sleep(0.1)
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        status = {
            "status": "ok",  # Always use lowercase 'ok' for consistency
            "ready": True,
            "initialized": self.is_initialized.is_set(),
            "message": f"{self.name} is healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime": time.time() - self.start_time,
            "active_threads": threading.active_count()
        }
        logger.debug(f"{self.name} health status: {status}")
        return status
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get("action")
        
        if action in ["ping", "health", "health_check"]:
            return self._get_health_status()
            
        return {"status": "error", "error": f"Unknown action: {action}"}
    
    def run(self):
        """Main run loop."""
        logger.info(f"{self.name} starting main loop")
        
        try:
            while self.running:
                try:
                    # Wait for request with proper error handling
                    if not hasattr(self, 'socket') or self.socket is None:
                        logger.warning("Main socket not initialized, waiting...")
                        time.sleep(1)
                        continue
                        
                    try:
                        if self.socket.poll(timeout=1000) != 0:
                            try:
                                message = self.socket.recv()
                            except zmq.error.Again:
                                # Timeout on receive, continue loop
                                continue
                            except Exception as e:
                                logger.error(f"Error receiving message: {e}")
                                continue
                                
                            try:
                                # Process request
                                request = json.loads(message.decode())
                                logger.debug(f"{self.name} received request: {request}")
                                
                                response = self.handle_request(request)
                                
                                # Send response
                                self.socket.send_json(response)
                                logger.debug(f"{self.name} sent response: {response}")
                            except json.JSONDecodeError:
                                logger.error(f"Invalid JSON in request: {message}")
                                self.socket.send_json({
                                    "status": "error",
                                    "error": "Invalid JSON request"
                                })
                            except UnicodeDecodeError:
                                logger.error(f"Invalid UTF-8 in request: {message}")
                                self.socket.send_json({
                                    "status": "error",
                                    "error": "Invalid UTF-8 request"
                                })
                            except Exception as e:
                                logger.error(f"Error processing request: {e}")
                                try:
                                    self.socket.send_json({
                                        "status": "error",
                                        "error": str(e)
                                    })
                                except Exception:
                                    pass
                    except zmq.error.ZMQError as e:
                        logger.error(f"{self.name} ZMQ error in main loop poll: {e}")
                        time.sleep(1)
                except Exception as e:
                    logger.error(f"{self.name} error in main loop: {e}")
                    time.sleep(1)
                    
                # Sleep briefly to avoid CPU hogging
                time.sleep(0.1)
                    
        except KeyboardInterrupt:
            logger.info(f"{self.name} interrupted")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources with proper error handling and ensure all background threads are joined."""
        logger.info(f"{self.name} cleaning up resources")
        # Signal loops to stop
        self.running = False

        # --- Gracefully join background threads ---
        joined = set()
        try:
            for t in getattr(self, "_background_threads", []):
                if isinstance(t, threading.Thread) and t.is_alive():
                    t.join(timeout=10)
                    joined.add(t)

            # Heuristic: join any thread attributes following *_thread or *_threads naming
            for attr_name in dir(self):
                if attr_name.endswith("_thread") or attr_name.endswith("_threads"):
                    attr = getattr(self, attr_name)
                    if isinstance(attr, threading.Thread) and attr not in joined:
                        if attr.is_alive():
                            attr.join(timeout=10)
                            joined.add(attr)
                    elif isinstance(attr, list):
                        for item in attr:
                            if isinstance(item, threading.Thread) and item not in joined and item.is_alive():
                                item.join(timeout=10)
                                joined.add(item)
        except Exception as e:
            logger.warning(f"{self.name}: error while joining background threads: {e}")

        logger.info(f"{self.name}: joined {len(joined)} background thread(s)")

        # --- Close main socket ---
        if hasattr(self, 'socket') and self.socket:
            try:
                self.socket.close()
                logger.debug(f"{self.name} closed main socket")
            except Exception as e:
                logger.error(f"{self.name} error closing main socket: {e}")
        
        # Close health socket
        if hasattr(self, 'health_socket') and self.health_socket:
            try:
                self.health_socket.close()
                logger.debug(f"{self.name} closed health socket")
            except Exception as e:
                logger.error(f"{self.name} error closing health socket: {e}")
        
        # Terminate contexts
        if hasattr(self, 'context') and self.context:
            try:
                self.context.term()
                logger.debug(f"{self.name} terminated main context")
            except Exception as e:
                logger.error(f"{self.name} error terminating main context: {e}")
                
        if hasattr(self, 'health_context') and self.health_context:
            try:
                self.health_context.term()
                logger.debug(f"{self.name} terminated health context")
            except Exception as e:
                logger.error(f"{self.name} error terminating health context: {e}")
        
        logger.info(f"{self.name} cleanup complete")
        
    def _safe_int(self, value: Any, default: int = 0) -> int:
        """Safely convert a value to int with a default."""
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Could not convert {value} to int, using default {default}")
            return default

    # ===================================================================
    #         STANDARDIZED COMMUNICATION METHODS
    # ===================================================================
    
    def _get_default_capabilities(self) -> List[str]:
        """Get default capabilities for this agent based on class name."""
        agent_type = self.__class__.__name__.lower()
        if "translator" in agent_type:
            return ["translation"]
        elif "memory" in agent_type:
            return ["memory_management"]
        elif "model" in agent_type:
            return ["model_inference"]
        elif "speech" in agent_type or "tts" in agent_type:
            return ["speech_processing"]
        else:
            return ["basic_agent"]
    
    def _register_with_digital_twin(self) -> None:
        """Register this agent with the SystemDigitalTwin for service discovery."""
        try:
            # Get hostname for registration
            hostname = socket.gethostname()
            try:
                ip_address = socket.gethostbyname(hostname)
            except socket.gaierror:
                ip_address = "127.0.0.1"
                logger.warning(f"Could not resolve hostname, using {ip_address}")
            
            # Prepare registration data
            registration = AgentRegistration(
                agent_id=self.name,
                agent_type=self.__class__.__name__,
                host=ip_address,
                port=self.port,
                health_check_port=self.health_check_port,
                capabilities=self.capabilities,
                dependencies=[],  # Subclasses should override this
                metadata={
                    "start_time": datetime.now().isoformat(),
                    "python_version": sys.version
                }
            )
            
            # Send registration to SystemDigitalTwin
            self.send_request_to_agent(
                "SystemDigitalTwin",
                {
                    "action": "register_agent",
                    "agent_name": self.name,
                    "status": "HEALTHY",
                    "location": "MainPC",  # Default to MainPC, can be overridden
                    "registration_data": registration.dict()
                },
                retries=3,
                retry_delay=2.0
            )
            logger.info(f"Successfully registered {self.name} with SystemDigitalTwin")
        except Exception as e:
            logger.warning(f"Failed to register with SystemDigitalTwin: {e}. Will continue without registration.")
    
    def get_agent_endpoint(self, agent_name: str) -> Tuple[str, int]:
        """Get the endpoint (host, port) for a specific agent from SystemDigitalTwin.
        
        Args:
            agent_name: Name of the agent to locate
            
        Returns:
            Tuple of (host, port) for the requested agent
            
        Raises:
            RuntimeError: If the agent cannot be found or ServiceRegistry is unreachable
        """
        try:
            response = self.send_request_to_agent(
                "ServiceRegistry",
                {"action": "get_agent_endpoint", "agent_name": agent_name},
                host=os.getenv("SERVICE_REGISTRY_HOST", "localhost"),
                port=int(os.getenv("SERVICE_REGISTRY_PORT", 7100))
            )
            
            if response.get("status") != "success":
                raise RuntimeError(f"Failed to get endpoint for {agent_name}: {response.get('error', 'Unknown error')}")
            
            host = response.get("host", "localhost")
            port = response.get("port")
            
            if port is None:
                raise RuntimeError(f"No port returned for agent {agent_name}")
                
            return host, int(port)
        except Exception as e:
            logger.error(f"Error getting endpoint for {agent_name}: {e}")
            raise RuntimeError(f"Could not locate agent {agent_name}: {str(e)}")
    
    def send_request_to_agent(
        self, 
        agent_name: str, 
        request: Dict[str, Any],
        host: Optional[str] = None,
        port: Optional[int] = None,
        timeout: int = 5000,
        retries: int = 1,
        retry_delay: float = 1.0
    ) -> Dict[str, Any]:
        """Send a request to another agent using standardized message format.
        
        Args:
            agent_name: Name of the target agent
            request: Request payload to send
            host: Optional host address, will try to discover if not provided
            port: Optional port number, will try to discover if not provided
            timeout: ZMQ timeout in milliseconds
            retries: Number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Response from the agent as a dictionary
            
        Raises:
            RuntimeError: If communication fails after all retries
        """
        # Special case for SystemDigitalTwin - use hardcoded values if discovery not available
        if agent_name == "SystemDigitalTwin" and (host is None or port is None):
            host = host or "localhost"
            port = port or 7120  # Default SystemDigitalTwin port from config
        
        # Try to discover the agent if host/port not provided
        if host is None or port is None:
            try:
                discovered_host, discovered_port = self.get_agent_endpoint(agent_name)
                host = host or discovered_host
                port = port or discovered_port
            except Exception as e:
                if agent_name == "SystemDigitalTwin":
                    # For SystemDigitalTwin, fall back to default if discovery fails
                    host = "localhost"
                    port = 7120
                    logger.warning(f"Using default SystemDigitalTwin endpoint: {host}:{port}")
                else:
                    raise RuntimeError(f"Could not discover endpoint for {agent_name}: {str(e)}")
        
        # Ensure host and port are not None at this point
        if host is None:
            host = "localhost"
            logger.warning(f"Host was None for {agent_name}, using default: {host}")
        
        if port is None:
            raise RuntimeError(f"Could not determine port for agent {agent_name}")
        
        # Set up request socket
        request_socket = None
        for attempt in range(retries):
            try:
                if request_socket:
                    request_socket.close()
                
                request_socket = self.context.socket(zmq.REQ)
                request_socket.setsockopt(zmq.LINGER, 0)
                request_socket.setsockopt(zmq.RCVTIMEO, timeout)
                request_socket.connect(f"tcp://{host}:{port}")
                
                # Add metadata to request
                enriched_request = request.copy()
                enriched_request.update({
                    "source_agent": self.name,
                    "request_id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat()
                })
                
                # Send request and wait for response
                request_socket.send_json(enriched_request)
                response_data = request_socket.recv_json()
                
                # Ensure we return a dictionary
                if not isinstance(response_data, dict):
                    response_data = {"status": "success", "data": response_data}
                
                return cast(Dict[str, Any], response_data)
                
            except zmq.error.Again:
                logger.warning(f"Timeout waiting for response from {agent_name} (attempt {attempt+1}/{retries})")
            except Exception as e:
                logger.error(f"Error communicating with {agent_name} (attempt {attempt+1}/{retries}): {e}")
            
            # Wait before retry
            if attempt < retries - 1:
                time.sleep(retry_delay)
        
        # Clean up socket if still exists
        if request_socket:
            request_socket.close()
            
        raise RuntimeError(f"Failed to communicate with {agent_name} after {retries} attempts")
    
    def send_event(self, event_type: str, data: Dict[str, Any], propagate: bool = False) -> None:
        """Send a system event to the SystemDigitalTwin for distribution.
        
        Args:
            event_type: Type of event being sent
            data: Event payload data
            propagate: Whether this event should be propagated to other machines
        """
        try:
            event = SystemEvent(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                source_agent=self.name,
                data=data,
                propagate=propagate
            )
            
            self.send_request_to_agent(
                "SystemDigitalTwin",
                {
                    "action": "publish_event",
                    "event": event.dict()
                }
            )
        except Exception as e:
            logger.error(f"Failed to send event {event_type}: {e}")
    
    def report_error(
        self, 
        error_type: str, 
        message: str, 
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: Optional[Dict[str, Any]] = None,
        stack_trace: Optional[str] = None,
        related_task_id: Optional[str] = None
    ) -> None:
        """Report an error to the error management system.
        
        Args:
            error_type: Type or category of error
            message: Human-readable error message
            severity: Error severity level
            context: Additional contextual information
            stack_trace: Optional stack trace
            related_task_id: ID of related task if applicable
        """
        try:
            error_report = ErrorReport(
                error_id=str(uuid.uuid4()),
                agent_id=self.name,
                severity=severity,
                error_type=error_type,
                message=message,
                context=context or {},
                stack_trace=stack_trace,
                related_task_id=related_task_id
            )
            
            self.send_request_to_agent(
                "SystemDigitalTwin",
                {
                    "action": "report_error",
                    "error": error_report.dict()
                }
            )
        except Exception as e:
            # Log locally if error reporting fails
            logger.error(f"Error in report_error: {e}")
            logger.error(f"Original error: {error_type} - {message}") 