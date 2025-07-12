#!/usr/bin/env python3
"""
Centralized Logging Manager

This module provides enhanced logging capabilities:
- Centralized log collection and configuration
- Structured logging for better searchability
- Performance metrics collection
- Support for different log levels per component
- Rotation of log files to prevent disk space issues
"""

import os
import sys
import json
import time
import logging
import logging.handlers
import threading
import socket
import traceback
import atexit
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, Callable, Set

# Import the PathManager for consistent path resolution
from utils.path_manager import PathManager

# Constants
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
STRUCTURED_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s - %(data)s"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

class StructuredLogRecord(logging.LogRecord):
    """Enhanced log record with structured data support."""
    
    def __init__(self, *args, **kwargs):
        """Initialize a structured log record."""
        super().__init__(*args, **kwargs)
        self.data = "{}"

class StructuredLogger(logging.Logger):
    """Logger with support for structured logging."""
    
    def __init__(self, name, level=logging.NOTSET):
        """Initialize a structured logger."""
        super().__init__(name, level)
    
    def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None, sinfo=None):
        """Create a structured log record."""
        record = StructuredLogRecord(name, level, fn, lno, msg, args, exc_info, func, sinfo)
        if extra:
            for key, value in extra.items():
                if key == "data" and isinstance(value, dict):
                    # Handle structured data
                    record.data = json.dumps(value)
                else:
                    setattr(record, key, value)
        return record
    
    def debug(self, msg, *args, data=None, **kwargs):
        """Log a debug message with structured data."""
        if data:
            kwargs["extra"] = kwargs.get("extra", {})
            kwargs["extra"]["data"] = data
        super().debug(msg, *args, **kwargs)
    
    def info(self, msg, *args, data=None, **kwargs):
        """Log an info message with structured data."""
        if data:
            kwargs["extra"] = kwargs.get("extra", {})
            kwargs["extra"]["data"] = data
        super().info(msg, *args, **kwargs)
    
    def warning(self, msg, *args, data=None, **kwargs):
        """Log a warning message with structured data."""
        if data:
            kwargs["extra"] = kwargs.get("extra", {})
            kwargs["extra"]["data"] = data
        super().warning(msg, *args, **kwargs)
    
    def error(self, msg, *args, data=None, **kwargs):
        """Log an error message with structured data."""
        if data:
            kwargs["extra"] = kwargs.get("extra", {})
            kwargs["extra"]["data"] = data
        super().error(msg, *args, **kwargs)
    
    def critical(self, msg, *args, data=None, **kwargs):
        """Log a critical message with structured data."""
        if data:
            kwargs["extra"] = kwargs.get("extra", {})
            kwargs["extra"]["data"] = data
        super().critical(msg, *args, **kwargs)
    
    def exception(self, msg, *args, data=None, **kwargs):
        """Log an exception message with structured data."""
        if data:
            kwargs["extra"] = kwargs.get("extra", {})
            kwargs["extra"]["data"] = data
        super().exception(msg, *args, **kwargs)

