"""Read-through proxy for Memory Fusion Hub.

Implements the MemoryFusionService gRPC interface and forwards requests to the
authoritative MFH while serving hot reads from an in-memory cache.

Environment variables:
- TARGET_MFH_HOST: upstream MFH host (default: "mfh")
- TARGET_MFH_PORT: upstream MFH gRPC port (default: "5714")
- CACHE_TTL_SEC: cache TTL in seconds (default: "60")
- PROXY_GRPC_PORT: proxy gRPC port (default: "5715")
- PROXY_METRICS_PORT: Prometheus metrics port (default: "8082")
"""

from __future__ import annotations

import asyncio
# import json
import os
import time
from dataclasses import dataclass
from typing import Dict, Optional, List, Any

import grpc
from grpc import aio
from prometheus_client import Counter, Gauge, start_http_server
from grpc_reflection.v1alpha import reflection

try:
    # When executed within the memory_fusion_hub package
    from ..memory_fusion_pb2 import (  # type: ignore
        GetRequest, GetResponse, PutRequest, PutResponse, DeleteRequest, DeleteResponse,
        BatchGetRequest, BatchGetResponse, ExistsRequest, ExistsResponse,
        ListKeysRequest, ListKeysResponse, HealthRequest, HealthResponse,
        MemoryItem as ProtoMemoryItem, ComponentHealth,
    )
    from ..memory_fusion_pb2_grpc import MemoryFusionServiceServicer, add_MemoryFusionServiceServicer_to_server, MemoryFusionServiceStub  # type: ignore
except Exception:  # pragma: no cover - fallback
    # Fallback if running standalone: add package dir to sys.path so generated modules
    # can be imported as top-level (they use absolute imports)
    import sys
    import os as _os
    sys.path.append(_os.path.dirname(_os.path.dirname(__file__)))
    from memory_fusion_pb2 import (  # type: ignore
        GetRequest, GetResponse, PutRequest, PutResponse, DeleteRequest, DeleteResponse,
        BatchGetRequest, BatchGetResponse, ExistsRequest, ExistsResponse,
        ListKeysRequest, ListKeysResponse, HealthRequest, HealthResponse,
        MemoryItem as ProtoMemoryItem, ComponentHealth,
    )
    from memory_fusion_pb2_grpc import MemoryFusionServiceServicer, add_MemoryFusionServiceServicer_to_server, MemoryFusionServiceStub  # type: ignore


# ------------------------------
# Metrics
# ------------------------------
HITS = Counter("mfh_proxy_cache_hits_total", "Cache hits", ["method"])
MISSES = Counter("mfh_proxy_cache_misses_total", "Cache misses", ["method"])
CACHE_SIZE = Gauge("mfh_proxy_cache_size", "Number of items in cache")


@dataclass
class CacheEntry:
    expires_at_ms: int
    item: ProtoMemoryItem


class ReadThroughCache:
    def __init__(self, ttl_seconds: int):
        self._ttl_ms = max(1, int(ttl_seconds)) * 1000
        self._store: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    async def get(self, key: str) -> Optional[ProtoMemoryItem]:
        async with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            if entry.expires_at_ms <= self._now_ms():
                self._store.pop(key, None)
                CACHE_SIZE.set(len(self._store))
                return None
            return entry.item

    async def put(self, key: str, item: ProtoMemoryItem) -> None:
        async with self._lock:
            self._store[key] = CacheEntry(self._now_ms() + self._ttl_ms, item)
            CACHE_SIZE.set(len(self._store))

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)
            CACHE_SIZE.set(len(self._store))


