"""Router wrapping UnifiedMemoryReasoningAgent (UMRA).

Exposes:
- POST /twin/{user_id}           update twin
- GET  /twin/{user_id}           get twin
- DELETE /twin/{user_id}         delete twin
- POST /interaction              add interaction
- GET  /context/{session_id}     get context summary
- POST /umra/raw                 raw action passthrough
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Body, Path, status

try:
    from pc2_code.agents.unified_memory_reasoning_agent import UnifiedMemoryReasoningAgent  # noqa: E402
except ModuleNotFoundError:
    from importlib import import_module

    UnifiedMemoryReasoningAgent = import_module("pc2_code.agents.unified_memory_reasoning_agent").UnifiedMemoryReasoningAgent  # type: ignore

logger = logging.getLogger("memory_hub.umra_router")

_umra: Optional[UnifiedMemoryReasoningAgent] = None

def get_umra() -> UnifiedMemoryReasoningAgent:
    global _umra
    if _umra is None:
        logger.info("[MemoryHub] Starting UnifiedMemoryReasoningAgent instance")
        _umra = UnifiedMemoryReasoningAgent(zmq_port=0, health_check_port=0)
    return _umra


def _process(payload: Dict[str, Any]) -> Dict[str, Any]:
    return get_umra().handle_request(payload)

router = APIRouter(prefix="", tags=["UnifiedMemoryReasoning"])

# ---------------------------------------------------------------------------
# Twin endpoints
# ---------------------------------------------------------------------------

@router.post("/twin/{user_id}")
async def update_twin(user_id: str = Path(...), twin_data: Dict[str, Any] = Body(...)):
    req = {"action": "update_twin", "user_id": user_id, "twin_data": twin_data}
    resp = _process(req)
    if resp.get("status") != "ok":
        raise HTTPException(status_code=500, detail=resp.get("reason"))
    return resp


@router.get("/twin/{user_id}")
async def get_twin(user_id: str = Path(...)):
    resp = _process({"action": "get_twin", "user_id": user_id})
    return resp


@router.delete("/twin/{user_id}")
async def delete_twin(user_id: str = Path(...)):
    resp = _process({"action": "delete_twin", "user_id": user_id})
    if resp.get("status") != "ok":
        raise HTTPException(status_code=404, detail=resp.get("reason"))
    return resp

# ---------------------------------------------------------------------------
# Interaction & context
# ---------------------------------------------------------------------------

@router.post("/interaction")
async def add_interaction(payload: Dict[str, Any] = Body(...)):
    required = {"session_id", "interaction_type", "content"}
    if not required.issubset(payload):
        raise HTTPException(status_code=400, detail=f"Missing required fields {required - set(payload.keys())}")
    resp = _process({"action": "add_interaction", **payload})
    if resp.get("status") != "ok":
        raise HTTPException(status_code=500, detail=resp.get("reason"))
    return resp


@router.get("/context/{session_id}")
async def get_context(session_id: str = Path(...), max_tokens: Optional[int] = None):
    req = {"action": "get_context", "session_id": session_id}
    if max_tokens is not None:
        req["max_tokens"] = max_tokens
    resp = _process(req)
    if resp.get("status") != "ok":
        raise HTTPException(status_code=404, detail=resp.get("reason"))
    return resp

# ---------------------------------------------------------------------------
# Error pattern solution
# ---------------------------------------------------------------------------

@router.post("/error_solution")
async def get_error_solution(body: Dict[str, Any] = Body(...)):
    error_message = body.get("error_message")
    if not error_message:
        raise HTTPException(status_code=400, detail="'error_message' required")
    resp = _process({"action": "get_error_solution", "error_message": error_message})
    return resp

# ---------------------------------------------------------------------------
# Raw access
# ---------------------------------------------------------------------------

@router.post("/umra/raw")
async def raw_forward(request_body: Dict[str, Any] = Body(...)):
    if not isinstance(request_body, dict):
        raise HTTPException(status_code=400, detail="JSON object expected")
    return _process(request_body)