
import yaml

from unified_observability_center.core.collector_manager import CollectorManager
from unified_observability_center.core.alert_engine import AlertEngine
from unified_observability_center.core.healing_engine import HealingEngine
from unified_observability_center.core.storage import StorageFacade


class Kernel:
    def __init__(self, config_path: str) -> None:
        with open(config_path, "r") as f:
            self.cfg = yaml.safe_load(f)
        nats_url = self.cfg["nats"]["url"]
        self._nats_url = nats_url
        enabled = self.cfg.get("collectors", {}).get("enabled", [])
        self._collector_mgr = CollectorManager(enabled)
        interval = self.cfg.get("alerting", {}).get("evaluation_interval_seconds", 30)
        rules_path = self.cfg.get("alerting", {}).get("rules_path")
        storage_cfg = self.cfg.get("storage", {})
        self._storage = StorageFacade(
            vm_url=storage_cfg.get("metrics", {}).get("url", "http://vmselect:8481"),
            loki_url=storage_cfg.get("logs", {}).get("url", "http://loki:3100"),
            circuit_failure_threshold=self.cfg.get("resilience", {}).get("circuit_breaker", {}).get("failure_threshold", 5),
            circuit_reset_timeout=float(self.cfg.get("resilience", {}).get("circuit_breaker", {}).get("reset_timeout", 15)),
        )
        self._alert_engine = AlertEngine(nats_url=nats_url, evaluation_interval_seconds=interval, rules_path=rules_path, storage=self._storage)
        self._healing_engine = HealingEngine(nats_url=nats_url)

    async def start(self) -> None:
        await self._collector_mgr.start_all()
        await self._alert_engine.start()
        await self._healing_engine.start()

    async def stop(self) -> None:
        await self._collector_mgr.stop_all()
        await self._alert_engine.stop()
        await self._healing_engine.stop()
        await self._storage.close()