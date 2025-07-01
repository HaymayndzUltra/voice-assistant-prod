from src.core.base_agent import BaseAgent
"""
Translator Agent
- Translates commands from Filipino to English
- Sits between listener and command router
- Uses local LLM for translation
- Maintains command context
"""
import zmq
import json
import time
import logging
import sys
import os
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional

# EARLY LOGGING
try:
    with open("translator_agent_early.log", "a", encoding="utf-8") as f:
        f.write("[EARLY LOG] Translator agent script started.\n")
except Exception as e:
    pass

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))
from config.system_config import config

# Configure logging
log_level = config.get('system.log_level', 'INFO')
log_file = Path(config.get('system.logs_dir', 'logs')) / "translator_agent.log"
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TranslatorAgent")

# Use completely different port range to avoid conflicts
TRANSLATOR_PORT = 8044  # Use a port in the 8000-8100 range to avoid conflicts
LISTENER_PORT = config.get('zmq.listener_port', 7561)      # Listener's publish port
TASK_ROUTER_PORT = config.get('zmq.task_router_port', 5558)  # Task router's port
MODEL_MANAGER_PORT = config.get('zmq.model_manager_port', 7556)  # Model manager for translation

# Optional: Import torch if available; Translator Agent can operate without PyTorch
try:
    import torch  # type: ignore
except ImportError:
    torch = None  # type: ignore  # PyTorch not installed; will trigger fallback paths

# Filipino command patterns and their English equivalents
COMMON_TRANSLATIONS = {
    "buksan": "open",
    "buksan mo": "open",
    "buksan mo ang": "open",
    "isara": "close",
    "isara mo": "close",
    "isara mo ang": "close",
    "i-save": "save",
    "i-save mo": "save",
    "i-save mo ang": "save",
    "gumawa": "create",
    "gumawa ng": "create",
    "gumawa ka ng": "create",
    "magsimula": "start",
    "magsimula ng": "start",
    "tumigil": "stop",
    "ihinto": "stop",
    "i-search": "search",
    "hanapin": "search",
    "hanapin mo": "search",
    "maghanap": "search",
    "maghanap ng": "search",
    "i-restart": "restart",
    "i-restart mo": "restart",
    "ayusin": "fix",
    "ayusin mo": "fix",
    "ayusin mo ang": "fix",
    "i-debug": "debug",
    "i-debug mo": "debug",
    "i-check": "check",
    "i-check mo": "check",
    "tingnan": "check",
    "tingnan mo": "check",
    "ipakita": "show",
    "ipakita mo": "show",
    "ipakita mo ang": "show",
    "i-run": "run",
    "patakbuhin": "run",
    "patakbuhin mo": "run",
    "i-execute": "execute",
    "i-execute mo": "execute",
    "i-translate": "translate",
    "i-translate mo": "translate",
    "isalin": "translate",
    "isalin mo": "translate",
    "magsalita": "speak",
    "magsalita ka": "speak",
    "sabihin": "say",
    "sabihin mo": "say",
    "i-play": "play",
    "i-play mo": "play",
    "i-pause": "pause",
    "i-pause mo": "pause",
    "i-resume": "resume",
    "i-resume mo": "resume",
    "i-stop": "stop",
    "i-stop mo": "stop",
    "i-cancel": "cancel",
    "i-cancel mo": "cancel",
    "kanselahin": "cancel",
    "kanselahin mo": "cancel",
    "i-delete": "delete",
    "i-delete mo": "delete",
    "burahin": "delete",
    "burahin mo": "delete",
    "i-update": "update",
    "i-update mo": "update",
    "i-upgrade": "upgrade",
    "i-upgrade mo": "upgrade",
    "i-install": "install",
    "i-install mo": "install",
    "i-uninstall": "uninstall",
    "i-uninstall mo": "uninstall",
    "i-download": "download",
    "i-download mo": "download",
    "i-upload": "upload",
    "i-upload mo": "upload",
    "i-send": "send",
    "i-send mo": "send",
    "ipadala": "send",
    "ipadala mo": "send",
    "i-receive": "receive",
    "i-receive mo": "receive",
    "tanggapin": "receive",
    "tanggapin mo": "receive",
    "i-accept": "accept",
    "i-accept mo": "accept",
    "tanggapin": "accept",
    "tanggapin mo": "accept",
    "i-reject": "reject",
    "i-reject mo": "reject",
    "tanggihan": "reject",
    "tanggihan mo": "reject",
    "i-approve": "approve",
    "i-approve mo": "approve",
    "aprubahan": "approve",
    "aprubahan mo": "approve",
    "i-deny": "deny",
    "i-deny mo": "deny",
    "tanggihan": "deny",
    "tanggihan mo": "deny",
    "i-confirm": "confirm",
    "i-confirm mo": "confirm",
    "kumpirmahin": "confirm",
    "kumpirmahin mo": "confirm",
    "i-verify": "verify",
    "i-verify mo": "verify",
    "patunayan": "verify",
    "patunayan mo": "verify",
    "i-validate": "validate",
    "i-validate mo": "validate",
    "patunayan": "validate",
    "patunayan mo": "validate",
    "i-check": "check",
    "i-check mo": "check",
    "suriin": "check",
    "suriin mo": "check",
    "i-test": "test",
    "i-test mo": "test",
    "subukan": "test",
    "subukan mo": "test",
    "i-try": "try",
    "i-try mo": "try",
    "subukan": "try",
    "subukan mo": "try",
    "i-analyze": "analyze",
    "i-analyze mo": "analyze",
    "suriin": "analyze",
    "suriin mo": "analyze",
    "i-monitor": "monitor",
    "i-monitor mo": "monitor",
    "bantayan": "monitor",
    "bantayan mo": "monitor",
    "i-track": "track",
    "i-track mo": "track",
    "subaybayan": "track",
    "subaybayan mo": "track",
    "i-follow": "follow",
    "i-follow mo": "follow",
    "sundan": "follow",
    "sundan mo": "follow",
    "i-generate": "generate",
    "i-generate mo": "generate",
    "gumawa": "generate",
    "gumawa ka": "generate",
    "gumawa ka ng": "generate",
    "i-fix": "fix",
    "i-fix mo": "fix",
    "ayusin": "fix",
    "ayusin mo": "fix",
    "i-repair": "repair",
    "i-repair mo": "repair",
    "ayusin": "repair",
    "ayusin mo": "repair",
    "i-solve": "solve",
    "i-solve mo": "solve",
    "lutasin": "solve",
    "lutasin mo": "solve",
    "i-resolve": "resolve",
    "i-resolve mo": "resolve",
    "lutasin": "resolve",
    "lutasin mo": "resolve",
    "i-debug": "debug",
    "i-debug mo": "debug",
    "i-debug mo ang": "debug",
    "i-optimize": "optimize",
    "i-optimize mo": "optimize",
    "i-optimize mo ang": "optimize",
    "i-improve": "improve",
    "i-improve mo": "improve",
    "i-improve mo ang": "improve",
    "pagbutihin": "improve",
    "pagbutihin mo": "improve",
    "pagbutihin mo ang": "improve",
    "i-enhance": "enhance",
    "i-enhance mo": "enhance",
    "i-enhance mo ang": "enhance",
    "pagbutihin": "enhance",
    "pagbutihin mo": "enhance",
    "pagbutihin mo ang": "enhance",
    "i-upgrade": "upgrade",
    "i-upgrade mo": "upgrade",
    "i-upgrade mo ang": "upgrade",
    "i-update": "update",
    "i-update mo": "update",
    "i-update mo ang": "update",
    "i-refresh": "refresh",
    "i-refresh mo": "refresh",
    "i-refresh mo ang": "refresh",
    "i-reload": "reload",
    "i-reload mo": "reload",
    "i-reload mo ang": "reload",
    "i-restart": "restart",
    "i-restart mo": "restart",
    "i-restart mo ang": "restart",
    "i-reboot": "reboot",
    "i-reboot mo": "reboot",
    "i-reboot mo ang": "reboot",
    "i-shutdown": "shutdown",
    "i-shutdown mo": "shutdown",
    "i-shutdown mo ang": "shutdown",
    "i-turn off": "turn off",
    "i-turn off mo": "turn off",
    "i-turn off mo ang": "turn off",
    "patayin": "turn off",
    "patayin mo": "turn off",
    "patayin mo ang": "turn off",
    "i-turn on": "turn on",
    "i-turn on mo": "turn on",
    "i-turn on mo ang": "turn on",
    "buksan": "turn on",
    "buksan mo": "turn on",
    "buksan mo ang": "turn on",
    "i-power on": "power on",
    "i-power on mo": "power on",
    "i-power on mo ang": "power on",
    "i-power off": "power off",
    "i-power off mo": "power off",
    "i-power off mo ang": "power off",
    "patayin": "power off",
    "patayin mo": "power off",
    "patayin mo ang": "power off"
}

class TranslatorAgent(BaseAgent):
    """Agent for translating Filipino commands to English"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="TranslatorAgent")
        # Initialize ZMQ
        self.context = zmq.Context()
        
        # Socket to publish translated commands - use a fixed port that won't conflict
        self.publisher = self.context.socket(zmq.PUB)
        
        # Use a fixed port that is unlikely to conflict with other agents
        fixed_port = 5544  # This port should not be used by any other agent
        try:
            self.publisher.bind(f"tcp://127.0.0.1:{fixed_port}")
            logger.info(f"Successfully bound to port {fixed_port}")
            # Update the global constant so other agents can find us
            global TRANSLATOR_PORT
            TRANSLATOR_PORT = fixed_port
        except zmq.error.ZMQError as e:
            logger.error(f"Error binding to port {fixed_port}: {e}")
            raise RuntimeError(f"Cannot bind to port {fixed_port}: {e}") from e
            
        # Socket to handle health check requests from dashboard
        self.health_socket = self.context.socket(zmq.REP)
        self.health_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        try:
            # Use the port 8044 as specified in the distributed_config.json
            health_port = 8044
            self.health_socket.bind(f"tcp://127.0.0.1:{health_port}")
            logger.info(f"Health check socket bound to port {health_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Error binding health check socket to port {health_port}: {e}")
            # Don't raise an exception here, just log the error and continue
        
        # Socket to subscribe to listener
        try:
            self.listener_sub = self.context.socket(zmq.SUB)
            self.listener_sub.connect(f"tcp://localhost:{LISTENER_PORT}")
            self.listener_sub.setsockopt_string(zmq.SUBSCRIBE, "")
            self.listener_sub.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            logger.info(f"Connected to Listener on port {LISTENER_PORT}")
        except Exception as e:
            logger.error(f"Error connecting to Listener: {e}")
            raise RuntimeError(f"Cannot connect to Listener: {e}") from e
        
        # Socket to communicate with model manager
        try:
            self.model_manager = self.context.socket(zmq.REQ)
            self.model_manager.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.model_manager.connect(f"tcp://localhost:{MODEL_MANAGER_PORT}")
            logger.info(f"Connected to Model Manager on port {MODEL_MANAGER_PORT}")
        except Exception as e:
            logger.error(f"Error connecting to Model Manager: {e}")
            raise RuntimeError(f"Cannot connect to Model Manager: {e}") from e
        
        # Initialize translation model
        self.translation_model = self._initialize_translation_model()
        
        # Running flag
        self.running = True
        
        logger.info("Translator Agent initialized")
    
    def _initialize_translation_model(self):
        """Initialize translation model with better error handling and fallbacks"""
        # First try to import the required modules
        try:
            if torch is None:
                logger.warning("PyTorch not installed; falling back to pattern matching only")
                return None
            import torch
            from transformers import MarianMTModel, MarianTokenizer
            logger.info("Successfully imported required modules for translation")
        except ImportError as e:
            logger.warning(f"Import error: {e}. Falling back to pattern matching only.")
            return None
        
        # Then try to load the model
        try:
            logger.info("Using HuggingFace transformers MarianMTModel for translation...")
            model_name = "Helsinki-NLP/opus-mt-tl-en"
            
            # Load tokenizer first
            try:
                tokenizer = MarianTokenizer.from_pretrained(model_name)
                logger.info("Tokenizer loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load tokenizer: {e}")
                return None
            
            # Determine device
            try:
                device = "cuda" if torch.cuda.is_available() else "cpu"
                logger.info(f"Using device: {device}")
            except Exception as e:
                logger.warning(f"Error determining device: {e}. Defaulting to CPU.")
                device = "cpu"
            
            # Load and move model to device
            try:
                model = MarianMTModel.from_pretrained(model_name)
                model = model.to(device)
                logger.info(f"Translation model loaded successfully on device: {device}")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                return None
            
            return {"tokenizer": tokenizer, "model": model, "type": "transformers", "device": device}
        except Exception as e:
            logger.error(f"Unexpected error initializing translation model: {str(e)}")
            traceback.print_exc()
            return None
    
    def translate_command(self, text: str) -> str:
        """Translate Filipino command to English, with Taglish detection."""
        from agents.taglish_detector import detect_taglish
import psutil
from datetime import datetime
        is_taglish, fil_ratio, eng_ratio = detect_taglish(text)
        if is_taglish:
            logger.info(f"[TranslatorAgent] Taglish detected: Filipino={fil_ratio:.2f}, English={eng_ratio:.2f}")
            # Placeholder: Adjust prompt or handling for Taglish if needed
        # Check if this is already English
        if self._is_likely_english(text):
            return text
        # Try using the translation model if available
        if self.translation_model:
            translated = self._model_translation(text)
            if translated and translated != text:
                return translated
        # Try pattern matching for common phrases
        translated = self._pattern_match_translation(text)
        # If pattern matching failed, use LLM
        if translated == text:
            translated = self._llm_translation(text)
        return translated
        
    def _model_translation(self, text: str) -> str:
        """Translate using the local translation model"""
        try:
            if not self.translation_model:
                return text
            
            if self.translation_model["type"] == "ctranslate2":
                # Use CTranslate2 for translation
                tokenizer = self.translation_model["tokenizer"]
                translator = self.translation_model["model"]
                
                # Tokenize input
                source = tokenizer(text, return_tensors="pt", padding=True)
                source_tokens = source.input_ids[0].tolist()
                
                # Translate
                translation = translator.translate_batch([source_tokens])
                target_tokens = translation[0].hypotheses[0]
                
                # Decode output
                translated_text = tokenizer.decode(target_tokens, skip_special_tokens=True)
                
                logger.info(f"Model translated: '{text}' -> '{translated_text}'")
                return translated_text
                
            elif self.translation_model["type"] == "transformers":
                # Use transformers for translation
                tokenizer = self.translation_model["tokenizer"]
                model = self.translation_model["model"]
                
                # Tokenize input
                encoded = tokenizer(text, return_tensors="pt", padding=True)
                
                # Move encoded input to the same device as the model
                device = self.translation_model["device"]
                for key in encoded.keys():
                    encoded[key] = encoded[key].to(device)
                
                # Generate translation
                output = model.generate(**encoded)
                
                # Decode output
                translated_text = tokenizer.decode(output[0], skip_special_tokens=True)
                
                logger.info(f"Model translated: '{text}' -> '{translated_text}'")
                return translated_text
            
            return text
            
            return self._llm_translation(text)
        except Exception as e:
            logger.error(f"Error in LLM translation: {str(e)}")
            # If LLM translation fails, return original text
            return text
    
    def _is_likely_english(self, text: str) -> bool:
        """Check if text is likely already in English"""
        # Simple heuristic: check if common Filipino words/prefixes are present
        filipino_markers = [
            "ang", "ng", "mga", "sa", "ko", "mo", "niya", "namin", "natin", "ninyo", "nila",
            "ito", "iyan", "iyon", "dito", "diyan", "doon", "na", "pa", "pang-", "pag-", 
            "nag", "mag", "i-", "ka-", "makipag-", "nakipag-"
        ]
        
        text_lower = text.lower()
        for marker in filipino_markers:
            if f" {marker} " in f" {text_lower} ":
                return False
        
        return True
    
    def _pattern_match_translation(self, text: str) -> Optional[str]:
        """Translate using pattern matching for common phrases"""
        text_lower = text.lower()
        
        # Try to match the start of the command with known patterns
        for filipino, english in COMMON_TRANSLATIONS.items():
            if text_lower.startswith(filipino + " "):
                # Replace the pattern and keep the rest of the command
                rest_of_command = text[len(filipino):].strip()
                return f"{english} {rest_of_command}"
        
        # If no direct pattern match, try more flexible matching
        words = text_lower.split()
        if len(words) >= 2:
            # Try first two words
            first_two = " ".join(words[:2])
            if first_two in COMMON_TRANSLATIONS:
                return f"{COMMON_TRANSLATIONS[first_two]} {' '.join(words[2:])}"
            
            # Try just the first word
            if words[0] in COMMON_TRANSLATIONS:
                return f"{COMMON_TRANSLATIONS[words[0]]} {' '.join(words[1:])}"
        
        return None
    
    def _llm_translation(self, text: str) -> str:
        """Use LLM for more complex translations"""
        prompt = f"""Translate the following Filipino command to English. 

    def health_check(self):
        '''
        Performs a health check on the agent, returning a dictionary with its status.
        '''
        try:
            # Basic health check logic
            is_healthy = True # Assume healthy unless a check fails
            
            # TODO: Add agent-specific health checks here.
            # For example, check if a required connection is alive.
            # if not self.some_service_connection.is_alive():
            #     is_healthy = False

            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else -1,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {} # Placeholder for agent-specific data
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            return {
                "status": "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "error": f"Health check failed with exception: {str(e)}"
            }

