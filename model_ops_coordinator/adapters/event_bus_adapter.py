#!/usr/bin/env python3
"""
EventBusAdapter
- Primary: NATS JetStream (if NATS_URL is set and connection succeeds)
- Fallback: In-process asyncio queues (subject → Queue)

Interface:
- await start()
- await publish(subject: str, data: bytes)
- await subscribe(subject: str, cb: Callable[[bytes], Awaitable[None]])
"""
import asyncio
import os
from typing import Awaitable, Callable, Dict


class EventBusAdapter:
    def __init__(self) -> None:
        self._use_nats: bool = False
        self._nats = None  # type: ignore
        self._js = None  # JetStream context
        self._subs = []
        self._queues: Dict[str, asyncio.Queue] = {}
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        nats_url = os.getenv("NATS_URL")
        if nats_url:
            try:
                from nats.aio.client import Client as NATS  # type: ignore
                self._nats = NATS()
                await self._nats.connect(servers=[nats_url])
                self._js = self._nats.jetstream()
                # Ensure streams exist (idempotent if they already do)
                try:
                    await self._js.add_stream(name="MODELS", subjects=["models.*"])  # type: ignore
                except Exception:
                    pass
                try:
                    await self._js.add_stream(name="MEMORY", subjects=["memory.*"])  # type: ignore
                except Exception:
                    pass
                self._use_nats = True
            except Exception:
                # Fallback to in-proc
                self._use_nats = False
        self._started = True

    async def publish(self, subject: str, data: bytes) -> None:
        if not self._started:
            await self.start()
        if self._use_nats and self._js is not None:
            await self._js.publish(subject, data)  # type: ignore
        else:
            q = self._queues.setdefault(subject, asyncio.Queue(maxsize=10000))
            await q.put(data)

    async def subscribe(self, subject: str, cb: Callable[[bytes], Awaitable[None]]) -> None:
        if not self._started:
            await self.start()
        if self._use_nats and self._js is not None and self._nats is not None:
            async def _handler(msg):  # type: ignore
                await cb(msg.data)
            sub = await self._js.subscribe(subject, cb=_handler, durable=f"dur-{subject.replace('.', '-')}")  # type: ignore
            self._subs.append(sub)
        else:
            q = self._queues.setdefault(subject, asyncio.Queue(maxsize=10000))
            async def _pump():
                while True:
                    data = await q.get()
                    await cb(data)
            asyncio.create_task(_pump())