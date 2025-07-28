"""Sitecustomize
Automatically enables lazy-loading of heavy dependencies across all agents.
This module is imported by Python at startup if present on sys.path.
"""
from common_utils.lazy_loader import enable as _enable_lazy

# Register default heavy modules for lazy loading
_enable_lazy()
