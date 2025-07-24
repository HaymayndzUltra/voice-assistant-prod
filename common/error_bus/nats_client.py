
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
NATS Error Bus Library for WP-10 NATS Error Bus Integration
Provides centralized error handling, flood detection, and error correlation
"""

import asyncio
import nats
import json
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
import logging
from collections import defaultdict, deque
import threading
import os

@dataclass
class ErrorMessage:
    """Standardized error message structure"""
    error_id: str
    timestamp: str
    source_agent: str
    error_type: str
    severity: str  # CRITICAL, ERROR, WARNING, INFO
    message: str
    stack_trace: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
    retry_count: int = 0

@dataclass
class ErrorPattern:
    """Error pattern for flood detection"""
    pattern: str
    threshold: int
    time_window: int  # seconds
    action: str  # THROTTLE, BLOCK, ESCALATE

class ErrorFloodDetector:
    """Detects and prevents error floods"""
    
    def __init__(self, patterns: List[ErrorPattern]):
        self.patterns = patterns
        self.error_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.throttled_patterns: Dict[str, datetime] = {}
        self.lock = threading.Lock()
    
    def check_flood(self, error_msg: ErrorMessage) -> bool:
        """Check if error should be throttled due to flood detection"""
        with self.lock:
            current_time = datetime.now()
            
            for pattern in self.patterns:
                if pattern.pattern in error_msg.message or pattern.pattern in error_msg.error_type:
                    pattern_key = f"{error_msg.source_agent}:{pattern.pattern}"
                    
                    # Check if pattern is currently throttled
                    if pattern_key in self.throttled_patterns:
                        throttle_end = self.throttled_patterns[pattern_key] + timedelta(seconds=pattern.time_window)
                        if current_time < throttle_end:
                            return True  # Still throttled
                        else:
                            del self.throttled_patterns[pattern_key]
                    
                    # Add to history
                    self.error_history[pattern_key].append(current_time)
                    
                    # Check if threshold exceeded
                    window_start = current_time - timedelta(seconds=pattern.time_window)
                    recent_errors = [t for t in self.error_history[pattern_key] if t >= window_start]
                    
                    if len(recent_errors) >= pattern.threshold:
                        if pattern.action == "THROTTLE":
                            self.throttled_patterns[pattern_key] = current_time
                            return True
                        elif pattern.action == "ESCALATE":
                            # Send escalation notification
                            self._escalate_error(error_msg, pattern, len(recent_errors))
            
            return False
    
    def _escalate_error(self, error_msg: ErrorMessage, pattern: ErrorPattern, count: int):
        """Escalate error to higher severity"""
        escalated_msg = ErrorMessage(
            error_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            source_agent="error_flood_detector",
            error_type="ERROR_FLOOD_DETECTED",
            severity="CRITICAL",
            message=f"Error flood detected: {pattern.pattern} occurred {count} times",
            context={
                "original_error": asdict(error_msg),
                "pattern": pattern.pattern,
                "count": count,
                "time_window": pattern.time_window
            }
        )
        
        # This would be sent back to the error bus
        print(f"ESCALATED: {escalated_msg.message}")

class NATSErrorBus:
    """
    NATS-based error bus for centralized error handling
    """
    
    def __init__(self, nats_servers: List[str] = None, agent_name: str = "unknown"):
        self.nats_servers = nats_servers or ["nats://localhost:4222"]
        self.agent_name = agent_name
        self.nc: Optional[nats.NATS] = None
        self.js: Optional[nats.aio.client.JetStreamContext] = None
        
        # Error handling configuration
        self.error_subject = "errors"
        self.error_stream = "ERROR_STREAM"
        self.error_consumer = f"error_consumer_{agent_name}"
        
        # Flood detection
        self.flood_detector = ErrorFloodDetector([
            ErrorPattern("ConnectionError", threshold=10, time_window=60, action="THROTTLE"),
            ErrorPattern("TimeoutError", threshold=5, time_window=30, action="THROTTLE"),
            ErrorPattern("MemoryError", threshold=3, time_window=300, action="ESCALATE"),
            ErrorPattern("CRITICAL", threshold=5, time_window=60, action="ESCALATE"),
        ])
        
        # Message handlers
        self.error_handlers: List[Callable[[ErrorMessage], None]] = []
        
        # Background task
        self._running = False
        self._consumer_task = None
        
        # Initialize logging
        self.logger = logging.getLogger(__name__)
    
    async def connect(self):
        """Connect to NATS server"""
        try:
            self.nc = await nats.connect(servers=self.nats_servers)
            self.js = self.nc.jetstream()
            
            # Create stream if it doesn't exist
            await self._ensure_stream_exists()
            
            # Start consuming errors
            await self._start_error_consumer()
            
            self.logger.info(f"Connected to NATS error bus for agent {self.agent_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to NATS: {e}")
            raise
    
    async def _ensure_stream_exists(self):
        """Ensure the error stream exists"""
        try:
            await self.js.stream_info(self.error_stream)
        except nats.js.errors.NotFoundError:
            # Create the stream
            await self.js.add_stream(
                name=self.error_stream,
                subjects=[f"{self.error_subject}.>"],
                retention="limits",
                max_msgs=1000000,
                max_age=7 * 24 * 3600,  # 7 days
                storage="file"
            )
            self.logger.info(f"Created NATS stream: {self.error_stream}")
    
    async def _start_error_consumer(self):
        """Start consuming error messages"""
        if self._consumer_task and not self._consumer_task.done():
            return
        
        self._running = True
        self._consumer_task = asyncio.create_task(self._consume_errors())
    
    async def _consume_errors(self):
        """Background task to consume error messages"""
        try:
            # Create consumer
            consumer = await self.js.pull_subscribe(
                subject=f"{self.error_subject}.>",
                stream=self.error_stream,
                durable=self.error_consumer
            )
            
            while self._running:
                try:
                    msgs = await consumer.fetch(batch=10, timeout=1)
                    
                    for msg in msgs:
                        try:
                            error_data = json.loads(msg.data.decode())
                            error_msg = ErrorMessage(**error_data)
                            
                            # Process error message
                            await self._process_error_message(error_msg)
                            
                            # Acknowledge message
                            await msg.ack()
                            
                        except Exception as e:
                            self.logger.error(f"Error processing message: {e}")
                            await msg.nak()
                
                except nats.js.errors.TimeoutError:
                    # No messages available, continue
                    continue
                except Exception as e:
                    self.logger.error(f"Error in consumer loop: {e}")
                    await asyncio.sleep(1)
                    
        except Exception as e:
            self.logger.error(f"Error starting consumer: {e}")
    
    async def _process_error_message(self, error_msg: ErrorMessage):
        """Process a received error message"""
        # Skip processing our own errors to avoid loops
        if error_msg.source_agent == self.agent_name:
            return
        
        # Call registered handlers
        for handler in self.error_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(error_msg)
                else:
                    handler(error_msg)
            except Exception as e:
                self.logger.error(f"Error in error handler: {e}")
    
    def add_error_handler(self, handler: Callable[[ErrorMessage], None]):
        """Add an error message handler"""
        self.error_handlers.append(handler)
    
    async def publish_error(self, error_type: str, message: str, severity: str = "ERROR",
                           stack_trace: str = None, context: Dict = None, 
                           correlation_id: str = None) -> bool:
        """Publish an error message to the bus"""
        error_msg = ErrorMessage(
            error_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            source_agent=self.agent_name,
            error_type=error_type,
            severity=severity,
            message=message,
            stack_trace=stack_trace,
            context=context or {},
            correlation_id=correlation_id
        )
        
        # Check flood detection
        if self.flood_detector.check_flood(error_msg):
            self.logger.debug(f"Error throttled due to flood detection: {message}")
            return False
        
        try:
            subject = f"{self.error_subject}.{severity.lower()}.{self.agent_name}"
            data = json.dumps(asdict(error_msg)).encode()
            
            await self.js.publish(subject, data)
            return True
            
        except Exception as e:
            # Fallback to local logging if NATS fails
            self.logger.error(f"Failed to publish error to NATS: {e}")
            self.logger.error(f"Original error: {message}")
            return False
    
    async def disconnect(self):
        """Disconnect from NATS"""
        self._running = False
        
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        
        if self.nc:
            await self.nc.close()
            self.nc = None
            self.js = None
        
        self.logger.info("Disconnected from NATS error bus")

# Global error bus instance
_error_bus: Optional[NATSErrorBus] = None

def get_error_bus() -> NATSErrorBus:
    """Get the global error bus instance"""
    global _error_bus
    if _error_bus is None:
        agent_name = os.getenv("AGENT_NAME", "unknown")
        nats_servers = os.getenv("NATS_SERVERS", "nats://localhost:4222").split(",")
        _error_bus = NATSErrorBus(nats_servers, agent_name)
    return _error_bus

async def init_error_bus(agent_name: str, nats_servers: List[str] = None) -> NATSErrorBus:
    """Initialize the error bus for an agent"""
    global _error_bus
    _error_bus = NATSErrorBus(nats_servers, agent_name)
    await _error_bus.connect()
    return _error_bus

# Convenience functions for error reporting
async def report_error(error_type: str, message: str, severity: str = "ERROR", **kwargs):
    """Report an error to the bus"""
    error_bus = get_error_bus()
    return await error_bus.publish_error(error_type, message, severity, **kwargs)

async def report_critical(message: str, **kwargs):
    """Report a critical error"""
    return await report_error("CRITICAL_ERROR", message, "CRITICAL", **kwargs)

async def report_warning(message: str, **kwargs):
    """Report a warning"""
    return await report_error("WARNING", message, "WARNING", **kwargs)

async def report_info(message: str, **kwargs):
    """Report an info message"""
    return await report_error("INFO", message, "INFO", **kwargs)

# Decorator for automatic error reporting
def error_bus_handler(error_type: str = None, severity: str = "ERROR"):
    """Decorator to automatically report exceptions to error bus"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    import traceback
                    await report_error(
                        error_type or f"{func.__name__}_error",
                        str(e),
                        severity,
                        stack_trace=traceback.format_exc(),
                        context={"function": func.__name__, "args": len(args), "kwargs": list(kwargs.keys())}
                    )
                    raise
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    import traceback
                    # For sync functions, we need to run the error reporting in an event loop
                    try:
                        loop = asyncio.get_event_loop()
                        loop.create_task(report_error(
                            error_type or f"{func.__name__}_error",
                            str(e),
                            severity,
                            stack_trace=traceback.format_exc(),
                            context={"function": func.__name__, "args": len(args), "kwargs": list(kwargs.keys())}
                        ))
                    except RuntimeError:
                        # No event loop running, fallback to logging
                        logging.error(f"Error in {func.__name__}: {e}")
                    raise
            return sync_wrapper
    return decorator

# Context manager for error correlation
class ErrorContext:
    """Context manager for error correlation"""
    
    def __init__(self, correlation_id: str = None, context: Dict = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.context = context or {}
        self._previous_correlation_id = None
    
    def __enter__(self):
        # Store in thread-local storage if needed
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Report the exception with correlation ID
            import traceback
            asyncio.create_task(report_error(
                str(exc_type.__name__),
                str(exc_val),
                "ERROR",
                stack_trace=traceback.format_exc(),
                correlation_id=self.correlation_id,
                context=self.context
            ))
        return False  # Don't suppress exceptions

# Usage examples in comments:
"""
# Initialize error bus
await init_error_bus("my_agent", ["nats://localhost:4222"])

# Report errors
await report_error("DATABASE_ERROR", "Connection failed", severity="CRITICAL")
await report_warning("High memory usage detected")

# Use decorator
@error_bus_handler("API_ERROR", "WARNING")
async def call_api():
    # Your API call here
    pass

# Use context manager
with ErrorContext(correlation_id="req-123", context={"user_id": "user456"}):
    # Your code here
    pass
"""
