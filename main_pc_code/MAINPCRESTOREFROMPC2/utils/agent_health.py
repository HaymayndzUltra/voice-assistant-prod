"""Lightweight health probe utility for agents.

Usage::

from main_pc_code.utils.agent_health import start_health_probe, set_ready
    start_health_probe(port)   # call ASAP, returns immediately
    ... heavy initialisation ...
    set_ready(True)            # when agent fully ready (optional)

The probe opens a plain TCP server on the given port (or port+1 if already
in use) in a daemon thread.  Any client that connects receives ``OK`` (or
``INIT`` until ready flag is set).  The connection then closes.  This lets
external health-checkers succeed instantly without blocking the main agent
startup.
"""
from __future__ import annotations

import socket
import threading
import logging
from contextlib import closing

__all__ = ["start_health_probe", "set_ready"]

_ready = False
_logger = logging.getLogger("agent_health")


def set_ready(value: bool = True) -> None:
    global _ready
    _ready = value


def _probe_server(port: int):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("", port))
        s.listen(5)
        _logger.info(f"Health probe listening on port {port}")
        while True:
            try:
                conn, _ = s.accept()
                with conn:
                    msg = b"OK" if _ready else b"INIT"
                    try:
                        conn.sendall(msg)
                    except Exception:  # pragma: no cover
                        pass
            except Exception as e:  # pragma: no cover
                _logger.warning(f"Health probe error: {e}")


def start_health_probe(port: int) -> int:
    """Start health probe in background. Returns the port being used."""
    try_port = port
    while True:
        try:
            # quick test bind then close to ensure availability
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.bind(("", try_port))
            test_sock.close()
            break
        except OSError:
            try_port += 1
    thread = threading.Thread(target=_probe_server, args=(try_port,), daemon=True)
    thread.start()
    return try_port
