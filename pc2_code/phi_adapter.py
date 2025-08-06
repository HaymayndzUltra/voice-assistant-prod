import os
import zmq
import time
import json
import logging
import requests
import re
import argparse
import random
from datetime import datetime
from common.env_helpers import get_env
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.log_setup import configure_logging

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

# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PhiTranslationAdapter")

class PhiTranslationAdapter:
    """Phi Translation Adapter for Taglish to English using Ollama."""
    
    DEFAULT_PORT = 5581
    
    # Default prompt template for translations
    DEFAULT_PROMPT_TEMPLATE = """Translate to English:

{INPUT}
"""

    def __init__(self, port=DEFAULT_PORT, prompt_template=None, enable_auth=ENABLE_AUTH):
        self.port = port
        self.context = zmq.Context()
        self.enable_auth = enable_auth
        
        # REP socket for receiving translation requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        logger.info(f"Phi Translation Adapter bound to port {self.port}")
        
        if not self.enable_auth:
            logger.warning("Authentication DISABLED - running in insecure mode")
        
        # Statistics tracking
        self.stats = {
            "requests": 0,
            "successful": 0,
            "failures": 0,
            "last_error": None,
            "last_update": time.time(),
            "last_client_ip": None,
            "last_token": None
        }
        
        self.running = True
        self.auth_token = AUTH_TOKEN
    
    def build_translation_prompt(self, text, source_lang="tl", target_lang="en"):
        """Build a minimal prompt for Tagalog/Taglish→English translation."""
        return self.DEFAULT_PROMPT_TEMPLATE.format(INPUT=text)
    
    def _clean_translation_output(self, raw_output, original_text):
        """
        Aggressively clean and extract only the proper translation from LLM response.
        """
        try:
            # Take just the first line as translation and strip any whitespace
            if raw_output:
                lines = [l.strip() for l in raw_output.splitlines() if l.strip()]
                if lines:
                    return lines[0].strip()
            return raw_output.strip()
        except Exception as e:
            logger.error(f"Error cleaning translation: {e}")
            return raw_output
    
    def _validate_translation(self, original_text, translation):
        """Basic validation - return None if good, error message if bad"""
        if not translation:
            return "Empty translation"
        return None
    
    def translate(self, text, source_lang="tl", target_lang="en"):
        """Translate text using Phi model via Ollama."""
        logger.info(f"Translating: '{text}'")
        start_time = time.time()
        self.stats["requests"] += 1
        
        prompt = self.build_translation_prompt(text, source_lang, target_lang)
        
        try:
            # Call Ollama API for translation
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "phi",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                raw_response = result.get("response", "").strip()
                
                # Clean translation output
                translation = self._clean_translation_output(raw_response, text)
                
                # Validate translation
                quality_issues = self._validate_translation(text, translation)
                
                if quality_issues:
                    logger.warning(f"Translation quality issue: {quality_issues}")
                    return {
                        "original": text,
                        "translated": text,  # Return original as fallback
                        "model": "phi",
                        "success": False,
                        "elapsed_sec": time.time() - start_time,
                        "message": f"Translation quality issue: {quality_issues}"
                    }
                
                elapsed = time.time() - start_time
                self.stats["successful"] += 1
                
                return {
                    "original": text,
                    "translated": translation,
                    "model": "phi",
                    "success": True,
                    "elapsed_sec": elapsed,
                    "message": "Success"
                }
            else:
                self.stats["failures"] += 1
                logger.error(f"Ollama API error: {response.status_code}")
                return {
                    "original": text,
                    "translated": text,
                    "model": "phi",
                    "success": False,
                    "elapsed_sec": time.time() - start_time,
                    "message": f"Ollama API error: {response.status_code}"
                }
        except Exception as e:
            self.stats["failures"] += 1
            self.stats["last_error"] = str(e)
            logger.error(f"Translation error: {e}")
            return {
                "original": text,
                "translated": text,
                "model": "phi",
                "success": False,
                "elapsed_sec": time.time() - start_time,
                "message": f"Error: {str(e)}"
            }
    
    def run(self):
        """Run the adapter, listening for translation and health check requests."""
        logger.info("=== Phi Translation Adapter ===")
        logger.info("Using Phi model via Ollama")
        logger.info(f"Binding to port: {self.port}")
        
        if not self.enable_auth:
            logger.warning("Authentication DISABLED - running in insecure mode")
        
        while self.running:
            try:
                request = self.socket.recv_json()
                
                # Track client IP for diagnostics
                client_ip = self.socket.get_string(zmq.LAST_ENDPOINT)
                self.stats["last_client_ip"] = client_ip
                self.stats["last_update"] = time.time()
                
                action = request.get("action", "")
                token = request.get("token", "")
                self.stats["last_token"] = token[:3] + "..." if token else "None"
                
                # Process requests
                if action == "health":
                    # Return health status without auth check
                    response = {
                        "success": True,
                        "message": "Phi Translation Adapter is healthy.",
                        "stats": self.stats,
                        "timestamp": time.time()
                    }
                    self.socket.send_json(response)
                elif self.enable_auth and token != self.auth_token:
                    # Auth required but invalid token
                    logger.warning(f"Auth failed from {client_ip}")
                    response = {
                        "success": False,
                        "message": "Authentication failed. Invalid token.",
                        "timestamp": time.time()
                    }
                    self.socket.send_json(response)
                elif action == "translate":
                    # Handle translation request
                    text = request.get("text", "")
                    source_lang = request.get("source_lang", "tl")
                    target_lang = request.get("target_lang", "en")
                    
                    result = self.translate(text, source_lang, target_lang)
                    self.socket.send_json(result)
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
    parser = argparse.ArgumentParser(description="Phi Translation Adapter for Taglish to English")
    parser.add_argument("--port", type=int, default=5581, help="Port to listen on")
    parser.add_argument("--no-auth", action="store_true", help="Disable authentication")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    enable_auth = not args.no_auth
    
    try:
        adapter = PhiTranslationAdapter(port=args.port, enable_auth=enable_auth)
        adapter.run()
    except KeyboardInterrupt:
        print("Shutting down Phi Translation Adapter...")
    except Exception as e:
        print(f"Error: {e}")
