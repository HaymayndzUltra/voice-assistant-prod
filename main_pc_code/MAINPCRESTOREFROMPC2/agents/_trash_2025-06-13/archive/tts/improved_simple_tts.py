from src.core.base_agent import BaseAgent
"""
Improved Simple TTS Agent
Enhanced version with better resource handling for multiple responses
"""
import os
import sys
import json
import time
import zmq
import logging
import threading
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(Path(__file__).parent.parent, 'modular_system', 'logs', 'simple_tts.log'))
    ]
)
logger = logging.getLogger("SimpleTTS_Agent")

# ZMQ Configuration
TTS_PORT = 5562  # Use the same port as other TTS agents for compatibility

class SimpleTTSAgent(BaseAgent):
    """Simple TTS agent with better resource handling"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ImprovedSimpleTts")
        """Initialize the TTS agent"""
        logger.info("Initializing Simple TTS Agent (Improved)")
        
        # Initialize ZMQ - using REP socket for reliable request-response pattern
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://*:{TTS_PORT}")
        logger.info(f"TTS Agent listening on port {TTS_PORT}")
        
        # Initialize TTS
        self._initialize_tts()
        
        # Keep track of running state
        self.running = True
        
        # Initialize stop event for clean shutdown
        self.stop_event = threading.Event()
        
    def _initialize_tts(self):
        """Initialize Windows TTS"""
        try:
            import win32com.client

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
            self.speaker = win32com.client.Dispatch("SAPI.SpVoice")
            logger.info("Windows SAPI TTS initialized successfully")
            self.speaker.Speak("TTS system ready.")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Windows SAPI TTS: {e}")
            return False
            
    def speak(self, text):
        """Speak the given text using Windows SAPI"""
        if not text:
            logger.warning("Empty text provided to speak")
            return False
            
        try:
            logger.info(f"Speaking: {text[:50]}...")
            self.speaker.Speak(text)
            logger.info("Speech completed")
            return True
        except Exception as e:
            logger.error(f"Error during speech: {e}")
            return False
            
    def handle_request(self, request_data):
        """Handle a TTS request"""
        try:
            # Parse request
            if isinstance(request_data, str):
                data = json.loads(request_data)
            else:
                data = request_data
                
            # Extract text
            if 'text' in data:
                text = data['text']
                logger.info(f"Received TTS request: {text[:50]}...")
                
                # Speak the text
                success = self.speak(text)
                
                # Return result
                if success:
                    return {"status": "success", "message": "Text spoken successfully"}
                else:
                    return {"status": "error", "message": "Failed to speak text"}
            else:
                logger.warning("Received invalid TTS request (no text field)")
                return {"status": "error", "message": "No text provided in request"}
                
        except Exception as e:
            logger.error(f"Error handling TTS request: {e}")
            return {"status": "error", "message": f"Error processing request: {str(e)}"}
    
    def run(self):
        """Main loop for the TTS agent"""
        logger.info("Simple TTS Agent starting main loop")
        
        # First speak to confirm ready
        self.speak("Voice assistant is ready.")
        
        try:
            while self.running and not self.stop_event.is_set():
                try:
                    # Wait for a message with timeout
                    request = None
                    if self.socket.poll(timeout=1000) == zmq.POLLIN:  # Poll with 1-second timeout
                        request = self.socket.recv_string()
                    
                    if request:
                        # Process request
                        result = self.handle_request(request)
                        
                        # Send response
                        self.socket.send_string(json.dumps(result))
                    
                except zmq.ZMQError as e:
                    logger.error(f"ZMQ error in main loop: {e}")
                    # Reset the socket on error
                    self._reset_socket()
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    # Try to send error response
                    try:
                        self.socket.send_string(json.dumps({"status": "error", "message": f"Error: {str(e)}"}))
                    except:
                        # Reset socket if send fails
                        self._reset_socket()
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info("TTS Agent interrupted by keyboard")
        finally:
            logger.info("TTS Agent shutting down")
            self.stop_event.set()
            self.running = False
            self.socket.close()
            self.context.term()
            
    def _reset_socket(self):
        """Reset the ZMQ socket on error"""
        try:
            logger.info("Resetting ZMQ socket")
            self.socket.close()
            time.sleep(0.5)
            self.socket = self.context.socket(zmq.REP)
            self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.socket.bind(f"tcp://*:{TTS_PORT}")
            logger.info("ZMQ socket reset successfully")
        except Exception as e:
            logger.error(f"Error resetting ZMQ socket: {e}")
            

if __name__ == "__main__":
    print("=== Improved Simple TTS Agent ===")
    print(f"Listening on ZMQ port {TTS_PORT}")
    print("Using Windows SAPI for TTS")
    
    agent = SimpleTTSAgent()
    agent.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise