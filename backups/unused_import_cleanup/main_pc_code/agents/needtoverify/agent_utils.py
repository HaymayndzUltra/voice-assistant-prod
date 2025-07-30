from common.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Agent Utilities
- Shared utilities for all agents
- ZMQ communication helpers
- Configuration management
- Logging utilities
- Error handling
"""
import zmq
import json
import time
import logging
import sys
import os
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable
import threading
import uuid

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))
from main_pc_code.config.system_config import config
from common.env_helpers import get_env

# Configure logging
log_level = config.get('system.log_level', 'INFO')
log_file = Path(config.get('system.logs_dir', 'logs')) / str(PathManager.get_logs_dir() / "agent_utils.log")
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AgentUtils")

class ZMQClient(BaseAgent):
    """ZMQ client for agent communication"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AgentUtils")
        """Initialize ZMQ client"""
        self.context = zmq.Context()
        self.socket = self.context.socket(socket_type)
        self.socket.connect(endpoint)
        self.timeout = timeout
        self.endpoint = endpoint
        
        logger.info(f"ZMQ client connected to {endpoint}")
    
    def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request and wait for response"""
        try:
            # Send request
            self.socket.send_string(json.dumps(request))
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(self.socket, zmq.POLLIN)
            
            if poller.poll(self.timeout):
                response_str = self.socket.recv_string()
                response = json.loads(response_str)
                return response
            else:
                logger.error(f"Timeout waiting for response from {self.endpoint}")
                return {"status": "error", "error": f"Timeout waiting for response from {self.endpoint}"}
        
        except Exception as e:
            logger.error(f"Error sending request to {self.endpoint}: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def close(self):
        """Close the socket"""
        self.socket.close()
        logger.info(f"ZMQ client disconnected from {self.endpoint}")

class ZMQServer(BaseAgent):
    """ZMQ server for agent communication"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AgentUtils")
        """Initialize ZMQ server"""
        self.context = zmq.Context()
        self.socket = self.context.socket(socket_type)
        self.socket.bind(f"tcp://127.0.0.1:{port}")
        self.port = port
        self.handler = handler
        self.running = threading.Event()
        self.running.set()
        
        logger.info(f"ZMQ server bound to port {port}")
    
    def start(self):
        """Start the server in a background thread"""
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info(f"ZMQ server started on port {self.port}")
    
    def _run(self):
        """Run the server loop"""
        while self.running.is_set():
            try:
                # Set timeout to allow checking running flag
                poller = zmq.Poller()
                poller.register(self.socket, zmq.POLLIN)
                
                if poller.poll(1000):  # 1 second timeout
                    # Receive request
                    request_str = self.socket.recv_string()
                    
                    try:
                        request = json.loads(request_str)
                        
                        # Handle request
                        if self.handler:
                            response = self.handler(request)
                        else:
                            response = {"status": "error", "error": "No handler registered"}
                    
                    except json.JSONDecodeError:
                        response = {"status": "error", "error": "Invalid JSON in request"}
                    except Exception as e:
                        logger.error(f"Error handling request: {str(e)}")
                        response = {"status": "error", "error": str(e)}
                    
                    # Send response
                    self.socket.send_string(json.dumps(response))
            
            except zmq.Again:
                # Timeout, continue loop
                pass
            except Exception as e:
                logger.error(f"Error in server loop: {str(e)}")
                traceback.print_exc()
    
    def stop(self):
        """Stop the server"""
        self.running.clear()
        
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=2)
        
        self.socket.close()
        logger.info(f"ZMQ server stopped on port {self.port}")

