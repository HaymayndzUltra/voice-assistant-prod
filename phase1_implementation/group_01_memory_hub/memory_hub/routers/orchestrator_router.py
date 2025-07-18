"""Router exposing MemoryOrchestratorService capabilities via REST.

Only a subset of high-level operations are mapped for Phase 1; advanced
clients may still use `/orchestrator/raw` for full action routing.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Body, Path, status

try:
    from pc2_code.agents.memory_orchestrator_service import MemoryOrchestratorService  # noqa: E402
except ModuleNotFoundError:
    from importlib import import_module

    MemoryOrchestratorService = import_module("pc2_code.agents.memory_orchestrator_service").MemoryOrchestratorService  # type: ignore

logger = logging.getLogger("memory_hub.orchestrator_router")

_orchestrator: Optional[MemoryOrchestratorService] = None

def get_orchestrator() -> MemoryOrchestratorService:
    global _orchestrator
    if _orchestrator is None:
        logger.info("[MemoryHub] Starting embedded MemoryOrchestratorService instance")
        _orchestrator = MemoryOrchestratorService(port=0, strict_port=False)
    return _orchestrator


def _process(payload: Dict[str, Any]) -> Dict[str, Any]:
    return get_orchestrator().handle_request(payload)

router = APIRouter(prefix="", tags=["MemoryOrchestrator"])

# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------

@router.post("/memory")
async def add_memory(payload: Dict[str, Any] = Body(...)):
    if "content" not in payload:
        raise HTTPException(status_code=400, detail="'content' field required")
    data = {
        **payload,
        "created_by": "MemoryHub",
    }
    req = {"action": "add_memory", "data": data}
    resp = _process(req)
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp


@router.get("/memory/{memory_id}")
async def get_memory(memory_id: str = Path(...)):
    resp = _process({"action": "get_memory", "data": {"memory_id": memory_id}})
    if resp.get("status") != "success":
        raise HTTPException(status_code=404, detail=resp.get("message"))
    return resp


@router.put("/memory/{memory_id}")
async def update_memory(memory_id: str = Path(...), update_data: Dict[str, Any] = Body(...)):
    req = {
        "action": "update_memory",
        "data": {"memory_id": memory_id, "update_data": update_data},
    }
    resp = _process(req)
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp


@router.delete("/memory/{memory_id}")
async def delete_memory(memory_id: str = Path(...), cascade: bool = True):
    req = {
        "action": "delete_memory",
        "data": {"memory_id": memory_id, "cascade": cascade},
    }
    resp = _process(req)
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp


@router.post("/memory/search")
async def search_memory(query_body: Dict[str, Any] = Body(...)):
    query = query_body.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="'query' required")
    data = {
        "query": query,
        "limit": int(query_body.get("limit", 10)),
    }
    if "memory_type" in query_body:
        data["memory_type"] = query_body["memory_type"]
    req = {"action": "search_memory", "data": data}
    resp = _process(req)
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp


@router.post("/memory/semantic_search")
async def semantic_search(body: Dict[str, Any] = Body(...)):
    query = body.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="'query' required")
    req = {
        "action": "semantic_search",
        "data": {"query": query, "k": int(body.get("k", 5)), "filters": body.get("filters")},
    }
    resp = _process(req)
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp


@router.post("/orchestrator/raw")
async def raw_forward(request_body: Dict[str, Any] = Body(...)):
    if not isinstance(request_body, dict):
        raise HTTPException(status_code=400, detail="JSON object expected")
    resp = _process(request_body)
    return resp