class LogManager:
    """Centralized log management for the AI System."""
    
    # Singleton instance
    _instance = None
    
    # Lock for thread safety
    _lock = threading.RLock()
    
    # Configuration
    _config: Dict[str, Any] = {}
    
    # Component loggers
    _loggers: Dict[str, StructuredLogger] = {}
    
    # Metrics collection
    _metrics: Dict[str, Dict[str, Any]] = {}
    
    # Metrics collection thread
    _metrics_thread = None
    _metrics_stop_event = threading.Event()
    
    # Components with active logs
    _active_components: Set[str] = set()
    
    def __new__(cls):
        """Ensure singleton pattern."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LogManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """Initialize the log manager."""
        with self._lock:
            if self._initialized:
                return
                
            self._initialized = True
            
            # Register the StructuredLogger class
            logging.setLoggerClass(StructuredLogger)
            
            # Load configuration
            self._load_config()
            
            # Create logs directory
            self._logs_dir = PathManager.get_logs_dir()
            self._logs_dir.mkdir(parents=True, exist_ok=True)
            
            # Configure root logger
            self._configure_root_logger()
            
            # Start metrics collection thread
            if self._config.get("collect_metrics", False):
                self._start_metrics_collection()
                
            # Register shutdown handler
            atexit.register(self.shutdown)
            
            logger = self.get_logger("log_manager")
            logger.info("Log manager initialized", data={"logs_dir": str(self._logs_dir)})
    
    def _load_config(self):
        """Load logging configuration."""
        try:
            # Try to import ConfigManager
            try:
                from main_pc_code.utils.config_manager import ConfigManager
                
                # Load logging configuration
                config = ConfigManager.load_config("logging")
                if config:
                    self._config = config
            except ImportError:
                # Fall back to environment variables
                self._config = {
                    "default_level": os.environ.get("LOG_LEVEL", "INFO"),
                    "collect_metrics": os.environ.get("COLLECT_METRICS", "false").lower() == "true",
                    "metrics_interval": int(os.environ.get("METRICS_INTERVAL", "60")),
                    "use_structured_logging": os.environ.get("STRUCTURED_LOGGING", "false").lower() == "true",
                    "log_to_console": os.environ.get("LOG_TO_CONSOLE", "true").lower() == "true",
                    "log_to_file": os.environ.get("LOG_TO_FILE", "true").lower() == "true"
                }
        except Exception as e:
            # Use defaults
            self._config = {
                "default_level": "INFO",
                "collect_metrics": False,
                "metrics_interval": 60,
                "use_structured_logging": False,
                "log_to_console": True,
                "log_to_file": True
            }
            
            # Print error to stderr since logging is not set up yet
            print(f"Error loading logging configuration: {e}", file=sys.stderr)
    
    def _configure_root_logger(self):
        """Configure the root logger."""
        root_logger = logging.getLogger()
        
        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
        # Set level
        level_name = self._config.get("default_level", "INFO")
        level = getattr(logging, level_name, logging.INFO)
        root_logger.setLevel(level)
        
        # Choose log format
        if self._config.get("use_structured_logging", False):
            log_format = STRUCTURED_LOG_FORMAT
        else:
            log_format = DEFAULT_LOG_FORMAT
            
        formatter = logging.Formatter(log_format)
        
        # Add console handler if configured
        if self._config.get("log_to_console", True):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
            
        # Add file handler if configured
        if self._config.get("log_to_file", True):
            file_path = self._logs_dir / "system.log"
            file_handler = logging.handlers.RotatingFileHandler(
                str(file_path),
                maxBytes=MAX_LOG_SIZE,
                backupCount=LOG_BACKUP_COUNT
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
    
    def get_logger(self, component: str) -> logging.Logger:
        """Get a logger for a component.
        
        Args:
            component: Component name
            
        Returns:
            Logger for the component
        """
        with self._lock:
            if component in self._loggers:
                return self._loggers[component]
                
            # Create a new logger
            logger = logging.getLogger(component)
            
            # Use component-specific level if configured
            component_level = self._config.get("component_levels", {}).get(component)
            if component_level:
                level = getattr(logging, component_level, None)
                if level is not None:
                    logger.setLevel(level)
                    
            # Add component-specific file handler if configured
            if self._config.get("log_to_file", True):
                file_path = self._logs_dir / f"{component}.log"
                
                # Check if this logger already has a file handler for this path
                has_handler = False
                for handler in logger.handlers:
                    if (isinstance(handler, logging.FileHandler) and 
                        getattr(handler, "baseFilename", None) == str(file_path)):
                        has_handler = True
                        break
                        
                if not has_handler:
                    # Choose log format
                    if self._config.get("use_structured_logging", False):
                        log_format = STRUCTURED_LOG_FORMAT
                    else:
                        log_format = DEFAULT_LOG_FORMAT
                        
                    formatter = logging.Formatter(log_format)
                    
                    file_handler = logging.handlers.RotatingFileHandler(
                        str(file_path),
                        maxBytes=MAX_LOG_SIZE,
                        backupCount=LOG_BACKUP_COUNT
                    )
                    file_handler.setFormatter(formatter)
                    logger.addHandler(file_handler)
                    
            # Cast to StructuredLogger if needed
            if not isinstance(logger, StructuredLogger):
                logger.__class__ = StructuredLogger
                
            # Store logger
            self._loggers[component] = logger
            self._active_components.add(component)
            
            return logger
    
    def log_event(self, component: str, level: str, message: str, data: Dict[str, Any] = None):
        """Log an event.
        
        Args:
            component: Component name
            level: Log level (debug, info, warning, error, critical)
            message: Log message
            data: Structured data to include
        """
        logger = self.get_logger(component)
        
        # Get log method based on level
        log_method = getattr(logger, level.lower(), logger.info)
        
        # Log the message
        log_method(message, data=data)
    
    def log_metric(self, component: str, metric_name: str, value: Any):
        """Log a metric.
        
        Args:
            component: Component name
            metric_name: Name of the metric
            value: Metric value
        """
        with self._lock:
            if component not in self._metrics:
                self._metrics[component] = {}
                
            self._metrics[component][metric_name] = {
                "value": value,
                "timestamp": time.time()
            }
            
            # Log the metric as an event
            self.log_event(component, "info", f"Metric: {metric_name}", {
                "metric": metric_name,
                "value": value,
                "type": "metric"
            })
    
    def log_exception(self, component: str, exception: Exception, message: str = None, data: Dict[str, Any] = None):
        """Log an exception.
        
        Args:
            component: Component name
            exception: Exception to log
            message: Optional message
            data: Structured data to include
        """
        logger = self.get_logger(component)
        
        # Prepare structured data
        if data is None:
            data = {}
            
        # Add exception details
        data.update({
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "traceback": traceback.format_exc()
        })
        
        # Log the exception
        if message:
            logger.exception(message, data=data)
        else:
            logger.exception(f"Exception: {str(exception)}", data=data)
    
    def get_metrics(self, component: str = None) -> Dict[str, Any]:
        """Get collected metrics.
        
        Args:
            component: Optional component name to filter metrics
            
        Returns:
            Dictionary of metrics
        """
        with self._lock:
            if component:
                return self._metrics.get(component, {})
            else:
                return self._metrics
    
    def _start_metrics_collection(self):
        """Start the metrics collection thread."""
        if self._metrics_thread is None or not self._metrics_thread.is_alive():
            self._metrics_stop_event.clear()
            self._metrics_thread = threading.Thread(target=self._collect_metrics)
            self._metrics_thread.daemon = True
            self._metrics_thread.start()
    
    def _collect_metrics(self):
        """Collect system metrics."""
        logger = self.get_logger("metrics")
        
        while not self._metrics_stop_event.is_set():
            try:
                # Collect system metrics
                metrics = self._get_system_metrics()
                
                # Log system metrics
                for metric_name, value in metrics.items():
                    self.log_metric("system", metric_name, value)
                
                # Log active components
                self.log_metric("system", "active_components", list(self._active_components))
                
                # Log a summary
                logger.info("System metrics collected", data={
                    "metrics_count": len(metrics),
                    "timestamp": time.time()
                })
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                
            # Wait for next collection
            interval = self._config.get("metrics_interval", 60)
            self._metrics_stop_event.wait(interval)
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system metrics.
        
        Returns:
            Dictionary of system metrics
        """
        metrics = {}
        
        try:
            # CPU usage
            import psutil
            
            # CPU metrics
            metrics["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            metrics["cpu_count"] = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            metrics["memory_total"] = memory.total
            metrics["memory_available"] = memory.available
            metrics["memory_used"] = memory.used
            metrics["memory_percent"] = memory.percent
            
            # Disk metrics
            disk = psutil.disk_usage(str(PathManager.get_project_root()))
            metrics["disk_total"] = disk.total
            metrics["disk_used"] = disk.used
            metrics["disk_free"] = disk.free
            metrics["disk_percent"] = disk.percent
            
            # Network metrics
            net_io = psutil.net_io_counters()
            metrics["net_bytes_sent"] = net_io.bytes_sent
            metrics["net_bytes_recv"] = net_io.bytes_recv
            
            # Process metrics
            process = psutil.Process()
            metrics["process_cpu_percent"] = process.cpu_percent(interval=0.1)
            metrics["process_memory_percent"] = process.memory_percent()
            metrics["process_memory_rss"] = process.memory_info().rss
            metrics["process_threads"] = process.num_threads()
            metrics["process_open_files"] = len(process.open_files())
            metrics["process_connections"] = len(process.connections())
        except ImportError:
            # If psutil is not available, collect basic metrics
            metrics["timestamp"] = time.time()
            metrics["hostname"] = socket.gethostname()
        except Exception as e:
            logger = self.get_logger("metrics")
            logger.error(f"Error collecting system metrics: {e}")
            
        return metrics
    
    def shutdown(self):
        """Shutdown the log manager."""
        with self._lock:
            # Stop the metrics collection thread
            if self._metrics_thread is not None and self._metrics_thread.is_alive():
                self._metrics_stop_event.set()
                self._metrics_thread.join(timeout=1)
                
            # Flush all loggers
            for logger in self._loggers.values():
                for handler in logger.handlers:
                    handler.flush()
                    
            # Reset instance
            LogManager._instance = None
            
            # Reset logger class
            logging.setLoggerClass(logging.Logger)

# Initialize the log manager
log_manager = LogManager()

def get_logger(component: str) -> logging.Logger:
    """Get a logger for a component.
    
    Args:
        component: Component name
        
    Returns:
        Logger for the component
    """
    return log_manager.get_logger(component)

def log_event(component: str, level: str, message: str, data: Dict[str, Any] = None):
    """Log an event.
    
    Args:
        component: Component name
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        data: Structured data to include
    """
    log_manager.log_event(component, level, message, data)

def log_metric(component: str, metric_name: str, value: Any):
    """Log a metric.
    
    Args:
        component: Component name
        metric_name: Name of the metric
        value: Metric value
    """
    log_manager.log_metric(component, metric_name, value)

def log_exception(component: str, exception: Exception, message: str = None, data: Dict[str, Any] = None):
    """Log an exception.
    
    Args:
        component: Component name
        exception: Exception to log
        message: Optional message
        data: Structured data to include
    """
    log_manager.log_exception(component, exception, message, data)

def get_metrics(component: str = None) -> Dict[str, Any]:
    """Get collected metrics.
    
    Args:
        component: Optional component name to filter metrics
        
    Returns:
        Dictionary of metrics
    """
    return log_manager.get_metrics(component) 