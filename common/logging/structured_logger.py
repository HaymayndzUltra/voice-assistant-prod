"""
Advanced Structured Logging Framework for AI System Monorepo

This module provides enterprise-grade logging capabilities with:
- JSON structured logging for machine readability
- Multiple output formats (JSON, text, console)
- Log correlation IDs for distributed tracing
- Performance metrics integration
- Automatic log aggregation
- Context-aware logging with metadata

Author: AI System Monorepo Team
Created: 2025-07-31
Phase: 4.1 - Advanced Logging and Audit Trail
"""

import json
import logging
import logging.handlers
import os
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import structlog
except ImportError:
    structlog = None

try:
    from pythonjsonlogger import jsonlogger
except ImportError:
    jsonlogger = None

try:
    from common.config.unified_config_manager import Config
except ImportError:
    Config = None


class LogLevel(Enum):
    """Standard log levels with numeric values"""
    TRACE = 5
    DEBUG = logging.DEBUG      # 10
    INFO = logging.INFO        # 20
    WARNING = logging.WARNING  # 30
    ERROR = logging.ERROR      # 40
    CRITICAL = logging.CRITICAL # 50
    AUDIT = 60  # Custom level for audit events


class LogFormat(Enum):
    """Supported log output formats"""
    JSON = "json"
    TEXT = "text"
    CONSOLE = "console"
    STRUCTURED = "structured"


