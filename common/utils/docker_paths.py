#!/usr/bin/env python3
"""
Docker Path Utilities
Centralizes path management for Docker container compatibility
Handles both development and container environments
"""

import os
from pathlib import Path
from typing import Union

# Detect if running in Docker container
def is_docker_environment() -> bool:
    """Check if running inside a Docker container"""
    return (
        os.path.exists('/.dockerenv') or
        os.environ.get('DOCKER_CONTAINER', '').lower() == 'true' or
        os.environ.get('PYTHONPATH', '').startswith('/app')
    )

def get_base_path() -> Path:
    """Get base path - /app in Docker, project root in development"""
    if is_docker_environment():
        return Path('/app')
    else:
        # Development environment - find project root
        current = Path(__file__).resolve()
        while current.parent != current:
            if (current / 'main_pc_code').exists() and (current / 'common').exists():
                return current
            current = current.parent
        return Path.cwd()

def get_logs_dir() -> Path:
    """Get logs directory path"""
    base = get_base_path()
    logs_dir = base / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir

def get_data_dir() -> Path:
    """Get data directory path"""
    base = get_base_path()
    data_dir = base / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def get_cache_dir() -> Path:
    """Get cache directory path"""
    base = get_base_path()
    cache_dir = base / 'cache'
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir

def get_temp_dir() -> Path:
    """Get temporary directory path"""
    base = get_base_path()
    temp_dir = base / 'temp'
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir

def get_config_path(config_type: str = 'mainpc') -> Path:
    """Get configuration file path"""
    base = get_base_path()
    
    if config_type.lower() == 'mainpc':
        return base / 'main_pc_code' / 'config' / 'startup_config.yaml'
    elif config_type.lower() == 'pc2':
        return base / 'pc2_code' / 'config' / 'startup_config.yaml'
    else:
        raise ValueError(f"Unknown config type: {config_type}")

def get_agent_log_path(agent_name: str) -> Path:
    """Get log file path for specific agent"""
    return get_logs_dir() / f"{agent_name}.log"

def get_agent_data_path(agent_name: str, filename: str) -> Path:
    """Get data file path for specific agent"""
    agent_data_dir = get_data_dir() / agent_name
    agent_data_dir.mkdir(parents=True, exist_ok=True)
    return agent_data_dir / filename

def get_agent_cache_dir(agent_name: str) -> Path:
    """Get cache directory for specific agent"""
    agent_cache_dir = get_cache_dir() / agent_name
    agent_cache_dir.mkdir(parents=True, exist_ok=True)
    return agent_cache_dir

def resolve_legacy_path(legacy_path: Union[str, Path]) -> Path:
    """
    Convert legacy hardcoded paths to Docker-compatible paths
    
    Examples:
        'phase1_implementation/logs/agent.log' -> '/app/logs/agent.log'
        'main_pc_code/config/startup_config.yaml' -> '/app/main_pc_code/config/startup_config.yaml'
        'data/database.db' -> '/app/data/database.db'
    """
    path_str = str(legacy_path)
    base = get_base_path()
    
    # Handle phase1_implementation paths
    if path_str.startswith('phase1_implementation/'):
        relative_path = path_str.replace('phase1_implementation/', '')
        return base / relative_path
    
    # Handle relative paths starting with main_pc_code, pc2_code, etc.
    if any(path_str.startswith(prefix) for prefix in ['main_pc_code/', 'pc2_code/', 'common/']):
        return base / path_str
    
    # Handle simple relative paths (logs/, data/, cache/, temp/)
    if path_str.startswith(('logs/', 'data/', 'cache/', 'temp/', 'models/')):
        return base / path_str
    
    # If already absolute or unclear, return as is but ensure it's a Path
    return Path(path_str)

def get_docker_volume_mappings() -> dict:
    """Get recommended Docker volume mappings"""
    return {
        'logs': '/app/logs',
        'data': '/app/data',
        'cache': '/app/cache',
        'temp': '/app/temp',
        'models': '/app/models',
        'config': '/app/config'
    }

# Compatibility aliases for existing code
def get_project_root() -> Path:
    """Alias for get_base_path() for backward compatibility"""
    return get_base_path() 