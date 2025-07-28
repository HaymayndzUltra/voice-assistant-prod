"""
Shared utility functions for all agents to reduce code duplication and improve performance.
"""

import functools
import time
import sys
import importlib
import types
import atexit
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for delay
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {current_delay}s...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            
            raise last_exception
        return wrapper
    return decorator

def lazy_import(module_name: str):
    """
    Lazy import a module to improve startup time.
    
    Args:
        module_name: Name of module to lazily import
    """
    class LazyModule(types.ModuleType):
        def __getattr__(self, item):
            try:
                module = importlib.import_module(module_name)
                # Replace the lazy module with the real one
                sys.modules[module_name] = module
                return getattr(module, item)
            except ImportError as e:
                logger.warning(f"Failed to lazy import {module_name}: {e}")
                raise
    
    # Only replace if not already imported
    if module_name not in sys.modules:
        sys.modules[module_name] = LazyModule(module_name)

def std_health_response(status: str = "healthy", details: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Generate standardized health check response.
    
    Args:
        status: Health status ('healthy', 'unhealthy', 'degraded')
        details: Optional additional details
    
    Returns:
        Standardized health response dict
    """
    response = {
        "status": status,
        "timestamp": time.time(),
        "details": details or {}
    }
    return response

# Global cleanup registry
_cleanup_functions: List[Callable] = []

def register_cleanup(cleanup_func: Callable):
    """
    Register a cleanup function to be called on exit.
    
    Args:
        cleanup_func: Function to call during cleanup
    """
    _cleanup_functions.append(cleanup_func)

def run_cleanup():
    """Execute all registered cleanup functions."""
    for cleanup_func in _cleanup_functions:
        try:
            cleanup_func()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Register global cleanup handler
atexit.register(run_cleanup)

def setup_lazy_imports():
    """Setup lazy imports for heavy modules to improve startup time."""
    heavy_modules = [
        'torch',
        'TTS', 
        'sounddevice',
        'numpy',
        'transformers',
        'sklearn',
        'matplotlib',
        'cv2'
    ]
    
    for module in heavy_modules:
        try:
            lazy_import(module)
            logger.debug(f"Set up lazy import for {module}")
        except Exception as e:
            logger.debug(f"Could not set up lazy import for {module}: {e}")
