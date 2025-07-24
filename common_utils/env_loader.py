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
    Get IP address for a machine using standardized environment variables.
    
    Args:
        machine: Machine name (main_pc, mainpc, or pc2)
        
    Returns:
        str: IP address of the machine
    """
    # Import here to avoid circular imports
    from common.utils.env_standardizer import get_machine_ip
    
    # Normalize machine name
    machine = machine.lower()
    if machine in ("main_pc", "mainpc"):
        machine = "mainpc"
    elif machine == "pc2":
        machine = "pc2"
    else:
        print(f"Warning: Unknown machine {machine}, using localhost")
        return "localhost"
    
    # Use standardized environment variables (Blueprint.md Step 4)
    return get_machine_ip(machine)

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