import asyncio
import json
from typing import Optional

from unified_observability_center.bus.nats_client import NatsClient
from unified_observability_center.bus import topics
from unified_observability_center.core.schemas import Alert


class AlertEngine:
    def __init__(self, nats_url: str, evaluation_interval_seconds: int = 30) -> None:
        self._nats_url = nats_url
        self._interval = evaluation_interval_seconds
        self._nc: Optional[NatsClient] = None
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        self._nc = NatsClient(self._nats_url)
        await self._nc.connect()
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._nc:
            await self._nc.close()

    async def _run_loop(self) -> None:
        while True:
            alert = Alert(rule_name="uoc.alive", severity="info", message="UOC alert engine heartbeat")
            await self._nc.publish(topics.ALERTS, json.dumps(alert.dict()).encode())
            await asyncio.sleep(self._interval)