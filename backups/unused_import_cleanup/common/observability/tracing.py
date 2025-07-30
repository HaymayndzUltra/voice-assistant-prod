"""
WP-09 Distributed Tracing System
Request correlation, span tracking, and performance analysis across distributed agents
"""

import asyncio
import time
import threading
import uuid
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager, asynccontextmanager
import json

class SpanKind(Enum):
    """Types of spans"""
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"

class SpanStatus(Enum):
    """Span completion status"""
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

@dataclass
class SpanContext:
    """Span context for correlation"""
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_span_id: Optional[str] = None
    flags: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "flags": self.flags
        }

@dataclass
class Span:
    """Distributed tracing span"""
    context: SpanContext
    operation_name: str
    kind: SpanKind = SpanKind.INTERNAL
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: SpanStatus = SpanStatus.OK
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    references: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def duration(self) -> Optional[float]:
        """Get span duration in seconds"""
        if self.end_time is None:
            return None
        return self.end_time - self.start_time
    
    @property
    def is_finished(self) -> bool:
        """Check if span is finished"""
        return self.end_time is not None
    
    def set_tag(self, key: str, value: Any):
        """Set span tag"""
        self.tags[key] = value
    
    def set_tags(self, tags: Dict[str, Any]):
        """Set multiple span tags"""
        self.tags.update(tags)
    
    def log_event(self, event: str, **fields):
        """Log event to span"""
        log_entry = {
            "timestamp": time.time(),
            "event": event,
            **fields
        }
        self.logs.append(log_entry)
    
    def log_error(self, exception: Exception, **fields):
        """Log error to span"""
        self.status = SpanStatus.ERROR
        self.log_event(
            "error",
            error_type=type(exception).__name__,
            error_message=str(exception),
            **fields
        )
    
    def finish(self, status: SpanStatus = SpanStatus.OK):
        """Finish span"""
        if self.end_time is None:
            self.end_time = time.time()
            self.status = status
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary"""
        return {
            "context": self.context.to_dict(),
            "operation_name": self.operation_name,
            "kind": self.kind.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "status": self.status.value,
            "tags": self.tags,
            "logs": self.logs,
            "references": self.references
        }
    
    def to_json(self) -> str:
        """Convert span to JSON"""
        return json.dumps(self.to_dict(), default=str)

class SpanRecorder:
    """Interface for recording spans"""
    
    async def record_span(self, span: Span):
        """Record completed span"""
        raise NotImplementedError

class InMemorySpanRecorder(SpanRecorder):
    """In-memory span recorder for testing"""
    
    def __init__(self, max_spans: int = 10000):
        self.max_spans = max_spans
        self._spans: List[Span] = []
        self._lock = threading.RLock()
    
    async def record_span(self, span: Span):
        """Record span in memory"""
        with self._lock:
            self._spans.append(span)
            
            # Keep only recent spans
            if len(self._spans) > self.max_spans:
                self._spans = self._spans[-self.max_spans:]
    
    def get_spans(self, trace_id: str = None) -> List[Span]:
        """Get recorded spans"""
        with self._lock:
            if trace_id:
                return [span for span in self._spans if span.context.trace_id == trace_id]
            return self._spans.copy()
    
    def clear(self):
        """Clear all spans"""
        with self._lock:
            self._spans.clear()

class FileSpanRecorder(SpanRecorder):
    """File-based span recorder"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._lock = threading.RLock()
    
    async def record_span(self, span: Span):
        """Record span to file"""
        span_json = span.to_json()
        
        with self._lock:
            with open(self.file_path, 'a', encoding='utf-8') as f:
                f.write(span_json + '\n')

