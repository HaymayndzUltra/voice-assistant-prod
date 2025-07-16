"""Router exposing ExperienceTrackerAgent functions.

Endpoints:
POST /experience                 – track experience (content, importance_score, metadata)
GET  /experience                 – list experiences (limit)
POST /experience_tracker/raw     – raw passthrough
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Body, Query, status

try:
    from pc2_code.agents.experience_tracker import ExperienceTrackerAgent  # noqa: E402
except ModuleNotFoundError:
    from importlib import import_module

    ExperienceTrackerAgent = import_module("pc2_code.agents.experience_tracker").ExperienceTrackerAgent  # type: ignore

logger = logging.getLogger("memory_hub.experience_tracker_router")

_et: Optional[ExperienceTrackerAgent] = None

def get_et() -> ExperienceTrackerAgent:
    global _et
    if _et is None:
        logger.info("[MemoryHub] Starting ExperienceTrackerAgent instance")
        _et = ExperienceTrackerAgent(port=0, health_port=0)
    return _et


def _process(payload: Dict[str, Any]) -> Dict[str, Any]:
    return get_et().handle_request(payload)

router = APIRouter(prefix="", tags=["ExperienceTracker"])

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/experience")
async def track_experience(
    content: str = Body(...),
    importance_score: float = Body(0.5),
    metadata: Optional[Dict[str, Any]] = Body(None),
    expires_at: Optional[str] = Body(None),
):
    payload = {
        "action": "track_experience",
        "content": content,
        "importance_score": importance_score,
        "metadata": metadata or {},
    }
    if expires_at:
        payload["expires_at"] = expires_at
    resp = _process(payload)
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message", "Failed"))
    return resp


@router.get("/experience")
async def get_experiences(limit: int = Query(10)):
    resp = _process({"action": "get_experiences", "limit": limit})
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp


@router.post("/experience_tracker/raw")
async def raw_forward(body: Dict[str, Any] = Body(...)):
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object expected")
    return _process(body)