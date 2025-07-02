#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration Loader
This module provides a simple configuration loader class
"""

import os
import json
import yaml
import logging
from pathlib import Path

class Config:
    """Simple configuration loader class."""
    
    def __init__(self):
        """Initialize the Config object."""
        self.config = {}
        self.config_file = None
        self.logger = logging.getLogger('Config')
        
        # Try to load configuration from various locations
        config_paths = [
            Path("config/config.json"),
            Path("config.json"),
            Path("../config/config.json"),
            Path("../../config/config.json"),
            Path("config/startup_config.yaml"),
            Path("../config/startup_config.yaml"),
            Path("../../config/startup_config.yaml"),
        ]
        
        for path in config_paths:
            if path.exists():
                self.config_file = path
                self.load_config(path)
                self.logger.info(f"Loaded configuration from {path}")
                break
        
        if not self.config:
            self.logger.warning("No configuration file found. Using empty config.")
    
    def load_config(self, config_file):
        """Load configuration from a file.
        
        Args:
            config_file: Path to the configuration file
        """
        try:
            if config_file.suffix == '.json':
                with open(config_file, 'r') as f:
                    self.config = json.load(f)
            elif config_file.suffix == '.yaml':
                with open(config_file, 'r') as f:
                    self.config = yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            self.config = {}
    
    def get(self, key, default=None):
        """Get a configuration value.
        
        Args:
            key: Configuration key (can use dot notation for nested keys)
            default: Default value to return if key is not found
            
        Returns:
            Configuration value or default
        """
        if '.' in key:
            # Handle nested keys
            parts = key.split('.')
            value = self.config
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            return value
        else:
            # Simple key
            return self.config.get(key, default)
    
    def set(self, key, value):
        """Set a configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self.config[key] = value
    
    def get_config(self):
        """Get the entire configuration.
        
        Returns:
            Configuration dictionary
        """
        return self.config

# Singleton instance
_instance = None

def get_instance():
    """Get the singleton instance of Config.
    
    Returns:
        Config instance
    """
    global _instance
    if _instance is None:
        _instance = Config()
    return _instance 