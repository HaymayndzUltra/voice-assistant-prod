"""
Configuration validation module for AI Agent System.

This module provides JSON schema validation for agent startup configurations
to prevent config drift between MainPC and PC2 systems.
"""

from .config_validator import ConfigValidator

__all__ = ['ConfigValidator'] 