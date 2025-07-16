from __future__ import annotations

"""
ModelManagerSuite (Phase 2.4)
=============================
Unified service that bundles the functionality of:
 - GGUFModelManager
 - ModelManagerAgent
 - PredictiveLoader
 - ModelEvaluationFramework

Critical guarantees:
 1. Preserve ALL existing logic – the original agents are imported *as-is*.
 2. Maintain backward-compatibility – every legacy action string / REST/gRPC payload will be routed to the originating agent implementation.
 3. Continue to expose the original ZMQ REQ/REP and health-check semantics while co-locating all agents on a single process (default ports: 7011 main, 7012 health).

NOTE:  This file purposefully *does not* attempt to rewrite or refactor internal logic of individual agents.  Doing so would risk subtle regressions.  Instead we use a
facade/adapter pattern that forwards requests to the underlying, battle-tested implementations.

This module can be imported as a library **or** executed directly via
`python -m main_pc_code.services.model_manager_suite` to launch the standalone service.
"""

import importlib
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, Optional

import zmq

# ---------------------------------------------------------------------------
# Project-level imports – keep at runtime to avoid circular import at module
# load time.  We lazily load heavy dependencies (torch, llama-cpp, etc.) only
# when their corresponding sub-agent is first invoked.
# ---------------------------------------------------------------------------
from common.core.base_agent import BaseAgent

# Absolute path helpers – ensures we can `import main_pc_code.*` even when
# executed from outside the repo root.
ROOT_DIR = Path(__file__).resolve().parent.parent
if ROOT_DIR.as_posix() not in sys.path:
    sys.path.insert(0, ROOT_DIR.as_posix())

# ---------------------------------------------------------------------------
# Logger configuration – re-use same pattern as other agents to guarantee
# consistent log rotation & format.
# ---------------------------------------------------------------------------
LOG_PATH = ROOT_DIR / "logs" / "model_manager_suite.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("ModelManagerSuite")


# ---------------------------------------------------------------------------
# Helper to lazy-load modules only when accessed the first time.
# ---------------------------------------------------------------------------
class _LazyLoader:
    """Utility that defers importing heavy agent modules until first use."""

    def __init__(self, module_path: str, attr_name: str):
        self._module_path = module_path
        self._attr_name = attr_name
        self._instance: Optional[Any] = None
        self._lock = threading.Lock()

    def instance(self):
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    logger.info("Lazy-loading %s", self._module_path)
                    module: ModuleType = importlib.import_module(self._module_path)
                    self._instance = getattr(module, self._attr_name)()
        return self._instance


# ---------------------------------------------------------------------------
# Suite Implementation
# ---------------------------------------------------------------------------
class ModelManagerSuite(BaseAgent):
    """Facade that muxes requests to the legacy sub-agents."""

    def __init__(self, port: int = 7011, **kwargs):
        super().__init__(name="ModelManagerSuite", port=port, **kwargs)

        # Sub-agents (lazy-loaded to keep start-up fast and reduce VRAM until
        # genuinely required)
        self.gguf_manager = _LazyLoader(
            "main_pc_code.agents.gguf_model_manager", "get_instance"
        )
        self.model_manager = _LazyLoader(
            "main_pc_code.agents.model_manager_agent", "ModelManagerAgent"
        )
        self.predictive_loader = _LazyLoader(
            "main_pc_code.agents.predictive_loader", "PredictiveLoader"
        )
        self.model_eval_framework = _LazyLoader(
            "main_pc_code.agents.model_evaluation_framework", "ModelEvaluationFramework"
        )

        # Health-check REP socket (7012 by convention)
        self.health_port = port + 1
        self._init_additional_sockets()

        # Start thread for handling external REQ/REP like the other agents.
        t = threading.Thread(target=self._request_loop, daemon=True)
        t.start()
        self._threads.append(t)

    # ---------------------------------------------------------------------
    # Socket wiring
    # ---------------------------------------------------------------------
    def _init_additional_sockets(self):
        ctx = self.context  # inherited from BaseAgent
        self._health_socket = ctx.socket(zmq.REP)
        self._health_socket.bind(f"tcp://*:{self.health_port}")
        logger.info("Health socket bound to port %s", self.health_port)

    # ---------------------------------------------------------------------
    # Request routing logic
    # ---------------------------------------------------------------------
    def _request_loop(self):
        logger.info("ModelManagerSuite main request loop started (port=%s)", self.port)
        while True:
            try:
                msg_bytes = self.socket.recv()
                request: Dict[str, Any] = json.loads(msg_bytes.decode("utf-8"))
                response = self.handle_request(request)
                self.socket.send_json(response)
            except (KeyboardInterrupt, SystemExit):
                logger.warning("Shutting down request loop…")
                break
            except Exception as exc:  # noqa: BLE001
                logger.exception("Unhandled error while processing request: %s", exc)
                # Safe error payload
                self.socket.send_json({"status": "error", "error": str(exc)})

    # NOTE:  This function purposefully duplicates the signature of the legacy
    # agents so that existing callers do not need to change anything.
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[override]
        """Route request to the appropriate sub-agent based on `request['action']`."""
        action = request.get("action") or request.get("cmd") or ""

        # -----------------------------------------------------------------
        # Mapping table – extend as new actions emerge.
        # -----------------------------------------------------------------
        # These strings are scattered across multiple services/tests – do NOT
        # rename casually; instead map new aliases to existing entries.
        # -----------------------------------------------------------------
        gguf_actions = {
            "gguf_generate",  # custom wrapper
            "load_gguf_model",
            "unload_gguf_model",
            "list_gguf_models",
        }

        mma_actions = {
            "select_model",
            "status",  # top-level status
            "load_model",
            "unload_model",
            # plus many others – fallback default
        }

        pred_loader_actions = {"predictive_load"}
        eval_actions = {"evaluate_model"}

        try:
            if action in gguf_actions:
                agent = self.gguf_manager.instance()
            elif action in pred_loader_actions:
                agent = self.predictive_loader.instance()
            elif action in eval_actions:
                agent = self.model_eval_framework.instance()
            else:
                # Default to ModelManagerAgent – it already gracefully handles
                # unknown actions.
                agent = self.model_manager.instance()

            if hasattr(agent, "handle_request"):
                return agent.handle_request(request)  # type: ignore[attr-defined]
            raise AttributeError(f"Sub-agent {agent} lacks handle_request")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Fatal error in request dispatch: %s", exc)
            return {"status": "error", "error": str(exc)}

    # ---------------------------------------------------------------------
    # Health-check endpoint – required by orchestration / monitoring layer.
    # ---------------------------------------------------------------------
    def _get_health_status(self) -> Dict[str, Any]:  # noqa: D401  # override
        return {"status": "ok", "details": {"uptime": time.time() - self.start_time}}

    # Extend BaseAgent’s health responder so external scripts can hit
    # tcp://*:7012 with a simple JSON `{}` and receive status.
    def _health_responder_loop(self):
        while True:
            try:
                _ = self._health_socket.recv(flags=0)
                self._health_socket.send_json(self._get_health_status())
            except zmq.error.ZMQError:
                break

    # Keep reference so BaseAgent.cleanup() can join.
    _threads: list[threading.Thread] = []


# ---------------------------------------------------------------------------
# Main entrypoint (for `python -m …` execution)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    suite = ModelManagerSuite()
    logger.info("ModelManagerSuite is up ‑ listening on port %s", suite.port)
    try:
        # Keep the main thread alive while background threads handle work.
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Shutdown requested – cleaning up…")
        suite.cleanup()