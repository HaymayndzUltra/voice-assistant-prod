#!/usr/bin/env python
"""
DEPRECATED: Dynamic command-line configuration parser for agents.

This module is deprecated. Please use utils.config_loader instead.
"""
import warnings
from .config_loader import parse_agent_args, _discover_dynamic_flags, _STANDARD_ARGS

warnings.warn(
    "'utils.config_parser' is deprecated. Please use 'utils.config_loader' instead.",
    DeprecationWarning,
    stacklevel=2
)
