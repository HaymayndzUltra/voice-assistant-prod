#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Utils Package
This package provides utility functions and classes for the Voice Assistant system
"""

from main_pc_code.utils.config_loader import Config, get_instance
import importlib, sys

# Provide backward compatibility for `from main_pc_code.utils.path_manager import PathManager`
try:
    _pm = importlib.import_module('utils.path_manager')
    sys.modules[__name__ + '.path_manager'] = _pm
except ImportError:  # Should not happen in normal operation
    pass

__all__ = ['Config', 'get_instance'] 