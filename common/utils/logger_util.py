import logging
import json
import sys
import time
from typing import Optional


class JsonFormatter(logging.Formatter):
    """Formatter that outputs one JSON object per line for each log record."""

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        # Basic structured payload
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "agent": getattr(record, "agent_name", record.name),
            "message": record.getMessage(),
        }

        # Include exception info if present
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        # Include any extra fields explicitly provided via logger.extra
        for key in ("request_id", "session_id", "component"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)

        return json.dumps(payload, ensure_ascii=False)


def _ensure_handler(logger: logging.Logger, handler: logging.Handler) -> None:
    """Attach handler if a similar one is not already present."""
    for h in logger.handlers:
        if type(h) is type(handler):
            return
    logger.addHandler(handler)


def configure_json_root_logger(level: int = logging.INFO) -> None:
    """Configure the root logger to emit JSON-formatted logs to stdout."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(JsonFormatter())
    _ensure_handler(root_logger, stream_handler)


def get_json_logger(name: Optional[str] = None, *, level: int = logging.INFO, logfile: Optional[str] = None) -> logging.Logger:
    """Return a logger that emits JSON lines. Optionally write to *logfile*."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Stream handler to stdout (only once per logger)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(JsonFormatter())
    _ensure_handler(logger, stream_handler)

    # Optional file handler
    if logfile:
        file_handler = logging.FileHandler(logfile)
        file_handler.setFormatter(JsonFormatter())
        _ensure_handler(logger, file_handler)

    return logger 