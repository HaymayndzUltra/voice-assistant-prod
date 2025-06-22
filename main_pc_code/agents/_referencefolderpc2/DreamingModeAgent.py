import zmq
import json
import logging
import time
import random
from port_config import ENHANCED_MODEL_ROUTER_PORT

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DreamingModeAgent")

class DreamingModeAgent:
    def __init__(self):
        # Initialize ZMQ context and socket
        self.context = zmq.Context()
        self.model_socket = self.context.socket(zmq.REQ)
        self.model_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.model_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.model_socket.connect(f"tcp://localhost:{ENHANCED_MODEL_ROUTER_PORT}")  # EnhancedModelRouter
        
        # Initialize agent state
        self.is_dreaming = False
        self.dream_thread = None
        self.running = True
        self.dream_interval = 3600  # Default: dream once per hour
        self.last_dream_time = 0
        
    # Rest of the class implementation would follow... 