"""Provider adapter placeholders."""

from typing import Any, Dict

class BaseProvider:
    async def call(self, *args, **kwargs) -> Any: ...

def build_provider(name: str):
    # Dynamic import map
    name_lower = name.lower()
    if name_lower.startswith("openai"):
        try:
            from .openai_provider import OpenAIProvider
            return OpenAIProvider(name)
        except Exception:
            pass  # fallthrough
    elif name_lower.startswith("google"):
        try:
            from .google_provider import GoogleProvider
            return GoogleProvider(name)
        except Exception:
            pass
    elif "whisper" in name_lower:
        try:
            from .local_whisper import LocalWhisperProvider
            return LocalWhisperProvider(name)
        except Exception:
            pass

    # default
    from .mock_provider import MockProvider
    return MockProvider(name)