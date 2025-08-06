"""
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.log_setup import configure_logging
Final Fix for PHI Translator
This version enforces extreme restrictions on prompt and output to ensure consistent, high-quality translations
"""

import os
import zmq
import time
import json
import logging
import requests
import re
import argparse
from datetime import datetime
from common.env_helpers import get_env

# --- Security Configuration ---
# Secure token access - no hardcoded fallback
try:
    from common.utils.secret_manager import SecretManager
    AUTH_${SECRET_PLACEHOLDER} SecretManager.get_api_token("PHI_TRANSLATOR")
except ImportError:
    # Fallback for systems without SecretManager
    AUTH_${SECRET_PLACEHOLDER} os.environ.get("PHI_TRANSLATOR_TOKEN")
    if not AUTH_${SECRET_PLACEHOLDER}
        raise ValueError("PHI_TRANSLATOR_TOKEN not found - configure via SecretManager or environment variable")
ENABLE_AUTH = True  # Can be disabled via command-line argument

# --- Tagalog-English Translation Dictionary ---
# Core common phrases for exact matching and fallbacks
TRANSLATION_DICT = {
    # Common phrases
    "buksan": "open",
    "isara": "close",
    "i-save": "save",
    "i-check": "check",
    "tingnan": "view",
    "hanapin": "search",
    "i-download": "download",
    "tanggalin": "remove",
    "gumawa": "create",
    "mag-install": "install",
    "i-delete": "delete",
    "i-update": "update",
    "i-restart": "restart",
    "i-setup": "setup",
    "i-configure": "configure",
    "ayusin": "fix",
    "palitan": "replace",
    "i-back up": "back up",
    "i-test": "test",
    "i-verify": "verify",
    "mag-debug": "debug",
    "i-compile": "compile",
    "i-run": "run",
    "i-execute": "execute",
    "gamitin": "use",
    "i-apply": "apply",
    "idagdag": "add",
    "alisin": "remove",
    "ilagay": "put",
    "ipakita": "show",
    "itago": "hide",
    "alamin": "determine",
    
    # File operations
    "file": "file",
    "folder": "folder",
    "dokumento": "document",
    
    # Common objects/modifiers
    "ito": "this",
    "iyan": "that",
    "lahat": "all",
    "bago": "new",
    "luma": "old",
    "mabilis": "quick",
    "mabagal": "slow",
    "malaki": "large",
    "maliit": "small",
    
    # Common prepositions
    "sa": "to/in/at",
    "mula sa": "from",
    "para sa": "for",
    
    # Pronouns
    "mo": "you",
    "ko": "I/me",
    "natin": "we/us",
    "niya": "he/she/it",
    "nila": "they/them",
    
    # Articles and connectors
    "ang": "the",
    "ng": "of",
    "at": "and",
    "o": "or",
    "pero": "but",
    "kung": "if",
}

# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PhiTranslator")

