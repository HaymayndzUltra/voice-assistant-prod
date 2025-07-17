#!/usr/bin/env python3
"""ModelManagementHub – Consolidated launcher for ModelManagementSuite.

Preserves original behaviour by spawning the existing agents in-process:
  * GGUFModelManager (port 5575)
  * ModelManagerAgent (port 5570)
  * PredictiveLoader (port 5617)

Each agent keeps its own ZeroMQ sockets and background threads.  This hub only
hosts a lightweight FastAPI summary endpoint mounted at `/model_management`
inside the existing CoreOrchestrator app (port 7000) so no new public ports are
required.
"""
from __future__ import annotations

import logging
import threading
import time
import signal
import sys
from typing import List, Tuple

import uvicorn
from fastapi import FastAPI

# ---------------------------------------------------------------------------
# Import legacy agents – paths remain unchanged so their logic stays intact.
# ---------------------------------------------------------------------------
from main_pc_code.agents.gguf_model_manager import GGUFModelManager
from main_pc_code.agents.model_manager_agent import ModelManagerAgent
from main_pc_code.agents.predictive_loader import PredictiveLoader

logger = logging.getLogger("ModelManagementHub")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

# Instantiate services (they do not block on __init__).
logger.info("Instantiating GGUFModelManager …")
_gm = GGUFModelManager(port=5575)
logger.info("Instantiating ModelManagerAgent …")
_mma = ModelManagerAgent()
logger.info("Instantiating PredictiveLoader …")
_pl = PredictiveLoader()

_services: List[Tuple[str, object]] = [
    ("GGUFModelManager", _gm),
    ("ModelManagerAgent", _mma),
    ("PredictiveLoader", _pl),
]

# ---------------------------------------------------------------------------
# Start each agent's .run() loop in a daemon thread (if present).
# ---------------------------------------------------------------------------
threads: List[threading.Thread] = []
for name, svc in _services:
    if hasattr(svc, "run"):
        t = threading.Thread(target=svc.run, name=f"{name}_run", daemon=True)
        t.start()
        threads.append(t)
        logger.info("Started %s run loop in background thread", name)

# ---------------------------------------------------------------------------
# Provide a small FastAPI app summarising status on port 6570 (health).
# ---------------------------------------------------------------------------
app = FastAPI(title="ModelManagementHub", version="1.0.0")


@app.get("/health")
async def health() -> dict:  # noqa: D401
    """Aggregate health of underlying model-management agents."""
    status = {}
    for name, svc in _services:
        if hasattr(svc, "_get_health_status"):
            try:
                status[name] = svc._get_health_status()  # type: ignore
            except Exception as exc:  # pylint: disable=broad-except
                status[name] = {"status": "error", "error": str(exc)}
    return {"status": "ok", "services": status}


# ---------------------------------------------------------------------------
# Run the FastAPI app on 0.0.0.0:6570 to match previous health port.
# ---------------------------------------------------------------------------

def _serve_api() -> None:  # noqa: D401
    uvicorn.run(app, host="0.0.0.0", port=6570, log_level="info")

_api_thread = threading.Thread(target=_serve_api, name="ModelManagementAPI", daemon=True)
_api_thread.start()
threads.append(_api_thread)

# ---------------------------------------------------------------------------
# Graceful shutdown on SIGINT/SIGTERM.
# ---------------------------------------------------------------------------

def _shutdown(*_):  # noqa: D401
    logger.warning("ModelManagementHub shutting down …")
    for _, svc in _services:
        try:
            if hasattr(svc, "cleanup"):
                svc.cleanup()  # type: ignore[attr-defined]
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Error during cleanup: %s", exc)
    time.sleep(2)
    sys.exit(0)

for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, _shutdown)

logger.info("ModelManagementHub fully operational. Threads: %s", len(threads))

# Keep main thread alive.
while True:
    time.sleep(60)