"""
WP-09 Distributed Logging & Observability
Centralized logging, structured logs, correlation tracking, and comprehensive observability
"""

import asyncio
import json
import time
import threading
import traceback
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
import logging
import logging.handlers
from contextlib import contextmanager, asynccontextmanager
from pathlib import Path

class LogLevel(Enum):
    """Log severity levels"""
    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class LogCategory(Enum):
    """Log categories for classification"""
    SYSTEM = "system"
    AGENT = "agent"
    API = "api"
    PERFORMANCE = "performance"
    SECURITY = "security"
    BUSINESS = "business"
    INTEGRATION = "integration"
    USER = "user"

@dataclass
class LogContext:
    """Contextual information for logs"""
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    operation: Optional[str] = None
    source: Optional[str] = None
    version: str = "1.0.0"
    environment: str = "development"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
        return {
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "operation": self.operation,
            "source": self.source,
            "version": self.version,
            "environment": self.environment
        }

@dataclass
class StructuredLogEntry:
    """Structured log entry with comprehensive metadata"""
    timestamp: float = field(default_factory=time.time)
    level: LogLevel = LogLevel.INFO
    category: LogCategory = LogCategory.SYSTEM
    message: str = ""
    context: LogContext = field(default_factory=LogContext)
    data: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[str] = None
    stack_trace: Optional[str] = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary"""
        entry = {
            "timestamp": self.timestamp,
            "iso_timestamp": datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat(),
            "level": self.level.value,
            "category": self.category.value,
            "message": self.message,
            "context": self.context.to_dict(),
            "data": self.data,
            "tags": self.tags
        }
        
        if self.exception:
            entry["exception"] = self.exception
        
        if self.stack_trace:
            entry["stack_trace"] = self.stack_trace
        
        if self.performance_metrics:
            entry["performance_metrics"] = self.performance_metrics
        
        return entry
    
    def to_json(self) -> str:
        """Convert log entry to JSON string"""
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False)

class LogFormatter(logging.Formatter):
    """Custom formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Extract structured log entry if available
        if hasattr(record, 'structured_entry'):
            return record.structured_entry.to_json()
        
        # Fallback to standard formatting with structure
        entry = StructuredLogEntry(
            timestamp=record.created,
            level=LogLevel(record.levelname.lower()),
            message=record.getMessage(),
            context=LogContext(source=record.name),
            data={
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
                "thread": record.thread,
                "process": record.process
            }
        )
        
        if record.exc_info:
            entry.exception = str(record.exc_info[1])
            entry.stack_trace = self.formatException(record.exc_info)
        
        return entry.to_json()

class LogHandler:
    """Base class for log handlers"""
    
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
    
    async def handle(self, entry: StructuredLogEntry) -> bool:
        """Handle log entry"""
        if not self.enabled:
            return False
        
        try:
            await self._process_entry(entry)
            return True
        except Exception as e:
            # Avoid recursive logging
            print(f"Log handler {self.name} failed: {e}")
            return False
    
    async def _process_entry(self, entry: StructuredLogEntry):
        """Process log entry - to be implemented by subclasses"""
        raise NotImplementedError