Keep it concise and focused on the command intent.
Only return the translated command, nothing else.

Filipino command: {text}

English translation:"""
        
        # Prepare request
        request = {
            "request_type": "generate",
            "model": "deepseek",  # Use a capable model
            "prompt": prompt,
            "temperature": 0.1  # Low temperature for deterministic translation
        }
        
        # Send request to model manager
        self.model_manager.send_string(json.dumps(request))
        
        # Wait for response with timeout
        poller = zmq.Poller()
        poller.register(self.model_manager, zmq.POLLIN)
        
        if poller.poll(10000):  # 10 second timeout
            response_str = self.model_manager.recv_string()
            response = json.loads(response_str)
            
            if response["status"] == "success":
                # Extract just the translated command
                translation = response["text"].strip()
                
                # Clean up the response - remove any markdown or explanations
                lines = [line for line in translation.split('\n') if line.strip()]
                if lines:
                    translation = lines[0]
                
                # Remove any quotes
                translation = translation.strip('"\'')
                
                return translation
            else:
                logger.error(f"Error from model manager: {response.get('error', 'Unknown error')}")
                raise Exception(response.get("error", "Unknown error"))
        else:
            logger.error("Timeout waiting for response from model manager")
            raise Exception("Timeout waiting for response from model manager")
    
    def handle_commands(self):
        """Listen for commands from the listener and translate them with improved error handling"""
        logger.info("Starting to handle commands...")
        
        # Process a batch of messages with timeout to avoid blocking forever
        start_time = time.time()
        max_processing_time = 1.0  # Maximum time to process messages before returning
        message_count = 0
        
        while self.running and (time.time() - start_time < max_processing_time):
            try:
                # Wait for message from listener with timeout
                if self.listener_sub.poll(timeout=100) == 0:  # 100ms timeout
                    # No message available, continue loop
                    continue
                
                # Receive message
                message_str = self.listener_sub.recv_string(flags=zmq.NOBLOCK)
                message_count += 1
                
                try:
                    message = json.loads(message_str)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON in message from listener")
                    continue
                
                # Extract the command text
                original_text = message.get("text", "")
                if not original_text:
                    logger.warning("Received empty text in message")
                    continue
                    
                logger.info(f"Received command: {original_text}")
                
                # Translate the command with fallback
                try:
                    translated_text = self.translate_command(original_text)
                except Exception as e:
                    logger.error(f"Translation error: {str(e)}, using original text")
                    translated_text = original_text
                
                # If translation is different, log it
                if translated_text != original_text:
                    logger.info(f"Translated: '{original_text}' -> '{translated_text}'")
                
                # Create new message with translated text
                translated_message = message.copy()
                translated_message["text"] = translated_text
                translated_message["original_text"] = original_text
                translated_message["translated"] = True
                
                # Publish translated message
                try:
                    self.publisher.send_string(json.dumps(translated_message))
                    logger.info("Published translated message")
                except Exception as e:
                    logger.error(f"Error publishing message: {str(e)}")
                
            except zmq.Again:
                # Timeout, continue loop
                pass
            except Exception as e:
                logger.error(f"Error handling command: {str(e)}")
                traceback.print_exc()
                # Continue processing despite errors
                
        # Return after processing batch or timeout
        if message_count > 0:
            logger.info(f"Processed {message_count} messages in this batch")
        
        # This function now returns normally, not exiting the loop
    
    def handle_health_check(self):
        """Handle health check requests from the dashboard"""
        try:
            # Check if there's a health check request with a short timeout
            if self.health_socket.poll(timeout=10) == 0:  # 10ms timeout
                return False  # No request
            
            # Receive the request
            request_str = self.health_socket.recv_string(flags=zmq.NOBLOCK)
            try:
                request = json.loads(request_str)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in health check request")
                self.health_socket.send_string(json.dumps({"status": "error", "message": "Invalid JSON"}))
                return True
            
            # Check if it's a health check request
            if request.get("request_type") == "health_check":
                logger.debug("Received health check request")
                # Send success response
                response = {
                    "status": "success",
                    "agent": "translator",
                    "timestamp": time.time()
                }
                self.health_socket.send_string(json.dumps(response))
                return True
            else:
                # Unknown request type
                logger.warning(f"Unknown request type: {request.get('request_type')}")
                self.health_socket.send_string(json.dumps({"status": "error", "message": "Unknown request type"}))
                return True
                
        except zmq.Again:
            # No message available
            return False
        except Exception as e:
            logger.error(f"Error handling health check: {str(e)}")
            try:
                self.health_socket.send_string(json.dumps({"status": "error", "message": str(e)}))
            except Exception:
                pass  # Ignore errors in sending error response
            return True
    
    def run(self):
        """Run the translator agent with session-aware processing and infinite loop pattern"""
        try:
            logger.info("Starting Translator Agent on port %s...", TRANSLATOR_PORT)
            self.running = True
            
            # Main processing loop - WILL NOT EXIT unless explicitly terminated
            while True:
                try:
                    # Handle health check requests
                    self.handle_health_check()
                    
                    # Handle commands with timeout to prevent blocking forever
                    self.handle_commands()
                    
                    # Small sleep to prevent CPU hogging
                    time.sleep(0.01)
                    
                except zmq.error.Again:
                    # Socket timeout, normal condition
                    continue
                except KeyboardInterrupt:
                    # Log but don't exit - let the orchestrator handle termination
                    logger.info("Translator Agent received keyboard interrupt, continuing operation")
                    time.sleep(0.5)
                except Exception as e:
                    # Log error but keep running
                    logger.error(f"Error in message processing loop: {str(e)}")
                    logger.error("Attempting to recover and continue...")
                    traceback.print_exc()
                    time.sleep(1)  # Slow down on errors
                    
        except Exception as e:
            # This should never happen - the inner loop should catch all exceptions
            logger.critical(f"CRITICAL: Outer exception handler triggered: {str(e)}")
            traceback.print_exc()
        finally:
            # Only reached if the infinite loop is somehow broken
            logger.critical("CRITICAL: Translator agent exiting run() method - THIS SHOULD NEVER HAPPEN")
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        self.publisher.close()
        self.listener_sub.close()
        self.model_manager.close()
        self.health_socket.close()
        self.context.term()
        logger.info("Translator Agent stopped")


if __name__ == "__main__":
    # Use a global try-except to catch any errors during startup
    try:
        with open("translator_agent_early.log", "a", encoding="utf-8") as f:
            f.write(f"[EARLY LOG] Translator agent script started.\n")
        
        # Create the agent
        agent = TranslatorAgent()
        logger.info("Translator Agent running and entering main loop...")
        
        # Enter the main loop - this should never exit
        while True:
            try:
                # Run the agent's main loop
                agent.run()
                # If run() somehow returns (it shouldn't), log and continue
                logger.critical("Agent.run() returned unexpectedly - restarting main loop")
                time.sleep(1)  # Prevent rapid restart loops
            except KeyboardInterrupt:
                # Handle keyboard interrupt but don't exit
                logger.info("Keyboard interrupt received, but continuing operation")
                time.sleep(1)
            except Exception as e:
                # Log any exceptions but don't exit
                logger.error(f"Error in main loop: {str(e)}")
                traceback.print_exc()
                time.sleep(5)  # Longer delay on errors
    except Exception as e:
        # Only catch startup exceptions here
        with open("translator_agent_early.log", "a", encoding="utf-8") as f:
            f.write(f"[EARLY EXCEPTION] {str(e)}\n")
        logger.error(f"[EARLY EXCEPTION] {str(e)}")
        traceback.print_exc()
        # Keep the process alive even on startup errors
        while True:
            time.sleep(60)  # Sleep indefinitely

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise