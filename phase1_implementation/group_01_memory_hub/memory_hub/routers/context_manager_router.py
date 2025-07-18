"""Router wrapping legacy ContextManager (PC2 version).

Endpoints:
POST /context/add             – add to context
GET  /context                  – get context list
GET  /context/text             – get formatted context text
POST /context/clear            – clear context (global or per speaker)
POST /context/prune            – prune low-importance items
POST /context_manager/raw      – raw dict passthrough (uses action field)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, List

from fastapi import APIRouter, HTTPException, Body, Query

try:
    from pc2_code.agents.context_manager import ContextManager  # noqa: E402
except ModuleNotFoundError:
    from importlib import import_module

    ContextManager = import_module("pc2_code.agents.context_manager").ContextManager  # type: ignore

logger = logging.getLogger("memory_hub.context_manager_router")

_ctx: Optional[ContextManager] = None

def get_ctx() -> ContextManager:
    global _ctx
    if _ctx is None:
        logger.info("[MemoryHub] Initialising ContextManager instance")
        _ctx = ContextManager()
    return _ctx

router = APIRouter(prefix="", tags=["ContextManager"])

# ---------------------------------------------------------------------------
# Helper for raw action mapping to stay compatible with original ContextManagerAgent
# ---------------------------------------------------------------------------

def _process(request: Dict[str, Any]) -> Dict[str, Any]:
    action = request.get("action")
    cm = get_ctx()
    try:
        if action == "add_to_context":
            cm.add_to_context(
                text=request.get("text"),
                speaker=request.get("speaker"),
                metadata=request.get("metadata"),
            )
            return {"status": "success", "message": "Added"}
        elif action == "get_context":
            ctx = cm.get_context(
                speaker=request.get("speaker"), max_items=request.get("max_items")
            )
            return {"status": "success", "context": ctx}
        elif action == "get_context_text":
            text = cm.get_context_text(
                speaker=request.get("speaker"), max_items=request.get("max_items")
            )
            return {"status": "success", "context_text": text}
        elif action == "clear_context":
            cm.clear_context(request.get("speaker"))
            return {"status": "success", "message": "Cleared"}
        elif action == "prune_context":
            cm.prune_context()
            return {"status": "success", "message": "Pruned"}
        else:
            return {"status": "error", "message": f"Unknown action {action}"}
    except Exception as e:
        logger.error(f"ContextManager error: {e}")
        return {"status": "error", "message": str(e)}

# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@router.post("/context/add")
async def add_to_context(
    text: str = Body(...),
    speaker: Optional[str] = Body(None),
    metadata: Optional[Dict[str, Any]] = Body(None),
):
    cm = get_ctx()
    cm.add_to_context(text=text, speaker=speaker, metadata=metadata)
    return {"status": "success"}


@router.get("/context")
async def get_context(
    speaker: Optional[str] = Query(None),
    max_items: Optional[int] = Query(None),
):
    cm = get_ctx()
    ctx_list: List[Dict[str, Any]] = cm.get_context(speaker=speaker, max_items=max_items)
    return {"status": "success", "context": ctx_list}


@router.get("/context/text")
async def get_context_text(
    speaker: Optional[str] = Query(None),
    max_items: Optional[int] = Query(None),
):
    cm = get_ctx()
    text = cm.get_context_text(speaker=speaker, max_items=max_items)
    return {"status": "success", "context_text": text}


@router.post("/context/clear")
async def clear_context(speaker: Optional[str] = Body(None)):
    cm = get_ctx()
    cm.clear_context(speaker)
    return {"status": "success"}


@router.post("/context/prune")
async def prune_context():
    cm = get_ctx()
    cm.prune_context()
    return {"status": "success"}


@router.post("/context_manager/raw")
async def raw_forward(body: Dict[str, Any] = Body(...)):
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object expected")
    return _process(body)