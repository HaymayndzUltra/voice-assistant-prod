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
from config.system_config import config

# Configure logging
log_level = config.get('system.log_level', 'INFO')
log_file = Path(config.get('system.logs_dir', 'logs')) / "tinyllama_service.log"
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TinyLlamaService")

class TinyLlamaService:
    """Service for TinyLLama model with on-demand loading/unloading"""
    
    def __init__(self):
        logger.info("=" * 80)
        logger.info("Initializing TinyLlama Service")
        logger.info("=" * 80)
        
        # Initialize ZMQ
        self.context = zmq.Context()
        
        # Socket to handle requests
        self.socket = self.context.socket(zmq.REP)
        self.service_port = config.get('model_configs.tinylama-service-zmq.zmq_port', 5615)
        try:
            self.socket.bind(f"tcp://0.0.0.0:{self.service_port}")
            logger.info(f"TinyLlama service bound to port {self.service_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Error binding to port {self.service_port}: {e}")
            raise RuntimeError(f"Cannot bind to port {self.service_port}") from e
        
        # Initialize model and tokenizer as None (not loaded initially)
        self.model = None
        self.tokenizer = None
        
        # Model configuration
        self.model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Idle timeout settings
        self.last_request_time = time.time()
        self.service_idle_timeout_seconds = config.get(
            'model_configs.tinylama-service-zmq.idle_timeout_seconds', 30
        )
        
        # Running flag
        self.running = True
        
        # Record start time for uptime tracking
        self.start_time = time.time()
        
        logger.info(f"TinyLlama Service initialized on {self.device}")
        logger.info(f"Model name: {self.model_name}")
        logger.info(f"Idle timeout: {self.service_idle_timeout_seconds} seconds")
        logger.info("=" * 80)
    
    def _load_model(self):
        """Load the TinyLlama model and tokenizer into memory"""
        try:
            if self.model is not None:
                logger.info("Model already loaded")
                return True
            
            logger.info(f"Loading TinyLlama model from {self.model_name}")
            logger.info(f"Device: {self.device}")
            
            # Import here to avoid loading transformers at startup
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            # Load tokenizer
            logger.info("Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            logger.info("Tokenizer loaded successfully")
            
            # Check if accelerate is available
            try:
                import accelerate
                accelerate_available = True
                logger.info("Accelerate package found, will use low_cpu_mem_usage")
            except ImportError:
                accelerate_available = False
                logger.info("Accelerate package not found, continuing without low_cpu_mem_usage")
                
            # Load model with appropriate settings based on accelerate availability
            logger.info("Loading model...")
            if accelerate_available:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    low_cpu_mem_usage=True,
                    ignore_mismatched_sizes=True
                )
            else:
                # Without accelerate, don't use low_cpu_mem_usage
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    ignore_mismatched_sizes=True
                )
            
            # Move model to device
            logger.info(f"Moving model to {self.device}...")
            self.model.to(self.device)
            
            logger.info("TinyLlama model loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error loading TinyLlama model: {e}")
            logger.error(traceback.format_exc())
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
        """Generate text using the TinyLlama model"""
        try:
            logger.info(f"Received generation request - max_tokens: {max_tokens}")
            
            # Load model if not loaded
            if self.model is None:
                logger.info("Model not loaded, attempting to load...")
                success = self._load_model()
                if not success:
                    logger.error("Failed to load model for generation")
                    return {"status": "error", "message": "Failed to load model"}
            
            # Update last request time
            self.last_request_time = time.time()
            
            # Format chat prompt for TinyLlama
            formatted_prompt = f"<human>: {prompt}\n<assistant>: "
            logger.debug(f"Formatted prompt: {formatted_prompt}")
            
            # Tokenize input
            logger.debug("Tokenizing input...")
            inputs = self.tokenizer(formatted_prompt, return_tensors="pt").to(self.device)
            
            # Generate text
            logger.info("Generating text...")
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
            logger.debug("Decoding generated text...")
            generated_text = self.tokenizer.decode(output[0], skip_special_tokens=True)
            
            # Extract only the assistant's response
            assistant_response = generated_text.split("<assistant>: ")[-1].strip()
            
            logger.info("Text generation completed successfully")
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
            logger.info(f"Model idle for {idle_time:.1f} seconds, unloading (timeout: {self.service_idle_timeout_seconds}s)")
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
                logger.debug(f"Received request: {request_str}")
                
                try:
                    request = json.loads(request_str)
                except json.JSONDecodeError:
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
                    # Handle health check request
                    logger.info("Received health check request")
                    model_status = "loaded" if self.model is not None else "unloaded"
                    response = {
                        "status": "ok",
                        "service": "tinyllama_service",
                        "model_status": model_status,
                        "timestamp": time.time(),
                        "device": self.device,
                        "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else 0
                    }
                    logger.info(f"Health check response: {json.dumps(response)}")
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
