from common.core.base_agent import BaseAgent
from common.utils.log_setup import configure_logging
"""
Discovery Service Agent
Provides service discovery for distributed agents across the network.
"""

import os
import sys
import json
import time
import socket
import logging
import threading
import zmq
from datetime import datetime

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Configure logging
logger = configure_logging(__name__)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(PathManager.get_logs_dir() / "discovery_service.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DiscoveryService")

# Default discovery service port
DEFAULT_PORT = 5555

class DiscoveryService(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="DiscoveryService")
        self.port = port
        self.services = {}  # Format: {service_name: {ip, port, last_seen, machine_id}}
        self.lock = threading.Lock()
        self.running = False
        
        # Load configuration
        self.config = self.load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml"))
        if not self.config:
            logger.error("Failed to load configuration. Exiting.")
            sys.exit(1)
        
        # Initialize ZMQ
        self.context = zmq.Context()
        
        # Socket for service registration (REP)
        self.register_socket = self.context.socket(zmq.REP)
        self.register_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.register_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.register_socket.bind(f"tcp://*:{self.port}")
        
        # Socket for service queries (REP)
        self.query_socket = self.context.socket(zmq.REP)
        self.query_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.query_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.query_socket.bind(f"tcp://*:{self.port+1}")
        
        # Socket for service broadcasts (PUB)
        self.broadcast_socket = self.context.socket(zmq.PUB)
        self.broadcast_socket.bind(f"tcp://*:{self.port+2}")
        
        logger.info(f"Discovery Service initialized on ports {self.port}-{self.port+2}")
    
    def load_config(self):
        """Load the distributed configuration"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                  "config", "distributed_config.json")
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return None
    
    def get_local_ip(self):
        """Get the local IP address of this machine"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            logger.error(f"Failed to get local IP: {e}")
            return "localhost"
    
    def register_service(self, service_data):
        """Register a service with the discovery service"""
        with self.lock:
            service_name = service_data.get("name")
            if not service_name:
                return {"status": "error", "message": "Service name is required"}
            
            # Update or add the service
            self.services[service_name] = {
                "ip": service_data.get("ip", "localhost"),
                "port": service_data.get("port", 0),
                "machine_id": service_data.get("machine_id", "unknown"),
                "last_seen": datetime.now().timestamp()
            }
            
            logger.info(f"Registered service: {service_name} at {self.services[service_name]['ip']}:{self.services[service_name]['port']}")
            
            # Broadcast the update
            self.broadcast_update(service_name)
            
            return {"status": "ok", "message": f"Service {service_name} registered successfully"}
    
    def query_service(self, service_name):
        """Query for a service by name"""
        with self.lock:
            if service_name in self.services:
                return {"status": "ok", "service": self.services[service_name]}
            else:
                return {"status": "error", "message": f"Service {service_name} not found"}
    
    def list_services(self):
        """List all registered services"""
        with self.lock:
            return {"status": "ok", "services": self.services}
    
    def broadcast_update(self, service_name):
        """Broadcast a service update to all listeners"""
        try:
            with self.lock:
                if service_name in self.services:
                    message = {
                        "event": "service_update",
                        "service_name": service_name,
                        "service_data": self.services[service_name]
                    }
                    self.broadcast_socket.send_string(json.dumps(message))
        except Exception as e:
            logger.error(f"Error broadcasting update: {e}")
    
    def cleanup_services(self):
        """Remove stale services"""
        while self.running:
            try:
                now = datetime.now().timestamp()
                with self.lock:
                    stale_services = []
                    for service_name, service_data in self.services.items():
                        if now - service_data["last_seen"] > 60:  # 60 seconds timeout
                            stale_services.append(service_name)
                    
                    for service_name in stale_services:
                        logger.info(f"Removing stale service: {service_name}")
                        del self.services[service_name]
                        # Broadcast the removal
                        message = {
                            "event": "service_removed",
                            "service_name": service_name
                        }
                        self.broadcast_socket.send_string(json.dumps(message))
            except Exception as e:
                logger.error(f"Error in cleanup: {e}")
            
            time.sleep(30)  # Check every 30 seconds
    
    def register_handler(self):
        """Handle service registration requests"""
        while self.running:
            try:
                message = self.register_socket.recv_string()
                data = json.loads(message)
                
                response = {}
                if data.get("action") == "register":
                    response = self.register_service(data.get("service", {}))
                elif data.get("action") == "heartbeat":
                    service_name = data.get("service_name")
                    with self.lock:
                        if service_name in self.services:
                            self.services[service_name]["last_seen"] = datetime.now().timestamp()
                            response = {"status": "ok", "message": "Heartbeat received"}
                        else:
                            response = {"status": "error", "message": "Service not found"}
                else:
                    response = {"status": "error", "message": "Unknown action"}
                
                self.register_socket.send_string(json.dumps(response))
            except Exception as e:
                logger.error(f"Error in register handler: {e}")
                try:
                    self.register_socket.send_string(json.dumps({"status": "error", "message": str(e)}))
                except:
                    pass
    
    def query_handler(self):
        """Handle service query requests"""
        while self.running:
            try:
                message = self.query_socket.recv_string()
                data = json.loads(message)
                
                response = {}
                if data.get("action") == "query":
                    service_name = data.get("service_name")
                    response = self.query_service(service_name)
                elif data.get("action") == "list":
                    response = self.list_services()
                else:
                    response = {"status": "error", "message": "Unknown action"}
                
                self.query_socket.send_string(json.dumps(response))
            except Exception as e:
                logger.error(f"Error in query handler: {e}")
                try:
                    self.query_socket.send_string(json.dumps({"status": "error", "message": str(e)}))
                except:
                    pass
    
    def register_local_services(self):
        """Register services from the local machine based on config"""
        try:
            # Identify current machine
            local_ip = self.get_local_ip()
            current_machine = None
            
            for machine_id, machine_info in self.config["machines"].items():
                if machine_info["ip"] == local_ip:
                    current_machine = machine_id
                    break
            
            if not current_machine:
                logger.warning(f"Could not identify current machine with IP {local_ip}")
                return
            
            logger.info(f"Registering local services for machine: {current_machine}")
            
            # Register each agent as a service
            machine_config = self.config["machines"][current_machine]
            for agent_name in machine_config.get("agents", []):
                port = self.config["ports"].get(agent_name, 0)
                
                service_data = {
                    "name": agent_name,
                    "ip": local_ip,
                    "port": port,
                    "machine_id": current_machine
                }
                
                self.register_service(service_data)
        except Exception as e:
            logger.error(f"Error registering local services: {e}")
    
    def run(self):
        """Run the discovery service"""
        self.running = True
        
        # Start handler threads
        register_thread = threading.Thread(target=self.register_handler)
        register_thread.daemon = True
        register_thread.start()
        
        query_thread = threading.Thread(target=self.query_handler)
        query_thread.daemon = True
        query_thread.start()
        
        cleanup_thread = threading.Thread(target=self.cleanup_services)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
        # Register local services
        self.register_local_services()
        
        logger.info("Discovery Service running. Press Ctrl+C to stop.")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down Discovery Service...")
            self.running = False
            # Wait for threads to finish
            register_thread.join(timeout=2)
            query_thread.join(timeout=2)
            cleanup_thread.join(timeout=2)
            logger.info("Discovery Service stopped.")

if __name__ == "__main__":
    # Get port from config if available
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                  "config", "distributed_config.json")
        with open(config_path, 'r') as f:
            config = json.load(f)
            port = config.get("discovery_service", {}).get("port", DEFAULT_PORT)
    except:
        port = DEFAULT_PORT
    
    service = DiscoveryService(port=port)
    service.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise