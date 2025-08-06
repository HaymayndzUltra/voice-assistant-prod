from main_pc_code.src.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.log_setup import configure_logging
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

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))
from main_pc_code.config.system_config import config
from common.env_helpers import get_env

# Configure logging
log_level = config.get('system.log_level', 'INFO')
log_file = Path(config.get('system.logs_dir', 'logs')) / str(PathManager.get_logs_dir() / "translator_agent.log")
log_file.parent.mkdir(exist_ok=True)

logger = configure_logging(__name__),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TranslatorAgent")

# Get ZMQ ports from config
TRANSLATOR_PORT = config.get('zmq.translator_port', 5559)  # New port for translator
LISTENER_PORT = config.get('zmq.listener_port', 5561)      # Listener's publish port
TASK_ROUTER_PORT = config.get('zmq.task_router_port', 5558)  # Task router's port
MODEL_MANAGER_PORT = config.get('zmq.model_manager_port', 5556)  # Model manager for translation

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
        super().__init__(port=port, name="Pc2translatorAgent")
        # Initialize ZMQ
        self.context = zmq.Context()
        
        # Socket to publish translated commands
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.bind(f"tcp://127.0.0.1:{TRANSLATOR_PORT}")
        logger.info(f"Publishing on port {TRANSLATOR_PORT}")
        
        # Socket to subscribe to listener
        self.listener_sub = self.context.socket(zmq.SUB)
        self.listener_sub.connect(f"tcp://localhost:{LISTENER_PORT}")
        self.listener_sub.setsockopt_string(zmq.SUBSCRIBE, "")
        logger.info(f"Connected to Listener on port {LISTENER_PORT}")
        
        # Socket to communicate with model manager
        self.model_manager = self.context.socket(zmq.REQ)
        self.model_manager.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.model_manager.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.model_manager.connect(f"tcp://localhost:{MODEL_MANAGER_PORT}")
        logger.info(f"Connected to Model Manager on port {MODEL_MANAGER_PORT}")
        
        # Initialize translation model
        self.translation_model = self._initialize_translation_model()
        
        # Running flag
        self.running = True
        
        logger.info("Translator Agent initialized")
    
    def _initialize_translation_model(self):
        """Initialize the NLLB translation model for Filipino to English"""
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except ImportError as e:
        print(f"Import error: {e}")
            import torch
            logger.info("Loading NLLB translation model: facebook/nllb-200-distilled-600M ...")
            model_name = "facebook/nllb-200-distilled-600M"
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model = model.to(device)
            logger.info("NLLB translation model loaded successfully")
            return {"tokenizer": tokenizer, "model": model, "device": device, "type": "nllb"}
        except Exception as e:
            logger.error(f"Error initializing NLLB translation model: {str(e)}")
            traceback.print_exc()
            return None

    
    def translate_command(self, text: str, source_lang="fil_Latn", target_lang="eng_Latn") -> str:
        """Translate Filipino command to English using NLLB"""
        # Check if this is already English
        if self._is_likely_english(text):
            return text
        # Try using the NLLB translation model if available
        if self.translation_model and self.translation_model["type"] == "nllb":
            translated = self._model_translation(text, source_lang=source_lang, target_lang=target_lang)
            if translated and translated != text:
                return translated
        # Try pattern matching for common phrases
        translated = self._pattern_match_translation(text)
        # If pattern matching failed, use LLM
        if not translated or translated == text:
            translated = self._llm_translation(text)
        return translated

        
    def _model_translation(self, text: str, source_lang="fil_Latn", target_lang="eng_Latn") -> str:
        """Translate using the NLLB model"""
        try:
            if not self.translation_model or self.translation_model["type"] != "nllb":
                return text
            tokenizer = self.translation_model["tokenizer"]
            model = self.translation_model["model"]
            device = self.translation_model["device"]
            # Tokenize
            inputs = tokenizer(text, return_tensors="pt").to(device)
            # Set forced BOS token to the target language
            forced_bos_token_id = tokenizer.lang_code_to_id[target_lang]
            # Generate translation
            outputs = model.generate(
                **inputs,
                forced_bos_token_id=forced_bos_token_id,
                max_length=128,
            )
            # Decode and return
            translation = tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
            logger.info(f"NLLB Model translated: '{text}' -> '{translation}'")
            return translation
        except Exception as e:
            logger.error(f"Error in NLLB translation: {str(e)}")
            return text
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
        """Listen for commands from the listener and translate them"""
        logger.info("Starting to handle commands...")
        while self.running:
            try:
                # Wait for message from listener
                message_str = self.listener_sub.recv_string()
                message = json.loads(message_str)
                # Extract the command text and language fields
                original_text = message.get("text", "")
                source_lang = message.get("source_lang", "fil_Latn")
                target_lang = message.get("target_lang", "eng_Latn")
                logger.info(f"Received command: {original_text}")
                # Translate the command
                translated_text = self.translate_command(original_text, source_lang=source_lang, target_lang=target_lang)
                # If translation is different, log it
                if translated_text != original_text:
                    logger.info(f"Translated: '{original_text}' -> '{translated_text}'")
                # Create new message with translated text
                translated_message = message.copy()
                translated_message["text"] = translated_text
                translated_message["original_text"] = original_text
                translated_message["translated"] = True
                # Publish translated message
                self.publisher.send_string(json.dumps(translated_message))
            except zmq.Again:
                # Timeout, continue loop
                pass
            except json.JSONDecodeError:
                logger.error("Invalid JSON in message from listener")
            except Exception as e:
                logger.error(f"Error handling command: {str(e)}")
                traceback.print_exc()
    
    def run(self):
        """Run the translator agent"""
        try:
            logger.info("Starting Translator Agent...")
            self.handle_commands()
        except KeyboardInterrupt:
            logger.info("Translator Agent interrupted by user")
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            traceback.print_exc()
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        self.publisher.close()
        self.listener_sub.close()
        self.model_manager.close()
        self.context.term()
        logger.info("Translator Agent stopped")


if __name__ == "__main__":
    import argparse

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
    parser = argparse.ArgumentParser(description="Translator Agent: Translates commands from Filipino to English.")
    parser.add_argument('--server', action='store_true', help='Run in server mode, waiting for ZMQ messages')
    args = parser.parse_args()
    
    agent = TranslatorAgent()
    
    if args.server:
        # Just initialize the agent and keep it running, waiting for ZMQ messages
        logger.info("Translator Agent running in server mode, waiting for messages...")
        try:
            # Keep the process alive
            agent.handle_commands()
        except KeyboardInterrupt:
            logger.info("Translator Agent interrupted by user")
    else:
        # Run the full agent
        agent.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise