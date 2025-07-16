"""Router exposing GGUFModelManager operations.

Endpoints (Phase-1):
GET  /models                  – list available models
GET  /models/{model_id}       – model info / status
POST /models/{model_id}/load  – load model into memory
POST /models/{model_id}/unload– unload model
GET  /models/{model_id}/stats – alias to status
POST /gguf/raw                – raw passthrough to handle_request
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Body, Path

try:
    from main_pc_code.agents.gguf_model_manager import GGUFModelManager  # noqa: E402
except ModuleNotFoundError:
    from importlib import import_module

    GGUFModelManager = import_module("main_pc_code.agents.gguf_model_manager").GGUFModelManager  # type: ignore

logger = logging.getLogger("model_manager_suite.gguf_router")

_gm: Optional[GGUFModelManager] = None

def get_gm() -> GGUFModelManager:
    global _gm
    if _gm is None:
        logger.info("[ModelManagerSuite] Starting GGUFModelManager instance")
        _gm = GGUFModelManager(port=0)
    return _gm

router = APIRouter(prefix="", tags=["GGUFModelManager"])

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _status(model_id: str) -> Dict[str, Any]:
    gm = get_gm()
    return gm.get_model_status(model_id)

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/models")
async def list_models():
    return {"status": "success", "models": get_gm().list_models()}


@router.get("/models/{model_id}")
async def model_info(model_id: str = Path(...)):
    return _status(model_id)


@router.get("/models/{model_id}/stats")
async def model_stats(model_id: str = Path(...)):
    return _status(model_id)


@router.post("/models/{model_id}/load")
async def load_model(model_id: str = Path(...)):
    if not get_gm().load_model(model_id):
        raise HTTPException(status_code=500, detail="Failed to load model")
    return {"status": "success"}


@router.post("/models/{model_id}/unload")
async def unload_model(model_id: str = Path(...)):
    if not get_gm().unload_model(model_id):
        raise HTTPException(status_code=500, detail="Failed to unload model")
    return {"status": "success"}


@router.post("/gguf/raw")
async def raw_forward(body: Dict[str, Any] = Body(...)):
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object expected")
    gm = get_gm()
    return gm.handle_request(body)