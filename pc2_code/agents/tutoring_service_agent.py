import os
import zmq
import json
import logging
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
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
        self.name = "TutoringServiceAgent"
        self.running = True
        self.start_time = time.time()
        self.health_port = self.port + 1
        
        # Bind to all interfaces
        self.socket.bind(f"tcp://{self.host}:{self.port}")
        
        # Initialize health check socket
        try:
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            self.health_socket.bind(f"tcp://0.0.0.0:{self.health_port}")
            logger.info(f"Health check socket bound to port {self.health_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind health check socket: {e}")
            raise
            
        logger.info(f"Tutoring Service Agent listening on {self.host}:{self.port}")
        
        # Initialize service state
        self.service_state = {}
        
        # Start health check thread
        self._start_health_check()
        
    def _start_health_check(self):
        """Start health check thread."""
        self.health_thread = threading.Thread(target=self._health_check_loop)
        self.health_thread.daemon = True
        self.health_thread.start()
        logger.info("Health check thread started")
    
    def _health_check_loop(self):
        """Background loop to handle health check requests."""
        logger.info("Health check loop started")
        
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
                logger.error(f"Error in health check loop: {e}")
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
            self.stop()
            
    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        # Handle health check requests
        if message.get('action') in ["health_check", "health", "ping"]:
            return self._get_health_status()
            
        # Process message and return response
        return {"status": "success", "message": "Tutoring service updated"}
    
    def stop(self):
        """Stop the agent and clean up resources."""
        # Set running flag to false to stop all threads
        self.running = False
        
        # Wait for threads to finish
        if hasattr(self, 'health_thread') and self.health_thread.is_alive():
            self.health_thread.join(timeout=2.0)
            logger.info("Health thread joined")
        
        # Close health socket if it exists
        if hasattr(self, "health_socket"):
            self.health_socket.close()
            logger.info("Health socket closed")
            
        self.socket.close()
        self.context.term()
        
if __name__ == "__main__":
    agent = TutoringServiceAgent()
    try:
        agent.start()
    except KeyboardInterrupt:
        agent.stop() 