import os
from pathlib import Path

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
