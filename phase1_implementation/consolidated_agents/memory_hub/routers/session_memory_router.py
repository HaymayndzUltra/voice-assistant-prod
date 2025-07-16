"""FastAPI router for the legacy SessionMemoryAgent.

This wrapper exposes session-centric endpoints that forward requests to
`SessionMemoryAgent.process_request` while preserving all underlying
logic.  It relies on the same MemoryClient pathway as the original
agent, therefore remains fully compatible with MemoryOrchestratorService.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Body, Path, Query, status

try:
    from main_pc_code.agents.session_memory_agent import SessionMemoryAgent  # noqa: E402
except ModuleNotFoundError:
    from importlib import import_module

    SessionMemoryAgent = import_module("main_pc_code.agents.session_memory_agent").SessionMemoryAgent  # type: ignore

logger = logging.getLogger("memory_hub.session_memory_router")

_agent: Optional[SessionMemoryAgent] = None

def get_agent() -> SessionMemoryAgent:
    global _agent
    if _agent is None:
        logger.info("[MemoryHub] Initialising SessionMemoryAgent instance for router")
        _agent = SessionMemoryAgent()
    return _agent

router = APIRouter(prefix="", tags=["SessionMemory"])

# ---------------------------------------------------------------------------
# Helper to send request dict to agent
# ---------------------------------------------------------------------------

def _process(payload: Dict[str, Any]) -> Dict[str, Any]:
    agent = get_agent()
    return agent.process_request(payload)


# ---------------------------------------------------------------------------
# REST endpoints mapping
# ---------------------------------------------------------------------------

@router.post("/session")
async def create_session(
    user_id: str = Body(...),
    session_type: str = Body("conversation"),
    metadata: Optional[Dict[str, Any]] = Body(None),
):
    payload = {
        "action": "create_session",
        "user_id": user_id,
        "session_type": session_type,
        "metadata": metadata or {},
    }
    resp = _process(payload)
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp


@router.post("/session/{session_id}/interaction")
async def add_interaction(
    session_id: str = Path(...),
    role: str = Body(...),
    content: str = Body(...),
    metadata: Optional[Dict[str, Any]] = Body(None),
):
    payload = {
        "action": "add_interaction",
        "session_id": session_id,
        "role": role,
        "content": content,
        "metadata": metadata or {},
    }
    resp = _process(payload)
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp


@router.get("/session/{session_id}/context")
async def get_context(session_id: str = Path(...), limit: int = Query(20)):
    payload = {
        "action": "get_context",
        "session_id": session_id,
        "limit": limit,
    }
    resp = _process(payload)
    if resp.get("status") != "success":
        raise HTTPException(status_code=404, detail=resp.get("message"))
    return resp


@router.delete("/session/{session_id}")
async def delete_session(session_id: str = Path(...)):
    payload = {
        "action": "delete_session",
        "session_id": session_id,
    }
    resp = _process(payload)
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp


@router.get("/session/{session_id}/search")
async def search_interactions(
    session_id: str = Path(...),
    query: str = Query(...),
    limit: int = Query(10),
):
    payload = {
        "action": "search_interactions",
        "session_id": session_id,
        "query": query,
        "limit": limit,
    }
    resp = _process(payload)
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp


@router.post("/session_agent/raw")
async def raw_forward(request_body: Dict[str, Any] = Body(...)):
    """Forward raw dict to SessionMemoryAgent.process_request."""
    if not isinstance(request_body, dict):
        raise HTTPException(status_code=400, detail="JSON object expected")
    resp = _process(request_body)
    return resp