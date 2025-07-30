from __future__ import annotations
"""Standardised health-check utilities (WP-00).

Provides a decorator for HTTP frameworks (FastAPI/Flask) **and** a helper
function for ZMQ REP handlers so all agents can expose a consistent health
payload.
"""

import functools
import time
from typing import Any, Callable, Dict

from orjson import dumps  # fast JSON encoding


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _json(data: Dict[str, Any]) -> bytes:  # type: ignore[name-defined]
    """Thin wrapper around **orjson.dumps** with default options."""
    return dumps(data)  # noqa: S107 – orjson safe by default


# ---------------------------------------------------------------------------
# FastAPI / Flask decorator
# ---------------------------------------------------------------------------

def standard_health_handler(fn: Callable[..., Dict[str, Any]]) -> Callable[..., Any]:
    """Decorator to wrap user-provided diagnostic function *fn*.

    The wrapped function returns a JSON dict; the decorator injects universal
    fields (`status`, `timestamp`, `uptime_seconds`) and serialises via orjson.
    """

    _start_time = time.perf_counter()

    @functools.wraps(fn)
    def _wrapper(*args: Any, **kwargs: Any):  # type: ignore[override]
        diagnostics: Dict[str, Any] = fn(*args, **kwargs) or {}
        now = time.perf_counter()
        payload: Dict[str, Any] = {
            "status": diagnostics.get("status", "ok"),
            "timestamp": int(time.time()),
            "uptime_seconds": round(now - _start_time, 2),
            **diagnostics,
        }
        return _json(payload)

    return _wrapper


# ---------------------------------------------------------------------------
# ZMQ helper
# ---------------------------------------------------------------------------

def zmq_health_payload(additional: Dict[str, Any] | None = None) -> bytes:
    """Return standard health payload for ZMQ REP sockets."""
    return _json(
        {
            "status": "ok",
            "timestamp": int(time.time()),
            **(additional or {}),
        }
    )


__all__ = [
    "standard_health_handler",
    "zmq_health_payload",
]