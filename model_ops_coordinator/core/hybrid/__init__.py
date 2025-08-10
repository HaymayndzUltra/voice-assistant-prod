from __future__ import annotations

"""Hybrid inference module scaffold.

Provides local-first / cloud-first routing for STT, TTS, Reasoning and Translate.
Final routing logic will be implemented incrementally.
"""

from pathlib import Path
import yaml
from typing import Optional, Any
from ..telemetry import Telemetry  # type: ignore
from ..lifecycle import LifecycleModule  # type: ignore
from ..resiliency.circuit_breaker import get_circuit_breaker  # type: ignore
from .policy_loader import HybridPolicy, PolicyLoader
from .router import HybridRouter


class HybridModule:
    """Central hybrid inference orchestrator (Local ⇄ Cloud)."""

    def __init__(self, cfg_path: Optional[Path], lifecycle: LifecycleModule, telemetry: Telemetry):
        self.lifecycle = lifecycle
        self.telemetry = telemetry
        self.policy_loader = PolicyLoader(cfg_path)
        self.policy: HybridPolicy = self.policy_loader.load()
        # Router will be wired once provider adapters are implemented
        self.router = HybridRouter(self.policy, lifecycle, telemetry)

    # --- Public API -----------------------------------------------------
    async def stt(self, audio_bytes: bytes, language: str = "en-US") -> Any:
        return await self.router.stt(audio_bytes, language)

    async def tts(self, text: str, voice: str | None = None, language: str = "en-US") -> Any:
        return await self.router.tts(text, voice, language)

    async def reason(self, prompt: str, model: str | None = None, temperature: float = 0.7) -> Any:
        return await self.router.reason(prompt, model, temperature)

    async def translate(self, text: str, target: str, source: str = "auto") -> Any:
        return await self.router.translate(text, target, source)

    # --- Metrics --------------------------------------------------------
    def get_metrics(self) -> dict:
        return self.router.get_metrics()