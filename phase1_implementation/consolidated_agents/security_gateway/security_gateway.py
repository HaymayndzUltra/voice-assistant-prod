
from __future__ import annotations

"""SecurityGateway consolidated service (Phase-1).

Combines AuthenticationAgent and AgentTrustScorer into a single FastAPI
application exposed on port 7005.

Features preserved:
  * JWT authentication & session handling (delegated to AuthenticationAgent)
  * Trust-score querying / performance logging (delegated to AgentTrustScorer)
  * Centralised health endpoint
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

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from common.core.base_agent import BaseAgent
except ImportError:
    class BaseAgent:  # Fallback minimal class
        def __init__(self, name: str, port: int, **_):
            self.name, self.port = name, port
            self.health_check_port = port + 100
            self.context = zmq.Context()
            self.start_time = time.time()
        def _get_health_status(self):
            return {"status": "ok", "uptime": time.time() - self.start_time}
        def cleanup(self):
            self.context.term()

# Safe imports of legacy agents
LEGACY = {}
for path in (
    ("auth", "pc2_code.agents.ForPC2.AuthenticationAgent.AuthenticationAgent"),
    ("trust", "pc2_code.agents.AgentTrustScorer.AgentTrustScorer"),
):
    key, dotted = path
    try:
        module_name, cls_name = dotted.rsplit(".", 1)
        module = __import__(module_name, fromlist=[cls_name])
        LEGACY[key] = getattr(module, cls_name)
    except Exception as exc:  # pylint: disable=broad-except
        logging.getLogger("SecurityGateway").warning("Could not import %s: %s", dotted, exc)
        LEGACY[key] = None  # type: ignore

LOGGER = logging.getLogger("SecurityGateway")
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "phase1_implementation/logs/security_gateway.log"),
    ],
)


class SecurityGateway(BaseAgent):
    """Unified Security gateway (port 7005)"""

    def __init__(self, *, port: int = 7005, health_check_port: int = 7105):
        super().__init__(name="SecurityGateway", port=port, health_check_port=health_check_port)

        self._agents: Dict[str, Any] = {}
        self._start_legacy()
        self._ctx = zmq.Context()

        self.app = FastAPI(title="SecurityGateway", description="Authentication & Trust facade", version="1.0.0")
        self._setup_routes()
        self._startup_time = time.time()
        LOGGER.info("SecurityGateway ready on %s", self.port)

    # ------------------------------------------------------------------
    # Legacy startup helpers
    # ------------------------------------------------------------------

    def _start_legacy(self):
        mapping = {
            "auth": (LEGACY.get("auth"), 7116),
            "trust": (LEGACY.get("trust"), 7122),
        }
        for key, (cls, port) in mapping.items():
            if cls is None:
                LOGGER.warning("Legacy %s unavailable", key)
                continue
            try:
                instance = cls(port=port)  # type: ignore[call-arg]
                threading.Thread(target=instance.run, daemon=True, name=f"legacy_{key}").start()
                self._agents[key] = instance
                LOGGER.info("Started legacy %s agent", key)
            except Exception as exc:  # pylint: disable=broad-except
                LOGGER.error("Failed to start legacy %s: %s", key, exc)

    # ------------------------------------------------------------------
    # Delegation helper
    # ------------------------------------------------------------------

    async def _delegate(self, key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        agent = self._agents.get(key)
        if agent and hasattr(agent, "handle_request"):
            try:
                return agent.handle_request(payload)  # type: ignore[attr-defined]
            except Exception as exc:  # pylint: disable=broad-except
                LOGGER.error("In-proc delegation error: %s", exc)
        # Fallback ZMQ
        port_map = {"auth": 7116, "trust": 7122}
        port = port_map.get(key)
        if port is None:
            return {"status": "error", "message": "unknown delegation target"}
        try:
            sock = self._ctx.socket(zmq.REQ)
            sock.setsockopt(zmq.RCVTIMEO, 3000)
            sock.connect(f"tcp://localhost:{port}")
            sock.send_json(payload)
            reply = sock.recv_json()
            sock.close()
            return reply
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.error("ZMQ delegation failure: %s", exc)
            return {"status": "error", "message": str(exc)}

    # ------------------------------------------------------------------
    # API Routes
    # ------------------------------------------------------------------

    def _setup_routes(self):
        @self.app.get("/health")
        async def health():  # pylint: disable=unused-variable
            return self._get_health_status()

        # ---------- Authentication ----------
        @self.app.post("/register")
        async def register(request: Request):  # pylint: disable=unused-variable
            data = await request.json()
            return await self._delegate("auth", {"action": "register", **data})

        @self.app.post("/login")
        async def login(request: Request):  # pylint: disable=unused-variable
            data = await request.json()
            return await self._delegate("auth", {"action": "login", **data})

        @self.app.post("/validate")
        async def validate(request: Request):  # pylint: disable=unused-variable
            data = await request.json()
            return await self._delegate("auth", {"action": "validate_token", **data})

        # ---------- Trust scoring ----------
        @self.app.get("/trust/{model_id}")
        async def trust_score(model_id: str):  # pylint: disable=unused-variable
            return await self._delegate("trust", {"action": "get_trust_score", "model_id": model_id})

    # ------------------------------------------------------------------
    # Health / cleanup
    # ------------------------------------------------------------------

    def _get_health_status(self):  # type: ignore[override]
        base = super()._get_health_status()
        base.update({
            "service": "SecurityGateway",
            "legacy_agents": list(self._agents.keys()),
            "uptime": time.time() - getattr(self, "_startup_time", time.time()),
        })
        return base

    def cleanup(self):  # type: ignore[override]
        for agent in self._agents.values():
            try:
                if hasattr(agent, "cleanup"):
                    agent.cleanup()  # type: ignore[attr-defined]
            except Exception as exc:  # pylint: disable=broad-except
                LOGGER.warning("Failed cleaning legacy: %s", exc)
        super().cleanup()


if __name__ == "__main__":
    gw = SecurityGateway()
    uvicorn.run(gw.app, host="0.0.0.0", port=gw.port, log_level="info")