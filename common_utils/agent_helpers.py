"""common_utils.agent_helpers
Shared utilities for all agents:
 - retry decorator with exponential back-off
 - std_health_response helper (consistent schema)
 - register_cleanup for graceful shutdown
 - lazy_import convenience (defers heavy import until first attribute access)
"""
from __future__ import annotations

import atexit
import functools
import importlib
import logging
import sys
import time
from types import ModuleType
from typing import Any, Callable, Iterable, List, Optional

__all__ = [
    "retry",
    "std_health_response",
    "register_cleanup",
    "lazy_import",
]

# ----------------------------------------------------------------------------
# Retry decorator
# ----------------------------------------------------------------------------

def retry(
    exceptions: tuple[type[Exception], ...] | type[Exception] = Exception,
    tries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    logger: Optional[logging.Logger] = None,
):
    """Retry calling the decorated function using an exponential backoff.

    Source-agnostic helper pulled out from several agents.

    Args:
        exceptions: exception(s) that trigger a retry.
        tries: total number of attempts.
        delay: initial delay between attempts in seconds.
        backoff: multiplier applied to delay after each failure.
        logger: optional logger to write exceptions to; if None, root logger.
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _tries, _delay = tries, delay
            while _tries > 1:
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    (_logger := logger or logging.getLogger(func.__module__)).warning(
                        "%s failed with %s. Retrying in %.1fs (%d tries left)",
                        func.__name__, exc, _delay, _tries - 1,
                    )
                    time.sleep(_delay)
                    _tries -= 1
                    _delay *= backoff
            # Final attempt – let exceptions propagate
            return func(*args, **kwargs)

        return wrapper

    return decorator


# ----------------------------------------------------------------------------
# Standard health-check response
# ----------------------------------------------------------------------------
_START_TS = time.time()


def std_health_response(additional: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Return a consistent health-check payload used across agents."""
    data = {
        "status": "ok",
        "uptime": round(time.time() - _START_TS, 2),
    }
    if additional:
        data.update(additional)
    return data


# ----------------------------------------------------------------------------
# Cleanup handling
# ----------------------------------------------------------------------------

_cleanup_funcs: List[Callable[[], Any]] = []


def register_cleanup(func: Callable[[], Any]) -> None:
    """Register a callable to be executed at interpreter exit."""
    _cleanup_funcs.append(func)


@atexit.register  # noqa: D401 – Simple phrase is fine here
def _run_cleanups() -> None:
    for func in _cleanup_funcs:
        try:
            func()
        except Exception:  # pragma: no cover – best-effort cleanup
            logging.exception("Cleanup callable %s raised", func)


# ----------------------------------------------------------------------------
# Lazy import helper
# ----------------------------------------------------------------------------


class _LazyModule(ModuleType):
    """Module proxy that loads the real module on first attribute access."""

    def __init__(self, name: str):
        super().__init__(name)
        self.__dict__["__lazy_name__"] = name
        self.__dict__["__loaded__"] = False

    def _load(self):
        if self.__dict__["__loaded__"]:
            return sys.modules[self.__lazy_name__]
        real_module = importlib.import_module(self.__lazy_name__)
        sys.modules[self.__lazy_name__] = real_module
        self.__dict__["__loaded__"] = True
        self.__dict__.update(real_module.__dict__)
        return real_module

    def __getattr__(self, item):
        module = self._load()
        return getattr(module, item)


def lazy_import(module_name: str) -> ModuleType:
    """Return a lazy proxy for *module_name* and register it in *sys.modules*.

    If the module is already imported, it is returned as-is.
    """
    if module_name in sys.modules:
        return sys.modules[module_name]
    proxy = _LazyModule(module_name)
    sys.modules[module_name] = proxy
    return proxy