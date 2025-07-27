# remote_api_adapter/adapter.py
"""Hybrid LLM Remote API Adapter

Unifies calls to external LLM endpoints (OpenAI, AWS Bedrock) and provides
consistent generate, embed, and translate interfaces.  Includes a basic
fail-over to local TinyLlamaServiceEnhanced when the remote request fails or
times out (>5s).
"""
from __future__ import annotations

import os
import time
from typing import List, Sequence

try:
    import openai  # type: ignore
except ImportError:  # pragma: no cover
    openai = None

try:
    import boto3  # type: ignore
except ImportError:  # pragma: no cover
    boto3 = None

# Local fallback (lazy import to avoid heavy deps if unused)
_LOCAL_MODEL: "TinyLlamaServiceEnhanced | None" = None

_TIMEOUT_SEC = float(os.getenv("REMOTE_API_TIMEOUT", "5"))

class RemoteApiAdapter:
    """Adapter exposing generate, embed, translate methods."""

    def __init__(self, provider: str = "openai") -> None:
        self.provider = provider.lower()
        if self.provider == "openai":
            if openai is None:
                raise ImportError("openai package not available")
            openai.api_key = os.getenv("OPENAI_API_KEY")
        elif self.provider in {"bedrock", "aws"}:
            if boto3 is None:
                raise ImportError("boto3 package not available for Bedrock usage")
            self._bedrock = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def generate(self, prompt: str, model: str = "gpt-4o", max_tokens: int = 4096) -> str:
        """LLM text generation with automatic fallback."""
        try:
            if self.provider == "openai":
                return self._openai_chat(prompt, model=model, max_tokens=max_tokens)
            return self._bedrock_chat(prompt, model=model, max_tokens=max_tokens)
        except Exception as exc:  # pragma: no cover
            return self._local_fallback_generate(prompt, str(exc))

    def embed(self, texts: Sequence[str], model: str = "text-embedding-3-small") -> List[List[float]]:
        """Get embeddings list for a batch of texts."""
        try:
            if self.provider == "openai":
                rsp = openai.Embedding.create(input=texts, model=model)
                return [d["embedding"] for d in rsp["data"]]
            body = {"texts": texts, "model": model}
            rsp = self._bedrock.invoke_model(body=body, modelId=model)
            return rsp["body"]["embeddings"]
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"Embed failed: {exc}") from exc

    def translate(self, text: str, target_lang: str, model: str | None = None) -> str:
        """Translation via remote NLLB (Bedrock) or GPT."""
        model = model or ("nllb-200-distilled-1.3B" if self.provider != "openai" else "gpt-3.5-turbo")
        prompt = f"Translate the following text to {target_lang}:\n\n{text}"
        return self.generate(prompt, model=model, max_tokens=2048)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _openai_chat(self, prompt: str, *, model: str, max_tokens: int) -> str:
        start = time.time()
        rsp = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            request_timeout=_TIMEOUT_SEC,
        )
        return rsp.choices[0].message.content

    def _bedrock_chat(self, prompt: str, *, model: str, max_tokens: int) -> str:
        body = {"prompt": prompt, "maxTokens": max_tokens}
        rsp = self._bedrock.invoke_model(body=body, modelId=model, timeout=_TIMEOUT_SEC)
        return rsp["body"].decode()

    # --------------------
    # Local Fallback Logic
    # --------------------
    def _local_fallback_generate(self, prompt: str, reason: str) -> str:
        global _LOCAL_MODEL
        if _LOCAL_MODEL is None:
            try:
                from main_pc_code.agents.tiny_llama_service_enhanced import TinyLlamaServiceEnhanced  # type: ignore

                _LOCAL_MODEL = TinyLlamaServiceEnhanced()
            except Exception:
                raise RuntimeError(f"Remote call failed: {reason} and local fallback unavailable")
        return _LOCAL_MODEL.generate(prompt)


def health_check() -> bool:
    """Simple health check used by Docker."""
    try:
        adapter = RemoteApiAdapter()
        _ = adapter.generate("ping", model="gpt-3.5-turbo", max_tokens=1)
        return True
    except Exception:
        return False