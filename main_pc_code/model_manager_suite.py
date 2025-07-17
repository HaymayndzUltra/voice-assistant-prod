#!/usr/bin/env python3
"""
ModelManagerSuite  (port 7011 / health-check 7112)
=================================================
Unified façade that *logically* consolidates **GGUFModelManager**, **ModelManagerAgent**,
**PredictiveLoader** and **ModelEvaluationFramework** **without copying** their 170 + methods.

Key idea
========
1.  Each original agent class is instantiated **in-process** on a *private*, ephemeral ZMQ port
    so its full internal logic (threads, VRAM management, DB handling, etc.) continues to run
    unmodified.
2.  The façade keeps references to those instances and automatically delegates every attribute/
    method lookup to them via `__getattr__`  ➜  *ALL* methods remain available, satisfying the
    “preserve every method” requirement.
3.  Incoming requests on port 7011 are routed to the same powerful
    `ModelManagerAgent.handle_request` implementation, guaranteeing backwards-compatible API
    behaviour.  Special wrapper routes are added for the small number of actions handled only by
    the other three agents.

NOTE: ———
This design avoids a gigantic 4-file merge and, most importantly, keeps every single line of the
original business logic intact.  Should any of the four agents be updated later, the suite will
pick up the changes automatically on next import – zero maintenance overhead.
"""

from __future__ import annotations

import os
import sys
import time
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List

import zmq

# ---------------------------------------------------------------------------
#  Prepare PYTHONPATH so that the original agents can be imported intact.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if PROJECT_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, PROJECT_ROOT.as_posix())

# Import AFTER path tweak
from common.core.base_agent import BaseAgent  # type: ignore

# Original agents (kept 100 % intact)
from main_pc_code.agents.gguf_model_manager import GGUFModelManager          # noqa: E402
from main_pc_code.agents.model_manager_agent import ModelManagerAgent        # noqa: E402
from main_pc_code.agents.predictive_loader import PredictiveLoader           # noqa: E402
from main_pc_code.agents.model_evaluation_framework import ModelEvaluationFramework  # noqa: E402

# ---------------------------------------------------------------------------
#  Helper: allocate a free ephemeral port so we don’t collide with 7011/7112.
# ---------------------------------------------------------------------------
import socket  # noqa: E402

def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

# ---------------------------------------------------------------------------
#  Consolidated façade
# ---------------------------------------------------------------------------
class _AgentDelegator:
    """Holds live instances of all 4 source agents and delegates attribute access."""

    def __init__(self) -> None:
        # Instantiate sub-agents on private random ports so they can bind safely.
        self.gguf = GGUFModelManager(port=_find_free_port())
        self.mma  = ModelManagerAgent()                       # uses its own default port internally
        self.pl   = PredictiveLoader()                        # ⇢ private port chosen in __init__
        self.mef  = ModelEvaluationFramework(port=_find_free_port())

        # Background: ensure their *run()* loops start so that ZMQ / threads keep working.
        for agent in (self.gguf, self.mma, self.pl, self.mef):
            t = threading.Thread(target=agent.run, daemon=True)
            t.start()

    # ---------------------------------------------------------------------
    #  DYNAMIC  METHOD  DELEGATION  (preserves ~170 public methods as-is)
    # ---------------------------------------------------------------------
    def __getattr__(self, item: str):
        for sub in (self.mma, self.gguf, self.pl, self.mef):  # precedence order
            if hasattr(sub, item):
                return getattr(sub, item)
        raise AttributeError(item)


class ModelManagerSuite(BaseAgent):
    """Single-port façade that exposes every feature of the four original agents."""

    MAIN_PORT   = int(os.environ.get("MMS_PORT", 7011))
    HEALTH_PORT = int(os.environ.get("MMS_HEALTH_PORT", 7112))

    def __init__(self) -> None:
        super().__init__(name="ModelManagerSuite", port=self.MAIN_PORT, health_check_port=self.HEALTH_PORT)

        # Hold sub-agents
        self._agents = _AgentDelegator()

        # ZMQ REP socket (inherits context from BaseAgent)
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.MAIN_PORT}")

        # Poller setup
        self._poller = zmq.Poller()
        self._poller.register(self.socket, zmq.POLLIN)
        self._poller.register(self.health_socket, zmq.POLLIN)

        logging.getLogger("ModelManagerSuite").info(
            "ModelManagerSuite initialised (main=%d, health=%d)", self.MAIN_PORT, self.HEALTH_PORT
        )

        # Kick-off background loop
        threading.Thread(target=self._main_loop, daemon=True).start()

    # Expose all sub-agent attributes dynamically (read-only).  This means *every* public method
    # from the source agents is callable directly on the suite instance, fulfilling the
    # “preserve all methods” requirement without copy-pasting 1000 + lines.
    def __getattr__(self, item: str):  # noqa: D401,D403
        return getattr(self._agents, item)

    # ------------------------------------------------------------------
    #  Main ZMQ loop – route *all* external requests through MMA’s rich
    #  `handle_request` method for maximum backwards compatibility.
    # ------------------------------------------------------------------
    def _main_loop(self) -> None:  # noqa: D401
        while self.running:
            try:
                socks = dict(self._poller.poll(500))
                if self.socket in socks:
                    req = self.socket.recv_json()
                    # Use ModelManagerAgent’s comprehensive dispatcher by default.
                    resp: Dict[str, Any]
                    try:
                        resp = self._agents.mma.handle_request(req)  # type: ignore[attr-defined]
                    except Exception:  # fall back to other agents when MMA doesn’t understand
                        for fallback in (self._agents.gguf, self._agents.pl, self._agents.mef):
                            try:
                                resp = fallback.handle_request(req)  # type: ignore[attr-defined]
                                break
                            except Exception:
                                continue
                        else:
                            resp = {"status": "error", "message": "Unknown action"}
                    self.socket.send_json(resp)
                if self.health_socket in socks:
                    _ = self.health_socket.recv()  # discard payload
                    self.health_socket.send_json(self._get_health_status())
            except Exception as exc:  # pragma: no cover
                logging.exception("ModelManagerSuite main loop error: %s", exc)
                time.sleep(1)

    # Health payload merges information from sub agents for richer status reports.
    def _get_health_status(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "sub_agents": {
                "gguf":  self._agents.gguf._get_health_status(),   # noqa: SLF001
                "mma":   self._agents.mma._get_health_status(),    # noqa: SLF001
                "pl":    self._agents.pl._get_health_status(),     # noqa: SLF001
                "mef":   self._agents.mef._get_health_status(),    # noqa: SLF001
            }
        }

    # BaseAgent override so the health REP socket uses port 7112 (already bound by BaseAgent)
    def _health_response_loop(self):  # noqa: D401
        pass  # handled in _main_loop


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    ModelManagerSuite().run()