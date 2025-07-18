"""FastAPI router integrating the legacy KnowledgeBase agent.

Endpoints mapped (Phase-1 minimal set):

POST /doc                     – create knowledge fact (topic + content)
GET  /doc/{topic}             – retrieve fact by topic
PUT  /doc/{memory_id}         – update fact by Memory ID
GET  /kb/search               – search facts (query param)
POST /knowledge_base/raw      – raw passthrough to agent.process_request

All operations delegate to the original KnowledgeBase class which
internally uses MemoryClient / MemoryOrchestratorService.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Body, Path, Query, status

try:
    from main_pc_code.agents.knowledge_base import KnowledgeBase  # noqa: E402
except ModuleNotFoundError:
    from importlib import import_module

    KnowledgeBase = import_module("main_pc_code.agents.knowledge_base").KnowledgeBase  # type: ignore

logger = logging.getLogger("memory_hub.knowledge_base_router")

_kb_agent: Optional[KnowledgeBase] = None

def get_agent() -> KnowledgeBase:
    global _kb_agent
    if _kb_agent is None:
        logger.info("[MemoryHub] Initialising KnowledgeBase instance for router")
        _kb_agent = KnowledgeBase()
    return _kb_agent

router = APIRouter(prefix="", tags=["KnowledgeBase"])


def _process(payload: Dict[str, Any]) -> Dict[str, Any]:
    return get_agent().process_request(payload)

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/doc")
async def add_fact(
    topic: str = Body(...),
    content: str = Body(...),
):
    payload = {
        "action": "add_fact",
        "topic": topic,
        "content": content,
    }
    resp = _process(payload)
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp


@router.get("/doc/{topic}")
async def get_fact(topic: str = Path(...)):
    payload = {
        "action": "get_fact",
        "topic": topic,
    }
    resp = _process(payload)
    if resp.get("status") != "success":
        raise HTTPException(status_code=404, detail=resp.get("message"))
    return resp


@router.put("/doc/{memory_id}")
async def update_fact(
    memory_id: str = Path(...),
    content: str = Body(...),
):
    payload = {
        "action": "update_fact",
        "memory_id": memory_id,
        "content": content,
    }
    resp = _process(payload)
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp


@router.get("/kb/search")
async def search_facts(query: str = Query(...), limit: int = Query(10)):
    payload = {
        "action": "search_facts",
        "query": query,
        "limit": limit,
    }
    resp = _process(payload)
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp


@router.post("/knowledge_base/raw")
async def raw_forward(request_body: Dict[str, Any] = Body(...)):
    if not isinstance(request_body, dict):
        raise HTTPException(status_code=400, detail="JSON object expected")
    return _process(request_body)