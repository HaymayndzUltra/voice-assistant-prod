import asyncio
from typing import Awaitable, Callable, Optional

import nats
from nats.aio.msg import Msg


class NatsClient:
    def __init__(self, url: str) -> None:
        self._url = url
        self._nc: Optional[nats.NATS] = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        async with self._lock:
            if self._nc is not None and self._nc.is_connected:
                return
            self._nc = await nats.connect(self._url)

    async def close(self) -> None:
        async with self._lock:
            if self._nc is not None:
                await self._nc.drain()
                await self._nc.close()
                self._nc = None

    async def publish(self, subject: str, data: bytes, reply: Optional[str] = None, headers: Optional[dict] = None) -> None:
        if self._nc is None:
            raise RuntimeError("NATS not connected")
        await self._nc.publish(subject, payload=data, reply=reply, headers=headers)

    async def subscribe(self, subject: str, cb: Callable[[Msg], Awaitable[None]], queue: Optional[str] = None):
        if self._nc is None:
            raise RuntimeError("NATS not connected")
        return await self._nc.subscribe(subject, queue, cb)

    def jetstream(self):
        if self._nc is None:
            raise RuntimeError("NATS not connected")
        return self._nc.jetstream()