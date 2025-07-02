from src.core.base_agent import BaseAgent
"""
Coordinator Module
Manages and coordinates all modules in the voice assistant system
"""

import os
import sys
import json
import logging
import time
import subprocess
import signal
import zmq
import threading
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('coordinator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Coordinator")

# ZMQ Configuration
COORDINATOR_PORT = 5590  # Main ROUTER socket
HEALTH_CHECK_PORT = 5590  # REP socket for health checks

class CoordinatorModule(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="Coordinator")
        """Initialize the coordinator module"""
        try:
            logger.info("Initializing Coordinator Module")
            self.start_time = time.time()
            
            # Initialize thread-safe data structures
            self.services_lock = threading.Lock()
            self.services = {}
            self.is_initialized = threading.Event()
            self.initialization_error = None
            
            # Initialize ZMQ
            logger.info("Setting up ZMQ sockets")
            self.context = zmq.Context()
            
            # ROUTER socket for main communication
            logger.info(f"Binding ROUTER socket to port {COORDINATOR_PORT}...")
            self.router_socket = self.context.socket(zmq.ROUTER)
            self.router_socket.setsockopt(zmq.LINGER, 0)
            self.router_socket.setsockopt(zmq.RCVTIMEO, 1000)
            self.router_socket.setsockopt(zmq.SNDTIMEO, 1000)
            self.router_socket.bind(f"tcp://*:{COORDINATOR_PORT}")
            logger.info(f"Successfully bound ROUTER socket to port {COORDINATOR_PORT}")
            
            # REP socket for health checks
            logger.info(f"Binding REP socket to port {HEALTH_CHECK_PORT}...")
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.setsockopt(zmq.LINGER, 0)
            self.health_socket.setsockopt(zmq.RCVTIMEO, 1000)
            self.health_socket.setsockopt(zmq.SNDTIMEO, 1000)
            self.health_socket.bind(f"tcp://*:{HEALTH_CHECK_PORT}")
            logger.info(f"Successfully bound REP socket to port {HEALTH_CHECK_PORT}")
            
            # Start background initialization thread
            logger.info("Starting background initialization thread...")
            self.init_thread = threading.Thread(target=self._initialize_background, daemon=True)
            self.init_thread.start()
            
            # Create readiness file
            logger.info("Creating readiness file...")
            self._create_readiness_file()
            
            logger.info("Coordinator Module initialization completed successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize Coordinator Module: {str(e)}"
            logger.error(error_msg)
            self.initialization_error = error_msg
            raise
    
    def _create_readiness_file(self):
        """Create a file to signal that the coordinator is ready."""
        try:
            readiness_file = Path("coordinator_ready")
            readiness_file.touch()
            logger.info("Created readiness file")
        except Exception as e:
            logger.error(f"Failed to create readiness file: {str(e)}")
    
    def _initialize_background(self):
        """Background initialization tasks."""
        try:
            logger.info("Starting background initialization...")
            
            # Discover services
            self._discover_services()
            
            # Mark initialization as complete
            self.is_initialized.set()
            logger.info("Background initialization completed successfully")
            
        except Exception as e:
            error_msg = f"Error in background initialization: {str(e)}"
            logger.error(error_msg)
            self.initialization_error = error_msg
    
    def _discover_services(self):
        """Discover available services in the system."""
        try:
            logger.info("Discovering services...")
            # For now, just initialize an empty services dictionary
            with self.services_lock:
                self.services = {}
            logger.info("Service discovery completed")
        except Exception as e:
            logger.error(f"Error discovering services: {str(e)}")
            raise
    
    def handle_request(self, request: Dict) -> Dict:
        """Handle incoming requests."""
        try:
            logger.info(f"handle_request received: {request} (type: {type(request)})")
            action = request.get("action")
            logger.info(f"Extracted action: {action}")
            
            if action in ["ping", "health"]:
                logger.info("Processing health check request")
                response = {
                    "status": "ok",
                    "ready": True,
                    "initialized": self.is_initialized.is_set(),
                    "message": "Coordinator is healthy",
                    "timestamp": datetime.now().isoformat(),
                    "uptime": time.time() - self.start_time,
                    "active_threads": threading.active_count(),
                    "queue_size": len(self.services) if hasattr(self, 'services') else 0
                }
                
                if self.initialization_error:
                    response.update({
                        "status": "error",
                        "ready": False,
                        "error": self.initialization_error
                    })
                
                logger.info(f"Health check response: {response}")
                return response
            
            # For other actions, check if initialization is complete
            if not self.is_initialized.is_set():
                return {
                    "status": "error",
                    "ready": False,
                    "error": "Coordinator is still initializing",
                    "initialized": False
                }
            
            # Handle other actions with thread safety
            with self.services_lock:
                if action == "start_service":
                    return self._start_service(request.get("service_name", ""))
                
                elif action == "stop_service":
                    return self._stop_service(request.get("service_name", ""))
                
                elif action == "restart_service":
                    return self._restart_service(request.get("service_name", ""))
                
                elif action == "get_service_status":
                    return self._get_service_status(request.get("service_name", ""))
                
                elif action == "list_services":
                    return {
                        "status": "success",
                        "services": self.services
                    }
                
                else:
                    logger.error(f"Unknown action received: {action}")
                    return {"status": "error", "error": f"Unknown action: {action}"}
        
        except Exception as e:
            logger.error(f"Exception in handle_request: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def run(self):
        """Main loop for handling requests."""
        try:
            logger.info("Coordinator main loop starting (polling both ROUTER and REP sockets)...")
            
            poller = zmq.Poller()
            poller.register(self.router_socket, zmq.POLLIN)
            poller.register(self.health_socket, zmq.POLLIN)
            
            while True:
                try:
                    socks = dict(poller.poll(1000))
                    
                    # Handle health check requests
                    if self.health_socket in socks:
                        message = self.health_socket.recv()
                        logger.info(f"Received health check message: {message}")
                        try:
                            request = json.loads(message)
                        except Exception as e:
                            logger.error(f"Failed to parse health check message: {e}")
                            self.health_socket.send_json({"status": "error", "error": str(e)})
                            continue
                        response = self.handle_request(request)
                        self.health_socket.send_json(response)
                        logger.info(f"Sent health check response: {response}")
                        continue
                    
                    # Handle main ROUTER requests
                    if self.router_socket in socks:
                        frames = self.router_socket.recv_multipart()
                        logger.info(f"Received frames: {frames}")
                        if len(frames) != 3:
                            logger.error(f"Invalid message format: {frames}")
                            continue
                        identity, empty, message = frames
                        try:
                            request = json.loads(message)
                        except Exception as e:
                            logger.error(f"Failed to parse ROUTER message: {e}")
                            response = {"status": "error", "error": str(e)}
                            self.router_socket.send_multipart([
                                identity,
                                b'',
                                json.dumps(response).encode()
                            ])
                            continue
                        response = self.handle_request(request)
                        self.router_socket.send_multipart([
                            identity,
                            b'',
                            json.dumps(response).encode()
                        ])
                        logger.info(f"Sent ROUTER response: {response}")
                except zmq.ZMQError as e:
                    logger.error(f"ZMQ error in main loop: {str(e)}")
                    continue
                except Exception as e:
                    logger.error(f"Error in main loop: {str(e)}")
                    continue
        except Exception as e:
            logger.error(f"Fatal error in main loop: {str(e)}")
            raise
        finally:
            self.router_socket.close()
            self.health_socket.close()
            self.context.term()
    
    def stop(self):
        """Stop the coordinator gracefully."""
        logger.info("Stopping Coordinator Module...")
        
        # Close sockets
        self.router_socket.close()
        self.health_socket.close()
        
        # Terminate context
        self.context.term()
        
        logger.info("Coordinator Module stopped")

def start_coordinator():
    """Start the Coordinator Module."""
    try:
        logger.info("Starting Coordinator Module...")
        coordinator = CoordinatorModule()
        logger.info("Coordinator Module initialized, starting main loop...")
        coordinator.run()
    except Exception as e:
        logger.exception("Coordinator Module crashed on startup: %s", str(e))
        raise

if __name__ == "__main__":
    try:
        start_coordinator()
    except Exception as e:
        logger.exception("Coordinator Module crashed on startup: %s", str(e))
        sys.exit(1)

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
