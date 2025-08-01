#!/usr/bin/env python3
"""
Configuration loader utility for PC2 agents.
Provides standardized access to configuration parameters.
"""

import os
import yaml
import logging

# Standardized environment variables (Blueprint.md Step 4)
from common.utils.env_standardizer import get_mainpc_ip, get_pc2_ip

logger = logging.getLogger(__name__)

def parse_agent_args(default_host='localhost'):
    """
    Parse command line arguments for agent configuration.
    
    Args:
        default_host (str): Default host to use if not specified
        
    Returns:
        object: An object with host attribute
    """
    # Simple implementation for compatibility
    class Args:
        def __init__(self, host):
            self.host = host
            
    return Args(default_host)

def load_config(config_path=None):
    """
    Load configuration from YAML file.
    
    Args:
        config_path (str, optional): Path to config file. If None, uses default location.
        
    Returns:
        dict: Configuration dictionary
    """
    if config_path is None:
        # Default to the network config in the project root
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                  "config", "network_config.yaml")
    
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config from {config_path}: {e}")
        # Return default fallback values
        return {
            "main_pc_ip": get_mainpc_ip(),
            "pc2_ip": get_pc2_ip(),
            "bind_address": "0.0.0.0",
            "secure_zmq": False
        } 