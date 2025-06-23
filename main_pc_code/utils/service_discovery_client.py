#!/usr/bin/env python3
"""
Service Discovery Client

This module provides client functions for agents to register themselves and discover other
agents in the distributed AI system via the SystemDigitalTwin service registry.
"""

import os
import sys
import json
import zmq
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union

# Set up logging
logger = logging.getLogger(__name__)

# Add project root to path to ensure imports work correctly
current_path = Path(__file__).resolve().parent
project_root = current_path.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import network utilities for configuration
from main_pc_code.utils.network_utils import get_mainpc_address, get_current_machine

# Default address for SystemDigitalTwin - will be overridden by get_mainpc_address
SDT_ADDRESS = "tcp://localhost:7120"

def _create_sdt_socket(timeout_ms: int = 5000, manual_sdt_address: str = None) -> zmq.Socket:
    """
    Create and configure a socket for communicating with SystemDigitalTwin.
    
    Args:
        timeout_ms: Socket timeout in milliseconds
        manual_sdt_address: Optional manual override for SDT address
        
    Returns:
        Configured ZMQ socket
    """
    try:
        # Create new context and socket
        context = zmq.Context.instance()
        socket = context.socket(zmq.REQ)
        
        # Set timeout to avoid blocking indefinitely
        socket.setsockopt(zmq.RCVTIMEO, timeout_ms)
        socket.setsockopt(zmq.SNDTIMEO, timeout_ms)
        
        # Get the address for SystemDigitalTwin
        if manual_sdt_address:
            sdt_address = manual_sdt_address
            logger.info(f"Using manually specified SDT address: {sdt_address}")
        else:
            # Try to get the configured address
            try:
                sdt_address = get_mainpc_address("system_digital_twin")
                # Detect if we're likely running locally
                this_machine = get_current_machine()
                if this_machine == "MainPC" or (os.environ.get("FORCE_LOCAL_SDT", "0") == "1"):
                    # If we're on MainPC, use localhost for better reliability
                    local_port = sdt_address.split(":")[-1]
                    sdt_address = f"tcp://localhost:{local_port}"
                    logger.info(f"Running on MainPC or local mode forced, using localhost: {sdt_address}")
            except Exception as e:
                logger.warning(f"Failed to get MainPC address: {e}, falling back to localhost:7120")
                sdt_address = "tcp://localhost:7120"
        
        logger.debug(f"Connecting to SystemDigitalTwin at {sdt_address}")
        
        # Check if secure ZMQ is enabled
        secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"
        if secure_zmq:
            try:
                # Import the secure ZMQ module
                from main_pc_code.src.network.secure_zmq import configure_secure_client, start_auth
                
                # Start the authenticator if needed
                start_auth()
                
                # Configure socket with CURVE security
                logger.debug("Configuring secure ZMQ connection")
                socket = configure_secure_client(socket)
                logger.debug("Secure ZMQ configured successfully")
            except ImportError as e:
                logger.warning(f"Failed to import secure ZMQ module: {e}, using standard ZMQ")
                secure_zmq = False  # Fallback to standard ZMQ
            except Exception as e:
                logger.warning(f"Error configuring secure ZMQ: {e}, using standard ZMQ")
                secure_zmq = False  # Fallback to standard ZMQ
        
        # Connect to the SystemDigitalTwin
        logger.info(f"Connecting to SystemDigitalTwin at {sdt_address} {'' if secure_zmq else 'without security'}")
        socket.connect(sdt_address)
        
        # Verify connection by testing a simple ping
        verify_connection = False  # Set to True for connection verification (may impact performance)
        
        if verify_connection:
            try:
                logger.debug("Verifying connection with ping...")
                if secure_zmq:
                    socket.send(b"ping")
                else:
                    socket.send_string("ping")
                    
                # Set a shorter timeout for the verification
                socket.setsockopt(zmq.RCVTIMEO, 1000)
                resp = socket.recv_string()
                socket.setsockopt(zmq.RCVTIMEO, timeout_ms)  # Reset timeout
                
                if resp == "pong":
                    logger.debug("Connection verified!")
                else:
                    logger.warning(f"Unexpected ping response: {resp}")
                    
            except zmq.error.Again:
                logger.warning("Connection verification failed (timeout)")
            except Exception as e:
                logger.warning(f"Connection verification failed: {e}")
        
        return socket
        
    except Exception as e:
        logger.error(f"Failed to create socket for SystemDigitalTwin: {e}")
        raise

