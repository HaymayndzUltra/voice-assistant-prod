"""
Base Agent Class with Proper Initialization and Standardized Health Check Patterns
Enhanced with unified health checking system
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
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# Import the PathManager for consistent path resolution
from common.utils.path_manager import PathManager

# Now that the path is set, we can use absolute imports
from main_pc_code.utils.config_loader import parse_agent_args
from common.utils.data_models import (
    SystemEvent, ErrorReport, ErrorSeverity, AgentRegistration
)

# Use centralized JSON logger
from common.utils.logger_util import get_json_logger
from common.env_helpers import get_env

# Import standardized health checking
from common.health.standardized_health import StandardizedHealthChecker, HealthStatus
from common.config_manager import get_service_ip, get_service_url, get_redis_url

# Import unified error handling (replaces direct NATS import)
from common.error_bus.unified_error_handler import UnifiedErrorHandler, create_unified_error_handler

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
            
        # HTTP health port should be separate to avoid conflicts with ZMQ health socket
        self.http_health_port = self.health_check_port + 1
        
        self.context = zmq.Context()
        self.strict_port = kwargs.get('strict_port', True)  # If True, do not auto-switch ports on bind failure
        
        # Initialize state
        self.running = True
        self.is_initialized = threading.Event()
        self.initialization_error = None
        self.start_time = time.time()
        self._cleanup_called = False  # Prevent multiple cleanup calls
        
        # Add task management for proper lifecycle (FIX for "Event loop is closed")
        self._error_reporting_tasks = set()  # Track all error reporting tasks
        self._shutdown_event = None  # Will be initialized when async context is available
        
        # Set up logging directory using PathManager
        self._setup_logging()
        
        # Initialize standardized health checker
        self.health_checker = StandardizedHealthChecker(
            agent_name=self.name,
            port=self.port,
            redis_host=kwargs.get('redis_host', 'localhost'),
            redis_port=kwargs.get('redis_port', 6379)
        )
        
        # Initialize unified error handler (handles both legacy ZMQ and modern NATS)
        self.unified_error_handler: Optional[UnifiedErrorHandler] = None
        self.error_handler_task = None
        self._start_unified_error_handler_initialization(
            enable_legacy=kwargs.get('enable_legacy_errors', True),
            enable_nats=kwargs.get('enable_nats_errors', True),
            nats_servers=kwargs.get('nats_servers', None)
        )
        
        # Initialize sockets with proper error handling
        self._init_sockets()
        
        # Start health check thread immediately
        self._start_health_check()
        self._start_http_health_server()
        
        # Start initialization in background
        self._start_initialization()
        
        # Get agent capabilities for registration
        self.capabilities = kwargs.get('capabilities', self._get_default_capabilities())
        
        # Set up graceful shutdown handlers
        self._setup_graceful_shutdown()
        
        # Set up auto-registration with SystemDigitalTwin
        self._register_with_digital_twin()
        
        logger.info(f"{self.name} initialized on port {self.port} (health check: {self.health_check_port})")
    
    def _setup_logging(self):
        """Configure per-agent JSON structured logging."""
        from pathlib import Path
        project_root = Path(PathManager.get_project_root())
        logs_dir = project_root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        agent_log_file = logs_dir / f"{self.name.lower()}.log"

        # Replace existing handlers with JSON handlers only once
        self.logger = get_json_logger(self.name, logfile=str(agent_log_file))

        # Attach agent_name attribute to records automatically via LoggerAdapter
        self.logger = logging.LoggerAdapter(self.logger, extra={"agent_name": self.name})

        self.logger.info(f"Initialized JSON logging -> {agent_log_file}")
    
    def _setup_graceful_shutdown(self):
        """Setup graceful shutdown handlers for SIGTERM and SIGINT signals."""
        
    
    def _atexit_cleanup(self):
        """Cleanup method called on normal Python exit."""
        if self.running:
            self.logger.info(f"{self.name} performing atexit cleanup...")
            self.cleanup()
    
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
                        self.http_health_port = self.health_check_port + 1
                        logger.info(f"Auto-switching health check port to {self.health_check_port}, HTTP health to {self.http_health_port}")
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
            
            # Mark agent as ready in Redis using standardized health system
            try:
                initialization_details = {
                    "initialized_at": datetime.now().isoformat(),
                    "uptime": time.time() - self.start_time,
                    "port": self.port,
                    "health_check_port": self.health_check_port
                }
                self.health_checker.set_agent_ready(initialization_details)
                logger.info(f"✅ {self.name} marked as ready in Redis")
            except Exception as e:
                logger.warning(f"Failed to set ready signal for {self.name}: {e}")
    
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
        """Get the current health status using standardized health checker."""
        try:
            # Use standardized health checker
            health_check = self.health_checker.perform_health_check()
            
            # Convert to legacy format for backward compatibility
            status = {
                "status": "ok" if health_check.status == HealthStatus.HEALTHY else "degraded",
                "ready": health_check.checks.get("ready_signal", False),
                "initialized": self.is_initialized.is_set(),
                "message": f"{self.name} is {health_check.status.value}",
                "timestamp": health_check.timestamp.isoformat(),
                "uptime": time.time() - self.start_time,
                "active_threads": threading.active_count(),
                # Add standardized health data
                "health_checks": health_check.checks,
                "health_details": health_check.details,
                "health_status": health_check.status.value
            }
            
            if health_check.error_message:
                status["error"] = health_check.error_message
                
        except Exception as e:
            # Fallback to basic status if standardized check fails
            logger.error(f"Standardized health check failed for {self.name}: {e}")
            status = {
                "status": "error",
                "ready": False,
                "initialized": self.is_initialized.is_set(),
                "message": f"{self.name} health check error: {e}",
                "timestamp": datetime.now().isoformat(),
                "uptime": time.time() - self.start_time,
                "active_threads": threading.active_count(),
                "error": str(e)
            }
            
        logger.debug(f"{self.name} health status: {status}")
        return status
    
    def _start_unified_error_handler_initialization(self, enable_legacy, enable_nats, nats_servers):
        """Start unified error handler initialization in background thread"""
        def init_unified_handler():
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def connect_unified_handler():
                    try:
                        self.unified_error_handler = await create_unified_error_handler(
                            agent_name=self.name,
                            enable_legacy=enable_legacy,
                            enable_nats=enable_nats,
                            nats_servers=nats_servers
                        )
                        
                        # Set up legacy error sending method (will be implemented separately)
                        self.unified_error_handler.set_legacy_handler(self._send_error_to_digital_twin)
                        
                        logger.info(f"✅ Unified Error Handler initialized for {self.name}")
                    except Exception as e:
                        logger.warning(f"Unified Error Handler initialization failed for {self.name}: {e}")
                        self.unified_error_handler = None
                
                loop.run_until_complete(connect_unified_handler())
                loop.close()
                
            except Exception as e:
                logger.warning(f"Unified error handler initialization failed for {self.name}: {e}")
                self.unified_error_handler = None
        
        # Start in background thread
        self.error_handler_task = threading.Thread(target=init_unified_handler, daemon=True)
        self.error_handler_task.start()
    
    async def _send_error_to_digital_twin(self, error_report):
        """Legacy method to send error to SystemDigitalTwin via ZMQ"""
        try:
            # This would be the existing ZMQ implementation to SystemDigitalTwin
            # For now, we'll log it - actual implementation depends on existing ZMQ setup
            logger.info(f"📤 Sending error to SystemDigitalTwin: {error_report.error_id}")
            
            # TODO: Implement actual ZMQ send to SystemDigitalTwin
            # Example:
            # if hasattr(self, 'digital_twin_socket') and self.digital_twin_socket:
            #     self.digital_twin_socket.send_json(error_report.dict())
            
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send error to SystemDigitalTwin: {e}")
            return False
    
    async def _report_error_async(self,
                                 error_type: str,
                                 message: str,
                                 severity,
                                 details: Optional[Dict[str, Any]] = None,
                                 category = None,
                                 stack_trace: Optional[str] = None,
                                 related_task_id: Optional[str] = None) -> Dict[str, bool]:
        """
        Internal async implementation for unified error reporting
        """
        if self.unified_error_handler:
            try:
                results = await self.unified_error_handler.report_error(
                    severity=severity,
                    message=message,
                    error_type=error_type,
                    details=details,
                    category=category,
                    stack_trace=stack_trace,
                    related_task_id=related_task_id
                )
                
                logger.debug(f"📊 Error reporting results: {results}")
                return results
                
            except Exception as e:
                logger.error(f"❌ Unified error reporting failed: {e}")
        
        # Fallback to basic logging if unified handler not available
        logger.error(f"[FALLBACK] {severity}: {message} - Details: {details}")
        return {"legacy": False, "nats": False}
    
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
        if self._cleanup_called:
            logger.debug(f"{self.name} cleanup already called, skipping")
            return
        
        self._cleanup_called = True
        logger.info(f"{self.name} cleaning up resources")
        
        # Mark agent as not ready in Redis
        try:
            self.health_checker.set_agent_not_ready("cleanup initiated")
            logger.info(f"🛑 {self.name} marked as not ready in Redis")
        except Exception as e:
            logger.warning(f"Failed to remove ready signal for {self.name}: {e}")
        
        # Close unified error handler
        if self.unified_error_handler:
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.unified_error_handler.close())
                loop.close()
                logger.info(f"✅ Unified error handler closed for {self.name}")
            except Exception as e:
                logger.warning(f"Failed to close unified error handler for {self.name}: {e}")
        
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
        
        # Shutdown HTTP server if exists
        if hasattr(self, 'http_server'):
            self.http_server.shutdown()
            self.http_server.server_close()
        
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
                ip_address = "localhost"
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
            
            # Get Digital Twin endpoint from env vars
            dt_host = os.getenv('DIGITAL_TWIN_HOST', '0.0.0.0')
            dt_port = int(os.getenv('DIGITAL_TWIN_PORT', 7120))
            
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
                host=dt_host,
                port=dt_port,
                retries=3,
                retry_delay=2.0
            )
            logger.info(f"Successfully registered {self.name} with SystemDigitalTwin at {dt_host}:{dt_port}")
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
                host=os.getenv("SERVICE_REGISTRY_HOST", get_env("BIND_ADDRESS", "0.0.0.0")),
                port=int(os.getenv("SERVICE_REGISTRY_PORT", 7100))
            )
            
            if response.get("status") != "success":
                raise RuntimeError(f"Failed to get endpoint for {agent_name}: {response.get('error', 'Unknown error')}")
            
            host = response.get("host", get_env("BIND_ADDRESS", "0.0.0.0"))
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
            host = host or get_env("BIND_ADDRESS", "0.0.0.0")
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
                    host = get_env("BIND_ADDRESS", "0.0.0.0")
                    port = 7120
                    logger.warning(f"Using default SystemDigitalTwin endpoint: {host}:{port}")
                else:
                    raise RuntimeError(f"Could not discover endpoint for {agent_name}: {str(e)}")
        
        # Ensure host and port are not None at this point
        if host is None:
            host = get_env("BIND_ADDRESS", "0.0.0.0")
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
    

    def report_error(self,
                     error_type: str,  # MAINTAIN original first parameter
                     message: str,     # MAINTAIN original second parameter  
                     severity = None,  # Accept legacy enum or new string
                     context: Optional[Dict[str, Any]] = None,  # Legacy name
                     details: Optional[Dict[str, Any]] = None,  # New name
                     category = None,  # New NATS category
                     stack_trace: Optional[str] = None,
                     related_task_id: Optional[str] = None,
                     wait_for_completion: bool = False,  # NEW: Control async behavior
                     **kwargs) -> Union[Dict[str, bool], Any]:
        """
        UNIFIED error reporting with PROPER TASK LIFECYCLE MANAGEMENT
        
        Supports both old and new calling patterns:
        - Legacy: report_error("network_error", "Connection failed", ErrorSeverity.CRITICAL)
        - Enhanced: report_error("network_error", "Connection failed", "critical", category=ErrorCategory.NETWORK)
        - Synchronous: report_error("error", "message", wait_for_completion=True)
        
        Args:
            error_type: Type or category of error (legacy parameter)
            message: Human-readable error message
            severity: Error severity level (accepts legacy enum, NATS enum, or string)
            context: Additional contextual information (legacy parameter name)
            details: Additional error context (new parameter name, same as context)
            category: NATS error category (new parameter for enhanced error bus)
            stack_trace: Optional stack trace
            related_task_id: ID of related task if applicable
            wait_for_completion: If True, waits for error reporting to complete (safer)
            
        Returns:
            Dict with success status: {"legacy": bool, "nats": bool} or asyncio.Task if in async context
        """
        # Import here to avoid circular imports
        from common.utils.data_models import ErrorSeverity as LegacyErrorSeverity
        
        # Parameter unification and defaults
        final_details = details or context or {}
        final_severity = severity or LegacyErrorSeverity.ERROR
        
        # Enhanced async/sync handling with proper task management
        try:
            import asyncio
            
            # Check if we have a running event loop
            try:
                loop = asyncio.get_running_loop()
                in_async_context = True
            except RuntimeError:
                # No running loop, we're in sync context
                in_async_context = False
                loop = None
            
            if in_async_context and not wait_for_completion:
                # SAFE ASYNC: Managed task creation with proper cleanup
                task = self._create_managed_error_task(
                    error_type=error_type,
                    message=message,
                    severity=final_severity,
                    details=final_details,
                    category=category,
                    stack_trace=stack_trace,
                    related_task_id=related_task_id
                )
                return task  # Returns awaitable with cleanup
            else:
                # SYNCHRONOUS: Run to completion safely
                return self._report_error_sync(
                    error_type=error_type,
                    message=message,
                    severity=final_severity,
                    details=final_details,
                    category=category,
                    stack_trace=stack_trace,
                    related_task_id=related_task_id
                )
        except Exception as e:
            logger.error(f"Error reporting failed: {e}")
            # Fallback to basic logging
            logger.error(f"[FALLBACK] {error_type}: {message} - Details: {final_details}")
            return {"legacy": False, "nats": False}

    def _ensure_shutdown_event(self):
        """Ensure shutdown event is initialized in async context"""
        if self._shutdown_event is None:
            import asyncio
            self._shutdown_event = asyncio.Event()

    def _create_managed_error_task(self, **kwargs):
        """Create error reporting task with proper lifecycle management"""
        import asyncio
        
        # Ensure shutdown event is initialized
        self._ensure_shutdown_event()
        
        async def managed_error_wrapper():
            try:
                # Check if shutdown is in progress
                if self._shutdown_event and self._shutdown_event.is_set():
                    logger.warning("Skipping error reporting - agent is shutting down")
                    return {"legacy": False, "nats": False}
                
                # Perform actual error reporting
                result = await self._report_error_async(**kwargs)
                return result
                
            except Exception as e:
                logger.error(f"Managed error reporting failed: {e}")
                return {"legacy": False, "nats": False}
            finally:
                # Remove task from tracking set when done
                current_task = asyncio.current_task()
                self._error_reporting_tasks.discard(current_task)
        
        # Create and track the task
        loop = asyncio.get_running_loop()
        task = loop.create_task(managed_error_wrapper())
        self._error_reporting_tasks.add(task)
        
        # Add callback to handle task completion
        task.add_done_callback(lambda t: self._error_reporting_tasks.discard(t))
        
        return task

    def _report_error_sync(self, **kwargs):
        """Synchronous error reporting with proper event loop handling"""
        import asyncio
        
        try:
            # Try to get existing loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, but user wants sync behavior
                # Create a new task and wait for it
                task = loop.create_task(self._report_error_async(**kwargs))
                
                # Use asyncio.wait_for with timeout to prevent hanging
                try:
                    future = asyncio.wait_for(task, timeout=30.0)  # 30 second timeout
                    return loop.run_until_complete(future)
                except asyncio.TimeoutError:
                    logger.error("Error reporting timed out after 30 seconds")
                    task.cancel()
                    return {"legacy": False, "nats": False}
                    
            except RuntimeError:
                # No running loop, create new one
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    return loop.run_until_complete(self._report_error_async(**kwargs))
                finally:
                    loop.close()
                    
        except Exception as e:
            logger.error(f"Synchronous error reporting failed: {e}")
            return {"legacy": False, "nats": False}

    async def shutdown_gracefully(self, timeout: float = 30.0):
        """Graceful shutdown with proper task cleanup"""
        logger.info(f"Starting graceful shutdown for {self.name}")
        
        # Signal shutdown to prevent new tasks
        self._ensure_shutdown_event()
        if self._shutdown_event:
            self._shutdown_event.set()
        
        # Wait for existing error reporting tasks to complete
        if self._error_reporting_tasks:
            logger.info(f"Waiting for {len(self._error_reporting_tasks)} error reporting tasks to complete")
            
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._error_reporting_tasks, return_exceptions=True),
                    timeout=timeout
                )
                logger.info("All error reporting tasks completed successfully")
            except asyncio.TimeoutError:
                logger.warning(f"Some error reporting tasks didn't complete within {timeout}s, cancelling...")
                for task in self._error_reporting_tasks:
                    if not task.done():
                        task.cancel()
                
                # Wait a bit more for cancellations to complete
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*self._error_reporting_tasks, return_exceptions=True),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    logger.error("Some tasks failed to cancel properly")
        
        # Shutdown unified error handler
        if hasattr(self, 'unified_error_handler') and self.unified_error_handler:
            try:
                await self.unified_error_handler.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down unified error handler: {e}")
        
        logger.info(f"Graceful shutdown completed for {self.name}") 

    def _start_http_health_server(self):
        """Start a simple HTTP server for health checks on separate port to avoid ZMQ conflict."""
        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(s):
                if s.path == '/health':
                    s.send_response(200)
                    s.send_header('Content-type', 'application/json')
                    s.end_headers()
                    status = self._get_health_status()
                    s.wfile.write(json.dumps(status).encode())
                else:
                    s.send_error(404)
            
            def log_message(self, format, *args):
                # Suppress HTTP server logs to reduce noise
                pass
        
        try:
            self.http_server = HTTPServer(('0.0.0.0', self.http_health_port), HealthHandler)
            thread = threading.Thread(target=self.http_server.serve_forever)
            thread.daemon = True
            thread.start()
            logger.info(f"Started HTTP health server on port {self.http_health_port} (ZMQ health on {self.health_check_port})")
        except OSError as e:
            logger.warning(f"Failed to start HTTP health server on port {self.http_health_port}: {e}")
            logger.info(f"HTTP health endpoint unavailable, ZMQ health check still available on port {self.health_check_port}") 