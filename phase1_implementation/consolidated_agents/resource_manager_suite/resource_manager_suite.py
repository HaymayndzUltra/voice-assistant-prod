
from __future__ import annotations

# ResourceManagerSuite Consolidated Service

import sys
import os
import logging
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
import uvicorn
import zmq

# Ensure project root in path for legacy agent imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from common.core.base_agent import BaseAgent
except ImportError:
    # Fallback minimal BaseAgent if common.core not yet available during early unit-testing
    class BaseAgent:  # type: ignore
        def __init__(self, name: str, port: int, **_: Any):
            self.name = name
            self.port = port
            self.health_check_port = port + 100
            self.context: zmq.Context = zmq.Context()
            self.running = True
            self.start_time = time.time()
        def _get_health_status(self) -> Dict[str, Any]:
            return {
                "status": "ok",
                "uptime": time.time() - self.start_time,
            }
        def cleanup(self):
            self.running = False
            if hasattr(self, "context"):
                self.context.term()

# Safe imports of legacy agents (facade pattern)
LEGACY_IMPORTS = {
    "ResourceManager": "pc2_code.agents.resource_manager.ResourceManager",
    "TaskSchedulerAgent": "pc2_code.agents.task_scheduler.TaskSchedulerAgent",
    "AsyncProcessor": "pc2_code.agents.async_processor.AsyncProcessor",
    "VramOptimizerAgent": "main_pc_code.agents.vram_optimizer_agent.VramOptimizerAgent",
}

_import_cache: Dict[str, Optional[type]] = {}

def _safe_import(path: str) -> Optional[type]:
    if path in _import_cache:
        return _import_cache[path]
    module_path, cls_name = path.rsplit(".", 1)
    try:
        module = __import__(module_path, fromlist=[cls_name])
        cls = getattr(module, cls_name)
        _import_cache[path] = cls
        return cls
    except Exception as exc:  # pylint: disable=broad-except
        logging.getLogger("ResourceManagerSuite").warning("Could not import %s: %s", path, exc)
        _import_cache[path] = None
        return None

# ---------------------------------------------------------------------------
# Consolidated Service Implementation
# ---------------------------------------------------------------------------

LOGGER = logging.getLogger("ResourceManagerSuite")
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "phase1_implementation/logs/resource_manager_suite.log"),
    ],
)


