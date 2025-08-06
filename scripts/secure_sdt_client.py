#!/usr/bin/env python3
"""
Secure SystemDigitalTwin Client

A simplified client that connects to SystemDigitalTwin using secure ZMQ.
"""

import os
import sys
import zmq
import json
import logging
import time
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
from common.env_helpers import get_env
from common.utils.log_setup import configure_logging

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging
logger = configure_logging(__name__)
logger = logging.getLogger("SecureSDTClient")

# ANSI color codes for terminal output
COLORS = {
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "RED": "\033[91m",
    "BLUE": "\033[94m",
    "PURPLE": "\033[95m",
    "CYAN": "\033[96m",
    "BOLD": "\033[1m",
    "END": "\033[0m"
}

class SecureSDTClient:
    def __init__(self, use_secure_zmq: bool = False, host: str = get_env("BIND_ADDRESS", "0.0.0.0"), port: int = 7120):
        """
        Initialize the secure client.
        
        Args:
            use_secure_zmq: Whether to use secure ZMQ
            host: Host address of SystemDigitalTwin
            port: Port number of SystemDigitalTwin
        """
        self.use_secure_zmq = use_secure_zmq
        self.host = host
        self.port = port
        self.context = None
        self.socket = None
        
        # Set environment variable for secure ZMQ
        os.environ["SECURE_ZMQ"] = "1" if use_secure_zmq else "0"
        logger.info(f"Secure ZMQ {'enabled' if use_secure_zmq else 'disabled'}")
        
    def connect(self) -> bool:
        """
        Connect to SystemDigitalTwin.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Create ZMQ context and socket
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REQ)
            
            # Set timeouts
            self.socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            self.socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5 second timeout
            
            # Configure secure ZMQ if enabled
            if self.use_secure_zmq:
                try:
                    logger.info("Importing secure ZMQ module...")
                    from main_pc_code.src.network.secure_zmq import secure_client_socket
                    logger.info("Configuring secure socket...")
                    self.socket = secure_client_socket(self.socket)
                    logger.info("Socket configured for secure communication")
                except Exception as e:
                    logger.error(f"Error configuring secure ZMQ: {e}")
                    return False
            
            # Connect to the server
            server_address = f"tcp://{self.host}:{self.port}"
            logger.info(f"Connecting to {server_address}...")
            self.socket.connect(server_address)
            logger.info("Connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to SystemDigitalTwin: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from SystemDigitalTwin."""
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
            
    def register_agent(self, agent_name: str, location: str = "PC2", status: str = "HEALTHY") -> bool:
        """
        Register an agent with SystemDigitalTwin.
        
        Args:
            agent_name: Name of the agent
            location: Location of the agent (MainPC/PC2)
            status: Status of the agent (HEALTHY/UNHEALTHY/NO_RESPONSE)
            
        Returns:
            bool: True if registration successful, False otherwise
        """
        try:
            # Prepare registration message
            register_msg = {
                "action": "register_agent",
                "agent_name": agent_name,
                "location": location,
                "status": status
            }
            
            # Send registration request
            logger.info(f"Registering agent: {register_msg}")
            self.socket.send_json(register_msg)
            
            # Wait for response
            try:
                response = self.socket.recv_json()
                logger.info(f"Registration response: {response}")
                if response.get("status") == "success":
                    logger.info(f"{COLORS['GREEN']}Successfully registered agent {agent_name}{COLORS['END']}")
                    return True
                else:
                    logger.warning(f"{COLORS['YELLOW']}Failed to register agent {agent_name}: {response.get('error', 'Unknown error')}{COLORS['END']}")
                    return False
            except zmq.error.Again:
                logger.error(f"{COLORS['RED']}Timeout waiting for registration response{COLORS['END']}")
                return False
                
        except Exception as e:
            logger.error(f"{COLORS['RED']}Error registering agent: {e}{COLORS['END']}")
            return False
            
    def get_all_status(self) -> Optional[Dict[str, Any]]:
        """
        Get the status of all registered agents.
        
        Returns:
            Dict with all registered agents or None if error
        """
        try:
            logger.info("Requesting status of all agents...")
            self.socket.send_string("GET_ALL_STATUS")
            
            try:
                response = self.socket.recv_json()
                logger.info(f"Received response with {len(response)} agents")
                return response
            except zmq.error.Again:
                logger.error(f"{COLORS['RED']}Timeout waiting for status response{COLORS['END']}")
                return None
                
        except Exception as e:
            logger.error(f"{COLORS['RED']}Error getting agent status: {e}{COLORS['END']}")
            return None
            
    def print_agent_status(self, agent_status: Dict[str, Any]):
        """
        Print the status of all agents.
        
        Args:
            agent_status: Dictionary with agent status information
        """
        print(f"\n{COLORS['BOLD']}{'=' * 80}{COLORS['END']}")
        print(f"{COLORS['BOLD']}{'AGENT STATUS':^80}{COLORS['END']}")
        print(f"{COLORS['BOLD']}{'=' * 80}{COLORS['END']}")
        
        if not agent_status:
            print(f"{COLORS['YELLOW']}No agents registered{COLORS['END']}")
            return
            
        # Print each agent
        for name, info in sorted(agent_status.items()):
            location = info.get("location", "Unknown")
            status = info.get("status", "Unknown")
            last_seen = info.get("last_seen", "N/A")
            
            # Format status with color
            if status == "HEALTHY":
                status_str = f"{COLORS['GREEN']}{status}{COLORS['END']}"
            elif status == "UNHEALTHY":
                status_str = f"{COLORS['RED']}{status}{COLORS['END']}"
            else:
                status_str = f"{COLORS['YELLOW']}{status}{COLORS['END']}"
                
            print(f"{COLORS['BOLD']}{name:<30}{COLORS['END']} | {location:<10} | {status_str:<30} | {last_seen}")
            
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Secure SystemDigitalTwin Client")
    parser.add_argument("--secure", action="store_true", help="Use secure ZMQ")
    parser.add_argument("--host", default=get_env("BIND_ADDRESS", "0.0.0.0"), help="SystemDigitalTwin host address")
    parser.add_argument("--port", type=int, default=7120, help="SystemDigitalTwin port number")
    parser.add_argument("--register", action="store_true", help="Register test agent")
    parser.add_argument("--agent-name", default="SecureTestAgent", help="Name of the test agent to register")
    
    args = parser.parse_args()
    
    # Print header
    print(f"{COLORS['BOLD']}Secure SystemDigitalTwin Client{COLORS['END']}")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Secure ZMQ: {COLORS['GREEN' if args.secure else 'RED']}{args.secure}{COLORS['END']}")
    print(f"Certificate Directory: {project_root / 'certificates'}")
    print()
    
    # Create client
    client = SecureSDTClient(use_secure_zmq=args.secure, host=args.host, port=args.port)
    
    # Connect to SystemDigitalTwin
    if not client.connect():
        sys.exit(1)
        
    try:
        # Register test agent if requested
        if args.register:
            if client.register_agent(args.agent_name):
                print(f"{COLORS['GREEN']}Agent {args.agent_name} registered successfully{COLORS['END']}")
            else:
                print(f"{COLORS['RED']}Failed to register agent {args.agent_name}{COLORS['END']}")
                
        # Get status of all agents
        status = client.get_all_status()
        if status:
            client.print_agent_status(status)
        else:
            print(f"{COLORS['RED']}Failed to get agent status{COLORS['END']}")
            
    finally:
        # Disconnect
        client.disconnect()
        
if __name__ == "__main__":
    main() 