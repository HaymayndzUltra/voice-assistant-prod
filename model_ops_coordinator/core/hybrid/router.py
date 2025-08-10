from __future__ import annotations

"""HybridRouter placeholder - will wrap providers with hedging logic."""
from typing import Any, List, Optional
import asyncio
import time
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
        """Local-first STT with hedging."""
        provs = self._providers.get('stt', {})
        local_list = provs.get('local', [])
        cloud_list = provs.get('cloud', [])
        
        if not local_list and not cloud_list:
            raise RuntimeError("No STT providers configured")
        
        # Get policy thresholds
        policy_cfg = self.policy.services.get('stt', {})
        fallback = policy_cfg.get('fallback_criteria', {})
        latency_threshold = fallback.get('latency_threshold_ms', 500) / 1000.0
        confidence_threshold = fallback.get('confidence_score_threshold', 0.75)
        timeout = fallback.get('per_call_timeout_ms', 4000) / 1000.0
        
        # Start with local
        local_task = None
        cloud_task = None
        
        try:
            if local_list:
                local_task = asyncio.create_task(local_list[0].call(audio_bytes=audio_bytes, language=language))
                
                # Wait for local up to latency threshold
                done, pending = await asyncio.wait({local_task}, timeout=latency_threshold, return_when=asyncio.FIRST_COMPLETED)
                
                if local_task in done:
                    result = await local_task
                    if result.get('confidence', 0) >= confidence_threshold:
                        return result
                    # Low confidence, hedge to cloud
                    if cloud_list:
                        cloud_task = asyncio.create_task(cloud_list[0].call(audio_bytes=audio_bytes, language=language))
                else:
                    # Latency exceeded, hedge to cloud
                    if cloud_list:
                        cloud_task = asyncio.create_task(cloud_list[0].call(audio_bytes=audio_bytes, language=language))
            
            # Race remaining tasks
            tasks = [t for t in [local_task, cloud_task] if t and not t.done()]
            if tasks:
                done, pending = await asyncio.wait(tasks, timeout=timeout, return_when=asyncio.FIRST_COMPLETED)
                if done:
                    return await done.pop()
            
            # Fallback to any completed task
            if local_task and local_task.done():
                return await local_task
            if cloud_task and cloud_task.done():
                return await cloud_task
                
            raise RuntimeError("STT timeout")
            
        finally:
            # Cancel pending tasks
            for t in [local_task, cloud_task]:
                if t and not t.done():
                    t.cancel()

    async def tts(self, text: str, voice: str | None, language: str) -> Any:
        """Cloud-first TTS with ordered fallback."""
        provs = self._providers.get('tts', {})
        policy_cfg = self.policy.services.get('tts', {})
        timeout = policy_cfg.get('per_call_timeout_ms', 3000) / 1000.0
        
        for category in ['primary', 'secondary', 'local']:
            for p in provs.get(category, []):
                try:
                    result = await asyncio.wait_for(
                        p.call(text=text, voice=voice, language=language),
                        timeout=timeout
                    )
                    if result and not result.get('error'):
                        return result
                except (asyncio.TimeoutError, Exception):
                    continue
                    
        raise RuntimeError("No TTS providers configured")

    async def reason(self, prompt: str, model: str | None, temperature: float):
        return {"provider": "mock_reason", "text": "mock"}

    async def translate(self, text: str, target: str, source: str):
        return {"provider": "mock_translate", "text": text}

    def get_metrics(self) -> dict:
        return {}