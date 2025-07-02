from main_pc_code.src.core.base_agent import BaseAgent
"""
Model Voting Adapter
-------------------
Handles integration between PC2's Enhanced Model Router and the main PC's voting system.
Ensures smooth communication and model selection across both systems.
"""
import zmq
import json
import logging
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Configure logging
LOG_PATH = "logs/model_voting_adapter.log"
Path(LOG_PATH).parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ModelVotingAdapter")

# Import the voting system
from lazy_voting import LazyVotingSystem
from model_voting_manager import ModelVotingManager

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

class ModelVotingAdapter(BaseAgent):
    """Adapter for integrating PC2's router with main PC's voting system"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ModelVotingAdapter")
        """Initialize the adapter
        
        Args:
            pc2_router_port: Port for PC2's Enhanced Model Router
            voting_port: Port for the voting system
        """
        # Initialize ZMQ context
        self.context = zmq.Context()
        
        # Connect to PC2's router
        self.pc2_socket = self.context.socket(zmq.REQ)
        self.pc2_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.pc2_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.pc2_socket.connect(f"tcp://192.168.1.2:{pc2_router_port}")
        logger.info(f"Connected to PC2's Enhanced Model Router on port {pc2_router_port}")
        
        # Initialize voting system
        self.voting_manager = ModelVotingManager(zmq_port=voting_port)
        logger.info(f"Initialized voting system on port {voting_port}")
        
        # Start voting manager in background
        self.voting_thread = threading.Thread(target=self.voting_manager.run)
        self.voting_thread.daemon = True
        self.voting_thread.start()
        
        # State tracking
        self.running = True
        self.request_count = 0
        self.last_request_time = None
        
        logger.info("Model Voting Adapter initialized successfully")
    
    def handle_pc2_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a request from PC2's router
        
        Args:
            request: Request data from PC2
            
        Returns:
            Response with voting results
        """
        self.request_count += 1
        self.last_request_time = time.time()
        
        try:
            # Extract task information
            task_type = request.get("type", "general")
            prompt = request.get("prompt", "")
            agent = request.get("agent")
            
            # Prepare voting request
            voting_request = {
                "prompt": prompt,
                "type": task_type,
                "agent": agent,
                "max_tokens": request.get("max_tokens", 1024),
                "temperature": request.get("temperature", 0.7),
                "request_id": f"pc2_req_{self.request_count}"
            }
            
            # Get voting results
            result = self.voting_manager.handle_request(voting_request)
            
            # Add metadata
            result["source"] = "model_voting_adapter"
            result["pc2_request_id"] = request.get("request_id")
            
            return result
            
        except Exception as e:
            logger.error(f"Error handling PC2 request: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "source": "model_voting_adapter"
            }
    
    def run(self):
        """Run the adapter service loop"""
        logger.info("Starting Model Voting Adapter service loop")
        
        while self.running:
            try:
                # Wait for request from PC2
                request_data = self.pc2_socket.recv_string()
                request = json.loads(request_data)
                
                # Process request
                result = self.handle_pc2_request(request)
                
                # Send response back to PC2
                self.pc2_socket.send_string(json.dumps(result))
                
            except Exception as e:
                logger.error(f"Error in service loop: {str(e)}")
                # Send error response
                try:
                    self.pc2_socket.send_string(json.dumps({
                        "status": "error",
                        "error": str(e),
                        "source": "model_voting_adapter"
                    }))
                except:
                    pass
    
    def stop(self):
        """Stop the adapter service"""
        self.running = False
        self.voting_manager.stop()
        logger.info("Model Voting Adapter stopped")

def main():
    """Main entry point"""
    adapter = ModelVotingAdapter()
    
    try:
        adapter.run()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        adapter.stop()

if __name__ == "__main__":
    main() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise