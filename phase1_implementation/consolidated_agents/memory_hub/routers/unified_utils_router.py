"""Router exposing UnifiedUtilsAgent utility operations.

Route format (from Phase plan):
POST /utils/{operation}
where operation is one of:
  - cleanup_temp_files
  - cleanup_logs
  - cleanup_cache
  - cleanup_browser_cache
  - run_windows_disk_cleanup
  - cleanup_system
Any additional fields in the JSON body are forwarded as keyword params.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Body, Path

try:
    from pc2_code.agents.ForPC2.unified_utils_agent import UnifiedUtilsAgent  # noqa: E402
except ModuleNotFoundError:
    from importlib import import_module

    UnifiedUtilsAgent = import_module("pc2_code.agents.ForPC2.unified_utils_agent").UnifiedUtilsAgent  # type: ignore

logger = logging.getLogger("memory_hub.unified_utils_router")

_utils: Optional[UnifiedUtilsAgent] = None

def get_utils() -> UnifiedUtilsAgent:
    global _utils
    if _utils is None:
        logger.info("[MemoryHub] Starting UnifiedUtilsAgent instance")
        _utils = UnifiedUtilsAgent(port=0, health_check_port=0)
    return _utils

router = APIRouter(prefix="", tags=["UnifiedUtils"])

# Allowed operations mapping directly to agent methods
_ALLOWED_OPS = {
    "cleanup_temp_files",
    "cleanup_logs",
    "cleanup_cache",
    "cleanup_browser_cache",
    "run_windows_disk_cleanup",
    "cleanup_system",
}


@router.post("/utils/{operation}")
async def utils_operation(
    operation: str = Path(...),
    params: Dict[str, Any] = Body(default_factory=dict),
):
    if operation not in _ALLOWED_OPS:
        raise HTTPException(status_code=404, detail="Unknown operation")

    agent = get_utils()
    method = getattr(agent, operation, None)
    if method is None:
        raise HTTPException(status_code=500, detail="Operation not implemented in agent")
    try:
        result = method(**params) if params else method()
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"UnifiedUtilsAgent error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/utils/raw")
async def raw_forward(body: Dict[str, Any] = Body(...)):
    """Forward raw dict to agent.handle_request (legacy compatibility)."""
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object expected")
    agent = get_utils()
    resp = agent.handle_request(body)
    return resp