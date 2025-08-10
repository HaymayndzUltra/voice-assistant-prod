from __future__ import annotations

"""HybridRouter placeholder - will wrap providers with hedging logic."""
from typing import Any
from .policy_loader import HybridPolicy
from ..telemetry import Telemetry  # type: ignore
from ..lifecycle import LifecycleModule  # type: ignore

# For now use mock providers builder
from .providers import build_provider


class HybridRouter:
    def __init__(self, policy: HybridPolicy, lifecycle: LifecycleModule, telemetry: Telemetry):
        self.policy = policy
        self.lifecycle = lifecycle
        self.telemetry = telemetry
        # Build provider map from policy (mock only)
        self._providers = {}
        for service, cfg in policy.services.items():
            prov_map = {}
            if 'providers' in cfg:
                for category, plist in cfg['providers'].items():
                    prov_map[category] = [build_provider(p['name']) for p in plist]
            self._providers[service] = prov_map

    async def stt(self, audio_bytes: bytes, language: str) -> Any:
        provs = self._providers.get('stt', {})
        local_list = provs.get('local', [])
        cloud_list = provs.get('cloud', [])
        # local first simple
        for p in local_list + cloud_list:
            result = await p.call(audio_bytes=audio_bytes, language=language)
            return result
        raise RuntimeError("No providers configured")

    async def tts(self, text: str, voice: str | None, language: str) -> Any:
        provs = self._providers.get('tts', {})
        for category in ['primary', 'secondary', 'local']:
            for p in provs.get(category, []):
                return await p.call(text=text, voice=voice, language=language)
        raise RuntimeError("No TTS providers configured")

    async def reason(self, prompt: str, model: str | None, temperature: float):
        return {"provider": "mock_reason", "text": "mock"}

    async def translate(self, text: str, target: str, source: str):
        return {"provider": "mock_translate", "text": text}

    def get_metrics(self) -> dict:
        return {}