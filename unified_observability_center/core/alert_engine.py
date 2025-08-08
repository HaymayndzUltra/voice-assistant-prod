import asyncio
import json
from typing import Optional

from unified_observability_center.bus.nats_client import NatsClient
from unified_observability_center.bus import topics
from unified_observability_center.core.schemas import Alert
from unified_observability_center.core.storage import StorageFacade
import glob
import yaml
from typing import Dict, Any, List


class AlertEngine:
    def __init__(self, nats_url: str, evaluation_interval_seconds: int = 30, rules_path: Optional[str] = None, storage: Optional[StorageFacade] = None) -> None:
        self._nats_url = nats_url
        self._interval = evaluation_interval_seconds
        self._nc: Optional[NatsClient] = None
        self._task: Optional[asyncio.Task] = None
        self._rules_path = rules_path
        self._storage = storage
        self._rules: List[Dict[str, Any]] = []

    async def start(self) -> None:
        self._nc = NatsClient(self._nats_url)
        await self._nc.connect()
        self._load_rules()
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
            # simple threshold rules: - rule: name, query, gt (threshold)
            if not self._rules or not self._storage:
                alert = Alert(rule_name="uoc.alive", severity="info", message="UOC alert engine heartbeat")
                await self._nc.publish(topics.ALERTS, json.dumps(alert.dict()).encode())
                await asyncio.sleep(self._interval)
                continue

            for rule in self._rules:
                try:
                    res = await self._storage.query_range(
                        promql=rule["query"],
                        start_unix=int(asyncio.get_event_loop().time()) - self._interval,
                        end_unix=int(asyncio.get_event_loop().time()),
                        step_seconds=max(1, self._interval // 3),
                    )
                    value = self._extract_last_value(res)
                    if value is None:
                        continue
                    if "gt" in rule and value > float(rule["gt"]):
                        alert = Alert(rule_name=rule.get("name", "rule"), severity="warning", message=f"{rule.get('name','rule')} breach: {value} > {rule['gt']}")
                        await self._nc.publish(topics.ALERTS, json.dumps(alert.dict()).encode())
                except Exception:
                    # swallow individual rule errors
                    continue
            await asyncio.sleep(self._interval)

    def _load_rules(self) -> None:
        if not self._rules_path:
            return
        paths = glob.glob(self._rules_path)
        rules: List[Dict[str, Any]] = []
        for p in paths:
            try:
                with open(p, "r") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, list):
                        rules.extend(data)
                    elif isinstance(data, dict):
                        rules.append(data)
            except Exception:
                continue
        self._rules = rules

    @staticmethod
    def _extract_last_value(resp: Dict[str, Any]) -> Optional[float]:
        try:
            result = resp["data"]["result"][0]["values"]
            if not result:
                return None
            _, v = result[-1]
            return float(v)
        except Exception:
            return None