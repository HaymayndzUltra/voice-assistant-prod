from __future__ import annotations

"""Policy loader for HybridModule.
Parses hybrid_policy.yaml and validates minimal required keys.
"""
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel, Field, ValidationError, conlist


class ProviderConfig(BaseModel):
    name: str
    model: Optional[str] = None
    voice: Optional[str] = None
    model_path: Optional[str] = None

class STTServiceConfig(BaseModel):
    strategy: str = Field(..., regex="^(local_first|cloud_first)$")
    providers: Dict[str, conlist(ProviderConfig, min_items=1)]
    fallback_criteria: Dict[str, Any]

class TTSServiceConfig(BaseModel):
    strategy: str = Field(..., regex="^(local_first|cloud_first)$")
    providers: Dict[str, conlist(ProviderConfig, min_items=1)]
    per_call_timeout_ms: int

class HybridPolicy(BaseModel):
    version: int
    services: Dict[str, Any]

    def stt_config(self) -> STTServiceConfig:
        return STTServiceConfig(**self.services.get("stt", {}))

    def tts_config(self) -> TTSServiceConfig:
        return TTSServiceConfig(**self.services.get("tts", {}))


class PolicyLoader:
    """Load and validate hybrid policy YAML."""

    def __init__(self, cfg_path: Optional[Path]):
        if cfg_path is None:
            cfg_path = Path(__file__).resolve().parent.parent.parent / "config" / "hybrid_policy.yaml"
        self.cfg_path = cfg_path

    def load(self) -> HybridPolicy:
        if not self.cfg_path.exists():
            raise FileNotFoundError(f"hybrid_policy.yaml not found: {self.cfg_path}")
        data = yaml.safe_load(self.cfg_path.read_text())
        try:
            return HybridPolicy(**data)
        except ValidationError as exc:
            raise RuntimeError(f"Invalid hybrid_policy.yaml: {exc}")