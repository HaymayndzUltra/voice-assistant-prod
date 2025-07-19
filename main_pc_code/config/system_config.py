#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
System Configuration
This module provides system configuration values and configuration management
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from common.env_helpers import get_env

# Get the root directory
ROOT_DIR = Path(__file__).parent.parent
LOGS_DIR = ROOT_DIR / "logs"
CONFIG_DIR = ROOT_DIR / "config"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)
CONFIG_DIR.mkdir(exist_ok=True)

class Config:
    _instance = None
    _config: Dict[str, Any] = {}
    _config_file = CONFIG_DIR / "system_config.json"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._load_config()
        return cls._instance
    
    @classmethod
    def _load_config(cls) -> None:
        """Load configuration from file"""
        try:
            if cls._config_file.exists():
                with open(cls._config_file, 'r') as f:
                    cls._config = json.load(f)
            else:
                # Initialize with default configuration
                cls._config = {
                    "common_settings": {
                        "system": {
                            "version": "1.0.0",
                            "name": "Voice Assistant",
                            "enable_telemetry": True,
                            "telemetry": {
                                "interval_sec": 30,
                                "retention_hours": 24,
                                "dashboard_port": 8088
                            }
                        },
                        "audio": {
                            "input_device": None,
                            "output_device": None,
                            "sample_rate": 16000,
                            "channels": 1,
                            "chunk_size": 1024
                        }
                    },
                    "main_pc_settings": {
                        "agents": {
                            "task_router": {
                                "port": 8570,
                                "host": "localhost"
                            },
                            "chain_of_thought": {
                                "port": 5572,
                                "host": "localhost"
                            }
                        }
                    },
                    "pc2_settings": {
                        "agents": {
                            "task_router": {
                                "port": 8570,
                                "host": "localhost"
                            }
                        }
                    }
                }
                cls.save_config()
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
            cls._config = {}
    
    @classmethod
    def _deep_merge(cls, default: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries, with override taking precedence"""
        result = default.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = cls._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    @classmethod
    def get(cls, key_path: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation"""
        if not cls._config:
            cls._load_config()
            
        keys = key_path.split('.')
        value = cls._config
        
        try:
            for key in keys:
                if not isinstance(value, dict):
                    return default
                value = value.get(key, default)
            return value
        except (KeyError, TypeError):
            return default
    
    @classmethod
    def set(cls, key_path: str, value: Any) -> None:
        """Set a configuration value using dot notation"""
        if not cls._config:
            cls._load_config()
            
        keys = key_path.split('.')
        config = cls._config
        
        # Navigate to the nested dictionary
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # Set the value
        config[keys[-1]] = value
    
    @classmethod
    def save_config(cls) -> bool:
        """Save the current configuration to file"""
        try:
            with open(cls._config_file, 'w') as f:
                json.dump(cls._config, f, indent=4)
            logging.info(f"Saved configuration to {cls._config_file}")
            return True
        except Exception as e:
            logging.error(f"Error saving configuration: {e}")
            return False
    
    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """Get the entire configuration dictionary"""
        if not cls._config:
            cls._load_config()
        return cls._config.copy()

# Create a global instance for other modules to import
config = Config()

def get_config_for_machine() -> Dict[str, Any]:
    """Get machine-specific configuration based on MACHINE_ROLE environment variable"""
    machine_role = os.environ.get("MACHINE_ROLE", "MAIN_PC").upper()
    config_instance = Config()
    full_config = config_instance.get_all()

    # Start with a deep copy of common settings
    machine_config = json.loads(json.dumps(full_config.get("common_settings", {})))

    specific_settings_key = None
    if machine_role == "MAIN_PC":
        specific_settings_key = "main_pc_settings"
    elif machine_role == "PC2":
        specific_settings_key = "pc2_settings"
    else:
        logging.warning(f"Unknown MACHINE_ROLE: {machine_role}. Falling back to Main PC specific settings.")
        specific_settings_key = "main_pc_settings"
    
    specific_settings = json.loads(json.dumps(full_config.get(specific_settings_key, {})))

    # Deep merge specific settings into the machine_config
    def _deep_update(target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                _deep_update(target[key], value)
            else:
                target[key] = value
        return target

    _deep_update(machine_config, specific_settings)
    
    # Ensure all top-level keys from specific settings are present
    for key, value in specific_settings.items():
        if key not in machine_config:
            machine_config[key] = value
            
    return machine_config

def setup_logging() -> None:
    """Setup logging configuration"""
    log_file = LOGS_DIR / "system.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

# Initialize logging
setup_logging() 