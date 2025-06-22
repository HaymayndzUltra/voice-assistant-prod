#!/usr/bin/env python
"""
Secure Agent Template
--------------------
This is a template for implementing secure ZMQ communication in agents.
It demonstrates how to modify existing agents to use CURVE security.
"""

import os
import sys
import zmq
import json
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Import secure ZMQ module
from src.network.secure_zmq import (
    secure_server_socket,
    secure_client_socket,
    start_auth,
    stop_auth,
    create_secure_context
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SecureAgentTemplate")

class SecureAgent:
    """
    Template for a secure agent using ZMQ CURVE security.
    """
    
    def __init__(self, name="SecureAgent", port=5555):
        """
        Initialize the secure agent.
        
        Args:
            name: The name of the agent
            port: The port to bind/connect to
        """
        self.name = name
        self.port = port
        
        # Check if we should use secure ZMQ
        self.use_secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"
        
        # Initialize ZMQ context
        if self.use_secure_zmq:
            logger.info("Initializing secure ZMQ context")
            self.context = create_secure_context()
        else:
            logger.info("Initializing standard ZMQ context")
            self.context = zmq.Context()
    
    def create_server_socket(self, socket_type=zmq.REP):
        """
        Create a secure server socket (REP, PUB, etc.).
        
        Args:
            socket_type: The ZMQ socket type
            
        Returns:
            A configured ZMQ socket
        """
        socket = self.context.socket(socket_type)
        
        if self.use_secure_zmq:
            logger.info("Configuring socket as secure CURVE server")
            socket = secure_server_socket(socket)
        
        # Bind the socket
        socket.bind(f"tcp://*:{self.port}")
        logger.info(f"Server socket bound to port {self.port}")
        
        return socket
    
    def create_client_socket(self, server_address, socket_type=zmq.REQ):
        """
        Create a secure client socket (REQ, SUB, etc.).
        
        Args:
            server_address: The address of the server to connect to
            socket_type: The ZMQ socket type
            
        Returns:
            A configured ZMQ socket
        """
        socket = self.context.socket(socket_type)
        
        if self.use_secure_zmq:
            logger.info("Configuring socket as secure CURVE client")
            socket = secure_client_socket(socket)
        
        # Connect the socket
        socket.connect(server_address)
        logger.info(f"Client socket connected to {server_address}")
        
        return socket
    
    def start(self):
        """
        Start the agent.
        This is a template method to be implemented by subclasses.
        """
        if self.use_secure_zmq:
            # Start the authenticator if not already started
            start_auth()
        
        logger.info(f"{self.name} started")
    
    def stop(self):
        """
        Stop the agent.
        This is a template method to be implemented by subclasses.
        """
        if self.use_secure_zmq:
            # Stop the authenticator
            stop_auth()
        
        logger.info(f"{self.name} stopped")


# Example implementation of a secure server agent
class SecureServerAgent(SecureAgent):
    """Example of a secure server agent."""
    
    def __init__(self, name="SecureServerAgent", port=5555):
        """Initialize the secure server agent."""
        super().__init__(name, port)
        self.socket = None
    
    def start(self):
        """Start the secure server agent."""
        super().start()
        
        # Create a REP socket
        self.socket = self.create_server_socket(zmq.REP)
        
        # Main loop
        try:
            while True:
                # Wait for a request
                message = self.socket.recv_json()
                logger.info(f"Received request: {message}")
                
                # Process the request
                response = {"status": "success", "message": "Request processed"}
                
                # Send the response
                self.socket.send_json(response)
                logger.info(f"Sent response: {response}")
                
        except KeyboardInterrupt:
            logger.info("Interrupted")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the secure server agent."""
        if self.socket:
            self.socket.close()
        
        super().stop()


# Example implementation of a secure client agent
class SecureClientAgent(SecureAgent):
    """Example of a secure client agent."""
    
    def __init__(self, name="SecureClientAgent", server_address="tcp://localhost:5555"):
        """Initialize the secure client agent."""
        super().__init__(name)
        self.server_address = server_address
        self.socket = None
    
    def start(self):
        """Start the secure client agent."""
        super().start()
        
        # Create a REQ socket
        self.socket = self.create_client_socket(self.server_address, zmq.REQ)
        
        # Send a request
        request = {"action": "test", "data": {"message": "Hello, secure world!"}}
        logger.info(f"Sending request: {request}")
        self.socket.send_json(request)
        
        # Wait for the response
        response = self.socket.recv_json()
        logger.info(f"Received response: {response}")
        
        self.stop()
    
    def stop(self):
        """Stop the secure client agent."""
        if self.socket:
            self.socket.close()
        
        super().stop()


def main():
    """Main function to demonstrate secure agent usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Secure Agent Template")
    parser.add_argument("--mode", choices=["server", "client"], default="server",
                      help="Run as server or client")
    parser.add_argument("--port", type=int, default=5555,
                      help="Port to bind/connect to")
    parser.add_argument("--address", default="tcp://localhost:5555",
                      help="Server address for client mode")
    
    args = parser.parse_args()
    
    if args.mode == "server":
        agent = SecureServerAgent(port=args.port)
    else:
        agent = SecureClientAgent(server_address=args.address)
    
    agent.start()


if __name__ == "__main__":
    main()

 