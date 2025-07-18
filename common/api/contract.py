"""Canonical API contract (WP-00).

Defines the standard **Request** and **Response** payloads shared by all
inter-agent HTTP/ZMQ communications.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Request(BaseModel):
    action: str = Field(..., description="Name of the operation to perform.")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = Field(default_factory=lambda: time.time())
    client_id: str | None = Field(default=None, description="Originating agent")


class SuccessResponse(Generic[T], BaseModel):
    status: str = Field("success", const=True)
    data: T
    request_id: str
    timestamp: float = Field(default_factory=lambda: time.time())
    processing_time_ms: float | None = None


class ErrorResponse(BaseModel):
    status: str = Field("error", const=True)
    error_code: str
    error_message: str
    error_details: Dict[str, Any] | None = None
    request_id: str
    timestamp: float = Field(default_factory=lambda: time.time())


__all__ = [
    "Request",
    "SuccessResponse",
    "ErrorResponse",
]