#!/usr/bin/env python3
"""
Network Utilities

Provides functions for network configuration and machine identification.
"""

import os
import sys
import yaml
import logging
import netifaces
from typing import Dict, Any, Optional


# Import path manager for containerization-friendly paths
from common.utils.path_env import get_path, join_path, get_file_path, get_project_root, get_main_pc_code
# Add the project's main_pc_code directory to the Python path
PROJECT_ROOT = get_project_root()
MAIN_PC_CODE = get_main_pc_code()
if str(MAIN_PC_CODE) not in sys.path:
    sys.path.insert(0, str(MAIN_PC_CODE))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Configure logging
logger = logging.getLogger(__name__)

# Global cache for network configuration
_network_config = None

def load_network_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load network configuration from YAML file.
    
    Args:
        config_path: Path to the configuration file, or None to use default
        
    Returns:
        Dictionary containing network configuration
    """
    global _network_config
    
    # Return cached configuration if available
    if _network_config is not None:
        return _network_config
    
    # Use default path if not specified
    if config_path is None:
        config_path = os.environ.get(
            "NETWORK_CONFIG_PATH", 
            join_path("config", "network_config.yaml")
        )
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Get environment type
        env_type = os.environ.get("ENV_TYPE", "development")
        
        # Load environment-specific configuration
        if "environment" in config and env_type in config["environment"]:
            env_config = config["environment"][env_type]
            
            # Override with environment variables
            for key, value in env_config.items():
                if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                    env_var = value[2:-1]
                    env_value = os.environ.get(env_var)
                    if env_value is not None:
                        env_config[key] = env_value
                    else:
                        # Use default if environment variable is not set
                        if "defaults" in config and key in config["defaults"]:
                            env_config[key] = config["defaults"][key]
            
            # Update machine IPs based on environment configuration
            if "machines" in config:
                for machine, machine_config in config["machines"].items():
                    if "ip" in machine_config and isinstance(machine_config["ip"], str):
                        if machine_config["ip"].startswith("${") and machine_config["ip"].endswith("}"):
                            env_var = machine_config["ip"][2:-1]
                            env_value = os.environ.get(env_var)
                            if env_value is not None:
                                machine_config["ip"] = env_value
                            elif machine.lower() == "mainpc" and "mainpc_ip" in env_config:
                                machine_config["ip"] = env_config["mainpc_ip"]
                            elif machine.lower() == "pc2" and "pc2_ip" in env_config:
                                machine_config["ip"] = env_config["pc2_ip"]
        
        logger.debug(f"Network configuration loaded successfully from {config_path}")
        _network_config = config
        return config
    except Exception as e:
        logger.error(f"Error loading network configuration from {config_path}: {e}")
        # Return a minimal default configuration
        return {
            "environment": {
                "development": {
                    "use_local_mode": True,
                    "mainpc_ip": "127.0.0.1",
                    "pc2_ip": "127.0.0.1"
                }
            },
            "machines": {
                "mainpc": {"ip": "127.0.0.1"},
                "pc2": {"ip": "127.0.0.1"}
            }
        }

def get_current_machine() -> str:
    """
    Determine which machine this code is running on based on IP address.
    
    Returns:
        String 'MAINPC', 'PC2', or 'UNKNOWN'
    """
    # Force local mode if environment variable is set
    if os.environ.get("FORCE_LOCAL_MODE", "").lower() in ("true", "1", "yes"):
        logger.info("Forced local mode, assuming MAINPC")
        return "MAINPC"
    
    try:
        # Get all IP addresses of this machine
        local_ips = []
        for interface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    local_ips.append(addr['addr'])
        
        # Remove loopback
        if '127.0.0.1' in local_ips:
            local_ips.remove('127.0.0.1')
            
        # Load network configuration
        config = load_network_config()
        
        # Check if any local IP matches a machine in the configuration
        if "machines" in config:
            for machine, machine_config in config["machines"].items():
                if "ip" in machine_config and machine_config["ip"] in local_ips:
                    logger.info(f"Identified as {machine.upper()} based on IP {machine_config['ip']}")
                    return machine.upper()
        
        # If we get here, no match was found
        if local_ips:
            logger.warning(f"Local IP {local_ips[0]} doesn't match any configured machine IP")
            
            # In development mode, assume MAINPC for convenience
            env_type = os.environ.get("ENV_TYPE", "development")
            if env_type == "development":
                logger.info("Development mode: assuming MAINPC despite IP mismatch")
                return "MAINPC"
        else:
            logger.warning("No non-loopback IP addresses found")
        
        return "UNKNOWN"
    except Exception as e:
        logger.error(f"Error determining current machine: {e}")
        return "UNKNOWN"

def get_machine_ip(machine: Optional[str] = None) -> str:
    """
    Get the IP address for the specified machine.
    
    Args:
        machine: Machine name ('MAINPC', 'PC2'), or None for current machine
    
    Returns:
        IP address as string, or '127.0.0.1' if not found
    """
    if machine is None:
        machine = get_current_machine()
    
    machine = machine.lower()
    
    # Check environment variables first
    if machine == "mainpc":
        env_ip = os.environ.get("MAINPC_IP")
        if env_ip:
            return env_ip
    elif machine == "pc2":
        env_ip = os.environ.get("PC2_IP")
        if env_ip:
            return env_ip
    
    # Then check configuration
    config = load_network_config()
    if "machines" in config and machine in config["machines"]:
        machine_config = config["machines"][machine]
        if "ip" in machine_config:
            return machine_config["ip"]
    
    # Default to loopback for development
    env_type = os.environ.get("ENV_TYPE", "development")
    if env_type == "development":
        logger.debug(f"Using loopback IP for {machine} in development mode")
        return "127.0.0.1"
    
    logger.warning(f"Could not find IP for machine {machine}, using loopback")
    return "127.0.0.1"

def is_local_mode() -> bool:
    """
    Check if the system is running in local mode.
    
    Returns:
        True if running in local mode, False otherwise
    """
    # Check environment variable first
    force_local = os.environ.get("FORCE_LOCAL_MODE", "").lower()
    if force_local in ("true", "1", "yes"):
        return True
    
    # Then check configuration
    config = load_network_config()
    env_type = os.environ.get("ENV_TYPE", "development")
    
    if "environment" in config and env_type in config["environment"]:
        env_config = config["environment"][env_type]
        if "use_local_mode" in env_config:
            return env_config["use_local_mode"]
    
    # Default to True for development
    if env_type == "development":
        return True
    
    return False

def get_zmq_connection_string(port: int, machine: str = "localhost", bind_address: str = "0.0.0.0") -> str:
    """
    Get a ZeroMQ connection string with proper IP address from the network configuration.
    
    Args:
        port: Port number for the connection
        machine: Target machine ('mainpc', 'pc2', 'localhost', or specific IP)
        bind_address: Address to bind to if creating a server socket (default '0.0.0.0')
    
    Returns:
        Connection string in format 'tcp://IP:PORT' 
    """
    # For binding sockets (servers), use the bind_address
    if machine.lower() == "bind":
        return f"tcp://{bind_address}:{port}"
    
    # For localhost, use IP from network configuration
    if machine.lower() == "localhost" or machine.lower() == "127.0.0.1":
        # In local mode, use actual localhost
        if is_local_mode():
            return f"tcp://127.0.0.1:{port}"
        
        # Otherwise, use the MainPC IP from configuration 
        # (since we're typically connecting from PC2 to MainPC in this case)
        ip = get_machine_ip("mainpc")
        return f"tcp://{ip}:{port}"
    
    # For specific machines, use their configured IP
    elif machine.lower() in ("mainpc", "pc2"):
        ip = get_machine_ip(machine)
        return f"tcp://{ip}:{port}"
    
    # If a specific IP is provided, use it directly
    else:
        return f"tcp://{machine}:{port}"

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
        print(f"MainPC SDT address: {get_machine_ip()}")
        print(f"PC2 UMR address: {get_machine_ip('pc2')}")
        print(f"Current machine: {get_current_machine()}")
