from src.core.base_agent import BaseAgent
"""
Code Generator Agent
- Generates code based on natural language descriptions
- Supports multiple programming languages
- Integrates with the AutoGen framework
- Uses local LLMs for code generation
"""
import os
import uuid
import time
import zmq
import json
import logging
import traceback
import sys
import gc
# from web_automation import GLOBAL_TASK_MEMORY  # Unified adaptive memory (commented out for PC1)
from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
import tempfile
import re
import threading

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))
from config.system_config import config

# Import the GGUF Model Manager
from agents.gguf_model_manager import get_instance as get_gguf_manager
from utils.config_parser import parse_agent_args
_agent_args = parse_agent_args()

# Check for GGUF support
try:
    import llama_cpp
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    logger = logging.getLogger("CodeGeneratorAgent")
    logger.warning("llama-cpp-python not installed. GGUF models will not be available.")

# Configure logging
log_level = config.get('system.log_level', 'INFO')
log_file = Path(config.get('system.logs_dir', 'logs')) / "code_generator_agent.log"
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CodeGeneratorAgent")

# Get ZMQ ports from config
CODE_GENERATOR_PORT = config.get('zmq.code_generator_port', 5604)
MODEL_MANAGER_PORT = config.get('zmq.model_manager_port', 5556)
AUTOGEN_FRAMEWORK_PORT = config.get('zmq.autogen_framework_port', 5600)
EXECUTOR_PORT = config.get('zmq.executor_port', 5613)

MODEL_IDLE_TIMEOUT = 600  # seconds
model_last_used = {}

