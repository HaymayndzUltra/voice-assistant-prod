#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Configuration loader utility for PC2 agents.
Provides standardized access to configuration parameters.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from common.env_helpers import get_env

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
            "main_pc_ip": get_service_ip("mainpc"),
            "pc2_ip": get_service_ip("pc2"),
            "bind_address": "0.0.0.0",
            "secure_zmq": False
        } 