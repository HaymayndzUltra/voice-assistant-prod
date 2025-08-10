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

    # --- Task-specific wrappers -----------------------------------------
    async def stt(self, audio_bytes: bytes, language: str = "en-US", model: str | None = None) -> Any:
        async def _inner():
            import tempfile, asyncio as _aio
            mdl = model or "whisper-1"
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp.flush()
                with open(tmp.name, "rb") as f:
                    resp = await _aio.to_thread(
                        self.client.audio.transcriptions.create,
                        model=mdl,
                        file=f,
                        language=language.split("-")[0] if language != "auto" else None,
                    )
                return {"text": resp.text, "provider": self.name, "confidence": 0.9}

        return await self.breaker.call_async(_inner)

    async def tts(self, text: str, voice: str | None = None, model: str | None = None) -> Any:
        async def _inner():
            import asyncio as _aio
            mdl = model or "tts-1-hd"
            v = voice or "alloy"
            resp = await _aio.to_thread(
                self.client.audio.speech.create,
                model=mdl,
                voice=v,
                input=text,
            )
            return {"audio_bytes": resp.content, "provider": self.name}

        return await self.breaker.call_async(_inner)

    # --- Generic dispatcher used by router for now ----------------------
    async def call(self, **kwargs) -> Any:
        if "audio_bytes" in kwargs:
            return await self.stt(kwargs["audio_bytes"], kwargs.get("language", "en-US"))
        elif "text" in kwargs:
            return await self.tts(kwargs["text"], kwargs.get("voice"))
        else:
            return {"provider": self.name, "error": "unknown payload"}