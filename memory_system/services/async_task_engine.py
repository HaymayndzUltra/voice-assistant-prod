"""Async Task Engine

Executes multiple tasks concurrently using asyncio + thread pool, leveraging the
existing `execute_task_intelligently` blocking API.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, List, Dict

from memory_system.services.telemetry import emit
from workflow_memory_intelligence import execute_task_intelligently

__all__ = ["AsyncTaskEngine"]


class AsyncTaskEngine:
    """Simple asyncio-based engine to run tasks in parallel."""

    def __init__(self, max_workers: int = 5):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="mem-task")

    async def _run_one(self, task_description: str) -> Dict[str, Any]:
        """Run a single task in the executor and capture telemetry."""
        loop = asyncio.get_running_loop()
        emit("task_start", description=task_description[:80])
        result = await loop.run_in_executor(self._executor, execute_task_intelligently, task_description)
        emit("task_end", description=task_description[:80], status=result.get("status"))
        return result

    async def execute_many(self, task_descriptions: List[str]) -> List[Dict[str, Any]]:
        """Execute a batch of tasks concurrently and return their results."""
        tasks = [asyncio.create_task(self._run_one(desc)) for desc in task_descriptions]
        return await asyncio.gather(*tasks)

    async def execute_one(self, task_description: str) -> Dict[str, Any]:
        """Shorthand for executing a single task asynchronously."""
        return await self._run_one(task_description)


# Convenience helper for CLI scripts

def run_tasks_concurrently(task_descriptions: List[str], max_workers: int = 5):
    """Blocking helper that runs tasks concurrently via asyncio.run()."""
    engine = AsyncTaskEngine(max_workers=max_workers)
    return asyncio.run(engine.execute_many(task_descriptions))