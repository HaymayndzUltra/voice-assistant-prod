from main_pc_code.src.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Model Manager Agent GGUF Connector
---------------------------------
Handles communication between Model Manager Agent and Code Generator Agent for GGUF model operations
"""
import zmq
import json
import logging
import time
import threading
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(PathManager.join_path("main_pc_code", ".."))))
from common.utils.path_manager import PathManager
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PathManager.join_path("logs", str(PathManager.get_logs_dir() / "mma_gguf_connector.log"))),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MMA_GGUF_Connector")

class GGUFConnector(BaseAgent):
    """Connector for handling GGUF model operations between MMA and CGA"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ModelManagerAgentGgufConnector")
        """Initialize the GGUF connector
        
        Args:
            cga_port: Port number for the Code Generator Agent. If None, load from config.
        """
        # Load port from config if not provided
        if cga_port is None:
            try:
                # Add parent directory to path to import config
                sys.path.append(str(Path(__file__).parent.parent))
from main_pc_code.config.system_config import Config
import psutil
from datetime import datetime
from common.env_helpers import get_env
                config = Config()
                cga_port = config.get('zmq.code_generator_port', 5604)
                logger.info(f"Loaded code_generator_port={cga_port} from config")
            except Exception as e:
                logger.warning(f"Failed to load code_generator_port from config: {e}")
                cga_port = 5604  # Default to 5604 as per config.json
                logger.info(f"Using default code_generator_port={cga_port}")
        
        self.cga_port = cga_port
        self.context = zmq.Context()
        self.socket = None
        self.connected = False
        self.request_timeout = 30000  # 30 seconds timeout for requests
        
        # Connect to the Code Generator Agent
        self._connect()
    
    def _connect(self) -> bool:
        """Connect to the Code Generator Agent
        
        Returns:
            bool: True if connected successfully, False otherwise
        """
        if self.connected and self.socket is not None:
            return True
            
        try:
            # Create socket if it doesn't exist
            if self.socket is None:
                self.socket = self.context.socket(zmq.REQ)
                self.socket.setsockopt(zmq.LINGER, 0)
                self.socket.setsockopt(zmq.RCVTIMEO, self.request_timeout)
                self.socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5 second send timeout
            
            # Connect to the CGA
            connection_url = f"tcp://localhost:{self.cga_port}"
            logger.info(f"Attempting to connect to Code Generator Agent at {connection_url}")
            self.socket.connect(connection_url)
            
            # Test connection with ping
            ping_request = {"action": "ping", "request_id": f"ping_{int(time.time())}"}
            logger.debug(f"Sending ping request: {ping_request}")
            self.socket.send_string(json.dumps(ping_request))
            
            # Wait for response with timeout
            response_str = self.socket.recv_string()
            logger.debug(f"Received ping response: {response_str}")
            response = json.loads(response_str)
            
            if response.get("status") in ["ok", "success"]:
                logger.info(f"Connected to Code Generator Agent on port {self.cga_port}")
                self.connected = True
                return True
            else:
                logger.error(f"Failed to connect to Code Generator Agent: {response}")
                self.connected = False
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to Code Generator Agent: {e}")
            self.connected = False
            
            # Cleanup socket on error
            if self.socket is not None:
                self.socket.close()
                self.socket = None
                
            return False
    
    def send_request(self, request: Dict[str, Any], retry_count: int = 2) -> Dict[str, Any]:
        """Send a request to the Code Generator Agent with automatic reconnection
        
        Args:
            request: The request to send
            retry_count: Number of retries if connection fails
            
        Returns:
            Response from the Code Generator Agent
        """
        # Ensure request has a request_id
        if 'request_id' not in request:
            request['request_id'] = f"req_{int(time.time())}"
            
        # Try to connect if not already connected
        if not self.connected:
            if not self._connect():
                return {"status": "error", "error": "Not connected to Code Generator Agent"}
        
        for attempt in range(retry_count + 1):
            try:
                # Log the request
                logger.debug(f"Sending request (attempt {attempt+1}/{retry_count+1}): {request}")
                
                # Send the request
                self.socket.send_string(json.dumps(request))
                
                # Get the response with timeout
                response_str = self.socket.recv_string()
                response = json.loads(response_str)
                
                # Log success
                logger.debug(f"Received response: {response}")
                return response
                    
            except zmq.error.Again as e:
                logger.warning(f"Timeout sending request to Code Generator Agent (attempt {attempt+1}/{retry_count+1}): {e}")
                # Only retry if not the last attempt
                if attempt < retry_count:
                    logger.info(f"Reconnecting and retrying...")
                    # Force reconnection
                    self.connected = False
                    if self.socket is not None:
                        self.socket.close()
                        self.socket = None
                    if not self._connect():
                        return {"status": "error", "error": "Failed to reconnect to Code Generator Agent"}
                else:
                    return {"status": "error", "error": "Request timed out after all retry attempts"}
            except Exception as e:
                logger.error(f"Error sending request to Code Generator Agent: {e}")
                self.connected = False
                
                # Cleanup socket on error
                if self.socket is not None:
                    self.socket.close()
                    self.socket = None
                    
                # Only retry if not the last attempt
                if attempt < retry_count:
                    logger.info(f"Reconnecting and retrying after error...")
                    if not self._connect():
                        return {"status": "error", "error": f"Failed to reconnect after error: {e}"}
                else:
                    return {"status": "error", "error": str(e)}
    
    def load_gguf_model(self, model_id: str) -> Dict[str, Any]:
        """Load a GGUF model
        
        Args:
            model_id: ID of the model to load
            
        Returns:
            Response from the Code Generator Agent
        """
        request = {
            "action": "load_gguf_model",
            "model_id": model_id,
            "timestamp": time.time(),
            "request_id": f"load_{int(time.time())}"
        }
        return self.send_request(request)
    
    def unload_gguf_model(self, model_id: str) -> Dict[str, Any]:
        """Unload a GGUF model
        
        Args:
            model_id: ID of the model to unload
            
        Returns:
            Response from the Code Generator Agent
        """
        request = {
            "action": "unload_gguf_model",
            "model_id": model_id,
            "timestamp": time.time(),
            "request_id": f"unload_{int(time.time())}"
        }
        return self.send_request(request)
    
    def generate_code(self, model_id: str, prompt: str, system_prompt: Optional[str] = None,
                     max_tokens: int = 1024, temperature: float = 0.7) -> Dict[str, Any]:
        """Generate code using a GGUF model
        
        Args:
            model_id: ID of the model to use
            prompt: The prompt to generate code from
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for sampling
            
        Returns:
            Response from the Code Generator Agent
        """
        request = {
            "action": "generate_with_gguf",
            "model_id": model_id,
            "prompt": prompt,
            "system_prompt": system_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "timestamp": time.time(),
            "request_id": f"generate_{int(time.time())}"
        }
        return self.send_request(request)
    
    def get_gguf_status(self) -> Dict[str, Any]:
        """Get status of all GGUF models
        
        Returns:
            Response from the Code Generator Agent
        """
        request = {
            "action": "get_gguf_status",
            "timestamp": time.time(),
            "request_id": f"status_{int(time.time())}"
        }
        return self.send_request(request)
    
    def list_gguf_models(self) -> Dict[str, Any]:
        """List all available GGUF models
        
        Returns:
            Response from the Code Generator Agent
        """
        request = {
            "action": "list_gguf_models",
            "timestamp": time.time(),
            "request_id": f"list_{int(time.time())}"
        }
        return self.send_request(request)
    
    def close(self):
        """Close the connection to the Code Generator Agent"""
        if self.socket is not None:
            self.socket.close()
            self.socket = None
        self.connected = False


    def health_check(self):
        '''
        Performs a health check on the agent, returning a dictionary with its status.
        '''
        try:
            # Basic health check logic
            is_healthy = True # Assume healthy unless a check fails
            
            # TODO: Add agent-specific health checks here.
            # For example, check if a required connection is alive.
            # if not self.some_service_connection.is_alive():
            #     is_healthy = False

            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else -1,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {} # Placeholder for agent-specific data
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            return {
                "status": "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "error": f"Health check failed with exception: {str(e)}"
            }

# Singleton instance
_instance = None

def get_instance(cga_port: Optional[int] = None) -> GGUFConnector:
    """Get the singleton instance of the GGUF connector
    
    Args:
        cga_port: Port number for the Code Generator Agent. If None, load from config.
        
    Returns:
        The GGUF connector instance
    """
    global _instance
    if _instance is None:
        _instance = GGUFConnector(cga_port)
    return _instance

# Test code
if __name__ == "__main__":
    connector = get_instance()
    
    # Test connection
    print("Testing connection to Code Generator Agent...")
    
    # Get GGUF status
    status = connector.get_gguf_status()
    print(f"GGUF status: {json.dumps(status, indent=2)}")
    
    # List GGUF models
    models = connector.list_gguf_models()
    print(f"GGUF models: {json.dumps(models, indent=2)}")
    
    # Close connection
    connector.close()
    print("Connection closed")

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise