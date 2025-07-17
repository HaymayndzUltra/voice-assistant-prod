#!/usr/bin/env python3
"""MemoryServicesHub – Unified wrapper for MemoryServices group.

This thin launcher simply imports **Memory Hub** (already a multi-router
FastAPI service consolidating MemoryClient, SessionMemoryAgent, KnowledgeBase,
and other related components) and runs it.  The indirection allows startup
config to reference a dedicated *memory_services_hub.py* so we can extend or
instrument the hub later without touching the original implementation.

Behaviour, routes and data schema are **identical** to the existing Memory Hub
located at
`phase1_implementation.consolidated_agents.memory_hub.memory_hub:app`.
"""
from __future__ import annotations

import logging

import uvicorn

from phase1_implementation.consolidated_agents.memory_hub.memory_hub import app  # noqa: E402

logger = logging.getLogger("MemoryServicesHub")
logging.basicConfig(level=logging.INFO)


def main() -> None:  # noqa: D401 – CLI entry
    """Run uvicorn using the Memory Hub FastAPI app."""
    logger.info("[MemoryServicesHub] Launching Memory Hub on 0.0.0.0:7010")
    uvicorn.run(app, host="0.0.0.0", port=7010, log_level="info")


if __name__ == "__main__":
    main()