class PhiTranslator:
    """
    Simplified and robust Phi-based translator for Tagalog/Taglish to English
    with fallbacks to ensure high-quality translations.
    """
    
    DEFAULT_PORT = 5581

    def __init__(self, port=DEFAULT_PORT, enable_auth=ENABLE_AUTH):
        self.port = port
        self.enable_auth = enable_auth
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        self.running = True
        self.auth_token = AUTH_TOKEN
        
        # Statistics tracking
        self.stats = {
            "requests": 0,
            "successful": 0,
            "failures": 0,
            "last_error": None,
            "last_update": time.time(),
            "last_client_ip": None
        }
        
        logger.info(f"PHI Translator initialized on port {self.port}")
        if not self.enable_auth:
            logger.warning("Authentication DISABLED - running in insecure mode")

    def translate_with_pattern_matching(self, text):
        """
        Translate text using pattern matching for accuracy.
        This is used as a fallback when the LLM fails.
        """
        words = text.lower().split()
        translated_words = []
        
        for word in words:
            # Clean the word of any punctuation
            clean_word = re.sub(r'[^\w\s]', '', word)
            
            # Look up in dictionary
            if clean_word in TRANSLATION_DICT:
                translated_words.append(TRANSLATION_DICT[clean_word])
            else:
                # Keep original if not in dictionary
                translated_words.append(word)
                
        return ' '.join(translated_words)

    def translate_with_llm(self, text):
        """
        Translate text using Phi model via Ollama.
        Uses a minimal prompt for best results.
        """
        try:
            # Ultra-minimal prompt
            prompt = f"Translate from Filipino to English: {text}"
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "phi",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=10
            )
            
            if response.status_code == 200:
                # Extract and clean response
                result = response.json()
                raw_output = result.get("response", "").strip()
                
                # Basic cleaning - just take the first line
                translation = raw_output.split('\n')[0].strip()
                
                # Remove any prefixes like "Translation:" or "English:"
                prefixes = ["translation:", "translated:", "english:", "in english:"]
                for prefix in prefixes:
                    if translation.lower().startswith(prefix):
                        translation = translation[len(prefix):].strip()
                        
                # If translation is empty or too long, consider it failed
                if not translation or len(translation) > len(text) * 3:
                    logger.warning(f"LLM translation failed quality check: '{translation}'")
                    return None
                    
                logger.info(f"LLM translation: '{text}' -> '{translation}'")
                return translation
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"LLM translation error: {e}")
            return None

    def translate(self, text):
        """
        Translate text with multi-level fallbacks for robustness.
        1. Try Phi LLM first
        2. Fall back to pattern matching if LLM fails
        """
        start_time = time.time()
        self.stats["requests"] += 1
        
        # Skip translation if text is already English
        if self.is_english(text):
            logger.info(f"Text already in English: '{text}'")
            self.stats["successful"] += 1
            return {
                "original": text,
                "translated": text,
                "model": "identity",
                "success": True,
                "elapsed_sec": time.time() - start_time,
                "message": "Text already in English"
            }
        
        # Method 1: Try LLM translation first
        llm_translation = self.translate_with_llm(text)
        
        if llm_translation and self.is_valid_translation(text, llm_translation):
            self.stats["successful"] += 1
            return {
                "original": text,
                "translated": llm_translation,
                "model": "phi",
                "success": True,
                "elapsed_sec": time.time() - start_time,
                "message": "Success"
            }
            
        # Method 2: Fall back to pattern matching
        logger.info("LLM translation failed, using pattern matching fallback")
        pattern_translation = self.translate_with_pattern_matching(text)
        
        if pattern_translation and pattern_translation != text:
            self.stats["successful"] += 1
            return {
                "original": text,
                "translated": pattern_translation,
                "model": "pattern",
                "success": True,
                "elapsed_sec": time.time() - start_time,
                "message": "Success (pattern fallback)"
            }
            
        # All methods failed, return original text with error
        self.stats["failures"] += 1
        logger.warning(f"All translation methods failed for: '{text}'")
        return {
            "original": text,
            "translated": text,
            "model": "none",
            "success": False,
            "elapsed_sec": time.time() - start_time,
            "message": "Translation failed"
        }
    
    def is_english(self, text):
        """Check if text is already in English."""
        # Simplified check: English words ratio
        english_words = set(["the", "a", "an", "is", "are", "was", "were", "be", "been", 
                           "for", "to", "and", "or", "but", "in", "on", "at", "by", "with", "you"])
        
        words = text.lower().split()
        if not words:
            return False
            
        english_count = sum(1 for word in words if word.strip(".,?!") in english_words)
        return english_count / len(words) > 0.4  # If 40%+ are common English words
    
    def is_valid_translation(self, original, translation):
        """Validate if translation looks reasonable."""
        # Some basic validation rules
        if not translation:
            return False
            
        # Length check - translation shouldn't be much longer or shorter than original
        words_ratio = len(translation.split() / max(1, len(original.split())
        if words_ratio < 0.5 or words_ratio > 2.5:
            logger.warning(f"Translation length ratio suspicious: {words_ratio}")
            return False
            
        # Content check - translation shouldn't contain certain markers
        suspicious_markers = ["translation:", "english:", "tagalog:", "in a system", "condition"]
        if any(marker in translation.lower() for marker in suspicious_markers):
            return False
            
        return True
    
    def run(self):
        """Run the adapter, listening for translation requests."""
        logger.info("=== PHI Translator Service ===")
        logger.info(f"Listening on port {self.port}")
        
        if not self.enable_auth:
            logger.warning("Authentication DISABLED - running in insecure mode")
            
        while self.running:
            try:
                request = self.socket.recv_json()
                client_ip = self.socket.get_string(zmq.LAST_ENDPOINT)
                self.stats["last_client_ip"] = client_ip
                self.stats["last_update"] = time.time()
                
                action = request.get("action", "")
                token = request.get("token", "")
                
                # Process request
                if action == "health":
                    # Return health status without auth check
                    response = {
                        "success": True,
                        "message": "Phi Translation Adapter is healthy.",
                        "stats": self.stats,
                        "timestamp": time.time()
                    }
                elif self.enable_auth and token != self.auth_token:
                    # Auth required but invalid token
                    logger.warning(f"Auth failed from {client_ip}")
                    response = {
                        "success": False,
                        "message": "Authentication failed. Invalid token.",
                        "timestamp": time.time()
                    }
                elif action == "translate":
                    # Handle translation request
                    text = request.get("text", "")
                    response = self.translate(text)
                else:
                    # Unknown action
                    logger.warning(f"Unknown action requested: {action}")
                    response = {
                        "success": False,
                        "message": f"Unknown action: {action}",
                        "timestamp": time.time()
                    }
                
                self.socket.send_json(response)
                
            except zmq.ZMQError as e:
                logger.error(f"ZMQ Error: {e}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON Decode Error: {e}")
                try:
                    self.socket.send_json({"success": False, "message": "Invalid JSON request"})
                except:
                    pass
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                try:
                    self.socket.send_json({"success": False, "message": f"Server error: {str(e)}"})
                except:
                    pass

def parse_args():
    parser = argparse.ArgumentParser(description="Phi Translator Service")
    parser.add_argument("--port", type=int, default=5581, help="Port to listen on")
    parser.add_argument("--no-auth", action="store_true", help="Disable authentication")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    enable_auth = not args.no_auth
    
    try:
        adapter = PhiTranslator(port=args.port, enable_auth=enable_auth)
        adapter.run()
    except KeyboardInterrupt:
        print("Shutting down Phi Translator...")
    except Exception as e:
        print(f"Error: {e}")
