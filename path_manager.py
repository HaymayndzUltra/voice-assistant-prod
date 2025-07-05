#!/usr/bin/env python3
"""
Centralized Path Manager for AI System

This module provides a consistent way to resolve paths across the codebase,
eliminating path resolution inconsistencies and making the system more robust.

Usage:
    from path_manager import PathManager
    
    # Get project root
    project_root = PathManager.get_project_root()
    
    # Get config directory
    config_dir = PathManager.get_config_dir()
    
    # Resolve a path relative to project root
    full_path = PathManager.resolve_path("main_pc_code/agents/model_manager_agent.py")
    
    # Get logs directory
    logs_dir = PathManager.get_logs_dir()
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Union, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PathManager:
    """Centralized path management for the AI System."""
    
    # Cache for resolved paths
    _cache: Dict[str, Path] = {}
    
    # Project root path
    _project_root: Optional[Path] = None
    
    @classmethod
    def get_project_root(cls) -> Path:
        """
        Get the project root directory.
        
        Returns:
            Path to the project root directory
        """
        if cls._project_root is None:
            # Try environment variable first
            env_root = os.environ.get("PROJECT_ROOT")
            if env_root and os.path.isdir(env_root):
                cls._project_root = Path(env_root).resolve()
            else:
                # Find project root by looking for key markers
                current_file = Path(__file__).resolve()
                
                # Start from the directory containing this file
                current_dir = current_file.parent
                
                # Go up the directory tree until we find the project root
                while current_dir.name and current_dir != current_dir.parent:
                    # Check for key markers that indicate project root
                    if any((current_dir / marker).exists() for marker in [
                        ".git",
                        "main_pc_code",
                        "pc2_code",
                        "config/network_config.yaml"
                    ]):
                        cls._project_root = current_dir
                        break
                    
                    # Go up one directory
                    current_dir = current_dir.parent
                
                # If we couldn't find the project root, use a reasonable default
                if cls._project_root is None:
                    # If this file is in main_pc_code/utils, go up two directories
                    if "main_pc_code/utils" in str(current_file):
                        cls._project_root = current_file.parent.parent.parent
                    else:
                        # Last resort: use current working directory
                        cls._project_root = Path.cwd()
                        logger.warning(
                            f"Could not determine project root, using current directory: {cls._project_root}"
                        )
            
            # Add project root to Python path if not already there
            project_root_str = str(cls._project_root)
            if project_root_str not in sys.path:
                sys.path.insert(0, project_root_str)
                logger.debug(f"Added {project_root_str} to Python path")
            
            logger.info(f"Project root: {cls._project_root}")
        
        return cls._project_root
    
    @classmethod
    def get_config_dir(cls) -> Path:
        """
        Get the configuration directory.
        
        Returns:
            Path to the configuration directory
        """
        key = "config_dir"
        if key not in cls._cache:
            # Check for environment variable
            env_config_dir = os.environ.get("CONFIG_DIR")
            if env_config_dir and os.path.isdir(env_config_dir):
                cls._cache[key] = Path(env_config_dir).resolve()
            else:
                # Default to config directory in project root
                cls._cache[key] = cls.get_project_root() / "config"
                
                # Create directory if it doesn't exist
                cls._cache[key].mkdir(exist_ok=True)
        
        return cls._cache[key]
    
    @classmethod
    def get_logs_dir(cls) -> Path:
        """
        Get the logs directory.
        
        Returns:
            Path to the logs directory
        """
        key = "logs_dir"
        if key not in cls._cache:
            # Check for environment variable
            env_logs_dir = os.environ.get("LOGS_DIR")
            if env_logs_dir and os.path.isdir(env_logs_dir):
                cls._cache[key] = Path(env_logs_dir).resolve()
            else:
                # Default to logs directory in project root
                cls._cache[key] = cls.get_project_root() / "logs"
                
                # Create directory if it doesn't exist
                cls._cache[key].mkdir(exist_ok=True)
        
        return cls._cache[key]
    
    @classmethod
    def get_data_dir(cls) -> Path:
        """
        Get the data directory.
        
        Returns:
            Path to the data directory
        """
        key = "data_dir"
        if key not in cls._cache:
            # Check for environment variable
            env_data_dir = os.environ.get("DATA_DIR")
            if env_data_dir and os.path.isdir(env_data_dir):
                cls._cache[key] = Path(env_data_dir).resolve()
            else:
                # Default to data directory in project root
                cls._cache[key] = cls.get_project_root() / "data"
                
                # Create directory if it doesn't exist
                cls._cache[key].mkdir(exist_ok=True)
        
        return cls._cache[key]
    
    @classmethod
    def get_models_dir(cls) -> Path:
        """
        Get the models directory.
        
        Returns:
            Path to the models directory
        """
        key = "models_dir"
        if key not in cls._cache:
            # Check for environment variable
            env_models_dir = os.environ.get("MODELS_DIR")
            if env_models_dir and os.path.isdir(env_models_dir):
                cls._cache[key] = Path(env_models_dir).resolve()
            else:
                # Default to models directory in project root
                cls._cache[key] = cls.get_project_root() / "models"
                
                # Create directory if it doesn't exist
                cls._cache[key].mkdir(exist_ok=True)
        
        return cls._cache[key]
    
    @classmethod
    def resolve_path(cls, path: Union[str, Path]) -> Path:
        """
        Resolve a path relative to the project root.
        
        Args:
            path: Path to resolve (absolute or relative to project root)
            
        Returns:
            Resolved absolute path
        """
        path_str = str(path)
        
        # Return cached path if available
        if path_str in cls._cache:
            return cls._cache[path_str]
        
        # Convert to Path object
        path_obj = Path(path_str)
        
        # If path is absolute, use it as is
        if path_obj.is_absolute():
            resolved_path = path_obj
        else:
            # Otherwise, resolve relative to project root
            resolved_path = cls.get_project_root() / path_obj
        
        # Cache the resolved path
        cls._cache[path_str] = resolved_path
        
        return resolved_path
    
    @classmethod
    def get_network_config_path(cls) -> Path:
        """
        Get the path to the network configuration file.
        
        Returns:
            Path to the network configuration file
        """
        key = "network_config_path"
        if key not in cls._cache:
            # Check for environment variable
            env_path = os.environ.get("NETWORK_CONFIG_PATH")
            if env_path and os.path.isfile(env_path):
                cls._cache[key] = Path(env_path).resolve()
            else:
                # Default to network_config.yaml in config directory
                cls._cache[key] = cls.get_config_dir() / "network_config.yaml"
        
        return cls._cache[key]
    
    @classmethod
    def get_agent_config_path(cls) -> Path:
        """
        Get the path to the agent configuration file.
        
        Returns:
            Path to the agent configuration file
        """
        key = "agent_config_path"
        if key not in cls._cache:
            # Check for environment variable
            env_path = os.environ.get("AGENT_CONFIG_PATH")
            if env_path and os.path.isfile(env_path):
                cls._cache[key] = Path(env_path).resolve()
            else:
                # Default to startup_config.yaml in config directory
                cls._cache[key] = cls.get_config_dir() / "startup_config.yaml"
        
        return cls._cache[key]
    
    @classmethod
    def get_temp_dir(cls) -> Path:
        """
        Get the temporary directory.
        
        Returns:
            Path to the temporary directory
        """
        key = "temp_dir"
        if key not in cls._cache:
            # Check for environment variable
            env_temp_dir = os.environ.get("TEMP_DIR")
            if env_temp_dir and os.path.isdir(env_temp_dir):
                cls._cache[key] = Path(env_temp_dir).resolve()
            else:
                # Default to system temp directory
                cls._cache[key] = Path(os.path.join(os.path.dirname(cls.get_project_root()), "temp"))
                
                # Create directory if it doesn't exist
                cls._cache[key].mkdir(exist_ok=True)
        
        return cls._cache[key]

# Initialize the project root when module is imported
PathManager.get_project_root()

if __name__ == "__main__":
    # Print key paths when run directly
    print(f"Project Root: {PathManager.get_project_root()}")
    print(f"Config Dir: {PathManager.get_config_dir()}")
    print(f"Logs Dir: {PathManager.get_logs_dir()}")
    print(f"Data Dir: {PathManager.get_data_dir()}")
    print(f"Models Dir: {PathManager.get_models_dir()}")
    print(f"Network Config: {PathManager.get_network_config_path()}")
    print(f"Agent Config: {PathManager.get_agent_config_path()}")
    print(f"Temp Dir: {PathManager.get_temp_dir()}") 