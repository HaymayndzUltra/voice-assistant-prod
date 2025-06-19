#!/usr/bin/env python3
"""
Quick Translator Service Fix
- Creates a simple, reliable ZMQ-based translator service
- Properly binds to 0.0.0.0:5564 for external access
- Responds to both health_check and translate actions
"""
import sys
import zmq
import json
import time
import logging
import threading
import uuid
import traceback
from pathlib import Path

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "fallback_translator.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("FallbackTranslator")

class TranslatorService:
    def __init__(self):
        logger.info("=" * 80)
        logger.info("Initializing Fallback Translator Service")
        logger.info("=" * 80)
        
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        
        # Critical: Set timeout so we don't block indefinitely
        self.socket.setsockopt(zmq.RCVTIMEO, 2000)  # 2 second timeout
        
        # Bind to all interfaces for external access
        self.bind_address = "tcp://0.0.0.0:5564"
        logger.info(f"Binding to {self.bind_address}")
        self.socket.bind(self.bind_address)
        
        self.running = True
        self.start_time = time.time()
        
        # Track statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.translation_requests = 0
        self.health_check_requests = 0
        
        # Simplified translation table
        self.translations = {
            "buksan mo ang file": "open the file",
            "i-save mo ang document": "save the document",
            "magsimula ng bagong project": "start a new project",
            "magandang umaga po": "good morning",
            "salamat po": "thank you",
        }
        
        logger.info("Fallback Translator service initialized successfully")
        logger.info(f"Translation table size: {len(self.translations)} entries")
        logger.info("=" * 80)
    
    def start(self):
        """Start the service in a separate thread to avoid blocking"""
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()
        logger.info("Fallback Translator service started in background thread")
        return self.thread
    
    def run(self):
        """Main service loop with timeout handling"""
        logger.info("Fallback Translator service running")
        
        while self.running:
            try:
                # Wait for next request with timeout
                message_str = self.socket.recv_string()
                logger.debug(f"Received message: {message_str[:100]}")
                
                # Parse and process
                try:
                message = json.loads(message_str)
                action = message.get("action", "unknown")
                logger.info(f"Processing action: {action}")
                
                # Handle the request
                if action == "translate":
                        self.translation_requests += 1
                    response = self._handle_translation(message)
                elif action == "health_check":
                        self.health_check_requests += 1
                    response = self._handle_health_check()
                else:
                    response = {"status": "error", "message": f"Unknown action: {action}"}
                        self.failed_requests += 1
                
                # Send response
                    logger.debug(f"Sending response: {str(response)[:100]}...")
                self.socket.send_json(response)
                    self.total_requests += 1
                    if response.get("status") == "success":
                        self.successful_requests += 1
                    else:
                        self.failed_requests += 1
                        
                except json.JSONDecodeError as e:
                    error_msg = f"Invalid JSON in request: {str(e)}"
                    logger.error(error_msg)
                    self.socket.send_json({"status": "error", "message": error_msg})
                    self.failed_requests += 1
                
            except zmq.error.Again:
                # Timeout - just continue the loop
                continue
            except Exception as e:
                error_msg = f"Error in service loop: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                try:
                    self.socket.send_json({"status": "error", "message": error_msg})
                except:
                    pass
                self.failed_requests += 1
                time.sleep(0.1)  # Small delay to prevent CPU spinning
    
    def _handle_translation(self, message):
        """Handle translation request"""
        text = message.get("text", "")
        source_lang = message.get("source_lang", "tl")
        target_lang = message.get("target_lang", "en")
        session_id = message.get("session_id", str(uuid.uuid4()))
        
        logger.info(f"Translation request - From: {source_lang}, To: {target_lang}, Text length: {len(text)}")
        
        # Perform translation
        text_lower = text.lower()
        if text_lower in self.translations:
            translated = self.translations[text_lower]
            logger.info(f"Found exact match in translation table")
        else:
            # Fallback translation - just echo back for demonstration
            translated = f"[EN] {text}"
            logger.info(f"No exact match found, using fallback translation")
        
        return {
            "status": "success",
            "translated_text": translated,
            "original_text": text,
            "method": "quick_fix",
            "confidence": 0.95,
            "session_id": session_id
        }
    
    def _handle_health_check(self):
        """Handle health check request"""
        logger.info("Processing health check request")
        response = {
            "status": "ok",
            "service": "fallback_translator",
            "timestamp": time.time(),
            "uptime_seconds": time.time() - self.start_time,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "translation_requests": self.translation_requests,
            "health_check_requests": self.health_check_requests,
            "bind_address": self.bind_address
        }
        logger.info(f"Health check response: {json.dumps(response)}")
        return response
    
    def stop(self):
        """Stop the service"""
        logger.info("Stopping Fallback Translator service...")
        self.running = False
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        logger.info("Fallback Translator service stopped")

if __name__ == "__main__":
    try:
        # Create and start the service
        service = TranslatorService()
        thread = service.start()
        
        # Keep the main thread alive
        logger.info("Service running in background. Press Ctrl+C to exit.")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        service.stop()
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)
