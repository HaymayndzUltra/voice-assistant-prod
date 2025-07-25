"""Common environment-specific defaults used across the codebase.
This module avoids scattering hard-coded hostnames/ports (e.g. "localhost")
throughout the project.  All agents should import helpers from here when they
need to connect to Redis or NATS.
"""
from __future__ import annotations

import os
from typing import List

# ---------------------------------------------------------------------------
# Redis helpers
# ---------------------------------------------------------------------------

def get_redis_host() -> str:
    """Return the Redis hostname for the current environment."""
    return os.getenv("REDIS_HOST", "redis")


def get_redis_port() -> int:
    """Return the Redis port for the current environment."""
    try:
        return int(os.getenv("REDIS_PORT", "6379"))
    except ValueError:
        return 6379


def get_redis_url(db: int = 0) -> str:
    """Return a redis:// URL using the host/port env vars."""
    return f"redis://{get_redis_host()}:{get_redis_port()}/{db}"

# ---------------------------------------------------------------------------
# NATS helpers
# ---------------------------------------------------------------------------

def get_nats_url() -> str:
    """Return the comma-separated NATS server list for the environment."""
    return os.getenv("NATS_URL", "nats://nats:4222")


def get_nats_servers() -> List[str]:
    """Return the list form (splits by comma)."""
    return [s.strip() for s in get_nats_url().split(",") if s.strip()]