#!/usr/bin/env python3
"""
SystemCoreHub - Phase 1 consolidated **SystemCore** group.

This launcher starts the following previously-independent services **inside the same
Python process** and preserves their original HTTP / ZMQ ports so that no
external clients need to change configuration:

* CoreOrchestrator  → port 7000 / 8000
* SecurityGateway   → port 7005 / 8005
* ObservabilityHub  → port 9000 / 9100
* ResourceManagerSuite → port 9001 / 9101
* ErrorBusSuite     → port 9002 / 9102

Each service keeps its own FastAPI application.  `SystemCoreHub` simply runs a
very small FastAPI "summary" app and spawns *Uvicorn* servers for every
sub-application in background threads.  This avoids route/port collisions while
still giving operators a single deployment artefact.

Logic/behaviour of every sub-service remains 100 % intact because we import the
existing classes without modification.
"""
from __future__ import annotations

import threading
import time
import logging
import signal
import sys
from typing import List, Tuple

import uvicorn
from fastapi import FastAPI

# ---------------------------------------------------------------------------
# Import consolidated sub-services (existing code) – paths are relative to the
# monorepo root so they work both when executed via `python -m` or as script.
# ---------------------------------------------------------------------------
from phase1_implementation.consolidated_agents.core_orchestrator.core_orchestrator import (
    CoreOrchestrator,
)
from phase1_implementation.consolidated_agents.security_gateway.security_gateway import (
    SecurityGateway,
)
from phase1_implementation.consolidated_agents.observability_hub.observability_hub import (
    ObservabilityHub,
)
from phase1_implementation.consolidated_agents.resource_manager_suite.resource_manager_suite import (
    ResourceManagerSuite,
)
from phase1_implementation.consolidated_agents.error_bus.error_bus_suite import (
    ErrorBusSuite,
)

logger = logging.getLogger("SystemCoreHub")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

# ---------------------------------------------------------------------------
# Instantiate sub-services (they do *not* start their own uvicorn servers yet).
# We pass the original port numbers so that downstream agents continue to work.
# ---------------------------------------------------------------------------
core = CoreOrchestrator(port=7000, health_check_port=8000)
security = SecurityGateway(port=7005, health_check_port=8005)
observe = ObservabilityHub(port=9000)
resources = ResourceManagerSuite(port=9001, health_check_port=9101)
errors = ErrorBusSuite(port=9002, health_check_port=9102)

_subapps: List[Tuple[str, FastAPI, int]] = [
    ("CoreOrchestrator", core.app, 7000),
    ("SecurityGateway", security.app, 7005),
    ("ObservabilityHub", observe.app, 9000),
    ("ResourceManagerSuite", resources.app, 9001),
    ("ErrorBusSuite", errors.app, 9002),
]

# ---------------------------------------------------------------------------
# Small summary API served on **/system_core** path of CoreOrchestrator’s app
# so that we don’t introduce yet another port.  We mount directly on the
# existing 7000 server which is already started below.
# ---------------------------------------------------------------------------
summary_app = FastAPI(title="SystemCoreHub", version="1.0.0", description="Unified SystemCore summary API")


@summary_app.get("/health")
async def health():  # pylint: disable=unused-variable
    """Aggregate health-checks from all sub-services."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "CoreOrchestrator": core._get_health_status(),  # type: ignore
            "SecurityGateway": security._get_health_status(),  # type: ignore
            "ObservabilityHub": observe._get_health_status(),  # type: ignore
            "ResourceManagerSuite": resources._get_health_status(),  # type: ignore
            "ErrorBusSuite": errors._get_health_status(),  # type: ignore
        },
    }

# Mount summary under `/system_core` on CoreOrchestrator so external callers can
# discover consolidated health without new port exposure.
core.app.mount("/system_core", summary_app)


# ---------------------------------------------------------------------------
# Helper: run uvicorn inside a daemon thread so that all sub-apps share one
# Python process but listen on their canonical ports.
# ---------------------------------------------------------------------------

def _serve(app: FastAPI, port: int):  # noqa: D401
    """Start a blocking Uvicorn server for *app* on *port*."""
    logger.info("Starting sub-service on port %s", port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def _launch_servers():
    threads: List[threading.Thread] = []
    for name, app, port in _subapps:
        t = threading.Thread(target=_serve, args=(app, port), name=f"{name}_uvicorn", daemon=True)
        t.start()
        threads.append(t)
        time.sleep(0.5)  # Stagger startup slightly
    return threads


threads_running: List[threading.Thread] = _launch_servers()


# ---------------------------------------------------------------------------
# Graceful shutdown on SIGINT/SIGTERM – delegate to sub-services‘ cleanup.
# ---------------------------------------------------------------------------

def _graceful_exit(*_):  # noqa: D401
    logger.warning("SystemCoreHub shutting down …")
    for svc in (core, security, observe, resources, errors):
        try:
            if hasattr(svc, "cleanup"):
                svc.cleanup()  # type: ignore[attr-defined]
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Error during cleanup of %s: %s", svc, exc)
    # Allow threads to terminate naturally; then exit.
    time.sleep(2)
    sys.exit(0)


for _sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(_sig, _graceful_exit)

# Block main thread forever (threads are daemonic).
logger.info("SystemCoreHub fully operational. Listening on consolidated ports.")
while True:
    time.sleep(60)