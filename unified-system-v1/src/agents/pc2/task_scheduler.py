import zmq
import yaml
import json
import logging
import threading
import time
import sys
from pathlib import Path
import os
from datetime import datetime
from typing import Dict, Any, Optional
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.path_manager import PathManager

# Import path manager for containerization-friendly paths
sys.path.insert(0, str(PathManager.get_project_root()))

from main_pc_code.utils.network_utils import get_zmq_connection_string, get_machine_ip
from common.env_helpers import get_env

logging.basicConfig
from common.core.base_agent import BaseAgent
from src.agents.pc2.utils.config_loader import Config

# Load configuration at the module level
config = Config().get_config()
logger = logging.getLogger('TaskScheduler')

# Load network configuration
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = Path(PathManager.get_project_root()) / "config" / "network_config.yaml"
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network config: {e}")
        # Default fallback values
        return {
            "main_pc_ip": get_mainpc_ip(),
            "pc2_ip": get_pc2_ip(),
            "bind_address": "0.0.0.0",
            "secure_zmq": False
        }

# Load both configurations
network_config = load_network_config()

# Get machine IPs from config
MAIN_PC_IP = get_mainpc_ip())
PC2_IP = network_config.get("pc2_ip", get_pc2_ip())
BIND_ADDRESS = network_config.get("bind_address", "0.0.0.0")

class TaskSchedulerAgent(BaseAgent):
    """
    TaskSchedulerAgent:  Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').
    """
    def __init__(self, port=7115, health_port=7116, async_processor_port=5555):
        super().__init__(name="TaskSchedulerAgent", port=7115)
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
        self.async_processor_port = async_processor_port
        self.context = zmq.Context()
        self.initialized = False
        self.initialization_error = None
        self._setup_sockets()
        self._start_health_check()
        self._init_thread = threading.Thread(target=self._initialize_background, daemon=True)
        self._init_thread.start()
        logger.info(f"TaskSchedulerAgent starting on port {port} (health: {health_port})")

    

        self.error_bus_port = 7150

        self.error_bus_host = get_pc2_ip()

        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"

        self.error_bus_pub = self.context.socket(zmq.PUB)

        self.error_bus_pub.connect(self.error_bus_endpoint)
    def _setup_sockets(self):
        try:
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://*:{self.port}")
            logger.info(f"TaskSchedulerAgent main socket bound to port {self.port}")
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
        # Socket to communicate with AsyncProcessor
        self.async_socket = self.context.socket(zmq.REQ)
        self.async_socket.connect(get_zmq_connection_string(self.async_processor_port, "localhost"))

    def _start_health_check(self):
        def health_check_loop():
            while True:
                try:
                    request = self.health_socket.recv_json()
                    if request.get('action') == 'health_check':
                        response = {
                            'status': 'ok' if self.initialized else 'initializing',
                            'service': 'TaskScheduler',
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
            # Simulate any heavy initialization if needed
            time.sleep(1)
            self.initialized = True
            logger.info("TaskSchedulerAgent initialization completed")
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"TaskSchedulerAgent initialization failed: {str(e)}")

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        action = request.get('action')
        if action == 'schedule_task':
            # Forward to AsyncProcessor
            self.async_socket.send_json({
                'type': request.get('type'),
                'data': request.get('data'),
                'priority': request.get('priority', 'medium')
            })
            response = self.async_socket.recv_json()
            return response
        elif action == 'ping':
            return {'status': 'success', 'message': 'pong'}
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}

    def run(self):
        logger.info("Starting TaskSchedulerAgent main loop")
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

        # Add any additional health information specific to TaskSchedulerAgent
        base_status.update({
            'service': 'TaskSchedulerAgent',
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
        self.async_socket.close()
        self.context.term()
        logger.info("TaskSchedulerAgent shutdown complete")

    def connect_to_main_pc_service(self, service_name: str):
        if not hasattr(self, 'main_pc_connections'):
            self.main_pc_connections = {}
        ports = network_config.get("ports") if network_config and isinstance(network_config.get("ports"), dict) else {}
        if service_name not in ports:
            logger.error(f"Service {service_name} not found in network configuration")
            return None
        port = ports[service_name]
        socket = self.context.socket(zmq.REQ)
        socket.connect(f"tcp://{MAIN_PC_IP}:{port}")
        self.main_pc_connections[service_name] = socket
        logger.info(f"Connected to {service_name} on MainPC at {MAIN_PC_IP}:{port}")
        return socket

if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = TaskSchedulerAgent()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'} on PC2...")
    except Exception as e:
        import traceback

# Standardized environment variables (Blueprint.md Step 4)
from common.utils.env_standardizer import get_mainpc_ip, get_pc2_ip, get_current_machine, get_env
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'} on PC2: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name} on PC2...")
            agent.cleanup()
