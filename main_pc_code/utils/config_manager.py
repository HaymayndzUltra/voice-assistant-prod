#!/usr/bin/env python3
"""
Centralized Configuration Manager

This module provides a standardized way to manage configuration across the system:
- Uses a single format (YAML) for all configuration files
- Provides validation for configuration values
- Handles environment-specific configurations
- Supports dynamic reconfiguration without restart
- Uses the PathManager for resolving configuration file paths
"""

import os
import yaml
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

# Import the PathManager for consistent path resolution
from utils.path_manager import PathManager
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__, level="INFO")
logger = logging.getLogger(__name__)

class ConfigManager:
    """Centralized configuration manager for the AI System."""
    
    # Singleton instance
    _instance = None
    
    # Lock for thread safety
    _lock = threading.RLock()
    
    # Cache for loaded configurations
    _cache: Dict[str, Dict[str, Any]] = {}
    
    # Change callbacks
    _callbacks: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
    
    # Watcher thread
    _watcher_thread = None
    _watcher_stop_event = threading.Event()
    
    def __new__(cls):
        """Ensure singleton pattern."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConfigManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """Initialize the configuration manager."""
        with self._lock:
            if self._initialized:
                return
                
            self._initialized = True
            
            # Start the watcher thread if not already running
            if self._watcher_thread is None or not self._watcher_thread.is_alive():
                self._watcher_stop_event.clear()
                self._watcher_thread = threading.Thread(target=self._watch_configs)
                self._watcher_thread.daemon = True
                self._watcher_thread.start()
    
    @classmethod
    def get_config_dir(cls) -> Path:
        """Get the configuration directory.
        
        Returns:
            Path to the configuration directory
        """
        return PathManager.get_config_dir()
    
    @classmethod
    def load_config(cls, config_name: str, reload: bool = False) -> Dict[str, Any]:
        """Load a configuration file.
        
        Args:
            config_name: Name of the configuration file (without extension)
            reload: Force reload from disk
            
        Returns:
            Dictionary containing configuration
        """
        with cls._lock:
            if not reload and config_name in cls._cache:
                return cls._cache[config_name]
            
            # Find configuration file
            config_path = cls._find_config_path(config_name)
            
            if config_path is None:
                logger.warning(f"Configuration file {config_name} not found")
                return {}
            
            # Load configuration
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Apply environment overrides
                config = cls._apply_env_overrides(config)
                
                # Cache the configuration
                cls._cache[config_name] = config
                
                logger.info(f"Loaded configuration from {config_path}")
                return config
            except Exception as e:
                logger.error(f"Error loading configuration from {config_path}: {e}")
                return {}
    
    @classmethod
    def get_config(cls, config_name: str, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            config_name: Name of the configuration file (without extension)
            key: Key to retrieve (can be nested using dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        config = cls.load_config(config_name)
        
        # Handle nested keys
        if '.' in key:
            parts = key.split('.')
            value = config
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            return value
        
        # Simple key lookup
        return config.get(key, default)
    
    @classmethod
    def save_config(cls, config_name: str, config: Dict[str, Any]) -> bool:
        """Save a configuration to file.
        
        Args:
            config_name: Name of the configuration file (without extension)
            config: Configuration dictionary to save
            
        Returns:
            True if successful, False otherwise
        """
        with cls._lock:
            # Find configuration file
            config_path = cls._find_config_path(config_name)
            
            if config_path is None:
                # Create a new file in the default location
                config_path = cls.get_config_dir() / f"{config_name}.yaml"
            
            # Save configuration
            try:
                # Create directory if it doesn't exist
                config_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(config_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
                
                # Update cache
                cls._cache[config_name] = config
                
                # Notify callbacks
                cls._notify_callbacks(config_name, config)
                
                logger.info(f"Saved configuration to {config_path}")
                return True
            except Exception as e:
                logger.error(f"Error saving configuration to {config_path}: {e}")
                return False
    
    @classmethod
    def update_config(cls, config_name: str, updates: Dict[str, Any]) -> bool:
        """Update a configuration with new values.
        
        Args:
            config_name: Name of the configuration file (without extension)
            updates: Dictionary of updates to apply
            
        Returns:
            True if successful, False otherwise
        """
        with cls._lock:
            # Load current configuration
            config = cls.load_config(config_name)
            
            # Apply updates
            cls._deep_update(config, updates)
            
            # Save updated configuration
            return cls.save_config(config_name, config)
    
    @classmethod
    def register_callback(cls, config_name: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback for configuration changes.
        
        Args:
            config_name: Name of the configuration file (without extension)
            callback: Function to call when configuration changes
        """
        with cls._lock:
            if config_name not in cls._callbacks:
                cls._callbacks[config_name] = []
                
            cls._callbacks[config_name].append(callback)
    
    @classmethod
    def unregister_callback(cls, config_name: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """Unregister a callback for configuration changes.
        
        Args:
            config_name: Name of the configuration file (without extension)
            callback: Function to unregister
            
        Returns:
            True if callback was found and removed, False otherwise
        """
        with cls._lock:
            if config_name in cls._callbacks and callback in cls._callbacks[config_name]:
                cls._callbacks[config_name].remove(callback)
                return True
            return False
    
    @classmethod
    def _find_config_path(cls, config_name: str) -> Optional[Path]:
        """Find the path to a configuration file.
        
        Args:
            config_name: Name of the configuration file (without extension)
            
        Returns:
            Path to the configuration file, or None if not found
        """
        # Check for environment variable
        env_var = f"{config_name.upper()}_CONFIG"
        env_path = os.environ.get(env_var)
        
        if env_path and os.path.isfile(env_path):
            return Path(env_path)
        
        # Check common locations
        extensions = ['.yaml', '.yml', '.json']
        locations = [
            cls.get_config_dir(),
            PathManager.get_project_root() / "config",
            PathManager.get_project_root() / "main_pc_code" / "config",
            PathManager.get_project_root() / "pc2_code" / "config"
        ]
        
        for location in locations:
            for ext in extensions:
                path = location / f"{config_name}{ext}"
                if path.exists():
                    return path
                    
        return None
    
    @classmethod
    def _apply_env_overrides(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration.
        
        Args:
            config: Original configuration
            
        Returns:
            Configuration with environment overrides applied
        """
        result = config.copy()
        
        # Look for environment overrides
        env = os.environ.get("ENV") or os.environ.get("ENVIRONMENT") or "development"
        
        # Check if environment-specific overrides exist
        if env in config and isinstance(config[env], dict):
            # Apply overrides
            cls._deep_update(result, config[env])
            
            # Remove environment sections
            for env_name in ["development", "testing", "production"]:
                if env_name in result:
                    del result[env_name]
                    
        return result
    
    @classmethod
    def _deep_update(cls, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Deep update a dictionary with another dictionary.
        
        Args:
            target: Target dictionary to update
            source: Source dictionary with updates
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                cls._deep_update(target[key], value)
            else:
                target[key] = value
    
    @classmethod
    def _notify_callbacks(cls, config_name: str, config: Dict[str, Any]) -> None:
        """Notify callbacks about configuration changes.
        
        Args:
            config_name: Name of the configuration that changed
            config: New configuration
        """
        if config_name in cls._callbacks:
            for callback in cls._callbacks[config_name]:
                try:
                    callback(config)
                except Exception as e:
                    logger.error(f"Error in configuration callback: {e}")
    
    @classmethod
    def _watch_configs(cls) -> None:
        """Watch for changes in configuration files."""
        last_modified = {}
        
        while not cls._watcher_stop_event.is_set():
            try:
                # Check all cached configurations
                for config_name in list(cls._cache.keys()):
                    config_path = cls._find_config_path(config_name)
                    
                    if config_path is None:
                        continue
                        
                    # Check if file has been modified
                    mtime = config_path.stat().st_mtime
                    
                    if config_name in last_modified and last_modified[config_name] < mtime:
                        logger.info(f"Configuration {config_name} has changed, reloading")
                        cls.load_config(config_name, reload=True)
                        
                    last_modified[config_name] = mtime
            except Exception as e:
                logger.error(f"Error watching configurations: {e}")
                
            # Wait before next check
            cls._watcher_stop_event.wait(10)
    
    @classmethod
    def shutdown(cls) -> None:
        """Shutdown the configuration manager."""
        with cls._lock:
            # Stop the watcher thread
            if cls._watcher_thread is not None and cls._watcher_thread.is_alive():
                cls._watcher_stop_event.set()
                cls._watcher_thread.join(timeout=1)
                
            # Clear cache and callbacks
            cls._cache.clear()
            cls._callbacks.clear()
            
            # Reset instance
            cls._instance = None

def get_config(config_name: str, key: str, default: Any = None) -> Any:
    """Convenience function to get a configuration value.
    
    Args:
        config_name: Name of the configuration file (without extension)
        key: Key to retrieve (can be nested using dot notation)
        default: Default value if key not found
        
    Returns:
        Configuration value or default
    """
    return ConfigManager.get_config(config_name, key, default)

def load_config(config_name: str, reload: bool = False) -> Dict[str, Any]:
    """Convenience function to load a configuration file.
    
    Args:
        config_name: Name of the configuration file (without extension)
        reload: Force reload from disk
        
    Returns:
        Dictionary containing configuration
    """
    return ConfigManager.load_config(config_name, reload)

def update_config(config_name: str, updates: Dict[str, Any]) -> bool:
    """Convenience function to update a configuration with new values.
    
    Args:
        config_name: Name of the configuration file (without extension)
        updates: Dictionary of updates to apply
        
    Returns:
        True if successful, False otherwise
    """
    return ConfigManager.update_config(config_name, updates)

def register_callback(config_name: str, callback: Callable[[Dict[str, Any]], None]) -> None:
    """Convenience function to register a callback for configuration changes.
    
    Args:
        config_name: Name of the configuration file (without extension)
        callback: Function to call when configuration changes
    """
    ConfigManager.register_callback(config_name, callback)

def unregister_callback(config_name: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
    """Convenience function to unregister a callback for configuration changes.
    
    Args:
        config_name: Name of the configuration file (without extension)
        callback: Function to unregister
        
    Returns:
        True if callback was found and removed, False otherwise
    """
    return ConfigManager.unregister_callback(config_name, callback) 