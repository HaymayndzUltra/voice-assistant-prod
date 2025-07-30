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
import argparse
import sys
from typing import List, Dict, Any, Optional
from pathlib import Path


# Define get_project_root function
def get_project_root():
    """Get the project root directory"""
    current_file = Path(__file__).resolve()
    # Go up two levels: from utils/ to main_pc_code/ to project root
    return current_file.parent.parent.parent

# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, str(get_project_root()))
from common.utils.path_manager import PathManager
from common.env_helpers import get_env
class Config:
    """Simple configuration loader class."""
    
    def __init__(self):
        """Initialize the Config object."""
        self.config = {}
        self.config_file = None
        self.logger = logging.getLogger('Config')
        
        # Try to load configuration from various locations
        config_paths = [
            Path(PathManager.join_path("config", "config.json")),
            Path("config.json"),
            Path("../config/config.json"),
            Path("../../config/config.json"),
            Path(PathManager.join_path("config", "startup_config.yaml")),
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

# Function used by agents
def load_config() -> Dict[str, Any]:
    """Load configuration from file.
    
    This function is used by agents to load their configuration.
    It returns the configuration as a dictionary.
    
    Returns:
        Configuration dictionary
    """
    config = get_instance()
    return config.get_config()

# Constants and functions from config_parser.py
_STANDARD_ARGS = ["host", "port"]


def _discover_dynamic_flags(argv: List[str]) -> List[str]:
    """Return flag names (without leading dashes) discovered in argv that are
    not the standard ones.
    Example: ['--modelmanager_host', '1234'] -> 'modelmanager_host'.
    """
    flags = []
    for item in argv:
        if item.startswith("--"):
            flag = item.lstrip("-")
            if flag not in _STANDARD_ARGS:
                flags.append(flag)
    return list(dict.fromkeys(flags))  # deduplicate preserving order


def parse_agent_args(argv: List[str] | None = None):
    """Parse command-line arguments passed to an agent.

    Always returns an ``argparse.Namespace`` providing at least:
        • host: str
        • port: int | None

    Additionally, any dynamic flags like ``--taskrouter_host`` or ``--modelmanager_port``
    are accepted automatically.  Flags ending in ``_port`` are parsed as ``int``,
    all others as ``str``.

    The function is intentionally lightweight and *never exits* the process –
    it raises ``ValueError`` on invalid input instead of calling ``sys.exit``.
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(add_help=False)
    # Standard flags
    parser.add_argument("--host", default=get_env("BIND_ADDRESS", "0.0.0.0"), type=str)
    parser.add_argument("--check_interval_seconds", type=int, default=15, help="How often to check VRAM and idle status.")
    parser.add_argument("--port", default=None, type=int)

    # GGUF VRAM Management Arguments
    parser.add_argument("--gguf_vram_management_enabled", action="store_true", help="Enable VRAM management for GGUF models.")
    parser.add_argument("--gguf_vram_budget_gb", type=float, default=12.0, help="VRAM budget in GB for GGUF models.")
    parser.add_argument("--gguf_idle_unload_timeout_seconds", type=int, default=300, help="Seconds of inactivity before unloading a GGUF model.")
    parser.add_argument("--gguf_check_interval_seconds", type=int, default=30, help="How often to check VRAM and idle status for GGUF models.")

    # Dynamically add flags discovered in argv so argparse won't error out
    for flag in _discover_dynamic_flags(argv):
        arg_name = f"--{flag}"
        arg_type = int if flag.endswith("_port") else str
        parser.add_argument(arg_name, dest=flag, type=arg_type)

    # Parse known args to avoid errors with unrelated argv entries (e.g., pytest arguments)
    try:
        parsed, _ = parser.parse_known_args(argv)
    except SystemExit as e:  # pragma: no cover – convert to ValueError to avoid sys.exit
        # Convert parsing failures to ValueError to maintain non-exiting behavior
        raise ValueError(f"Argument parsing failed: {e}")

    return parsed 