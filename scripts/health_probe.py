#!/usr/bin/env python3
"""
Light-weight container health probe for AI System Monorepo.

Usage (inside container):
  CMD [ "python3", "-m", "scripts.health_probe", "--url", "http://localhost:8200/health", "--push-metrics" ]

If --push-metrics is enabled, the probe sends a JSON payload to ObservabilityHub
(endpoint provided via $OBS_HUB_PUSH or defaults to http://observability:9000/ingest).
Exit code 0 indicates healthy; non-zero indicates failure.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

import requests

__all__ = ["probe"]


def probe(url: str, timeout: float = 5.0) -> tuple[bool, dict[str, Any]]:
    """Return (is_healthy, payload)."""
    start = time.perf_counter()
    try:
        response = requests.get(url, timeout=timeout)
        latency = time.perf_counter() - start
        healthy = response.ok
        status = response.status_code
        reason = response.text[:256]  # Trim to avoid log spam
    except Exception as exc:  # noqa: BLE001
        latency = time.perf_counter() - start
        healthy = False
        status = "ERR"
        reason = str(exc)

    payload: dict[str, Any] = {
        "target": url,
        "status": "up" if healthy else "down",
        "http_status": status,
        "latency_ms": round(latency * 1000, 1),
        "timestamp": int(time.time()),
    }
    if not healthy:
        payload["error"] = reason
    return healthy, payload


def push_metrics(payload: dict[str, Any]) -> None:
    """Best-effort push of probe metrics to ObservabilityHub."""
    obs_url = os.getenv("OBS_HUB_PUSH", "http://observability:9000/ingest")
    try:
        requests.post(obs_url, json=payload, timeout=2)
    except Exception:
        # Probe must never fail due to metrics push issues
        pass


def main() -> None:  # noqa: D401
    """CLI entry-point."""
    parser = argparse.ArgumentParser(description="Unified container health probe")
    parser.add_argument("--url", required=True, help="Health endpoint URL to probe")
    parser.add_argument("--timeout", type=float, default=5.0, help="Request timeout seconds")
    parser.add_argument("--push-metrics", action="store_true", help="Send results to ObservabilityHub")
    args = parser.parse_args()

    ok, data = probe(args.url, args.timeout)
    if args.push_metrics:
        push_metrics(data)

    # Always output JSON for easy parsing in logs
    print(json.dumps(data, separators=(",", ":")))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":  # pragma: no cover
    main()