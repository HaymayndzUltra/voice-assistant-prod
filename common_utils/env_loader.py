import os
import yaml
import pathlib
from typing import Dict, Any, Optional
from common.config_manager import get_service_ip, get_service_url, get_redis_url

def load_network_config() -> Dict[str, Any]:
    """
    Load network configuration from the network_config.yaml file
    
    Returns:
        Dict[str, Any]: Network configuration dictionary
    """
    config_path = pathlib.Path(__file__).parent.parent / 'config' / 'network_config.yaml'
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"Error loading network config: {e}")
        # Return default configuration
        return {
            "main_pc": {"ip": get_service_ip("mainpc")},
            "pc2": {"ip": get_service_ip("pc2")},
            "services": {}
        }

# Load config once at module import
CFG = load_network_config()

def get_env(var_name: str, default: str = None) -> str:
    """
    Get environment variable with fallback to default
    
    Args:
        var_name: Name of the environment variable
        default: Default value if environment variable is not set
        
    Returns:
        str: Value of the environment variable or default
    """
    return os.environ.get(var_name, default)

def get_ip(machine: str) -> str:
    """
    Get IP address for a machine from environment variables or config
    
    Args:
        machine: Machine name (main_pc or pc2)
        
    Returns:
        str: IP address of the machine
    """
    # First check environment variable
    env_var = f"{machine.upper()}_IP"
    env_ip = os.environ.get(env_var)
    if env_ip:
        return env_ip
    
    # Fall back to config
    try:
        return CFG[machine]["ip"]
    except (KeyError, TypeError):
        # Return localhost as last resort
        print(f"Warning: Could not find IP for {machine}, using localhost")
        return "localhost"

def addr(service: str, target: str) -> str:
    """
    Get full address for a service on a target machine
    
    Args:
        service: Service name
        target: Target machine (main_pc or pc2)
        
    Returns:
        str: Full ZMQ address for the service
    """
    try:
        port = CFG["services"][service][f"{target}_port"]
        return f"tcp://{get_ip(target)}:{port}"
    except (KeyError, TypeError):
        # Return a default port if not found
        print(f"Warning: Could not find port for {service} on {target}")
        return f"tcp://{get_ip(target)}:5000" 