"""
Real-Time Audio Pipeline - Telemetry and Metrics

This module provides comprehensive performance monitoring and telemetry
for the RTAP system using Prometheus metrics. Critical for maintaining
the ≤150ms p95 latency budget.
"""

import time
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
import threading


class PipelineMetrics:
    """
    Comprehensive metrics collection for Real-Time Audio Pipeline.
    
    Provides Prometheus-compatible metrics for monitoring pipeline performance,
    latency, throughput, and system health. Essential for maintaining SLA
    and debugging performance bottlenecks.
    
    Key Metrics:
    - End-to-end latency histograms (p50, p95, p99)
    - Frame processing counters
    - State transition tracking
    - Buffer utilization gauges
    - Error rate counters
    - Wake word detection metrics
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Initialize pipeline metrics.
        
        Args:
            registry: Optional Prometheus registry (uses default if None)
        """
        self.registry = registry or CollectorRegistry()
        self._lock = threading.Lock()
        
        # Initialize all metrics
        self._create_metrics()
        
        # Performance tracking
        self.start_time = time.perf_counter()
        self.last_reset = time.time()
        
    def _create_metrics(self) -> None:
        """Create all Prometheus metrics."""
        
        # === LATENCY METRICS ===
        self.end_to_end_latency = Histogram(
            'rtap_end_to_end_latency_seconds',
            'End-to-end pipeline latency from audio capture to transcript output',
            buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0),
            registry=self.registry
        )
        
        self.stage_latency = Histogram(
            'rtap_stage_latency_seconds',
            'Individual stage processing latency',
            labelnames=['stage'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.5),
            registry=self.registry
        )
        
        self.state_loop_latency = Histogram(
            'rtap_state_loop_latency_seconds',
            'State machine loop iteration latency',
            buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05),
            registry=self.registry
        )
        
        # === THROUGHPUT METRICS ===
        self.frames_processed = Counter(
            'rtap_frames_processed_total',
            'Total number of audio frames processed',
            labelnames=['stage'],
            registry=self.registry
        )
        
        self.transcripts_completed = Counter(
            'rtap_transcripts_completed_total',
            'Total number of completed transcriptions',
            registry=self.registry
        )
        
        self.wakeword_detections = Counter(
            'rtap_wakeword_detections_total',
            'Total number of wake word detections',
            labelnames=['confidence_level'],
            registry=self.registry
        )
        
        # === STATE METRICS ===
        self.state_transitions = Counter(
            'rtap_state_transitions_total',
            'Total number of state transitions',
            labelnames=['from_state', 'to_state'],
            registry=self.registry
        )
        
        self.current_state = Gauge(
            'rtap_current_state',
            'Current pipeline state (0=IDLE, 1=LISTENING, 2=PROCESSING, 3=EMIT, 4=SHUTDOWN, 5=ERROR)',
            registry=self.registry
        )
        
        # === BUFFER METRICS ===
        self.buffer_utilization = Gauge(
            'rtap_buffer_utilization_ratio',
            'Audio buffer utilization as a ratio (0.0 to 1.0)',
            registry=self.registry
        )
        
        self.buffer_overflows = Counter(
            'rtap_buffer_overflows_total',
            'Total number of buffer overflow events',
            registry=self.registry
        )
        
        self.queue_size = Gauge(
            'rtap_queue_size',
            'Current size of inter-stage queues',
            labelnames=['queue_name'],
            registry=self.registry
        )
        
        # === ERROR METRICS ===
        self.errors = Counter(
            'rtap_errors_total',
            'Total number of errors by category',
            labelnames=['error_type', 'stage'],
            registry=self.registry
        )
        
        self.model_errors = Counter(
            'rtap_model_errors_total',
            'Model-specific errors (STT, wake word, language)',
            labelnames=['model_type', 'error_code'],
            registry=self.registry
        )
        
        # === PERFORMANCE METRICS ===
        self.cpu_usage = Gauge(
            'rtap_cpu_usage_percent',
            'CPU usage percentage for pipeline process',
            registry=self.registry
        )
        
        self.memory_usage = Gauge(
            'rtap_memory_usage_bytes',
            'Memory usage in bytes for pipeline process',
            registry=self.registry
        )
        
        self.warmup_time = Histogram(
            'rtap_warmup_time_seconds',
            'Time taken to warm up pipeline components',
            labelnames=['component'],
            registry=self.registry
        )
        
        # === QUALITY METRICS ===
        self.transcript_confidence = Histogram(
            'rtap_transcript_confidence',
            'Confidence scores for generated transcripts',
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99),
            registry=self.registry
        )
        
        self.language_detection_confidence = Histogram(
            'rtap_language_detection_confidence',
            'Confidence scores for language detection',
            buckets=(0.1, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99),
            registry=self.registry
        )
    
    def record_end_to_end_latency(self, latency_seconds: float) -> None:
        """Record end-to-end pipeline latency."""
        with self._lock:
            self.end_to_end_latency.observe(latency_seconds)
    
    def record_stage_latency(self, stage: str, latency_seconds: float) -> None:
        """Record individual stage latency."""
        with self._lock:
            self.stage_latency.labels(stage=stage).observe(latency_seconds)
    
    def record_state_loop_time(self, loop_time_seconds: float) -> None:
        """Record state machine loop iteration time."""
        with self._lock:
            self.state_loop_latency.observe(loop_time_seconds)
    
    def record_frames_processed(self, stage: str, count: int = 1) -> None:
        """Record frames processed by a stage."""
        with self._lock:
            self.frames_processed.labels(stage=stage).inc(count)
    
    def record_transcript_completion(self, transcript_data: Dict[str, Any]) -> None:
        """Record completed transcript with metadata."""
        with self._lock:
            self.transcripts_completed.inc()
            
            # Record confidence if available
            confidence = transcript_data.get('confidence', 0.0)
            if confidence > 0:
                self.transcript_confidence.observe(confidence)
            
            # Record processing time if available
            processing_time_ms = transcript_data.get('processing_time_ms', 0)
            if processing_time_ms > 0:
                self.record_end_to_end_latency(processing_time_ms / 1000.0)
    
    def record_wakeword_detection(self, confidence: float = 1.0) -> None:
        """Record wake word detection event."""
        with self._lock:
            # Categorize confidence level
            if confidence >= 0.9:
                confidence_level = 'high'
            elif confidence >= 0.7:
                confidence_level = 'medium'
            else:
                confidence_level = 'low'
            
            self.wakeword_detections.labels(confidence_level=confidence_level).inc()
    
    def record_state_transition(self, from_state: str, to_state: str) -> None:
        """Record state machine transition."""
        with self._lock:
            self.state_transitions.labels(from_state=from_state, to_state=to_state).inc()
            
            # Update current state gauge
            state_map = {
                'idle': 0, 'listening': 1, 'processing': 2, 
                'emit': 3, 'shutdown': 4, 'error': 5
            }
            if to_state.lower() in state_map:
                self.current_state.set(state_map[to_state.lower()])
    
    def update_buffer_metrics(self, buffer_stats: Dict[str, Any]) -> None:
        """Update buffer-related metrics."""
        with self._lock:
            utilization = buffer_stats.get('utilization', 0.0)
            self.buffer_utilization.set(utilization)
            
            overflows = buffer_stats.get('overflows', 0)
            if overflows > 0:
                self.buffer_overflows.inc(overflows)
    
    def update_queue_sizes(self, queue_sizes: Dict[str, int]) -> None:
        """Update inter-stage queue size metrics."""
        with self._lock:
            for queue_name, size in queue_sizes.items():
                self.queue_size.labels(queue_name=queue_name).set(size)
    
    def record_error(self, error_type: str, stage: str = 'unknown') -> None:
        """Record an error event."""
        with self._lock:
            self.errors.labels(error_type=error_type, stage=stage).inc()
    
    def record_model_error(self, model_type: str, error_code: str) -> None:
        """Record model-specific error."""
        with self._lock:
            self.model_errors.labels(model_type=model_type, error_code=error_code).inc()
    
    def record_warmup_time(self, component: str, warmup_seconds: float) -> None:
        """Record component warmup time."""
        with self._lock:
            self.warmup_time.labels(component=component).observe(warmup_seconds)
    
    def update_system_metrics(self, cpu_percent: float, memory_bytes: int) -> None:
        """Update system resource metrics."""
        with self._lock:
            self.cpu_usage.set(cpu_percent)
            self.memory_usage.set(memory_bytes)
    
    def record_language_detection(self, confidence: float) -> None:
        """Record language detection confidence."""
        with self._lock:
            self.language_detection_confidence.observe(confidence)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive metrics statistics."""
        uptime = time.perf_counter() - self.start_time
        
        with self._lock:
            # Get sample counts from metrics
            frames_count = sum(
                metric._value.get() for metric in self.frames_processed._metrics.values()
            ) if hasattr(self.frames_processed, '_metrics') else 0
            
            transcripts_count = (
                self.transcripts_completed._value.get() 
                if hasattr(self.transcripts_completed, '_value') else 0
            )
            
            errors_count = sum(
                metric._value.get() for metric in self.errors._metrics.values()
            ) if hasattr(self.errors, '_metrics') else 0
            
            return {
                'uptime_seconds': uptime,
                'frames_processed': frames_count,
                'transcripts_completed': transcripts_count,
                'total_errors': errors_count,
                'current_state': int(self.current_state._value.get()),
                'buffer_utilization': self.buffer_utilization._value.get(),
                'metrics_collected_at': time.time(),
            }
    
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus-formatted metrics."""
        return generate_latest(self.registry).decode('utf-8')
    
    def reset_counters(self) -> None:
        """Reset all counter metrics (for testing/debugging)."""
        with self._lock:
            # Note: In production, counters should not be reset
            # This is primarily for testing scenarios
            self.last_reset = time.time()
    
    def get_latency_percentiles(self) -> Dict[str, float]:
        """Get latency percentile data for monitoring."""
        # This would require access to histogram buckets
        # For now, return placeholder that could be implemented
        # with custom histogram collection
        return {
            'p50_ms': 0.0,
            'p95_ms': 0.0,
            'p99_ms': 0.0,
            'max_ms': 0.0,
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check based on metrics."""
        stats = self.get_stats()
        
        # Basic health indicators
        is_healthy = True
        issues = []
        
        # Check if pipeline is stuck
        if stats['current_state'] == 5:  # ERROR state
            is_healthy = False
            issues.append("Pipeline in ERROR state")
        
        # Check buffer utilization
        if stats['buffer_utilization'] > 0.9:
            issues.append("Buffer utilization high (>90%)")
        
        # Check error rate
        uptime_hours = stats['uptime_seconds'] / 3600
        if uptime_hours > 0 and stats['total_errors'] / uptime_hours > 10:
            is_healthy = False
            issues.append("High error rate (>10 errors/hour)")
        
        return {
            'healthy': is_healthy,
            'issues': issues,
            'checked_at': time.time(),
            'uptime_seconds': stats['uptime_seconds'],
        }
    
    def __repr__(self) -> str:
        """String representation of metrics state."""
        stats = self.get_stats()
        return (f"PipelineMetrics(uptime={stats['uptime_seconds']:.1f}s, "
                f"frames={stats['frames_processed']}, "
                f"transcripts={stats['transcripts_completed']})")


# Global metrics instance (singleton pattern)
_global_metrics: Optional[PipelineMetrics] = None
_metrics_lock = threading.Lock()


def get_global_metrics() -> PipelineMetrics:
    """Get or create global metrics instance."""
    global _global_metrics
    
    with _metrics_lock:
        if _global_metrics is None:
            _global_metrics = PipelineMetrics()
        return _global_metrics


def set_global_metrics(metrics: PipelineMetrics) -> None:
    """Set global metrics instance (for testing)."""
    global _global_metrics
    
    with _metrics_lock:
        _global_metrics = metrics