from src.core.base_agent import BaseAgent
"""
Streaming Language to LLM Connector
Connects the language analyzer to the LLM translation connector.
"""
import zmq
import pickle
import json
import time
import logging
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LanguageToLLMConnector")

# ZMQ settings
LANGUAGE_PORT = 5577  # Language analyzer output (updated)
LLM_INPUT_PORT = 5580  # LLM translator input

class StreamingLanguageToLLM(BaseAgent):
    """Connects language analyzer to LLM translation connector"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="StreamingLanguageToLlm")
        """Initialize the connector"""
        # Set up ZMQ context
        self.context = zmq.Context()
        
        # Socket to receive from language analyzer
        self.receiver = self.context.socket(zmq.SUB)
        self.receiver.connect(f"tcp://localhost:{LANGUAGE_PORT}")
        self.receiver.setsockopt(zmq.SUBSCRIBE, b"")
        
        # Socket to send to LLM connector
        self.sender = self.context.socket(zmq.PUB)
        self.sender.bind(f"tcp://*:{LLM_INPUT_PORT}")
        
        # Running flag
        self.running = False
        
        logger.info("Language to LLM Connector initialized")
    
    def start(self):
        """Start the connector"""
        self.running = True
        logger.info("Language to LLM Connector started")
        
        while self.running:
            try:
                # Receive message from language analyzer
                msg = self.receiver.recv(flags=zmq.NOBLOCK)
                print(f"[DEBUG] LanguageToLLM received raw msg: {msg}")
                logger.info(f"[DEBUG] LanguageToLLM received raw msg: {msg}")
                data = pickle.loads(msg)
                
                # Check if we have necessary data
                if 'transcription' in data and 'language_type' in data:
                    text = data.get('transcription', '')
                    language_type = data.get('language_type', 'unknown')
                    
                    logger.info(f"Received {language_type} text: {text}")
                    
                    # Forward to LLM connector
                    llm_msg = {
                        'type': 'translation_request',
                        'text': text,
                        'language_type': language_type,
                        'timestamp': time.time()
                    }
                    logger.info(f"DEBUG: Outgoing LLM message: {llm_msg}")
                    self.sender.send(pickle.dumps(llm_msg))
                    logger.info(f"Forwarded to LLM translator")
                    
            except zmq.Again:
                # No message available
                time.sleep(0.01)
            except Exception as e:
                logger.error(f"Error in connector: {e}")
                time.sleep(0.1)
    
    def stop(self):
        """Stop the connector"""
        self.running = False
        
        # Close sockets
        self.receiver.close()
        self.sender.close()
        
        logger.info("Language to LLM Connector stopped")

if __name__ == "__main__":
    logger.info("Starting Language to LLM Connector")
    connector = StreamingLanguageToLLM()
    
    try:
        connector.start()
    except KeyboardInterrupt:
        logger.info("Language to LLM Connector stopped by user")
    finally:
        connector.stop()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
