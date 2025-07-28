import atexit
import logging
import os
from datetime import datetime
from typing import Any, Dict

LOG_FILE = os.path.join(os.getcwd(), "session_logs.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)


class SessionActionLogger:
    """Writes simple event logs so humans have an audit trail."""

    def __init__(self) -> None:
        self._start_time = datetime.utcnow()
        logging.info("🟢 New Cursor session started.")
        atexit.register(self._on_exit)

    def log(self, action: str, details: Dict[str, Any] | str | None = None) -> None:
        if isinstance(details, dict):
            msg = ", ".join(f"{k}={v}" for k, v in details.items())
        else:
            msg = str(details or "")
        logging.info("%s | %s", action, msg)

    def _on_exit(self) -> None:
        duration = datetime.utcnow() - self._start_time
        logging.info("🔴 Cursor session ended. Duration: %s", duration)


# Singleton instance for convenience
logger = SessionActionLogger()