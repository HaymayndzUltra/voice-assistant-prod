"""
Agent Utilities - UPDATED for BaseAgent Integration
- Shared utilities for all agents
- ZMQ communication helpers
- Configuration management
- Logging utilities
- Error handling
- DEPRECATION WARNING: AgentBase is deprecated, use common.core.base_agent.BaseAgent instead
"""
import zmq
import json
import time
import logging
import sys
import os
import traceback
import warnings
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable
import threading
import uuid

# Import standardized BaseAgent
from common.core.base_agent import BaseAgent
from common.utils.path_manager import PathManager
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.logger_util import get_json_logger

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))

try:
    from pc2_code.config.system_config import config
except ImportError:
    # Fallback config if system_config is not available
    config = {'system': {'log_level': 'INFO', 'logs_dir': 'logs'}}

# Configure logging with standardized logger
logger = get_json_logger("AgentUtils")

class ZMQClient:
    """ZMQ client for agent communication"""
    def __init__(self, endpoint: str, socket_type: int = zmq.REQ, timeout: int = 5000):
        """Initialize ZMQ client"""
        self.context = zmq.Context()
        self.socket = self.context.socket(socket_type)
        self.socket.connect(endpoint)
        self.timeout = timeout
        self.endpoint = endpoint
        
        logger.info("ZMQ client connected", extra={
            "endpoint": endpoint,
            "socket_type": socket_type,
            "component": "zmq_client"
        })
    
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
                
                logger.info("Request processed successfully", extra={
                    "endpoint": self.endpoint,
                    "request_type": request.get("request_type", "unknown"),
                    "component": "zmq_client"
                })
                
                return response
            else:
                error_msg = f"Timeout waiting for response from {self.endpoint}"
                logger.error(error_msg, extra={
                    "endpoint": self.endpoint,
                    "timeout": self.timeout,
                    "component": "zmq_client"
                })
                return {"status": "error", "error": error_msg}
        
        except Exception as e:
            logger.error("Error sending request", extra={
                "endpoint": self.endpoint,
                "error": str(e),
                "component": "zmq_client"
            })
            return {"status": "error", "error": str(e)}
    
    def close(self):
        """Close the socket"""
        self.socket.close()
        logger.info("ZMQ client disconnected", extra={
            "endpoint": self.endpoint,
            "component": "zmq_client"
        })

class ZMQServer:
    """ZMQ server for agent communication"""
    def __init__(self, port: int, socket_type: int = zmq.REP):
        """Initialize ZMQ server"""
        self.context = zmq.Context()
        self.socket = self.context.socket(socket_type)
        self.socket.bind(f"tcp://*:{port}")
        self.port = port
        
        logger.info("ZMQ server started", extra={
            "port": port,
            "socket_type": socket_type,
            "component": "zmq_server"
        })
    
    def recv_request(self) -> Optional[Dict[str, Any]]:
        """Receive a request"""
        try:
            request_str = self.socket.recv_string()
            return json.loads(request_str)
        except Exception as e:
            logger.error("Error receiving request", extra={
                "error": str(e),
                "component": "zmq_server"
            })
            return None
    
    def send_response(self, response: Dict[str, Any]):
        """Send a response"""
        try:
            self.socket.send_string(json.dumps(response))
        except Exception as e:
            logger.error("Error sending response", extra={
                "error": str(e),
                "component": "zmq_server"
            })
    
    def close(self):
        """Close the server"""
        self.socket.close()
        logger.info("ZMQ server stopped", extra={
            "port": self.port,
            "component": "zmq_server"
        })

# DEPRECATED: Legacy AgentBase class - use common.core.base_agent.BaseAgent instead
class AgentBase:
    """
    DEPRECATED: Legacy base class for agents
    
    WARNING: This class is deprecated and will be removed in a future version.
    Please use common.core.base_agent.BaseAgent instead for new agent development.
    
    Migration guide:
    1. Import BaseAgent: from common.core.base_agent import BaseAgent
    2. Change inheritance: class MyAgent(BaseAgent)
    3. Update __init__ method to call super().__init__(name="MyAgent", ...)
    4. Remove custom health check implementations (BaseAgent provides this)
    5. Use BaseAgent.run() method for main execution
    """
    
    def __init__(self, agent_id: str, port: int, capabilities: List[str] = None):
        """
        Initialize legacy agent base (DEPRECATED)
        
        Args:
            agent_id: Unique identifier for the agent
            port: Port number for the agent to bind to
            capabilities: List of agent capabilities
        """
        # Issue deprecation warning
        warnings.warn(
            "AgentBase is deprecated. Use common.core.base_agent.BaseAgent instead. "
            "See class docstring for migration guide.",
            DeprecationWarning,
            stacklevel=2
        )
        
        logger.warning("Using deprecated AgentBase class", extra={
            "agent_id": agent_id,
            "port": port,
            "migration_guide": "Use common.core.base_agent.BaseAgent instead",
            "component": "deprecated_agent_base"
        })
        
        self.agent_id = agent_id
        self.port = port
        self.capabilities = capabilities or []
        
        # Setup ZMQ
        self.context = zmq.Context()
        
        # Socket to receive requests
        self.receiver = self.context.socket(zmq.REP)
        self.receiver.bind(f"tcp://0.0.0.0:{port}")
        logger.info(f"Legacy agent {agent_id} bound to port {port}")
        
        # Socket to communicate with autogen framework
        self.framework = self.context.socket(zmq.REQ)
        try:
            framework_port = config.get('zmq.autogen_framework_port', 5600)
            self.framework.connect(f"tcp://localhost:{framework_port}")
            logger.info(f"Connected to AutoGen Framework on port {framework_port}")
        except Exception as e:
            logger.error(f"Failed to connect to AutoGen Framework: {e}")
        
        # Running flag
        self.running = threading.Event()
        self.running.set()
        
        logger.info(f"Legacy agent {agent_id} initialized")
    
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
        
        logger.info(f"Legacy agent {self.agent_id} stopped")

