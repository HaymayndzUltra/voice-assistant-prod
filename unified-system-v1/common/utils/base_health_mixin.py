from __future__ import annotations
"""BaseHealthMixin

Light-weight mixin that exposes a simple HTTP `/health` endpoint returning
`200 OK` and JSON payload `{"status": "ok"}`.  Agents that already inherit
`common.core.base_agent.BaseAgent` have a richer Prometheus-aware health
checker; this mixin is meant for small utility scripts that do *not* depend on
that heavy base class but still need to pass container orchestrator
liveness/readiness probes.

Usage:

    class MyUtilityAgent(BaseHealthMixin):
        def __init__(self):
            BaseHealthMixin.__init__(self, port=8123)
            # ... rest of init ...

The mixin starts the HTTP server in a background thread so it does not block
the agent's main loop.
"""

import http.server
import json
import socketserver
import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class _HealthRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/health", "/healthz", "/ready"):
            self.send_response(404)
            self.end_headers()
            return
        payload = json.dumps({"status": "ok"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    # Suppress default noisy logging
    def log_message(self, *_):
        pass

class BaseHealthMixin:
    """Provide minimal HTTP health endpoint on given `health_port`."""

    def __init__(self, port: int = 8000, bind_address: str = "0.0.0.0"):
        self._health_port: int = port
        self._bind_address: str = bind_address
        self._health_thread: Optional[threading.Thread] = None
        self._start_health_server()

    def _start_health_server(self):
        def _serve():
            with socketserver.TCPServer((self._bind_address, self._health_port), _HealthRequestHandler) as httpd:
                logger.info(f"Health endpoint listening on {self._bind_address}:{self._health_port}")
                httpd.serve_forever()

        self._health_thread = threading.Thread(target=_serve, name="health-server", daemon=True)
        self._health_thread.start()