class RemoteSpanRecorder(SpanRecorder):
    """Remote span recorder for centralized tracing"""
    
    def __init__(self, endpoint: str, batch_size: int = 100, flush_interval: float = 5.0):
        self.endpoint = endpoint
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        self._batch: List[Span] = []
        self._batch_lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        
        self._start_flushing()
    
    def _start_flushing(self):
        """Start background flushing"""
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._flush_loop())
    
    async def _flush_loop(self):
        """Background flush loop"""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_batch()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Trace flush error: {e}")
    
    async def record_span(self, span: Span):
        """Add span to batch"""
        async with self._batch_lock:
            self._batch.append(span)
            
            if len(self._batch) >= self.batch_size:
                await self._flush_batch()
    
    async def _flush_batch(self):
        """Flush batch to remote"""
        if not self._batch:
            return
        
        async with self._batch_lock:
            current_batch = self._batch.copy()
            self._batch.clear()
        
        try:
            # Send to remote endpoint
            await self._send_to_remote(current_batch)
        except Exception as e:
            print(f"Failed to send traces to {self.endpoint}: {e}")
            
            # Re-add failed spans
            async with self._batch_lock:
                self._batch.extend(current_batch)
    
    async def _send_to_remote(self, spans: List[Span]):
        """Send spans to remote endpoint"""
        span_data = [span.to_dict() for span in spans]
        
        try:
            from common.pools.http_pool import get_http_pool
            
            pool = get_http_pool()
            response = await pool.request(
                "POST",
                self.endpoint,
                json={"spans": span_data}
            )
            
            if response.status_code != 200:
                raise Exception(f"Remote tracing failed: {response.status_code}")
                
        except ImportError:
            # Fallback
            print(f"Would send {len(spans)} spans to {self.endpoint}")

