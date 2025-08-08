import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator


class Bulkhead:
    def __init__(self, max_concurrent: int = 64, max_queue_size: int = 256) -> None:
        self._sem = asyncio.Semaphore(max_concurrent)
        self._queue = asyncio.Queue(maxsize=max_queue_size)

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[None]:
        await self._queue.put(object())
        try:
            await self._sem.acquire()
            try:
                yield
            finally:
                self._sem.release()
        finally:
            self._queue.get_nowait()
            self._queue.task_done()