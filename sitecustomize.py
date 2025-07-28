"""
Global sitecustomize.py to automatically enable lazy loading of heavy modules.
This file is automatically imported by Python on startup.
"""

try:
    # Enable lazy loading as early as possible
    import common_utils.lazy_loader
    # The lazy_loader module automatically enables lazy loading on import
except ImportError:
    # Silently fail if common_utils is not available
    pass
except Exception:
    # Silently fail for any other errors to avoid breaking the system
    pass
