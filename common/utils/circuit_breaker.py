"""Reusable Circuit Breaker utility.

Exposes a minimal thread-safe implementation used across the code-base.  All legacy
per-agent copies should import this instead of redefining their own.
"""
from __future__ import annotations

import logging
import threading
import time

__all__ = ["CircuitBreaker"]

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Simple thread-safe circuit-breaker.

    Parameters
    ----------
    name: str
        Identifier of the protected dependency (service name).
    failure_threshold: int, default 3
        Consecutive failures required to *trip* the breaker.
    reset_timeout: int, default 30
        Seconds after which the breaker moves from *OPEN* to *HALF_OPEN*.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(self, name: str, *, failure_threshold: int = 3, reset_timeout: int = 30) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.state = self.CLOSED
        self.failure_count = 0
        self.last_failure_time: float = 0.0
        self._lock = threading.Lock()
        logger.debug("CircuitBreaker(%s) initialised (threshold=%s, timeout=%ss)", name, failure_threshold, reset_timeout)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def allow_request(self) -> bool:
        """Return *True* if the protected call should be attempted."""
        with self._lock:
            if self.state == self.OPEN:
                if time.time() - self.last_failure_time > self.reset_timeout:
                    logger.info("CircuitBreaker[%s]: timeout elapsed – switching to HALF_OPEN", self.name)
                    self.state = self.HALF_OPEN
                    return True
                return False
            return True

    def record_success(self) -> None:
        """Call after a successful request."""
        with self._lock:
            self.failure_count = 0
            if self.state in (self.HALF_OPEN, self.OPEN):
                logger.info("CircuitBreaker[%s]: SUCCESS – back to CLOSED", self.name)
            self.state = self.CLOSED

    def record_failure(self) -> None:
        """Call after a failed request/exception."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.state == self.HALF_OPEN or self.failure_count >= self.failure_threshold:
                if self.state != self.OPEN:
                    logger.warning("CircuitBreaker[%s]: TRIPPED – moving to OPEN", self.name)
                self.state = self.OPEN

    # ------------------------------------------------------------------
    # Debug helpers
    # ------------------------------------------------------------------
    def __repr__(self) -> str:  # pragma: no cover
        return f"<CircuitBreaker name={self.name!r} state={self.state} failures={self.failure_count}>"