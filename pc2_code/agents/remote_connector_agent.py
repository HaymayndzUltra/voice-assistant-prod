"""
Remote Connector / API Client Agent
- Handles API requests to remote/local models
- Provides a unified interface for all AI models
- Supports both synchronous and asynchronous requests
- Uses centralized configuration system
- Implements response caching for improved performance
"""
import zmq
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
import yaml # Added explicitly for network_config loading
from typing import Dict, Any, Optional, Union, List # Combined and ordered imports

# Add project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import base agent and config loaders
from common.core.base_agent import BaseAgent
from pc2_code.agents.utils.config_loader import Config

# Load PC2 specific configuration system
# Removed 'from pc2_code.config.system_config import config' to avoid potential conflicts
# and rely on the Config().get_config() pattern used elsewhere in the project.
app_config = Config().get_config() # Renamed to avoid conflict with global variables

# Import common utilities if available (not used in provided snippet, but keeping structure)
try:
    # Assuming this module exists and provides `create_socket`
    # from common_utils.zmq_helper import create_socket # This was not used, commenting out
    USE_COMMON_UTILS = True
except ImportError as e:
    print(f"Import error: {e}. Some common utilities might not be available.")
    USE_COMMON_UTILS = False

# Load network configuration
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = os.path.join(project_root, "config", "network_config.yaml") # Use project_root
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
            "secure_zmq": False,
            "ports": {} # Ensure ports key exists for .get("ports", {})
        }

network_config = load_network_config()

# Get machine IPs from network config
MAIN_PC_IP = network_config.get("main_pc_ip", "192.168.100.16")
PC2_IP = network_config.get("pc2_ip", "192.168.100.17")
BIND_ADDRESS = network_config.get("bind_address", "0.0.0.0")

# Configure logging
log_level = app_config.get('system.log_level', 'INFO')
log_file_path = Path(app_config.get('system.logs_dir', 'logs')) / "remote_connector.log"
log_file_path.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RemoteConnector")

# Get ZMQ ports from app_config (formerly 'config')
REMOTE_CONNECTOR_PORT = app_config.get('zmq.remote_connector_port', 5557)
MODEL_MANAGER_PORT = app_config.get('zmq.model_manager_port', 5556)  # Base port for MMA
MODEL_MANAGER_HOST = app_config.get('zmq.model_manager_host', '192.168.100.16')  # Main PC's IP address
TASK_ROUTER_PORT = app_config.get('zmq.task_router_port', 5558) # Unused in this snippet

