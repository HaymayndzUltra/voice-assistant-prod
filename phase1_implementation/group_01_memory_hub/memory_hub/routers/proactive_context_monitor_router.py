"""Router wrapping ProactiveContextMonitor agent.

Endpoints:
POST /proactive/context           – add context entry
GET  /proactive/history           – retrieve history (limit)
POST /proactive/clear             – clear history
POST /proactive/raw               – raw passthrough
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Body, Query

try:
    from pc2_code.agents.ForPC2.proactive_context_monitor import ProactiveContextMonitor  # noqa: E402
except ModuleNotFoundError:
    from importlib import import_module

    ProactiveContextMonitor = import_module("pc2_code.agents.ForPC2.proactive_context_monitor").ProactiveContextMonitor  # type: ignore

logger = logging.getLogger("memory_hub.proactive_context_monitor_router")

_pcm: Optional[ProactiveContextMonitor] = None

def get_pcm() -> ProactiveContextMonitor:
    global _pcm
    if _pcm is None:
        logger.info("[MemoryHub] Starting ProactiveContextMonitor instance")
        _pcm = ProactiveContextMonitor(port=0, health_check_port=0)
    return _pcm


def _process(payload: Dict[str, Any]) -> Dict[str, Any]:
    return get_pcm().handle_request(payload)

router = APIRouter(prefix="", tags=["ProactiveContextMonitor"])

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/proactive/context")
async def add_context(context: Dict[str, Any] = Body(...)):
    if not context:
        raise HTTPException(status_code=400, detail="Missing context data")
    resp = _process({"action": "add_context", "context": context})
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp


@router.get("/proactive/history")
async def get_history(limit: int = Query(10)):
    resp = _process({"action": "get_context_history", "limit": limit})
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp


@router.post("/proactive/clear")
async def clear_history():
    resp = _process({"action": "clear_context_history"})
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp


@router.post("/proactive/raw")
async def raw_forward(body: Dict[str, Any] = Body(...)):
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object expected")
    return _process(body)