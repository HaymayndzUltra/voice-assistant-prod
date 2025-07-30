#!/usr/bin/env python3
"""
Environment Variable Loader

This module provides functions to load environment variables for the AI System,
with appropriate defaults and type conversion.
"""

import os
import logging
from typing import Any, Dict, List
from common.env_helpers import get_env

# Set up logging
logger = logging.getLogger(__name__)

# Type conversion functions
def _to_bool(value: str) -> bool:
    """Convert string to boolean."""
    return value.lower() in ('true', '1', 'yes', 'y', 'on')

def _to_int(value: str) -> int:
    """Convert string to integer."""
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Could not convert '{value}' to int, using default")
        return 0

def _to_float(value: str) -> float:
    """Convert string to float."""
    try:
        return float(value)
    except ValueError:
        logger.warning(f"Could not convert '{value}' to float, using default")
        return 0.0

def _to_list(value: str, delimiter: str = ',') -> List[str]:
    """Convert comma-separated string to list."""
    return [item.strip() for item in value.split(delimiter) if item.strip()]

# Environment variable definitions with defaults and types
ENV_VARS = {
    # Machine type
    'MACHINE_TYPE': {'default': 'MAINPC', 'type': str},
    
    # Network configuration
    'MAIN_PC_IP': {'default': 'localhost', 'type': str},
    'PC2_IP': {'default': 'localhost', 'type': str},
    'BIND_ADDRESS': {'default': '0.0.0.0', 'type': str},
    
    # Security settings
    'SECURE_ZMQ': {'default': '1', 'type': _to_bool},
    'ZMQ_CERTIFICATES_DIR': {'default': 'certificates', 'type': str},
    
    # Service discovery
    'SYSTEM_DIGITAL_TWIN_PORT': {'default': '7120', 'type': _to_int},
    'SERVICE_DISCOVERY_ENABLED': {'default': '1', 'type': _to_bool},
    'FORCE_LOCAL_SDT': {'default': '1', 'type': _to_bool},
    
    # Voice pipeline ports
    'TASK_ROUTER_PORT': {'default': '8571', 'type': _to_int},
    'RESPONDER_PORT': {'default': '5637', 'type': _to_int},
    'STREAMING_TTS_PORT': {'default': '5562', 'type': _to_int},
    'TTS_PORT': {'default': '5562', 'type': _to_int},
    'INTERRUPT_PORT': {'default': '5576', 'type': _to_int},
    
    # Resource constraints
    'MAX_MEMORY_MB': {'default': '2048', 'type': _to_int},
    'MAX_VRAM_MB': {'default': '2048', 'type': _to_int},
    
    # Logging
    'LOG_LEVEL': {'default': 'INFO', 'type': str},
    'LOG_DIR': {'default': 'logs', 'type': str},
    
    # Timeouts and retries
    'ZMQ_REQUEST_TIMEOUT': {'default': '5000', 'type': _to_int},
    'CONNECTION_RETRIES': {'default': '3', 'type': _to_int},
    'SERVICE_DISCOVERY_TIMEOUT': {'default': '10000', 'type': _to_int},
    
    # Voice pipeline settings
    'VOICE_SAMPLE_DIR': {'default': 'voice_samples', 'type': str},
    'MODEL_DIR': {'default': 'models', 'type': str},
    'CACHE_DIR': {'default': 'cache', 'type': str},
}

def get_env(name: str, default: Any = None) -> Any:
    """
    Get an environment variable with appropriate type conversion.
    
    Args:
        name: Name of the environment variable
        default: Default value if not found (overrides the default in ENV_VARS)
        
    Returns:
        The environment variable value with appropriate type conversion
    """
    if name not in ENV_VARS:
        logger.warning(f"Unknown environment variable: {name}")
        return default
    
    env_def = ENV_VARS[name]
    env_default = default if default is not None else env_def['default']
    env_type = env_def['type']
    
    value = os.environ.get(name, env_default)
    
    # Apply type conversion
    if env_type == str:
        return value
    else:
        try:
            return env_type(value)
        except Exception as e:
            logger.error(f"Error converting {name}={value} to {env_type.__name__}: {e}")
            return env_default

def load_all_env() -> Dict[str, Any]:
    """
    Load all defined environment variables with appropriate type conversion.
    
    Returns:
        Dictionary of all environment variables
    """
    env_dict = {}
    for name in ENV_VARS:
        env_dict[name] = get_env(name)
    return env_dict

def is_mainpc() -> bool:
    """
    Check if current machine is MainPC.
    
    Returns:
        True if MACHINE_TYPE is MAINPC, False otherwise
    """
    return get_env('MACHINE_TYPE') == 'MAINPC'

def is_pc2() -> bool:
    """
    Check if current machine is PC2.
    
    Returns:
        True if MACHINE_TYPE is PC2, False otherwise
    """
    return get_env('MACHINE_TYPE') == 'PC2'

# Load all environment variables when module is imported
ENV = load_all_env()

if __name__ == '__main__':
    # Configure logging for the test
    logging.basicConfig(level=logging.INFO, 
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Print all environment variables
    print("Environment Variables:")
    for name, value in ENV.items():
        print(f"{name} = {value} ({type(value).__name__})") 