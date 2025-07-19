import zmq
import json
import logging
import time
import random
import threading
from datetime import datetime
from typing import Dict, Any

# Add project root to Python path for common_utils import
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import common utilities if available
try:
    from common_utils.zmq_helper import create_socket
from main_pc_code.utils.network_utils import get_zmq_connection_string, get_machine_ip
from common.env_helpers import get_env
    except ImportError as e:
        print(f"Import error: {e}")
    USE_COMMON_UTILS = True
except ImportError:
    USE_COMMON_UTILS = False



# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LearningAdjusterAgent")

class LearningAdjusterAgent:
    def __init__(self):

        self.name = "LearningAdjusterAgent"
        self.running = True
        self.start_time = time.time()
        self.health_port = self.port + 1

        
        # Start health check thread
        self._start_health_check()

        # Initialize ZMQ context and socket
        self.context = zmq.Context()
        self.trust_socket = self.context.socket(zmq.REQ)
        self.trust_socket.connect(get_zmq_connection_string(5590, "localhost")))  # AgentTrustScorer
        
        # Initialize agent state
        self.running = True
        self.adjustment_interval = 1800  # Default: adjust every 30 minutes
        self.last_adjustment_time = 0
        
    # Rest of the class implementation would follow... 
    def _start_health_check(self):
        """Start health check thread."""
        self.health_thread = threading.Thread(target=self._health_check_loop)
        self.health_thread.daemon = True
        self.health_thread.start()
        logging.info("Health check thread started")
    
    def _health_check_loop(self):
        """Background loop to handle health check requests."""
        logging.info("Health check loop started")
        
        while self.running:
            try:
                # Check for health check requests with timeout
                if self.health_socket.poll(100, zmq.POLLIN):
                    # Receive request (don't care about content)
                    _ = self.health_socket.recv()
                    
                    # Get health data
                    health_data = self._get_health_status()
                    
                    # Send response
                    self.health_socket.send_json(health_data)
                    
                time.sleep(0.1)  # Small sleep to prevent CPU hogging
                
            except Exception as e:
                logging.error(f"Error in health check loop: {e}")
                time.sleep(1)  # Sleep longer on error
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        uptime = time.time() - self.start_time
        
        return {
            "agent": self.name,
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "uptime": uptime
        }
