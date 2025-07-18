"""Router exposing CacheManager functionality via HTTP.

Supported routes (Phase-1):
GET    /cache/{cache_type}/{key}               – retrieve entry
POST   /cache/{cache_type}/{key}               – put entry (value, ttl)
DELETE /cache/{cache_type}/{key}               – invalidate entry
POST   /cache/{cache_type}/flush               – flush all entries of type
GET    /memory_cache/{memory_id}               – get cached memory
POST   /memory_cache/{memory_id}               – cache memory (data, ttl)
DELETE /memory_cache/{memory_id}               – invalidate memory cache
POST   /cache_manager/raw                      – raw passthrough
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Body, Path, status

try:
    from pc2_code.agents.cache_manager import CacheManager  # noqa: E402
except ModuleNotFoundError:
    from importlib import import_module

    CacheManager = import_module("pc2_code.agents.cache_manager").CacheManager  # type: ignore

logger = logging.getLogger("memory_hub.cache_manager_router")

_cm: Optional[CacheManager] = None

def get_cm() -> CacheManager:
    global _cm
    if _cm is None:
        logger.info("[MemoryHub] Starting CacheManager instance")
        _cm = CacheManager(port=0, health_port=0)
    return _cm


def _process(payload: Dict[str, Any]) -> Dict[str, Any]:
    return get_cm().process_request(payload)

router = APIRouter(prefix="", tags=["CacheManager"])

# ---------------------------------------------------------------------------
# Generic cache operations
# ---------------------------------------------------------------------------

@router.get("/cache/{cache_type}/{key}")
async def get_cache_entry(cache_type: str = Path(...), key: str = Path(...)):
    resp = _process({"action": "get", "cache_type": cache_type, "key": key})
    if resp.get("status") != "success":
        raise HTTPException(status_code=404, detail=resp.get("message"))
    return resp


@router.post("/cache/{cache_type}/{key}")
async def put_cache_entry(
    cache_type: str = Path(...),
    key: str = Path(...),
    value: Any = Body(...),
    ttl: Optional[int] = Body(None),
):
    payload = {
        "action": "put",
        "cache_type": cache_type,
        "key": key,
        "value": value,
    }
    if ttl is not None:
        payload["ttl"] = ttl
    resp = _process(payload)
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp


@router.delete("/cache/{cache_type}/{key}")
async def invalidate_cache_entry(cache_type: str = Path(...), key: str = Path(...)):
    resp = _process({"action": "invalidate", "cache_type": cache_type, "key": key})
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp


@router.post("/cache/{cache_type}/flush")
async def flush_cache(cache_type: str = Path(...)):
    resp = _process({"action": "flush", "cache_type": cache_type})
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp

# ---------------------------------------------------------------------------
# Memory-specific helpers
# ---------------------------------------------------------------------------

@router.get("/memory_cache/{memory_id}")
async def get_memory_cache(memory_id: str = Path(...)):
    resp = _process({"action": "get_cached_memory", "memory_id": memory_id})
    if resp.get("status") != "success":
        raise HTTPException(status_code=404, detail=resp.get("message"))
    return resp


@router.post("/memory_cache/{memory_id}")
async def cache_memory(memory_id: str = Path(...), data: Dict[str, Any] = Body(...), ttl: int = Body(3600)):
    payload = {
        "action": "cache_memory",
        "memory_id": memory_id,
        "data": data,
        "ttl": ttl,
    }
    resp = _process(payload)
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp


@router.delete("/memory_cache/{memory_id}")
async def invalidate_memory_cache(memory_id: str = Path(...)):
    resp = _process({"action": "invalidate_memory_cache", "memory_id": memory_id})
    if resp.get("status") != "success":
        raise HTTPException(status_code=500, detail=resp.get("message"))
    return resp

# ---------------------------------------------------------------------------
# Raw access
# ---------------------------------------------------------------------------

@router.post("/cache_manager/raw")
async def raw_forward(body: Dict[str, Any] = Body(...)):
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object expected")
    return _process(body)