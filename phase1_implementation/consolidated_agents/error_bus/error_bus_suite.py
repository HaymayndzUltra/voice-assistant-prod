
from __future__ import annotations

"""ErrorBus consolidated wrapper (Phase‐1).

This wrapper launches the legacy error bus implementation (`pc2_code.agents.error_bus_service.ErrorBusService`)
inside the same process (thread) so that CoreOrchestrator and other services can
interact through a FastAPI façade (port 7003).

Legacy logic – DB schema, pattern scanning, ZMQ pub/sub – remains untouched to
preserve 100 % behaviour.  The facade merely exposes convenient HTTP/gRPC‐like
routes and offers an in-proc delegation path when imported as a library.
"""

import sys
import os
import logging
import threading
import time
from pathlib import Path
from typing import Dict, Any

import zmq
from fastapi import FastAPI, Request, HTTPException
import uvicorn

# ---------------------------------------------------------------------------
# Dynamic path setup & safe import of legacy ErrorBusService
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from common.core.base_agent import BaseAgent
except ImportError:
    class BaseAgent:  # Minimal placeholder
        def __init__(self, name: str, port: int, **_):
            self.name, self.port = name, port
            self.health_check_port = port + 100
            self.context = zmq.Context()
            self.start_time = time.time()
        def _get_health_status(self):  # noqa: D401
            return {"status": "ok", "uptime": time.time() - self.start_time}
        def cleanup(self):
            self.context.term()

# Safe import of legacy service implementation
try:
    from pc2_code.agents.error_bus_service import ErrorBusService
except Exception as exc:  # pylint: disable=broad-except
    ErrorBusService = None  # type: ignore[assignment]
    logging.getLogger("ErrorBusSuite").warning("Legacy ErrorBusService unavailable: %s", exc)

# ---------------------------------------------------------------------------

LOGGER = logging.getLogger("ErrorBusSuite")
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "phase1_implementation/logs/error_bus_suite.log"),
    ],
)


class ErrorBusSuite(BaseAgent):
    """Consolidated ErrorBus façade service (port 7003)."""

    def __init__(self, *, port: int = 9002, health_check_port: int = 9102):
        super().__init__(name="ErrorBusSuite", port=port, health_check_port=health_check_port)

        self._legacy: ErrorBusService | None = None  # type: ignore[valid-type]
        self._start_legacy()

        # Optional: in‐proc SystemHealthManager for additional health aggregation per corrections spec
        self._system_health: Any | None = None
        self._start_system_health_manager()

        self._ctx = zmq.Context()
        self.app = FastAPI(title="ErrorBusSuite", description="Unified error-management bus", version="1.0.0")
        self._setup_routes()
        self._startup_time = time.time()
        LOGGER.info("ErrorBusSuite ready on port %s", self.port)

    # ------------------------------------------------------------------
    # Legacy bootstrap & delegation
    # ------------------------------------------------------------------

    def _start_legacy(self):
        if ErrorBusService is None:
            LOGGER.error("Legacy ErrorBusService class not importable; running in degraded mode.")
            return
        try:
            self._legacy = ErrorBusService(port=7150)  # Keep legacy port for PUB/SUB compatibility
            threading.Thread(target=self._legacy.run, daemon=True, name="legacy_error_bus").start()
            LOGGER.info("Legacy ErrorBusService running in-proc")
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.error("Failed to start legacy ErrorBusService: %s", exc)
            self._legacy = None

    # ------------------------------------------------------------------
    # SystemHealthManager bootstrap
    # ------------------------------------------------------------------

    def _start_system_health_manager(self):
        """Launch SystemHealthManager inside this process if available."""
        try:
            from pc2_code.agents.ForPC2.system_health_manager import SystemHealthManager  # type: ignore
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.warning("SystemHealthManager unavailable: %s", exc)
            return

        try:
            self._system_health = SystemHealthManager(port=7121)  # keep legacy port
            threading.Thread(target=self._system_health.run, daemon=True, name="legacy_system_health").start()
            LOGGER.info("SystemHealthManager running in-proc within ErrorBusSuite")
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.error("Failed to start SystemHealthManager: %s", exc)

    async def _delegate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        if self._legacy and hasattr(self._legacy, "handle_request"):
            try:
                return self._legacy.handle_request(request)  # type: ignore[attr-defined]
            except Exception as exc:  # pylint: disable=broad-except
                LOGGER.error("In-proc delegation failed: %s", exc)
        # Fallback to ZMQ REQ/REP on same machine
        try:
            sock = self._ctx.socket(zmq.REQ)
            sock.setsockopt(zmq.RCVTIMEO, 3000)
            sock.connect("tcp://localhost:7150")
            sock.send_json(request)
            reply = sock.recv_json()
            sock.close()
            return reply
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.error("ZMQ delegation failed: %s", exc)
            return {"status": "error", "message": str(exc)}

    # ------------------------------------------------------------------
    # API Routes
    # ------------------------------------------------------------------

    def _setup_routes(self):
        @self.app.get("/health")
        async def health():  # pylint: disable=unused-variable
            return self._get_health_status()

        @self.app.post("/report")
        async def report(request: Request):  # pylint: disable=unused-variable
            data = await request.json()
            if not isinstance(data, dict):
                raise HTTPException(status_code=400, detail="Payload must be JSON object")
            topic_wrapped = {"action": "publish", "data": data}
            return await self._delegate(topic_wrapped)

        @self.app.get("/recent")
        async def recent(limit: int = 100):  # pylint: disable=unused-variable
            return await self._delegate({"action": "get_recent_errors", "data": {"limit": limit}})

        @self.app.get("/agent_health")
        async def agent_health():  # pylint: disable=unused-variable
            return await self._delegate({"action": "get_agent_health"})

    # ------------------------------------------------------------------
    # Health / cleanup overrides
    # ------------------------------------------------------------------

    def _get_health_status(self):  # type: ignore[override]
        base = super()._get_health_status()
        base.update({
            "service": "ErrorBusSuite",
            "legacy_running": self._legacy is not None,
            "system_health": self._system_health is not None,
            "uptime": time.time() - getattr(self, "_startup_time", time.time()),
        })
        return base

    def cleanup(self):  # type: ignore[override]
        LOGGER.info("Shutting down ErrorBusSuite …")
        if self._legacy and hasattr(self._legacy, "cleanup"):
            try:
                self._legacy.cleanup()  # type: ignore[attr-defined]
            except Exception as exc:  # pylint: disable=broad-except
                LOGGER.warning("Error during legacy cleanup: %s", exc)
        super().cleanup()


if __name__ == "__main__":
    svc = ErrorBusSuite()
    uvicorn.run(svc.app, host="0.0.0.0", port=svc.port, log_level="info")