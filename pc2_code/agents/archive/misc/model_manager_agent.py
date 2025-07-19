"""
from common.config_manager import get_service_ip, get_service_url, get_redis_url
Model Manager / Resource Monitor Agent
- Tracks status and availability of all models
- Provides model selection based on capabilities, availability and task requirements
- Performs regular health checks on model services
- Does NOT perform direct model inference (handled by Remote Connector Agent)
"""
import zmq
import torch
import json
import time
import logging
import requests
import threading
import sys
import os
from pathlib import Path
import pickle
from datetime import datetime, timedelta

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))

# Set up basic logging first in case config import fails
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ModelManager")

try:
    # Import config module
from pc2_code.config.system_config import config
from common.env_helpers import get_env
    
    # Configure logging with config settings
    log_level = config.get('system.log_level', 'INFO')
    logs_dir = Path(config.get('system.logs_dir', 'logs'))
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / "model_manager.log"
    
    # Add file handler to logger
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.setLevel(getattr(logging, log_level))
    
    logger.info("Logging configured successfully")
except Exception as e:
    logger.error(f"Error setting up config or logging: {e}")
    logger.error("Continuing with default settings")

# ZMQ ports
MODEL_MANAGER_PORT = 5570
TASK_ROUTER_PORT = 5571

class ModelManagerAgent:
    def __init__(self):
        # Setup device for GPU acceleration
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Model Manager using device: {self.device}")
        
        # Track GPU memory usage
        self.gpu_memory_limit = config.get('models.gpu_memory_limit', 0.9)  # Default: use up to 90% of GPU memory
        self.gpu_memory_reserved = 0  # Track reserved memory in MB
        if self.device == 'cuda':
            self.total_gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)  # Convert to MB
            logger.info(f"Total GPU memory: {self.total_gpu_memory:.2f} MB")
        else:
            self.total_gpu_memory = 0

        # ZMQ setup
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        port = config.get('zmq.model_manager_port', 5556)
        self.socket.bind(f"tcp://0.0.0.0:{port}")
        logger.info(f"Model Manager bound to port {port}")
        
        # Publisher for status updates
        self.pub_socket = self.context.socket(zmq.PUB)
        pub_port = port + 10  # Convention: pub ports are 10 higher than req/rep ports
        self.pub_socket.bind(f"tcp://0.0.0.0:{pub_port}")
        logger.info(f"Model Manager publisher bound to port {pub_port}")
        
        # Track loaded models and their memory usage
        self.loaded_models = {}
        self.model_last_used = {}
        self.model_memory_usage = {}
        
        # Model loading/unloading settings
        self.idle_timeout = config.get('models.idle_timeout', 300)  # Unload models after 5 minutes of inactivity
        self.memory_check_interval = config.get('models.memory_check_interval', 30)  # Check memory every 30 seconds
        
        # Load model information from config
        self.models = {}
        self._load_models_from_config()
        
        # Note: Caching is now handled by the Remote Connector Agent
        # The Model Manager Agent no longer maintains a response cache
        
        # Health check interval (seconds)
        self.health_check_interval = config.get('models.health_check_interval', 30)
        self.running = True
    
    def _load_models_from_config(self):
        """Load model configurations from the central config"""
        # Load Ollama models
        ollama_config = config.get('models.ollama', {})
        ollama_url = ollama_config.get('url', 'http://localhost:11434')
        ollama_models = ollama_config.get('models', {})
        
        for model_name, model_config in ollama_models.items():
            if model_config.get('enabled', True):
                self.models[model_name] = {
                    'url': ollama_url,
                    'status': 'unknown',
                    'last_check': 0,
                    'capabilities': model_config.get('capabilities', []),
                    'context_length': model_config.get('context_length', 2048)
                }
        
        # Load Deepseek model if enabled
        deepseek_config = config.get('models.deepseek', {})
        if deepseek_config.get('enabled', False):
            self.models['deepseek'] = {
                'url': deepseek_config.get('url', 'http://localhost:8000'),
                'status': 'unknown',
                'last_check': 0,
                'capabilities': deepseek_config.get('capabilities', []),
                'context_length': deepseek_config.get('context_length', 16000)
            }
            
        # Register TinyLlama service (ZMQ port 5615)
        self.models['tinyllama'] = {
            'url': 'zmq://localhost:5615',  # Using ZMQ protocol instead of HTTP
            'status': 'unknown',
            'last_check': 0,
            'capabilities': ['text-generation', 'fallback'],  # This is a fallback model
            'context_length': 2048,  # TinyLlama context window
            'priority': 'low',  # Lower priority than other models
            'type': 'zmq'  # Indicate this is a ZMQ service, not HTTP
        }
        logger.info("Registered TinyLlama service on port 5615")
        
        logger.info(f"Loaded {len(self.models)} models from configuration")
    
    def select_model(self, task_type, context_size=None):
        """Select the best model for a given task type"""
        # Filter for online models
        available_models = {name: info for name, info in self.models.items() 
                          if info['status'] == 'online'}
        
        if not available_models:
            logger.warning("No models are online! Returning first model as fallback.")
            return next(iter(self.models))
        
        # Filter by context size if specified
        if context_size:
            suitable_models = {name: info for name, info in available_models.items() 
                              if info['context_length'] >= context_size}
            
            if not suitable_models:
                logger.warning(f"No models can handle context size {context_size}! Returning largest model.")
                return max(self.models.items(), key=lambda x: x[1]['context_length'])[0]
            available_models = suitable_models
        
        # Match by capability
        capable_models = {}
        for name, info in available_models.items():
            if task_type in info['capabilities']:
                capable_models[name] = info
        
        if capable_models:
            # If we have multiple capable models, use a weighted selection based on:
            # 1. Context length (larger is better)
            # 2. Historical performance (if tracked)
            # 3. Load balancing considerations
            
            # For now, just return the model with the largest context window among capable models
            selected_model = max(capable_models.items(), key=lambda x: x[1]['context_length'])[0]
            logger.info(f"Selected model '{selected_model}' for task type '{task_type}'")
            return selected_model
        else:
            # Fallback to any available model
            logger.warning(f"No models have capability '{task_type}'! Returning first available model.")
            selected_model = next(iter(available_models))
            logger.info(f"Fallback: selected model '{selected_model}' for task type '{task_type}'")
            return selected_model
    
    def health_check(self):
        # Check Ollama models
        ollama_models = [model for model, info in self.models.items() 
                        if info['url'] == config.get('models.ollama.url', 'http://localhost:11434')]
        
        # Group Ollama models to check them with a single API call
        if ollama_models:
            try:
                ollama_url = config.get('models.ollama.url', 'http://localhost:11434')
                r = requests.get(f"{ollama_url}/api/tags", timeout=5)
                if r.status_code == 200:
                    available_models = r.json().get('models', [])
                    
                    # Update status for each Ollama model
                    for model in ollama_models:
                        if model in available_models:
                            self.models[model]['status'] = 'online'
                        else:
                            self.models[model]['status'] = 'available_not_loaded'
                        self.models[model]['last_check'] = time.time()
                else:
                    # Ollama server error
                    for model in ollama_models:
                        self.models[model]['status'] = 'error'
                        self.models[model]['last_check'] = time.time()
            except Exception as e:
                logger.error(f"Error checking Ollama models: {e}")
                # Mark all Ollama models as offline
                for model in ollama_models:
                    self.models[model]['status'] = 'offline'
                    self.models[model]['last_check'] = time.time()
        
        # Check Deepseek if configured
        if 'deepseek' in self.models:
            try:
                # Always get the latest URL from config
                deepseek_config = config.get('models.deepseek', {})
                base_url = deepseek_config.get('url', 'http://localhost:8000')
                
                # Extract the base URL without the endpoint
                if '/generate' in base_url:
                    base_url = base_url.split('/generate')[0]
                
                # Update the URL in the models dictionary
                self.models['deepseek']['url'] = base_url
                
                # For DeepSeek, we check if the /generate endpoint is available
                # This is based on the deepseekcoder_client.py implementation
                generate_url = f"{base_url}/generate"
                logger.info(f"Checking Deepseek model at {generate_url}")
                
                # Send a simple OPTIONS request to check if the endpoint exists
                r = requests.options(generate_url, timeout=5)
                
                if r.status_code != 404:
                    # If we get any response other than 404, the endpoint likely exists
                    self.models['deepseek']['status'] = 'online'
                    logger.info(f"Deepseek model is online at {generate_url}")
                else:
                    self.models['deepseek']['status'] = 'error'
                    logger.error(f"Deepseek endpoint not found at {generate_url}")
            except Exception as e:
                logger.error(f"Error checking deepseek: {e}")
                self.models['deepseek']['status'] = 'offline'
            
            self.models['deepseek']['last_check'] = time.time()
        
        # Check TinyLlama ZMQ service (port 5615)
        if 'tinyllama' in self.models:
            try:
                # Health check for ZMQ-based TinyLlama service
                zmq_context = zmq.Context()
                zmq_socket = zmq_context.socket(zmq.REQ)
                zmq_socket.setsockopt(zmq.LINGER, 0)  # Don't wait on close
                zmq_socket.setsockopt(zmq.RCVTIMEO, 2000)  # 2 second timeout for receiving
                zmq_socket.setsockopt(zmq.SNDTIMEO, 2000)  # 2 second timeout for sending
                
                # Extract port from the URL
                url = self.models['tinyllama']['url']
                port = 5615  # Default
                if '://' in url:
                    parts = url.split('://')
                    if len(parts) > 1 and ':' in parts[1]:
                        port = int(parts[1].split(':')[1])
                
                zmq_socket.connect(f"tcp://localhost:{port}")
                
                # Send health check request
                health_request = {"action": "health_check"}
                zmq_socket.send_string(json.dumps(health_request))
                
                # Wait for response with timeout
                response = json.loads(zmq_socket.recv_string())
                
                # Update status based on response
                if response.get("status") == "ok" and response.get("service") == "running":
                    self.models['tinyllama']['status'] = 'online'
                    logger.info(f"TinyLlama service is online at port {port}")
                else:
                    self.models['tinyllama']['status'] = 'error'
                    logger.warning(f"TinyLlama service reported issues: {response}")
                    
                # Clean up ZMQ socket
                zmq_socket.close()
                zmq_context.term()
                
            except Exception as e:
                logger.error(f"Error checking TinyLlama service: {e}")
                self.models['tinyllama']['status'] = 'offline'
            
            self.models['tinyllama']['last_check'] = time.time()
        
        # Publish status update
        status_message = json.dumps({
            'event': 'model_status_update',
            'models': self.models,
            'timestamp': time.time()
        })
        self.pub_socket.send_string(status_message)
        
        # Log status update (but only if debug mode is enabled or status changed)
        if config.get('system.debug_mode', False):
            logger.info(f"Published model status update: {self.models}")
        else:
            # Just log a summary
            status_summary = {model: info['status'] for model, info in self.models.items()}
            logger.info(f"Model status: {status_summary}")
    
    def handle_request(self, request):
        """Handle incoming requests"""
        try:
            request_data = json.loads(request)
            request_type = request_data.get('request_type')
            
            if request_type == 'health_check':
                self.health_check()
                return json.dumps({
                    'status': 'success',
                    'models': self.models
                })
            
            elif request_type == 'select_model':
                task_type = request_data.get('task_type', 'chat')
                context_size = request_data.get('context_size')
                selected_model = self.select_model(task_type, context_size)
                return json.dumps({
                    'status': 'success',
                    'selected_model': selected_model,
                    'model_info': self.models[selected_model]
                })
            
            elif request_type == 'get_model_status':
                model_name = request_data.get('model')
                if model_name in self.models:
                    return json.dumps({
                        'status': 'success',
                        'model': model_name,
                        'model_status': self.models[model_name]
                    })
                else:
                    return json.dumps({
                        'status': 'error',
                        'message': f"Model '{model_name}' not found"
                    })
            
            else:
                return json.dumps({
                    'status': 'error',
                    'message': f"Unknown request type: {request_type}"
                })
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return json.dumps({
                'status': 'error',
                'message': str(e)
            })
    
    def health_check_loop(self):
        """Background thread for periodic health checks"""
        logger.info("Started health check loop")
        while self.running:
            try:
                self.health_check()
            except Exception as e:
                logger.error(f"Error in health check: {e}")
            
            # Sleep for the health check interval
            for _ in range(self.health_check_interval):
                if not self.running:
                    break
                time.sleep(1)
    
    def run(self):
        """Main loop for the model manager agent"""
        try:
            # Start health check thread
            health_thread = threading.Thread(target=self.health_check_loop)
            health_thread.daemon = True
            health_thread.start()
            
            logger.info("Model Manager Agent ready to handle requests")
            
            # Main loop - handle incoming requests
            while self.running:
                try:
                    # Wait for incoming request with timeout
                    if self.socket.poll(1000) == 0:
                        continue
                    
                    # Receive and process request
                    message = self.socket.recv_string()
                    response = self.handle_request(message)
                    
                    # Send response
                    self.socket.send_string(response)
                    
                except zmq.Again:
                    # Timeout, continue loop
                    pass
                except Exception as e:
                    logger.error(f"Error handling request: {e}")
                    # Try to send error response
                    try:
                        self.socket.send_string(json.dumps({
                            'status': 'error',
                            'message': str(e)
                        }))
                    except:
                        pass
        finally:
            # Cleanup
            self._save_cache()
            self.socket.close()
            self.pub_socket.close()
            self.context.term()
            logger.info("Model Manager Agent stopped")


# Main entry point
if __name__ == "__main__":
    try:
        # Create necessary directories
        Path("logs").mkdir(exist_ok=True)
        Path("cache").mkdir(exist_ok=True)
        
        logger.info("Starting Model Manager Agent")
        agent = ModelManagerAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
