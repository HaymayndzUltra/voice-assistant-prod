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
from datetime import datetime

# Add project root to Python path for common_utils import
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

# Import BaseAgent for standardized agent implementation
from common.core.base_agent import BaseAgent

ZMQ_REQUEST_TIMEOUT = 5000  # Socket timeout in milliseconds

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))
from main_pc_code.config.system_config import config
from main_pc_code.utils.config_loader import load_config

# Parse agent arguments for standardized configuration
config = load_config()

# ZMQ Configuration
ZMQ_BIND_ADDRESS = "0.0.0.0"  # Listen on all interfaces
PC2_IP = "192.168.100.17"  # PC2's IP address
MAIN_PC_IP = "192.168.100.16"  # Main PC's IP address

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
    """Model state enum."""
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

# Resource management config (should be loaded from config in production)
DEFAULT_BATCH_SIZE = 8
MAX_BATCH_SIZE = 16
ENABLE_DYNAMIC_QUANTIZATION = True
TENSORRT_ENABLED = False  # Placeholder for future TensorRT integration

class ResourceManager:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.memory_threshold = 0.9  # 90% memory usage threshold
        self.vram_threshold = 0.9 if self.device == "cuda" else None
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
        self.default_batch_size = DEFAULT_BATCH_SIZE
        self.max_batch_size = MAX_BATCH_SIZE
        self.enable_dynamic_quantization = ENABLE_DYNAMIC_QUANTIZATION
    
    def get_stats(self) -> Dict:
        """Get current resource statistics"""
        stats = {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'memory_available': psutil.virtual_memory().available,
            'device': self.device,
            'timestamp': time.time()
        }
        
        if self.device == "cuda":
            stats.update({
                'cuda_memory_allocated': torch.cuda.memory_allocated(),
                'cuda_memory_reserved': torch.cuda.memory_reserved(),
                'cuda_memory_cached': torch.cuda.memory_cached(),
                'cuda_device_count': torch.cuda.device_count(),
                'cuda_device_name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
            })
        
        return stats
    
    def check_resources(self) -> bool:
        """Check if resources are available for model loading"""
        # Check system memory
        if psutil.virtual_memory().percent > self.memory_threshold * 100:
            logger.warning("System memory usage too high")
            return False
        
        # Check GPU memory if available
        if self.device == "cuda":
            allocated = torch.cuda.memory_allocated()
            total = torch.cuda.get_device_properties(0).total_memory
            if allocated / total > self.vram_threshold:
                logger.warning("GPU memory usage too high")
                return False
        
        # Periodic cleanup
        if time.time() - self.last_cleanup > self.cleanup_interval:
            self.cleanup()
            self.last_cleanup = time.time()
        
        return True
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("Performing resource cleanup")
        if self.device == "cuda":
            torch.cuda.empty_cache()
        gc.collect()
        logger.info("Resource cleanup completed")

    def get_system_load(self):
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        try:
            import torch
            gpu = torch.cuda.memory_allocated() / torch.cuda.max_memory_allocated() * 100
        except ImportError as e:
            print(f"Import error: {e}")
            gpu = 0
        except Exception:
            gpu = 0
        return cpu, mem, gpu

    def get_batch_size(self):
        cpu, mem, gpu = self.get_system_load()
        if max(cpu, mem, gpu) > 80:
            return max(1, self.default_batch_size // 2)
        elif max(cpu, mem, gpu) < 40:
            return min(self.max_batch_size, self.default_batch_size * 2)
        else:
            return self.default_batch_size

    def get_quantization(self):
        if not self.enable_dynamic_quantization:
            return 'float16'
        cpu, mem, gpu = self.get_system_load()
        if max(cpu, mem, gpu) > 80:
            return 'int8'
        else:
            return 'float16'

    def use_tensorrt(self):
        return TENSORRT_ENABLED

class TinyLlamaService(BaseAgent):
    """Enhanced TinyLlama Service with resource management"""
    
    def _start_health_check(self):
        """Start health check thread."""
        self.health_thread = threading.Thread(target=self._health_check_loop)
        self.health_thread.daemon = True
        self.health_thread.start()
        logger.info("Health check thread started")
    
    def _health_check_loop(self):
        """Background loop to handle health check requests."""
        logger.info("Health check loop started")
        
        while self.running:
            try:
                # Check for health check requests with timeout
                if self.health_socket.poll(100, zmq.POLLIN):
                    # Receive request (don't care about content)
                    _ = self.health_socket.recv()
                    
                    # Get health data
                    health_data = self._get_health_status()
                    
                    # Send response
                    self.health_socket.send_json(health_data)
                
                time.sleep(0.1)  # Small sleep to prevent CPU hogging
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(1)
    
    def __init__(self, port: int = None, name: str = None, **kwargs):
        # Standardized port and name handling with fallback to 5615 for port
        agent_port = config.get("port", 5615) if port is None else port
        agent_name = config.get("name", 'TinyLlamaService') if name is None else name
        health_check_port = config.get("health_check_port", 6615)
        super().__init__(port=agent_port, name=agent_name, health_check_port=health_check_port)
        
        logger.info("=" * 80)
        logger.info("Initializing Enhanced TinyLlama Service")
        logger.info("=" * 80)
        
        # Initialize managers
        self.resource_manager = ResourceManager()
        self.model_state = ModelState.UNLOADED
        
        # Setup error reporting
        self.error_bus_port = config.get("error_bus_port", 7150)
        self.error_bus_host = os.environ.get('PC2_IP', config.get("pc2_ip", '192.168.100.17'))
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.connect(self.error_bus_endpoint)
        
        # Model configuration
        self.model_name = config.get("model_name", "/mnt/c/Users/haymayndz/Desktop/Voice assistant/models/gguf/tinyllama-1.1b-chat-v1.0.Q4_0.gguf")
        self.model = None
        self.tokenizer = None
        
        # Generation configuration
        self.default_config = GenerationConfig()
        
        # Idle timeout settings
        self.last_request_time = time.time()
        self.service_idle_timeout_seconds = config.get(
            'model_configs.tinylama-service-zmq.idle_timeout_seconds', 30
        )
        
        # Start health check
        self.running = True
        self._start_health_check()
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info(f"Enhanced TinyLlama Service initialized on {self.resource_manager.device}")
        logger.info(f"Model name: {self.model_name}")
        logger.info(f"Idle timeout: {self.service_idle_timeout_seconds} seconds")
        logger.info("=" * 80)
    
    def report_error(self, error_message, severity="WARNING", context=None):
        """Report an error to the error bus"""
        try:
            error_data = {
                "source": self.name,
                "timestamp": datetime.utcnow().isoformat(),
                "severity": severity,
                "message": error_message,
                "context": context or {}
            }
            self.error_bus_pub.send_string(f"ERROR:{json.dumps(error_data)}")
            logger.error(f"Reported error: {error_message}")
        except Exception as e:
            logger.error(f"Failed to report error to error bus: {e}")

    def _get_health_status(self) -> Dict[str, Any]:
        """Override BaseAgent's health status to include TinyLlamaService-specific info."""
        base_status = super()._get_health_status()
        base_status.update({
            "service": "tinyllama_service",
            "model_state": self.model_state.value,
            "resource_stats": self.resource_manager.get_stats()
        })
        return base_status
    
    def _setup_zmq_socket(self):
        """Setup ZMQ socket with proper configuration"""
        # BaseAgent already initialized the main socket in super().__init__()
        # This method is kept for compatibility but doesn't need to do anything
        pass
    
    def _load_model(self) -> bool:
        """Load the TinyLlama model with resource checks"""
        if self.model_state == ModelState.LOADED:
            return True
        
        if not self.resource_manager.check_resources():
            logger.warning("Insufficient resources for model loading")
            self.report_error("Insufficient resources for model loading")
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
            self.report_error(f"Error loading TinyLlama model: {e}")
            self.model_state = ModelState.ERROR
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
        """Monitor system resources and model state"""
        while self.running:
            try:
                # Check if model should be unloaded due to idle timeout
                if (self.model_state == ModelState.LOADED and 
                    time.time() - self.last_request_time > self.service_idle_timeout_seconds):
                    logger.info("Model idle timeout reached, unloading model")
                    self._unload_model()
                
                time.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
                time.sleep(1)
    
    def handle_request(self, request: Dict) -> Dict:
        """Handle incoming requests"""
        try:
            action = request.get('action')
            if not action:
                return {'error': 'No action specified'}
            
            # Handle health check using BaseAgent's implementation
            if action in ['health', 'health_check', 'ping']:
                return self._get_health_status()
            
            elif action == 'generate':
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
        
        # Wait for monitoring thread to finish
        if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
            logger.info("Monitor thread joined")
        
        # Wait for health check thread to finish
        if hasattr(self, 'health_thread') and self.health_thread.is_alive():
            self.health_thread.join(timeout=2.0)
            logger.info("Health check thread joined")
        
        # Close error bus socket
        if hasattr(self, 'error_bus_pub'):
            try:
                self.error_bus_pub.close()
                logger.info("Closed error bus connection")
            except Exception as e:
                logger.error(f"Error closing error bus connection: {e}")
        
        # Unload model if loaded
        self._unload_model()
        
        # Call BaseAgent's cleanup to handle the main socket and health socket
        super().cleanup()
        
        logger.info("TinyLlama Service cleanup completed")

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        # Instantiate the agent. Its __init__ will now use _agent_args.
        agent = TinyLlamaService()
        agent.run() # Assuming a standard run() method exists
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()