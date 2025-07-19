from common.core.base_agent import BaseAgent
#!/usr/bin/env python3
"""
Configuration loader utility for PC2 agents.
Provides standardized access to configuration parameters.
"""

import os
import yaml
import json
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
import argparse
from common.env_helpers import get_env

logger = logging.getLogger(__name__)

class Config:
    def __init__(self, config_path=None):

        super().__init__(*args, **kwargs)        """Initialize the configuration loader"""
        # If specific config path is provided, use it
        if config_path:
            self.config_path = config_path
        else:
            # Use default location
            self.config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                'config',
                'config.json'
            )
        
        # Load and process config
        self._config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            # Ensure config_path is valid
            if not self.config_path or not os.path.exists(self.config_path):
                logger.warning(f"Configuration file not found at {self.config_path}, using defaults")
                return {}
                
            # Determine file type from extension
            if self.config_path.endswith('.json'):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
            elif self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f)
            else:
                logger.warning(f"Unsupported config file type: {self.config_path}")
                return {}
                
            # Process environment variables in the config
            return self._process_env_vars(config)
            
        except FileNotFoundError:
            logger.warning(f"Configuration file not found at {self.config_path}, using defaults")
            return {}
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return {}
    
    def _process_env_vars(self, config: Dict) -> Dict:
        """Process environment variables in the configuration"""
        def process_value(value: Any) -> Any:
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_var = value[2:-1]
                return os.environ.get(env_var, value)
            elif isinstance(value, dict):
                return {k: process_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [process_value(v) for v in value]
            else:
                return value
        
        if not isinstance(config, dict):
            return {}
                
        return process_value(config)
    
    def get_config(self) -> Dict[str, Any]:
        """Return the entire configuration"""
        return self._config
    
    def get(self, key: str, default=None) -> Any:
        """Get a configuration value by key"""
        return self._config.get(key, default)
    
    def get_nested(self, path: str, default=None) -> Any:
        """Get a nested configuration value using dot notation
        
        Example:
            config.get_nested('database.host', 'localhost')
        """
        keys = path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
                
        return value

def parse_agent_args(default_host='localhost'):
    """
    Parse command line arguments for agent configuration.
    
    Args:
        default_host (str): Default host to use if not specified
        
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Agent Configuration')
    parser.add_argument('--host', type=str, default=default_host,
                      help='Host to bind to')
    parser.add_argument('--port', type=int, default=None,
                      help='Port to bind to')
    parser.add_argument('--health-port', type=int, default=None,
                      help='Health check port')
    parser.add_argument('--name', type=str, default=None,
                      help='Agent name')
    parser.add_argument('--debug', action='store_true',
                      help='Enable debug logging')
    
    # Parse args with empty list as default to avoid parsing script args
    return parser.parse_args([])

def load_config(config_path=None):
    """
    Load configuration from YAML file.
    
    Args:
        config_path (str, optional): Path to config file. If None, uses default location.
        
    Returns:
        dict: Configuration dictionary
    """
    if config_path is None:
        # Default to the startup config in the project root
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", 
            "startup_config.yaml"
        )
    
    try:
        if not os.path.exists(config_path):
            logger.warning(f"Configuration file not found at {config_path}, using defaults")
            return default_config()
            
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            return config
    except Exception as e:
        logger.error(f"Error loading config from {config_path}: {e}")
        return default_config()

def default_config():
    """Return default configuration when config file cannot be loaded"""
    return {
        "pc2_network": {
            "host": "0.0.0.0",
            "agent_ports": {
                "start": 7100,
                "end": 7199
            },
            "health_check_ports": {
                "start": 8100,
                "end": 8199
            }
        }
    }

def load_network_config():
    """
    Load network configuration from YAML file.
    
    Returns:
        dict: Network configuration dictionary
    """
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "config", 
        "network_config.yaml"
    )
    
    try:
        if not os.path.exists(config_path):
            logger.warning(f"Network configuration file not found at {config_path}, using defaults")
            return {
                "main_pc_ip": "192.168.100.16",
                "pc2_ip": "192.168.100.17",
                "bind_address": "0.0.0.0",
                "secure_zmq": False
            }
            
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network config from {config_path}: {e}")
        # Return default fallback values
        return {
            "main_pc_ip": "192.168.100.16",
            "pc2_ip": "192.168.100.17",
            "bind_address": "0.0.0.0",
            "secure_zmq": False
        } 