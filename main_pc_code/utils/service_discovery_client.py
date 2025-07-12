#!/usr/bin/env python3
"""
Service Discovery Client

Provides a robust mechanism for agents to discover and connect to other services
in the distributed system. Implements retry logic, exponential backoff, and
graceful fallbacks.
"""

import os
import sys
import time
import random
import logging
import zmq
from typing import Dict, Any, Optional, Tuple, List, Union

from common.utils.path_env import get_project_root, get_main_pc_code, join_path
PROJECT_ROOT = get_project_root()
MAIN_PC_CODE = get_main_pc_code()
if MAIN_PC_CODE not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE)

from main_pc_code.utils.network_utils import get_machine_ip, is_local_mode

# Configure logging
logger = logging.getLogger(__name__)

class ServiceDiscoveryClient:
    """
    Client for discovering services in the distributed system.
    Implements robust retry logic and exponential backoff.
    """

    def __init__(self, sdt_port: int = 7120):
        """
        Initialize the service discovery client.
    
        Args:
            sdt_port: Port number for the SystemDigitalTwin service
        """
        self.sdt_port = sdt_port
        self.context = zmq.Context()
        self.timeout = int(os.environ.get("SERVICE_DISCOVERY_TIMEOUT", "5000"))  # ms
        self.max_retries = int(os.environ.get("SERVICE_DISCOVERY_RETRIES", "3"))
        self.secure = os.environ.get("ENABLE_SECURE_ZMQ", "").lower() in ("true", "1", "yes")
        self.local_mode = is_local_mode()
        
    def discover_service(self, service_name: str, machine: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Discover a service with exponential backoff retry logic.
        
        Args:
            service_name: Name of the service to discover
            machine: Machine where the service is running (None for any)
        
    Returns:
            Tuple of (success, service_info)
        """
        logger.info(f"Discovering service {service_name} via SystemDigitalTwin")
        
        # Determine the IP address for the SystemDigitalTwin
        sdt_ip = get_machine_ip("mainpc")
        
        # Use localhost in local mode
        if self.local_mode:
            sdt_ip = "127.0.0.1"
            logger.debug(f"Using local mode, connecting to SystemDigitalTwin at {sdt_ip}:{self.sdt_port}")
        
        # Construct the address
        address = f"tcp://{sdt_ip}:{self.sdt_port}"
        
        # Initialize retry parameters
        retries = 0
        backoff_time = 1.0
        
        while retries <= self.max_retries:
            try:
                # Create a new socket for each attempt
                socket = self.context.socket(zmq.REQ)
                socket.setsockopt(zmq.LINGER, 0)
                socket.setsockopt(zmq.RCVTIMEO, self.timeout)
        
        # Connect to the SystemDigitalTwin
                logger.info(f"Connecting to SystemDigitalTwin at {address} {'with' if self.secure else 'without'} security")
                socket.connect(address)
        
                # Prepare the discovery request
                request = {
                    "command": "DISCOVER",
                    "payload": {
                        "name": service_name
                    }
                }
                
                if machine:
                    request["payload"]["machine"] = machine
                
                # Send the request
                socket.send_json(request)
                
                # Wait for the response
                response = socket.recv_json()
                
                # Close the socket
                socket.close()
                
                # Check if the service was found
                if response.get("status") == "SUCCESS":
                    logger.info(f"Successfully discovered {service_name} at {response.get('payload', {}).get('ip')}:{response.get('payload', {}).get('port')}")
                    return True, response
                else:
                    error_msg = response.get("message", "Unknown error")
                    logger.warning(f"Failed to discover {service_name}: {error_msg}")
                    
                    # If the service is not registered, no need to retry
                    if "not registered" in error_msg.lower() or "not found" in error_msg.lower():
                        return False, response
                    
                    # Otherwise, retry with backoff
                    retries += 1
                    
            except zmq.error.Again:
                # Timeout occurred
                logger.error(f"Request to SystemDigitalTwin timed out")
                retries += 1
                
            except Exception as e:
                # Other error occurred
                logger.error(f"Error discovering service {service_name}: {e}")
                retries += 1
            
            # Close the socket if it's still open
            try:
                socket.close()
            except:
                pass
            
            # If we've reached the max retries, give up
            if retries > self.max_retries:
                break
                
            # Calculate backoff time with jitter
            jitter = random.uniform(0.8, 1.2)
            sleep_time = backoff_time * jitter
            logger.info(f"Retrying in {sleep_time:.2f} seconds (attempt {retries}/{self.max_retries})")
            time.sleep(sleep_time)
            
            # Exponential backoff
            backoff_time = min(backoff_time * 2, 10.0)
        
        # If we get here, all retries failed
        logger.error(f"Failed to discover {service_name} after {self.max_retries} attempts")
        return False, {"status": "error", "message": f"Failed after {self.max_retries} attempts"}
    
    def get_service_address(self, service_name: str, machine: str = None) -> Optional[str]:
        """
        Get the address of a service.
        
        Args:
            service_name: Name of the service to discover
            machine: Machine where the service is running (None for any)
            
        Returns:
            Service address as string, or None if not found
        """
        client = get_service_discovery_client()
        
        # Enhanced retry logic with multiple attempts
        max_discovery_attempts = 3
        base_wait_time = 2.0  # seconds
        
        for attempt in range(max_discovery_attempts):
            # Try to get the service address
            success, response = client.discover_service(service_name, machine)
            
            if success and isinstance(response, dict) and "payload" in response:
                service_info = response.get("payload", {})
                if isinstance(service_info, dict) and "ip" in service_info and "port" in service_info:
                    ip = service_info["ip"]
                    port = service_info["port"]
                    # If the IP is 0.0.0.0, use 127.0.0.1 for local connections
                    if ip == "0.0.0.0":
                        ip = "127.0.0.1"
                    return f"tcp://{ip}:{port}"
            
            # If not successful and not the last attempt, wait and retry
            if attempt < max_discovery_attempts - 1:
                wait_time = base_wait_time * (attempt + 1) * random.uniform(0.8, 1.2)
                logger.info(f"Service {service_name} not found, retrying in {wait_time:.2f} seconds (attempt {attempt+1}/{max_discovery_attempts})")
                time.sleep(wait_time)
        
        # If all attempts failed, try local mode fallback
        if client.local_mode:
            # Check if we have a port mapping for this service
            try:
                from main_pc_code.config.agent_ports import AGENT_PORTS
                if service_name in AGENT_PORTS:
                    port = AGENT_PORTS[service_name]
                    logger.info(f"Local mode fallback: using default port {port} for {service_name}")
                    return f"tcp://127.0.0.1:{port}"
            except ImportError:
                logger.warning("Could not import AGENT_PORTS for local mode fallback")
        
        logger.error(f"Failed to get address for service {service_name} after {max_discovery_attempts} attempts")
        return None
    
    def connect_to_service(self, service_name: str, machine: str = None, socket_type: int = zmq.REQ) -> Optional[zmq.Socket]:
        """
        Discover a service and connect to it.
        
        Args:
            service_name: Name of the service to discover
            machine: Machine where the service is running (None for any)
            socket_type: ZMQ socket type (default: REQ)
            
        Returns:
            Connected ZMQ socket, or None if connection failed
        """
        address = self.get_service_address(service_name, machine)
        
        if not address:
            logger.error(f"Failed to discover {service_name}")
            return None
        
        try:
            socket = self.context.socket(socket_type)
            socket.setsockopt(zmq.LINGER, 0)
            socket.setsockopt(zmq.RCVTIMEO, self.timeout)
            socket.connect(address)
            logger.info(f"Connected to {service_name} at {address}")
            return socket
        except Exception as e:
            logger.error(f"Error connecting to {service_name} at {address}: {e}")
            return None


# Singleton instance for convenience
_client = None

def get_service_discovery_client() -> ServiceDiscoveryClient:
    """
    Get the singleton instance of the service discovery client.
    
    Returns:
        ServiceDiscoveryClient instance
    """
    global _client
    if _client is None:
        _client = ServiceDiscoveryClient()
    return _client

def discover_service(service_name: str, machine: str = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Convenience function to discover a service.
    
    Args:
        service_name: Name of the service to discover
        machine: Machine where the service is running (None for any)
        
    Returns:
        Tuple of (success, service_info)
    """
    client = get_service_discovery_client()
    return client.discover_service(service_name, machine)

def get_service_address(service_name: str, machine: str = None) -> Optional[str]:
    """
    Convenience function to get the address of a service.
    
    Args:
        service_name: Name of the service to discover
        machine: Machine where the service is running (None for any)
        
    Returns:
        Service address as string, or None if not found
    """
    client = get_service_discovery_client()
    
    # Enhanced retry logic with multiple attempts
    max_discovery_attempts = 3
    base_wait_time = 2.0  # seconds
    
    for attempt in range(max_discovery_attempts):
        # Try to get the service address
        success, response = client.discover_service(service_name, machine)
        
        if success and isinstance(response, dict) and "payload" in response:
            service_info = response.get("payload", {})
            if isinstance(service_info, dict) and "ip" in service_info and "port" in service_info:
                ip = service_info["ip"]
                port = service_info["port"]
                # If the IP is 0.0.0.0, use 127.0.0.1 for local connections
                if ip == "0.0.0.0":
                    ip = "127.0.0.1"
                return f"tcp://{ip}:{port}"
        
        # If not successful and not the last attempt, wait and retry
        if attempt < max_discovery_attempts - 1:
            wait_time = base_wait_time * (attempt + 1) * random.uniform(0.8, 1.2)
            logger.info(f"Service {service_name} not found, retrying in {wait_time:.2f} seconds (attempt {attempt+1}/{max_discovery_attempts})")
            time.sleep(wait_time)
    
    # If all attempts failed, try local mode fallback
    if client.local_mode:
        # Check if we have a port mapping for this service
        try:
            from main_pc_code.config.agent_ports import AGENT_PORTS
            if service_name in AGENT_PORTS:
                port = AGENT_PORTS[service_name]
                logger.info(f"Local mode fallback: using default port {port} for {service_name}")
                return f"tcp://127.0.0.1:{port}"
        except ImportError:
            logger.warning("Could not import AGENT_PORTS for local mode fallback")
    
    logger.error(f"Failed to get address for service {service_name} after {max_discovery_attempts} attempts")
    return None

def connect_to_service(service_name: str, machine: str = None, socket_type: int = zmq.REQ) -> Optional[zmq.Socket]:
    """
    Convenience function to connect to a service.
    
    Args:
        service_name: Name of the service to discover
        machine: Machine where the service is running (None for any)
        socket_type: ZMQ socket type (default: REQ)
        
    Returns:
        Connected ZMQ socket, or None if connection failed
    """
    client = get_service_discovery_client()
    return client.connect_to_service(service_name, machine, socket_type)

def register_service(name: str, location: Optional[str] = None, 
                     ip: Optional[str] = None, port: Optional[int] = None,
                     additional_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Register this service with the SystemDigitalTwin service registry.
    
    Args:
        name: Name of the service/agent
        location: Location (MainPC/PC2), auto-detected if not provided
        ip: IP address, auto-detected if not provided
        port: Port number
        additional_info: Any additional information to store with the service
        
    Returns:
        Response dictionary from the SystemDigitalTwin
    """
    client = get_service_discovery_client()
    
    # Build the payload
    payload = {"name": name}
    
    # Add location if provided
    if location is not None:
        payload["location"] = location
    
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
    
    # Connect to SystemDigitalTwin
    socket = client.context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.RCVTIMEO, client.timeout)
    
    # Determine the IP address for the SystemDigitalTwin
    sdt_ip = get_machine_ip("mainpc")
    
    # Use localhost in local mode
    if client.local_mode:
        sdt_ip = "127.0.0.1"
    
    # Construct the address
    address = f"tcp://{sdt_ip}:{client.sdt_port}"
    
    try:
        # Connect to the SystemDigitalTwin
        socket.connect(address)
        
        # Send the request
        socket.send_json(request)
        
        # Wait for the response
        response = socket.recv_json()
        
        return response
    except Exception as e:
        logger.error(f"Error registering service {name}: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        socket.close()

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