class ZMQPublisher(BaseAgent):
    """ZMQ publisher for broadcasting messages"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AgentUtils")
        """Initialize ZMQ publisher"""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind(f"tcp://127.0.0.1:{port}")
        self.port = port
        
        # Sleep briefly to allow subscribers to connect
        time.sleep(0.1)
        
        logger.info(f"ZMQ publisher bound to port {port}")
    
    def publish(self, topic: str, message: Dict[str, Any]):
        """Publish a message on a topic"""
        try:
            # Convert message to JSON
            message_str = json.dumps(message)
            
            # Publish message
            self.socket.send_string(f"{topic} {message_str}")
            
            logger.debug(f"Published message on topic {topic}")
        
        except Exception as e:
            logger.error(f"Error publishing message: {str(e)}")
    
    def close(self):
        """Close the socket"""
        self.socket.close()
        logger.info(f"ZMQ publisher closed on port {self.port}")

class ZMQSubscriber(BaseAgent):
    """ZMQ subscriber for receiving broadcast messages"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AgentUtils")
        """Initialize ZMQ subscriber"""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(endpoint)
        self.endpoint = endpoint
        self.handler = handler
        self.running = threading.Event()
        self.running.set()
        
        # Subscribe to topics
        if topics:
            for topic in topics:
                self.socket.setsockopt_string(zmq.SUBSCRIBE, topic)
        else:
            # Subscribe to all topics
            self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        logger.info(f"ZMQ subscriber connected to {endpoint}")
    
    def start(self):
        """Start the subscriber in a background thread"""
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info(f"ZMQ subscriber started for {self.endpoint}")
    
    def _run(self):
        """Run the subscriber loop"""
        while self.running.is_set():
            try:
                # Set timeout to allow checking running flag
                poller = zmq.Poller()
                poller.register(self.socket, zmq.POLLIN)
                
                if poller.poll(1000):  # 1 second timeout
                    # Receive message
                    message = self.socket.recv_string()
                    
                    try:
                        # Parse topic and message
                        parts = message.split(" ", 1)
                        
                        if len(parts) == 2:
                            topic, msg_str = parts
                            msg = json.loads(msg_str)
                            
                            # Handle message
                            if self.handler:
                                self.handler(topic, msg)
                        else:
                            logger.warning(f"Received malformed message: {message}")
                    
                    except json.JSONDecodeError:
                        logger.warning(f"Received invalid JSON: {message}")
                    except Exception as e:
                        logger.error(f"Error handling message: {str(e)}")
            
            except zmq.Again:
                # Timeout, continue loop
                pass
            except Exception as e:
                logger.error(f"Error in subscriber loop: {str(e)}")
                traceback.print_exc()
    
    def stop(self):
        """Stop the subscriber"""
        self.running.clear()
        
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=2)
        
        self.socket.close()
        logger.info(f"ZMQ subscriber stopped for {self.endpoint}")

class AgentBase(BaseAgent):
    """Base class for(BaseAgent) all agents"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AgentUtils")
        """Initialize agent base"""
        self.agent_id = agent_id
        self.port = port
        self.capabilities = capabilities or []
        
        # Setup ZMQ
        self.context = zmq.Context()
        
        # Socket to receive requests
        self.receiver = self.context.socket(zmq.REP)
        self.receiver.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.receiver.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.receiver.bind(f"tcp://127.0.0.1:{port}")
        logger.info(f"Agent {agent_id} bound to port {port}")
        
        # Socket to communicate with autogen framework
        self.framework = self.context.socket(zmq.REQ)
        self.framework.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.framework.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.framework.connect(f"tcp://localhost:{config.get('zmq.autogen_framework_port', 5600)}")
        logger.info(f"Connected to AutoGen Framework on port {config.get('zmq.autogen_framework_port', 5600)}")
        
        # Running flag
        self.running = threading.Event()
        self.running.set()
        
        logger.info(f"Agent {agent_id} initialized")
    
    def register_with_framework(self):
        """Register agent with the AutoGen framework"""
        try:
            # Register with AutoGen framework
            self.framework.send_string(json.dumps({
                "request_type": "register_agent",
                "agent_id": self.agent_id,
                "endpoint": f"tcp://localhost:{self.port}",
                "capabilities": self.capabilities
            }))
            
            # Wait for response
            response_str = self.framework.recv_string()
            response = json.loads(response_str)
            
            if response["status"] != "success":
                logger.error(f"Error registering with AutoGen framework: {response.get('error', 'Unknown error')}")
                return False
            else:
                logger.info(f"Agent {self.agent_id} registered with AutoGen framework")
                return True
        
        except Exception as e:
            logger.error(f"Error registering with AutoGen framework: {str(e)}")
            return False
    
    def unregister_from_framework(self):
        """Unregister agent from the AutoGen framework"""
        try:
            # Unregister from AutoGen framework
            self.framework.send_string(json.dumps({
                "request_type": "unregister_agent",
                "agent_id": self.agent_id
            }))
            
            # Wait for response
            response_str = self.framework.recv_string()
            response = json.loads(response_str)
            
            if response["status"] != "success":
                logger.error(f"Error unregistering from AutoGen framework: {response.get('error', 'Unknown error')}")
                return False
            else:
                logger.info(f"Agent {self.agent_id} unregistered from AutoGen framework")
                return True
        
        except Exception as e:
            logger.error(f"Error unregistering from AutoGen framework: {str(e)}")
            return False
    
    def handle_requests(self):
        """Main loop to handle incoming requests"""
        logger.info(f"Agent {self.agent_id} starting request handler")
        
        while self.running.is_set():
            try:
                # Set timeout to allow checking running flag
                poller = zmq.Poller()
                poller.register(self.receiver, zmq.POLLIN)
                
                if poller.poll(1000):  # 1 second timeout
                    # Receive request
                    request_str = self.receiver.recv_string()
                    
                    try:
                        request = json.loads(request_str)
                        request_type = request.get("request_type")
                        
                        logger.info(f"Agent {self.agent_id} received request: {request_type}")
                        
                        # Handle request
                        response = self.process_request(request)
                    
                    except json.JSONDecodeError:
                        response = {"status": "error", "error": "Invalid JSON in request"}
                    except Exception as e:
                        logger.error(f"Error processing request: {str(e)}")
                        response = {"status": "error", "error": str(e)}
                    
                    # Send response
                    self.receiver.send_string(json.dumps(response))
            
            except zmq.Again:
                # Timeout, continue loop
                pass
            except Exception as e:
                logger.error(f"Error in request handler: {str(e)}")
                traceback.print_exc()
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request (to be implemented by subclasses)"""
        raise NotImplementedError("Subclasses must implement process_request")
    
    def run(self):
        """Run the agent"""
        try:
            # Register with AutoGen framework
            self.register_with_framework()
            
            # Main request handling loop
            self.handle_requests()
                
        except KeyboardInterrupt:
            logger.info(f"Agent {self.agent_id} interrupted by user")
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            traceback.print_exc()
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.running.clear()
        
        # Unregister from AutoGen framework
        self.unregister_from_framework()
        
        self.receiver.close()
        self.framework.close()
        self.context.term()
        
        logger.info(f"Agent {self.agent_id} stopped")

