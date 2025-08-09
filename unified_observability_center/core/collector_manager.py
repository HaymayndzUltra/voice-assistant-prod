import asyncio
import importlib
from typing import Dict, List


class CollectorManager:
    def __init__(self, enabled_collectors: List[str]) -> None:
        self.enabled_collectors = enabled_collectors
        self._tasks: Dict[str, asyncio.Task] = {}

    async def start_all(self) -> None:
        for name in self.enabled_collectors:
            mod = importlib.import_module(f"unified_observability_center.plugins.{name}")
            if not hasattr(mod, "run_collector"):
                continue
            task = asyncio.create_task(mod.run_collector())
            self._tasks[name] = task

    async def stop_all(self) -> None:
        for name, task in list(self._tasks.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            finally:
                self._tasks.pop(name, None)