def _send_request(request: Dict[str, Any], manual_sdt_address: str = None) -> Dict[str, Any]:
    """
    Send a request to SystemDigitalTwin and get the response.
    
    Args:
        request: The request dictionary to send
        manual_sdt_address: Optional manual override for SDT address
        
    Returns:
        The response dictionary
    """
    socket = None
    try:
        # Create a new socket
        socket = _create_sdt_socket(manual_sdt_address=manual_sdt_address)
        
        # Serialize the request to JSON
        request_json = json.dumps(request)
        
        # Send the request
        logger.debug(f"Sending request to SystemDigitalTwin: {request}")
        
        # Check if using secure ZMQ
        secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"
        if secure_zmq:
            # For secure connections, send as bytes
            socket.send(request_json.encode('utf-8'))
            logger.debug("Request sent using secure ZMQ")
        else:
            # For non-secure connections, use send_json
            socket.send_json(request)
            logger.debug("Request sent using standard ZMQ")
        
        # Wait for and parse the response
        # Always try to receive as JSON first, which works for both secure and non-secure
        try:
            response = socket.recv_json()
            logger.debug(f"Received JSON response: {response}")
            return response
        except zmq.error.Again:
            logger.error("Request to SystemDigitalTwin timed out")
            return {"status": "ERROR", "message": "Request to SystemDigitalTwin timed out"}
        except ValueError as e:
            # If recv_json fails, try receiving raw data and parsing manually
            logger.warning(f"Failed to receive JSON response: {e}")
            try:
                raw_response = socket.recv()
                response_str = raw_response.decode('utf-8')
                logger.debug(f"Received raw response: {response_str}")
                return json.loads(response_str)
            except Exception as parse_err:
                logger.error(f"Failed to parse response: {parse_err}")
                return {"status": "ERROR", "message": f"Failed to parse response: {parse_err}"}
        
    except zmq.error.Again:
        logger.error("Request to SystemDigitalTwin timed out")
        return {"status": "ERROR", "message": "Request to SystemDigitalTwin timed out"}
    except Exception as e:
        logger.error(f"Error communicating with SystemDigitalTwin: {e}")
        return {"status": "ERROR", "message": str(e)}
    finally:
        if socket:
            socket.close()

def register_service(name: str, location: Optional[str] = None, 
                     ip: Optional[str] = None, port: Optional[int] = None,
                     additional_info: Optional[Dict[str, Any]] = None,
                     manual_sdt_address: Optional[str] = None) -> Dict[str, Any]:
    """
    Register this service with the SystemDigitalTwin service registry.
    
    Args:
        name: Name of the service/agent
        location: Location (MainPC/PC2), auto-detected if not provided
        ip: IP address, auto-detected if not provided
        port: Port number
        additional_info: Any additional information to store with the service
        manual_sdt_address: Optional manual override for SDT address
        
    Returns:
        Response dictionary from the SystemDigitalTwin
    """
    # Auto-detect location if not provided
    if location is None:
        location = get_current_machine()
    
    # Build the payload
    payload = {"name": name, "location": location}
    
    # Add IP if provided
    if ip is not None:
        payload["ip"] = ip
    
    # Add port if provided
    if port is not None:
        payload["port"] = port
    
    # Add any additional information
    if additional_info and isinstance(additional_info, dict):
        payload.update(additional_info)
    
    # Create the request
    request = {"command": "REGISTER", "payload": payload}
    
    # Send the request
    logger.info(f"Registering service {name} with SystemDigitalTwin")
    return _send_request(request, manual_sdt_address=manual_sdt_address)

def discover_service(name: str, manual_sdt_address: Optional[str] = None) -> Dict[str, Any]:
    """
    Discover a service from the SystemDigitalTwin registry.
    
    Args:
        name: Name of the service/agent to discover
        manual_sdt_address: Optional manual override for SDT address
        
    Returns:
        Response dictionary containing:
        - status: "SUCCESS" or error status
        - payload: Service information if found
        - message: Error message if status is not "SUCCESS"
    """
    # Create the request
    request = {"command": "DISCOVER", "payload": {"name": name}}
    
    # Send the request
    logger.info(f"Discovering service {name} via SystemDigitalTwin")
    return _send_request(request, manual_sdt_address=manual_sdt_address)

def get_service_address(name: str, manual_sdt_address: Optional[str] = None) -> Optional[str]:
    """
    Get the full ZMQ address for a service.
    
    Args:
        name: Name of the service/agent to discover
        manual_sdt_address: Optional manual override for SDT address
        
    Returns:
        String address in format "tcp://ip:port" if service is found,
        None otherwise
    """
    response = discover_service(name, manual_sdt_address=manual_sdt_address)
    
    if response.get("status") == "SUCCESS" and "payload" in response:
        service_info = response["payload"]
        if "ip" in service_info and "port" in service_info:
            return f"tcp://{service_info['ip']}:{service_info['port']}"
    
    logger.warning(f"Failed to get address for service {name}: {response.get('message', 'Unknown error')}")
    return None

if __name__ == "__main__":
    # Set up logging for the test
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test the service discovery client
    print("Testing service discovery client...")
    
    # Try to register a test service
    register_response = register_service(
        name="TestService",
        port=9999,
        additional_info={"capabilities": ["test", "debug"]}
    )
    print(f"Register response: {register_response}")
    
    # Try to discover the test service
    discover_response = discover_service("TestService")
    print(f"Discover response: {discover_response}")
    
    # Try to get the address
    address = get_service_address("TestService")
    print(f"Service address: {address}") 