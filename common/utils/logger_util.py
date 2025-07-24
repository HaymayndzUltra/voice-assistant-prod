import logging
import json
import sys
import time
from typing import Optional
from logging.handlers import RotatingFileHandler


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
    """Ensure handler is added to logger without duplicates."""
    if handler not in logger.handlers:
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


def get_rotating_json_logger(name: Optional[str] = None, 
                           log_file: Optional[str] = None,
                           max_bytes: int = 10*1024*1024,  # 10MB default
                           backup_count: int = 5,          # Keep 5 backup files
                           level: int = logging.INFO,
                           console_output: bool = True) -> logging.Logger:
    """
    Create logger with rotation to prevent disk issues.
    
    Args:
        name: Logger name (optional)
        log_file: Path to log file (optional)
        max_bytes: Maximum size in bytes before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
        level: Logging level (default: INFO)
        console_output: Whether to also log to console (default: True)
        
    Returns:
        Logger configured with rotating file handler and JSON formatting
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # JSON formatter for all handlers
    formatter = JsonFormatter()
    
    # Console handler (optional)
    if console_output:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    
    # Rotating file handler (if log_file specified)
    if log_file:
        # Ensure directory exists
        import os
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Create rotating handler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Log configuration info
        logger.info(f"Rotating JSON logger configured", extra={
            "log_file": log_file,
            "max_bytes": max_bytes,
            "backup_count": backup_count,
            "rotation_enabled": True
        })
    
    return logger


def upgrade_logger_to_rotating(logger: logging.Logger,
                             log_file: str,
                             max_bytes: int = 10*1024*1024,
                             backup_count: int = 5) -> bool:
    """
    Upgrade an existing logger to use rotating file handler.
    
    Args:
        logger: Existing logger to upgrade
        log_file: Path to log file
        max_bytes: Maximum size before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
        
    Returns:
        True if upgrade successful, False otherwise
    """
    try:
        # Find and remove existing file handlers
        file_handlers_to_remove = []
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler) and not isinstance(handler, RotatingFileHandler):
                file_handlers_to_remove.append(handler)
        
        for handler in file_handlers_to_remove:
            logger.removeHandler(handler)
            handler.close()
        
        # Ensure directory exists
        import os
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Add rotating file handler
        rotating_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        rotating_handler.setFormatter(JsonFormatter())
        logger.addHandler(rotating_handler)
        
        logger.info(f"Logger upgraded to rotating file handler", extra={
            "log_file": log_file,
            "max_bytes": max_bytes,
            "backup_count": backup_count,
            "upgrade_successful": True
        })
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to upgrade logger to rotating handler: {e}")
        return False 