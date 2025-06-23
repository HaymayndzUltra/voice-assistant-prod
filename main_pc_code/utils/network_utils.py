#!/usr/bin/env python3
"""
Network Configuration Utilities

This module provides functions to load and access the central network configuration
for the distributed AI system running across MainPC and PC2.
"""

import os
import sys
import yaml
import socket
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Construct the path relative to the project root to make it more robust
# This approach works regardless of where the script is imported from
PROJECT_ROOT = Path(os.path.abspath(__file__)).parent.parent.parent
CONFIG_PATH = os.path.join(PROJECT_ROOT, 'config', 'network_config.yaml')

def load_network_config() -> Optional[Dict[str, Any]]:
    """
    Loads the central network configuration from network_config.yaml.
    
    Returns:
        dict: A dictionary containing the network configuration, or None if an error occurs.
    """
    try:
        with open(os.path.abspath(CONFIG_PATH), 'r') as f:
            config = yaml.safe_load(f)
            logger.debug(f"Network configuration loaded successfully from {CONFIG_PATH}")
            return config
    except FileNotFoundError:
        logger.error(f"Network configuration file not found at {CONFIG_PATH}")
        return None
    except yaml.YAMLError as e:
        logger.error(f"Could not parse network_config.yaml: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading network config: {e}")
        return None

def get_mainpc_address(service_name: str = "system_digital_twin") -> str:
    """
    Gets the full address (host:port) for a service on MainPC.
    
    Args:
        service_name: Name of the service as defined in the ports section of the config file
                     Defaults to "system_digital_twin"
    
    Returns:
        str: TCP address string in format "tcp://host:port"
    """
    config = load_network_config()
    if not config:
        logger.warning("Network configuration not loaded. Falling back to localhost:7120")
        return "tcp://localhost:7120"
    
    host = config.get('main_pc_ip', 'localhost')
    port = config.get('ports', {}).get(service_name, 7120)
    
    return f"tcp://{host}:{port}"

def get_pc2_address(service_name: str = "unified_memory_reasoning") -> str:
    """
    Gets the full address (host:port) for a service on PC2.
    
    Args:
        service_name: Name of the service as defined in the ports section of the config file
                    Defaults to "unified_memory_reasoning"
    
    Returns:
        str: TCP address string in format "tcp://host:port"
    """
    config = load_network_config()
    if not config:
        logger.warning("Network configuration not loaded. Falling back to localhost:7230")
        return "tcp://localhost:7230"
    
    host = config.get('pc2_ip', 'localhost')
    port = config.get('ports', {}).get(service_name, 7230)
    
    return f"tcp://{host}:{port}"

def get_current_machine() -> str:
    """
    Determine which machine this code is running on (MainPC or PC2)
    by comparing the local IP address with the configured IPs.
    
    Returns:
        str: "MAINPC", "PC2", or "UNKNOWN"
    """
    config = load_network_config()
    if not config:
        return "UNKNOWN"
    
    try:
        # Get the local IP address by creating a temporary socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't need to be reachable, just to determine the outgoing interface
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        if local_ip == config.get('main_pc_ip'):
            return "MAINPC"
        elif local_ip == config.get('pc2_ip'):
            return "PC2"
        else:
            logger.warning(f"Local IP {local_ip} doesn't match any configured machine IP")
            return "UNKNOWN"
    except Exception as e:
        logger.error(f"Error determining current machine: {e}")
        return "UNKNOWN"

if __name__ == '__main__':
    # Configure logging for the test
    logging.basicConfig(level=logging.INFO, 
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # A simple test to ensure the loader works
    config = load_network_config()
    if config:
        print("Network configuration loaded successfully:")
        print(f"MainPC IP: {config.get('main_pc_ip')}")
        print(f"PC2 IP: {config.get('pc2_ip')}")
        print(f"System Digital Twin port: {config.get('ports', {}).get('system_digital_twin')}")
        
        print("\nUtility function tests:")
        print(f"MainPC SDT address: {get_mainpc_address()}")
        print(f"PC2 UMR address: {get_pc2_address()}")
        print(f"Current machine: {get_current_machine()}")
    else:
        print("Failed to load network configuration") 