"""
Shared utility functions used across multiple modules.
Consolidates common functionality to reduce code duplication.
"""

import logging
import sys
import asyncio
from typing import Any, Dict, Optional, Callable
from pathlib import Path


def setup_logging(name: str, level: str = "INFO") -> logging.Logger:
    """
    Set up logging configuration for a module.
    
    Args:
        name: Logger name (usually __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding multiple handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger


def cleanup_resources(*resources: Any) -> None:
    """
    Generic cleanup function for various resources.
    
    Args:
        *resources: Variable number of resources to clean up
    """
    for resource in resources:
        try:
            if hasattr(resource, 'close'):
                resource.close()
            elif hasattr(resource, 'cleanup'):
                resource.cleanup()
            elif hasattr(resource, 'shutdown'):
                resource.shutdown()
            elif asyncio.iscoroutine(resource):
                asyncio.create_task(resource)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error cleaning up resource {resource}: {e}")


def check_health(service_name: str, health_check_func: Callable[[], bool]) -> Dict[str, Any]:
    """
    Generic health check function for services.
    
    Args:
        service_name: Name of the service being checked
        health_check_func: Function that returns True if healthy
        
    Returns:
        Dict with health status information
    """
    try:
        is_healthy = health_check_func()
        return {
            "service": service_name,
            "status": "HEALTHY" if is_healthy else "UNHEALTHY",
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "service": service_name,
            "status": "ERROR",
            "error": str(e),
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }


def load_config(config_path: str, default_config: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Load configuration from a file with fallback to defaults.
    
    Args:
        config_path: Path to configuration file
        default_config: Default configuration to use if file not found
        
    Returns:
        Configuration dictionary
    """
    config_file = Path(config_path)
    
    if config_file.exists():
        import json
        try:
            with open(config_file, 'r') as f:
                if config_file.suffix == '.json':
                    return json.load(f)
                elif config_file.suffix in ['.yaml', '.yml']:
                    import yaml
                    return yaml.safe_load(f)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error loading config from {config_path}: {e}")
            
    return default_config or {}


def ensure_directory(path: str) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        Path object for the directory
    """
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def safe_import(module_name: str, attribute: Optional[str] = None) -> Optional[Any]:
    """
    Safely import a module or attribute, returning None if not available.
    
    Args:
        module_name: Name of the module to import
        attribute: Optional attribute to get from the module
        
    Returns:
        Module or attribute, or None if import fails
    """
    try:
        module = __import__(module_name, fromlist=[attribute] if attribute else [])
        return getattr(module, attribute) if attribute else module
    except ImportError:
        return None


def run_async(coro: Any) -> Any:
    """
    Run an async coroutine in a sync context.
    
    Args:
        coro: Coroutine to run
        
    Returns:
        Result of the coroutine
    """
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If loop is already running, schedule the coroutine
        return asyncio.create_task(coro)
    else:
        # Otherwise, run it
        return loop.run_until_complete(coro)