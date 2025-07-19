from common.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = get_main_pc_code()
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

Remote Connector / API Client Agent
- Handles API requests to remote/local models
- Provides a unified interface for all AI models
- Supports both synchronous and asynchronous requests
- Uses centralized configuration system
- Implements response caching for improved performance
"""
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import json
import time
import logging
import threading
import requests
import sys
import os
import traceback
from pathlib import Path
from datetime import datetime, timedelta
import hashlib

# Add the parent directory to sys.path to import the config module
from main_pc_code.config.system_config import config
import psutil
from datetime import datetime
from common.env_helpers import get_env

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Configure logging
log_level = config.get('system.log_level', 'INFO')
log_file = Path(config.get('system.logs_dir', 'logs')) / "remote_connector.log"
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RemoteConnector")

# Get ZMQ ports from config
REMOTE_CONNECTOR_PORT = config.get('zmq.remote_connector_port', 5557)
TASK_ROUTER_PORT = config.get('zmq.task_router_port', 8570)  # Updated to connect to Task Router instead of Model Manager
TASK_ROUTER_PUB_PORT = TASK_ROUTER_PORT + 10  # Publisher port is base + 10

class RemoteConnectorAgent(BaseAgent):
    """
    RemoteConnectorAgent: Handles remote model/API connections. Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').
    """
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="RemoteConnectorAgent")
        # Initialize ZMQ
        self.context = None  # Using pool
        
        # Socket to receive requests
        self.receiver = self.context.socket(zmq.REP)
        self.receiver.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.receiver.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        # Determine bind host from configuration or environment variable
        bind_host = config.get('network.bind_address', os.environ.get('BIND_ADDRESS', '0.0.0.0'))
        self.receiver.bind(f"tcp://{bind_host}:{REMOTE_CONNECTOR_PORT}")
        logger.info(f"Remote Connector bound to port {REMOTE_CONNECTOR_PORT}")
        
        # Socket to communicate with task router (previously model manager)
        self.task_router = self.context.socket(zmq.REQ)
        self.task_router.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.task_router.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        task_router_port = config.get('zmq.task_router_port', 8570)
        # Determine task-router host (typically the same container or docker-compose service name)
        task_router_host = config.get('network.task_router_host', os.environ.get('TASK_ROUTER_HOST', 'localhost'))
        self.task_router.connect(f"tcp://{task_router_host}:{task_router_port}")
        logger.info(f"Connected to Task Router on port {task_router_port}")
        
        # Socket to subscribe to model status updates
        self.model_status = self.context.socket(zmq.SUB)
        model_status_port = task_router_port + 10  # Publisher port is base + 10
        # Use the same resolved host for the publisher connection
        self.model_status.connect(f"tcp://{task_router_host}:{model_status_port}")
        self.model_status.setsockopt_string(zmq.SUBSCRIBE, "")
        logger.info(f"Subscribed to Task Router status updates on port {model_status_port}")
        
        # Setup response cache
        self.cache_enabled = config.get('models.cache_enabled', True)
        self.cache_dir = Path(config.get('system.cache_dir', 'cache')) / "model_responses"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = config.get('models.cache_ttl', 3600)  # Cache TTL in seconds (default: 1 hour)
        
        # Cache for model status
        self.model_cache = {}
        
        # Thread for handling model status updates
        self.status_thread = None
        
        # Running flag
        self.running = True
        
        logger.info("Remote Connector Agent initialized")
        
        self.error_bus_port = 7150
        self.error_bus_host = get_service_ip("pc2")
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.connect(self.error_bus_endpoint)
    
    def _calculate_cache_key(self, model, prompt, system_prompt=None, temperature=0.7):
        """Calculate a unique cache key for a request"""
        # Create a string representation of the request
        request_str = f"{model}:{prompt}:{system_prompt}:{temperature}"
        # Create a hash of the request
        return hashlib.md5(request_str.encode()).hexdigest()
    
    def _check_cache(self, cache_key):
        """Check if a response is cached and still valid"""
        if not self.cache_enabled:
            return None
            
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                
                # Check if cache is still valid
                timestamp = datetime.fromisoformat(cached_data['timestamp'])
                if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                    logger.info(f"Cache hit for key {cache_key[:8]}...")
                    return cached_data['response']
            except Exception as e:
                logger.warning(f"Error reading cache: {e}")
        
        return None
    
    def _save_to_cache(self, cache_key, response):
        """Save a response to the cache"""
        if not self.cache_enabled:
            return
            
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'response': response
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
            logger.info(f"Saved response to cache with key {cache_key[:8]}...")
        except Exception as e:
            logger.warning(f"Error saving to cache: {e}")
    
    def send_to_ollama(self, model, prompt, system_prompt=None, temperature=0.7):
        """Send a request to an Ollama model with caching"""
        # Check cache first if enabled
        cache_key = self._calculate_cache_key(model, prompt, system_prompt, temperature)
        cached_response = self._check_cache(cache_key)
        if cached_response:
            return {
                "status": "success",
                "model": model,
                "response": cached_response,
                "cached": True
            }
        
        # Not in cache, make the actual request
        ollama_url = config.get('models.ollama.url', 'http://localhost:11434')
        url = f"{ollama_url}/api/generate"
        
        # Prepare request data
        data = {
            "model": model, 
            "prompt": prompt, 
            "stream": False,
            "temperature": temperature
        }
        
        # Add system prompt if provided
        if system_prompt:
            data["system"] = system_prompt
        
        try:
            logger.info(f"Sending request to Ollama model '{model}'")
            response = requests.post(url, json=data, timeout=120)
            response.raise_for_status()
            result = response.json().get("response", response.text)
            logger.info(f"Received response from Ollama model '{model}' ({len(result)} chars)")
            
            # Save to cache
            self._save_to_cache(cache_key, result)
            
            return {
                "status": "success",
                "model": model,
                "response": result,
                "cached": False
            }
        except Exception as e:
            error_msg = f"Error contacting Ollama model '{model}': {str(e)}"
            logger.error(error_msg)
            self.report_error("OllamaConnectionError", error_msg)
            return {
                "status": "error",
                "model": model,
                "error": error_msg
            }

    def send_to_deepseek(self, prompt, temperature=0.7, max_tokens=2048):
        """Send a request to Deepseek Coder with caching"""
        # Check cache first if enabled
        cache_key = self._calculate_cache_key("deepseek", prompt, None, temperature)
        cached_response = self._check_cache(cache_key)
        if cached_response:
            return {
                "status": "success",
                "model": "deepseek",
                "response": cached_response,
                "cached": True
            }
        
        # Not in cache, make the actual request
        deepseek_url = config.get('models.deepseek.url', 'http://192.168.1.100:8000')
        url = f"{deepseek_url}/generate"
        
        # Prepare request data
        data = {
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            logger.info("Sending request to Deepseek Coder")
            response = requests.post(url, json=data, timeout=120)
            response.raise_for_status()
            result = response.json().get("text", response.text)
            logger.info(f"Received response from Deepseek Coder ({len(result)} chars)")
            
            # Save to cache
            self._save_to_cache(cache_key, result)
            
            return {
                "status": "success",
                "model": "deepseek",
                "response": result,
                "cached": False
            }
        except Exception as e:
            error_msg = f"Error contacting Deepseek Coder: {str(e)}"
            logger.error(error_msg)
            self.report_error("DeepseekConnectionError", error_msg)
            return {
                "status": "error",
                "model": "deepseek",
                "error": error_msg
            }
            
    def check_model_status(self, model_name):
        """Check if a model is available"""
        # First check the cache
        if model_name in self.model_cache:
            return self.model_cache[model_name].get("status") == "online"
        
        # If not in cache, ask the task router
        try:
            request = {
                "request": "status",
                "model": model_name
            }
            
            self.task_router.send_string(json.dumps(request))
            
            # Wait for response with timeout
            if self.task_router.poll(5000) == 0:
                logger.error(f"Timeout waiting for model status: {model_name}")
                return False
            
            response = self.task_router.recv_string()
            response_data = json.loads(response)
            
            if response_data.get("status") == "success":
                model_info = response_data.get("info", {})
                self.model_cache[model_name] = model_info
                return model_info.get("status") == "online"
            
            return False
        except Exception as e:
            logger.error(f"Error checking model status: {str(e)}")
            return False
    
    def handle_model_status_updates(self):
        """Thread function to handle model status updates"""
        logger.info("Started model status update thread")
        
        while self.running:
            try:
                # Use poll to avoid blocking indefinitely
                if self.model_status.poll(timeout=1000) == 0:
                    continue
                
                # Receive update
                message = self.model_status.recv_string()
                update = json.loads(message)
                
                event_type = update.get("event")
                if event_type == "model_status_update":
                    models = update.get("models", {})
                    
                    # Update cache
                    for model_name, model_info in models.items():
                        self.model_cache[model_name] = model_info
                        status = model_info.get("status")
                        logger.info(f"Model status update: {model_name} is {status}")
            
            except zmq.Again:
                # Timeout, continue loop
                pass
            except Exception as e:
                logger.error(f"Error in model status thread: {str(e)}")
                traceback.print_exc()
    
    def handle_requests(self):
        """Main loop to handle incoming requests"""
        logger.info("Started request handler loop")
        
        while self.running:
            try:
                # Use poll to avoid blocking indefinitely
                if self.receiver.poll(timeout=1000) == 0:
                    continue
                
                # Receive request
                message = self.receiver.recv_string()
                try:
                    request = json.loads(message)
                    request_type = request.get("request_type")
                    
                    if request_type == "generate":
                        # Handle text generation request
                        model = request.get("model")
                        prompt = request.get("prompt")
                        system_prompt = request.get("system_prompt")
                        temperature = request.get("temperature", 0.7)
                        
                        if not model or not prompt:
                            response = {
                                "status": "error",
                                "error": "Missing required parameters: model and prompt"
                            }
                        else:
                            # Route to appropriate model
                            if model.startswith("llama") or model.startswith("phi"):
                                response = self.send_to_ollama(model, prompt, system_prompt, temperature)
                            elif model == "deepseek":
                                response = self.send_to_deepseek(prompt, temperature)
                            else:
                                response = {
                                    "status": "error",
                                    "error": f"Unknown model: {model}"
                                }
                    
                    elif request_type == "check_status":
                        # Handle status check request
                        model = request.get("model")
                        
                        if not model:
                            response = {
                                "status": "error",
                                "error": "Missing required parameter: model"
                            }
                        else:
                            is_available = self.check_model_status(model)
                            response = {
                                "status": "success",
                                "model": model,
                                "available": is_available
                            }
                    
                    else:
                        response = {
                            "status": "error",
                            "error": f"Unknown request type: {request_type}"
                        }
                
                except json.JSONDecodeError:
                    response = {
                        "status": "error",
                        "error": "Invalid JSON in request"
                    }
                except Exception as e:
                    response = {
                        "status": "error",
                        "error": f"Error processing request: {str(e)}"
                    }
                
                # Send response
                self.receiver.send_string(json.dumps(response))
                
            except zmq.Again:
                # Timeout, continue loop
                pass
            except Exception as e:
                logger.error(f"Error in request handler: {str(e)}")
                traceback.print_exc()
    
    def run(self):
        """Run the remote connector agent"""
        try:
            # Start model status thread
            self.status_thread = threading.Thread(target=self.handle_model_status_updates)
            self.status_thread.daemon = True
            self.status_thread.start()
            
            # Main request handling loop
            self.handle_requests()
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            traceback.print_exc()
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        
        if self.status_thread and self.status_thread.is_alive():
            self.status_thread.join(timeout=2)
        
        self.receiver.close()
        self.task_router.close()
        self.model_status.close()
        self.
        logger.info("Remote Connector Agent stopped")

    def report_error(self, error_type, message, severity="ERROR", context=None):
        error_data = {
            "error_type": error_type,
            "message": message,
            "severity": severity,
            "context": context or {}
        }
        try:
            msg = json.dumps(error_data).encode('utf-8')
            self.error_bus_pub.send_multipart([b"ERROR:", msg])
        except Exception as e:
            print(f"Failed to publish error to Error Bus: {e}")

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

# Main entry point
if __name__ == "__main__":
    try:
        logger.info("Starting Remote Connector Agent...")
        agent = RemoteConnectorAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Remote Connector Agent interrupted by user")
    except Exception as e:
        logger.error(f"Error running Remote Connector Agent: {str(e)}")
        traceback.print_exc()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise