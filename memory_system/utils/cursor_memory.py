"""Cursor Memory Utilities

Provides helper to store summaries to MCP memory graph and append to
memory-bank/current-session.md. Safe to call even if `mcp_memory_store` binary
is unavailable (no-op fallback).
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from datetime import datetime

MEMORY_FILE = Path("memory-bank/current-session.md")


def store_summary(text: str) -> None:  # noqa: D401
    timestamp = datetime.utcnow().isoformat(timespec="seconds")
    entry = f"\n[{timestamp}] {text}\n"

    # 1. Append to current-session.md
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with MEMORY_FILE.open("a", encoding="utf-8") as fp:
        fp.write(entry)

    # 2. Try invoking mcp_memory_store if present
    try:
        subprocess.run(["mcp_memory_store", text], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        # Binary not present – ignore
        pass