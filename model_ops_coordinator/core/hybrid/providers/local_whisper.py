"""Local Whisper adapter (skeleton)."""
from __future__ import annotations
import asyncio, logging
from typing import Any
from ...resiliency.circuit_breaker import get_circuit_breaker, CircuitBreaker

logger = logging.getLogger(__name__)

class LocalWhisperProvider:
    def __init__(self, name: str):
        self.name = name
        self.breaker: CircuitBreaker = get_circuit_breaker(name)
        try:
            import whisper  # type: ignore
        except ImportError:
            logger.warning("whisper not installed; using mock output")
            whisper = None
        self._whisper = whisper

    async def call(self, **kwargs) -> Any:
        async def _inner():
            await asyncio.sleep(0.05)
            return {"provider": self.name, "result": "local-whisper-mock", "confidence": 0.85}
        return await self.breaker.call_async(_inner)