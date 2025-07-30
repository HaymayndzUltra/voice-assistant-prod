from __future__ import annotations

"""AsyncRunner – thin asyncio wrapper around subprocess calls.

Example::

    result = await AsyncRunner().run(sys.executable, "queue_cli.py", "status")

Returns dict similar to *subprocess.CompletedProcess* for easy drop-in replacement.
"""
import asyncio
import sys
from dataclasses import dataclass
from typing import List


@dataclass
class RunResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:  # convenience
        return self.returncode == 0


class AsyncRunner:
    """Singleton helper to run subprocesses without blocking Tk loop."""

    _instance: "AsyncRunner | None" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loop = asyncio.get_event_loop()
        return cls._instance

    async def run(self, *cmd: str | bytes, timeout: int | None = None, cwd: str | None = None) -> RunResult:  # noqa: D401,E501
        """Run *cmd* asynchronously in executor, capture output."""

        def _blocking() -> RunResult:  # executed in thread executor
            import subprocess

            try:
                completed = subprocess.run(
                    cmd,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                return RunResult(completed.returncode, completed.stdout, completed.stderr)
            except subprocess.TimeoutExpired as exc:
                return RunResult(-1, exc.stdout or "", "Command timeout")
            except Exception as exc:  # pylint: disable=broad-except
                return RunResult(-1, "", str(exc))

        return await self._loop.run_in_executor(None, _blocking)