class StructuredLogger:
    """
    Enterprise-grade structured logger with JSON output, correlation IDs,
    and automatic metadata enrichment.
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize structured logger
        
        Args:
            name: Logger name (usually module or agent name)
            config: Optional configuration override
        """
        self.name = name
        self.config = config or self._load_default_config()
        self.correlation_id = str(uuid.uuid4())
        self.context = {}
        
        # Thread-local storage for request context
        self._local = threading.local()
        
        # Register custom log levels
        self._register_custom_levels()
        
        # Initialize structlog and standard logging
        self._setup_logging()
        
        # Create logger instances
        if structlog is not None:
            self.logger = structlog.get_logger(name)
            self.audit_logger = structlog.get_logger(f"{name}.audit")
            self.performance_logger = structlog.get_logger(f"{name}.performance")
        else:
            # Fallback to standard logging
            self.logger = logging.getLogger(name)
            self.audit_logger = logging.getLogger(f"{name}.audit")
            self.performance_logger = logging.getLogger(f"{name}.performance")
    
    def _register_custom_levels(self):
        """Register custom log levels with Python logging"""
        # Add TRACE level
        logging.addLevelName(LogLevel.TRACE.value, "TRACE")
        
        # Add AUDIT level
        logging.addLevelName(LogLevel.AUDIT.value, "AUDIT")
        
        # Add methods to standard logger class
        def trace(self, message, *args, **kwargs):
            if self.isEnabledFor(LogLevel.TRACE.value):
                self._log(LogLevel.TRACE.value, message, args, **kwargs)
        
        def audit(self, message, *args, **kwargs):
            if self.isEnabledFor(LogLevel.AUDIT.value):
                self._log(LogLevel.AUDIT.value, message, args, **kwargs)
        
        # Monkey patch methods onto Logger class
        logging.Logger.trace = trace
        logging.Logger.audit = audit
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load logging configuration from unified config"""
        try:
            if Config is None:
                raise ImportError("Unified config not available")
            config = Config.for_agent(__file__)
            return {
                "level": config.str("logging.level", "INFO"),
                "format": config.str("logging.format", "json"),
                "output_dir": config.str("logging.output_dir", "logs"),
                "max_size": config.int("logging.max_file_size", 100 * 1024 * 1024),  # 100MB
                "backup_count": config.int("logging.backup_count", 10),
                "enable_console": config.bool("logging.enable_console", True),
                "enable_file": config.bool("logging.enable_file", True),
                "enable_json": config.bool("logging.enable_json", True),
                "correlation_id_header": config.str("logging.correlation_header", "X-Correlation-ID"),
                "performance_threshold": config.float("logging.performance_threshold", 1.0),  # seconds
                "audit_events": config.list("logging.audit_events", [
                    "config_change", "agent_start", "agent_stop", "error_critical"
                ])
            }
        except Exception:
            # Fallback configuration if unified config unavailable
            return {
                "level": "INFO",
                "format": "json",
                "output_dir": "logs",
                "max_size": 100 * 1024 * 1024,
                "backup_count": 10,
                "enable_console": True,
                "enable_file": True,
                "enable_json": True,
                "correlation_id_header": "X-Correlation-ID",
                "performance_threshold": 1.0,
                "audit_events": ["config_change", "agent_start", "agent_stop", "error_critical"]
            }
    
    def _setup_logging(self):
        """Configure structlog and standard logging"""
        # Ensure log directory exists
        log_dir = Path(self.config["output_dir"])
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure structlog processors
        processors = [
            self._add_timestamp,
            self._add_correlation_id,
            self._add_context,
            self._add_logger_name,
        ]
        
        if structlog is not None:
            processors.extend([
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
            ])
            
            # Add JSON formatting if enabled
            if self.config["format"] == "json":
                processors.append(structlog.processors.JSONRenderer())
            else:
                processors.append(structlog.dev.ConsoleRenderer())
        
        # Configure structlog if available
        if structlog is not None:
            structlog.configure(
                processors=processors,
                wrapper_class=structlog.make_filtering_bound_logger(
                    self._get_log_level(self.config["level"])
                ),
                logger_factory=structlog.PrintLoggerFactory(),
                cache_logger_on_first_use=True,
            )
        
        # Configure standard logging
        self._setup_standard_logging()
    
    def _setup_standard_logging(self):
        """Configure standard Python logging with handlers"""
        # Create formatters
        if jsonlogger is not None:
            json_formatter = jsonlogger.JsonFormatter(
                fmt='%(asctime)s %(name)s %(levelname)s %(message)s'
            )
        else:
            # Fallback to standard formatter
            json_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        text_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(self._get_log_level(self.config["level"]))
        
        # Console handler
        if self.config["enable_console"]:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(text_formatter)
            root_logger.addHandler(console_handler)
        
        # File handlers
        if self.config["enable_file"]:
            log_dir = Path(self.config["output_dir"])
            
            # Main log file
            file_handler = logging.handlers.RotatingFileHandler(
                log_dir / f"{self.name}.log",
                maxBytes=self.config.get("max_file_size", self.config.get("max_size", 100 * 1024 * 1024)),
                backupCount=self.config.get("backup_count", 10)
            )
            file_handler.setFormatter(text_formatter)
            root_logger.addHandler(file_handler)
            
            # JSON log file
            if self.config["enable_json"]:
                json_handler = logging.handlers.RotatingFileHandler(
                    log_dir / f"{self.name}.json.log",
                    maxBytes=self.config.get("max_file_size", self.config.get("max_size", 100 * 1024 * 1024)),
                    backupCount=self.config.get("backup_count", 10)
                )
                json_handler.setFormatter(json_formatter)
                root_logger.addHandler(json_handler)
            
            # Audit log file
            audit_handler = logging.handlers.RotatingFileHandler(
                log_dir / f"{self.name}.audit.log",
                maxBytes=self.config.get("max_file_size", self.config.get("max_size", 100 * 1024 * 1024)),
                backupCount=self.config.get("backup_count", 10)
            )
            audit_handler.setFormatter(json_formatter)
            audit_handler.setLevel(LogLevel.AUDIT.value)
            
            # Create audit logger
            audit_logger = logging.getLogger(f"{self.name}.audit")
            audit_logger.addHandler(audit_handler)
            audit_logger.setLevel(LogLevel.AUDIT.value)
    
    def _get_log_level(self, level: str) -> int:
        """Convert string log level to integer"""
        level_mapping = {
            "TRACE": LogLevel.TRACE.value,
            "DEBUG": LogLevel.DEBUG.value,
            "INFO": LogLevel.INFO.value,
            "WARNING": LogLevel.WARNING.value,
            "ERROR": LogLevel.ERROR.value,
            "CRITICAL": LogLevel.CRITICAL.value,
            "AUDIT": LogLevel.AUDIT.value,
        }
        return level_mapping.get(level.upper(), LogLevel.INFO.value)
    
    def _add_timestamp(self, logger, method_name, event_dict):
        """Add ISO timestamp to log events"""
        event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
        return event_dict
    
    def _add_correlation_id(self, logger, method_name, event_dict):
        """Add correlation ID to log events"""
        # Try to get correlation ID from thread-local storage first
        correlation_id = getattr(self._local, 'correlation_id', self.correlation_id)
        event_dict["correlation_id"] = correlation_id
        return event_dict
    
    def _add_context(self, logger, method_name, event_dict):
        """Add context metadata to log events"""
        # Add global context
        event_dict.update(self.context)
        
        # Add thread-local context
        thread_context = getattr(self._local, 'context', {})
        event_dict.update(thread_context)
        
        return event_dict
    
    def _add_logger_name(self, logger, method_name, event_dict):
        """Add logger name to log events"""
        event_dict["logger"] = self.name
        return event_dict
    
    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for current thread"""
        self._local.correlation_id = correlation_id
    
    def set_context(self, **kwargs):
        """Set context variables for current thread"""
        if not hasattr(self._local, 'context'):
            self._local.context = {}
        self._local.context.update(kwargs)
    
    def clear_context(self):
        """Clear thread-local context"""
        if hasattr(self._local, 'context'):
            self._local.context.clear()
    
    def _format_message(self, message: str, **kwargs) -> str:
        """Format message with metadata for standard logging"""
        if kwargs:
            metadata = ' '.join([f"{k}={v}" for k, v in kwargs.items()])
            return f"{message} {metadata}"
        return message
    
    def with_context(self, **kwargs):
        """Return logger with additional context (immutable)"""
        if structlog is not None and hasattr(self.logger, 'bind'):
            return self.logger.bind(**kwargs)
        else:
            # For standard logging, just return self with temp context
            temp_logger = StructuredLogger(self.name, self.config)
            temp_logger.set_context(**kwargs)
            return temp_logger
    
    # Standard logging methods
    def trace(self, message: str, **kwargs):
        """Log trace message"""
        if structlog is not None and hasattr(self.logger, 'log'):
            self.logger.log(LogLevel.TRACE.value, message, **kwargs)
        else:
            self.logger.log(LogLevel.TRACE.value, self._format_message(message, **kwargs))
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        if structlog is not None and hasattr(self.logger, 'debug'):
            self.logger.debug(message, **kwargs)
        else:
            self.logger.debug(self._format_message(message, **kwargs))
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        if structlog is not None and hasattr(self.logger, 'info'):
            self.logger.info(message, **kwargs)
        else:
            self.logger.info(self._format_message(message, **kwargs))
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        if structlog is not None and hasattr(self.logger, 'warning'):
            self.logger.warning(message, **kwargs)
        else:
            self.logger.warning(self._format_message(message, **kwargs))
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        if structlog is not None and hasattr(self.logger, 'error'):
            self.logger.error(message, **kwargs)
        else:
            self.logger.error(self._format_message(message, **kwargs))
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        if structlog is not None and hasattr(self.logger, 'critical'):
            self.logger.critical(message, **kwargs)
        else:
            self.logger.critical(self._format_message(message, **kwargs))
    
    # Specialized logging methods
    def audit(self, event: str, **kwargs):
        """Log audit event"""
        if event in self.config.get("audit_events", []):
            kwargs.update({
                "event_type": "audit",
                "audit_event": event,
                "user": kwargs.get("user", "system"),
                "session_id": kwargs.get("session_id", self.correlation_id)
            })
            
            # Use INFO level for structlog compatibility, mark as audit with metadata
            if structlog is not None and hasattr(self.audit_logger, 'info'):
                self.audit_logger.info(f"AUDIT: {event}", **kwargs)
            else:
                # For standard logging, use the custom AUDIT level
                self.audit_logger.log(LogLevel.AUDIT.value, f"AUDIT: {event}", **kwargs)
    
    def performance(self, operation: str, duration: float, **kwargs):
        """Log performance metrics"""
        kwargs.update({
            "event_type": "performance",
            "operation": operation,
            "duration_seconds": duration,
            "duration_ms": duration * 1000
        })
        
        if duration > self.config.get("performance_threshold", 1.0):
            if structlog is not None and hasattr(self.performance_logger, 'warning'):
                self.performance_logger.warning(
                    f"SLOW: {operation} took {duration:.3f}s", **kwargs
                )
            else:
                self.performance_logger.warning(
                    self._format_message(f"SLOW: {operation} took {duration:.3f}s", **kwargs)
                )
        else:
            if structlog is not None and hasattr(self.performance_logger, 'info'):
                self.performance_logger.info(
                    f"PERF: {operation} completed in {duration:.3f}s", **kwargs
                )
            else:
                self.performance_logger.info(
                    self._format_message(f"PERF: {operation} completed in {duration:.3f}s", **kwargs)
                )
    
    def exception(self, message: str, exc_info=True, **kwargs):
        """Log exception with stack trace"""
        if structlog is not None and hasattr(self.logger, 'error'):
            self.logger.error(message, exc_info=exc_info, **kwargs)
        else:
            self.logger.error(self._format_message(message, **kwargs), exc_info=exc_info)


