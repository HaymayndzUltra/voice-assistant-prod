"""
Advanced Logging Package for AI System Monorepo

This package provides enterprise-grade logging capabilities including:
- Structured logging with JSON output
- Log aggregation and search
- Performance monitoring and metrics
- Real-time log streaming
- Audit trail support

Author: AI System Monorepo Team
Created: 2025-07-31
Phase: 4.1 - Advanced Logging and Audit Trail
"""

from .structured_logger import (
    StructuredLogger,
    PerformanceTimer,
    LogLevel,
    LogFormat,
    get_logger,
    performance_timer
)

from .log_aggregator import (
    LogAggregator,
    LogEntry,
    SearchResult,
    get_log_aggregator
)

# Version information
__version__ = "1.0.0"
__author__ = "AI System Monorepo Team"
__phase__ = "4.1 - Advanced Logging and Audit Trail"

# Package exports
__all__ = [
    # Structured Logger
    "StructuredLogger",
    "PerformanceTimer", 
    "LogLevel",
    "LogFormat",
    "get_logger",
    "performance_timer",
    
    # Log Aggregator
    "LogAggregator",
    "LogEntry",
    "SearchResult",
    "get_log_aggregator",
    
    # Convenience functions
    "setup_logging",
    "get_default_logger",
    "enable_performance_monitoring"
]


def setup_logging(
    component_name: str,
    level: str = "INFO",
    enable_json: bool = True,
    enable_console: bool = True,
    enable_file: bool = True,
    enable_aggregation: bool = True
) -> StructuredLogger:
    """
    Setup comprehensive logging for a component
    
    Args:
        component_name: Name of the component
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_json: Enable JSON log format
        enable_console: Enable console output
        enable_file: Enable file output
        enable_aggregation: Enable log aggregation
        
    Returns:
        Configured StructuredLogger instance
    """
    config = {
        "level": level,
        "format": "json" if enable_json else "text",
        "enable_console": enable_console,
        "enable_file": enable_file,
        "enable_json": enable_json
    }
    
    logger = get_logger(component_name, config)
    
    # Setup aggregation if enabled
    if enable_aggregation:
        aggregator = get_log_aggregator()
        # The aggregator will automatically discover and monitor log files
    
    return logger


def get_default_logger(component_name: str) -> StructuredLogger:
    """
    Get a logger with default configuration
    
    Args:
        component_name: Name of the component
        
    Returns:
        StructuredLogger with default settings
    """
    return get_logger(component_name)


def enable_performance_monitoring(logger: StructuredLogger) -> StructuredLogger:
    """
    Enable performance monitoring for a logger
    
    Args:
        logger: StructuredLogger instance
        
    Returns:
        Logger with performance monitoring enabled
    """
    # Performance monitoring is enabled by default in StructuredLogger
    return logger


# Example usage documentation
EXAMPLE_USAGE = '''
# Basic usage
from common.logging import get_logger, performance_timer

logger = get_logger("my_component")
logger.info("Application started", version="1.0.0")

# Performance monitoring
with performance_timer(logger, "data_processing", records=1000):
    # Your code here
    pass

# Advanced setup
from common.logging import setup_logging

logger = setup_logging(
    component_name="my_service",
    level="DEBUG",
    enable_json=True,
    enable_aggregation=True
)

# Search logs
from common.logging import get_log_aggregator

aggregator = get_log_aggregator()
results = aggregator.search(
    query="error",
    filters={"level": "ERROR", "component": "my_service"},
    limit=100
)
'''

# Configuration recommendations
CONFIG_RECOMMENDATIONS = {
    "development": {
        "level": "DEBUG",
        "format": "console",
        "enable_console": True,
        "enable_file": True,
        "enable_aggregation": False
    },
    "staging": {
        "level": "INFO", 
        "format": "json",
        "enable_console": True,
        "enable_file": True,
        "enable_aggregation": True
    },
    "production": {
        "level": "WARNING",
        "format": "json",
        "enable_console": False,
        "enable_file": True,
        "enable_aggregation": True
    }
}
