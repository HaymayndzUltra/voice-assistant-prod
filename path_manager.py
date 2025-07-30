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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PathManager:
    """Centralized path management for the AI System."""
    _cache: Dict[str, Path] = {}
    _project_root: Optional[Path] = None

    @classmethod
    def get_project_root(cls) -> Path:
        """
        Get the project root directory.
        
        Returns:
            Path to the project root directory
        """
        if cls._project_root is None:
            env_root = os.environ.get('PROJECT_ROOT')
            if env_root and os.path.isdir(env_root):
                cls._project_root = Path(env_root).resolve()
            else:
                current_file = Path(__file__).resolve()
                current_dir = current_file.parent
                while current_dir.name and current_dir != current_dir.parent:
                    if any(((current_dir / marker).exists() for marker in ['.git', 'main_pc_code', 'pc2_code', 'config/network_config.yaml'])):
                        cls._project_root = current_dir
                        break
                    current_dir = current_dir.parent
                if cls._project_root is None:
                    if 'main_pc_code/utils' in str(current_file):
                        cls._project_root = current_file.parent.parent.parent
                    else:
                        cls._project_root = Path.cwd()
                        logger.warning(f'Could not determine project root, using current directory: {cls._project_root}')
            project_root_str = str(cls._project_root)
            if project_root_str not in sys.path:
                sys.path.insert(0, project_root_str)
                logger.debug(f'Added {project_root_str} to Python path')
            logger.info(f'Project root: {cls._project_root}')
        return cls._project_root

    @classmethod
    def get_config_dir(cls) -> Path:
        """
        Get the configuration directory.
        
        Returns:
            Path to the configuration directory
        """
        key = 'config_dir'
        if key not in cls._cache:
            env_config_dir = os.environ.get('CONFIG_DIR')
            if env_config_dir and os.path.isdir(env_config_dir):
                cls._cache[key] = Path(env_config_dir).resolve()
            else:
                cls._cache[key] = cls.get_project_root() / 'config'
                cls._cache[key].mkdir(exist_ok=True)
        return cls._cache[key]

    @classmethod
    def get_logs_dir(cls) -> Path:
        """
        Get the logs directory.
        
        Returns:
            Path to the logs directory
        """
        key = 'logs_dir'
        if key not in cls._cache:
            env_logs_dir = os.environ.get('LOGS_DIR')
            if env_logs_dir and os.path.isdir(env_logs_dir):
                cls._cache[key] = Path(env_logs_dir).resolve()
            else:
                cls._cache[key] = cls.get_project_root() / 'logs'
                cls._cache[key].mkdir(exist_ok=True)
        return cls._cache[key]

    @classmethod
    def get_data_dir(cls) -> Path:
        """
        Get the data directory.
        
        Returns:
            Path to the data directory
        """
        key = 'data_dir'
        if key not in cls._cache:
            env_data_dir = os.environ.get('DATA_DIR')
            if env_data_dir and os.path.isdir(env_data_dir):
                cls._cache[key] = Path(env_data_dir).resolve()
            else:
                cls._cache[key] = cls.get_project_root() / 'data'
                cls._cache[key].mkdir(exist_ok=True)
        return cls._cache[key]

    @classmethod
    def get_models_dir(cls) -> Path:
        """
        Get the models directory.
        
        Returns:
            Path to the models directory
        """
        key = 'models_dir'
        if key not in cls._cache:
            env_models_dir = os.environ.get('MODELS_DIR')
            if env_models_dir and os.path.isdir(env_models_dir):
                cls._cache[key] = Path(env_models_dir).resolve()
            else:
                cls._cache[key] = cls.get_project_root() / 'models'
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
        if path_str in cls._cache:
            return cls._cache[path_str]
        path_obj = Path(path_str)
        if path_obj.is_absolute():
            resolved_path = path_obj
        else:
            resolved_path = cls.get_project_root() / path_obj
        cls._cache[path_str] = resolved_path
        return resolved_path

    @classmethod
    def get_network_config_path(cls) -> Path:
        """
        Get the path to the network configuration file.
        
        Returns:
            Path to the network configuration file
        """
        key = 'network_config_path'
        if key not in cls._cache:
            env_path = os.environ.get('NETWORK_CONFIG_PATH')
            if env_path and os.path.isfile(env_path):
                cls._cache[key] = Path(env_path).resolve()
            else:
                cls._cache[key] = cls.get_config_dir() / 'network_config.yaml'
        return cls._cache[key]

    @classmethod
    def get_agent_config_path(cls) -> Path:
        """
        Get the path to the agent configuration file.
        
        Returns:
            Path to the agent configuration file
        """
        key = 'agent_config_path'
        if key not in cls._cache:
            env_path = os.environ.get('AGENT_CONFIG_PATH')
            if env_path and os.path.isfile(env_path):
                cls._cache[key] = Path(env_path).resolve()
            else:
                cls._cache[key] = cls.get_config_dir() / 'startup_config.yaml'
        return cls._cache[key]

    @classmethod
    def get_temp_dir(cls) -> Path:
        """
        Get the temporary directory.
        
        Returns:
            Path to the temporary directory
        """
        key = 'temp_dir'
        if key not in cls._cache:
            env_temp_dir = os.environ.get('TEMP_DIR')
            if env_temp_dir and os.path.isdir(env_temp_dir):
                cls._cache[key] = Path(env_temp_dir).resolve()
            else:
                cls._cache[key] = Path(os.path.join(os.path.dirname(cls.get_project_root()), 'temp'))
                cls._cache[key].mkdir(exist_ok=True)
        return cls._cache[key]
PathManager.get_project_root()
if __name__ == '__main__':
    logger.info(f'Project Root: {PathManager.get_project_root()}')
    logger.info(f'Config Dir: {PathManager.get_config_dir()}')
    logger.info(f'Logs Dir: {PathManager.get_logs_dir()}')
    logger.info(f'Data Dir: {PathManager.get_data_dir()}')
    logger.info(f'Models Dir: {PathManager.get_models_dir()}')
    logger.info(f'Network Config: {PathManager.get_network_config_path()}')
    logger.info(f'Agent Config: {PathManager.get_agent_config_path()}')
    logger.info(f'Temp Dir: {PathManager.get_temp_dir()}')