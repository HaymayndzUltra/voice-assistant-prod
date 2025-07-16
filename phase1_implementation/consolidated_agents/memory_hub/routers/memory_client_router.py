"""FastAPI router that wraps the legacy MemoryClient agent.

This router exposes simplified REST endpoints that internally delegate
operations to the original `MemoryClient` (ZeroMQ client).  The goal is
to keep **all** capabilities accessible while providing developer-
friendly HTTP routes.

Initial endpoints implemented:

GET  /kv/{key}      → MemoryClient.get_memory
POST /kv/{key}      → Upsert value using add_memory / update_memory
POST /memory_client/raw  → Forward arbitrary action/data payload to the
                           MemoryOrchestratorService (full power, legacy
                           compatible).

Future work may add richer semantic routes; for Phase 1 we prioritise
loss-less exposure.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Body, status

try:
    from main_pc_code.agents.memory_client import MemoryClient  # noqa: E402 – relative import
except ModuleNotFoundError:  # fallback path resolution
    # In case working directory path differs inside container
    from importlib import import_module

    MemoryClient = import_module("main_pc_code.agents.memory_client").MemoryClient  # type: ignore

logger = logging.getLogger("memory_hub.memory_client_router")

# Single shared client instance (thread-safe send/recv due to ZMQ REQ? we
# protect with send_mutex later if needed).  For read-only operations this
# is acceptable within uvicorn workers.
_memory_client: Optional[MemoryClient] = None


def get_client() -> MemoryClient:
    global _memory_client
    if _memory_client is None:
        logger.info("[MemoryHub] Initialising MemoryClient instance for router")
        _memory_client = MemoryClient(agent_name="MemoryHubRouter")
    return _memory_client


router = APIRouter(prefix="", tags=["MemoryClient"])


@router.get("/kv/{key}")
async def kv_get(key: str):
    """Retrieve a value/memory by key (memory_id)."""
    client = get_client()
    resp: Dict[str, Any] = client.get_memory(key)
    if resp.get("status") != "success":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=resp.get("message"))
    return resp


@router.post("/kv/{key}")
async def kv_put(key: str, payload: Dict[str, Any] = Body(...)):
    """Create or update a key.

    The payload may contain:
    - content: str (required)
    - metadata, tags, importance, etc.
    """
    client = get_client()

    content = payload.get("content")
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'content' field required")

    # Determine if memory exists
    current = client.get_memory(key)
    if current.get("status") == "success":
        # Update
        update_resp = client.update_memory(memory_id=key, update_payload={"content": content, **{k: v for k, v in payload.items() if k != "content"}})
        if update_resp.get("status") != "success":
            raise HTTPException(status_code=500, detail=update_resp.get("message"))
        return update_resp

    # Else create new memory with given key by using parent-specified memory_id? add_memory generates id; we can't set memory_id
    add_resp = client.add_memory(
        content=content,
        memory_type=payload.get("memory_type", "kv"),
        memory_tier=payload.get("memory_tier", "short"),
        importance=float(payload.get("importance", 0.5)),
        metadata=payload.get("metadata"),
        tags=payload.get("tags"),
        parent_id=payload.get("parent_id"),
    )
    return add_resp


@router.post("/memory_client/raw")
async def raw_forward(request_body: Dict[str, Any] = Body(...)):
    """Forward an arbitrary payload to MemoryOrchestratorService.

    This maintains backward-compatible access for advanced clients that
    already speak the legacy action/data schema.
    """
    if not isinstance(request_body, dict):
        raise HTTPException(status_code=400, detail="JSON object expected")
    client = get_client()
    resp = client._send_request(request_body)  # pylint: disable=protected-access
    return resp