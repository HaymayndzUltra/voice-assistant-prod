"""
Base Agent class with health check implementation
All agents should inherit from this class
"""

import zmq
import json
import time
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class BaseAgent:
    def __init__(self, port: int, name: str, host: str = "localhost"):
        """Initialize base agent with health check support.
        
        Args:
            port: Main port for agent communication
            name: Name of the agent
            host: Host to bind to (default: localhost)
        """
        self.port = port
        self.name = name
        self.host = host
        self.start_time = time.time()
        self.running = True
        self.is_initialized = threading.Event()
        self.initialization_error = None
        
        # Initialize ZMQ context and sockets
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.health_socket = self.context.socket(zmq.REP)
        
        # Set socket options
        self.socket.setsockopt(zmq.LINGER, 0)
        self.health_socket.setsockopt(zmq.LINGER, 0)
        
        # Bind sockets
        self.socket.bind(f"tcp://{host}:{port}")
        self.health_socket.bind(f"tcp://{host}:{port + 1}")
        
        # Start health check thread
        self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_thread.start()
        
        logger.info(f"{name} initialized with main port {port} and health check port {port + 1}")
        
    def _health_check_loop(self):
        """Health check loop that handles health check requests."""
        while self.running:
            try:
                if self.health_socket.poll(timeout=1000) != 0:
                    # Receive message as bytes
                    message_bytes = self.health_socket.recv()
                    try:
                        # Decode message
                        message = json.loads(message_bytes.decode('utf-8'))
                        if message.get("action") == "health":
                            response = self._get_health_status()
                            # Send response as bytes
                            self.health_socket.send(json.dumps(response).encode('utf-8'))
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in health check request: {message_bytes}")
                        self.health_socket.send(json.dumps({
                            "status": "error",
                            "error": "Invalid JSON request"
                        }).encode('utf-8'))
                    except UnicodeDecodeError:
                        logger.error(f"Invalid UTF-8 in health check request: {message_bytes}")
                        self.health_socket.send(json.dumps({
                            "status": "error",
                            "error": "Invalid UTF-8 request"
                        }).encode('utf-8'))
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(1)
                
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent.
        
        Override this method in subclasses to provide additional health metrics.
        """
        return {
            "status": "ok",
            "ready": self.is_initialized.is_set(),
            "initialized": self.is_initialized.is_set(),
            "message": f"{self.name} is healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime": time.time() - self.start_time,
            "active_threads": threading.active_count()
        }
        
    def handle_request(self, request: Dict) -> Dict:
        """Handle incoming requests.
        
        Override this method in subclasses to implement specific request handling.
        """
        action = request.get("action")
        
        if action in ["ping", "health"]:
            return self._get_health_status()
            
        return {
            "status": "error",
            "error": f"Unknown action: {action}"
        }
        
    def run(self):
        """Main agent loop.
        
        Override this method in subclasses to implement specific agent behavior.
        """
        logger.info(f"Starting {self.name} main loop...")
        
        while self.running:
            try:
                if self.socket.poll(timeout=1000) != 0:
                    # Receive message as bytes
                    message_bytes = self.socket.recv()
                    try:
                        # Decode message
                        message = json.loads(message_bytes.decode('utf-8'))
                        response = self.handle_request(message)
                        # Send response as bytes
                        self.socket.send(json.dumps(response).encode('utf-8'))
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in request: {message_bytes}")
                        self.socket.send(json.dumps({
                            "status": "error",
                            "error": "Invalid JSON request"
                        }).encode('utf-8'))
                    except UnicodeDecodeError:
                        logger.error(f"Invalid UTF-8 in request: {message_bytes}")
                        self.socket.send(json.dumps({
                            "status": "error",
                            "error": "Invalid UTF-8 request"
                        }).encode('utf-8'))
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(1)
                
    def stop(self):
        """Stop the agent and clean up resources."""
        self.running = False
        self.socket.close()
        self.health_socket.close()
        self.context.term()
        logger.info(f"{self.name} stopped") 