from common.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
TinyLLama Service
- Provides access to the TinyLLama model via ZMQ
- Supports on-demand loading/unloading for VRAM management
- Compatible with the ModelManagerAgent (MMA) for orchestration

Request Format:
- For text generation: {"action": "generate", "prompt": "Your prompt here", "max_tokens": 100}
- For loading model: {"action": "ensure_loaded"}
- For unloading model: {"action": "request_unload"}
- For health check: {"action": "health_check"}

Response Format:
- For generation: {"status": "success", "text": "Generated text"}
- For load/unload: {"status": "success", "message": "Model loaded/unloaded"}
- For health check: {"status": "ok", "service": "tinyllama_service", 
                    "model_status": "loaded" or "unloaded", "timestamp": time.time()}
"""

import zmq
import json
import time
import logging
import sys
import os
import traceback
import threading
from pathlib import Path
import torch

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))
from pc2_code.config.system_config import config
from common.env_helpers import get_env

# Configure logging
log_level = config.get('system.log_level', 'INFO')
log_file = Path(config.get('system.logs_dir', 'logs')) / "tinyllama_service.log"
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TinyLlamaService")

class TinyLlamaService:
    """Service for TinyLLama model with on-demand loading/unloading"""
    
    def __init__(self, zmq_port=TINYLLAMA_SERVICE_PORT, ollama_base_url=OLLAMA_API_BASE):

        super().__init__(*args, **kwargs)        """Initialize the TinyLlama Service with ZMQ REP socket on specified port"""
        # ZMQ setup
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://127.0.0.1:{zmq_port}")
        
        # Ollama connection
        self.ollama_base_url = ollama_base_url
        self.model_name = "tinyllama"  # Default model name in Ollama
        
        # Agent state
        self.running = True
        self.lock = threading.Lock()
        self.start_time = datetime.now()
        self.request_count = 0
        self.error_count = 0
        self.last_request_time = None
        
        # Model parameters
        self.default_params = {
            "temperature": 0.7,
            "max_tokens": 512,
            "top_p": 0.9,
            "top_k": 40,
            "stream": False
        }
        
        logger.info(f"[TinyLlama] Service started on port {zmq_port} with REP socket")
        
        # Check if model is available
        self._check_model()
    
    def _check_model(self):
        """Check if TinyLlama is available in Ollama"""
        try:
            response = requests.get(f"{self.ollama_base_url}/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                tinyllama_models = [model for model in models if "tinyllama" in model["name"].lower()]
                
                if tinyllama_models:
                    self.model_name = tinyllama_models[0]["name"]
                    logger.info(f"[TinyLlama] Found model: {self.model_name}")
                    return True
                else:
                    logger.warning("[TinyLlama] No TinyLlama model found in Ollama. Will attempt to pull.")
                    # Try to pull the model
                    self._pull_model()
            else:
                logger.error(f"[TinyLlama] Error checking models: {response.status_code} {response.text}")
                
        except Exception as e:
            logger.error(f"[TinyLlama] Error connecting to Ollama: {str(e)}")
            return False
    
    def _pull_model(self):
        """Pull the TinyLlama model from Ollama if not available"""
        try:
            logger.info("[TinyLlama] Attempting to pull tinyllama model from Ollama")
            response = requests.post(
                f"{self.ollama_base_url}/pull",
                json={"name": "tinyllama"}
            )
            
            if response.status_code == 200:
                logger.info("[TinyLlama] Successfully initiated model pull")
                return True
            else:
                logger.error(f"[TinyLlama] Failed to pull model: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"[TinyLlama] Error pulling model: {str(e)}")
            return False
    
    def _generate_text(self, prompt, system_prompt=None, params=None):
        """Generate text using TinyLlama via Ollama API"""
        try:
            # Merge default parameters with any provided parameters
            request_params = self.default_params.copy()
            if params:
                request_params.update(params)
            
            # Prepare the request
            request_data = {
                "model": self.model_name,
                "prompt": prompt,
                **request_params
            }
            
            # Add system prompt if provided
            if system_prompt:
                request_data["system"] = system_prompt
                
            # Make the request to Ollama
            response = requests.post(
                f"{self.ollama_base_url}/generate",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "status": "ok",
                    "generated_text": result.get("response", ""),
                    "tokens_used": result.get("eval_count", 0)
                }
            else:
                logger.error(f"[TinyLlama] Generation error: {response.status_code} {response.text}")
                return {
                    "status": "error",
                    "reason": f"API error: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"[TinyLlama] Generation exception: {str(e)}")
            return {
                "status": "error",
                "reason": str(e)
            }
    
    def handle_request(self, request):
        """Process incoming requests"""
        try:
            self.request_count += 1
            self.last_request_time = datetime.now()
            
            action = request.get("action", "generate")
            
            # Handle different types of requests
            if action == "generate":
                prompt = request.get("prompt", "")
                system_prompt = request.get("system_prompt")
                params = request.get("params", {})
                
                if not prompt:
                    return {"status": "error", "reason": "Missing prompt parameter"}
                
                logger.info(f"[TinyLlama] Generation request: {prompt[:50]}..." if len(prompt) > 50 else f"[TinyLlama] Generation request: {prompt}")
                return self._generate_text(prompt, system_prompt, params)
                
            elif action == "get_status":
                return {"status": "ok", **self.get_status()}
                
            elif action == "health_check":
                # Quick check if service and Ollama are responsive
                try:
                    response = requests.get(f"{self.ollama_base_url}/tags")
                    ollama_status = "ok" if response.status_code == 200 else "error"
                except:
                    ollama_status = "error"
                    
                return {
                    "status": "ok",
                    "service": "running",
                    "ollama": ollama_status,
                    "model": self.model_name
                }
            
            else:
                return {"status": "error", "reason": f"Unknown action: {action}"}
                
        except Exception as e:
            self.error_count += 1
            logger.error(f"[TinyLlama] Request handling error: {str(e)}")
            return {"status": "error", "reason": str(e)}
    
    def get_status(self):
        """Get service status information"""
        uptime = datetime.now() - self.start_time
        return {
            "status": "running" if self.running else "stopped",
            "model": self.model_name,
            "uptime_seconds": uptime.total_seconds(),
            "uptime_human": str(uptime),
            "request_count": self.request_count,
            "error_count": self.error_count,
            "last_request": self.last_request_time.isoformat() if self.last_request_time else None
        }
    
    def run(self):
        """Main service loop"""
        logger.info("[TinyLlama] Starting service loop")
        
        while self.running:
            try:
                # Wait for next request
                request_json = self.socket.recv_string()
                
                try:
                    request = json.loads(request_json)
                    response = self.handle_request(request)
                except json.JSONDecodeError:
                    response = {"status": "error", "reason": "Invalid JSON"}
                    self.error_count += 1
                except Exception as e:
                    response = {"status": "error", "reason": str(e)}
                    self.error_count += 1
                
                # Send response
                self.socket.send_string(json.dumps(response))
                
            except Exception as e:
                logger.error(f"[TinyLlama] Error in service loop: {str(e)}")
                try:
                    self.socket.send_string(json.dumps({"status": "error", "reason": str(e)}))
                except:
                    pass
    
    def stop(self):
        """Stop the service gracefully"""
        logger.info("[TinyLlama] Stopping service")
        self.running = False

def send_request(request, port=TINYLLAMA_SERVICE_PORT):
    """Helper function to send requests to TinyLlama service"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://localhost:{port}")
    
    socket.send_string(json.dumps(request))
    response = socket.recv_string()
    socket.close()
    
    return json.loads(response)

if __name__ == "__main__":
    service = TinyLlamaService()
    try:
        logger.info("[TinyLlama] Starting TinyLlama Service...")
        service.run()
    except KeyboardInterrupt:
        logger.info("[TinyLlama] Interrupted by user")
    except Exception as e:
        logger.error(f"[TinyLlama] Error: {str(e)}")
    finally:
        service.stop()
        logger.info("[TinyLlama] Service stopped")
