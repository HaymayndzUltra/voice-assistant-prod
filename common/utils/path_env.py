import os
import sys
from pathlib import Path
from typing import Dict, Optional, Union

class PathManager:
    """
    Centralized path management for the AI System.
    This class provides a consistent way to access directories and files
    across the entire system, making it containerization-friendly.
    """
    
    def __init__(self):
        # Determine the project root based on environment variable or current file location
        self.project_root = os.environ.get(
            "PROJECT_ROOT", 
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        )
        
        # Main directories
        self.main_pc_code = os.path.join(self.project_root, "main_pc_code")
        self.pc2_code = os.path.join(self.project_root, "pc2_code")
        
        # Common subdirectories
        self._subdirs = {
            "config": os.path.join(self.project_root, "config"),
            "logs": os.path.join(self.project_root, "logs"),
            "data": os.path.join(self.project_root, "data"),
            "models": os.path.join(self.project_root, "models"),
            "cache": os.path.join(self.project_root, "cache"),
            "certificates": os.path.join(self.project_root, "certificates"),
            "temp": os.path.join(self.project_root, "temp"),
            
            # Main PC specific paths
            "main_pc_agents": os.path.join(self.main_pc_code, "agents"),
            "main_pc_config": os.path.join(self.main_pc_code, "config"),
            "main_pc_logs": os.path.join(self.main_pc_code, "logs"),
            "main_pc_data": os.path.join(self.main_pc_code, "data"),
            "main_pc_cache": os.path.join(self.main_pc_code, "cache"),
            
            # PC2 specific paths
            "pc2_agents": os.path.join(self.pc2_code, "agents"),
            "pc2_config": os.path.join(self.pc2_code, "config"),
            "pc2_logs": os.path.join(self.pc2_code, "logs"),
            "pc2_data": os.path.join(self.pc2_code, "data"),
            "pc2_cache": os.path.join(self.pc2_code, "cache"),
        }
        
        # Ensure all directories exist
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Create all required directories if they don't exist."""
        for dir_path in self._subdirs.values():
            os.makedirs(dir_path, exist_ok=True)
    
    def get_path(self, path_type: str) -> str:
        """
        Get the absolute path for a specific directory type.
        
        Args:
            path_type: The type of path to retrieve (e.g., 'config', 'logs', 'data')
            
        Returns:
            The absolute path for the requested directory
            
        Raises:
            ValueError: If the path_type is not recognized
        """
        if path_type in self._subdirs:
            return self._subdirs[path_type]
        raise ValueError(f"Unknown path type: {path_type}")
    
    def join_path(self, path_type: str, *paths: str) -> str:
        """
        Join a base directory with additional path components.
        
        Args:
            path_type: The type of base directory (e.g., 'config', 'logs', 'data')
            *paths: Additional path components to join
            
        Returns:
            The absolute joined path
            
        Raises:
            ValueError: If the path_type is not recognized
        """
        base_path = self.get_path(path_type)
        return os.path.join(base_path, *paths)
    
    def get_file_path(self, path_type: str, filename: str) -> str:
        """
        Get the absolute path for a specific file within a directory type.
        
        Args:
            path_type: The type of directory (e.g., 'config', 'logs', 'data')
            filename: The name of the file
            
        Returns:
            The absolute path to the file
            
        Raises:
            ValueError: If the path_type is not recognized
        """
        return self.join_path(path_type, filename)
    
    def get_relative_path(self, absolute_path: str) -> str:
        """
        Convert an absolute path to a path relative to the project root.
        
        Args:
            absolute_path: The absolute path to convert
            
        Returns:
            The path relative to the project root
        """
        return os.path.relpath(absolute_path, self.project_root)
    
    def add_custom_path(self, name: str, path: str) -> None:
        """
        Add a custom path to the path manager.
        
        Args:
            name: The name to associate with this path
            path: The path to store (can be relative to project_root or absolute)
            
        Raises:
            ValueError: If the name already exists
        """
        if name in self._subdirs:
            raise ValueError(f"Path name '{name}' already exists")
        
        # Convert to absolute path if it's relative
        if not os.path.isabs(path):
            path = os.path.join(self.project_root, path)
            
        self._subdirs[name] = path
        os.makedirs(path, exist_ok=True)


# Create a singleton instance for global use
path_manager = PathManager()

# Convenience functions
def get_path(path_type: str) -> str:
    """Get the absolute path for a specific directory type."""
    return path_manager.get_path(path_type)

def join_path(path_type: str, *paths: str) -> str:
    """Join a base directory with additional path components."""
    return path_manager.join_path(path_type, *paths)

def get_file_path(path_type: str, filename: str) -> str:
    """Get the absolute path for a specific file within a directory type."""
    return path_manager.get_file_path(path_type, filename)

def get_project_root() -> str:
    """Get the absolute path to the project root."""
    return path_manager.project_root

def get_main_pc_code() -> str:
    """Get the absolute path to the main_pc_code directory."""
    return path_manager.main_pc_code

def get_pc2_code() -> str:
    """Get the absolute path to the pc2_code directory."""
    return path_manager.pc2_code 