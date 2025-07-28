"""
Lazy loading mechanism for heavy modules to improve startup performance.
"""

import sys
import importlib
import types
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class LazyModule(types.ModuleType):
    """A lazy-loading module wrapper."""
    
    def __init__(self, name: str):
        super().__init__(name)
        self._module_name = name
        self._loaded = False
        self._real_module = None
    
    def __getattr__(self, item):
        if not self._loaded:
            self._load_module()
        return getattr(self._real_module, item)
    
    def __dir__(self):
        if not self._loaded:
            self._load_module()
        return dir(self._real_module)
    
    def _load_module(self):
        """Load the actual module."""
        if self._loaded:
            return
            
        try:
            self._real_module = importlib.import_module(self._module_name)
            self._loaded = True
            
            # Replace the lazy module with the real one in sys.modules
            sys.modules[self._module_name] = self._real_module
            
            logger.debug(f"Lazy loaded module: {self._module_name}")
        except ImportError as e:
            logger.warning(f"Failed to lazy load {self._module_name}: {e}")
            raise

def enable_lazy_loading(modules: List[str]):
    """
    Enable lazy loading for specified modules.
    
    Args:
        modules: List of module names to lazy load
    """
    for module_name in modules:
        # Only apply lazy loading if module isn't already imported
        if module_name not in sys.modules:
            lazy_module = LazyModule(module_name)
            sys.modules[module_name] = lazy_module
            logger.debug(f"Enabled lazy loading for: {module_name}")
        else:
            logger.debug(f"Module {module_name} already imported, skipping lazy loading")

def enable_default_lazy_modules():
    """Enable lazy loading for commonly heavy modules."""
    default_heavy_modules = [
        'torch',
        'TTS',
        'sounddevice', 
        'numpy',
        'transformers',
        'sklearn',
        'matplotlib',
        'cv2',
        'whisper',
        'librosa',
        'scipy',
        'pandas'
    ]
    
    enable_lazy_loading(default_heavy_modules)
    logger.info(f"Enabled lazy loading for {len(default_heavy_modules)} heavy modules")

# Auto-enable lazy loading on import
enable_default_lazy_modules()
