import asyncio
import json
from typing import Optional

from unified_observability_center.bus.nats_client import NatsClient
from unified_observability_center.bus import topics
from unified_observability_center.core.schemas import Action


class HealingEngine:
    def __init__(self, nats_url: str) -> None:
        self._nats_url = nats_url
        self._nc: Optional[NatsClient] = None
        self._sub = None

    async def start(self) -> None:
        self._nc = NatsClient(self._nats_url)
        await self._nc.connect()

        async def on_alert(msg):
            # For now, echo a mock action
            action = Action(name="noop")
            await self._nc.publish(topics.ACTIONS, json.dumps(action.dict()).encode())

        self._sub = await self._nc.subscribe(topics.ALERTS, cb=on_alert)

    async def stop(self) -> None:
        if self._nc:
            await self._nc.close()
            self._nc = None