def create_agent_logger(agent_name: str) -> logging.Logger:
    """Create a logger for an agent"""
    log_file = Path(config.get('system.logs_dir', 'logs')) / fstr(PathManager.get_logs_dir() / "{agent_name.lower()}.log")
    log_file.parent.mkdir(exist_ok=True)
    
    logger = logging.getLogger(agent_name)
    logger.setLevel(getattr(logging, log_level))
    
    # Add file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)
    
    return logger

def generate_unique_id() -> str:
    """Generate a unique ID"""
    return uuid.uuid4().hex

def format_exception(e: Exception) -> str:
    """Format an exception for logging"""
    return f"{type(e).__name__}: {str(e)}"

def safe_json_loads(json_str: str) -> Dict[str, Any]:
    """Safely load JSON string"""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON: {json_str}")
        return {}

def safe_json_dumps(obj: Any) -> str:
    """Safely dump object to JSON string"""
    try:
        return json.dumps(obj)
    except Exception as e:
        logger.error(f"Error dumping to JSON: {str(e)}")
        return "{}"

def get_agent_port(agent_name: str) -> int:
    """Get the port for an agent from config"""
    port_key = f"zmq.{agent_name.lower()}_port"
    return config.get(port_key, 5600)

def get_agent_endpoint(agent_name: str) -> str:
    """Get the endpoint for an agent"""
    port = get_agent_port(agent_name)
    return f"tcp://localhost:{port}"

def is_port_in_use(port: int) -> bool:
    """Check if a port is in use"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_available_port(start_port: int = 5600, max_attempts: int = 100) -> int:
    """Find an available port starting from start_port"""
    port = start_port
    attempts = 0
    
    while attempts < max_attempts:
        if not is_port_in_use(port):
            return port
        
        port += 1
        attempts += 1
    
    raise RuntimeError(f"Could not find an available port after {max_attempts} attempts")

def get_system_info() -> Dict[str, Any]:
    """Get system information"""
    import platform
    
    info = {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version()
    }
    
    # Add psutil information if available
    try:
        import psutil

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager
    except ImportError as e:
        print(f"Import error: {e}")

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
        
        info.update({
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": {str(part.mountpoint): {
                "total": part.total,
                "used": part.used,
                "free": part.free,
                "percent": part.percent
            } for part in psutil.disk_partitions() if part.fstype}
        })
    except ImportError:
        pass
    
    return info

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise