"""Minimal stub for a `conf` module expected by some legacy scripts.

This module exposes a single attribute, `settings`, which behaves like a simple
namespace/dictionary for configuration values.  Extend as needed.
"""
from types import SimpleNamespace

settings = SimpleNamespace()

# Example default values – extend or remove as appropriate
settings.DEBUG = False
settings.VERSION = "0.0.1-stub"

__all__ = ["settings"]
