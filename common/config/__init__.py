#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Common Configuration Package

Unified configuration management with validation and schema support.
Part of Phase 1.2 + Phase 2.4 - O3 Roadmap Implementation
"""

# Core configuration management
from .unified_config_manager import Config, ConfigError

# Configuration validation (Phase 2.4)
from .validation import (
    ConfigValidator,
    ValidationLevel,
    ValidationResult,
    ValidationReporter,
    validate_config_file,
    validate_agent_config,
    validate_all_configs,
    get_validator
)

__all__ = [
    # Core config
    "Config", 
    "ConfigError",
    # Validation
    "ConfigValidator",
    "ValidationLevel", 
    "ValidationResult",
    "ValidationReporter",
    "validate_config_file",
    "validate_agent_config",
    "validate_all_configs",
    "get_validator"
]

# Version info
__version__ = "2.4.0"
__phase__ = "Phase 1.2 + Phase 2.4: Unified Config + Validation"
