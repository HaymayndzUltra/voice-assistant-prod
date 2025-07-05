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
from typing import Dict, Any, cast, Optional, Union
from datetime import datetime
from abc import ABC, abstractmethod

# Import the PathManager for consistent path resolution
from main_pc_code.utils.path_manager import PathManager

# Now that the path is set, we can use absolute imports
from main_pc_code.utils.config_loader import parse_agent_args

# Configure logger
logger = logging.getLogger(__name__)

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
        
        logger.info(f"{self.name} initialized on port {self.port} (health check: {self.health_check_port})")
    
    def _setup_logging(self):
        """Set up logging with proper path resolution using PathManager."""
        logs_dir = PathManager.get_logs_dir()
        
        # Create agent-specific log file
        agent_log_file = logs_dir / f"{self.name.lower()}.log"
        
        # Add file handler if not already added
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler) and handler.baseFilename == str(agent_log_file):
                return
        
        file_handler = logging.FileHandler(str(agent_log_file))
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)
        
        logger.info(f"Logging set up for {self.name} at {agent_log_file}")
    
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
                logger.debug(f"BaseAgent._init_sockets: Attempt {attempt+1} binding main socket to port {self.port}")
                
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
        """Clean up resources with proper error handling."""
        logger.info(f"{self.name} cleaning up resources")
        self.running = False
        
        # Close main socket
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