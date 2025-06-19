#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Chain of Thought Agent
This agent implements chain-of-thought reasoning for complex tasks
"""

import os
import json
import logging
import zmq
from typing import Dict, Any, Optional
import time

# Configure logging
logger = logging.getLogger("ChainOfThoughtAgent")

class ChainOfThoughtAgent:
    def __init__(self, port: int = 5612):
        """Initialize the Chain of Thought Agent"""
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://0.0.0.0:{self.port}")
        
        # Initialize poller for timeouts
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
        
        logger.info(f"ChainOfThoughtAgent initialized on port {self.port}")
        
    def handle_health_check(self) -> Dict[str, Any]:
        """Handle health check request"""
        return {
            "status": "ok",
            "ready": True,
            "initialized": True,
            "message": "Chain of Thought Agent is healthy",
            "timestamp": time.time(),
            "agent": "ChainOfThoughtAgent"
        }
        
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests"""
        try:
            request_type = request.get("action", "")
            
            if request_type in ["health_check", "health", "ping"]:
                return self.handle_health_check()
            
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
            while True:
                # Wait for request with timeout
                events = dict(self.poller.poll(1000))  # 1 second timeout
                
                if self.socket in events:
                    try:
                        # Receive request
                        request_str = self.socket.recv_string()
                        request = json.loads(request_str)
                        
                        # Process request
                        response = self.handle_request(request)
                        
                        # Send response
                        self.socket.send_string(json.dumps(response))
                        
                    except Exception as e:
                        logger.error(f"Error processing request: {e}")
                        error_response = {
                            "status": "error",
                            "message": str(e)
                        }
                        self.socket.send_string(json.dumps(error_response))
                        
        except KeyboardInterrupt:
            logger.info("Shutting down Chain of Thought Agent...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, "socket"):
            self.socket.close()
        if hasattr(self, "context"):
            self.context.term()
        logger.info("ChainOfThoughtAgent shutdown complete")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Start agent with default port
    agent = ChainOfThoughtAgent()
    agent.run()
