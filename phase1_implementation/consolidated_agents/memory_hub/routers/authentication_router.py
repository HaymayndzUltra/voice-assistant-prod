"""Router wrapping AuthenticationAgent.

Endpoints:
POST /auth/register     – register (user_id, password)
POST /auth/login        – login (user_id, password)
POST /auth/logout       – logout (token)
POST /auth/verify       – verify token
POST /auth/raw          – raw passthrough
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Body

try:
    from pc2_code.agents.ForPC2.AuthenticationAgent import AuthenticationAgent  # noqa: E402
except ModuleNotFoundError:
    from importlib import import_module

    AuthenticationAgent = import_module("pc2_code.agents.ForPC2.AuthenticationAgent").AuthenticationAgent  # type: ignore

logger = logging.getLogger("memory_hub.authentication_router")

_auth: Optional[AuthenticationAgent] = None

def get_auth() -> AuthenticationAgent:
    global _auth
    if _auth is None:
        logger.info("[MemoryHub] Starting AuthenticationAgent instance")
        _auth = AuthenticationAgent(port=0, health_check_port=0)
    return _auth


def _process(payload: Dict[str, Any]) -> Dict[str, Any]:
    return get_auth().handle_request(payload)

router = APIRouter(prefix="", tags=["Authentication"])

# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@router.post("/auth/register")
async def register(user_id: str = Body(...), password: str = Body(...)):
    resp = _process({"action": "register", "user_id": user_id, "password": password})
    if resp.get("status") != "success":
        raise HTTPException(status_code=400, detail=resp.get("message"))
    return resp


@router.post("/auth/login")
async def login(user_id: str = Body(...), password: str = Body(...)):
    resp = _process({"action": "login", "user_id": user_id, "password": password})
    if resp.get("status") != "success":
        raise HTTPException(status_code=401, detail=resp.get("message"))
    return resp


@router.post("/auth/logout")
async def logout(token: str = Body(...)):
    resp = _process({"action": "logout", "token": token})
    if resp.get("status") != "success":
        raise HTTPException(status_code=400, detail=resp.get("message"))
    return resp


@router.post("/auth/verify")
async def verify(token: str = Body(...)):
    resp = _process({"action": "validate_token", "token": token})
    return resp


@router.post("/auth/raw")
async def raw_forward(body: Dict[str, Any] = Body(...)):
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object expected")
    return _process(body)