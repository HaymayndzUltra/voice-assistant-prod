"""
ModelManagerSuite
-----------------
Unified service that consolidates the following legacy agents into a single
process on MainPC (RTX 4090):

    • GGUFModelManager
    • ModelManagerAgent
    • PredictiveLoader
    • ModelEvaluationFramework

The goal is to preserve ALL existing logic and endpoints of the individual
agents while providing a consolidated health-check interface on the new
suite port (default 7011, health 7012).  The suite simply instantiates each
legacy agent in-process and lets them continue to bind to their historical
ports.  This ensures backwards compatibility with zero behaviour change for
callers already relying on those ports / protocols.

NOTE
====
1. No modifications are made to the internal implementations of the legacy
   agents – they are imported and executed exactly as before.
2. Each agent is executed in its own daemon thread using its native `.run()`
   entry point (or an equivalent if provided).  All exceptions are captured
   and surfaced through the suite health endpoint.
3. The suite exposes a lightweight REP ZMQ socket for health checks.  This
   mirrors the pattern used by other BaseAgent-derived services to integrate
   seamlessly with the existing monitoring stack.
4. Further orchestration / proxying of calls between agents can be layered
   on top of this trampoline class in future phases without breaking the
   public interface established here.
"""

from __future__ import annotations

import threading
import time
import traceback
from typing import Dict, List

import zmq

# Shared utilities
from common.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config

# Legacy agents (imported WITHOUT modification)
from main_pc_code.agents.gguf_model_manager import get_instance as get_gguf_manager
from main_pc_code.agents.model_manager_agent import ModelManagerAgent
from main_pc_code.agents.predictive_loader import PredictiveLoader
from main_pc_code.agents.model_evaluation_framework import ModelEvaluationFramework

# ---------------------------------------------------------------------------
# Suite implementation
# ---------------------------------------------------------------------------


class _AgentWrapper:
    """Light utility to standardise background-thread execution of an agent."""

    def __init__(self, agent: BaseAgent, name: str):
        self.agent = agent
        self.name = name
        self.thread: threading.Thread | None = None
        self.last_error: str | None = None

    def start(self):
        """Start the agent’s main loop in a daemon thread."""

        def _run_agent():
            try:
                # Some legacy agents expose `.run()`, others rely on BaseAgent
                # event loops started in `__init__`.  Execute `.run()` when
                # available to respect their preferred lifecycle.
                run_callable = getattr(self.agent, "run", None)
                if callable(run_callable):
                    run_callable()  # Blocking call; will exit on KeyboardInterrupt/stop
                else:
                    # If no explicit run method, just idle while the internal
                    # BaseAgent background threads perform their duties.
                    while getattr(self.agent, "running", True):
                        time.sleep(1)
            except Exception as exc:  # pylint: disable=broad-except
                # Capture the exception so the suite can surface it.
                self.last_error = f"{exc}\n{traceback.format_exc()}"
                # Ensure that the agent is flagged as not running.
                if hasattr(self.agent, "running"):
                    try:
                        self.agent.running = False  # type: ignore[attr-defined]
                    except Exception:  # pragma: no cover
                        pass

        self.thread = threading.Thread(target=_run_agent, name=self.name, daemon=True)
        self.thread.start()

    def health(self) -> Dict[str, str]:
        """Return minimal health snapshot for this wrapped agent."""
        status = "ok"
        if self.last_error is not None:
            status = "error"
        elif hasattr(self.agent, "_get_health_status"):
            try:
                status_info = self.agent._get_health_status()  # type: ignore[attr-defined]
                # normalise to status field used by BaseAgent pattern
                status = status_info.get("status", status_info.get("state", "ok"))
            except Exception:  # pragma: no cover
                status = "error"
        return {
            "name": self.name,
            "status": status,
            "last_error": self.last_error,
        }


class ModelManagerSuite(BaseAgent):
    """Main consolidation service for model management-related agents."""

    DEFAULT_PORT = 7011
    DEFAULT_HEALTH_PORT = 7012

    def __init__(self, *, port: int | None = None, health_port: int | None = None):
        self.config = load_config()
        self.port = port or int(self.config.get("model_manager_suite_port", self.DEFAULT_PORT))
        self.health_port = health_port or self.port + 1  # override via arg if provided
        super().__init__(name="ModelManagerSuite", port=self.port, health_check_port=self.health_port)

        # ------------------------------------------------------------------
        # Initialise legacy agents – order DOES matter where dependencies
        # exist.  GGUF manager is lightweight and stateless, spawn first.
        # ------------------------------------------------------------------
        self._agents: List[_AgentWrapper] = []

        self._instantiate_agents()
        self._start_agents()

    # ------------------------------------------------------------------
    # Agent initialisation helpers
    # ------------------------------------------------------------------

    def _instantiate_agents(self):
        # GGUFModelManager uses a factory returning a singleton instance.
        gguf_manager = get_gguf_manager()
        self._agents.append(_AgentWrapper(gguf_manager, "GGUFModelManager"))

        # ModelManagerAgent (primary orchestrator)
        mma = ModelManagerAgent()
        self._agents.append(_AgentWrapper(mma, "ModelManagerAgent"))

        # PredictiveLoader – determine if it needs custom ports from config
        predictive_loader = PredictiveLoader()
        self._agents.append(_AgentWrapper(predictive_loader, "PredictiveLoader"))

        # ModelEvaluationFramework
        mef = ModelEvaluationFramework()
        self._agents.append(_AgentWrapper(mef, "ModelEvaluationFramework"))

    def _start_agents(self):
        for wrapper in self._agents:
            wrapper.start()
            self.logger.info("Started child agent: %s", wrapper.name)

    # ------------------------------------------------------------------
    # Health / status aggregation
    # ------------------------------------------------------------------

    def _aggregate_child_health(self) -> List[Dict[str, str]]:
        return [wrapper.health() for wrapper in self._agents]

    def _get_health_status(self):  # overrides BaseAgent helper
        child_health = self._aggregate_child_health()
        overall_status = "ok" if all(ch["status"] == "ok" for ch in child_health) else "degraded"
        return {
            "status": overall_status,
            "child_components": child_health,
            "uptime_sec": int(time.time() - self.start_time) if hasattr(self, "start_time") else 0,
        }

    # ------------------------------------------------------------------
    # Cleanup / graceful shutdown
    # ------------------------------------------------------------------

    def cleanup(self):
        self.logger.info("ModelManagerSuite initiating cleanup…")
        for wrapper in self._agents:
            try:
                if hasattr(wrapper.agent, "cleanup"):
                    wrapper.agent.cleanup()
            except Exception:  # pragma: no cover
                self.logger.exception("Error during cleanup of %s", wrapper.name)
        super().cleanup()
        self.logger.info("ModelManagerSuite cleanup complete.")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def _main():  # pragma: no cover
    suite = None
    try:
        suite = ModelManagerSuite()
        # The suite itself does not expose additional functionality beyond
        # health checks (REP socket handled by BaseAgent).  Just idle until
        # interrupted.
        while getattr(suite, "running", True):
            time.sleep(1)
    except KeyboardInterrupt:
        print("[ModelManagerSuite] Shutdown requested by user…")
    except Exception as exc:  # pylint: disable=broad-except
        traceback.print_exc()
        print(f"[ModelManagerSuite] Fatal error: {exc}")
    finally:
        if suite is not None:
            suite.cleanup()


if __name__ == "__main__":
    _main()