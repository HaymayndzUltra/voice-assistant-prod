"""Model Manager Suite FastAPI service (Port 7011)."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger("model_manager_suite")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[ModelManagerSuite] Starting up – importing legacy agents…")
    # Routers import triggers embedded agent instantiation when first used
    import phase1_implementation.consolidated_agents.model_manager_suite.routers as _  # noqa: F401
    logger.info("[ModelManagerSuite] Ready")
    yield
    logger.info("[ModelManagerSuite] Shutting down")


app = FastAPI(
    title="Model Manager Suite",
    description="Consolidated GGUF & model management service",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
from .routers import (  # noqa: E402
    gguf_manager_router,
    model_manager_router,
    predictive_loader_router,
    evaluation_framework_router,
)

for r in [
    gguf_manager_router.router,
    model_manager_router.router,
    predictive_loader_router.router,
    evaluation_framework_router.router,
]:
    app.include_router(r)


@app.get("/", response_class=PlainTextResponse)
async def root():
    return "Model Manager Suite – OK"


@app.get("/health")
async def health():
    return {"status": "ok", "service": "model_manager_suite"}


def main():
    import uvicorn

    logger.info("Launching ModelManagerSuite on 0.0.0.0:7011")
    uvicorn.run(
        "phase1_implementation.consolidated_agents.model_manager_suite.model_manager_suite:app",
        host="0.0.0.0",
        port=7011,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()