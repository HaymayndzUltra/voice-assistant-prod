"""
Base Agent Class with Proper Initialization and Health Check Patterns
"""

import threading
import time
import zmq
import logging
import json
from typing import Dict, Any, Optional, Union, cast
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseAgent:
    """Base class for all agents with proper initialization and health check patterns."""
    
    def __init__(self, port: Optional[int] = None, name: Optional[str] = None, *, strict_port: bool = False):
        """Initialize the base agent.
        
        Args:
            port: Port number for the agent's main socket
            name: Name of the agent
        """
        self.name = name or self.__class__.__name__
        self.port = port or self._find_available_port()
        self.health_check_port = self.port + 1
        self.context = zmq.Context()
        self.strict_port = strict_port  # If True, do not auto-switch ports on bind failure
        
        # Initialize state
        self.running = True
        self.is_initialized = threading.Event()
        self.initialization_error = None
        self.start_time = time.time()
        
        # Initialize sockets with proper error handling
        self._init_sockets()
        
        # Start health check thread immediately
        self._start_health_check()
        
        # Start initialization in background
        self._start_initialization()
        
        logger.info(f"{self.name} initialized on port {self.port} (health check: {self.health_check_port})")
    
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
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                # Main socket for agent communication
                self.socket = self.context.socket(zmq.REP)
                self.socket.setsockopt(zmq.LINGER, 0)
                self.socket.bind(f"tcp://*:{self.port}")
                
                # Health check socket (use a separate context for thread safety)
                self.health_context = zmq.Context()
                self.health_socket = self.health_context.socket(zmq.REP)
                self.health_socket.setsockopt(zmq.LINGER, 0)
                self.health_socket.bind(f"tcp://*:{self.health_check_port}")
                
                logger.info(f"{self.name} successfully bound to ports {self.port} and {self.health_check_port}")
                return
                
            except zmq.error.ZMQError as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed to initialize sockets: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    if self.strict_port:
                        continue  # retry same port without changing
                    # Try a new port automatically unless strict
                    self.port = self._find_available_port(self.port + 1)
                    self.health_check_port = self.port + 1
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
                # Check for health check requests
                if self.health_socket.poll(timeout=1000) != 0:
                    message = self.health_socket.recv()
                    logger.info(f"[DEBUG] {self.name} health check loop received message: {message}")
                    try:
                        request = cast(Dict[str, Any], json.loads(message.decode()))
                        logger.debug(f"{self.name} received health check request: {request}")
                        response = self._get_health_status()
                        self.health_socket.send_json(response)
                        logger.debug(f"{self.name} sent health check response: {response}")
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in health check request: {message}")
                        self.health_socket.send_json({
                            "status": "error",
                            "error": "Invalid JSON request"
                        })
                    except UnicodeDecodeError:
                        logger.error(f"Invalid UTF-8 in health check request: {message}")
                        self.health_socket.send_json({
                            "status": "error",
                            "error": "Invalid UTF-8 request"
                        })
            except zmq.error.ZMQError as e:
                logger.error(f"{self.name} ZMQ error in health check loop: {e}")
                time.sleep(1)
            except Exception as e:
                logger.error(f"{self.name} error in health check loop: {e}")
                time.sleep(1)
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        status = {
            "status": "ok",
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
                    # Wait for request
                    if self.socket.poll(timeout=1000) != 0:
                        message = self.socket.recv()
                        try:
                            request = cast(Dict[str, Any], json.loads(message.decode()))
                            logger.debug(f"{self.name} received request: {request}")
                            
                            # Process request
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
                        
                except zmq.error.ZMQError as e:
                    logger.error(f"{self.name} ZMQ error in main loop: {e}")
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"{self.name} error in main loop: {e}")
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info(f"{self.name} interrupted")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Default cleanup for BaseAgent."""
        try:
            if hasattr(self, 'socket'):
                self.socket.close()
            if hasattr(self, 'health_socket'):
                self.health_socket.close()
            if hasattr(self, 'context'):
                self.context.term()
        except Exception as e:
            logger.error(f"Error during BaseAgent cleanup: {e}")

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
                # Check for health check requests
                if self.health_socket.poll(timeout=1000) != 0:
                    message = self.health_socket.recv()
                    logger.info(f"[DEBUG] {self.name} health check loop received message: {message}")
                    try:
                        request = cast(Dict[str, Any], json.loads(message.decode()))
                        logger.debug(f"{self.name} received health check request: {request}")
                        response = self._get_health_status()
                        self.health_socket.send_json(response)
                        logger.debug(f"{self.name} sent health check response: {response}")
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in health check request: {message}")
                        self.health_socket.send_json({
                            "status": "error",
                            "error": "Invalid JSON request"
                        })
                    except UnicodeDecodeError:
                        logger.error(f"Invalid UTF-8 in health check request: {message}")
                        self.health_socket.send_json({
                            "status": "error",
                            "error": "Invalid UTF-8 request"
                        })
            except zmq.error.ZMQError as e:
                logger.error(f"{self.name} ZMQ error in health check loop: {e}")
                time.sleep(1)
            except Exception as e:
                logger.error(f"{self.name} error in health check loop: {e}")
                time.sleep(1)
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        status = {
            "status": "ok",
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
                    # Wait for request
                    if self.socket.poll(timeout=1000) != 0:
                        message = self.socket.recv()
                        try:
                            request = cast(Dict[str, Any], json.loads(message.decode()))
                            logger.debug(f"{self.name} received request: {request}")
                            
                            # Process request
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
                        
                except zmq.error.ZMQError as e:
                    logger.error(f"{self.name} ZMQ error in main loop: {e}")
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"{self.name} error in main loop: {e}")
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info(f"{self.name} interrupted")
        finally:
            self.cleanup() 