from main_pc_code.src.core.base_agent import BaseAgent
import zmq
import json
import logging
from main_pc_code.agents.error_publisher import ErrorPublisher
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


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", ".."))))
from common.utils.path_env import get_path, join_path, get_file_path
# Configure logging

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = get_main_pc_code()
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ZMQ Configuration
SYSTEM_AGENT_PORT = 5568
HEALTH_CHECK_PORT = 5569

class UnifiedSystemAgent(BaseAgent):
    """Unified system management agent that handles orchestration, service discovery, and maintenance."""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="UnifiedSystemAgent2")
        """Initialize the unified system agent."""
        # Initialize thread-safe data structures
        self.services_lock = threading.Lock()
        self.services = {}
        self.is_initialized = threading.Event()
        
        # Initialize ZMQ context and sockets
        self.context = zmq.Context()
        
        # Main socket for general communication (ROUTER)
        self.main_socket = self.context.socket(zmq.ROUTER)
        self.main_socket.bind(f"tcp://*:{SYSTEM_AGENT_PORT}")
        logger.info(f"Bound ROUTER socket to port {SYSTEM_AGENT_PORT}")
        
        # Health check socket (REP)
        self.health_socket = self.context.socket(zmq.REP)
        self.health_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.health_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.health_socket.bind(f"tcp://*:{HEALTH_CHECK_PORT}")
        logger.info(f"Bound REP socket to port {HEALTH_CHECK_PORT}")
        
        # Start background initialization thread
        self.init_thread = threading.Thread(target=self._initialize_background, daemon=True)
        self.init_thread.start()
        if not hasattr(self, "_background_threads"):
            self._background_threads = []
        self._background_threads.append(self.init_thread)
        
        # Start service monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_services, daemon=True)
        self.monitor_thread.start()
        # Initialise error publisher
        self.error_publisher = ErrorPublisher(self.name)
        if not hasattr(self, "_background_threads"):
            self._background_threads = []
        self._background_threads.append(self.monitor_thread)
        
        logger.info("UnifiedSystemAgent initialized")
    
    def _initialize_background(self):
        """Background initialization tasks."""
        try:
            # Load configuration
            self.config = self._load_config()
            logger.info("Configuration loaded successfully")
            
            # Discover services
            self._discover_services()
            
            # Mark initialization as complete
            self.is_initialized.set()
            logger.info("Background initialization completed")
            
        except Exception as e:
            logger.error(f"Error in background initialization: {str(e)}")
            self.error_publisher.publish_error(error_type="background_init", severity="high", details=str(e))
            # Even if initialization fails, we'll still respond to health checks
    
    def _load_config(self) -> Dict:
        """Load system configuration."""
        try:
            config_path = Path(join_path("config", "system_config.py"))
            if not config_path.exists():
                logger.error(f"Configuration file not found: {config_path}")
                return {}
            
            # Import the configuration module
            import system_config

            
            # Get the configuration
            config = {
                "main_pc": system_config.MAIN_PC_CONFIG,
                "pc2": system_config.PC2_CONFIG,
                "agents": system_config.AGENT_CONFIGS
            }
            
            return config
            
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            return {}
    
    def _discover_services(self):
        """Discover running services."""
        try:
            discovered_services = {}
            
            # Scan for ZMQ services
            for port in range(5500, 5600):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.1)
                    result = sock.connect_ex(('localhost', port))
                    if result == 0:
                        discovered_services[f"zmq_{port}"] = {
                            "type": "zmq",
                            "port": port,
                            "status": "running",
                            "last_check": datetime.now().isoformat()
                        }
                    sock.close()
                except:
                    continue
            
            # Scan for HTTP services
            for port in range(8000, 8100):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.1)
                    result = sock.connect_ex(('localhost', port))
                    if result == 0:
                        discovered_services[f"http_{port}"] = {
                            "type": "http",
                            "port": port,
                            "status": "running",
                            "last_check": datetime.now().isoformat()
                        }
                    sock.close()
                except:
                    continue
            
            # Update services with thread safety
            with self.services_lock:
                self.services.update(discovered_services)
            
        except Exception as e:
            logger.error(f"Error discovering services: {str(e)}")
    
    def handle_request(self, request: Dict) -> Dict:
        """Handle incoming requests."""
        try:
            action = request.get("action")
            logger.info(f"Received request with action: {action}")
            
            if action in ["ping", "health"]:
                logger.info("Processing health check request")
                return {
                    "status": "ok",
                    "ready": True,
                    "initialized": self.is_initialized.is_set(),
                    "message": "Unified System Agent is healthy",
                    "timestamp": datetime.now().isoformat()
                }
            
            # For other actions, check if initialization is complete
            if not self.is_initialized.is_set():
                return {
                    "status": "error",
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
                    return {
                        "status": "error",
                        "error": f"Unknown action: {action}"
                    }
        
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _start_service(self, service_name: str) -> Dict:
        """Start a service."""
        try:
            if service_name in self.services:
                return {
                    "status": "error",
                    "error": f"Service {service_name} is already running"
                }
            
            # Get service configuration
            service_config = self.config.get("services", {}).get(service_name)
            if not service_config:
                return {
                    "status": "error",
                    "error": f"Service {service_name} not found in configuration"
                }
            
            # Start the service
            process = subprocess.Popen(
                service_config["command"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Update service registry
            self.services[service_name] = {
                "type": service_config.get("type", "unknown"),
                "pid": process.pid,
                "status": "running",
                "start_time": datetime.now().isoformat(),
                "last_check": datetime.now().isoformat()
            }
            
            return {
                "status": "success",
                "pid": process.pid
            }
            
        except Exception as e:
            logger.error(f"Error starting service: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _stop_service(self, service_name: str) -> Dict:
        """Stop a service."""
        try:
            if service_name not in self.services:
                return {
                    "status": "error",
                    "error": f"Service {service_name} not found"
                }
            
            service = self.services[service_name]
            if "pid" in service:
                try:
                    os.kill(service["pid"], signal.SIGTERM)
                    time.sleep(1)  # Give it time to terminate
                    
                    # Check if process is still running
                    try:
                        os.kill(service["pid"], 0)
                        # If we get here, process is still running
                        os.kill(service["pid"], signal.SIGKILL)
                    except OSError:
                        # Process is already terminated
                        pass
                    
                    # Update service registry
                    self.services[service_name]["status"] = "stopped"
                    self.services[service_name]["stop_time"] = datetime.now().isoformat()
                    
                    return {
                        "status": "success"
                    }
                    
                except Exception as e:
                    logger.error(f"Error stopping service: {str(e)}")
                    return {
                        "status": "error",
                        "error": str(e)
                    }
            else:
                return {
                    "status": "error",
                    "error": f"Service {service_name} has no PID"
                }
            
        except Exception as e:
            logger.error(f"Error stopping service: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _restart_service(self, service_name: str) -> Dict:
        """Restart a service."""
        try:
            # Stop the service
            stop_result = self._stop_service(service_name)
            if stop_result["status"] == "error":
                return stop_result
            
            # Wait a moment
            time.sleep(2)
            
            # Start the service
            return self._start_service(service_name)
            
        except Exception as e:
            logger.error(f"Error restarting service: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _get_service_status(self, service_name: str) -> Dict:
        """Get status of a service."""
        try:
            if service_name not in self.services:
                return {
                    "status": "error",
                    "error": f"Service {service_name} not found"
                }
            
            service = self.services[service_name]
            if "pid" in service:
                try:
                    os.kill(service["pid"], 0)
                    service["status"] = "running"
                except OSError:
                    service["status"] = "stopped"
            
            service["last_check"] = datetime.now().isoformat()
            
            return {
                "status": "success",
                "service": service
            }
            
        except Exception as e:
            logger.error(f"Error getting service status: {str(e)}")
            self.error_publisher.publish_error(error_type="service_status", severity="medium", details=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _cleanup_system(self) -> Dict:
        """Perform system cleanup."""
        try:
            # Clean up temporary files
            temp_dir = Path("agents/temp")
            if temp_dir.exists():
                for file in temp_dir.glob("*"):
                    try:
                        file.unlink()
                    except:
                        pass
            
            # Clean up logs
            log_dir = Path("agents/logs")
            if log_dir.exists():
                for file in log_dir.glob("*.log"):
                    if (datetime.now() - datetime.fromtimestamp(file.stat().st_mtime)).days > 7:
                        try:
                            file.unlink()
                        except:
                            pass
            
            # Clean up cache
            cache_dir = Path("agents/cache")
            if cache_dir.exists():
                for file in cache_dir.glob("*"):
                    if (datetime.now() - datetime.fromtimestamp(file.stat().st_mtime)).days > 1:
                        try:
                            file.unlink()
                        except:
                            pass
            
            return {
                "status": "success",
                "message": "System cleanup completed"
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up system: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _get_system_info(self) -> Dict:
        """Get system information."""
        try:
            info = {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "disk_usage": psutil.disk_usage('/').percent,
                "timestamp": datetime.now().isoformat()
            }
            
            return {
                "status": "success",
                "info": info
            }
            
        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _monitor_services(self):
        """Background thread for service monitoring."""
        while True:
            try:
                # Check all services
                for service_name in list(self.services.keys()):
                    self._get_service_status(service_name)
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in service monitoring: {str(e)}")
                time.sleep(30)  # Wait before retrying
    
    def run(self):
        """Run the agent's main loop."""
        logger.info("Starting UnifiedSystemAgent main loop")
        
        # Set up poller for non-blocking receive
        poller = zmq.Poller()
        poller.register(self.main_socket, zmq.POLLIN)
        poller.register(self.health_socket, zmq.POLLIN)
        
        while True:
            try:
                # Wait for any message with timeout
                socks = dict(poller.poll(1000))  # 1 second timeout
                
                # Handle health check socket
                if self.health_socket in socks:
                    logger.debug("Received health check request")
                    message = self.health_socket.recv_json()
                    response = self.handle_request(message)
                    logger.debug(f"Sending health check response: {response}")
                    self.health_socket.send_json(response)
                    logger.debug("Health check response sent successfully")
                
                # Handle main socket
                if self.main_socket in socks:
                    logger.debug("Received main request")
                    identity, _, message = self.main_socket.recv_multipart()
                    message = json.loads(message)
                    response = self.handle_request(message)
                    logger.debug(f"Sending main response: {response}")
                    self.main_socket.send_multipart([identity, b"", json.dumps(response).encode()])
                    logger.debug("Main response sent successfully")
                
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                try:
                    error_response = {
                        "status": "error",
                        "error": str(e)
                    }
                    logger.error(f"Sending error response: {error_response}")
                    if self.health_socket in socks:
                        self.health_socket.send_json(error_response)
                    elif self.main_socket in socks:
                        self.main_socket.send_multipart([identity, b"", json.dumps(error_response).encode()])
                    logger.debug("Error response sent successfully")
                except Exception as send_error:
                    logger.error(f"Failed to send error response: {str(send_error)}")

if __name__ == "__main__":
    agent = UnifiedSystemAgent()
    agent.run() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise