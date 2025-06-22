"""Stub implementation of the `web_automation` package.

This lightweight stub is only meant to satisfy imports in environments where the
full `web_automation` package is not available.
It exposes a minimal `GLOBAL_TASK_MEMORY` object and stubs a few utility
sub-modules that some legacy agents expect.

If your project later integrates the real web_automation package, simply remove
this stub directory from the Python path.
"""
from __future__ import annotations

import logging
import sys
import types
from types import ModuleType
from typing import Any, Dict


class _GlobalTaskMemory(dict):
    """In-memory key-value store standing in for the real TaskMemory class."""

    def get_memory(self, key: str, default: Any | None = None) -> Any | None:
        return self.get(key, default)

    def set_memory(self, key: str, value: Any) -> None:
        self[key] = value


# Public singleton expected by the rest of the code-base
GLOBAL_TASK_MEMORY: _GlobalTaskMemory = _GlobalTaskMemory()

# ---------------------------------------------------------------------------
# Stub out the most common sub-modules referenced by legacy code so that, e.g.,
#   `from web_automation.utils import setup_logger`
#   `from web_automation.utils.task_memory import TaskMemory`
# work without the real package being present.
# ---------------------------------------------------------------------------

# utils module
_utils_mod: ModuleType = types.ModuleType("web_automation.utils")


def _setup_logger(name: str = "web_automation", level: int = logging.INFO, **kwargs: Any) -> logging.Logger:  # noqa: D401
    """Return a standard `logging` logger.

    This is *not* feature-complete compared to the original implementation but
    is good enough for typical usage within this project.
    """

    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


_utils_mod.setup_logger = _setup_logger  # type: ignore[attr-defined]

# utils.task_memory sub-module
_task_memory_mod: ModuleType = types.ModuleType("web_automation.utils.task_memory")


class TaskMemory(dict):
    """A microscopic stand-in for the real `TaskMemory` class."""

    def get(self, key: str, default: Any | None = None) -> Any | None:  # noqa: D401
        return super().get(key, default)

    def set(self, key: str, value: Any) -> None:  # noqa: D401
        self[key] = value


_task_memory_mod.TaskMemory = TaskMemory  # type: ignore[attr-defined]

# Expose sub-modules via sys.modules so regular import statements succeed
sys.modules[_utils_mod.__name__] = _utils_mod
sys.modules[_task_memory_mod.__name__] = _task_memory_mod

# Clean-up module namespace
del logging, sys, types, ModuleType, Any, Dict, _utils_mod, _task_memory_mod

__all__ = ["GLOBAL_TASK_MEMORY"]
