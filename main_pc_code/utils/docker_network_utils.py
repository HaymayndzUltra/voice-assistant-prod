#!/usr/bin/env python3
"""
Docker Network Utilities

This module provides functions to handle Docker networking for service discovery.
It extends the existing network_utils.py to work in a Docker environment.
"""

import os
import socket
import logging
import yaml

# Import the environment loader
from main_pc_code.utils.env_loader import get_env
from common.env_helpers import get_env
from common.utils.log_setup import configure_logging

# Set up logging
logger = logging.getLogger(__name__)

def get_container_hostname() -> str:
    """
    Get the hostname of the current container.
    
    Returns:
        str: The hostname of the container
    """
    return socket.gethostname()

def get_container_ip() -> str:
    """
    Get the IP address of the current container.
    
    Returns:
        str: The IP address of the container
    """
    try:
        # This works in Docker networks
        hostname = get_container_hostname()
        return socket.gethostbyname(hostname)
    except Exception as e:
        logger.warning(f"Could not get container IP: {e}, falling back to localhost")
        return "localhost"

def get_service_host(service_name: str) -> str:
    """
    Get the host for a service in Docker.
    
    In Docker Compose, services can be addressed by their service name.
    This function converts a service name to the appropriate Docker service name.
    
    Args:
        service_name: Name of the service
        
    Returns:
        str: The host address for the service
    """
    # Convert CamelCase to kebab-case for Docker service names
    import re
    
    # Handle special case for SystemDigitalTwin
    if service_name == "SystemDigitalTwin":
        return "system-digital-twin"
    
    # Convert CamelCase to kebab-case
    kebab_name = re.sub(r'(?<!^)(?=[A-Z])', '-', service_name).lower()
    
    # Remove "Agent" suffix if present
    kebab_name = kebab_name.replace('-agent', '')
    
    return kebab_name

def get_service_address(service_name: str) -> str:
    """
    Get the full address (host:port) for a service in Docker.
    
    Args:
        service_name: Name of the service
        
    Returns:
        str: TCP address string in format "tcp://host:port"
    """
    # Get the Docker service name
    host = get_service_host(service_name)
    
    # Get the port from environment variables or use default
    port_env_name = f"{service_name.upper()}_PORT"
    port = get_env(port_env_name)
    
    # If port is not defined in environment, use some common mappings
    if not port:
        common_ports = {
            "SystemDigitalTwin": 7120,
            "TaskRouter": 8571,
            "StreamingTTSAgent": 5562,
            "TTSAgent": 5563,
            "ResponderAgent": 5637,
            "StreamingInterruptHandler": 5576
        }
        port = common_ports.get(service_name, 5000)
    
    return f"tcp://{host}:{port}"

def is_running_in_docker() -> bool:
    """
    Check if the code is running inside a Docker container.
    
    Returns:
        bool: True if running in Docker, False otherwise
    """
    # Check for .dockerenv file
    if os.path.exists('/.dockerenv'):
        return True
    
    # Check for cgroup
    try:
        with open('/proc/1/cgroup', 'r') as f:
            return 'docker' in f.read()
    except:
        pass
    
    return False

def update_network_config_for_docker():
    """
    Update the network configuration for Docker.
    
    This function updates the network_config.yaml file to use Docker service names
    instead of IP addresses.
    """
    config_path = os.path.join(os.environ.get('PYTHONPATH', ''), 'config', 'network_config.yaml')
    
    try:
        # Load the existing configuration
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Update for Docker
        config['main_pc_ip'] = 'system-digital-twin'
        config['pc2_ip'] = 'pc2-service'
        config['bind_address'] = '0.0.0.0'
        
        # Write back the updated configuration
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
            
        logger.info("Updated network configuration for Docker")
    except Exception as e:
        logger.error(f"Error updating network configuration for Docker: {e}")

# Initialize Docker network if running in Docker
if is_running_in_docker():
    logger.info("Running in Docker environment")
    update_network_config_for_docker()
else:
    logger.info("Not running in Docker environment")

if __name__ == '__main__':
    # Configure logging for the test
    logger = configure_logging(__name__)
    
    # Print Docker network information
    print(f"Running in Docker: {is_running_in_docker()}")
    print(f"Container hostname: {get_container_hostname()}")
    print(f"Container IP: {get_container_ip()}")
    
    # Test service address resolution
    services = ["SystemDigitalTwin", "TaskRouter", "StreamingTTSAgent", "TTSAgent"]
    for service in services:
        print(f"{service} address: {get_service_address(service)}") 