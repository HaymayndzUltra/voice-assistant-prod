import asyncio
import uuid
from typing import Optional

from unified_observability_center.bus.nats_client import NatsClient

try:
    from nats.js.kv import KeyValueConfig
except Exception:  # pragma: no cover
    KeyValueConfig = None  # type: ignore


class LeaderElector:
    def __init__(self, nats_url: str, cluster_name: str, ttl_seconds: int = 10) -> None:
        self._nats_url = nats_url
        self._cluster = cluster_name
        self._ttl = ttl_seconds
        self._nc: Optional[NatsClient] = None
        self._leader: bool = False
        self._instance_id = str(uuid.uuid4())
        self._task: Optional[asyncio.Task] = None
        self._stopped = asyncio.Event()
        self._bucket = f"uoc_leader_{cluster_name}"

    async def start(self) -> None:
        self._nc = NatsClient(self._nats_url)
        await self._nc.connect()
        self._stopped.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stopped.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._nc:
            await self._nc.close()
            self._nc = None
        self._leader = False

    def is_leader(self) -> bool:
        return self._leader

    async def _run(self) -> None:
        assert self._nc is not None
        js = self._nc.jetstream()
        kv = None
        try:
            # Try to access or create KV bucket
            if KeyValueConfig is not None:
                try:
                    kv = await js.key_value(self._bucket)
                except Exception:
                    kv = await js.create_key_value(KeyValueConfig(bucket=self._bucket, history=1))
            else:
                kv = await js.key_value(self._bucket)
        except Exception:
            # If KV not available, become leader by default
            self._leader = True
            while not self._stopped.is_set():
                await asyncio.sleep(self._ttl)
            return

        # Election loop
        while not self._stopped.is_set():
            try:
                if not self._leader:
                    # Try to acquire by create-if-not-exists
                    try:
                        await kv.create("leader", self._instance_id.encode())
                        self._leader = True
                    except Exception:
                        self._leader = False
                else:
                    # Refresh leadership by updating value
                    try:
                        await kv.put("leader", self._instance_id.encode())
                        self._leader = True
                    except Exception:
                        # Lost leadership
                        self._leader = False
            except Exception:
                # ignore transient errors
                pass
            await asyncio.sleep(max(1, self._ttl // 2))