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
from contextlib import contextmanager

__all__ = ["emit", "span"]

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


# ---------------------------------------------------------------------------
# Span helper for timed events
# ---------------------------------------------------------------------------


@contextmanager
def span(name: str, *, stream=None, **fields: Any):  # noqa: D401
    """Context manager that emits *_start and *_end events with duration.

    Example::

        with span("task", description="Refactor module X"):
            heavy_work()
    """
    start_ts = _now()
    emit(f"{name}_start", stream=stream, **fields)
    try:
        yield
    except Exception as exc:  # noqa: BLE001
        emit(f"{name}_error", stream=stream, error=str(exc), **fields)
        raise
    else:
        duration = _now() - start_ts
        emit(f"{name}_end", stream=stream, duration=duration, **fields)