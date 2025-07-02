import zmq
import yaml
import json
import logging
import threading
import time
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig
from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config

# Load configuration at the module level
config = load_config()(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/health_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('HealthMonitor')

class HealthMonitorAgent(BaseAgent):
    def __init__(self, port=7114, health_port=7115):
         super().__init__(name="HealthMonitorAgent", port=7114)

         # Record start time for uptime calculation

         self.start_time = time.time()

         

         # Initialize agent state

         self.running = True

         self.request_count = 0

         

         # Set up connection to main PC if needed

         self.main_pc_connections = {}

         

         logger.info(f"{self.__class__.__name__} initialized on PC2 (IP: {PC2_IP}) port {self.port}")

self.port = port
        self.health_port = health_port
        self.context = zmq.Context()
        self.initialized = False
        self.initialization_error = None
        self.agent_status = {}
        self._setup_sockets()
        self._start_health_check()
        self._init_thread = threading.Thread(target=self._initialize_background, daemon=True)
        self._init_thread.start()
        logger.info(f"HealthMonitorAgent starting on port {port} (health: {health_port})")

    def _setup_sockets(self):
        try:
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://*:{self.port}")
            logger.info(f"HealthMonitorAgent main socket bound to port {self.port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind main socket to port {self.port}: {str(e)}")
            raise
        try:
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.bind(f"tcp://*:{self.health_port}")
            logger.info(f"Health check endpoint on port {self.health_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind health check to port {self.health_port}: {str(e)}")
            raise

    def _start_health_check(self):
        def health_check_loop():
            while True:
                try:
                    request = self.health_socket.recv_json()
                    if request.get('action') == 'health_check':
                        response = {
                            'status': 'ok' if self.initialized else 'initializing',
                            'service': 'HealthMonitor',
                            'initialization_status': 'complete' if self.initialized else 'in_progress',
                            'port': self.port,
                            'health_port': self.health_port,
                            'timestamp': datetime.now().isoformat()
                        }
                        if self.initialization_error:
                            response['initialization_error'] = str(self.initialization_error)
                    else:
                        response = {
                            'status': 'unknown_action',
                            'message': f"Unknown action: {request.get('action', 'none')}"
                        }
                    self.health_socket.send_json(response)
                except Exception as e:
                    logger.error(f"Health check error: {str(e)}")
                    time.sleep(1)
        health_thread = threading.Thread(target=health_check_loop, daemon=True)
        health_thread.start()

    def _initialize_background(self):
        try:
            # Simulate heavy initialization (e.g., loading config, agent list)
            time.sleep(1)
            self.agent_status = {}
            self.initialized = True
            logger.info("HealthMonitorAgent initialization completed")
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"HealthMonitorAgent initialization failed: {str(e)}")

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        action = request.get('action')
        if action == 'get_status':
            return {
                'status': 'success',
                'agent_status': self.agent_status,
                'timestamp': datetime.now().isoformat()
            }
        elif action == 'ping':
            return {'status': 'success', 'message': 'pong'}
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}

    def run(self):
        logger.info("Starting HealthMonitorAgent main loop")
        while True:
            try:
                if self.socket.poll(1000) > 0:
                    request = self.socket.recv_json()
                    response = self.handle_request(request)
                    self.socket.send_json(response)
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                time.sleep(1)


    def _get_health_status(self) -> dict:

        """Return health status information."""

        base_status = super()._get_health_status()

        # Add any additional health information specific to HealthMonitorAgent

        base_status.update({

            'service': 'HealthMonitorAgent',

            'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0,

            'additional_info': {}

        })

        return base_status


    def cleanup(self):

        """Clean up resources before shutdown."""

        logger.info("Cleaning up resources...")

        # Add specific cleanup code here

        super().cleanup()

    def shutdown(self):
        self.socket.close()
        self.health_socket.close()
        self.context.term()
        logger.info("HealthMonitorAgent shutdown complete")





if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = HealthMonitorAgent()
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

# Load network configuration
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "network_config.yaml")
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network config: {e}")
        # Default fallback values
        return {
            "main_pc_ip": "192.168.100.16",
            "pc2_ip": "192.168.100.17",
            "bind_address": "0.0.0.0",
            "secure_zmq": False
        }

# Load both configurations
network_config = load_network_config()

# Get machine IPs from config
MAIN_PC_IP = network_config.get("main_pc_ip", "192.168.100.16")
PC2_IP = network_config.get("pc2_ip", "192.168.100.17")
BIND_ADDRESS = network_config.get("bind_address", "0.0.0.0")
print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()

    def connect_to_main_pc_service(self, service_name: str):

        """

        Connect to a service on the main PC using the network configuration.

        

        Args:

            service_name: Name of the service in the network config ports section

        

        Returns:

            ZMQ socket connected to the service

        """

        if not hasattr(self, 'main_pc_connections'):

            self.main_pc_connections = {}

            

        if service_name not in network_config.get("ports", {}):

            logger.error(f"Service {service_name} not found in network configuration")

            return None

            

        port = network_config["ports"][service_name]

        

        # Create a new socket for this connection

        socket = self.context.socket(zmq.REQ)

        

        # Connect to the service

        socket.connect(f"tcp://{MAIN_PC_IP}:{port}")

        

        # Store the connection

        self.main_pc_connections[service_name] = socket

        

        logger.info(f"Connected to {service_name} on MainPC at {MAIN_PC_IP}:{port}")

        return socket