class Tracer:
    """Distributed tracer"""
    
    def __init__(self, service_name: str, recorder: SpanRecorder = None):
        self.service_name = service_name
        self.recorder = recorder or InMemorySpanRecorder()
        
        # Context management
        self._active_spans: Dict[str, Span] = {}
        self._context_stack: List[SpanContext] = []
        self._context_lock = threading.RLock()
        
        # Metrics
        self._metrics = {
            'spans_created': 0,
            'spans_finished': 0,
            'spans_with_errors': 0,
            'total_duration': 0.0
        }
    
    def _get_current_context(self) -> Optional[SpanContext]:
        """Get current span context"""
        with self._context_lock:
            if self._context_stack:
                return self._context_stack[-1]
            return None
    
    def start_span(self, 
                   operation_name: str,
                   kind: SpanKind = SpanKind.INTERNAL,
                   parent_context: SpanContext = None,
                   tags: Dict[str, Any] = None,
                   references: List[Dict[str, Any]] = None) -> Span:
        """Start new span"""
        
        # Determine parent
        if parent_context is None:
            parent_context = self._get_current_context()
        
        # Create span context
        if parent_context:
            span_context = SpanContext(
                trace_id=parent_context.trace_id,
                parent_span_id=parent_context.span_id
            )
        else:
            span_context = SpanContext()
        
        # Create span
        span = Span(
            context=span_context,
            operation_name=operation_name,
            kind=kind,
            tags=tags or {},
            references=references or []
        )
        
        # Set service tag
        span.set_tag("service.name", self.service_name)
        
        # Store active span
        self._active_spans[span.context.span_id] = span
        
        # Update metrics
        self._metrics['spans_created'] += 1
        
        return span
    
    async def finish_span(self, span: Span, status: SpanStatus = SpanStatus.OK):
        """Finish span and record it"""
        if span.is_finished:
            return
        
        span.finish(status)
        
        # Update metrics
        self._metrics['spans_finished'] += 1
        if span.duration:
            self._metrics['total_duration'] += span.duration
        if status == SpanStatus.ERROR:
            self._metrics['spans_with_errors'] += 1
        
        # Remove from active spans
        self._active_spans.pop(span.context.span_id, None)
        
        # Record span
        await self.recorder.record_span(span)
    
    @contextmanager
    def span(self, 
             operation_name: str,
             kind: SpanKind = SpanKind.INTERNAL,
             tags: Dict[str, Any] = None):
        """Context manager for spans"""
        span = self.start_span(operation_name, kind=kind, tags=tags)
        
        # Push context
        with self._context_lock:
            self._context_stack.append(span.context)
        
        try:
            yield span
        except Exception as e:
            span.log_error(e)
            raise
        finally:
            # Pop context
            with self._context_lock:
                if self._context_stack:
                    self._context_stack.pop()
            
            # Finish span (sync context - limited async support)
            asyncio.create_task(self.finish_span(span))
    
    @asynccontextmanager
    async def async_span(self,
                        operation_name: str,
                        kind: SpanKind = SpanKind.INTERNAL,
                        tags: Dict[str, Any] = None):
        """Async context manager for spans"""
        span = self.start_span(operation_name, kind=kind, tags=tags)
        
        # Push context
        with self._context_lock:
            self._context_stack.append(span.context)
        
        try:
            yield span
        except Exception as e:
            span.log_error(e)
            await self.finish_span(span, SpanStatus.ERROR)
            raise
        else:
            await self.finish_span(span, SpanStatus.OK)
        finally:
            # Pop context
            with self._context_lock:
                if self._context_stack:
                    self._context_stack.pop()
    
    def get_active_spans(self) -> List[Span]:
        """Get currently active spans"""
        return list(self._active_spans.values())
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get tracing metrics"""
        avg_duration = 0.0
        if self._metrics['spans_finished'] > 0:
            avg_duration = self._metrics['total_duration'] / self._metrics['spans_finished']
        
        return {
            **self._metrics,
            'active_spans': len(self._active_spans),
            'avg_duration': avg_duration,
            'error_rate': self._metrics['spans_with_errors'] / max(1, self._metrics['spans_finished'])
        }

class TraceAnalyzer:
    """Analyze traces for performance insights"""
    
    def __init__(self, recorder: SpanRecorder):
        self.recorder = recorder
    
    def analyze_trace(self, trace_id: str) -> Dict[str, Any]:
        """Analyze single trace"""
        if not isinstance(self.recorder, InMemorySpanRecorder):
            return {"error": "Analysis requires InMemorySpanRecorder"}
        
        spans = self.recorder.get_spans(trace_id)
        if not spans:
            return {"error": "Trace not found"}
        
        # Build trace tree
        span_map = {span.context.span_id: span for span in spans}
        root_spans = [span for span in spans if span.context.parent_span_id is None]
        
        if not root_spans:
            return {"error": "No root span found"}
        
        root_span = root_spans[0]
        total_duration = root_span.duration or 0
        
        # Calculate metrics
        error_spans = [span for span in spans if span.status == SpanStatus.ERROR]
        slowest_span = max(spans, key=lambda s: s.duration or 0)
        
        # Service breakdown
        services = {}
        for span in spans:
            service = span.tags.get("service.name", "unknown")
            if service not in services:
                services[service] = {"spans": 0, "duration": 0, "errors": 0}
            
            services[service]["spans"] += 1
            services[service]["duration"] += span.duration or 0
            if span.status == SpanStatus.ERROR:
                services[service]["errors"] += 1
        
        return {
            "trace_id": trace_id,
            "total_spans": len(spans),
            "total_duration": total_duration,
            "error_count": len(error_spans),
            "error_rate": len(error_spans) / len(spans),
            "slowest_operation": {
                "name": slowest_span.operation_name,
                "duration": slowest_span.duration,
                "service": slowest_span.tags.get("service.name", "unknown")
            },
            "services": services,
            "critical_path": self._find_critical_path(spans, span_map)
        }
    
    def _find_critical_path(self, spans: List[Span], span_map: Dict[str, Span]) -> List[Dict[str, Any]]:
        """Find critical path through trace"""
        # Find root span
        root_spans = [span for span in spans if span.context.parent_span_id is None]
        if not root_spans:
            return []
        
        root_span = root_spans[0]
        path = []
        
        def traverse(span):
            path.append({
                "operation": span.operation_name,
                "duration": span.duration,
                "service": span.tags.get("service.name", "unknown")
            })
            
            # Find child spans
            children = [s for s in spans if s.context.parent_span_id == span.context.span_id]
            if children:
                # Take longest child for critical path
                longest_child = max(children, key=lambda s: s.duration or 0)
                traverse(longest_child)
        
        traverse(root_span)
        return path
    
    def get_performance_summary(self, time_window: float = 3600) -> Dict[str, Any]:
        """Get performance summary for time window"""
        if not isinstance(self.recorder, InMemorySpanRecorder):
            return {"error": "Analysis requires InMemorySpanRecorder"}
        
        current_time = time.time()
        recent_spans = [
            span for span in self.recorder.get_spans()
            if span.start_time > (current_time - time_window) and span.is_finished
        ]
        
        if not recent_spans:
            return {"message": "No spans in time window"}
        
        # Calculate metrics
        total_spans = len(recent_spans)
        error_spans = [span for span in recent_spans if span.status == SpanStatus.ERROR]
        durations = [span.duration for span in recent_spans if span.duration is not None]
        
        # Operation breakdown
        operations = {}
        for span in recent_spans:
            op = span.operation_name
            if op not in operations:
                operations[op] = {"count": 0, "total_duration": 0, "errors": 0}
            
            operations[op]["count"] += 1
            operations[op]["total_duration"] += span.duration or 0
            if span.status == SpanStatus.ERROR:
                operations[op]["errors"] += 1
        
        # Calculate averages
        for op_data in operations.values():
            op_data["avg_duration"] = op_data["total_duration"] / op_data["count"]
            op_data["error_rate"] = op_data["errors"] / op_data["count"]
        
        return {
            "time_window": time_window,
            "total_spans": total_spans,
            "error_rate": len(error_spans) / total_spans,
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "p95_duration": sorted(durations)[int(0.95 * len(durations))] if durations else 0,
            "operations": operations,
            "slowest_operations": sorted(
                operations.items(),
                key=lambda x: x[1]["avg_duration"],
                reverse=True
            )[:10]
        }

# Global tracer instance
_tracer: Optional[Tracer] = None

def get_tracer(service_name: str = "ai_system") -> Tracer:
    """Get global tracer"""
    global _tracer
    if _tracer is None:
        # Setup default recorder
        recorder = InMemorySpanRecorder(max_spans=50000)
        _tracer = Tracer(service_name, recorder)
    
    return _tracer

def setup_tracing(service_name: str, 
                 recorder_type: str = "memory",
                 **recorder_config):
    """Setup distributed tracing"""
    global _tracer
    
    # Create recorder based on type
    if recorder_type == "memory":
        recorder = InMemorySpanRecorder(**recorder_config)
    elif recorder_type == "file":
        recorder = FileSpanRecorder(**recorder_config)
    elif recorder_type == "remote":
        recorder = RemoteSpanRecorder(**recorder_config)
    else:
        raise ValueError(f"Unknown recorder type: {recorder_type}")
    
    _tracer = Tracer(service_name, recorder)
    return _tracer

# Convenience decorators
def trace_function(operation_name: str = None,
                  kind: SpanKind = SpanKind.INTERNAL,
                  tags: Dict[str, Any] = None):
    """Decorator for automatic function tracing"""
    
    def decorator(func):
        import functools
        
        func_name = operation_name or f"{func.__module__}.{func.__qualname__}"
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            
            span_tags = tags or {}
            span_tags.update({
                "function.name": func.__name__,
                "function.module": func.__module__
            })
            
            async with tracer.async_span(func_name, kind=kind, tags=span_tags) as span:
                span.set_tag("function.args_count", len(args))
                span.set_tag("function.kwargs_count", len(kwargs))
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_tag("function.result_type", type(result).__name__)
                    return result
                except Exception as e:
                    span.set_tag("error.type", type(e).__name__)
                    span.set_tag("error.message", str(e))
                    raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            
            span_tags = tags or {}
            span_tags.update({
                "function.name": func.__name__,
                "function.module": func.__module__
            })
            
            with tracer.span(func_name, kind=kind, tags=span_tags) as span:
                span.set_tag("function.args_count", len(args))
                span.set_tag("function.kwargs_count", len(kwargs))
                
                try:
                    result = func(*args, **kwargs)
                    span.set_tag("function.result_type", type(result).__name__)
                    return result
                except Exception as e:
                    span.set_tag("error.type", type(e).__name__)
                    span.set_tag("error.message", str(e))
                    raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Convenience functions
async def trace_operation(operation_name: str, tags: Dict[str, Any] = None):
    """Create traced operation context"""
    tracer = get_tracer()
    return tracer.async_span(operation_name, tags=tags)

def get_current_trace_id() -> Optional[str]:
    """Get current trace ID"""
    tracer = get_tracer()
    current_context = tracer._get_current_context()
    return current_context.trace_id if current_context else None

def get_current_span_id() -> Optional[str]:
    """Get current span ID"""
    tracer = get_tracer()
    current_context = tracer._get_current_context()
    return current_context.span_id if current_context else None 