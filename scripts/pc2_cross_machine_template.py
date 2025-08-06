#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.log_setup import configure_logging
"""
PC2 Cross-Machine Agent Template
-------------------------------
Template for agents running on PC2 machine that need to communicate with main PC.
This template handles the cross-machine architecture requirements.
"""

import time
import logging
import zmq
import json
import os
import sys
import yaml
from typing import Dict, Any, Optional

# Add the repository root to Python path for absolute imports
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Import BaseAgent from main_pc_code - this works because we're using the same repo structure
from main_pc_code.src.core.base_agent import BaseAgent

# Import PC2-specific configuration
from pc2_code.agents.utils.config_loader import Config

# Load network configuration
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = os.path.join(repo_root, "config", "network_config.yaml")
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading network config: {e}")
        # Default fallback values
        return {
            "main_pc_ip": get_service_ip("mainpc"),
            "pc2_ip": get_service_ip("pc2"),
            "bind_address": "0.0.0.0",
            "secure_zmq": False
        }

# Load both configurations
network_config = load_network_config()
pc2_config = Config().get_config()

# Get machine IPs from config
MAIN_PC_IP = network_config.get("main_pc_ip", get_service_ip("mainpc"))
PC2_IP = network_config.get("pc2_ip", get_service_ip("pc2"))
BIND_ADDRESS = network_config.get("bind_address", "0.0.0.0")
SECURE_ZMQ = network_config.get("secure_zmq", False)

# Set up logging for PC2 environment
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pc2_code", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "pc2_agent_template.log")

logger = configure_logging(__name__),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PC2Template")


class PC2CrossMachineAgent(BaseAgent):
    """Template for agents running on the PC2 machine."""
    
    def __init__(self, port: Optional[int] = None, name: str = "PC2CrossMachineAgent"):
        """Initialize the PC2 agent.
        
        Args:
            port: The port number to use for ZMQ communication.
            name: Name of the agent.
        """
        # Call the BaseAgent's __init__ with proper parameters
        super().__init__(name=name, port=port)
        
        # Record start time for uptime calculation
        self.start_time = time.time()
        
        # Agent-specific initialization
        self.port = port if port is not None else 5580
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        
        # Bind to all interfaces so it can be accessed from main PC
        self.socket.bind(f"tcp://{BIND_ADDRESS}:{self.port}")
        
        # Initialize agent state
        self.running = True
        self.request_count = 0
        self.hostname = "PC2"
        
        # Set up connection to main PC if needed
        self.main_pc_connections = {}
        
        logger.info(f"{self.__class__.__name__} initialized on PC2 (IP: {PC2_IP}) port {self.port}")
        logger.info(f"MainPC IP configured as: {MAIN_PC_IP}")
    
    def connect_to_main_pc_service(self, service_name: str):
        """
        Connect to a service on the main PC using the network configuration.
        
        Args:
            service_name: Name of the service in the network config ports section
        
        Returns:
            ZMQ socket connected to the service
        """
        if service_name not in network_config.get("ports", {}):
            logger.error(f"Service {service_name} not found in network configuration")
            return None
            
        port = network_config["ports"][service_name]
        
        # Create a new socket for this connection
        socket = self.context.socket(zmq.REQ)
        
        # Configure security if enabled
        if SECURE_ZMQ:
            cert_dir = network_config.get("zmq_key_directory", "certificates")
            cert_path = os.path.join(repo_root, cert_dir)
            
            # Load client keys
            client_public = os.path.join(cert_path, "client.key")
            client_secret = os.path.join(cert_path, "client.key_secret")
            
            # Load server key
            server_public = os.path.join(cert_path, "server.key")
            
            if os.path.exists(client_public) and os.path.exists(client_secret) and os.path.exists(server_public):
                with open(client_public, 'rb') as f:
                    client_key = f.read()
                with open(client_secret, 'rb') as f:
                    client_secret_key = f.read()
                with open(server_public, 'rb') as f:
                    server_key = f.read()
                
                socket.curve_publickey = client_key
                socket.curve_secretkey = client_secret_key
                socket.curve_serverkey = server_key
                
                logger.info(f"Configured secure ZMQ for connection to {service_name}")
            else:
                logger.warning(f"Secure ZMQ enabled but certificates not found in {cert_path}")
        
        # Connect to the service
        socket.connect(f"tcp://{MAIN_PC_IP}:{port}")
        
        # Store the connection
        self.main_pc_connections[service_name] = socket
        
        logger.info(f"Connected to {service_name} on MainPC at {MAIN_PC_IP}:{port}")
        return socket
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Return health status information.
        
        Returns:
            Dict containing health status information.
        """
        # Get base status from parent
        base_status = super()._get_health_status()
        
        # Add PC2-specific health information
        base_status.update({
            'service': self.__class__.__name__,
            'uptime': time.time() - self.start_time,
            'request_count': self.request_count,
            'machine': 'PC2',
            'ip': PC2_IP,
            'status': 'healthy',
            'main_pc_connections': list(self.main_pc_connections.keys())
        })
        
        return base_status
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming request.
        
        Args:
            request: The request to process
            
        Returns:
            Response dictionary
        """
        # Handle health check requests
        if request.get('action') == 'health_check':
            return self._get_health_status()
        
        # Handle other request types
        self.request_count += 1
        return {
            'status': 'success',
            'message': f'PC2 agent on PC2 processed request #{self.request_count}',
            'timestamp': time.time()
        }
    
    def run(self):
        """Run the agent's main loop."""
        logger.info(f"Starting {self.__class__.__name__} on PC2 port {self.port}")
        
        try:
            while self.running:
                try:
                    # Wait for request with timeout
                    if self.socket.poll(1000, zmq.POLLIN):
                        message = self.socket.recv()
                        
                        # Parse message safely
                        try:
                            request = json.loads(message)
                        except json.JSONDecodeError:
                            request = {"error": "Invalid JSON"}
                            
                        logger.info(f"Received request: {request}")
                        
                        # Process the request
                        response = self.process_request(request)
                        
                        # Send the response
                        self.socket.send_json(response)
                    
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    # Send error response if socket is in a valid state
                    try:
                        self.socket.send_json({
                            'status': 'error',
                            'error': str(e)
                        })
                    except zmq.ZMQError:
                        pass
        
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            raise
        finally:
            logger.info("Exiting main loop")
    
    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info(f"Cleaning up {self.__class__.__name__} on PC2...")
        self.running = False
        
        # Close all connections to main PC
        for service_name, socket in self.main_pc_connections.items():
            try:
                socket.close()
                logger.info(f"Closed connection to {service_name} on MainPC")
            except Exception as e:
                logger.error(f"Error closing connection to {service_name}: {e}")
        
        # Close main socket
        if hasattr(self, 'socket') and self.socket:
            self.socket.close()
        
        # Terminate context
        if hasattr(self, 'context') and self.context:
            self.context.term()
        
        # Call parent cleanup
        super().cleanup()


if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = PC2CrossMachineAgent()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'} on PC2...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'} on PC2: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name} on PC2...")
            agent.cleanup() 