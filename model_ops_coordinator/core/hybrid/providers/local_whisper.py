"""Local Whisper adapter (skeleton)."""
from __future__ import annotations
import asyncio, logging, tempfile, os
from typing import Any
from ...resiliency.circuit_breaker import get_circuit_breaker, CircuitBreaker

logger = logging.getLogger(__name__)

class LocalWhisperProvider:
    def __init__(self, name: str):
        self.name = name
        self.breaker: CircuitBreaker = get_circuit_breaker(name)
        try:
            import whisper  # type: ignore
            self.model = whisper.load_model("base")
        except ImportError:
            logger.warning("whisper not installed; using mock output")
            self.model = None

    async def stt(self, audio_bytes: bytes, language: str = "en-US") -> Any:
        async def _inner():
            if not self.model:
                return {"text": "whisper-mock", "provider": self.name, "confidence": 0.7}
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp.flush()
                result = await asyncio.to_thread(
                    self.model.transcribe,
                    tmp.name,
                    language=language.split("-")[0] if language != "auto" else None
                )
                os.unlink(tmp.name)
                return {
                    "text": result.get("text", "").strip(),
                    "provider": self.name,
                    "confidence": 1.0 - result.get("no_speech_prob", 0.1)
                }
        return await self.breaker.call_async(_inner)

    async def call(self, **kwargs) -> Any:
        if "audio_bytes" in kwargs:
            return await self.stt(kwargs["audio_bytes"], kwargs.get("language", "en-US"))
        else:
            return {"provider": self.name, "error": "no audio_bytes"}