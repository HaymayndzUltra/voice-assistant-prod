#!/usr/bin/env python3
"""
Compatibility shim for MainPC PathManager imports.

This module redirects all PathManager imports to the consolidated 
common/utils/path_manager.py implementation while maintaining
backward compatibility.

IMPORTANT: This is a temporary shim during the consolidation phase.
All new code should import directly from common.utils.path_manager.

Usage:
    # Old way (still works via this shim)
    from main_pc_code.utils.path_manager import PathManager
    
    # New way (preferred)
    from common.utils.path_manager import PathManager
"""

import warnings
import logging

# Show deprecation warning for MainPC PathManager usage
warnings.warn(
    "Importing from main_pc_code.utils.path_manager is deprecated. "
    "Use 'from common.utils.path_manager import PathManager' instead.",
    DeprecationWarning,
    stacklevel=2
)

logger = logging.getLogger(__name__)
logger.info("PathManager: Redirecting MainPC import to consolidated common version")

# Import and re-export the consolidated PathManager
try:
    from common.utils.path_manager import PathManager
    
    # Re-export for backward compatibility
    __all__ = ['PathManager']
    
    # Also support the old module-level join_path function
    def join_path(*args):
        """Legacy module-level join_path function for backward compatibility."""
        return PathManager.join_path(*args)
    
    logger.debug("PathManager shim: Successfully imported consolidated version")
    
except ImportError as e:
    logger.error(f"PathManager shim: Failed to import consolidated version: {e}")
    raise ImportError(
        "Could not import consolidated PathManager from common.utils.path_manager. "
        "Ensure the common/utils/path_manager.py file exists and is properly configured."
    ) from e
