import os
import logging
from pathlib import Path
from typing import Optional, Union, Dict

# Configure logging
logger = logging.getLogger(__name__)

class PathManager:
    """
    Centralized path management for the AI System.
    This class provides a consistent way to access directories and files
    across the entire system, making it containerization-friendly.
    
    Features:
    - Caching for performance
    - Environment variable overrides
    - Auto-creation of directories
    - Docker/container-friendly paths
    """
    
    # Cache for resolved paths (merged from MainPC version)
    _cache: Dict[str, Path] = {}
    
    # Project root path
    _project_root: Optional[Path] = None
    
    @classmethod
    def get_project_root(cls) -> Path:
        """
        Get the project root directory with caching and environment override support.
        
        Returns:
            Path to the project root directory
        """
        if cls._project_root is None:
            # Try environment variable first (merged from MainPC)
            env_root = os.environ.get("PROJECT_ROOT")
            if env_root and os.path.isdir(env_root):
                cls._project_root = Path(env_root).resolve()
                logger.info(f"Using PROJECT_ROOT from environment: {cls._project_root}")
            else:
                # Find project root by looking for key markers (improved detection)
                current_file = Path(__file__).resolve()
                current_dir = current_file.parent
                
                # Go up the directory tree until we find the project root
                while current_dir.name and current_dir != current_dir.parent:
                    # Check for key markers that indicate project root
                    if any((current_dir / marker).exists() for marker in [
                        ".git",
                        "main_pc_code",
                        "pc2_code",
                        "config/network_config.yaml",
                        "startup_config.yaml"
                    ]):
                        cls._project_root = current_dir
                        break
                    
                    # Go up one directory
                    current_dir = current_dir.parent
                
                # If we couldn't find the project root, use fallback
                if cls._project_root is None:
                    # This file is in common/utils, so go up two directories
                    cls._project_root = current_file.parent.parent.parent
                    logger.warning(
                        f"Could not find project root markers, using fallback: {cls._project_root}"
                    )
            
            logger.info(f"Project root resolved to: {cls._project_root}")
        
        return cls._project_root
    
    @staticmethod
    def get_main_pc_code():
        """Return the absolute path to the main_pc_code directory."""
        return str(Path(PathManager.get_project_root()) / "main_pc_code")
    
    @staticmethod
    def get_pc2_code():
        """Return the absolute path to the pc2_code directory."""
        return str(Path(PathManager.get_project_root()) / "pc2_code")
    
    @classmethod
    def get_logs_dir(cls) -> Path:
        """
        Get the logs directory with caching and environment override support.
        
        Returns:
            Path to the logs directory
        """
        key = "logs_dir"
        if key not in cls._cache:
            # Check for environment variable override
            env_logs_dir = os.environ.get("LOGS_DIR")
            if env_logs_dir and os.path.isdir(env_logs_dir):
                cls._cache[key] = Path(env_logs_dir).resolve()
                logger.debug(f"Using LOGS_DIR from environment: {cls._cache[key]}")
            else:
                # Default to logs directory in project root
                cls._cache[key] = cls.get_project_root() / "logs"
                
                # Create directory if it doesn't exist (auto-creation feature)
                cls._cache[key].mkdir(exist_ok=True)
                logger.debug(f"Using default logs directory: {cls._cache[key]}")
        
        return cls._cache[key]
    
    @classmethod
    def get_data_dir(cls) -> Path:
        """Get the data directory with caching and environment override support."""
        key = "data_dir"
        if key not in cls._cache:
            env_data_dir = os.environ.get("DATA_DIR")
            if env_data_dir and os.path.isdir(env_data_dir):
                cls._cache[key] = Path(env_data_dir).resolve()
            else:
                cls._cache[key] = cls.get_project_root() / "data"
                cls._cache[key].mkdir(exist_ok=True)
        return cls._cache[key]
    
    @classmethod
    def get_config_dir(cls) -> Path:
        """Get the config directory with caching and environment override support."""
        key = "config_dir"
        if key not in cls._cache:
            env_config_dir = os.environ.get("CONFIG_DIR")
            if env_config_dir and os.path.isdir(env_config_dir):
                cls._cache[key] = Path(env_config_dir).resolve()
            else:
                cls._cache[key] = cls.get_project_root() / "config"
                cls._cache[key].mkdir(exist_ok=True)
        return cls._cache[key]
    
    @classmethod
    def get_models_dir(cls) -> Path:
        """Get the models directory with caching and environment override support."""
        key = "models_dir"
        if key not in cls._cache:
            env_models_dir = os.environ.get("MODELS_DIR")
            if env_models_dir and os.path.isdir(env_models_dir):
                cls._cache[key] = Path(env_models_dir).resolve()
            else:
                cls._cache[key] = cls.get_project_root() / "models"
                cls._cache[key].mkdir(exist_ok=True)
        return cls._cache[key]
    
    @classmethod
    def get_cache_dir(cls) -> Path:
        """Get the cache directory with caching and environment override support."""
        key = "cache_dir"
        if key not in cls._cache:
            env_cache_dir = os.environ.get("CACHE_DIR")
            if env_cache_dir and os.path.isdir(env_cache_dir):
                cls._cache[key] = Path(env_cache_dir).resolve()
            else:
                cls._cache[key] = cls.get_project_root() / "cache"
                cls._cache[key].mkdir(exist_ok=True)
        return cls._cache[key]

    @staticmethod
    def get_path(path_type: str) -> str:
        """
        Get path based on type for compatibility with legacy path_env usage.
        
        Args:
            path_type: Type of path ('project_root', 'main_pc_code', 'pc2_code', 'logs', 'data', 'config', 'models', 'cache')
            
        Returns:
            Absolute path as string
        """
        path_map = {
            'project_root': PathManager.get_project_root(),
            'main_pc_code': PathManager.get_main_pc_code(),
            'pc2_code': PathManager.get_pc2_code(),
            'logs': str(PathManager.get_logs_dir()),
            'data': str(PathManager.get_data_dir()),
            'config': str(PathManager.get_config_dir()),
            'models': str(PathManager.get_models_dir()),
            'cache': str(PathManager.get_cache_dir()),
        }
        return path_map.get(path_type, PathManager.get_project_root())
    
    @staticmethod
    def join_path(*paths: str) -> str:
        """
        Join path components using os.path.join for compatibility.
        
        This method provides the expected signature that most of the codebase uses:
        PathManager.join_path("logs", "file.log") instead of requiring a path_type.
        
        Args:
            *paths: Path components to join
            
        Returns:
            Joined path as string
        """
        if not paths:
            return ""
        return os.path.join(*paths)
    
    @classmethod
    def resolve_path(cls, path: Union[str, Path]) -> Path:
        """
        Resolve a path relative to the project root with caching.
        
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
    def get_temp_dir(cls) -> Path:
        """Get the temporary directory with caching and environment override support."""
        key = "temp_dir"
        if key not in cls._cache:
            env_temp_dir = os.environ.get("TEMP_DIR")
            if env_temp_dir and os.path.isdir(env_temp_dir):
                cls._cache[key] = Path(env_temp_dir).resolve()
            else:
                cls._cache[key] = cls.get_project_root() / "temp"
                cls._cache[key].mkdir(exist_ok=True)
        return cls._cache[key]
    
    @classmethod
    def get_network_config_path(cls) -> Path:
        """Get the network configuration file path with environment override support."""
        key = "network_config_path"
        if key not in cls._cache:
            env_path = os.environ.get("NETWORK_CONFIG_PATH")
            if env_path and os.path.isfile(env_path):
                cls._cache[key] = Path(env_path).resolve()
            else:
                cls._cache[key] = cls.get_config_dir() / "network_config.yaml"
        return cls._cache[key]
    
    @classmethod 
    def get_agent_config_path(cls) -> Path:
        """Get the agent configuration file path with environment override support."""
        key = "agent_config_path"
        if key not in cls._cache:
            env_path = os.environ.get("AGENT_CONFIG_PATH")
            if env_path and os.path.isfile(env_path):
                cls._cache[key] = Path(env_path).resolve()
            else:
                cls._cache[key] = cls.get_config_dir() / "startup_config.yaml"
        return cls._cache[key]

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
