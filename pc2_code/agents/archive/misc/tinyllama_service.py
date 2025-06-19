"""
TinyLLama Service
- Provides access to the TinyLLama model via ZMQ
- Implements robust self-managed on-demand loading and idle unloading
- Reports accurate model status to Main PC MMA via health_check

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
sys.path.append(str(Path(__file__).resolve().parent.parent))

try:
    from config.system_config import get_config_for_service, get_config_for_machine
    SERVICE_ID = "tinyllama-service-pc2"
    service_config = get_config_for_service(SERVICE_ID)
    pc2_general_config = get_config_for_machine("pc2")

    LOG_LEVEL = pc2_general_config.get('log_level', 'INFO')
    LOGS_DIR = Path(pc2_general_config.get('logs_dir', 'logs'))
    CONFIG_ZMQ_PORT = service_config.get('zmq_port', 5615)
    CONFIG_ZMQ_BIND_ADDRESS = service_config.get('zmq_bind_address', "0.0.0.0")
    CONFIG_MODEL_PATH_OR_NAME = service_config.get('model_path_or_name', "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
    CONFIG_DEVICE = service_config.get('device', 'auto') # auto, cuda, cpu
    CONFIG_IDLE_TIMEOUT = service_config.get('idle_timeout_seconds_self', 300)

except ImportError:
    print("WARNING: Could not import system_config. Using default/hardcoded settings for TinyLlamaService.")
    LOG_LEVEL = 'INFO'
    LOGS_DIR = Path('logs')
    CONFIG_ZMQ_PORT = 5615
    CONFIG_ZMQ_BIND_ADDRESS = "0.0.0.0"
    CONFIG_MODEL_PATH_OR_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    CONFIG_DEVICE = 'auto'
    CONFIG_IDLE_TIMEOUT = 300

LOGS_DIR.mkdir(parents=True, exist_ok=True)
log_file_path = LOGS_DIR / "tinyllama_service.log"

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler(sys.stdout)  # Ensure console output
    ]
)
logger = logging.getLogger("TinyLlamaService")

logger.info(f"Imported config: Port={CONFIG_ZMQ_PORT}, Bind={CONFIG_ZMQ_BIND_ADDRESS}, Model={CONFIG_MODEL_PATH_OR_NAME}, Device={CONFIG_DEVICE}, IdleTimeout={CONFIG_IDLE_TIMEOUT}")

class TinyLlamaService:
    """Service for TinyLLama model with on-demand loading/unloading"""
    
    def __init__(self):
        # Initialize ZMQ
        self.context = zmq.Context()
        
        # Socket to handle requests
        self.socket = self.context.socket(zmq.REP)
        self.service_port = CONFIG_ZMQ_PORT
        self.bind_address = CONFIG_ZMQ_BIND_ADDRESS
        try:
            self.socket.bind(f"tcp://{self.bind_address}:{self.service_port}")
            logger.info(f"TinyLlama service bound to tcp://{self.bind_address}:{self.service_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Error binding to port {self.service_port} on address {self.bind_address}: {e}")
            # Attempt to bind to localhost as a fallback if 0.0.0.0 fails for some reason (e.g. restrictive env)
            if self.bind_address == "0.0.0.0":
                logger.warning(f"Attempting fallback bind to tcp://127.0.0.1:{self.service_port}")
                try:
                    self.socket.bind(f"tcp://127.0.0.1:{self.service_port}")
                    logger.info(f"TinyLlama service bound to FALLBACK tcp://127.0.0.1:{self.service_port}")
                    self.bind_address = "127.0.0.1"
                except zmq.error.ZMQError as e2:
                    logger.error(f"Fallback bind also failed: {e2}")
                    raise RuntimeError(f"Cannot bind to port {self.service_port}") from e2
            else:
                 raise RuntimeError(f"Cannot bind to port {self.service_port} on {self.bind_address}") from e
        
        # Initialize model and tokenizer as None (not loaded initially)
        self.model = None
        self.tokenizer = None
        
        # Model configuration
        self.model_name = CONFIG_MODEL_PATH_OR_NAME
        if CONFIG_DEVICE == 'auto':
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = CONFIG_DEVICE
        
        # Idle timeout settings
        self.last_request_time = time.time()
        self.service_idle_timeout_seconds = CONFIG_IDLE_TIMEOUT
        
        # Running flag
        self.running = True
        
        logger.info(f"TinyLlama Service initialized on {self.device}")
    
    def _load_model(self):
        try:
            if self.model is not None:
                logger.info("Model already loaded, skipping load.")
                return True
            
            logger.info(f"Starting model load for {self.model_name} on target device: {self.device}")
            
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            # Load tokenizer with logging
            logger.info(f"Loading tokenizer for {self.model_name}...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            logger.info("Tokenizer loaded successfully.")
            
            # Load model
            logger.info(f"Loading model {self.model_name} with explicit device_map='{self.device}' and torch_dtype=torch.float32...")
            # For single device (cuda or cpu), device_map should be self.device
            # For 'auto', transformers will handle it, but if we've resolved 'auto' to 'cuda' or 'cpu', we pass that directly.
            effective_device_map = self.device if self.device in ['cuda', 'cpu'] else 'auto'
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map=effective_device_map, # Use resolved device or 'auto'
                torch_dtype=torch.float32
            )
            logger.info(f"Model {self.model_name} loaded. Effective device map: {self.model.device}")
            
            return True
        except Exception as e:
            logger.error(f"Error loading TinyLlama model: {str(e)}")
            logger.error(f"Detailed traceback: {traceback.format_exc()}")
            self.model = None
            self.tokenizer = None
            return False
    
    def _unload_model(self):
        """Unload the TinyLlama model and tokenizer from memory"""
        if self.model is None:
            logger.info("Model already unloaded")
            return True
        
        try:
            logger.info("Unloading TinyLlama model")
            
            # Delete model and tokenizer
            del self.model
            del self.tokenizer
            self.model = None
            self.tokenizer = None
            
            # Clear CUDA cache if available
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            logger.info("TinyLlama model unloaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error unloading TinyLlama model: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def generate_text(self, prompt, max_tokens=100):
        """Generate text using the TinyLlama model with on-demand loading"""
        try:
            # On-demand loading if model is not loaded
            if self.model is None:
                logger.info("On-demand loading of model for text generation request")
                success = self._load_model()
                if not success:
                    return {"status": "error", "message": "Failed to load model"}
            
            # Update last request time to prevent idle unloading during active use
            self.last_request_time = time.time()
            
            # Format chat prompt for TinyLlama
            formatted_prompt = f"<human>: {prompt}\n<assistant>: "
            
            # Tokenize input
            inputs = self.tokenizer(formatted_prompt, return_tensors="pt").to(self.device)
            
            # Generate text
            with torch.no_grad():
                output = self.model.generate(
                    inputs["input_ids"],
                    max_new_tokens=max_tokens,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.9,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode the generated text
            generated_text = self.tokenizer.decode(output[0], skip_special_tokens=True)
            
            # Extract only the assistant's response
            assistant_response = generated_text.split("<assistant>: ")[-1].strip()
            
            return {"status": "success", "text": assistant_response}
        except Exception as e:
            logger.error(f"Error generating text: {e}")
            logger.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}
    
    def _check_idle_timeout(self):
        """Check if the model has been idle for too long and unload if needed"""
        if self.model is None:
            return  # Model already unloaded
        
        idle_time = time.time() - self.last_request_time
        if idle_time > self.service_idle_timeout_seconds:
            logger.info(f"Self-managed unloading: Model idle for {idle_time:.1f} seconds, unloading (timeout: {self.service_idle_timeout_seconds}s)")
            self._unload_model()
    
    def _idle_monitoring_thread(self):
        """Thread that monitors model idle time and unloads when needed"""
        logger.info("Starting idle monitoring thread")
        while self.running:
            try:
                self._check_idle_timeout()
            except Exception as e:
                logger.error(f"Error in idle monitoring thread: {e}")
            
            # Check every 5 seconds
            time.sleep(5)
    
    def handle_requests(self):
        """Handle incoming ZMQ requests"""
        while self.running:
            try:
                # Use a timeout to allow checking for shutdown
                if self.socket.poll(1000) == 0:  # 1 second timeout
                    continue
                
                # Receive request
                request_str = self.socket.recv_string()
                
                # Get peer information if available
                peer_info = "unknown peer"
                try:
                    # Get last endpoint information
                    last_endpoint = self.socket.get_last_endpoint().decode('utf-8')
                    peer_info = f"endpoint: {last_endpoint}"
                except Exception as e:
                    logger.debug(f"Could not get peer info: {e}")
                
                logger.info(f"Received request from {peer_info}: {request_str}")
                
                try:
                    request = json.loads(request_str)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in request: {request_str}")
                    self.socket.send_string(json.dumps({
                        "status": "error",
                        "message": "Invalid JSON in request"
                    }))
                    continue
                
                # Process request based on action
                action = request.get("action", "")
                
                if action == "generate":
                    # Handle text generation request
                    prompt = request.get("prompt", "")
                    max_tokens = int(request.get("max_tokens", 100))
                    
                    response = self.generate_text(prompt, max_tokens)
                    self.socket.send_string(json.dumps(response))
                
                elif action == "ensure_loaded":
                    # Handle model loading request
                    if self.model is None:
                        success = self._load_model()
                        if success:
                            response = {
                                "status": "success",
                                "message": "Model loaded successfully",
                                "success": True
                            }
                        else:
                            response = {
                                "status": "error",
                                "message": "Failed to load model",
                                "success": False
                            }
                    else:
                        # Model already loaded, update last request time
                        self.last_request_time = time.time()
                        response = {
                            "status": "success",
                            "message": "Model already loaded",
                            "success": True
                        }
                    
                    self.socket.send_string(json.dumps(response))
                
                elif action == "request_unload":
                    # Handle model unloading request
                    if self.model is not None:
                        success = self._unload_model()
                        if success:
                            response = {
                                "status": "success",
                                "message": "Model unloaded successfully",
                                "success": True
                            }
                        else:
                            response = {
                                "status": "error",
                                "message": "Failed to unload model",
                                "success": False
                            }
                    else:
                        # Model already unloaded
                        response = {
                            "status": "success",
                            "message": "Model already unloaded",
                            "success": True
                        }
                    
                    self.socket.send_string(json.dumps(response))
                
                elif action == "health_check":
                    # Enhanced health check with accurate model status for Main PC MMA
                    model_status = "loaded" if self.model else "unloaded"
                    idle_time = time.time() - self.last_request_time if self.model else 0
                    
                    logger.info(f"HEALTH CHECK: Current model_status: {model_status}, idle_time: {round(idle_time, 2)}s, self_managed: True")
                    
                    response = {
                        "status": "ok",
                        "service": "tinyllama_service",
                        "model_status": model_status,  # Critical for Main PC MMA status monitoring
                        "is_loaded": self.model is not None,
                        "idle_time": round(idle_time, 2),
                        "idle_timeout": self.service_idle_timeout_seconds,
                        "timestamp": time.time(),
                        "device": self.device,
                        "self_managed": True  # Indicates this service manages its own loading/unloading
                    }
                    
                    logger.info(f"HEALTH CHECK RESPONSE: {json.dumps(response)}")
                    
                    self.socket.send_string(json.dumps(response))
                
                else:
                    # Unknown action
                    self.socket.send_string(json.dumps({
                        "status": "error",
                        "message": f"Unknown action: {action}"
                    }))
            
            except zmq.error.Again:
                # Socket timeout, continue
                continue
            except Exception as e:
                logger.error(f"Error handling request: {e}")
                logger.error(traceback.format_exc())
                
                # Try to send error response
                try:
                    self.socket.send_string(json.dumps({
                        "status": "error",
                        "message": f"Internal server error: {str(e)}"
                    }))
                except:
                    pass
    
    def run(self):
        """Run the TinyLlama service"""
        try:
            # Start idle monitoring thread
            idle_thread = threading.Thread(target=self._idle_monitoring_thread)
            idle_thread.daemon = True
            idle_thread.start()
            
            logger.info("TinyLlama service started")
            
            # Handle requests
            self.handle_requests()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down")
        except Exception as e:
            logger.error(f"Error in TinyLlama service: {e}")
            logger.error(traceback.format_exc())
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources")
        self.running = False
        
        # Unload model
        if self.model is not None:
            self._unload_model()
        
        # Close ZMQ socket
        self.socket.close()
        self.context.term()
        
        logger.info("TinyLlama service shut down")


if __name__ == "__main__":
    try:
        # Create necessary directories
        Path("logs").mkdir(exist_ok=True)
        
        # Start the service
        service = TinyLlamaService()
        service.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
