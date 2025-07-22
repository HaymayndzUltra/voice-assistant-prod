import os
from pathlib import Path
from typing import Optional

class PathManager:
    """
    Centralized path management for the AI System.
    This class provides a consistent way to access directories and files
    across the entire system, making it containerization-friendly.
    """
    
    @staticmethod
    def get_project_root():
        """Return the absolute path to the project root directory."""
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    
    @staticmethod
    def get_logs_dir():
        """Return the logs directory path."""
        return Path(PathManager.get_project_root()) / "logs"
    
    @staticmethod
    def get_data_dir():
        """Return the data directory path."""
        return Path(PathManager.get_project_root()) / "data"
    
    @staticmethod
    def get_config_dir():
        """Return the config directory path."""
        return Path(PathManager.get_project_root()) / "config"
    
    @staticmethod
    def get_models_dir():
        """Return the models directory path."""
        return Path(PathManager.get_project_root()) / "models"
    
    @staticmethod
    def get_cache_dir():
        """Return the cache directory path."""
        return Path(PathManager.get_project_root()) / "cache"

    @staticmethod
    def resolve_script(relative_path: str) -> Optional[Path]:
        """
        Resolve any script_path in YAML to an absolute path under project root.
        
        This method fixes the start_system_v2.py validation bug by properly
        resolving relative script paths to absolute paths within the project.
        
        Args:
            relative_path: Relative path from project root (e.g., "main_pc_code/agents/service.py")
            
        Returns:
            Absolute Path object if script exists, None if not found
            
        Example:
            path = PathManager.resolve_script("main_pc_code/agents/service_registry_agent.py")
            if path and path.exists():
                print(f"Script found at: {path}")
        """
        if not relative_path:
            return None
            
        # Get project root as Path object
        project_root = Path(PathManager.get_project_root())
        
        # Resolve the relative path to absolute
        absolute_path = (project_root / relative_path).resolve()
        
        # Verify the resolved path is still within project root (security check)
        try:
            absolute_path.relative_to(project_root)
        except ValueError:
            # Path is outside project root - potential security issue
            return None
            
        # Return the absolute path (existence check is done by caller)
        return absolute_path
    
    @staticmethod
    def resolve_path(relative_path: str) -> Path:
        """
        General purpose path resolver for any relative path within project.
        
        Args:
            relative_path: Relative path from project root
            
        Returns:
            Absolute Path object (existence not guaranteed)
        """
        project_root = Path(PathManager.get_project_root())
        return (project_root / relative_path).resolve()
    
    @staticmethod
    def ensure_directory(directory_path: Path) -> Path:
        """
        Ensure directory exists, creating it if necessary.
        
        Args:
            directory_path: Path object for directory
            
        Returns:
            Path object of the directory
        """
        directory_path.mkdir(parents=True, exist_ok=True)
        return directory_path
