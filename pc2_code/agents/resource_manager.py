import zmq
from pathlib import Path
import yaml
import json
import logging
import threading
import time
import sys
import os
import psutil
from datetime import datetime
from collections import deque
from typing import Dict, Any, Optional
from common.config_manager import get_service_ip, get_service_url, get_redis_url


# Import path utilities
from common.utils.path_manager import PathManager
# Try to import torch for GPU monitoring
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    TORCH_AVAILABLE = False

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
from common.core.base_agent import BaseAgent
from pc2_code.agents.utils.config_loader import Config

# Load configuration at the module level
config = Config().get_config()
logger = logging.getLogger(__name__)

class ResourceManager(BaseAgent):
    """
    ResourceManager:  Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').
    """
    def __init__(self, port=7113, health_port=7114):
         super().__init__(name="ResourceManager", port=7113)

         # Record start time for uptime calculation
         self.start_time = time.time()

         # Initialize agent state
         self.running = True
         self.request_count = 0

         # Set up connection to main PC if needed
         self.main_pc_connections = {}
         logger.info(f"{self.__class__.__name__} initialized on PC2 port {self.port}")
         self.port = port
         self.health_port = health_port
         self.context = zmq.Context()
         self.initialized = False
         self.initialization_error = None
         
         # Resource thresholds
         self.cpu_threshold = 80  # percentage
         self.memory_threshold = 80  # percentage
         self.gpu_threshold = 80  # percentage if available
         
         # Resource allocation tracking
         self.allocated_resources = {}
         self.resource_locks = {}
         self.stats_history = deque(maxlen=100)
         
         # Setup sockets first for immediate health check availability
         self._setup_sockets()
         
         # Start health check endpoint immediately
         self._start_health_check()
         
         # Start initialization in background thread
         self._init_thread = threading.Thread(target=self._initialize_background, daemon=True)
         self._init_thread.start()
         
         logger.info(f"ResourceManager starting on port {port} (health: {health_port})")
    
        # ✅ Using BaseAgent's built-in error reporting (UnifiedErrorHandler)
    def _setup_sockets(self):
        """Setup ZMQ sockets."""
        # Main socket for handling requests
        try:
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://*:{self.port}")
            logger.info(f"ResourceManager main socket bound to port {self.port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind main socket to port {self.port}: {str(e)}")
            raise
        
        # Health check socket
        try:
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.bind(f"tcp://*:{self.health_port}")
            logger.info(f"Health check endpoint on port {self.health_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind health check to port {self.health_port}: {str(e)}")
            raise
    
    def _start_health_check(self):
        """Start health check endpoint in background thread."""
        def health_check_loop():
            while True:
                try:
                    request = self.health_socket.recv_json()
                    if request.get('action') == 'health_check':
                        response = {
                            'status': 'ok' if self.initialized else 'initializing',
                            'service': 'ResourceManager',
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
        """Initialize agent components in background thread."""
        try:
            # Initialize resource monitoring
            self._init_resource_monitoring()
            self.initialized = True
            logger.info("ResourceManager initialization completed")
            
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"ResourceManager initialization failed: {str(e)}")
    
    def _init_resource_monitoring(self):
        """Initialize resource monitoring capabilities."""
        # Test resource monitoring
        self.get_current_stats()
        logger.info("Resource monitoring initialized")
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current resource statistics."""
        stats = {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'memory_available': psutil.virtual_memory().available,
            'memory_total': psutil.virtual_memory().total,
            'disk_usage': psutil.disk_usage('/').percent,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add GPU stats if available
        if TORCH_AVAILABLE and torch.cuda.is_available():
            try:
                max_memory = torch.cuda.max_memory_allocated()
                if max_memory > 0:
                    stats['gpu_memory_percent'] = torch.cuda.memory_allocated() / max_memory * 100
                else:
                    stats['gpu_memory_percent'] = 0.0
                stats['gpu_memory_allocated'] = torch.cuda.memory_allocated()
                stats['gpu_memory_reserved'] = torch.cuda.memory_reserved()
            except Exception as e:
                logger.warning(f"Failed to get GPU stats: {str(e)}")
                stats['gpu_memory_percent'] = 0.0
        else:
            stats['gpu_memory_percent'] = 0.0
        
        self.stats_history.append(stats)
        return stats
    
    def check_resources_available(self) -> bool:
        """Check if resources are available for processing."""
        stats = self.get_current_stats()
        
        if stats['cpu_percent'] > self.cpu_threshold:
            return False
        
        if stats['memory_percent'] > self.memory_threshold:
            return False
        
        if 'gpu_memory_percent' in stats and stats['gpu_memory_percent'] > self.gpu_threshold:
            return False
        
        return True
    
    def allocate_resources(self, resource_id: str, resource_type: str, amount: float) -> Dict[str, Any]:
        """Allocate resources for a specific task."""
        try:
            if resource_id in self.allocated_resources:
                return {
                    'status': 'error',
                    'message': f'Resource ID {resource_id} already allocated'
                }
            
            # Check if resources are available
            if not self.check_resources_available():
                return {
                    'status': 'error',
                    'message': 'Insufficient system resources'
                }
            
            # Allocate resources
            self.allocated_resources[resource_id] = {
                'type': resource_type,
                'amount': amount,
                'allocated_at': datetime.now().isoformat(),
                'status': 'active'
            }
            
            logger.info(f"Allocated {amount} {resource_type} for {resource_id}")
            return {
                'status': 'success',
                'resource_id': resource_id,
                'message': f'Allocated {amount} {resource_type}'
            }
            
        except Exception as e:
            logger.error(f"Error allocating resources: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def release_resources(self, resource_id: str) -> Dict[str, Any]:
        """Release allocated resources."""
        try:
            if resource_id not in self.allocated_resources:
                return {
                    'status': 'error',
                    'message': f'Resource ID {resource_id} not found'
                }
            
            resource_info = self.allocated_resources.pop(resource_id)
            resource_info['released_at'] = datetime.now().isoformat()
            resource_info['status'] = 'released'
            
            logger.info(f"Released resources for {resource_id}")
            return {
                'status': 'success',
                'resource_id': resource_id,
                'message': 'Resources released successfully'
            }
            
        except Exception as e:
            logger.error(f"Error releasing resources: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_resource_status(self) -> Dict[str, Any]:
        """Get current resource allocation status."""
        try:
            stats = self.get_current_stats()
            return {
                'status': 'success',
                'current_stats': stats,
                'allocated_resources': self.allocated_resources,
                'resources_available': self.check_resources_available(),
                'thresholds': {
                    'cpu': self.cpu_threshold,
                    'memory': self.memory_threshold,
                    'gpu': self.gpu_threshold
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting resource status: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def set_thresholds(self, cpu_threshold: Optional[float] = None, 
                      memory_threshold: Optional[float] = None,
                      gpu_threshold: Optional[float] = None) -> Dict[str, Any]:
        """Set resource thresholds."""
        try:
            if cpu_threshold is not None:
                self.cpu_threshold = cpu_threshold
            if memory_threshold is not None:
                self.memory_threshold = memory_threshold
            if gpu_threshold is not None:
                self.gpu_threshold = gpu_threshold
            
            logger.info(f"Updated thresholds: CPU={self.cpu_threshold}%, Memory={self.memory_threshold}%, GPU={self.gpu_threshold}%")
            return {
                'status': 'success',
                'thresholds': {
                    'cpu': self.cpu_threshold,
                    'memory': self.memory_threshold,
                    'gpu': self.gpu_threshold
                }
            }
            
        except Exception as e:
            logger.error(f"Error setting thresholds: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action')
        
        if action == 'get_stats':
            return {
                'status': 'success',
                'stats': self.get_current_stats()
            }
        
        elif action == 'check_resources':
            return {
                'status': 'success',
                'available': self.check_resources_available()
            }
        
        elif action == 'allocate_resources':
            return self.allocate_resources(
                resource_id=request.get('resource_id'),
                resource_type=request.get('resource_type'),
                amount=request.get('amount', 1.0)
            )
        
        elif action == 'release_resources':
            return self.release_resources(
                resource_id=request.get('resource_id')
            )
        
        elif action == 'get_status':
            return self.get_resource_status()
        
        elif action == 'set_thresholds':
            return self.set_thresholds(
                cpu_threshold=request.get('cpu_threshold'),
                memory_threshold=request.get('memory_threshold'),
                gpu_threshold=request.get('gpu_threshold')
            )
        
        else:
            return {
                'status': 'error',
                'message': f'Unknown action: {action}'
            }
    
    def run(self):
        """Main loop to handle incoming requests."""
        logger.info("Starting ResourceManager main loop")
        
        while True:
            try:
                # Wait for request with timeout
                if self.socket.poll(1000) > 0:  # 1 second timeout
                    request = self.socket.recv_json()
                    response = self.handle_request(request)
                    self.socket.send_json(response)
                    
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                time.sleep(1)


    def _get_health_status(self) -> dict:

        """Return health status information."""

        base_status = super()._get_health_status()

        # Add any additional health information specific to ResourceManager

        base_status.update({

            'service': 'ResourceManager',

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
        """Gracefully shutdown the manager."""
        self.socket.close()
        self.health_socket.close()
        self.context.term()
        logger.info("ResourceManager shutdown complete")

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
        agent = ResourceManager()
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
