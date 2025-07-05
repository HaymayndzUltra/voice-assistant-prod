#!/usr/bin/env python3
"""
Template Agent Implementation

This is a robust template for agent implementation that properly handles:
1. ZMQ socket binding and configuration
2. Health check responses
3. Error handling and graceful termination
4. Environment variable configuration
5. Path resolution

Use this as a reference when fixing Layer 0 agents.
"""

import os
import sys
import time
import zmq
import json
import signal
import logging
import threading
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('template_agent.log')
    ]
)

class TemplateAgent:
    """Template Agent class with proper health check and error handling"""
    
    def __init__(self, name="TemplateAgent", port=None):
        """Initialize the agent with proper error handling"""
        # Setup logging
        self.logger = logging.getLogger(name)
        
        # Basic configuration
        self.name = name
        self.port = port or int(os.environ.get("AGENT_PORT", "7777"))
        self.health_port = int(os.environ.get("HEALTH_CHECK_PORT", str(self.port + 1)))
        self.running = True
        self.start_time = time.time()
        
        # Get project root
        self.project_root = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.abspath(__file__)))
        
        # Add project root to Python path
        if self.project_root not in sys.path:
            sys.path.insert(0, self.project_root)
        
        # Initialize ZMQ
        self.context = None
        self.socket = None
        self.health_socket = None
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info(f"Initialized {self.name} on port {self.port} (health: {self.health_port})")
    
    def _signal_handler(self, sig, frame):
        """Handle signals for graceful termination"""
        self.logger.info(f"Received signal {sig}, shutting down")
        self.running = False
        time.sleep(1)  # Give threads time to notice
        self.cleanup()
        sys.exit(0)
    
    def setup_zmq(self):
        """Set up ZMQ sockets with proper error handling"""
        try:
            self.context = zmq.Context()
            
            # Main socket
            self.socket = self.context.socket(zmq.REP)
            self.socket.setsockopt(zmq.LINGER, 0)
            self.socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            
            # Health socket
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.setsockopt(zmq.LINGER, 0)
            self.health_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            
            # Bind sockets with retry logic
            self._bind_socket_with_retry(self.socket, self.port)
            self._bind_socket_with_retry(self.health_socket, self.health_port)
            
            return True
        except Exception as e:
            self.logger.error(f"Error setting up ZMQ: {e}")
            self.cleanup()
            return False
    
    def _bind_socket_with_retry(self, socket, port, max_retries=5):
        """Bind a socket with retry logic"""
        retries = 0
        while retries < max_retries:
            try:
                socket.bind(f"tcp://*:{port}")
                self.logger.info(f"Successfully bound to port {port}")
                return True
            except zmq.error.ZMQError as e:
                retries += 1
                self.logger.warning(f"Failed to bind to port {port} (attempt {retries}/{max_retries}): {e}")
                if retries >= max_retries:
                    self.logger.error(f"Failed to bind to port {port} after {max_retries} attempts")
                    raise
                time.sleep(1)  # Wait before retrying
        return False
    
    def _health_check_loop(self):
        """Health check loop with proper error handling"""
        self.logger.info("Starting health check loop")
        
        while self.running:
            try:
                # Check for health check requests with timeout
                if self.health_socket.poll(100) != 0:
                    # Receive request (don't care about content)
                    message = self.health_socket.recv()
                    self.logger.debug(f"Received health check request: {message}")
                    
                    # Send response
                    response = {
                        "status": "ok",
                        "name": self.name,
                        "uptime": time.time() - self.start_time
                    }
                    self.health_socket.send_json(response)
                    self.logger.debug("Sent health check response")
            except zmq.error.Again:
                # Timeout on receive, this is normal
                pass
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
            
            time.sleep(0.1)
    
    def run(self):
        """Main run loop with proper error handling"""
        self.logger.info(f"Starting {self.name}")
        
        # Setup ZMQ
        if not self.setup_zmq():
            self.logger.error("Failed to set up ZMQ, exiting")
            return
        
        # Start health check thread
        health_thread = threading.Thread(target=self._health_check_loop)
        health_thread.daemon = True
        health_thread.start()
        
        try:
            while self.running:
                try:
                    # Check for main socket messages with timeout
                    if self.socket.poll(1000) != 0:
                        # Receive request
                        message = self.socket.recv()
                        self.logger.info(f"Received message: {message}")
                        
                        # Process message (replace with your agent's logic)
                        response = self.process_message(message)
                        
                        # Send response
                        self.socket.send_json(response)
                        self.logger.info("Sent response")
                except zmq.error.Again:
                    # Timeout on receive, this is normal
                    pass
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
                
                # Periodic status logging
                if int(time.time()) % 30 == 0:  # Log every 30 seconds
                    self.logger.info(f"{self.name} is running (uptime: {time.time() - self.start_time:.1f}s)")
                    time.sleep(1)  # Avoid multiple logs in the same second
                else:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        finally:
            self.cleanup()
    
    def process_message(self, message):
        """Process a received message (override this in your agent)"""
        # Default implementation just echoes the message
        try:
            decoded = message.decode('utf-8')
            return {
                "status": "ok",
                "message": f"Processed: {decoded}",
                "agent": self.name
            }
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return {
                "status": "error",
                "message": str(e),
                "agent": self.name
            }
    
    def cleanup(self):
        """Clean up resources with proper error handling"""
        self.logger.info("Cleaning up resources")
        self.running = False
        
        # Close sockets
        if hasattr(self, 'socket') and self.socket:
            try:
                self.socket.close()
            except Exception as e:
                self.logger.error(f"Error closing main socket: {e}")
        
        if hasattr(self, 'health_socket') and self.health_socket:
            try:
                self.health_socket.close()
            except Exception as e:
                self.logger.error(f"Error closing health socket: {e}")
        
        # Terminate context
        if hasattr(self, 'context') and self.context:
            try:
                self.context.term()
            except Exception as e:
                self.logger.error(f"Error terminating ZMQ context: {e}")
        
        self.logger.info(f"{self.name} stopped")

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Template Agent')
    parser.add_argument('--name', type=str, default="TemplateAgent", help='Agent name')
    parser.add_argument('--port', type=int, default=None, help='Agent port')
    args = parser.parse_args()
    
    # Create and run the agent
    agent = TemplateAgent(name=args.name, port=args.port)
    agent.run() 