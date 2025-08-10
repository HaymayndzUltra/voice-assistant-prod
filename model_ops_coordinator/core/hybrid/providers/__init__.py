"""Provider adapter placeholders."""

from typing import Any, Dict

class BaseProvider:
    async def call(self, *args, **kwargs) -> Any: ...

def build_provider(name: str):
    from .mock_provider import MockProvider
    return MockProvider(name)