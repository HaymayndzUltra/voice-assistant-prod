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

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).resolve().parent.parent))

try:
    from config.system_config import get_config_for_service, get_config_for_machine
    SERVICE_ID = "nllb-translation-adapter-pc2"
    service_config = get_config_for_service(SERVICE_ID)
    pc2_general_config = get_config_for_machine("pc2")

    LOG_LEVEL = pc2_general_config.get('log_level', 'INFO')
    LOGS_DIR = Path(pc2_general_config.get('logs_dir', 'logs'))
    CONFIG_ZMQ_PORT = service_config.get('zmq_port', 5581)
    CONFIG_ZMQ_BIND_ADDRESS = service_config.get('zmq_bind_address', "0.0.0.0")
    CONFIG_MODEL_PATH_OR_NAME = service_config.get('model_path_or_name', "facebook/nllb-200-distilled-600M")
    CONFIG_DEVICE = service_config.get('device', 'auto') # auto, cuda, cpu
    CONFIG_IDLE_TIMEOUT = service_config.get('idle_timeout_seconds_self', 300)

except ImportError:
    print("WARNING: Could not import system_config. Using default/hardcoded settings for NLLBTranslationAdapter.")
    LOG_LEVEL = 'INFO'
    LOGS_DIR = Path('logs')
    CONFIG_ZMQ_PORT = 5581
    CONFIG_ZMQ_BIND_ADDRESS = "0.0.0.0"
    CONFIG_MODEL_PATH_OR_NAME = "facebook/nllb-200-distilled-600M"
    CONFIG_DEVICE = 'auto'
    CONFIG_IDLE_TIMEOUT = 300

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

logger.info(f"Imported config: Port={CONFIG_ZMQ_PORT}, Bind={CONFIG_ZMQ_BIND_ADDRESS}, Model={CONFIG_MODEL_PATH_OR_NAME}, Device={CONFIG_DEVICE}, IdleTimeout={CONFIG_IDLE_TIMEOUT}")

class NLLBTranslationAdapter:
    """Service for NLLB translation model with self-managed on-demand loading/unloading"""
    
    def __init__(self):
        # Initialize ZMQ
        self.context = zmq.Context()
        
        # Socket to handle requests
        self.socket = self.context.socket(zmq.REP)
        self.service_port = CONFIG_ZMQ_PORT
        self.bind_address = CONFIG_ZMQ_BIND_ADDRESS
        try:
            self.socket.bind(f"tcp://{self.bind_address}:{self.service_port}")
            logger.info(f"NLLB Translation Adapter bound to tcp://{self.bind_address}:{self.service_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Error binding to port {self.service_port} on address {self.bind_address}: {e}")
            if self.bind_address == "0.0.0.0":
                logger.warning(f"Attempting fallback bind to tcp://127.0.0.1:{self.service_port}")
                try:
                    self.socket.bind(f"tcp://127.0.0.1:{self.service_port}")
                    logger.info(f"NLLB Translation Adapter bound to FALLBACK tcp://127.0.0.1:{self.service_port}")
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
        
        logger.info(f"NLLB Translation Adapter initialized on {self.device}")
    
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
            logger.info("Model already unloaded")
            return True
        
        try:
            logger.info("Unloading NLLB model")
            
            # Delete model and tokenizer
            del self.model
            del self.tokenizer
            self.model = None
            self.tokenizer = None
            
            # Clear CUDA cache if available
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            logger.info("NLLB model unloaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error unloading NLLB model: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def translate_text(self, text, source_lang, target_lang):
        """Translate text using the NLLB model with on-demand loading"""
        try:
            # On-demand loading if model is not loaded
            if self.model is None:
                logger.info("On-demand loading of model for translation request")
                success = self._load_model()
                if not success:
                    return {"status": "error", "message": "Failed to load model"}
            
            # Update last request time to prevent idle unloading during active use
            self.last_request_time = time.time()
            
            # Tokenize input
            inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
            
            # Set the language token
            self.tokenizer.src_lang = source_lang
            forced_bos_token_id = self.tokenizer.lang_code_to_id[target_lang]
            
            # Generate translation
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    forced_bos_token_id=forced_bos_token_id,
                    max_length=256
                )
            
            # Decode the generated text
            translated_text = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
            
            return {"status": "success", "translated_text": translated_text}
        except Exception as e:
            logger.error(f"Error translating text: {e}")
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
                
                if action == "translate":
                    # Handle translation request
                    text = request.get("text", "")
                    source_lang = request.get("source_lang", "tgl_Latn")
                    target_lang = request.get("target_lang", "eng_Latn")
                    
                    response = self.translate_text(text, source_lang, target_lang)
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
        """Run the NLLB Translation Adapter"""
        try:
            # Start idle monitoring thread
            idle_thread = threading.Thread(target=self._idle_monitoring_thread)
            idle_thread.daemon = True
            idle_thread.start()
            
            logger.info("NLLB Translation Adapter started")
            
            # Handle requests
            self.handle_requests()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down")
        except Exception as e:
            logger.error(f"Error in NLLB Translation Adapter: {e}")
            logger.error(traceback.format_exc())
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources")
        self.running = False
        
        # Unload model if loaded
        if self.model is not None:
            self._unload_model()
        
        # Close socket
        try:
            self.socket.close()
            logger.info("Socket closed")
        except Exception as e:
            logger.error(f"Error closing socket: {e}")
        
        # Close ZMQ context
        try:
            self.context.term()
            logger.info("ZMQ context terminated")
        except Exception as e:
            logger.error(f"Error terminating ZMQ context: {e}")


if __name__ == "__main__":
    try:
        # Create necessary directories
        log_file_path = LOGS_DIR / "nllb_translation_adapter.log"
        os.makedirs(LOGS_DIR, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file_path),
                logging.StreamHandler()
            ]
        )
        logger = logging.getLogger("NLLBTranslationAdapter")
        
        logger.info(f"Imported config: Port={CONFIG_ZMQ_PORT}, Bind={CONFIG_ZMQ_BIND_ADDRESS}, Model={CONFIG_MODEL_PATH_OR_NAME}, Device={CONFIG_DEVICE}, IdleTimeout={CONFIG_IDLE_TIMEOUT}")
        
        # Start the service
        service = NLLBTranslationAdapter()
        service.run()
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
    except Exception as e:
        logger.error(f"Error starting service: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
