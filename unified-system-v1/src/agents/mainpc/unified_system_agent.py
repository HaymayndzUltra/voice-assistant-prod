#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from common.core.base_agent import BaseAgent

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
from common.utils.path_manager import PathManager
MAIN_PC_CODE_DIR = PathManager.get_project_root()
if MAIN_PC_CODE_DIR not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR)

from main_pc_code.utils.config_loader import load_config
config = load_config()
"""
Unified System Agent
-------------------
Central command center for system orchestration, service discovery, maintenance, and monitoring.
Provides comprehensive system management capabilities through ZMQ interface.
"""

from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import json
import logging
import os
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import threading
import time
import psutil
import subprocess
import signal
import socket
import platform
import traceback
from src.agents.mainpc.error_publisher import ErrorPublisher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(PathManager.get_logs_dir() / "unified_system_agent.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ZMQ configuration
SYSTEM_AGENT_PORT = 5568  # ROUTER socket for main communication
HEALTH_CHECK_PORT = 5569  # REP socket for health checks

# Service Discovery Configuration
ZMQ_PORT_RANGE = (5500, 5600)
HTTP_PORT_RANGE = (8000, 8100)

class UnifiedSystemAgent(BaseAgent):
    """
    Unified System Agent
    -------------------
    Central command center for system orchestration, service discovery, maintenance, and monitoring.
    Provides comprehensive system management capabilities through ZMQ interface.
    """

    def __init__(self):
        """Initialize the unified system agent."""
        try:
            logger.info("Starting UnifiedSystemAgent initialization...")
            
            # Initialize thread-safe data structures
            self.services_lock = threading.Lock()
            self.services = {}
            self.is_initialized = threading.Event()
            self.initialization_error = None
            
            # Initialize ZMQ context and sockets
            logger.info("Initializing ZMQ context...")
            self.context = None  # Using pool
            
            # ROUTER socket for main communication
            logger.info(f"Binding ROUTER socket to port {SYSTEM_AGENT_PORT}...")
            self.router_socket = self.context.socket(zmq.ROUTER)
            self.router_socket.setsockopt(zmq.LINGER, 0)
            self.router_socket.setsockopt(zmq.RCVTIMEO, 1000)
            self.router_socket.setsockopt(zmq.SNDTIMEO, 1000)
            self.router_socket.bind(f"tcp://{config.get('host')}:{self.port}")
            logger.info(f"Successfully bound ROUTER socket to port {self.port}")
            
            # REP socket for health checks
            logger.info(f"Binding REP socket to port {HEALTH_CHECK_PORT}...")
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.setsockopt(zmq.LINGER, 0)
            self.health_socket.setsockopt(zmq.RCVTIMEO, 1000)
            self.health_socket.setsockopt(zmq.SNDTIMEO, 1000)
            self.health_socket.bind(f"tcp://{config.get('host')}:{HEALTH_CHECK_PORT}")
            logger.info(f"Successfully bound REP socket to port {HEALTH_CHECK_PORT}")
            
            # Start background initialization thread
            logger.info("Starting background initialization thread...")
            self.init_thread = threading.Thread(target=self._initialize_background, daemon=True)
            self.init_thread.start()
            
            # Start service monitoring thread
            logger.info("Starting service monitoring thread...")
            self.monitor_thread = threading.Thread(target=self._monitor_services, daemon=True)
            self.monitor_thread.start()
            
            # Create readiness file
            logger.info("Creating readiness file...")
            self._create_readiness_file()
            
            logger.info("UnifiedSystemAgent initialization completed successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize UnifiedSystemAgent: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self.initialization_error = error_msg
            raise
    
    def _create_readiness_file(self):
        """Create a file to signal that the agent is ready."""
        try:
            readiness_file = Path("unified_system_ready")
            readiness_file.touch()
            logger.info("Created readiness file")
        except Exception as e:
            logger.error(f"Failed to create readiness file: {str(e)}")
    
    def _send_ready_signal(self):
        """Send an explicit ready signal to the Coordinator."""
        try:
            # Get face recognition port from config
            fra_port = self.config.get("main_pc_settings", {}).get("zmq_ports", {}).get("face_recognition_port", 5560)
            
            # Create a temporary socket to send ready signal
            ready_socket = self.context.socket(zmq.REQ)
            ready_socket.connect(f"tcp://{config.get('host')}:{fra_port}")  # Connect to FaceRecognitionAgent
            
            # Send ready signal
            ready_socket.send_json({
                "type": "status",
                "value": "READY",
                "agent": "UnifiedSystemAgent",
                "timestamp": datetime.now().isoformat()
            })
            
            # Wait for acknowledgment
            if ready_socket.poll(5000, zmq.POLLIN):
                response = ready_socket.recv_json()
                logger.info(f"Received ready signal acknowledgment: {response}")
            else:
                logger.warning("No acknowledgment received for ready signal")
            
            ready_
        except Exception as e:
            logger.error(f"Failed to send ready signal: {str(e)}")
    
    def _initialize_background(self):
        """Background initialization tasks."""
        try:
            logger.info("Starting background initialization...")
            
            # Load configuration
            self.config = self._load_config()
            logger.info("Configuration loaded successfully")
            
            # Discover services
            self._discover_services()
            
            # Mark initialization as complete
            self.is_initialized.set()
            logger.info("Background initialization completed successfully")
            
        except Exception as e:
            error_msg = f"Error in background initialization: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self.initialization_error = error_msg
    
    def _load_config(self) -> Dict:
        """Load configuration from file or environment."""
        try:
            # For now, return a basic configuration
            return {
                "services": {},
                "max_retries": 3,
                "retry_delay": 5,
                "monitoring_interval": 60
            }
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            return {}
    
    def _monitor_services(self):
        """Monitor running services and restart if needed."""
        while self.running:
            try:
                with self.services_lock:
                    for service_name, service_info in list(self.services.items()):
                        if not service_info.get("pid"):
                            continue
                        
                        try:
                            process = psutil.Process(service_info["pid"])
                            if not process.is_running():
                                logger.warning(f"Service {service_name} is not running, attempting restart")
                                self._restart_service(service_name)
                        except psutil.NoSuchProcess:
                            logger.warning(f"Service {service_name} process not found, attempting restart")
                            self._restart_service(service_name)
                
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in service monitoring: {str(e)}")
                time.sleep(60)  # Wait before retrying
    
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
    
    def _restart_service(self, service_name):
        """Restart a service by name."""
        logger.info(f"Restarting service: {service_name}")
        # Implementation would go here
        pass
    
    def handle_request(self, request: Dict) -> Dict:
        """Handle incoming requests."""
        try:
            logger.info(f"handle_request received: {request} (type: {type(request)})")
            action = request.get("action")
            logger.info(f"Extracted action: {action}")
            
            if action in ["ping", "health"]:
                logger.info("Processing health check request")
                return self._get_health_status()
            
            if not self.is_initialized.is_set():
                logger.warning("Received request but agent is not fully initialized yet")
                return {
                    "status": "error",
                    "ready": False,
                    "error": "Agent is still initializing",
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
                
                elif action == "cleanup_system":
                    return self._cleanup_system()
                
                elif action == "get_system_info":
                    return self._get_system_info()
                
                else:
                    logger.error(f"Unknown action received: {action}")
                    return {"status": "error", "error": f"Unknown action: {action}"}
        
        except Exception as e:
            logger.error(f"Exception in handle_request: {str(e)}\n{traceback.format_exc()}")
            return {"status": "error", "error": str(e)}
    
    def _get_service_status(self, service_name):
        """Get status of a specific service."""
        return {"status": "success", "service": service_name, "info": self.services.get(service_name, {})}
    
    def _start_service(self, service_name):
        """Start a service by name."""
        return {"status": "success", "message": f"Started service {service_name}"}
    
    def _stop_service(self, service_name):
        """Stop a service by name."""
        return {"status": "success", "message": f"Stopped service {service_name}"}
    
    def _cleanup_system(self):
        """Clean up system resources."""
        return {"status": "success", "message": "System cleanup completed"}
    
    def _get_system_info(self):
        """Get system information."""
        return {
            "status": "success", 
            "system_info": {
                "hostname": socket.gethostname(),
                "platform": platform.system(),
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total
            }
        }
    
    def run(self):
        """Main loop for handling requests."""
        try:
            logger.info("UnifiedSystemAgent main loop starting (polling both ROUTER and REP sockets)...")
            
            poller = zmq.Poller()
            poller.register(self.router_socket, zmq.POLLIN)
            poller.register(self.health_socket, zmq.POLLIN)
            
            while self.running:
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
                    logger.error(f"Error in main loop: {str(e)}\n{traceback.format_exc()}")
                    continue
        except Exception as e:
            logger.error(f"Fatal error in main loop: {str(e)}\n{traceback.format_exc()}")
            raise
        finally:
            self.router_
            self.health_
        # TODO-FIXME – removed stray 'self.' (O3 Pro Max fix)
    def _connect_to_agents(self):
        """Connect to all required agents."""
        try:
            # Connect to FaceRecognitionAgent
            fra_port = self.config.get("main_pc_settings", {}).get("zmq_ports", {}).get("face_recognition_port", 5560)
            ready_socket = self.context.socket(zmq.REQ)
            ready_socket.setsockopt(zmq.LINGER, 0)
            ready_socket.connect(f"tcp://{config.get('host')}:{fra_port}")  # Connect to FaceRecognitionAgent
            self.agent_sockets = {}
            self.agent_sockets['face_recognition'] = ready_socket
            logger.info(f"Connected to FaceRecognitionAgent on port {fra_port}")
            
            # Add other agent connections here...
            
        except Exception as e:
            logger.error(f"Error connecting to agents: {e}")
            raise
    
    def cleanup(self):
        """Clean up resources before exit."""
        try:
            logger.info("Cleaning up UnifiedSystemAgent resources...")
            self.running = False
            
            # Stop monitoring thread
            if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5)
                
            # Close sockets
            if hasattr(self, 'router_socket'):
                self.router_
            if hasattr(self, 'health_socket'):
                self.health_
            # Close agent sockets
            if hasattr(self, 'agent_sockets'):
                for socket_name, socket in self.agent_sockets.items():
                    socket.close()
            # Terminate ZMQ context
            if hasattr(self, 'context'):
                self.context.term()
            logger.info("UnifiedSystemAgent cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def stop(self):
        """Stop the agent gracefully."""
        logger.info("Stopping Unified System Agent...")
        self.cleanup()
        logger.info("Unified System Agent stopped")

    def _get_health_status(self):
        """Get the current health status of the agent.
        
        This method overrides the BaseAgent._get_health_status method to add 
        agent-specific health information.
        
        Returns:
            Dict[str, Any]: A dictionary containing health status information
        """
        # Get the base health status from parent class
        base_status = super()._get_health_status()
        
        # Add UnifiedSystemAgent-specific health metrics
        try:
            # System resource utilization
            system_metrics = {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent,
                "network_connections": len(psutil.net_connections())
            }
            
            # Service-specific metrics
            service_metrics = {
                "registered_services": len(self.services) if hasattr(self, 'services') else 0,
                "healthy_services": sum(1 for s in self.services.values() if s.get("status") == "healthy") if hasattr(self, 'services') else 0,
                "unhealthy_services": sum(1 for s in self.services.values() if s.get("status") != "healthy") if hasattr(self, 'services') else 0,
                "last_service_check": getattr(self, 'last_service_check', 'never')
            }
            
            # Update the base status with our additional information
            base_status.update({
                "system_metrics": system_metrics,
                "service_metrics": service_metrics,
                "initialization_complete": self.is_initialized.is_set(),
            })
            
        except Exception as e:
            logger.error(f"Error collecting health metrics: {e}")
            base_status.update({"health_metrics_error": str(e)})
        
        return base_status

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = UnifiedSystemAgent()
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