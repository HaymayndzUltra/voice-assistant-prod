"""
NLLB Translation Adapter (Self-Managed)
- Provides access to the NLLB translation model via ZMQ.
- Implements self-managed on-demand loading and idle unloading.
- Intended for direct calls from other services (e.g., TranslatorAgent) on the same machine.

Request Format (Only 'translate' action is supported):
- For translation: {"action": "translate", "text": "Text to translate", "source_lang": "tgl_Latn", "target_lang": "eng_Latn"}

Response Format:
- For translation: {"status": "success", "translated_text": "Translated text"}
                 or {"status": "error", "message": "Error details"}
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
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import psutil
from datetime import datetime
from common.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config
from main_pc_code.utils.network_utils import get_zmq_connection_string, get_machine_ip

# Load configuration
config = load_config()

# Timeout for ZeroMQ send/recv operations (milliseconds)
ZMQ_REQUEST_TIMEOUT = config.get("zmq_request_timeout", 5000)  # 5 seconds

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Configuration settings - use config with fallbacks
LOG_LEVEL = config.get("log_level", 'INFO')
LOGS_DIR = Path(config.get("logs_dir", 'logs'))
CONFIG_ZMQ_PORT = config.get("nllb_zmq_port", 5581)
CONFIG_ZMQ_BIND_ADDRESS = config.get("nllb_zmq_bind_address", "0.0.0.0")
CONFIG_MODEL_PATH_OR_NAME = config.get("nllb_model_path", "facebook/nllb-200-distilled-600M")
CONFIG_DEVICE = config.get("nllb_device", 'auto')
CONFIG_IDLE_TIMEOUT = config.get("nllb_idle_timeout", 3600)

# Try to load config from environment variables if available
if 'LOG_LEVEL' in os.environ:
    LOG_LEVEL = os.environ['LOG_LEVEL']
if 'LOGS_DIR' in os.environ:
    LOGS_DIR = Path(os.environ['LOGS_DIR'])
if 'NLLB_ZMQ_PORT' in os.environ:
    CONFIG_ZMQ_PORT = int(os.environ['NLLB_ZMQ_PORT'])
if 'NLLB_ZMQ_BIND_ADDRESS' in os.environ:
    CONFIG_ZMQ_BIND_ADDRESS = os.environ['NLLB_ZMQ_BIND_ADDRESS']
if 'NLLB_MODEL_PATH' in os.environ:
    CONFIG_MODEL_PATH_OR_NAME = os.environ['NLLB_MODEL_PATH']
if 'NLLB_DEVICE' in os.environ:
    CONFIG_DEVICE = os.environ['NLLB_DEVICE']
if 'NLLB_IDLE_TIMEOUT' in os.environ:
    CONFIG_IDLE_TIMEOUT = int(os.environ['NLLB_IDLE_TIMEOUT'])

LOGS_DIR.mkdir(parents=True, exist_ok=True)
log_file_path = LOGS_DIR / "nllb_translation_adapter.log"

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler(sys.stdout)  # Ensure console output
    ]
)
logger = logging.getLogger("NLLBTranslationAdapter")

logger.info(f"Configuration: Port={CONFIG_ZMQ_PORT}, Bind={CONFIG_ZMQ_BIND_ADDRESS}, Model={CONFIG_MODEL_PATH_OR_NAME}, Device={CONFIG_DEVICE}, IdleTimeout={CONFIG_IDLE_TIMEOUT}")

MODEL_IDLE_TIMEOUT = config.get("model_idle_timeout", 600)  # seconds
model_last_used = 0

# Resource management config (should be loaded from config in production)
DEFAULT_BATCH_SIZE = config.get("default_batch_size", 8)
MAX_BATCH_SIZE = config.get("max_batch_size", 16)
ENABLE_DYNAMIC_QUANTIZATION = config.get("enable_dynamic_quantization", True)
TENSORRT_ENABLED = config.get("tensorrt_enabled", False)  # Placeholder for future TensorRT integration

class NLLBTranslationAdapter(BaseAgent):
    """Service for NLLB translation model with self-managed on-demand loading/unloading."""
    
    def __init__(self):
        # Call BaseAgent's __init__ first
        super().__init__(name="NLLBTranslationAdapter", port=CONFIG_ZMQ_PORT, health_check_port=CONFIG_ZMQ_PORT+1)

        # Initialize logger
        self.logger = logging.getLogger("NLLBTranslationAdapter")
        
        # Initialize ZMQ
        self.context = zmq.Context()
        
        # Socket to handle requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.service_port = CONFIG_ZMQ_PORT
        self.bind_address = CONFIG_ZMQ_BIND_ADDRESS
        
        # Error bus setup
        self.error_bus_port = config.get("error_bus_port", 7150)
        self.error_bus_endpoint = get_zmq_connection_string(self.error_bus_port, "pc2")
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.connect(self.error_bus_endpoint)
        
        # Socket binding will be handled below with retry/fallback logic to avoid duplicate bind attempts
        
        # Health monitoring
        self.health_status = {
            "status": "ok",
            "service": "nllb_translation_adapter",
            "model_state": "unloaded",
            "last_check": time.time(),
            "resource_stats": {
                "device": None,
                "memory_usage": None,
                "gpu_memory": None
            }
        }
        
        # Language code mapping
        self.language_code_mapping = {
            'fil_Latn': 'tgl_Latn'  # Map Filipino to Tagalog
        }
        
        try:
            bind_endpoint = get_zmq_connection_string(self.service_port, "bind", self.bind_address)
            self.socket.bind(bind_endpoint)
            self.logger.info(f"NLLB Translation Adapter bound to {bind_endpoint}")
        except zmq.error.ZMQError as e:
            self.logger.error(f"Error binding to port {self.service_port} on address {self.bind_address}: {e}")
            self.report_error(f"Error binding to port {self.service_port} on address {self.bind_address}: {e}")
            if self.bind_address == "0.0.0.0":
                self.logger.warning(f"Attempting fallback bind to localhost")
                try:
                    fallback_endpoint = get_zmq_connection_string(self.service_port, "bind", "127.0.0.1")
                    self.socket.bind(fallback_endpoint)
                    self.logger.info(f"NLLB Translation Adapter bound to FALLBACK {fallback_endpoint}")
                    self.bind_address = "127.0.0.1"
                except zmq.error.ZMQError as e2:
                    self.logger.error(f"Fallback bind also failed: {e2}")
                    self.report_error(f"Fallback bind also failed: {e2}")
                    raise RuntimeError(f"Cannot bind to port {self.service_port}") from e2
            else:
                raise RuntimeError(f"Cannot bind to port {self.service_port} on {self.bind_address}") from e
        
        # Initialize health check socket
        self.name = "NLLBTranslationAdapter"
        self.start_time = time.time()
        self.health_port = self.service_port + 1
        
        try:
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            health_endpoint = get_zmq_connection_string(self.health_port, "bind", "0.0.0.0")
            self.health_socket.bind(health_endpoint)
            self.logger.info(f"Health check socket bound to {health_endpoint}")
        except zmq.error.ZMQError as e:
            self.logger.error(f"Failed to bind health check socket: {e}")
            self.report_error(f"Failed to bind health check socket: {e}")
            # Continue even if health check socket fails
        
        # Initialize model and tokenizer as None (not loaded initially)
        self.model = None
        self.tokenizer = None
        
        # Model configuration
        self.model_name = CONFIG_MODEL_PATH_OR_NAME
        
        if CONFIG_DEVICE == 'auto':
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = CONFIG_DEVICE
        
        self.logger.info(f"Using device: {self.device}")
        
        # Start background monitor thread for idle model unloading
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        self.logger.info("Resource monitor thread started")
    
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
            self.logger.error(f"Reported error: {error_message}")
        except Exception as e:
            self.logger.error(f"Failed to report error to error bus: {e}")
    
    def _load_model(self):
        """Load NLLB model and tokenizer"""
        try:
            self.logger.info("Loading NLLB model and tokenizer...")
            
            # Load tokenizer
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.logger.info("Tokenizer loaded successfully")
            except Exception as e:
                self.logger.error(f"Failed to load tokenizer: {str(e)}")
                self.logger.error(traceback.format_exc())
                raise
                
            # Determine device
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.logger.info(f"Using device: {device}")
            
            # Load model with appropriate device mapping
            try:
                self.model = AutoModelForSeq2SeqLM.from_pretrained(
                    self.model_name,
                    device_map="auto" if device == "cuda" else None,
                    torch_dtype=torch.float16 if device == "cuda" else torch.float32
                )
                
                # If using CPU, explicitly move model to CPU
                if device == "cpu":
                    self.model = self.model.to(device)
                    
                self.logger.info("Model loaded successfully")
                
                # Verify model is on correct device
                if device == "cuda" and not next(self.model.parameters()).is_cuda:
                    self.logger.warning("Model not on CUDA, attempting to move...")
                    self.model = self.model.to(device)
                    
            except Exception as e:
                self.logger.error(f"Failed to load model: {str(e)}")
                self.logger.error(traceback.format_exc())
                self.model = None
                self.tokenizer = None
                raise
                
            self.model_loaded = True
            self.last_used = time.time()
            
        except Exception as e:
            self.logger.error(f"Model loading failed: {str(e)}")
            self.logger.error(traceback.format_exc())
            self.model_loaded = False
            self.model = None
            self.tokenizer = None
            raise
    
    def _unload_model(self):
        """Unload the NLLB model and tokenizer from memory"""
        if self.model is None:
            self.logger.info("Model already unloaded")
            return True
        
        try:
            self.logger.info("Unloading NLLB model")
            
            # Delete model and tokenizer
            del self.model
            del self.tokenizer
            self.model = None
            self.tokenizer = None
            
            # Clear CUDA cache if available
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            self.logger.info("NLLB model unloaded successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error unloading NLLB model: {e}")
            self.logger.error(traceback.format_exc())
            return False
    
    def translate_text(self, text, source_lang, target_lang):
        """Translate text using NLLB model"""
        try:
            # Map language codes if needed
            source_lang = self.language_code_mapping.get(source_lang, source_lang)
            target_lang = self.language_code_mapping.get(target_lang, target_lang)
            
            # Validate language codes
            if source_lang not in self.supported_languages:
                return {
                    'status': 'error',
                    'message': f'Unsupported source language: {source_lang}. Supported languages: {list(self.supported_languages.keys())}'
                }
            if target_lang not in self.supported_languages:
                return {
                    'status': 'error',
                    'message': f'Unsupported target language: {target_lang}. Supported languages: {list(self.supported_languages.keys())}'
                }
            
            # Load model if not loaded
            if self.model is None:
                self._load_model()
            
            # Update last request time
            self.last_request_time = time.time()
            
            # Ensure model and tokenizer are loaded
            if self.model is None or self.tokenizer is None:
                return {
                    'status': 'error',
                    'message': 'Model or tokenizer failed to load'
                }
                
            # Tokenize input
            inputs = self.tokenizer(text, return_tensors="pt", padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate translation
            outputs = self.model.generate(
                **inputs,
                forced_bos_token_id=self.tokenizer.lang_code_to_id[target_lang],
                max_length=512,
                num_beams=5,
                length_penalty=1.0,
                early_stopping=True
            )
            
            # Decode output
            translated_text = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
            
            return {
                'status': 'success',
                'translated_text': translated_text
            }
            
        except KeyError as e:
            self.logger.error(f"Language code error: {str(e)}")
            return {
                'status': 'error',
                'message': f'Invalid language code: {str(e)}'
            }
        except Exception as e:
            self.logger.error(f"Translation error: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _monitor_resources(self):
        """Monitor system resources and model state"""
        while self.running:
            try:
                # Update health status
                current_time = time.time()
                self.health_status.update({
                    "model_state": "loaded" if self.model is not None else "unloaded",
                    "last_check": current_time,
                    "resource_stats": {
                        "device": self.device,
                        "memory_usage": psutil.virtual_memory().percent,
                        "gpu_memory": torch.cuda.memory_allocated() if self.device == "cuda" else None
                    }
                })
                
                # Check if model should be unloaded due to idle timeout
                if (self.model is not None and 
                    time.time() - self.last_request_time > self.service_idle_timeout_seconds):
                    self.logger.info("Model idle timeout reached, unloading model")
                    self._unload_model()
                
                # Log resource stats periodically
                if int(current_time) % 60 < 1:  # Log every minute
                    self.logger.info(f"Resource stats: {self.health_status['resource_stats']}")
                
                time.sleep(1)  # Check every second
                
            except Exception as e:
                self.logger.error(f"Error in resource monitoring: {e}")
                time.sleep(1)
    
    def handle_requests(self):
        """Handle incoming translation requests"""
        while self.running:
            try:
                # Receive request
                message = self.socket.recv_json()
                self.last_request_time = time.time()
                
                # Handle health check request
                if isinstance(message, dict) and "action" in message and message["action"] == "health_check":
                    response = self._get_health_status()
                    self.socket.send_json(response)
                    continue
                
                # Handle translation request
                if isinstance(message, dict) and "action" in message and message["action"] == "translate":
                    try:
                        # Extract text and language parameters safely
                        text = ""
                        source_lang = ""
                        target_lang = ""
                        
                        if isinstance(message, dict):
                            if "text" in message and isinstance(message["text"], str):
                                text = message["text"]
                            if "source_lang" in message and isinstance(message["source_lang"], str):
                                source_lang = message["source_lang"]
                            if "target_lang" in message and isinstance(message["target_lang"], str):
                                target_lang = message["target_lang"]
                        
                        # Map Filipino to Tagalog if needed
                        source_lang = self.language_code_mapping.get(source_lang, source_lang)
                        target_lang = self.language_code_mapping.get(target_lang, target_lang)
                        
                        # Validate languages
                        if source_lang not in self.supported_languages:
                            raise ValueError(f"Unsupported source language: {source_lang}")
                        if target_lang not in self.supported_languages:
                            raise ValueError(f"Unsupported target language: {target_lang}")
                        
                        # Ensure model is loaded
                        if self.model is None:
                            self._load_model()
                        
                        # Perform translation
                        translated_text = self.translate_text(text, source_lang, target_lang)
                        
                        response = {
                            "status": "success",
                            "translated_text": translated_text
                        }
                        
                    except Exception as e:
                        self.logger.error(f"Translation error: {e}")
                        response = {
                            "status": "error",
                            "message": str(e)
                        }
                    
                    self.socket.send_json(response)
                    continue
                
                # Unknown action
                action = "unknown"
                if isinstance(message, dict) and "action" in message:
                    action = message["action"]
                else:
                    action = "Invalid request format"
                    
                self.socket.send_json({
                    "status": "error",
                    "message": f"Unknown action: {action}"
                })
                
            except zmq.error.Again:
                # Timeout waiting for message; continue listening
                continue
            except Exception as e:
                self.logger.error(f"Error handling request: {e}")
                # Attempt to report error if socket is in a proper state
                try:
                    self.socket.send_json({
                        "status": "error",
                        "message": "Internal server error"
                    })
                except zmq.error.ZMQError:
                    # Ignore if cannot send due to socket state
                    pass
    
    def run(self):
        """Run the NLLB Translation Adapter"""
        try:
            self.logger.info("NLLB Translation Adapter started")
            
            # Handle requests
            self.handle_requests()
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt, shutting down")
        except Exception as e:
            self.logger.error(f"Error in NLLB Translation Adapter: {e}")
            self.logger.error(traceback.format_exc())
        finally:
            self.cleanup()
    
    def _get_health_status(self) -> dict:
        """Get the current health status of the agent."""
        # Get base status from parent class
        base_status = super()._get_health_status()
        
        # Add NLLB-specific metrics
        base_status.update({
            "model_state": "loaded" if self.model is not None else "unloaded",
            "device": self.device,
            "resource_stats": {
                "device": self.device,
                "memory_usage": psutil.virtual_memory().percent,
                "gpu_memory": torch.cuda.memory_allocated() if self.device == "cuda" else None
            }
        })
        
        return base_status
    
    def cleanup(self):
        """Clean up resources before exiting"""
        self.logger.info("Cleaning up resources...")
        self.running = False
        
        # Unload model to free up GPU memory
        if self.model is not None:
            self._unload_model()
        
        # Close ZMQ socket
        if hasattr(self, 'socket') and self.socket:
            self.socket.close()
            self.logger.info("Main socket closed")
        
        # Wait for threads to finish
        if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
            self.logger.info("Monitor thread joined")
        
        # Call parent cleanup to handle BaseAgent resources
        super().cleanup()
        
        self.logger.info("Cleanup completed")

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = NLLBTranslationAdapter()
        agent.run()
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