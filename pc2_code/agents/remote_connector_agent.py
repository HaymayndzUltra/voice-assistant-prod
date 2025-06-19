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

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))
from config.system_config import config

# Configure logging
log_level = config.get('system.log_level', 'INFO')
log_file = Path(config.get('system.logs_dir', 'logs')) / "remote_connector.log"
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RemoteConnector")

# Get ZMQ ports from config
REMOTE_CONNECTOR_PORT = config.get('zmq.remote_connector_port', 5557)
MODEL_MANAGER_PORT = config.get('zmq.model_manager_port', 5556)  # Base port for MMA
MODEL_MANAGER_HOST = config.get('zmq.model_manager_host', '192.168.100.16')  # Main PC's IP address
TASK_ROUTER_PORT = config.get('zmq.task_router_port', 5558)

class RemoteConnectorAgent:
    def __init__(self):
        logger.info("=" * 80)
        logger.info("Initializing Remote Connector Agent")
        logger.info("=" * 80)
        
        # Initialize ZMQ
        self.context = zmq.Context()
        
        # Socket to receive requests
        self.receiver = self.context.socket(zmq.REP)
        self.receiver.bind(f"tcp://0.0.0.0:{REMOTE_CONNECTOR_PORT}")
        logger.info(f"Remote Connector bound to port {REMOTE_CONNECTOR_PORT}")
        
        # Socket to communicate with model manager
        self.model_manager = self.context.socket(zmq.REQ)
        self.model_manager_port = config.get('zmq.model_manager_port', 5555)  # Changed from 5556 to 5555 to connect to MMA's REP socket
        self.model_manager_connected = False
        try:
            self.model_manager.connect(f"tcp://{MODEL_MANAGER_HOST}:{self.model_manager_port}")
            # Set a short timeout for the connection attempt
            self.model_manager.setsockopt(zmq.RCVTIMEO, 500)  # 500ms timeout
            self.model_manager_connected = True
            logger.info(f"Connected to Model Manager on {MODEL_MANAGER_HOST}:{self.model_manager_port}")
        except Exception as e:
            logger.warning(f"Could not connect to Model Manager: {e}. Will operate in standalone mode.")
        
        # Socket to subscribe to model status updates
        self.model_status = self.context.socket(zmq.SUB)
        self.model_status_port = self.model_manager_port + 10  # Publisher port is base + 10
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
        
        # Record start time for uptime tracking
        self.start_time = time.time()
        
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
    
    def _calculate_cache_key(self, model, prompt, system_prompt=None, temperature=0.7):
        """Calculate a unique cache key for a request"""
        # Create a string representation of the request
        request_str = f"{model}:{prompt}:{system_prompt}:{temperature}"
        # Create a hash of the request
        return hashlib.md5(request_str.encode()).hexdigest()
    
    def _check_cache(self, cache_key):
        """Check if a response is in the cache and not expired"""
        if not self.cache_enabled:
            return None
            
        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            self.cache_misses += 1
            return None
            
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
            
            # Check if cache entry is expired
            if time.time() - cached_data.get('timestamp', 0) > self.cache_ttl:
                self.cache_misses += 1
                return None
                
            self.cache_hits += 1
            return cached_data.get('response')
        except Exception as e:
            logger.error(f"Error reading from cache: {e}")
            self.cache_misses += 1
            return None
    
    def _save_to_cache(self, cache_key, response):
        """Save a response to the cache"""
        if not self.cache_enabled:
            return
            
        try:
            cache_file = self.cache_dir / f"{cache_key}.json"
            with open(cache_file, 'w') as f:
                json.dump({
                    'response': response,
                    'timestamp': time.time()
                }, f)
        except Exception as e:
            logger.error(f"Error saving to cache: {e}")
    
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
                logger.debug(f"Request URL: {url}")
                
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
                logger.warning(f"Request timed out after {timeout} seconds (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    return {
                        "status": "error",
                        "model": model,
                        "message": f"Request timed out after {max_retries} attempts"
                    }
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    return {
                        "status": "error",
                        "model": model,
                        "message": "Connection error after multiple attempts"
                    }
                    
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                logger.error(traceback.format_exc())
                return {
                    "status": "error",
                    "model": model,
                    "message": f"Unexpected error: {str(e)}"
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
        deepseek_url = config.get('models.deepseek.url', 'http://localhost:8000')
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
            return {
                "status": "error",
                "model": "deepseek",
                "error": error_msg
            }
            
    def check_model_status(self, model_name):
        """Check if a model is available"""
        # Check the cache first
        if model_name in self.model_cache:
            cached_status = self.model_cache[model_name]
            if cached_status.get('timestamp', 0) > time.time() - 60:  # Cache valid for 60 seconds
                return cached_status.get('available', False)
        
        # If in standalone mode, consider certain models available without checking
        if self.standalone_mode:
            # In standalone mode, we'll assume these models are available locally
            local_models = ['phi3', 'phi2', 'llama3', 'gemma', 'mistral']
            available = model_name.lower() in [m.lower() for m in local_models]
            
            # Update cache
            self.model_cache[model_name] = {
                'available': available,
                'timestamp': time.time()
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
                
                self.model_manager.send_string(json.dumps(request))
                response_str = self.model_manager.recv_string()
                response = json.loads(response_str)
                
                available = response.get('available', False)
                
                # Update cache
                self.model_cache[model_name] = {
                    'available': available,
                    'timestamp': time.time()
                }
                
                return available
            except Exception as e:
                logger.warning(f"Error checking model status with Model Manager: {e}")
                # Fall through to default behavior
        
        # Default to checking Ollama directly for Ollama models
        if model_name.startswith("ollama/"):
            try:
                ollama_url = config.get('models.ollama.url', 'http://localhost:11434')
                r = requests.get(f"{ollama_url}/api/tags", timeout=5)
                if r.status_code == 200:
                    available_models = r.json().get('models', [])
                    available = model_name in available_models
                    
                    # Update cache
                    self.model_cache[model_name] = {
                        'available': available,
                        'timestamp': time.time()
                    }
                    
                    return available
            except Exception as e:
                logger.error(f"Error checking Ollama model status: {e}")
        
        # Default to unavailable if we can't determine
        return False
    
    def handle_model_status_updates(self):
        """Handle model status updates from the model manager"""
        while self.running:
            try:
                # Use poll with timeout
                if self.model_status.poll(timeout=1000) == 0:
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
                            logger.info(f"Model status update: {model_name} is {status}")
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in model status update: {message}")
                except Exception as e:
                    logger.error(f"Error processing model status update: {str(e)}")
            
            except zmq.Again:
                # Timeout, continue loop
                pass
            except Exception as e:
                logger.error(f"Error in model status thread: {str(e)}")
                time.sleep(5)  # Avoid tight loop in case of error
    
    def handle_requests(self):
        """Handle incoming ZMQ requests"""
        while self.running:
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
                    # Handle health check request
                    logger.info("Processing health check request")
                    response = {
                        "status": "ok",
                        "service": "remote_connector_agent",
                        "timestamp": time.time(),
                        "uptime_seconds": time.time() - self.start_time,
                        "total_requests": self.total_requests,
                        "successful_requests": self.successful_requests,
                        "failed_requests": self.failed_requests,
                        "cache_enabled": self.cache_enabled,
                        "cache_hits": self.cache_hits,
                        "cache_misses": self.cache_misses,
                        "cache_hit_ratio": (self.cache_hits / (self.cache_hits + self.cache_misses) * 100) if (self.cache_hits + self.cache_misses) > 0 else 0,
                        "model_manager_connected": self.model_manager_connected,
                        "standalone_mode": self.standalone_mode
                    }
                    logger.info(f"Health check response: {json.dumps(response)}")
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
                        # Handle Google translation request
                        try:
                            # Use the system prompt as the translation instruction
                            translation_instruction = system_prompt or f"Translate from {request.get('source_lang', 'eng_Latn')} to {request.get('target_lang', 'tgl_Latn')}"
                            
                            # Send to Ollama for translation
                            result = self.send_to_ollama("ollama/phi", prompt, translation_instruction, temperature)
                            
                            # If successful, format the response
                            if result.get("status") == "success":
                                result = {
                                    "status": "success",
                                    "model": "google",
                                    "translated_text": result.get("response", ""),
                                    "cached": result.get("cached", False)
                                }
                        except Exception as e:
                            logger.error(f"Error in Google translation: {str(e)}")
                            result = {
                                "status": "error",
                                "model": "google",
                                "error": str(e)
                            }
                        else:
                            error_msg = f"Unknown model: {model}"
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
                
                else:
                    error_msg = f"Unknown request type: {request_type}"
                    logger.error(error_msg)
                    self.failed_requests += 1
                    self.receiver.send_json({
                        "status": "error",
                        "message": error_msg
                    })
                
            except zmq.error.Again:
                # Socket timeout, continue
                continue
            except Exception as e:
                error_msg = f"Error handling request: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                self.failed_requests += 1
                try:
                    self.receiver.send_json({
                        "status": "error",
                        "message": error_msg
                    })
                except:
                    pass
    
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
        self.model_manager.close()
        self.model_status.close()
        self.context.term()
        
        logger.info("Remote Connector Agent stopped")


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