#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Chain of Thought Agent
This agent implements chain-of-thought reasoning for complex tasks
"""

import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Add project root to Python path for common_utils import
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import BaseAgent for standardized agent implementation
from main_pc_code.src.core.base_agent import BaseAgent

# Import common utilities if available
try:
    from common_utils.zmq_helper import create_socket
    USE_COMMON_UTILS = True
except ImportError:
    USE_COMMON_UTILS = False

import json
import logging
import zmq
import threading
from datetime import datetime
from typing import Dict, Any, Optional
import time
from utils.config_parser import parse_agent_args

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
args = parse_agent_args()

# Configure logging
logger = logging.getLogger("ChainOfThoughtAgent")

class ChainOfThoughtAgent(BaseAgent):
    def __init__(self, port: int = None):
        """Initialize the Chain of Thought Agent"""
        # Ensure port is properly set with a default value
        port_value = 5612  # Default port
        if port is not None:
            port_value = int(port)
        elif hasattr(args, 'port') and args.port is not None:
            try:
                port_value = int(args.port)
            except (ValueError, TypeError):
                logger.warning(f"Invalid port value from args: {args.port}, using default")
                port_value = 5612
            
        # Initialize BaseAgent with proper parameters
        super().__init__(name="ChainOfThoughtAgent", port=port_value)
        
        # Store instance variables
        self.name = "ChainOfThoughtAgent"
        self.port = port_value
        self.context = zmq.Context()
        self.running = True
        self.start_time = time.time()
        
        # Initialize main socket
        try:
            self.socket = self.context.socket(zmq.REP)
            self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.socket.bind(f"tcp://0.0.0.0:{self.port}")
            logger.info(f"Main socket bound to port {self.port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind main socket: {e}")
            raise
        
        # Initialize poller for timeouts
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
        
        logger.info(f"ChainOfThoughtAgent initialized on port {self.port}")
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        uptime = time.time() - self.start_time
        
        return {
            "agent": self.name,
            "status": "ok",
            "ready": True,
            "initialized": True,
            "message": "Chain of Thought Agent is healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime": uptime,
            "threads": {
                "health_thread": True  # This thread is running if we're here
            }
        }
        
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests"""
        try:
            request_type = request.get("action", "")
            
            if request_type in ["health_check", "health", "ping"]:
                return self._get_health_status()
            
            return {
                "status": "error",
                "message": f"Unknown request type: {request_type}"
            }
            
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def run(self):
        """Main agent loop"""
        try:
            logger.info("Starting main loop")
            while self.running:
                # Wait for request with timeout
                events = dict(self.poller.poll(1000))  # 1 second timeout
                
                if self.socket in events:
                    try:
                        # Receive request
                        request_str = self.socket.recv_string()
                        request = json.loads(request_str)
                        logger.debug(f"Received request: {request}")
                        
                        # Process request
                        response = self.handle_request(request)
                        
                        # Send response
                        self.socket.send_string(json.dumps(response))
                        logger.debug(f"Sent response: {response}")
                        
                    except Exception as e:
                        logger.error(f"Error processing request: {e}")
                        error_response = {
                            "status": "error",
                            "message": str(e)
                        }
                        try:
                            self.socket.send_string(json.dumps(error_response))
                        except zmq.error.ZMQError:
                            # Socket might be in a bad state, just continue
                            pass
                        
        except KeyboardInterrupt:
            logger.info("Shutting down Chain of Thought Agent...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up resources")
        
        # Set running flag to false to stop all threads
        self.running = False
        
        # Close sockets
        if hasattr(self, "socket"):
            self.socket.close()
            logger.info("Main socket closed")
            
        # Call parent cleanup to handle health check socket and other resources
        super().cleanup()
            
        logger.info("ChainOfThoughtAgent shutdown complete")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Start agent with default port
    agent = ChainOfThoughtAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("Agent stopped by user")
    finally:
        agent.cleanup()