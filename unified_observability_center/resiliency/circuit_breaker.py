import asyncio
import time
from typing import Callable, Optional, TypeVar, Awaitable

T = TypeVar("T")


class CircuitBreakerOpenError(Exception):
    pass


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout_seconds: float = 15.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        self._fail_count = 0
        self._state = "closed"  # closed | open | half_open
        self._opened_at: Optional[float] = None
        self._lock = asyncio.Lock()

    def _can_attempt(self) -> bool:
        if self._state == "closed":
            return True
        if self._state == "open":
            if self._opened_at is None:
                return False
            if (time.time() - self._opened_at) >= self.reset_timeout_seconds:
                self._state = "half_open"
                return True
            return False
        if self._state == "half_open":
            return True
        return False

    async def call(self, func: Callable[[], Awaitable[T]]) -> T:
        async with self._lock:
            if not self._can_attempt():
                raise CircuitBreakerOpenError("circuit open")

        try:
            result = await func()
        except Exception:
            async with self._lock:
                self._fail_count += 1
                if self._fail_count >= self.failure_threshold:
                    self._state = "open"
                    self._opened_at = time.time()
            raise

        async with self._lock:
            # success path
            self._fail_count = 0
            if self._state in ("open", "half_open"):
                self._state = "closed"
                self._opened_at = None
        return result