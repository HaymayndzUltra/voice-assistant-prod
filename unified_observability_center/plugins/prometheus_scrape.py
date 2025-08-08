import asyncio
import json
import time
from typing import Dict

from unified_observability_center.bus.nats_client import NatsClient
from unified_observability_center.bus import topics


async def run_collector() -> None:
    nc = NatsClient(url="nats://nats:4222")
    await nc.connect()
    try:
        while True:
            payload: Dict[str, str] = {
                "name": "uoc_heartbeat",
                "value": "1",
                "timestamp_unix": str(time.time()),
            }
            await nc.publish(topics.METRICS, json.dumps(payload).encode())
            await asyncio.sleep(15)
    finally:
        await nc.close()