class FileLogHandler(LogHandler):
    """File-based log handler with rotation"""
    
    def __init__(self, name: str, file_path: Path, max_size: int = 10*1024*1024, backup_count: int = 5):
        super().__init__(name)
        self.file_path = file_path
        self.max_size = max_size
        self.backup_count = backup_count
        
        # Create directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Setup rotating file handler
        self._handler = logging.handlers.RotatingFileHandler(
            filename=str(file_path),
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        self._handler.setFormatter(LogFormatter())
        
        # Create logger for this handler
        self._logger = logging.getLogger(f"file_handler_{name}")
        self._logger.addHandler(self._handler)
        self._logger.setLevel(logging.DEBUG)
        self._logger.propagate = False
    
    async def _process_entry(self, entry: StructuredLogEntry):
        """Write log entry to file"""
        # Create log record with structured entry
        record = logging.LogRecord(
            name=entry.context.source or "unknown",
            level=getattr(logging, entry.level.value.upper()),
            pathname="",
            lineno=0,
            msg=entry.message,
            args=(),
            exc_info=None
        )
        record.structured_entry = entry
        
        # Write to file (in thread to avoid blocking)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._handler.emit, record)

class ConsoleLogHandler(LogHandler):
    """Console log handler with colored output"""
    
    def __init__(self, name: str, colored: bool = True):
        super().__init__(name)
        self.colored = colored
        self._colors = {
            LogLevel.TRACE: "\033[90m",      # Gray
            LogLevel.DEBUG: "\033[94m",      # Blue
            LogLevel.INFO: "\033[92m",       # Green
            LogLevel.WARNING: "\033[93m",    # Yellow
            LogLevel.ERROR: "\033[91m",      # Red
            LogLevel.CRITICAL: "\033[95m",   # Magenta
        }
        self._reset = "\033[0m"
    
    async def _process_entry(self, entry: StructuredLogEntry):
        """Write log entry to console"""
        timestamp = datetime.fromtimestamp(entry.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        
        if self.colored and entry.level in self._colors:
            color = self._colors[entry.level]
            level_str = f"{color}{entry.level.value.upper()}{self._reset}"
        else:
            level_str = entry.level.value.upper()
        
        # Format basic message
        message = f"[{timestamp}] {level_str} [{entry.category.value}] {entry.message}"
        
        # Add context if available
        if entry.context.correlation_id:
            message += f" (ID: {entry.context.correlation_id[:8]})"
        
        if entry.context.agent_id:
            message += f" [Agent: {entry.context.agent_id}]"
        
        # Add performance metrics if available
        if entry.performance_metrics:
            metrics_str = ", ".join(f"{k}: {v:.3f}" for k, v in entry.performance_metrics.items())
            message += f" [Metrics: {metrics_str}]"
        
        print(message)
        
        # Print exception if available
        if entry.exception:
            print(f"Exception: {entry.exception}")
        
        if entry.stack_trace:
            print(f"Stack trace:\n{entry.stack_trace}")

class RemoteLogHandler(LogHandler):
    """Remote log handler for centralized logging"""
    
    def __init__(self, name: str, endpoint: str, batch_size: int = 100, flush_interval: float = 5.0):
        super().__init__(name)
        self.endpoint = endpoint
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        # Batch management
        self._batch: List[StructuredLogEntry] = []
        self._batch_lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        
        # Start background flushing
        self._start_flushing()
    
    def _start_flushing(self):
        """Start background batch flushing"""
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._flush_loop())
    
    async def _flush_loop(self):
        """Background loop for flushing batches"""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_batch()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Flush loop error in {self.name}: {e}")
    
    async def _process_entry(self, entry: StructuredLogEntry):
        """Add entry to batch"""
        async with self._batch_lock:
            self._batch.append(entry)
            
            if len(self._batch) >= self.batch_size:
                await self._flush_batch()
    
    async def _flush_batch(self):
        """Flush current batch to remote endpoint"""
        if not self._batch:
            return
        
        async with self._batch_lock:
            current_batch = self._batch.copy()
            self._batch.clear()
        
        try:
            # Convert batch to JSON
            batch_data = [entry.to_dict() for entry in current_batch]
            
            # Send to remote endpoint (placeholder - implement actual HTTP client)
            await self._send_to_remote(batch_data)
            
        except Exception as e:
            print(f"Failed to flush batch to {self.endpoint}: {e}")
            
            # Re-add failed entries to batch for retry
            async with self._batch_lock:
                self._batch.extend(current_batch)
    
    async def _send_to_remote(self, batch_data: List[Dict[str, Any]]):
        """Send batch to remote endpoint"""
        # Placeholder implementation
        # In production, use aiohttp or similar HTTP client
        try:
            from common.pools.http_pool import get_http_pool
            
            pool = get_http_pool()
            response = await pool.request(
                "POST",
                self.endpoint,
                json={"logs": batch_data}
            )
            
            if response.status_code != 200:
                raise Exception(f"Remote logging failed: {response.status_code}")
                
        except ImportError:
            # Fallback without HTTP pool
            print(f"Would send {len(batch_data)} log entries to {self.endpoint}")

class DistributedLogger:
    """Central distributed logging system"""
    
    def __init__(self, name: str = "distributed_logger"):
        self.name = name
        self._handlers: List[LogHandler] = []
        self._context_stack: List[LogContext] = []
        self._context_lock = threading.RLock()
        
        # Default context
        self._default_context = LogContext()
        
        # Metrics
        self._metrics = {
            'total_logs': 0,
            'logs_by_level': {level: 0 for level in LogLevel},
            'logs_by_category': {category: 0 for category in LogCategory},
            'failed_logs': 0
        }
        self._metrics_lock = threading.RLock()
    
    def add_handler(self, handler: LogHandler):
        """Add log handler"""
        self._handlers.append(handler)
        print(f"Added log handler: {handler.name}")
    
    def remove_handler(self, handler_name: str):
        """Remove log handler by name"""
        self._handlers = [h for h in self._handlers if h.name != handler_name]
    
    def set_default_context(self, context: LogContext):
        """Set default context for all logs"""
        self._default_context = context
    
    @contextmanager
    def context(self, **kwargs):
        """Context manager for log context"""
        # Create new context based on current + overrides
        current_context = self._get_current_context()
        new_context = LogContext(**{
            **current_context.to_dict(),
            **{k: v for k, v in kwargs.items() if v is not None}
        })
        
        with self._context_lock:
            self._context_stack.append(new_context)
        
        try:
            yield new_context
        finally:
            with self._context_lock:
                if self._context_stack:
                    self._context_stack.pop()
    
    @asynccontextmanager
    async def async_context(self, **kwargs):
        """Async context manager for log context"""
        # Create new context based on current + overrides
        current_context = self._get_current_context()
        new_context = LogContext(**{
            **current_context.to_dict(),
            **{k: v for k, v in kwargs.items() if v is not None}
        })
        
        with self._context_lock:
            self._context_stack.append(new_context)
        
        try:
            yield new_context
        finally:
            with self._context_lock:
                if self._context_stack:
                    self._context_stack.pop()
    
    def _get_current_context(self) -> LogContext:
        """Get current context from stack"""
        with self._context_lock:
            if self._context_stack:
                return self._context_stack[-1]
            return self._default_context
    
    async def log(self,
                  level: LogLevel,
                  message: str,
                  category: LogCategory = LogCategory.SYSTEM,
                  data: Optional[Dict[str, Any]] = None,
                  exception: Optional[Exception] = None,
                  performance_metrics: Optional[Dict[str, float]] = None,
                  tags: Optional[List[str]] = None,
                  **context_overrides):
        """Log structured entry"""
        
        # Create log entry
        current_context = self._get_current_context()
        
        # Override context if specified
        if context_overrides:
            context_dict = current_context.to_dict()
            context_dict.update({k: v for k, v in context_overrides.items() if v is not None})
            context = LogContext(**context_dict)
        else:
            context = current_context
        
        entry = StructuredLogEntry(
            level=level,
            category=category,
            message=message,
            context=context,
            data=data or {},
            performance_metrics=performance_metrics or {},
            tags=tags or []
        )
        
        # Add exception info if provided
        if exception:
            entry.exception = str(exception)
            entry.stack_trace = traceback.format_exc()
        
        # Update metrics
        with self._metrics_lock:
            self._metrics['total_logs'] += 1
            self._metrics['logs_by_level'][level] += 1
            self._metrics['logs_by_category'][category] += 1
        
        # Send to all handlers
        failed_handlers = 0
        for handler in self._handlers:
            try:
                success = await handler.handle(entry)
                if not success:
                    failed_handlers += 1
            except Exception as e:
                failed_handlers += 1
                print(f"Handler {handler.name} failed: {e}")
        
        if failed_handlers > 0:
            with self._metrics_lock:
                self._metrics['failed_logs'] += failed_handlers
    
    # Convenience methods for different log levels
    async def trace(self, message: str, **kwargs):
        await self.log(LogLevel.TRACE, message, **kwargs)
    
    async def debug(self, message: str, **kwargs):
        await self.log(LogLevel.DEBUG, message, **kwargs)
    
    async def info(self, message: str, **kwargs):
        await self.log(LogLevel.INFO, message, **kwargs)
    
    async def warning(self, message: str, **kwargs):
        await self.log(LogLevel.WARNING, message, **kwargs)
    
    async def error(self, message: str, **kwargs):
        await self.log(LogLevel.ERROR, message, **kwargs)
    
    async def critical(self, message: str, **kwargs):
        await self.log(LogLevel.CRITICAL, message, **kwargs)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get logging metrics"""
        with self._metrics_lock:
            return {
                **self._metrics,
                'handlers': [h.name for h in self._handlers],
                'context_stack_depth': len(self._context_stack)
            }

# Global logger instance
_distributed_logger: Optional[DistributedLogger] = None

def get_distributed_logger() -> DistributedLogger:
    """Get global distributed logger"""
    global _distributed_logger
    if _distributed_logger is None:
        _distributed_logger = DistributedLogger()
        
        # Setup default handlers
        setup_default_handlers(_distributed_logger)
    
    return _distributed_logger

def setup_default_handlers(logger: DistributedLogger):
    """Setup default log handlers"""
    # Console handler
    console_handler = ConsoleLogHandler("console")
    logger.add_handler(console_handler)
    
    # File handler
    log_dir = Path("logs")
    file_handler = FileLogHandler(
        "application",
        log_dir / "application.log",
        max_size=50*1024*1024,  # 50MB
        backup_count=10
    )
    logger.add_handler(file_handler)
    
    # Error file handler
    error_handler = FileLogHandler(
        "errors",
        log_dir / "errors.log",
        max_size=10*1024*1024,  # 10MB
        backup_count=5
    )
    logger.add_handler(error_handler)

# Decorators for automatic logging
def log_function_calls(level: LogLevel = LogLevel.DEBUG, 
                      category: LogCategory = LogCategory.SYSTEM,
                      include_args: bool = False,
                      include_result: bool = False):
    """Decorator for automatic function call logging"""
    
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_distributed_logger()
            
            func_name = f"{func.__module__}.{func.__qualname__}"
            
            # Log function entry
            log_data = {"function": func_name}
            if include_args:
                log_data["args"] = str(args)
                log_data["kwargs"] = str(kwargs)
            
            async with logger.async_context(operation=func_name):
                await logger.log(
                    level,
                    f"Entering function: {func_name}",
                    category=category,
                    data=log_data,
                    tags=["function_entry"]
                )
                
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    
                    # Log successful exit
                    execution_time = time.time() - start_time
                    result_data = {"function": func_name, "execution_time": execution_time}
                    
                    if include_result:
                        result_data["result"] = str(result)
                    
                    await logger.log(
                        level,
                        f"Exiting function: {func_name}",
                        category=category,
                        data=result_data,
                        performance_metrics={"execution_time": execution_time},
                        tags=["function_exit", "success"]
                    )
                    
                    return result
                    
                except Exception as e:
                    # Log exception
                    execution_time = time.time() - start_time
                    
                    await logger.log(
                        LogLevel.ERROR,
                        f"Function failed: {func_name}",
                        category=category,
                        data={"function": func_name, "execution_time": execution_time},
                        exception=e,
                        performance_metrics={"execution_time": execution_time},
                        tags=["function_exit", "error"]
                    )
                    
                    raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, create async context in thread
            
            get_distributed_logger()
            func_name = f"{func.__module__}.{func.__qualname__}"
            
            log_data = {"function": func_name}
            if include_args:
                log_data["args"] = str(args)
                log_data["kwargs"] = str(kwargs)
            
            # Simple sync logging (without context)
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Note: Sync logging is limited - recommend using async
                print(f"SYNC LOG: Function {func_name} completed in {execution_time:.3f}s")
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                print(f"SYNC LOG: Function {func_name} failed after {execution_time:.3f}s: {e}")
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def log_exceptions(level: LogLevel = LogLevel.ERROR,
                  category: LogCategory = LogCategory.SYSTEM):
    """Decorator for automatic exception logging"""
    
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger = get_distributed_logger()
                func_name = f"{func.__module__}.{func.__qualname__}"
                
                await logger.log(
                    level,
                    f"Unhandled exception in {func_name}",
                    category=category,
                    data={"function": func_name},
                    exception=e,
                    tags=["unhandled_exception"]
                )
                
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                func_name = f"{func.__module__}.{func.__qualname__}"
                print(f"SYNC LOG: Unhandled exception in {func_name}: {e}")
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Convenience functions
async def log_info(message: str, **kwargs):
    """Quick info log"""
    logger = get_distributed_logger()
    await logger.info(message, **kwargs)

async def log_error(message: str, exception: Exception = None, **kwargs):
    """Quick error log"""
    logger = get_distributed_logger()
    await logger.error(message, exception=exception, **kwargs)

async def log_performance(operation: str, metrics: Dict[str, float], **kwargs):
    """Quick performance log"""
    logger = get_distributed_logger()
    await logger.info(
        f"Performance metrics for {operation}",
        category=LogCategory.PERFORMANCE,
        performance_metrics=metrics,
        tags=["performance"],
        **kwargs
    ) 