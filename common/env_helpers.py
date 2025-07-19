from __future__ import annotations
"""Utility helpers for fetching and validating environment variables.

This module is introduced as part of WP-00 (Bootstrap) to centralise environment
configuration access across all agents.  All new code – and legacy agents during
migration – should import from `common.env_helpers` instead of using `os.getenv`
scattered throughout the codebase.
"""

import os
from typing import Optional, TypeVar, Callable, cast

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Core getters
# ---------------------------------------------------------------------------

def get_env(name: str, default: Optional[str] | None = None, *, required: bool = False) -> str:
    """Return the value of *name* from the environment.

    Parameters
    ----------
    name:
        Environment variable key.
    default:
        Fallback value if key not present. Ignored when *required* is ``True``.
    required:
        When *True* the absence of *name* raises :class:`KeyError`.
    """
    try:
        value = os.environ[name]
    except KeyError:
        if required:
            raise KeyError(f"Missing required environment variable '{name}'.") from None
        if default is None:
            raise KeyError(
                f"Environment variable '{name}' not set and no default provided.") from None
        value = default
    return value


def get_int(name: str, default: int | None = None, *, required: bool = False) -> int:
    """Fetch *name* and cast to :class:`int`."""
    raw = get_env(name, None if required else str(default) if default is not None else None, required=required)
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Expected integer for env '{name}', got '{raw}'.") from exc


def get_float(name: str, default: float | None = None, *, required: bool = False) -> float:
    """Fetch *name* and cast to :class:`float`."""
    raw = get_env(name, None if required else str(default) if default is not None else None, required=required)
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Expected float for env '{name}', got '{raw}'.") from exc


def get_bool(name: str, default: bool | None = None, *, required: bool = False) -> bool:
    """Fetch *name* and cast to :class:`bool`.

    Truthy values: "1", "true", "yes", "on" (case-insensitive).
    Falsy  values: "0", "false", "no", "off".
    """
    raw = get_env(name, None if required else str(default).lower() if default is not None else None, required=required)
    lowered = raw.lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean literal for env '{name}': '{raw}'.")

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def require_set(*names: str) -> None:
    """Ensure all *names* are present in ``os.environ``.

    Raises
    ------
    KeyError
        If any name is missing.
    """
    missing = [n for n in names if n not in os.environ]
    if missing:
        raise KeyError(f"Required environment variables missing: {', '.join(missing)}")


__all__ = [
    "get_env",
    "get_int",
    "get_float",
    "get_bool",
    "require_set",
]