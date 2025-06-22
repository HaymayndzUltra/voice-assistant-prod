#!/usr/bin/env python3
"""
Simplified Translator Agent
- Focuses on reliable ZMQ communication with proper timeout handling
- Uses external binding (0.0.0.0) for Main PC connectivity
- Provides quick responses to health checks and translation requests
"""
import os
import sys
import json
import time
import zmq
import uuid
import logging
import re
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/translator_simple.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("TranslatorSimple")

# Constants
ZMQ_PORT = 5563
ZMQ_BIND_ADDRESS = "0.0.0.0"
RECV_TIMEOUT_MS = 1000  # 1 second timeout for receiving messages

class SimpleTranslator:
    def __init__(self):
        """Initialize a simplified translator agent focused on reliability"""
        logger.info("Initializing SimpleTranslator agent")
        
        # Initialize ZMQ
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        
        # Set socket timeout to prevent blocking indefinitely
        self.socket.setsockopt(zmq.RCVTIMEO, RECV_TIMEOUT_MS)
        
        # Bind to external interface
        bind_address = f"tcp://{ZMQ_BIND_ADDRESS}:{ZMQ_PORT}"
        logger.info(f"Binding to {bind_address}")
        self.socket.bind(bind_address)
        
        # Basic statistics
        self.start_time = time.time()
        self.request_count = 0
        
        # Simple translation cache
        self.translation_cache = {}
        
        logger.info("SimpleTranslator agent initialized successfully")
    
    def run(self):
        """Main event loop with timeout handling"""
        logger.info("SimpleTranslator running and waiting for requests")
        
        try:
            while True:
                try:
                    # Wait for next request from client with timeout
                    message_json = self.socket.recv_string()
                    
                    # Parse the message
                    try:
                        message = json.loads(message_json)
                        logger.info(f"Received request: {message.get('action', 'unknown')}")
                        
                        # Process request
                        response = self._process_request(message)
                        
                        # Send response back
                        self.socket.send_json(response)
                        self.request_count += 1
                        
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON: {message_json}")
                        self.socket.send_json({"status": "error", "error": "Invalid JSON format"})
                
                except zmq.error.Again:
                    # Socket timeout - no messages received
                    # This prevents the socket from blocking indefinitely
                    continue
                    
                except Exception as e:
                    logger.error(f"Error in run loop: {str(e)}", exc_info=True)
                    try:
                        self.socket.send_json({"status": "error", "error": str(e)})
                    except:
                        pass
                    time.sleep(0.1)  # Prevent CPU spinning in case of repeated errors
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self._cleanup()
    
    def _process_request(self, message):
        """Process incoming requests with explicit timeout handling"""
        action = message.get("action", "unknown")
        
        if action == "translate":
            # Handle translation request
            text = message.get("text", "")
            source_lang = message.get("source_lang", "tl")
            target_lang = message.get("target_lang", "en")
            session_id = message.get("session_id", str(uuid.uuid4()))
            
            # Check cache first
            cache_key = f"{text.lower()}:{source_lang}:{target_lang}"
            if cache_key in self.translation_cache:
                translated = self.translation_cache[cache_key]
                method = "cache"
            else:
                # Simple translation (this would be replaced with actual ML model in production)
                translated = self._simple_translate(text)
                self.translation_cache[cache_key] = translated
                method = "simple_model"
            
            return {
                "status": "success",
                "translated_text": translated,
                "original_text": text,
                "method": method,
                "session_id": session_id
            }
        
        elif action == "health_check":
            # Handle health check request
            return {
                "status": "success",
                "service": "translator_simple",
                "uptime_seconds": time.time() - self.start_time,
                "request_count": self.request_count,
                "cache_size": len(self.translation_cache)
            }
        
        else:
            # Unknown action
            return {
                "status": "error",
                "error": f"Unknown action: {action}"
            }
    
    def _simple_translate(self, text):
        """Simple translation logic for testing/demo purposes"""
        # This is a very basic translation for demo purposes
        # In production, this would call an actual translation service
        
        # Basic Tagalog patterns
        translations = {
            "buksan": "open",
            "isara": "close",
            "i-save": "save",
            "i-download": "download",
            "magandang umaga": "good morning",
            "magandang hapon": "good afternoon",
            "magandang gabi": "good evening",
            "salamat": "thank you",
            "oo": "yes",
            "hindi": "no",
            "file": "file",
            "ang": "the",
            "mo": "you",
            "ito": "this",
            "iyon": "that",
            "ko": "I",
            "namin": "we",
            "sila": "they",
            "siya": "he/she",
            "tayo": "we (inclusive)",
            "kayo": "you (plural)",
            "sa": "to/at/in",
            "ng": "of",
            "bagong": "new",
            "lumang": "old",
            "malaki": "big",
            "maliit": "small",
            "mabilis": "fast",
            "mabagal": "slow",
            "magsimula": "start",
            "huminto": "stop",
            "mag-on": "turn on",
            "mag-off": "turn off",
            "i-on": "turn on",
            "i-off": "turn off",
            "i-turn on": "turn on",
            "i-turn off": "turn off",
            "pakiusap": "please",
            "po": "",  # Politeness marker, often not directly translated
            "na": "already/now",
            "pa": "still/more",
            "muli": "again",
            "paki": "please",
            "document": "document",
            "project": "project",
            "gumawa": "create/make",
            "gawin": "do/make"
        }
        
        text_lower = text.lower()
        result = text_lower
        
        # Replace words with translations
        for tagalog, english in translations.items():
            pattern = r'\b' + re.escape(tagalog) + r'\b'
            result = re.sub(pattern, english, result)
        
        # Fix common patterns
        result = result.replace("open the file", "open the file")
        result = result.replace("save the document", "save the document")
        result = result.replace("start new project", "start a new project")
        result = result.replace("download that file", "download that file")
        
        # Return the result with proper capitalization
        return result.capitalize()
    
    def _cleanup(self):
        """Clean up resources"""
        try:
            # Close ZMQ socket
            if hasattr(self, 'socket'):
                self.socket.close()
            
            # Terminate ZMQ context
            if hasattr(self, 'context'):
                self.context.term()
                
            logger.info("SimpleTranslator agent shutdown complete")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

if __name__ == "__main__":
    # Create and run the translator
    translator = SimpleTranslator()
    translator.run()
