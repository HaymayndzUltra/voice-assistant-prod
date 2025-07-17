# Re-exported from original main_pc_code/agents/error_publisher.py to provide a
# single import path (common.utils.error_publisher.ErrorPublisher).

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Optional

import zmq

__all__ = ["ErrorPublisher"]

logger = logging.getLogger(__name__)


class ErrorPublisher:  # noqa: D101
    def __init__(self, source: str, *, endpoint: Optional[str] = None, context: Optional[zmq.Context] = None) -> None:
        self.source = source
        self.endpoint = endpoint or self._build_default_endpoint()
        self._ctx_provided = context is not None
        self.context = context or zmq.Context.instance()
        try:
            self.socket = self.context.socket(zmq.PUB)
            self.socket.connect(self.endpoint)
        except Exception as exc:  # pragma: no cover
            logger.error("ErrorPublisher: failed to set up PUB socket: %s", exc)
            self.socket = None  # type: ignore

    # ---------------------------------------------
    def publish_error(
        self,
        *,
        error_type: str,
        severity: str = "error",
        details: Any = None,
        message_type: str = "error_report",
    ) -> None:
        if self.socket is None:
            return
        payload = {
            "message_type": message_type,
            "source": self.source,
            "timestamp": datetime.utcnow().isoformat(),
            "error_data": {
                "error_id": str(uuid.uuid4()),
                "error_type": error_type,
                "severity": severity,
                "details": details,
            },
        }
        try:
            self.socket.send_string(f"ERROR:{json.dumps(payload)}")
        except Exception as exc:  # pragma: no cover
            logger.error("ErrorPublisher: failed to send error: %s", exc)

    # ---------------------------------------------
    def close(self) -> None:
        if self.socket is not None:
            try:
                self.socket.close(linger=0)
            except Exception:
                pass
        if not self._ctx_provided and getattr(self, "context", None) is not None:
            try:
                self.context.term()
            except Exception:
                pass

    # ---------------------------------------------
    @staticmethod
    def _build_default_endpoint() -> str:
        host = os.environ.get("ERROR_BUS_HOST") or os.environ.get("PC2_IP", "localhost")
        port = int(os.environ.get("ERROR_BUS_PORT", 7150))
        return f"tcp://{host}:{port}"

    # Context manager helpers -------------------------------------------------
    def __enter__(self):  # noqa: D401
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # noqa: D401, D403
        self.close()