# UPDATED: Standardized agent utilities for BaseAgent
def create_agent_logger(agent_name: str) -> logging.Logger:
    """
    Create a standardized JSON logger for an agent.
    
    This function is updated to use the standardized logging infrastructure.
    """
    return get_json_logger(agent_name)

def create_baseagent_instance(agent_class, name: str, port: int = None, **kwargs):
    """
    Helper function to create a BaseAgent instance with standard configuration.
    
    Args:
        agent_class: The agent class that inherits from BaseAgent
        name: Name of the agent
        port: Port for the agent (optional)
        **kwargs: Additional configuration parameters
        
    Returns:
        Configured agent instance
    """
    if not issubclass(agent_class, BaseAgent):
        raise ValueError(f"Agent class {agent_class} must inherit from BaseAgent")
    
    return agent_class(
        name=name,
        port=port,
        **kwargs
    )

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
        logger.error("Invalid JSON provided", extra={
            "json_str": json_str[:100] + "..." if len(json_str) > 100 else json_str,
            "component": "json_utils"
        })
        return {}

def safe_json_dumps(obj: Any) -> str:
    """Safely dump object to JSON string"""
    try:
        return json.dumps(obj)
    except Exception as e:
        logger.error("Error dumping to JSON", extra={
            "error": str(e),
            "object_type": type(obj).__name__,
            "component": "json_utils"
        })
        return "{}"

def get_agent_port(agent_name: str) -> int:
    """Get the port for an agent from config"""
    port_key = f"zmq.{agent_name.lower()}_port"
    return config.get(port_key, 5600)

def get_agent_endpoint(agent_name: str, host: str = "localhost") -> str:
    """Get the endpoint for an agent"""
    port = get_agent_port(agent_name)
    return f"tcp://{host}:{port}"

def is_port_in_use(port: int, host: str = "localhost") -> bool:
    """Check if a port is in use"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

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
        "python_version": platform.python_version(),
        "timestamp": time.time()
    }
    
    # Add psutil information if available
    try:
        import psutil
        
        info.update({
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "memory_percent": psutil.virtual_memory().percent,
        })
        
        # Add disk usage information
        disk_usage = {}
        for partition in psutil.disk_partitions():
            try:
                partition_usage = psutil.disk_usage(partition.mountpoint)
                disk_usage[partition.mountpoint] = {
                    "total": partition_usage.total,
                    "used": partition_usage.used,
                    "free": partition_usage.free,
                    "percent": (partition_usage.used / partition_usage.total) * 100
                }
            except PermissionError:
                # Skip partitions we can't access
                continue
        
        info["disk_usage"] = disk_usage
        
    except ImportError:
        logger.warning("psutil not available, system info will be limited")
    
    return info

# Migration helper functions
def migrate_legacy_agent_to_baseagent(legacy_agent_file: str, output_file: str = None):
    """
    Helper function to assist in migrating legacy agents to BaseAgent.
    
    Args:
        legacy_agent_file: Path to the legacy agent file
        output_file: Path for the migrated agent file (optional)
    """
    warnings.warn(
        "This migration helper is a placeholder. "
        "Please use the BaseAgent migration template for proper migration.",
        FutureWarning
    )
    
    logger.info("Legacy agent migration requested", extra={
        "legacy_file": legacy_agent_file,
        "output_file": output_file,
        "component": "migration_helper"
    })

if __name__ == "__main__":
    # This module is a utility library and should not be run directly
    print("Agent Utilities - Updated for BaseAgent Integration")
    print("=" * 50)
    print("This module provides utility functions for agents using BaseAgent.")
    print("")
    print("Key utilities:")
    print("- ZMQClient/ZMQServer: ZMQ communication helpers")
    print("- create_agent_logger(): Standardized logging")
    print("- create_baseagent_instance(): BaseAgent instance helper")
    print("- Various utility functions for agent development")
    print("")
    print("DEPRECATION WARNING:")
    print("- AgentBase class is deprecated")
    print("- Use common.core.base_agent.BaseAgent instead")
    print("")
    print("System Information:")
    system_info = get_system_info()
    for key, value in system_info.items():
        if key != "disk_usage":  # Skip complex nested data
            print(f"- {key}: {value}")
