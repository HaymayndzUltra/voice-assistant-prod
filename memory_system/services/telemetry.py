"""Simple Telemetry Collector

This very lightweight collector emits JSON-line events to stdout (or a provided
file-like stream) so that higher-level tooling or external log shippers can pick
up task execution metrics.

This is intentionally minimal for Phase-2; it can be replaced with full
OpenTelemetry or structured logging later.
"""
from __future__ import annotations

import json
import sys
import time
from typing import Any, Dict

__all__ = ["emit"]

def _now() -> float:  # Epoch seconds
    return time.time()

def _default_stream():
    return sys.stdout


def emit(event: str, *, stream=None, **fields: Any) -> None:  # noqa: D401
    """Emit a telemetry event as a single JSON line.

    Example:
        emit("task_start", description="Refactor module X")
    """
    payload: Dict[str, Any] = {"ts": _now(), "event": event}
    if fields:
        payload.update(fields)
    (stream or _default_stream()).write(json.dumps(payload) + "\n")
    (stream or _default_stream()).flush()