class MFHProxyServicer(MemoryFusionServiceServicer):  # type: ignore[misc]
    def __init__(self, upstream_addr: str, cache_ttl_sec: int = 60):
        self._upstream_addr = upstream_addr
        self._channel = grpc.insecure_channel(upstream_addr)
        self._stub = MemoryFusionServiceStub(self._channel)
        self._cache = ReadThroughCache(cache_ttl_sec)

    # --------------- RPCs ---------------
    async def Get(self, request: Any, context: aio.ServicerContext) -> GetResponse:  # type: ignore[override]
        key = request.key
        cached = await self._cache.get(key)
        if cached is not None:
            HITS.labels(method="Get").inc()
            resp = GetResponse(found=True)
            resp.item.CopyFrom(cached)
            return resp

        MISSES.labels(method="Get").inc()
        # Upstream fetch
        upstream = self._stub.Get(request)
        # self._stub is sync; call in thread executor to avoid blocking loop
        loop = asyncio.get_running_loop()
        upstream_resp: GetResponse = await loop.run_in_executor(None, upstream)
        if upstream_resp.found and upstream_resp.item.key:
            await self._cache.put(upstream_resp.item.key, upstream_resp.item)
        return upstream_resp

    async def Put(self, request: Any, context: aio.ServicerContext) -> PutResponse:  # type: ignore[override]
        # Forward write
        loop = asyncio.get_running_loop()
        upstream = self._stub.Put(request)
        upstream_resp: PutResponse = await loop.run_in_executor(None, upstream)
        if upstream_resp.success and request.key:
            # Update local cache with new value
            await self._cache.put(request.key, request.item)
        return upstream_resp

    async def Delete(self, request: Any, context: aio.ServicerContext) -> DeleteResponse:  # type: ignore[override]
        loop = asyncio.get_running_loop()
        upstream = self._stub.Delete(request)
        upstream_resp: DeleteResponse = await loop.run_in_executor(None, upstream)
        await self._cache.delete(request.key)
        return upstream_resp

    async def BatchGet(self, request: Any, context: aio.ServicerContext) -> BatchGetResponse:  # type: ignore[override]
        loop = asyncio.get_running_loop()
        response = BatchGetResponse()
        missing: List[str] = []

        # Serve hits from cache
        for key in request.keys:
            cached = await self._cache.get(key)
            if cached is not None:
                HITS.labels(method="BatchGet").inc()
                response.items[key].CopyFrom(cached)
            else:
                MISSES.labels(method="BatchGet").inc()
                missing.append(key)

        # Fetch misses from upstream
        if missing:
            upstream_req = BatchGetRequest(keys=missing, agent_id=request.agent_id)
            upstream_call = self._stub.BatchGet(upstream_req)
            upstream_resp: BatchGetResponse = await loop.run_in_executor(None, upstream_call)
            # merge
            for key, item in upstream_resp.items.items():
                response.items[key].CopyFrom(item)
                await self._cache.put(key, item)
            for key in upstream_resp.missing_keys:
                response.missing_keys.append(key)

        return response

    async def Exists(self, request: Any, context: aio.ServicerContext) -> ExistsResponse:  # type: ignore[override]
        cached = await self._cache.get(request.key)
        if cached is not None:
            HITS.labels(method="Exists").inc()
            return ExistsResponse(exists=True)
        MISSES.labels(method="Exists").inc()
        loop = asyncio.get_running_loop()
        upstream = self._stub.Exists(request)
        return await loop.run_in_executor(None, upstream)

    async def ListKeys(self, request: Any, context: aio.ServicerContext) -> ListKeysResponse:  # type: ignore[override]
        # Always forward for authoritative listing
        loop = asyncio.get_running_loop()
        upstream = self._stub.ListKeys(request)
        return await loop.run_in_executor(None, upstream)

    async def GetHealth(self, request: Any, context: aio.ServicerContext) -> HealthResponse:  # type: ignore[override]
        loop = asyncio.get_running_loop()
        upstream = self._stub.GetHealth(request)
        resp: HealthResponse = await loop.run_in_executor(None, upstream)
        # add proxy component
        proxy_component = ComponentHealth()
        proxy_component.healthy = True
        proxy_component.info["cache_items"] = str(int(CACHE_SIZE._value.get()))
        proxy_component.info["upstream"] = self._upstream_addr
        resp.components["proxy"].CopyFrom(proxy_component)
        return resp


class MFHProxyServer:
    def __init__(self, grpc_port: int, upstream_addr: str, cache_ttl_sec: int, metrics_port: int):
        self._grpc_port = grpc_port
        self._upstream_addr = upstream_addr
        self._cache_ttl_sec = cache_ttl_sec
        self._metrics_port = metrics_port
        self._server: Optional[aio.Server] = None

    async def start(self) -> None:
        # Start metrics server
        start_http_server(self._metrics_port)
        self._server = aio.server()
        servicer = MFHProxyServicer(self._upstream_addr, self._cache_ttl_sec)
        add_MemoryFusionServiceServicer_to_server(servicer, self._server)  # type: ignore[no-untyped-call]

        # Enable reflection for grpcurl/introspection
        service_names = (
            'memory_fusion.MemoryFusionService',
            reflection.SERVICE_NAME,
        )
        reflection.enable_server_reflection(service_names, self._server)
        self._server.add_insecure_port(f"[::]:{self._grpc_port}")
        await self._server.start()

    async def serve(self) -> None:
        await self.start()
        assert self._server is not None
        await self._server.wait_for_termination()

    async def stop(self, grace: int = 3) -> None:
        if self._server:
            await self._server.stop(grace)


async def run_proxy_from_env() -> None:
    target_host = os.environ.get("TARGET_MFH_HOST", "mfh")
    target_port = int(os.environ.get("TARGET_MFH_PORT", "5714"))
    upstream_addr = f"{target_host}:{target_port}"
    cache_ttl_sec = int(os.environ.get("CACHE_TTL_SEC", "60"))
    grpc_port = int(os.environ.get("PROXY_GRPC_PORT", "5715"))
    metrics_port = int(os.environ.get("PROXY_METRICS_PORT", "8082"))

    server = MFHProxyServer(grpc_port, upstream_addr, cache_ttl_sec, metrics_port)
    try:
        await server.serve()
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(run_proxy_from_env())