class ResourceManagerSuite(BaseAgent):
    """Unified Resource-management & Scheduling service (port 7001).

    Facade over:
      * ResourceManager (resource accounting / NVML / psutil)
      * TaskSchedulerAgent (priority queue, async delegation)
      * AsyncProcessor (async workers)
      * VramOptimizerAgent (GPU-specific optimisation)
    """

    def __init__(self, *, port: int = 7001, health_check_port: int = 7101):
        super().__init__(name="ResourceManagerSuite", port=port, health_check_port=health_check_port)

        # Thread-pool for background tasks
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="RMSuite")
        self._agents: Dict[str, BaseAgent] = {}
        self._launch_legacy_agents()

        # ZMQ context for delegations not in-proc (fallback)
        self._zmq_ctx = zmq.Context()

        # FastAPI app for consolidated API
        self.app = FastAPI(
            title="ResourceManagerSuite",
            description="Phase-1 consolidated resource management & scheduling service",
            version="1.0.0",
        )
        self._setup_routes()

        self._startup_time = time.time()
        LOGGER.info("ResourceManagerSuite initialised on port %s", self.port)

    # ---------------------------------------------------------------------
    # Legacy agent bootstrapping
    # ---------------------------------------------------------------------

    def _launch_legacy_agents(self) -> None:  # noqa: C901  (complexity acceptable)
        """Instantiate legacy agent classes inside threads using facade pattern."""
        mapping = {
            "resource_manager": ("ResourceManager", 7113),
            "task_scheduler": ("TaskSchedulerAgent", 7115),
            "async_processor": ("AsyncProcessor", 7101),
            "vram_optimizer": ("VramOptimizerAgent", None),  # port determined inside
        }
        for key, (cls_name, legacy_port) in mapping.items():
            cls = _safe_import(LEGACY_IMPORTS[cls_name]) if cls_name in LEGACY_IMPORTS else None
            if cls is None:
                LOGGER.warning("%s class unavailable – running in unified-only mode", cls_name)
                continue
            try:
                # Instantiate with explicit port when possible to avoid conflicts.
                kwargs: Dict[str, Any] = {}
                if legacy_port is not None:
                    kwargs["port"] = legacy_port
                instance = cls(**kwargs)  # type: ignore[arg-type]
                thread = threading.Thread(target=instance.run, daemon=True, name=f"legacy_{key}")
                thread.start()
                self._agents[key] = instance  # keep ref for delegation
                LOGGER.info("Started legacy agent %s in-proc thread", cls_name)
            except Exception as exc:  # pylint: disable=broad-except
                LOGGER.error("Failed to start legacy %s: %s", cls_name, exc)

    # ---------------------------------------------------------------------
    # API Routes
    # ---------------------------------------------------------------------

    def _setup_routes(self) -> None:
        @self.app.get("/health")
        async def health() -> Dict[str, Any]:  # pylint: disable=unused-variable
            return self._get_health_status()

        # ------------- Resource endpoints -------------
        @self.app.post("/allocate")
        async def allocate(request: Request):  # type: ignore[no-return]
            data = await request.json()
            return await self._delegate("resource_manager", {"action": "allocate_resources", **data})

        @self.app.post("/release")
        async def release(request: Request):  # type: ignore[no-return]
            data = await request.json()
            return await self._delegate("resource_manager", {"action": "release_resources", **data})

        @self.app.get("/status")
        async def status():  # type: ignore[no-return]
            return await self._delegate("resource_manager", {"action": "get_status"})

        # ------------- Task scheduling endpoints -------------
        @self.app.post("/schedule")
        async def schedule(request: Request):  # type: ignore[no-return]
            data = await request.json()
            return await self._delegate("task_scheduler", {"action": "schedule_task", **data})

        # ------------- Async processing diagnostics -------------
        @self.app.get("/queue_stats")
        async def queue_stats():  # type: ignore[no-return]
            return await self._delegate("async_processor", {"action": "health_check"})

    # ---------------------------------------------------------------------
    # Delegation helpers
    # ---------------------------------------------------------------------

    async def _delegate(self, key: str, payload: Dict[str, Any], timeout_ms: int = 5000) -> Dict[str, Any]:
        """Delegate the request to an in-proc legacy agent if available, else via ZMQ."""
        agent = self._agents.get(key)
        if agent is not None and hasattr(agent, "handle_request"):
            try:
                return agent.handle_request(payload)  # type: ignore[attr-defined]
            except Exception as exc:  # pylint: disable=broad-except
                LOGGER.error("In-proc delegation to %s failed: %s", key, exc)

        # Fallback ZMQ delegation (legacy agent might be running as separate proc)
        target_port = {
            "resource_manager": 7113,
            "task_scheduler": 7115,
            "async_processor": 7101,
        }.get(key)
        if target_port is None:
            return {"status": "error", "message": f"Unknown delegation target: {key}"}
        try:
            sock = self._zmq_ctx.socket(zmq.REQ)
            sock.setsockopt(zmq.RCVTIMEO, timeout_ms)
            sock.connect(f"tcp://localhost:{target_port}")
            sock.send_json(payload)
            reply = sock.recv_json()
            sock.close()
            return reply
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.error("ZMQ delegation to %s@%s failed: %s", key, target_port, exc)
            return {"status": "error", "message": str(exc)}

    # ---------------------------------------------------------------------
    # Health / cleanup
    # ---------------------------------------------------------------------

    def _get_health_status(self):  # type: ignore[override]
        base = super()._get_health_status()
        base.update({
            "service": "ResourceManagerSuite",
            "legacy_agents": {k: v.__class__.__name__ for k, v in self._agents.items()},
            "uptime": time.time() - self._startup_time,
        })
        return base

    def cleanup(self):  # type: ignore[override]
        LOGGER.info("Cleaning up ResourceManagerSuite …")
        for agent in self._agents.values():
            try:
                if hasattr(agent, "cleanup"):
                    agent.cleanup()  # type: ignore[attr-defined]
            except Exception as exc:  # pylint: disable=broad-except
                LOGGER.warning("Error during legacy agent cleanup: %s", exc)
        super().cleanup()


# ---------------------------------------------------------------------------
# Stand-alone execution helper for local development
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    service = ResourceManagerSuite()
    uvicorn.run(service.app, host="0.0.0.0", port=service.port, log_level="info")