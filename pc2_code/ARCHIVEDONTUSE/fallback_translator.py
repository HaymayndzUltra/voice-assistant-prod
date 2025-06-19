#!/usr/bin/env python3
"""
Fallback Translator Agent
- Provides fallback translation capabilities when primary translator fails
- Uses simpler translation models for reliability
- Maintains a cache of recent translations
"""

import zmq
import json
import time
import logging
import threading
from pathlib import Path
import sys

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))
from config.system_config import config

# Configure logging
log_level = config.get('system.log_level', 'INFO')
log_file = Path(config.get('system.logs_dir', 'logs')) / "fallback_translator.log"
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("FallbackTranslator")

class FallbackTranslator:
    def __init__(self, port=5564, bind_address="0.0.0.0"):
        """Initialize the Fallback Translator"""
        self.port = port
        self.bind_address = bind_address
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        
        try:
            self.socket.bind(f"tcp://{self.bind_address}:{self.port}")
            logger.info(f"Fallback Translator bound to port {self.port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Error binding to port {self.port}: {e}")
            raise RuntimeError(f"Cannot bind to port {self.port}")
        
        # Initialize state
        self.start_time = time.time()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.health_check_count = 0
        
        logger.info("Fallback Translator initialized")
    
    def get_status(self):
        """Get the current status of the Fallback Translator"""
        uptime = time.time() - self.start_time
        return {
            "status": "ok",
            "service": "fallback_translator",
            "timestamp": time.time(),
            "uptime_seconds": uptime,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "health_check_count": self.health_check_count,
            "bind_address": f"tcp://{self.bind_address}:{self.port}"
        }
    
    def handle_request(self, request):
        """Handle incoming translation requests"""
        try:
            action = request.get("action")
            
            if action == "health_check":
                self.health_check_count += 1
                return self.get_status()
            elif action == "translate":
                self.total_requests += 1
                text = request.get("text")
                source_lang = request.get("source_lang", "auto")
                target_lang = request.get("target_lang", "en")
                
                if not text:
                    self.failed_requests += 1
                    return {"status": "error", "reason": "No text provided"}
                
                # TODO: Implement actual translation logic
                # For now, just echo back the text
                translated_text = f"[FALLBACK] {text}"
                
                self.successful_requests += 1
                return {
                    "status": "ok",
                    "translated_text": translated_text,
                    "source_lang": source_lang,
                    "target_lang": target_lang
                }
            else:
                return {"status": "error", "reason": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            self.failed_requests += 1
            return {"status": "error", "reason": str(e)}
    
    def run(self):
        """Main service loop"""
        logger.info("Fallback Translator service loop started")
        while True:
            try:
                msg = self.socket.recv_string()
                request = json.loads(msg)
                response = self.handle_request(request)
                self.socket.send_string(json.dumps(response))
            except Exception as e:
                logger.error(f"Error in service loop: {e}")
                self.socket.send_string(json.dumps({
                    "status": "error",
                    "reason": str(e)
                }))

def main():
    """Main entry point"""
    try:
        translator = FallbackTranslator()
        translator.run()
    except KeyboardInterrupt:
        logger.info("Shutting down Fallback Translator")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 