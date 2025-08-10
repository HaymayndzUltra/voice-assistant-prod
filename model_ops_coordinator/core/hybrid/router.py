from __future__ import annotations

"""HybridRouter placeholder - will wrap providers with hedging logic."""
from typing import Any
from .policy_loader import HybridPolicy
from ..telemetry import Telemetry  # type: ignore
from ..lifecycle import LifecycleModule  # type: ignore


class HybridRouter:
    def __init__(self, policy: HybridPolicy, lifecycle: LifecycleModule, telemetry: Telemetry):
        self.policy = policy
        self.lifecycle = lifecycle
        self.telemetry = telemetry
        # TODO: initialize providers and configure routing logic

    async def stt(self, audio_bytes: bytes, language: str) -> Any:
        raise NotImplementedError("STT routing not yet implemented")

    async def tts(self, text: str, voice: str | None, language: str) -> Any:
        raise NotImplementedError("TTS routing not yet implemented")

    async def reason(self, prompt: str, model: str | None, temperature: float):
        raise NotImplementedError("Reasoning routing not yet implemented")

    async def translate(self, text: str, target: str, source: str):
        raise NotImplementedError("Translate routing not yet implemented")

    def get_metrics(self) -> dict:
        return {}