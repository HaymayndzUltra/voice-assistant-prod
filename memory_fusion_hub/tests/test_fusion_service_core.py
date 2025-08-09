import asyncio
import pytest
from typing import Optional, Dict
from unittest.mock import AsyncMock, patch

from memory_fusion_hub.core.models import (
    MemoryItem,
    FusionConfig,
    ServerConfig,
    StorageConfig,
    ReplicationConfig,
)
from memory_fusion_hub.core.fusion_service import FusionService


class InMemoryRepo:
    def __init__(self) -> None:
        self.store: Dict[str, MemoryItem] = {}

    async def initialize(self) -> None:
        return None

    async def get(self, key: str) -> Optional[MemoryItem]:
        return self.store.get(key)

    async def put(self, key: str, value: MemoryItem) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self.store

    async def list_keys(self, prefix: str = "", limit: int = 100):
        return [k for k in self.store.keys() if k.startswith(prefix)][:limit]

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_fusion_service_basic_crud(monkeypatch: pytest.MonkeyPatch) -> None:
    # Build config
    cfg = FusionConfig(
        title="test",
        server=ServerConfig(zmq_port=0, grpc_port=0, max_workers=1),
        storage=StorageConfig(sqlite_path=":memory:", redis_url="redis://localhost:6379/0"),
        replication=ReplicationConfig(enabled=False),
    )

    # Patch repository factory and cache/event log
    fake_repo = InMemoryRepo()
    monkeypatch.setattr("memory_fusion_hub.core.repository.build_repo", lambda _cfg: fake_repo)

    # Stub RedisCache methods to no-op
    with patch("memory_fusion_hub.core.fusion_service.RedisCache") as MockCache:
        cache = MockCache.return_value
        cache.__aenter__.return_value = cache
        cache.__aexit__.return_value = None
        cache.health_check = AsyncMock(return_value=True)
        cache.get = AsyncMock(return_value=None)
        cache.put = AsyncMock(return_value=None)
        cache.evict = AsyncMock(return_value=True)
        cache.exists = AsyncMock(return_value=False)
        cache.get_cache_info = AsyncMock(return_value={"clients": 1})

        # Stub EventLog to avoid Redis/NATS
        with patch("memory_fusion_hub.core.fusion_service.EventLog") as MockEventLog:
            ev = MockEventLog.return_value
            ev.initialize = AsyncMock(return_value=None)
            ev.publish = AsyncMock(return_value="evt_1")
            ev.get_stream_info = AsyncMock(return_value={"length": 0})
            ev.close = AsyncMock(return_value=None)

            svc = FusionService(cfg)
            await svc.initialize()

            item = MemoryItem(key="k1", content={"v": 1})
            await svc.put("k1", item, agent_id="agentX")

            got = await svc.get("k1")
            assert isinstance(got, MemoryItem)
            assert got.key == "k1"

            assert await svc.exists("k1") is True

            keys = await svc.list_keys(prefix="k")
            assert "k1" in keys

            batch = await svc.batch_get(["k1", "k2"])
            assert batch["k1"] is not None and batch["k2"] is None

            deleted = await svc.delete("k1")
            assert deleted is True
            assert await svc.exists("k1") is False

            health = await svc.get_health_status()
            assert health.get("service") == "Memory Fusion Hub"
            assert "components" in health

            await svc.close()