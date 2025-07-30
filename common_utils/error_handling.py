#!/usr/bin/env python3
"""error_handling.py

SafeExecutor helper for graceful exception handling and error pattern replacement.
Designed to replace broad 'except:' and 'except Exception:' patterns with more
specific, logged, and recoverable error handling.

Usage:
    from common_utils.error_handling import SafeExecutor
    
    with SafeExecutor(logger, recoverable=(ZMQError, asyncio.TimeoutError)):
        risky_call()
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import contextmanager
from typing import Any, Callable, Optional, Tuple, Type

try:
    import zmq
    ZMQError = zmq.ZMQError
except ImportError:
    # Fallback for environments without ZMQ
    class ZMQError(Exception):
        pass


class SafeExecutorError(Exception):
    """Raised when SafeExecutor encounters an unrecoverable error."""


class SafeExecutor:
    """
    Context manager for safe execution with specific exception handling.
    
    Replaces broad exception catches with specific, logged error handling.
    Supports both synchronous and asynchronous contexts.
    """
    
    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        recoverable: Tuple[Type[Exception], ...] = (),
        reraise_unrecoverable: bool = True,
        default_return: Any = None,
        max_retries: int = 0,
        retry_delay: float = 1.0,
        on_error: Optional[Callable[[Exception], None]] = None
    ):
        """
        Initialize SafeExecutor.
        
        Args:
            logger: Logger instance for error reporting
            recoverable: Tuple of exception types that are recoverable
            reraise_unrecoverable: Whether to reraise non-recoverable exceptions
            default_return: Default value to return on recoverable errors
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            on_error: Optional callback function called on any error
        """
        self.logger = logger or logging.getLogger(__name__)
        self.recoverable = recoverable
        self.reraise_unrecoverable = reraise_unrecoverable
        self.default_return = default_return
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.on_error = on_error
        self.last_exception: Optional[Exception] = None
        self.retry_count = 0
    
    def __enter__(self):
        """Enter the context manager."""
        return self
    
    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Handle exceptions when exiting the context."""
        if exc_type is None:
            return False  # No exception occurred
        
        self.last_exception = exc_value
        
        # Call error callback if provided
        if self.on_error:
            try:
                self.on_error(exc_value)
            except Exception as callback_error:
                self.logger.error(f"Error in error callback: {callback_error}")
        
        # Check if this is a recoverable exception
        if self.recoverable and isinstance(exc_value, self.recoverable):
            self._log_recoverable_error(exc_value)
            return True  # Suppress the exception
        
        # Log unrecoverable errors
        self._log_unrecoverable_error(exc_value)
        
        if self.reraise_unrecoverable:
            return False  # Let the exception propagate
        else:
            return True  # Suppress even unrecoverable exceptions
    
    def _log_recoverable_error(self, exception: Exception) -> None:
        """Log a recoverable error."""
        self.logger.warning(
            f"Recoverable error handled: {type(exception).__name__}: {exception}",
            extra={"exception_type": type(exception).__name__, "recoverable": True}
        )
    
    def _log_unrecoverable_error(self, exception: Exception) -> None:
        """Log an unrecoverable error with full traceback."""
        self.logger.error(
            f"Unrecoverable error: {type(exception).__name__}: {exception}",
            exc_info=True,
            extra={"exception_type": type(exception).__name__, "recoverable": False}
        )
    
    async def execute_async(self, coro_func: Callable[..., Any], *args, **kwargs) -> Any:
        """
        Execute an async function with retry logic.
        
        Args:
            coro_func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function or default_return on recoverable error
        """
        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(coro_func):
                    return await coro_func(*args, **kwargs)
                else:
                    return coro_func(*args, **kwargs)
            except Exception as e:
                self.retry_count = attempt
                self.last_exception = e
                
                if self.on_error:
                    try:
                        self.on_error(e)
                    except Exception as callback_error:
                        self.logger.error(f"Error in error callback: {callback_error}")
                
                if self.recoverable and isinstance(e, self.recoverable):
                    if attempt < self.max_retries:
                        self.logger.info(f"Retrying after recoverable error (attempt {attempt + 1}/{self.max_retries + 1}): {e}")
                        await asyncio.sleep(self.retry_delay)
                        continue
                    else:
                        self._log_recoverable_error(e)
                        return self.default_return
                else:
                    self._log_unrecoverable_error(e)
                    if self.reraise_unrecoverable:
                        raise
                    return self.default_return
        
        return self.default_return
    
    def execute(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """
        Execute a synchronous function with retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function or default_return on recoverable error
        """
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self.retry_count = attempt
                self.last_exception = e
                
                if self.on_error:
                    try:
                        self.on_error(e)
                    except Exception as callback_error:
                        self.logger.error(f"Error in error callback: {callback_error}")
                
                if self.recoverable and isinstance(e, self.recoverable):
                    if attempt < self.max_retries:
                        self.logger.info(f"Retrying after recoverable error (attempt {attempt + 1}/{self.max_retries + 1}): {e}")
                        import time
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        self._log_recoverable_error(e)
                        return self.default_return
                else:
                    self._log_unrecoverable_error(e)
                    if self.reraise_unrecoverable:
                        raise
                    return self.default_return
        
        return self.default_return


# Convenience functions for common patterns
@contextmanager
def safe_zmq_operation(logger: Optional[logging.Logger] = None, default_return: Any = None):
    """
    Context manager for safe ZMQ operations.
    
    Usage:
        with safe_zmq_operation(logger):
            socket.send(message)
    """
    with SafeExecutor(
        logger=logger,
        recoverable=(ZMQError, asyncio.TimeoutError),
        default_return=default_return
    ):
        yield


@contextmanager
def safe_async_operation(logger: Optional[logging.Logger] = None, default_return: Any = None):
    """
    Context manager for safe async operations.
    
    Usage:
        with safe_async_operation(logger):
            await some_async_call()
    """
    with SafeExecutor(
        logger=logger,
        recoverable=(asyncio.TimeoutError, asyncio.CancelledError),
        default_return=default_return
    ):
        yield


@contextmanager
def safe_io_operation(logger: Optional[logging.Logger] = None, default_return: Any = None):
    """
    Context manager for safe I/O operations.
    
    Usage:
        with safe_io_operation(logger):
            with open(file) as f:
                data = f.read()
    """
    with SafeExecutor(
        logger=logger,
        recoverable=(OSError, IOError, FileNotFoundError, PermissionError),
        default_return=default_return
    ):
        yield


def create_error_handler(
    logger: Optional[logging.Logger] = None,
    recoverable: Tuple[Type[Exception], ...] = (),
    **kwargs
) -> SafeExecutor:
    """
    Factory function to create pre-configured SafeExecutor instances.
    
    Args:
        logger: Logger instance
        recoverable: Tuple of recoverable exception types
        **kwargs: Additional SafeExecutor parameters
        
    Returns:
        Configured SafeExecutor instance
    """
    return SafeExecutor(logger=logger, recoverable=recoverable, **kwargs)


# Pattern detection for migration scripts
def find_broad_exception_patterns(file_path: str) -> list[tuple[int, str]]:
    """
    Find broad exception patterns in a Python file for migration.
    
    Args:
        file_path: Path to Python file to analyze
        
    Returns:
        List of (line_number, line_content) tuples with broad exceptions
    """
    import re
    
    patterns = [
        r'except\s*:\s*$',  # bare except
        r'except\s+Exception\s*:\s*$',  # except Exception
        r'except\s+BaseException\s*:\s*$',  # except BaseException
    ]
    
    findings = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                for pattern in patterns:
                    if re.search(pattern, line):
                        findings.append((line_num, line.strip()))
    except Exception as e:
        logging.getLogger(__name__).error(f"Error analyzing {file_path}: {e}")
    
    return findings


if __name__ == "__main__":
    # Example usage and testing
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Test basic usage
    with SafeExecutor(logger, recoverable=(ValueError,)):
        raise ValueError("This should be caught and logged")
    
    print("SafeExecutor test completed successfully") 