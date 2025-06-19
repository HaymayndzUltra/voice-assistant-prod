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

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StreamingInterruptHandler")

# ZMQ Configuration
ZMQ_SUB_PORT = 5575  # Subscribe to partial transcripts
ZMQ_PUB_PORT = 5576  # Publish interrupt signals
TTS_PORT = 5562      # TTS agent port for sending stop commands

# Interruption keywords in different languages
INTERRUPT_KEYWORDS = {
    'en': ['stop', 'wait', 'cancel', 'enough', 'shut up', 'be quiet', 'pause'],
    'tl': ['tama', 'tama na', 'tumigil', 'hinto', 'sapat na', 'teka', 'sandali']
}

class StreamingInterruptHandler(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="StreamingInterruptHandler")
        self.context = zmq.Context()
        
        # Subscribe to partial transcripts
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect(f"tcp://localhost:{ZMQ_SUB_PORT}")
        self.sub_socket.setsockopt(zmq.SUBSCRIBE, b"")
        logger.info(f"Connected to partial transcripts on port {ZMQ_SUB_PORT}")
        
        # Publish interrupt signals
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.bind(f"tcp://*:{ZMQ_PUB_PORT}")
        logger.info(f"Publishing interrupt signals on port {ZMQ_PUB_PORT}")
        
        # TTS agent socket for direct stop commands
        self.tts_socket = self.context.socket(zmq.REQ)
        self.tts_socket.connect(f"tcp://localhost:{TTS_PORT}")
        logger.info(f"Connected to TTS agent on port {TTS_PORT}")
        
        self.running = True
        self.last_interrupt_time = 0
        self.interrupt_cooldown = 2.0  # Seconds between interrupts to prevent duplicates
    
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
            self.sub_socket.close()
            self.pub_socket.close()
            self.tts_socket.close()
            self.context.term()

if __name__ == "__main__":
    print("=== Streaming Interrupt Handler ===")
    print("Monitors partial transcripts for interruption keywords")
    print(f"Subscribing to partial transcripts on port {ZMQ_SUB_PORT}")
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
