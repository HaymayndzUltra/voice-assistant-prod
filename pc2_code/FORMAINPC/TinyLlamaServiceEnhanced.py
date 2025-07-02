"""
TinyLLama Service
- Provides access to the TinyLLama model via ZMQ
- Supports on-demand loading/unloading for VRAM management
- Compatible with the ModelManagerAgent (MMA) for orchestration
- Enhanced resource management and generation handling

Request Format:
- For text generation: {"action": "generate", "prompt": "Your prompt here", "max_tokens": 100}
- For loading model: {"action": "ensure_loaded"}
- For unloading model: {"action": "request_unload"}
- For health check: {"action": "health_check"}
- For resource stats: {"action": "resource_stats"}

Response Format:
- For generation: {"status": "success", "text": "Generated text"}
- For load/unload: {"status": "success", "message": "Model loaded/unloaded"}
- For health check: {"status": "ok", "service": "tinyllama_service", 
                    "model_status": "loaded" or "unloaded", "timestamp": time.time()}
- For resource stats: {"status": "success", "stats": {...}}
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
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from enum import Enum
import psutil
import gc

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))
from pc2_code.config.system_config import config

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

class ModelState(Enum):
    """Model state enum"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    UNLOADING = "unloading"
    ERROR = "error"

@dataclass
class GenerationConfig:
    """Generation configuration"""
    max_tokens: int = 100
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.1
    do_sample: bool = True

class ResourceManager:
    """Manages system resources"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.memory_threshold = 0.9  # 90% memory usage threshold
        self.vram_threshold = 0.9 if self.device == "cuda" else None
    
    def get_stats(self) -> Dict:
        """Get current resource statistics"""
        stats = {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'memory_available': psutil.virtual_memory().available,
            'device': self.device
        }
        
        if self.device == "cuda":
            stats.update({
                'cuda_memory_allocated': torch.cuda.memory_allocated(),
                'cuda_memory_reserved': torch.cuda.memory_reserved(),
                'cuda_memory_cached': torch.cuda.memory_cached()
            })
        
        return stats
    
    def check_resources(self) -> bool:
        """Check if resources are available for model loading"""
        if psutil.virtual_memory().percent > self.memory_threshold * 100:
            return False
        
        if self.device == "cuda":
            if torch.cuda.memory_allocated() / torch.cuda.get_device_properties(0).total_memory > self.vram_threshold:
                return False
        
        return True
    
    def cleanup(self):
        """Cleanup resources"""
        if self.device == "cuda":
            torch.cuda.empty_cache()
        gc.collect()

class TinyLlamaService:
    """Enhanced TinyLlama Service with resource management"""
    
    def __init__(self):
        logger.info("=" * 80)
        logger.info("Initializing Enhanced TinyLlama Service")
        logger.info("=" * 80)
        
        # Initialize ZMQ
        self.context = zmq.Context()
        self._setup_zmq_socket()
        
        # Initialize managers
        self.resource_manager = ResourceManager()
        self.model_state = ModelState.UNLOADED
        
        # Model configuration
        self.model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        self.model = None
        self.tokenizer = None
        
        # Generation configuration
        self.default_config = GenerationConfig()
        
        # Idle timeout settings
        self.last_request_time = time.time()
        self.service_idle_timeout_seconds = config.get(
            'model_configs.tinylama-service-zmq.idle_timeout_seconds', 30
        )
        
        # Running flag
        self.running = True
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info(f"Enhanced TinyLlama Service initialized on {self.resource_manager.device}")
        logger.info(f"Model name: {self.model_name}")
        logger.info(f"Idle timeout: {self.service_idle_timeout_seconds} seconds")
        logger.info("=" * 80)
    
    def _setup_zmq_socket(self):
        """Setup ZMQ socket"""
        self.socket = self.context.socket(zmq.REP)
        self.service_port = config.get('model_configs.tinylama-service-zmq.zmq_port', 5615)
        try:
            self.socket.bind(f"tcp://0.0.0.0:{self.service_port}")
            logger.info(f"TinyLlama service bound to port {self.service_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Error binding to port {self.service_port}: {e}")
            raise RuntimeError(f"Cannot bind to port {self.service_port}") from e
    
    def _load_model(self) -> bool:
        """Load the TinyLlama model with resource checks"""
        if self.model_state == ModelState.LOADED:
            return True
        
        if not self.resource_manager.check_resources():
            logger.warning("Insufficient resources for model loading")
            return False
        
        try:
            self.model_state = ModelState.LOADING
            logger.info(f"Loading TinyLlama model from {self.model_name}")
            
            # Import here to avoid loading transformers at startup
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            # Load model with appropriate settings
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.resource_manager.device == "cuda" else torch.float32,
                low_cpu_mem_usage=True,
                ignore_mismatched_sizes=True
            )
            
            # Move model to device
            self.model.to(self.resource_manager.device)
            
            self.model_state = ModelState.LOADED
            logger.info("TinyLlama model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading TinyLlama model: {e}")
            self.model_state = ModelState.ERROR
            self._cleanup_resources()
            return False
    
    def _unload_model(self) -> bool:
        """Unload the TinyLlama model with resource cleanup"""
        if self.model_state == ModelState.UNLOADED:
            return True
        
        try:
            self.model_state = ModelState.UNLOADING
            logger.info("Unloading TinyLlama model")
            
            # Delete model and tokenizer
            del self.model
            del self.tokenizer
            self.model = None
            self.tokenizer = None
            
            # Cleanup resources
            self.resource_manager.cleanup()
            
            self.model_state = ModelState.UNLOADED
            logger.info("TinyLlama model unloaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error unloading TinyLlama model: {e}")
            self.model_state = ModelState.ERROR
            return False
    
    def generate_text(self, prompt: str, config: Optional[GenerationConfig] = None) -> Dict:
        """Generate text with enhanced error handling"""
        try:
            if self.model_state != ModelState.LOADED:
                if not self._load_model():
                    return {"status": "error", "message": "Failed to load model"}
            
            # Update last request time
            self.last_request_time = time.time()
            
            # Use provided config or default
            gen_config = config or self.default_config
            
            # Format chat prompt
            formatted_prompt = f"<human>: {prompt}\n<assistant>: "
            
            # Tokenize input
            inputs = self.tokenizer(formatted_prompt, return_tensors="pt").to(self.resource_manager.device)
            
            # Generate text
            with torch.no_grad():
                output = self.model.generate(
                    inputs["input_ids"],
                    max_new_tokens=gen_config.max_tokens,
                    do_sample=gen_config.do_sample,
                    temperature=gen_config.temperature,
                    top_p=gen_config.top_p,
                    top_k=gen_config.top_k,
                    repetition_penalty=gen_config.repetition_penalty,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode and extract response
            generated_text = self.tokenizer.decode(output[0], skip_special_tokens=True)
            assistant_response = generated_text.split("<assistant>: ")[-1].strip()
            
            return {
                "status": "success",
                "text": assistant_response,
                "config": {
                    "max_tokens": gen_config.max_tokens,
                    "temperature": gen_config.temperature,
                    "top_p": gen_config.top_p
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating text: {e}")
            return {"status": "error", "message": str(e)}
    
    def _monitor_resources(self):
        """Monitor system resources"""
        while self.running:
            try:
                stats = self.resource_manager.get_stats()
                if not self.resource_manager.check_resources():
                    logger.warning("Resource usage high, unloading model")
                    self._unload_model()
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
            time.sleep(5)
    
    def handle_request(self, request: Dict) -> Dict:
        """Handle incoming requests"""
        try:
            action = request.get('action')
            if not action:
                return {'error': 'No action specified'}
            
            if action == 'generate':
                return self.generate_text(
                    request['prompt'],
                    GenerationConfig(
                        max_tokens=request.get('max_tokens', self.default_config.max_tokens),
                        temperature=request.get('temperature', self.default_config.temperature),
                        top_p=request.get('top_p', self.default_config.top_p)
                    )
                )
            elif action == 'ensure_loaded':
                success = self._load_model()
                return {
                    'status': 'success' if success else 'error',
                    'message': 'Model loaded' if success else 'Failed to load model'
                }
            elif action == 'request_unload':
                success = self._unload_model()
                return {
                    'status': 'success' if success else 'error',
                    'message': 'Model unloaded' if success else 'Failed to unload model'
                }
            elif action == 'health_check':
                return {
                    'status': 'ok',
                    'service': 'tinyllama_service',
                    'model_status': self.model_state.value,
                    'timestamp': time.time()
                }
            elif action == 'resource_stats':
                return {
                    'status': 'success',
                    'stats': self.resource_manager.get_stats()
                }
            else:
                return {'error': f'Unknown action: {action}'}
                
        except Exception as e:
            logger.error(f"Request handling error: {e}")
            return {'error': str(e)}
    
    def run(self):
        """Run the service"""
        try:
            logger.info("Starting TinyLlama Service...")
            while self.running:
                try:
                    request = self.socket.recv_json()
                    response = self.handle_request(request)
                    self.socket.send_json(response)
                except zmq.error.Again:
                    continue
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    self.socket.send_json({'error': str(e)})
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        self.running = False
        self._unload_model()
        self.socket.close()
        self.context.term()

def main():
    """Main entry point"""
    service = TinyLlamaService()
    service.run()

if __name__ == "__main__":
    main()
