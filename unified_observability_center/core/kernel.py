import asyncio
from typing import Optional

import yaml

from unified_observability_center.bus.nats_client import NatsClient
from unified_observability_center.core.collector_manager import CollectorManager
from unified_observability_center.core.alert_engine import AlertEngine
from unified_observability_center.core.healing_engine import HealingEngine


class Kernel:
    def __init__(self, config_path: str) -> None:
        with open(config_path, "r") as f:
            self.cfg = yaml.safe_load(f)
        nats_url = self.cfg["nats"]["url"]
        self._nats_url = nats_url
        enabled = self.cfg.get("collectors", {}).get("enabled", [])
        self._collector_mgr = CollectorManager(enabled)
        interval = self.cfg.get("alerting", {}).get("evaluation_interval_seconds", 30)
        self._alert_engine = AlertEngine(nats_url=nats_url, evaluation_interval_seconds=interval)
        self._healing_engine = HealingEngine(nats_url=nats_url)

    async def start(self) -> None:
        await self._collector_mgr.start_all()
        await self._alert_engine.start()
        await self._healing_engine.start()

    async def stop(self) -> None:
        await self._collector_mgr.stop_all()
        await self._alert_engine.stop()
        await self._healing_engine.stop()