"""
Centralized Configuration Management System for Voice Assistant

This module provides a unified interface for managing all configuration settings
across the voice assistant system. It handles loading, validation, updating,
and persisting configuration data.
"""

import os
import sys
import yaml
import json
import logging
import threading
from typing import Dict, Any, Optional, List, Union, Callable
from datetime import datetime
from pathlib import Path


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, get_project_root())
from common.utils.path_env import get_path, join_path, get_file_path
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ConfigManager")

class ConfigManager:
    """Centralized configuration manager for the voice assistant system"""
    
    # Singleton instance
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConfigManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, config_dir: Optional[str] = None):
        with self._lock:
            if self._initialized:
                return
                
            # Base configuration directory
            self._config_dir = config_dir or os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "config"
            )
            
            # Ensure config directory exists
            os.makedirs(self._config_dir, exist_ok=True)
            
            # Main config file paths
            self._main_config_path = os.path.join(self._config_dir, "system_config.yaml")
            self._user_config_path = os.path.join(self._config_dir, "user_config.yaml")
            self._secrets_path = os.path.join(self._config_dir, "secrets.yaml")
            
            # Cache for loaded configurations
            self._config_cache = {}
            self._validators = {}
            self._defaults = {}
            
            # Initialize with system defaults
            self._init_system_defaults()
            
            # Load all configurations
            self._load_all_configs()
            
            # Flag to avoid reinitialization
            self._initialized = True
    
    def _init_system_defaults(self):
        """Initialize system default configurations"""
        self._defaults["system"] = {
            "version": "1.0.0",
            "name": "Voice Assistant",
            "logs_dir": get_path("logs"),
            "enable_telemetry": True,
            "telemetry": {
                "interval_sec": 30,
                "retention_hours": 24,
                "dashboard_port": 8088,
                "alert_thresholds": {
                    "vram_usage_percent": 85,
                    "queue_depth": 10,
                    "response_time_sec": 3.0,
                    "error_rate_percent": 10
                }
            },
            "agents": {
                "max_concurrent": 3,
                "timeout_sec": 60,
                "retry_attempts": 3,
                "retry_delay_sec": 1.0
            },
            "models": {
                "default_fallback": "tinyllama",
                "emergency_vram_threshold": 0.05,
                "model_timeout_sec": 300,
                "check_compatibility": True
            },
            "audio": {
                "input_device": None,
                "output_device": None,
                "sample_rate": 16000,
                "channels": 1,
                "chunk_size": 1024,
                "use_streaming": False,
                "streaming_threshold": 0.5
            },
            "ui": {
                "theme": "dark",
                "enable_animations": True,
                "enable_voice_viz": True,
                "font_size": "medium",
                "display_confidence": True
            },
            "paths": {
                "models_dir": get_path("models"),
                "cache_dir": get_path("cache"),
                "temp_dir": os.path.join(os.path.dirname(self._config_dir), "temp"),
                "recordings_dir": os.path.join(os.path.dirname(self._config_dir), "recordings")
            }
        }
        
        # User defaults
        self._defaults["user"] = {
            "name": "User",
            "voice_id": "default",
            "language": "en-US",
            "tts_speed": 1.0,
            "auto_start": False,
            "startup_greeting": True,
            "shutdown_farewell": True,
            "wake_word": "assistant",
            "wake_word_sensitivity": 0.5,
            "hotkeys": {
                "toggle_listening": "ctrl+shift+l",
                "stop_speaking": "escape",
                "repeat_last": "ctrl+r"
            },
            "chat_history": {
                "save_history": True,
                "max_entries": 100,
                "enable_search": True
            }
        }
        
        # API keys and secrets (empty defaults)
        self._defaults["secrets"] = {
            "openai_api_key": "",
            "elevenlabs_api_key": "",
            "google_api_key": "",
            "azure_api_key": "",
            "anthropic_api_key": ""
        }
    
    def _load_all_configs(self):
        """Load all configuration files"""
        # System config
        if not os.path.exists(self._main_config_path):
            logger.info(f"System configuration file not found, creating default at {self._main_config_path}")
            self._save_config("system", self._defaults["system"])
        else:
            self._load_config("system", self._main_config_path)
        
        # User config
        if not os.path.exists(self._user_config_path):
            logger.info(f"User configuration file not found, creating default at {self._user_config_path}")
            self._save_config("user", self._defaults["user"])
        else:
            self._load_config("user", self._user_config_path)
        
        # Secrets (without overwriting with defaults if missing)
        if os.path.exists(self._secrets_path):
            self._load_config("secrets", self._secrets_path)
        else:
            logger.info(f"Secrets file not found, creating empty template at {self._secrets_path}")
            # Create but don't overwrite with defaults
            self._config_cache["secrets"] = {}
            self._save_config("secrets", {})
    
    def _load_config(self, config_type: str, config_path: str) -> Dict:
        """Load a specific configuration file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                if config is None:
                    config = {}
                
                # Merge with defaults to ensure all required fields exist
                defaults = self._defaults.get(config_type, {})
                merged_config = self._deep_merge(defaults, config)
                
                # Cache the loaded configuration
                self._config_cache[config_type] = merged_config
                
                logger.info(f"Loaded {config_type} configuration from {config_path}")
                return merged_config
                
        except Exception as e:
            logger.error(f"Error loading {config_type} configuration: {e}")
            # Fall back to defaults
            self._config_cache[config_type] = self._defaults.get(config_type, {})
            return self._config_cache[config_type]
    
    def _save_config(self, config_type: str, config: Dict) -> bool:
        """Save a specific configuration to file"""
        try:
            # Determine the file path based on config type
            if config_type == "system":
                config_path = self._main_config_path
            elif config_type == "user":
                config_path = self._user_config_path
            elif config_type == "secrets":
                config_path = self._secrets_path
            else:
                config_path = os.path.join(self._config_dir, f"{config_type}_config.yaml")
            
            # Create backup of existing config
            if os.path.exists(config_path):
                backup_path = f"{config_path}.bak"
                try:
                    with open(config_path, 'r') as src, open(backup_path, 'w') as dst:
                        dst.write(src.read())
                except Exception as e:
                    logger.warning(f"Failed to create backup: {e}")
            
            # Save the new configuration
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            # Update the cache
            self._config_cache[config_type] = config
            
            logger.info(f"Saved {config_type} configuration to {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving {config_type} configuration: {e}")
            return False
    
    def get_config(self, config_type: str) -> Dict:
        """Get a complete configuration by type"""
        if config_type not in self._config_cache:
            if config_type in self._defaults:
                self._config_cache[config_type] = self._defaults[config_type]
            else:
                logger.warning(f"Unknown configuration type: {config_type}")
                return {}
        
        return self._config_cache[config_type]
    
    def get_value(self, config_path: str, default: Any = None) -> Any:
        """
        Get a specific configuration value using dot notation path
        
        Example: config_manager.get_value("system.audio.sample_rate")
        """
        if not config_path or not isinstance(config_path, str):
            return default
            
        # Split the path into components
        components = config_path.split('.')
        if not components:
            return default
            
        # First component is the config type
        config_type = components[0]
        config = self.get_config(config_type)
        
        # Navigate through the nested structure
        current = config
        for comp in components[1:]:
            if isinstance(current, dict) and comp in current:
                current = current[comp]
            else:
                return default
        
        return current
    
    def set_value(self, config_path: str, value: Any, save: bool = True) -> bool:
        """
        Set a specific configuration value using dot notation path
        
        Example: config_manager.set_value("system.audio.sample_rate", 22050)
        """
        if not config_path or not isinstance(config_path, str):
            return False
            
        # Split the path into components
        components = config_path.split('.')
        if not components:
            return False
            
        # First component is the config type
        config_type = components[0]
        config = self.get_config(config_type)
        
        # Navigate to the parent of the target setting
        current = config
        for comp in components[1:-1]:
            if comp not in current:
                current[comp] = {}
            current = current[comp]
            
        # Set the value
        current[components[-1]] = value
        
        # Save the updated configuration if requested
        if save:
            return self._save_config(config_type, config)
        else:
            # Just update the cache
            self._config_cache[config_type] = config
            return True
    
    def register_validator(self, config_path: str, validator: Callable[[Any], bool]) -> None:
        """Register a validation function for a specific configuration path"""
        self._validators[config_path] = validator
    
    def validate_config(self, config_type: str = None) -> Dict[str, List[str]]:
        """Validate configuration, returning a dict of error messages by path"""
        errors = {}
        
        # If a specific type is provided, only validate that
        config_types = [config_type] if config_type else self._config_cache.keys()
        
        for ctype in config_types:
            config = self.get_config(ctype)
            # Find all relevant validators
            for path, validator in self._validators.items():
                if path.startswith(ctype + '.'):
                    # Extract the value at this path
                    value = self.get_value(path)
                    try:
                        if not validator(value):
                            errors[path] = f"Validation failed for {path}"
                    except Exception as e:
                        errors[path] = f"Validation error for {path}: {str(e)}"
        
        return errors
    
    def reset_to_defaults(self, config_type: str) -> bool:
        """Reset a configuration type back to system defaults"""
        if config_type not in self._defaults:
            logger.warning(f"No defaults available for {config_type}")
            return False
            
        return self._save_config(config_type, self._defaults[config_type])
    
    def create_snapshot(self, name: Optional[str] = None) -> str:
        """Create a snapshot of all configurations for backup/restore"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = name or f"config_snapshot_{timestamp}"
        
        snapshot_dir = os.path.join(self._config_dir, "snapshots")
        os.makedirs(snapshot_dir, exist_ok=True)
        
        snapshot_path = os.path.join(snapshot_dir, f"{name}.yaml")
        
        try:
            # Gather all configs
            full_config = {}
            for config_type in self._config_cache:
                # Skip secrets by default for security
                if config_type != "secrets":
                    full_config[config_type] = self._config_cache[config_type]
            
            # Save the snapshot
            with open(snapshot_path, 'w') as f:
                yaml.dump(full_config, f, default_flow_style=False)
                
            logger.info(f"Created configuration snapshot: {snapshot_path}")
            return snapshot_path
            
        except Exception as e:
            logger.error(f"Error creating configuration snapshot: {e}")
            return ""
    
    def restore_snapshot(self, snapshot_path: str) -> bool:
        """Restore configuration from a snapshot"""
        try:
            # Check if snapshot exists
            if not os.path.exists(snapshot_path):
                logger.error(f"Snapshot file not found: {snapshot_path}")
                return False
                
            # Load the snapshot
            with open(snapshot_path, 'r') as f:
                snapshot = yaml.safe_load(f)
                
            if not snapshot or not isinstance(snapshot, dict):
                logger.error("Invalid snapshot format")
                return False
                
            # Restore each configuration type
            for config_type, config in snapshot.items():
                if self._save_config(config_type, config):
                    logger.info(f"Restored {config_type} configuration from snapshot")
                else:
                    logger.error(f"Failed to restore {config_type} configuration")
                    return False
                    
            logger.info(f"Configuration successfully restored from {snapshot_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring configuration: {e}")
            return False
    
    def _deep_merge(self, defaults: Dict, config: Dict) -> Dict:
        """
        Deep merge two dictionaries, preferring values from config but
        ensuring all keys from defaults are present
        """
        result = defaults.copy()
        
        for key, value in config.items():
            # If both values are dictionaries, merge them recursively
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                # Otherwise, prefer the value from config
                result[key] = value
                
        return result
    
    def list_snapshots(self) -> List[Dict[str, str]]:
        """List all available configuration snapshots"""
        snapshot_dir = os.path.join(self._config_dir, "snapshots")
        if not os.path.exists(snapshot_dir):
            return []
            
        snapshots = []
        for filename in os.listdir(snapshot_dir):
            if filename.endswith('.yaml'):
                path = os.path.join(snapshot_dir, filename)
                timestamp = os.path.getmtime(path)
                date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                
                snapshots.append({
                    "name": filename.replace('.yaml', ''),
                    "path": path,
                    "date": date_str,
                    "size": os.path.getsize(path)
                })
                
        # Sort by date (newest first)
        return sorted(snapshots, key=lambda x: x["date"], reverse=True)
    
    def get_all_config_paths(self) -> List[str]:
        """
        Get a list of all available config paths using dot notation
        Useful for generating configuration UI forms
        """
        paths = []
        
        def _explore_dict(d, current_path):
            for key, value in d.items():
                path = f"{current_path}.{key}" if current_path else key
                if isinstance(value, dict):
                    _explore_dict(value, path)
                else:
                    paths.append(path)
        
        # Explore each config type
        for config_type, config in self._config_cache.items():
            _explore_dict(config, config_type)
            
        return sorted(paths)

