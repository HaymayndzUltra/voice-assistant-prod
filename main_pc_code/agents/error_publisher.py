from __future__ import annotations
from common.core.base_agent import BaseAgent
"""Utility class for standardized error-bus publishing.

All agents should use `ErrorPublisher` (instantiated once, ideally in `__init__`) and call
`publish_error()` whenever a critical or noteworthy error occurs. This sends a JSON message
matching the system-wide standard to the central error-bus (ZMQ PUB/SUB).
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Optional

from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
from common.env_helpers import get_env


class ErrorPublisher:
    """Lightweight wrapper around a ZMQ PUB socket that publishes error reports.

    Parameters
    ----------
    source : str
        Human-readable name of the agent/service publishing the error.
    endpoint : Optional[str]
        Full ZMQ endpoint (e.g. ``tcp://host:port``).  If *None*, it is constructed
        from environment variables ``ERROR_BUS_HOST`` / ``PC2_IP`` and
        ``ERROR_BUS_PORT`` (default ``7150``).
    context : Optional[zmq.Context]
        Existing ZMQ context.  If *None*, the global instance is used.
    """

    def __init__(self, source: str, *, endpoint: Optional[str] = None, context: Optional[zmq.Context] = None) -> None:
        self.source = source
        self.endpoint = endpoint or self._build_default_endpoint()
        self._ctx_provided = context is not None
        self.context = context or zmq.Context.instance()

        try:
            self.socket = get_pub_socket(self.endpoint).socket
            # PUB sockets must *connect* to the central SUB (collector) or vice-versa.
            # We assume collector is a SUB‐binding central bus; agents therefore connect.
            self.socket.connect(self.endpoint)
        except Exception as exc:  # pragma: no cover – initialisation issues
            logging.error("ErrorPublisher: failed to set up PUB socket: %s", exc)
            # Degrade gracefully: create a dummy no-op publisher
            self.socket = None  # type: ignore

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------
    def publish_error(
        self,
        *,
        error_type: str,
        severity: str = "error",
        details: Any = None,
        message_type: str = "error_report",
    ) -> None:
        """Publish an error on the bus.

        Parameters
        ----------
        error_type : str
            Short machine-friendly category of the error.
        severity : str, optional
            ``critical``, ``high``, ``medium``, ``low``, defaults to ``error``.
        details : Any, optional
            Additional JSON-serialisable payload.
        message_type : str, optional
            Either ``error_report`` or ``critical_alert``.
        """
        if self.socket is None:
            return  # silently ignore if initialisation failed

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
            # Prefix with a simple topic so collectors can subscribe with filters.
            self.socket.send_string(f"ERROR:{json.dumps(payload)}")
        except Exception as exc:  # pragma: no cover – runtime issues
            logging.error("ErrorPublisher: failed to send error: %s", exc)

    def close(self) -> None:
        """Cleanly close the PUB socket if we created it."""
        if self.socket is not None:
            try:
                self.socket.close(linger=0)
            except Exception:
                pass
        if not self._ctx_provided and getattr(self, "context", None) is not None:
            try:
                self.
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _build_default_endpoint() -> str:
        host = os.environ.get("ERROR_BUS_HOST") or os.environ.get("PC2_IP", get_env("BIND_ADDRESS", "0.0.0.0"))
        port = int(os.environ.get("ERROR_BUS_PORT", 7150))
        return f"tcp://{host}:{port}"

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------
    def __enter__(self) -> "ErrorPublisher":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # noqa: D401, D403
        self.close()