class RemoteConnectorAgent(BaseAgent):
    def __init__(self, port: int = None):
        # Initialize BaseAgent first
        super().__init__(name="RemoteConnectorAgent", port=port if port else REMOTE_CONNECTOR_PORT)

        logger.info("=" * 80)
        logger.info("Initializing Remote Connector Agent")
        logger.info("=" * 80)

        # Use self.port from BaseAgent if no explicit port was given
        self.port = self.port if self.port else REMOTE_CONNECTOR_PORT
        # Health check port is agent port + 1
        self.health_port = self.port + 1

        # Initialize ZMQ Context
        self.context = zmq.Context()

        # Socket to receive requests (main REP socket)
        self.receiver = self.context.socket(zmq.REP)
        self.receiver.bind(f"tcp://0.0.0.0:{self.port}") # Use self.port
        logger.info(f"Remote Connector bound to port {self.port}")

        # Health check socket (separate from main receiver)
        self.health_socket = self.context.socket(zmq.REP)
        self.health_socket.bind(f"tcp://0.0.0.0:{self.health_port}") # Use self.health_port
        logger.info(f"Remote Connector health check bound to port {self.health_port}")

        # Socket to communicate with model manager
        self.model_manager = self.context.socket(zmq.REQ)
        self.model_manager_port = app_config.get('zmq.model_manager_port', 5555) # Use app_config
        self.model_manager_connected = False
        try:
            self.model_manager.connect(f"tcp://{MODEL_MANAGER_HOST}:{self.model_manager_port}")
            self.model_manager.setsockopt(zmq.RCVTIMEO, 500)  # 500ms timeout
            self.model_manager_connected = True
            logger.info(f"Connected to Model Manager on {MODEL_MANAGER_HOST}:{self.model_manager_port}")
        except Exception as e:
            logger.warning(f"Could not connect to Model Manager: {e}. Will operate in standalone mode.")

        # Socket to subscribe to model status updates
        self.model_status = self.context.socket(zmq.SUB)
        # Publisher port is typically base + 1, so if MMA is 5555, publisher might be 5556
        # Or it could be explicitly defined in config as 'model_status_pub_port'
        self.model_status_port = app_config.get('zmq.model_status_pub_port', self.model_manager_port + 1) # Use app_config
        try:
            self.model_status.connect(f"tcp://{MODEL_MANAGER_HOST}:{self.model_status_port}")
            self.model_status.setsockopt_string(zmq.SUBSCRIBE, "")
            self.model_status.setsockopt(zmq.RCVTIMEO, 500)  # 500ms timeout
            logger.info(f"Subscribed to Model Manager status updates on {MODEL_MANAGER_HOST}:{self.model_status_port}")
        except Exception as e:
            logger.warning(f"Could not connect to Model Manager status updates: {e}. Will operate without live model status.")

        # Set all models as available in standalone mode
        self.standalone_mode = not self.model_manager_connected

        # Setup response cache
        self.cache_enabled = app_config.get('models.cache_enabled', True) # Use app_config
        self.cache_dir = Path(app_config.get('system.cache_dir', 'cache')) / "model_responses" # Use app_config
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = app_config.get('models.cache_ttl', 3600)  # Cache TTL in seconds (default: 1 hour), use app_config

        # Cache for model status
        self.model_cache = {}

        # Threads
        self.status_thread = None # Thread for handling model status updates
        self.health_thread = None # Thread for handling health check requests

        # Running flag inherited from BaseAgent: self.running = True
        # Start time for uptime tracking inherited from BaseAgent: self.start_time = time.time()

        # Track statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0

        logger.info("Remote Connector Agent initialized")
        logger.info(f"Cache enabled: {self.cache_enabled}")
        logger.info(f"Cache TTL: {self.cache_ttl} seconds")
        logger.info(f"Standalone mode: {self.standalone_mode}")
        logger.info("=" * 80)

    def _start_health_check_thread(self):
        """Start health check thread."""
        self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True) # Set as daemon
        self.health_thread.start()
        logger.info("Health check thread started")

    def _health_check_loop(self):
        """Background loop to handle health check requests."""
        logger.info("Health check loop started")

        while self.running: # Use self.running from BaseAgent
            try:
                # Poll for health check requests with timeout
                if self.health_socket.poll(100) == 0: # 100ms timeout, using zmq.POLLIN is implicit
                    continue

                # Receive request (don't care about content)
                _ = self.health_socket.recv()

                # Get health data (calls the overridden _get_health_status)
                health_data = self._get_health_status()

                # Send response
                self.health_socket.send_json(health_data)

                time.sleep(0.01) # Very small sleep to prevent CPU hogging in fast loop

            except Exception as e:
                logger.error(f"Error in health check loop: {e}", exc_info=True)
                time.sleep(1)  # Sleep longer on error

    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent. Overrides BaseAgent's method."""
        base_status = super()._get_health_status() # Get base status from parent

        # Add RemoteConnectorAgent specific health info
        base_status.update({
            "agent": self.name,
            "status": "ok", # Overall status, refine if specific checks fail
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": time.time() - self.start_time,
            "metrics": {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "cache_enabled": self.cache_enabled,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "cache_hit_ratio": (self.cache_hits / (self.cache_hits + self.cache_misses) * 100) if (self.cache_hits + self.cache_misses) > 0 else 0,
                "model_manager_connected": self.model_manager_connected,
                "standalone_mode": self.standalone_mode,
                "status_thread_alive": self.status_thread.is_alive() if self.status_thread else False,
                "health_thread_alive": self.health_thread.is_alive() if self.health_thread else False,
            }
        })
        return base_status

    def _calculate_cache_key(self, model: str, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.7) -> str:
        """Calculate a unique cache key for a request"""
        # Create a string representation of the request
        request_str = f"{model}:{prompt}:{system_prompt if system_prompt else ''}:{temperature}" # Handle None system_prompt
        # Create a hash of the request
        return hashlib.md5(request_str.encode('utf-8')).hexdigest() # Encode to utf-8

    def _check_cache(self, cache_key: str) -> Optional[str]:
        """Check if a response is in the cache and not expired"""
        if not self.cache_enabled:
            return None

        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            self.cache_misses += 1
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f: # Specify encoding
                cached_data = json.load(f)

            # Check if cache entry is expired
            if time.time() - cached_data.get('timestamp', 0) > self.cache_ttl:
                logger.debug(f"Cache expired for key: {cache_key}")
                self.cache_misses += 1
                os.remove(cache_file) # Optionally remove expired cache
                return None

            self.cache_hits += 1
            logger.debug(f"Cache hit for key: {cache_key}")
            return cached_data.get('response')
        except Exception as e:
            logger.error(f"Error reading from cache for key {cache_key}: {e}", exc_info=True)
            self.cache_misses += 1
            # If error, treat as cache miss and potentially corrupt entry
            if cache_file.exists():
                os.remove(cache_file)
            return None

    def _save_to_cache(self, cache_key: str, response: str):
        """Save a response to the cache"""
        if not self.cache_enabled:
            return

        try:
            cache_file = self.cache_dir / f"{cache_key}.json"
            with open(cache_file, 'w', encoding='utf-8') as f: # Specify encoding
                json.dump({
                    'response': response,
                    'timestamp': time.time()
                }, f, ensure_ascii=False, indent=2) # Save with indent and non-ascii chars
            logger.debug(f"Saved to cache: {cache_key}")
        except Exception as e:
            logger.error(f"Error saving to cache for key {cache_key}: {e}", exc_info=True)

    def send_to_ollama(self, model: str, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.7) -> Dict[str, Any]:
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
        ollama_url = app_config.get('models.ollama.url', 'http://localhost:11434') # Use app_config
        url = f"{ollama_url}/api/generate"

        # Strip 'ollama/' prefix if present
        model_name = model.replace('ollama/', '')

        # Prepare request data
        data = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "temperature": temperature
        }

        # Add system prompt if provided
        if system_prompt:
            data["system"] = system_prompt

        # Configure retries and timeouts
        max_retries = 3
        base_timeout = 30  # Base timeout in seconds
        retry_delay = 2  # Delay between retries in seconds

        for attempt in range(max_retries):
            try:
                logger.info(f"Sending request to Ollama model '{model_name}' (attempt {attempt + 1}/{max_retries})")
                logger.debug(f"Request URL: {url}, Data: {data}")

                # Calculate timeout for this attempt (exponential backoff)
                timeout = base_timeout * (2 ** attempt)

                response = requests.post(
                    url,
                    json=data,
                    timeout=timeout
                )

                response.raise_for_status()

                result = response.json()
                response_text = result.get("response", "").strip()

                # Save to cache if successful
                self._save_to_cache(cache_key, response_text)

                return {
                    "status": "success",
                    "model": model,
                    "response": response_text,
                    "cached": False
                }
            except requests.exceptions.Timeout:
                logger.warning(f"Request to Ollama timed out after {timeout} seconds (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    return {
                        "status": "error",
                        "model": model,
                        "message": f"Request to Ollama timed out after {max_retries} attempts"
                    }
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error to Ollama (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    return {
                        "status": "error",
                        "model": model,
                        "message": "Connection error to Ollama after multiple attempts"
                    }
            except requests.exceptions.RequestException as e: # Catch other request errors
                logger.error(f"HTTP request error to Ollama: {e}", exc_info=True)
                return {
                    "status": "error",
                    "model": model,
                    "message": f"HTTP request error to Ollama: {str(e)}"
                }
            except Exception as e:
                logger.error(f"Unexpected error when sending to Ollama: {str(e)}", exc_info=True)
                return {
                    "status": "error",
                    "model": model,
                    "message": f"Unexpected error with Ollama: {str(e)}"
                }

    def send_to_deepseek(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048) -> Dict[str, Any]:
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
        deepseek_url = app_config.get('models.deepseek.url', 'http://localhost:8000') # Use app_config
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
            result = response.json().get("text", response.text) # Deepseek API might return differently
            logger.info(f"Received response from Deepseek Coder ({len(result)} chars)")

            # Save to cache
            self._save_to_cache(cache_key, result)

            return {
                "status": "success",
                "model": "deepseek",
                "response": result,
                "cached": False
            }
        except requests.exceptions.RequestException as e: # Catch all request-related errors
            error_msg = f"Error contacting Deepseek Coder: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "status": "error",
                "model": "deepseek",
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error with Deepseek Coder: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "status": "error",
                "model": "deepseek",
                "error": error_msg
            }

    def check_model_status(self, model_name: str) -> bool:
        """Check if a model is available"""
        # Check the cache first
        if model_name in self.model_cache:
            cached_status = self.model_cache[model_name]
            if cached_status.get('timestamp', 0) > time.time() - 60:  # Cache valid for 60 seconds
                logger.debug(f"Using cached model status for {model_name}: {cached_status.get('available')}")
                return cached_status.get('available', False)

        # If in standalone mode, consider certain models available without checking
        if self.standalone_mode:
            # In standalone mode, we'll assume these models are available locally
            local_models = ['phi3', 'phi2', 'llama3', 'gemma', 'mistral', 'deepseek'] # Added deepseek
            available = model_name.lower().replace('ollama/', '') in [m.lower() for m in local_models] # Normalize names

            # Update cache
            self.model_cache[model_name] = {
                'available': available,
                'timestamp': time.time(),
                'status': 'online' if available else 'offline',
                'source': 'standalone_mode'
            }

            logger.info(f"[Standalone Mode] Model {model_name} availability: {available}")
            return available

        # Ask the model manager if connected
        if self.model_manager_connected:
            try:
                request = {
                    "action": "check_model",
                    "model": model_name
                }
                logger.debug(f"Querying Model Manager for status of {model_name}")
                self.model_manager.send_string(json.dumps(request))
                response_str = self.model_manager.recv_string()
                response = json.loads(response_str)

                available = response.get('available', False)
                status_info = response.get('status', 'unknown') # Get full status info

                # Update cache
                self.model_cache[model_name] = {
                    'available': available,
                    'timestamp': time.time(),
                    'status': status_info,
                    'source': 'model_manager'
                }
                logger.info(f"Model Manager reported {model_name} as {status_info} (Available: {available})")
                return available
            except Exception as e:
                logger.warning(f"Error checking model status with Model Manager for {model_name}: {e}", exc_info=True)
                # Fall through to default behavior or direct Ollama check

        # Default to checking Ollama directly for Ollama models if Model Manager not connected/failed
        if model_name.startswith("ollama/"):
            try:
                ollama_url = app_config.get('models.ollama.url', 'http://localhost:11434') # Use app_config
                r = requests.get(f"{ollama_url}/api/tags", timeout=5)
                r.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                if r.status_code == 200:
                    available_models = [m['name'] for m in r.json().get('models', [])] # Ollama tags returns list of dicts
                    available = model_name in available_models

                    # Update cache
                    self.model_cache[model_name] = {
                        'available': available,
                        'timestamp': time.time(),
                        'status': 'online' if available else 'offline',
                        'source': 'ollama_direct'
                    }
                    logger.info(f"Direct Ollama check reported {model_name} as available: {available}")
                    return available
            except requests.exceptions.RequestException as e:
                logger.error(f"Error checking Ollama model status directly for {model_name}: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Unexpected error during direct Ollama check for {model_name}: {e}", exc_info=True)

        # Default to unavailable if we can't determine
        logger.warning(f"Could not determine status for model {model_name}, assuming unavailable.")
        self.model_cache[model_name] = { # Cache as unavailable
            'available': False,
            'timestamp': time.time(),
            'status': 'offline',
            'source': 'unknown'
        }
        return False

    def handle_model_status_updates(self):
        """Handle model status updates from the model manager"""
        logger.info("Starting model status update subscription thread.")
        while self.running: # Use self.running from BaseAgent
            try:
                # Use poll with timeout
                if self.model_status.poll(timeout=1000) == 0: # 1 second timeout
                    continue

                # Receive update
                message = self.model_status.recv_string()

                try:
                    update = json.loads(message)

                    event_type = update.get("event")
                    if event_type == "model_status_update":
                        models = update.get("models", {})

                        # Update cache
                        for model_name, model_info in models.items():
                            self.model_cache[model_name] = model_info
                            status = model_info.get("status")
                            logger.info(f"Model status update from MMA: {model_name} is {status}")
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in model status update: {message}")
                except Exception as e:
                    logger.error(f"Error processing model status update: {str(e)}", exc_info=True)

            except zmq.error.Again: # Timeout, continue loop
                pass
            except Exception as e:
                logger.error(f"Error in model status thread: {str(e)}", exc_info=True)
                time.sleep(5)  # Avoid tight loop in case of error
        logger.info("Model status update thread exited.")

    def handle_requests(self):
        """Handle incoming ZMQ requests from other agents on the main REP socket."""
        logger.info("Starting main request handling loop.")
        while self.running: # Use self.running from BaseAgent
            try:
                # Use a timeout to allow checking for shutdown
                if self.receiver.poll(1000) == 0:  # 1 second timeout
                    continue

                # Receive request
                request = self.receiver.recv_json()
                logger.debug(f"Received request: {request}")

                # Process request based on type
                request_type = request.get("request_type", "")
                self.total_requests += 1

                if request_type == "health_check":
                    # This is handled by a separate health socket/thread, but if sent here, respond.
                    logger.info("Processing health check request via main socket.")
                    response = self._get_health_status()
                    self.receiver.send_json(response)

                elif request_type == "generate":
                    # Handle model generation request
                    model = request.get("model", "")
                    prompt = request.get("prompt", "")
                    system_prompt = request.get("system_prompt")
                    temperature = request.get("temperature", 0.7)

                    logger.info(f"Processing generation request - model: {model}, prompt length: {len(prompt)}")
                    if system_prompt:
                        logger.info(f"System prompt provided - length: {len(system_prompt)}")

                    # Route to appropriate model handler
                    if model.startswith("ollama/"):
                        result = self.send_to_ollama(model, prompt, system_prompt, temperature)
                    elif model == "deepseek":
                        result = self.send_to_deepseek(prompt, temperature)
                    elif model == "google":
                        # Handle Google-like translation/NLP request
                        try:
                            # Use the system prompt as the translation instruction, or define a default
                            translation_instruction = system_prompt or f"Translate from {request.get('source_lang', 'eng_Latn')} to {request.get('target_lang', 'tgl_Latn')}"

                            # Route to an Ollama model capable of translation (e.g., phi, llama)
                            # You might need a more sophisticated model routing or a dedicated translation service
                            translation_model = app_config.get('models.translation_model', 'ollama/phi')
                            result = self.send_to_ollama(translation_model, prompt, translation_instruction, temperature)

                            # If successful, format the response
                            if result.get("status") == "success":
                                result = {
                                    "status": "success",
                                    "model": "google_translation_sim", # Indicate it's simulated Google
                                    "translated_text": result.get("response", ""),
                                    "cached": result.get("cached", False)
                                }
                            else: # If Ollama call itself failed
                                result = {
                                    "status": "error",
                                    "model": "google_translation_sim",
                                    "error": result.get("message", "Translation failed")
                                }
                        except Exception as e:
                            logger.error(f"Error in Google translation simulation: {str(e)}", exc_info=True)
                            result = {
                                "status": "error",
                                "model": "google_translation_sim",
                                "error": str(e)
                            }
                    else: # If model name doesn't match any known handler
                        error_msg = f"Unknown model specified for generation: {model}"
                        logger.error(error_msg)
                        result = {
                            "status": "error",
                            "model": model,
                            "error": error_msg
                        }

                    if result.get("status") == "success":
                        self.successful_requests += 1
                    else:
                        self.failed_requests += 1

                    logger.info(f"Generation completed - status: {result.get('status')}")
                    self.receiver.send_json(result)

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

                    self.receiver.send_json(response)

                else: # Unknown request type
                    error_msg = f"Unknown request type received: {request_type}"
                    logger.error(error_msg)
                    self.failed_requests += 1
                    self.receiver.send_json({
                        "status": "error",
                        "message": error_msg
                    })

            except zmq.error.Again: # Timeout, no message received
                continue
            except Exception as e:
                error_msg = f"Error handling request in main loop: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self.failed_requests += 1
                try:
                    self.receiver.send_json({
                        "status": "error",
                        "message": error_msg
                    })
                except Exception as send_error:
                    logger.error(f"Failed to send error response after exception: {send_error}")
        logger.info("Main request handling loop exited.")


    def run(self):
        """Run the remote connector agent. Overrides BaseAgent's run method."""
        try:
            logger.info(f"{self.name} starting background threads...")
            # Start health check thread
            self._start_health_check_thread()
            # Start model status thread
            self.status_thread = threading.Thread(target=self.handle_model_status_updates, daemon=True)
            self.status_thread.start()

            # Main request handling loop (blocking until self.running is False)
            self.handle_requests() # This method contains the while self.running loop

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down.")
        except Exception as e:
            logger.error(f"An unexpected error occurred in {self.name}'s main run loop: {e}", exc_info=True)
        finally:
            self.cleanup() # Ensure cleanup is called


    def cleanup(self):
        """Clean up resources before shutdown. Overrides BaseAgent's cleanup method."""
        logger.info(f"Cleaning up {self.name} resources...")
        self.running = False # Signal threads to stop

        # Wait for threads to finish (with timeout)
        threads_to_join = [self.status_thread, self.health_thread]
        for thread in threads_to_join:
            if thread and thread.is_alive():
                logger.info(f"Waiting for {thread.name} to terminate...")
                thread.join(timeout=2)
                if thread.is_alive():
                    logger.warning(f"{thread.name} did not terminate gracefully.")

        # Close ZMQ sockets
        try:
            for sock in [self.receiver, self.model_manager, self.model_status, self.health_socket]:
                if hasattr(self, 'context') and sock and not sock.closed:
                    sock.close()
                    logger.info(f"Closed ZMQ socket: {sock}")
        except Exception as e:
            logger.error(f"Error closing ZMQ sockets: {e}", exc_info=True)

        # Terminate ZMQ context
        try:
            if hasattr(self, 'context') and self.context and not self.context.closed:
                self.context.term()
                logger.info("ZMQ context terminated.")
        except Exception as e:
            logger.error(f"Error terminating ZMQ context: {e}", exc_info=True)

        logger.info(f"{self.name} cleanup complete.")
        super().cleanup() # Call parent's cleanup

    def connect_to_main_pc_service(self, service_name: str) -> Optional[zmq.Socket]:
        """
        Connect to a service on the main PC using the network configuration.

        Args:
            service_name: Name of the service in the network config ports section

        Returns:
            ZMQ socket connected to the service, or None if connection fails or service not found.
        """
        if service_name not in network_config.get("ports", {}):
            logger.error(f"Service {service_name} not found in network configuration ports section.")
            return None

        port = network_config.get("ports")[service_name]

        # Check if a connection already exists
        if hasattr(self, 'main_pc_connections') and service_name in self.main_pc_connections:
            # For simplicity, return existing socket. In production, add validation if it's still active.
            return self.main_pc_connections[service_name]
        
        # Initialize main_pc_connections if it doesn't exist
        if not hasattr(self, 'main_pc_connections'):
            self.main_pc_connections = {}

        # Create a new socket for this connection
        socket = self.context.socket(zmq.REQ)

        # Apply secure ZMQ if available and enabled (assuming security setup is global)
        # from main_pc_code.src.network.secure_zmq import configure_secure_client, start_auth
        # This agent needs to know if secure ZMQ is enabled globally.
        # If SECURE_ZMQ_AVAILABLE and a secure_zmq flag is maintained in self, apply it.
        # For this example, assuming it's not explicitly managed in RemoteConnectorAgent.

        try:
            # Connect to the service
            connect_address = f"tcp://{MAIN_PC_IP}:{port}" # Use global MAIN_PC_IP
            socket.connect(connect_address)
            logger.info(f"Connected to {service_name} on MainPC at {connect_address}")
            self.main_pc_connections[service_name] = socket
            return socket
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to connect to {service_name} at {connect_address}: {e}", exc_info=True)
            socket.close() # Close the socket if connection fails
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while connecting to {service_name}: {e}", exc_info=True)
            if socket and not socket.closed:
                socket.close()
            return None


if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = RemoteConnectorAgent()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'} on PC2 due to keyboard interrupt...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'} on PC2: {e}")
        traceback.print_exc()
    finally:
        if agent:
            # The agent's cleanup method will now be called by the run() method's finally block,
            # or directly if run() was interrupted earlier.
            # We call it explicitly here as a safeguard if the agent object was created but run() wasn't entered.
            # It's also safe to call cleanup() multiple times as it checks if sockets are closed.
            agent.cleanup()