# Create global instance
config_manager = ConfigManager()

# Additional helper functions
def get_config(config_type: str) -> Dict:
    """Helper function to get a complete configuration section"""
    return config_manager.get_config(config_type)

def get_value(path: str, default: Any = None) -> Any:
    """Helper function to get a specific configuration value using dot notation"""
    return config_manager.get_value(path, default)

def set_value(path: str, value: Any, save: bool = True) -> bool:
    """Helper function to set a specific configuration value using dot notation"""
    return config_manager.set_value(path, value, save)

# Initialize configuration system
def initialize():
    """Initialize the configuration system"""
    return config_manager._initialized

# Export the singleton instance
if __name__ == "__main__":
    # Simple CLI for testing
    import argparse
    
    parser = argparse.ArgumentParser(description="Configuration Manager CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Get value command
    get_parser = subparsers.add_parser("get", help="Get a configuration value")
    get_parser.add_argument("path", help="Configuration path in dot notation")
    
    # Set value command
    set_parser = subparsers.add_parser("set", help="Set a configuration value")
    set_parser.add_argument("path", help="Configuration path in dot notation")
    set_parser.add_argument("value", help="Value to set")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all configuration paths")
    
    # Snapshot commands
    snapshot_parser = subparsers.add_parser("snapshot", help="Manage configuration snapshots")
    snapshot_subparsers = snapshot_parser.add_subparsers(dest="snapshot_command", help="Snapshot command")
    
    # Create snapshot
    create_parser = snapshot_subparsers.add_parser("create", help="Create a configuration snapshot")
    create_parser.add_argument("--name", help="Snapshot name")
    
    # Restore snapshot
    restore_parser = snapshot_subparsers.add_parser("restore", help="Restore a configuration snapshot")
    restore_parser.add_argument("path", help="Path to snapshot file")
    
    # List snapshots
    list_snapshots_parser = snapshot_subparsers.add_parser("list", help="List available snapshots")
    
    # Reset to defaults
    reset_parser = subparsers.add_parser("reset", help="Reset a configuration to defaults")
    reset_parser.add_argument("type", help="Configuration type to reset")
    
    args = parser.parse_args()
    
    if args.command == "get":
        value = config_manager.get_value(args.path)
        print(f"{args.path}: {value}")
        
    elif args.command == "set":
        # Convert value to appropriate type
        value = args.value
        # Try to convert to int, float, boolean if appropriate
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        else:
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass  # Keep as string
        
        success = config_manager.set_value(args.path, value)
        if success:
            print(f"Successfully set {args.path} to {value}")
        else:
            print(f"Failed to set {args.path}")
            
    elif args.command == "list":
        paths = config_manager.get_all_config_paths()
        for path in paths:
            value = config_manager.get_value(path)
            print(f"{path}: {value}")
            
    elif args.command == "snapshot":
        if args.snapshot_command == "create":
            path = config_manager.create_snapshot(args.name)
            if path:
                print(f"Created snapshot: {path}")
            else:
                print("Failed to create snapshot")
                
        elif args.snapshot_command == "restore":
            success = config_manager.restore_snapshot(args.path)
            if success:
                print(f"Successfully restored configuration from {args.path}")
            else:
                print(f"Failed to restore configuration from {args.path}")
                
        elif args.snapshot_command == "list":
            snapshots = config_manager.list_snapshots()
            if snapshots:
                print("Available snapshots:")
                for snapshot in snapshots:
                    print(f"- {snapshot['name']} ({snapshot['date']}, {snapshot['size']} bytes)")
            else:
                print("No snapshots available")
                
    elif args.command == "reset":
        success = config_manager.reset_to_defaults(args.type)
        if success:
            print(f"Successfully reset {args.type} configuration to defaults")
        else:
            print(f"Failed to reset {args.type} configuration")
            
    else:
        parser.print_help()