class CodeGeneratorAgent(BaseAgent):
    def __init__(self, port: int = None, debug: bool = False, **kwargs):
        super().__init__(port=port, name="CodeGeneratorAgent")
        # Initialize the Code Generator Agent
        import logging
        import json
        import time
        import zmq
        import sys
        import os
        
        # Configure logging
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("logs/code_generator.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger("CodeGeneratorAgent")
        
        # Set up ZMQ socket
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.port = port
        self.debug = debug
        
        # Initialize model manager connection
        self.model_manager_address = f"tcp://{_agent_args.get('model_manager_host', 'localhost')}:{_agent_args.get('model_manager_port', 5570)}"
        
        # VRAM management now handled by VRAMOptimizerAgent

        # Initialize GGUF support if available
        try:
            from agents.gguf_model_manager import GGUFModelManager
            self.gguf_manager = GGUFModelManager()
            self.logger.info("GGUF Model Manager initialized")
        except Exception as e:
            self.logger.warning(f"GGUF Model Manager not available: {e}")
            self.gguf_manager = None
        
        self.logger.info(f"Code Generator Agent initialized on port {port}")
    
    def start(self):
        """Start the agent and bind to the port"""
        try:
            self.socket.bind(f"tcp://*:{self.port}")
            self.logger.info(f"Code Generator Agent listening on port {self.port}")
            self.handle_requests()
        except Exception as e:
            self.logger.error(f"Failed to start Code Generator Agent: {e}")
    
    def handle_requests(self):
        """Handle incoming requests"""
        import json
        import time
        
        self.logger.info("Ready to handle requests...")
        
        while True:
            try:
                # Wait for request
                message = self.socket.recv_string()
                self.logger.debug(f"Received message: {message[:100]}...")
                
                # Parse request
                request = json.loads(message)
                action = request.get('action')
                
                # Default response
                response = {"status": "error", "error": "Unknown action"}
                
                self.logger.info(f"Handling action: {action}")
                
                # Handle different actions
                if action == 'ping':
                    response = {"status": "success", "message": "pong", "timestamp": time.time()}
                
                elif action == 'health_check':
                    response = {"status": "healthy", "service": "CodeGeneratorAgent"}
                
                elif action == 'load_gguf_model':
                    model_id = request.get('model_id')
                    if not model_id:
                        response = {"status": "error", "error": "Missing model_id parameter"}
                    else:
                        response = self.load_gguf_model(model_id)
                
                elif action == 'unload_gguf_model':
                    model_id = request.get('model_id')
                    if not model_id:
                        response = {"status": "error", "error": "Missing model_id parameter"}
                    else:
                        response = self.unload_gguf_model(model_id)
                
                elif action == 'generate_with_gguf':
                    model_id = request.get('model_id')
                    prompt = request.get('prompt')
                    system_prompt = request.get('system_prompt')
                    max_tokens = request.get('max_tokens', 1024)
                    temperature = request.get('temperature', 0.7)
                    
                    if not model_id or not prompt:
                        response = {"status": "error", "error": "Missing required parameters"}
                    else:
                        response = self.generate_with_gguf(
                            model_id=model_id,
                            prompt=prompt,
                            system_prompt=system_prompt,
                            max_tokens=max_tokens,
                            temperature=temperature
                        )
                
                elif action == 'get_gguf_status':
                    # Get status of all GGUF models
                    if self.gguf_manager:
                        try:
                            models = self.gguf_manager.list_models()
                            status = {}
                            for model in models:
                                model_id = model.get('model_id')
                                # Map 'loaded' boolean to 'loaded'/'unloaded' status string
                                if model.get('loaded', False):
                                    status[model_id] = 'loaded'
                                else:
                                    status[model_id] = 'unloaded'
                                
                            response = {
                                "status": "success", 
                                "models": status,
                                "timestamp": time.time()
                            }
                        except Exception as e:
                            self.logger.error(f"Error getting GGUF model status: {e}")
                            response = {"status": "error", "error": str(e)}
                    else:
                        response = {
                            "status": "error", 
                            "error": "GGUF manager not available",
                            "timestamp": time.time()
                        }
                
                elif action == 'list_gguf_models':
                    # List all available GGUF models
                    if self.gguf_manager:
                        try:
                            models = self.gguf_manager.list_models()
                            response = {
                                "status": "success", 
                                "models": models,
                                "timestamp": time.time()
                            }
                        except Exception as e:
                            self.logger.error(f"Error listing GGUF models: {e}")
                            response = {"status": "error", "error": str(e)}
                    else:
                        response = {
                            "status": "error", 
                            "error": "GGUF manager not available",
                            "timestamp": time.time()
                        }
                
                elif action == 'generate':
                    # Generate code with Ollama model
                    model = request.get('model')
                    prompt = request.get('prompt')
                    request_id = request.get('request_id', f"gen_{int(time.time())}")
                    
                    self.logger.info(f"Ollama generation request (ID: {request_id}): model={model}, prompt_len={len(prompt) if prompt else 0}")
                    
                    if not model or not prompt:
                        response = {"status": "error", "error": "Missing model or prompt parameter"}
                    else:
                        try:
                            # Call Ollama API to generate code
                            import requests
                            ollama_url = "http://localhost:11434/api/generate"
                            
                            ollama_request = {
                                "model": model,
                                "prompt": prompt,
                                "stream": False
                            }
                            
                            self.logger.info(f"Sending request to Ollama API: {model}")
                            ollama_response = requests.post(ollama_url, json=ollama_request)
                            
                            if ollama_response.status_code == 200:
                                result = ollama_response.json()
                                generated_text = result.get('response', '')
                                
                                # Extract code blocks if present
                                code_blocks = re.findall(r'```(?:\w+)?\n([\s\S]*?)```', generated_text)
                                code = code_blocks[0] if code_blocks else generated_text
                                
                                response = {
                                    "status": "success",
                                    "code": code,
                                    "full_response": generated_text,
                                    "model": model,
                                    "request_id": request_id
                                }
                            else:
                                response = {
                                    "status": "error",
                                    "error": f"Ollama API error: {ollama_response.status_code} {ollama_response.text}",
                                    "request_id": request_id
                                }
                        except Exception as e:
                            self.logger.error(f"Error generating with Ollama: {e}")
                            response = {"status": "error", "error": f"Error: {str(e)}"}
                
                elif action == 'generate_code':
                    # Generate code based on the description
                    description = request.get('description', '')
                    language = request.get('language')
                    use_voting = request.get("use_voting", False)
                    save_to_file = request.get("save_to_file", True)
                    model_id = request.get('model_id')  # Optional specific GGUF model to load
                    request_id = request.get('request_id', f"gen_{int(time.time())}")
                    
                    self.logger.info(f"Code generation request (ID: {request_id}): desc len={len(description)}, lang={language}, model_id={model_id}")
                    
                    if not description:
                        response = {"status": "error", "error": "Missing description parameter"}
                    else:
                        # Forward to model manager
                        response = self.forward_to_model_manager({
                            "request_type": "generate_code",
                            "description": description,
                            "language": language,
                            "use_voting": use_voting,
                            "save_to_file": save_to_file,
                            "model_id": model_id,
                            "request_id": request_id
                        })
                
                # Send response
                self.logger.debug(f"Sending response: {response}")
                self.socket.send_string(json.dumps(response))
                
            except Exception as e:
                self.logger.error(f"Error handling request: {e}")
                try:
                    # Try to send error response
                    self.socket.send_string(json.dumps({"status": "error", "error": str(e)}))
                except:
                    pass
    
    def load_gguf_model(self, model_id):
        """Load a GGUF model"""
        if not self.gguf_manager:
            return {"status": "error", "error": "GGUF manager not available"}
        
        try:
            result = self.gguf_manager.load_model(model_id)
            return result
        except Exception as e:
            self.logger.error(f"Error loading GGUF model {model_id}: {e}")
            return {"status": "error", "error": str(e)}
    
    # Model unloading now handled by VRAMOptimizerAgent and ModelManagerAgent

    def unload_gguf_model(self, model_id):
        """Unload a GGUF model"""
        if not self.gguf_manager:
            return {"status": "error", "error": "GGUF manager not available"}
        
        try:
            result = self.gguf_manager.unload_model(model_id)
            return result
        except Exception as e:
            self.logger.error(f"Error unloading GGUF model {model_id}: {e}")
            return {"status": "error", "error": str(e)}
    
    def generate_with_gguf(self, model_id, prompt, system_prompt=None, max_tokens=1024, temperature=0.7):
        """Generate text with a GGUF model"""
        if not self.gguf_manager:
            return {"status": "error", "error": "GGUF manager not available"}
        
        try:
            # Inform the VRAM manager that this model is being used
            self._update_model_usage(model_id)
            
            # Check if model is loaded
            models = self.gguf_manager.list_models()
            model_loaded = False
            
            for model in models:
                if model.get('model_id') == model_id and model.get('loaded', False):
                    model_loaded = True
                    break
            
            # Load model if not loaded
            if not model_loaded:
                load_success = self.gguf_manager.load_model(model_id)
                if not load_success:
                    return {"status": "error", "error": f"Failed to load model {model_id}"}
            
            # Generate text
            result = self.gguf_manager.generate_text(
                model_id=model_id,
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return result
        except Exception as e:
            self.logger.error(f"Error generating with GGUF model {model_id}: {e}")
            return {"status": "error", "error": str(e)}
    
    def forward_to_model_manager(self, request):
        """Forward a request to the Model Manager Agent"""
        import zmq
        
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        socket.setsockopt(zmq.RCVTIMEO, 60000)  # 60 second timeout
        
        try:
            self.logger.info(f"Connecting to Model Manager at {self.model_manager_address}")
            # Connect to task router instead of model manager
            task_router_address = self.model_manager_address.replace("5556", "8570")
            socket.connect(task_router_address)
            
            self.logger.info(f"Forwarding request to Model Manager: {request}")
            socket.send_string(json.dumps(request))
            
            self.logger.info("Waiting for response from Model Manager...")
            response_str = socket.recv_string()
            response = json.loads(response_str)
            
            self.logger.info(f"Received response from Model Manager: {response}")
            return response
        except Exception as e:
            self.logger.error(f"Error forwarding to Model Manager: {e}")
            return {"status": "error", "error": f"Error communicating with Model Manager: {e}"}
        finally:
            socket.close()
            context.term()

    def get_model(self, model_id):
        now = time.time()
        # Unload idle models
        for mid, last_used in list(model_last_used.items()):
            if now - last_used > MODEL_IDLE_TIMEOUT:
                self.unload_gguf_model(mid)
                del model_last_used[mid]
        # Lazy load
        if model_id not in model_last_used:
            self.load_gguf_model(model_id)
        model_last_used[model_id] = now
        return True

# Run the agent if executed directly
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Code Generator Agent')
    parser.add_argument('--port', type=int, default=5604, help='Port to run the agent on')
    parser.add_argument("--ollama_base_url", type=str, default="http://localhost:11434", help="Base URL for the Ollama API")
    parser.add_argument('--simple-debug', action='store_true', help='Enable simple debug mode')
    
    args = parser.parse_args()
    
    agent = CodeGeneratorAgent(port=args.port, debug=args.simple_debug)
    agent.start()
 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise