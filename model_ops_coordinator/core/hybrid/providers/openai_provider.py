"""OpenAI provider adapter (skeleton)."""
from __future__ import annotations

import os
import asyncio
from typing import Any
import logging
from ...resiliency.circuit_breaker import get_circuit_breaker, CircuitBreaker

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """Adapter for OpenAI endpoints (chat, stt, tts, translate)."""

    def __init__(self, name: str):
        self.name = name
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not set; OpenAIProvider unavailable")
        self.breaker: CircuitBreaker = get_circuit_breaker(name)
        # Lazy import to avoid heavy cost if unused
        import openai  # type: ignore
        self.client = openai.OpenAI(api_key=self.api_key,
                                    base_url=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
                                    organization=os.getenv("OPENAI_ORGANIZATION"))

    # --- Public wrappers -------------------------------------------------
    async def call(self, **kwargs) -> Any:
        """Generic call used by mock router until specific tasks mapped."""
        async def _inner():
            await asyncio.sleep(0.05)
            return {"provider": self.name, "result": "openai-mock"}
        return await self.breaker.call_async(_inner)