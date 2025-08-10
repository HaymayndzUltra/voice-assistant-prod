"""Mock provider that returns canned responses for testing."""
import asyncio
from typing import Any

class MockProvider:
    def __init__(self, name: str):
        self.name = name

    async def call(self, *args, **kwargs) -> Any:
        await asyncio.sleep(0.01)
        return {
            "provider": self.name,
            "result": "mock-result",
            "confidence": 0.9
        }