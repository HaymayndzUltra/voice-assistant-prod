"""Router wrapping AgentTrustScorer.

Endpoints:
POST /trust/{model_id}/log       – log performance (success, response_time, error_message?)
GET  /trust/{model_id}           – get trust score
GET  /trust/{model_id}/history   – get performance history (limit)
POST /trust/raw                  – raw passthrough
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Body, Path, Query

try:
    from pc2_code.agents.AgentTrustScorer import AgentTrustScorer  # noqa: E402
except ModuleNotFoundError:
    from importlib import import_module

    AgentTrustScorer = import_module("pc2_code.agents.AgentTrustScorer").AgentTrustScorer  # type: ignore

logger = logging.getLogger("memory_hub.trust_scorer_router")

_ts: Optional[AgentTrustScorer] = None

def get_ts() -> AgentTrustScorer:
    global _ts
    if _ts is None:
        logger.info("[MemoryHub] Starting AgentTrustScorer instance")
        _ts = AgentTrustScorer(port=0)
    return _ts


def _process(payload: Dict[str, Any]) -> Dict[str, Any]:
    return get_ts().handle_request(payload)

router = APIRouter(prefix="", tags=["AgentTrustScorer"])

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/trust/{model_id}/log")
async def log_performance(
    model_id: str = Path(...),
    success: bool = Body(...),
    response_time: float = Body(0.0),
    error_message: Optional[str] = Body(None),
):
    payload = {
        "action": "log_performance",
        "model_id": model_id,
        "success": success,
        "response_time": response_time,
    }
    if error_message:
        payload["error_message"] = error_message
    resp = _process(payload)
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message", "Failed"))
    return resp


@router.get("/trust/{model_id}")
async def get_trust_score(model_id: str = Path(...)):
    resp = _process({"action": "get_trust_score", "model_id": model_id})
    if resp.get("status") != "success":
        raise HTTPException(status_code=404, detail=resp.get("message"))
    return resp


@router.get("/trust/{model_id}/history")
async def get_history(model_id: str = Path(...), limit: int = Query(10)):
    resp = _process({"action": "get_performance_history", "model_id": model_id, "limit": limit})
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp


@router.post("/trust/raw")
async def raw_forward(body: Dict[str, Any] = Body(...)):
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object expected")
    return _process(body)