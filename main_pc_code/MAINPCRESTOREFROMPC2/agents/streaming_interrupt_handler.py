from src.core.base_agent import BaseAgent
"""
Streaming Interrupt Handler
Monitors partial transcripts for interruption keywords and sends interrupt signals
"""
import zmq
import pickle
import json
import time
import logging
import threading
import os
from utils.config_parser import parse_agent_args
from utils.service_discovery_client import get_service_address, register_service
from utils.env_loader import get_env
from src.network.secure_zmq import configure_secure_client, configure_secure_server

# Parse command line arguments
_agent_args = parse_agent_args()

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StreamingInterruptHandler")

# ZMQ Configuration - using ports from startup_config.yaml via args
ZMQ_SUB_PORT = int(getattr(_agent_args, 'streaming_speech_recognition_port', 5575))  # Subscribe to partial transcripts
ZMQ_PUB_PORT = int(getattr(_agent_args, 'port', 5576))  # Publish interrupt signals
TTS_PORT = int(getattr(_agent_args, 'streaming_tts_agent_port', 5562))  # TTS agent port for sending stop commands

# Get bind address from environment variables with default to 0.0.0.0 for Docker compatibility
BIND_ADDRESS = get_env('BIND_ADDRESS', '0.0.0.0')

# Interruption keywords in different languages
INTERRUPT_KEYWORDS = {
    'en': ['stop', 'wait', 'cancel', 'enough', 'shut up', 'be quiet', 'pause'],
    'tl': ['tama', 'tama na', 'tumigil', 'hinto', 'sapat na', 'teka', 'sandali']
}

class StreamingInterruptHandler(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="StreamingInterruptHandler")
        self.context = zmq.Context()
        self.secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"
        
        # Subscribe to partial transcripts - use service discovery
        self.sub_socket = self.context.socket(zmq.SUB)
        if self.secure_zmq:
            self.sub_socket = configure_secure_client(self.sub_socket)
            
        # Try to get the address from service discovery
        stt_address = get_service_address("StreamingSpeechRecognition")
        if not stt_address:
            # Fall back to configured port
            stt_address = f"tcp://localhost:{ZMQ_SUB_PORT}"
            
        self.sub_socket.connect(stt_address)
        self.sub_socket.setsockopt(zmq.SUBSCRIBE, b"")
        logger.info(f"Connected to partial transcripts at {stt_address}")
        
        # Publish interrupt signals
        self.pub_socket = self.context.socket(zmq.PUB)
        if self.secure_zmq:
            self.pub_socket = configure_secure_server(self.pub_socket)
            
        bind_address = f"tcp://{BIND_ADDRESS}:{ZMQ_PUB_PORT}"
        self.pub_socket.bind(bind_address)
        logger.info(f"Publishing interrupt signals on {bind_address}")
        
        # Register with service discovery
        self._register_service(ZMQ_PUB_PORT)
        
        # TTS agent socket for direct stop commands - use service discovery
        self.tts_socket = self.context.socket(zmq.REQ)
        if self.secure_zmq:
            self.tts_socket = configure_secure_client(self.tts_socket)
            
        self.tts_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.tts_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        
        # Try to get the TTS address from service discovery
        tts_address = get_service_address("StreamingTtsAgent")
        if not tts_address:
            # Fall back to configured port
            tts_address = f"tcp://localhost:{TTS_PORT}"
            
        self.tts_socket.connect(tts_address)
        logger.info(f"Connected to TTS agent at {tts_address}")
        
        self.running = True
        self.last_interrupt_time = 0
        self.interrupt_cooldown = 2.0  # Seconds between interrupts to prevent duplicates
    
    def _register_service(self, port):
        """Register this agent with the service discovery system"""
        try:
            register_result = register_service(
                name="StreamingInterruptHandler",
                port=port,
                additional_info={
                    "capabilities": ["interrupt", "streaming"],
                    "status": "running"
                }
            )
            if register_result and register_result.get("status") == "SUCCESS":
                logger.info("Successfully registered with service discovery")
            else:
                logger.warning(f"Service registration failed: {register_result.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error registering service: {e}")
    
    def detect_interruption(self, text, language='en'):
        """Check if text contains interruption keywords"""
        if not text:
            return False
            
        text = text.lower()
        
        # Check English keywords first (most common)
        for keyword in INTERRUPT_KEYWORDS['en']:
            if keyword in text:
                return True
                
        # If language is specified and not English, check that language too
        if language != 'en' and language in INTERRUPT_KEYWORDS:
            for keyword in INTERRUPT_KEYWORDS[language]:
                if keyword in text:
                    return True
                    
        return False
    
    def send_tts_stop_command(self):
        """Send stop command directly to TTS agent"""
        try:
            logger.info("Sending stop command to TTS agent")
            self.tts_socket.send_string(json.dumps({
                "command": "stop"
            }))
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(self.tts_socket, zmq.POLLIN)
            if poller.poll(1000):  # 1 second timeout
                response = self.tts_socket.recv_string()
                logger.info(f"TTS agent response: {response}")
                return True
            else:
                logger.warning("TTS agent did not respond to stop command")
                return False
                
        except Exception as e:
            logger.error(f"Error sending stop command to TTS agent: {e}")
            return False
    
    def publish_interrupt(self):
        """Publish interrupt signal to all modules"""
        try:
            # Check cooldown to prevent duplicate interrupts
            current_time = time.time()
            if current_time - self.last_interrupt_time < self.interrupt_cooldown:
                logger.info("Interrupt cooldown active, skipping")
                return False
                
            self.last_interrupt_time = current_time
            
            # Send interrupt signal
            interrupt_msg = pickle.dumps({
                'type': 'interrupt',
                'timestamp': current_time
            })
            self.pub_socket.send(interrupt_msg)
            logger.info("Published interrupt signal")
            
            # Also send direct stop command to TTS agent
            self.send_tts_stop_command()
            
            return True
            
        except Exception as e:
            logger.error(f"Error publishing interrupt: {e}")
            return False
    
    def run(self):
        """Main loop for interrupt handler"""
        logger.info("Starting streaming interrupt handler")
        
        try:
            while self.running:
                try:
                    # Check for partial transcripts
                    msg = self.sub_socket.recv(flags=zmq.NOBLOCK)
                    data = pickle.loads(msg)
                    
                    if data.get('type') == 'partial_transcription':
                        text = data.get('text', '')
                        language = data.get('detected_language', 'en')
                        
                        # Check for interruption keywords
                        if self.detect_interruption(text, language):
                            logger.info(f"Interruption detected in: '{text}'")
                            self.publish_interrupt()
                            
                except zmq.Again:
                    time.sleep(0.05)
                    
        except KeyboardInterrupt:
            logger.info("Interrupt handler stopped by user")
            self.running = False
        except Exception as e:
            logger.error(f"Error in interrupt handler: {e}")
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Clean up ZMQ resources to prevent leaks"""
        logger.info("Cleaning up resources")
        try:
            if hasattr(self, 'sub_socket'):
                self.sub_socket.close()
            if hasattr(self, 'pub_socket'):
                self.pub_socket.close()
            if hasattr(self, 'tts_socket'):
                self.tts_socket.close()
            if hasattr(self, 'context'):
                self.context.term()
            logger.info("All resources cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    print("=== Streaming Interrupt Handler ===")
    print("Monitors partial transcripts for interruption keywords")
    print(f"Subscribing to partial transcripts via service discovery")
    print(f"Publishing interrupt signals on port {ZMQ_PUB_PORT}")
    
    handler = StreamingInterruptHandler()
    handler.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise