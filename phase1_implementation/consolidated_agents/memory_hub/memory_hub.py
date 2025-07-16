"""Memory Hub FastAPI service (Phase 1).

This file boots a FastAPI application that will expose a REST façade for
all 12 legacy memory-related agents, running on **port 7010** (PC2).

During Phase 1 we keep the surface minimal (root, health, metrics)
while we incrementally attach each legacy agent’s router or background
component.  All heavy lifting still resides inside the original agent
modules – we simply import them to guarantee their logic is preserved.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

# Import package helper (ensures legacy modules are loaded early)
from . import import_legacy_agents

logger = logging.getLogger("memory_hub")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: D401 – FastAPI lifespan hook
    """Application start-up / shut-down hooks."""
    logger.info("[MemoryHub] Starting up – importing legacy agents…")
    import_legacy_agents()
    logger.info("[MemoryHub] Legacy agents imported – service ready")
    yield
    logger.info("[MemoryHub] Shutting down")


app = FastAPI(
    title="Memory Hub",
    description="Unified service consolidating 12 legacy memory agents (Phase 1)",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware – allow cross-service calls inside LAN
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers (legacy integration)
# ---------------------------------------------------------------------------
from .routers import memory_client_router  # noqa: E402 – import after FastAPI instance
from .routers import session_memory_router
from .routers import knowledge_base_router
from .routers import orchestrator_router
from .routers import unified_memory_reasoning_router

app.include_router(memory_client_router.router)
app.include_router(session_memory_router.router)
app.include_router(knowledge_base_router.router)
app.include_router(orchestrator_router.router)
app.include_router(unified_memory_reasoning_router.router)


# ---------------------------------------------------------------------------
# Base endpoints
# ---------------------------------------------------------------------------
@app.get("/", response_class=PlainTextResponse)
async def root() -> str:  # noqa: D401 – simple handler
    """Root endpoint – simple liveness check."""
    return "Memory Hub (Phase 1) – OK"


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Return basic health status.

    Detailed per-agent diagnostics will be attached in later milestones.
    """
    return {
        "status": "ok",
        "service": "memory_hub",
        "phase": 1,
    }


@app.get("/metrics")
async def metrics() -> Response:  # pragma: no cover – placeholder
    """Prometheus metrics placeholder."""
    # TODO: integrate prometheus_client
    return PlainTextResponse("# metrics will appear here\n", status_code=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Entrypoint helper (uvicorn)
# ---------------------------------------------------------------------------

def main() -> None:  # noqa: D401 – CLI entry
    import uvicorn

    logger.info("[MemoryHub] Launching uvicorn on 0.0.0.0:7010")
    uvicorn.run(
        "phase1_implementation.consolidated_agents.memory_hub.memory_hub:app",
        host="0.0.0.0",
        port=7010,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()