class PerformanceTimer:
    """Context manager for measuring and logging operation performance"""
    
    def __init__(self, logger: StructuredLogger, operation: str, **kwargs):
        self.logger = logger
        self.operation = operation
        self.kwargs = kwargs
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(f"Starting {self.operation}", **self.kwargs)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        if exc_type is None:
            self.logger.performance(self.operation, duration, **self.kwargs)
        else:
            self.kwargs.update({
                "exception_type": exc_type.__name__,
                "exception_message": str(exc_val)
            })
            self.logger.performance(
                self.operation, duration, status="failed", **self.kwargs
            )


def get_logger(name: str, config: Optional[Dict[str, Any]] = None) -> StructuredLogger:
    """
    Get or create a structured logger instance
    
    Args:
        name: Logger name (usually module or agent name)
        config: Optional configuration override
        
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name, config)


def performance_timer(logger: StructuredLogger, operation: str, **kwargs) -> PerformanceTimer:
    """
    Create a performance timer context manager
    
    Args:
        logger: StructuredLogger instance
        operation: Operation name for logging
        **kwargs: Additional context for logging
        
    Returns:
        PerformanceTimer context manager
    """
    return PerformanceTimer(logger, operation, **kwargs)


# Example usage and testing
if __name__ == "__main__":
    # Example usage
    logger = get_logger("test_agent")
    
    logger.info("Agent starting", agent_id="test-001", version="1.0.0")
    
    # Set context for all subsequent logs
    logger.set_context(request_id="req-123", user_id="user-456")
    
    # Log with additional context
    logger.with_context(action="process_data").info("Processing user data")
    
    # Performance timing
    with performance_timer(logger, "data_processing", records=1000):
        time.sleep(0.1)  # Simulate work
    
    # Audit logging
    logger.audit("config_change", old_value="debug", new_value="info")
    
    # Error logging
    try:
        raise ValueError("Test error")
    except Exception:
        logger.exception("Error processing data")
    
    logger.info("Agent stopped gracefully")
