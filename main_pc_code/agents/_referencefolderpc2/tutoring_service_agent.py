import os
import zmq
import json
import logging
from typing import Dict, Any, Optional
from config.system_config import get_service_host, get_service_port

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TutoringServiceAgent:
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.ROUTER)
        
        # Get host and port from environment or config
        self.host = get_service_host('tutoring_service', '0.0.0.0')
        self.port = get_service_port('tutoring_service', 5604)
        
        # Bind to all interfaces
        self.socket.bind(f"tcp://{self.host}:{self.port}")
        logger.info(f"Tutoring Service Agent listening on {self.host}:{self.port}")
        
        # Initialize service state
        self.service_state = {}
        
    def start(self):
        try:
            while True:
                # Receive message
                identity, _, message = self.socket.recv_multipart()
                message = json.loads(message.decode())
                
                # Process message
                response = self.process_message(message)
                
                # Send response
                self.socket.send_multipart([
                    identity,
                    b'',
                    json.dumps(response).encode()
                ])
                
        except KeyboardInterrupt:
            logger.info("Shutting down Tutoring Service Agent...")
        finally:
            self.socket.close()
            self.context.term()
            
    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        # Process message and return response
        return {"status": "success", "message": "Tutoring service updated"}
        
if __name__ == "__main__":
    agent = TutoringServiceAgent()
    agent.start() 