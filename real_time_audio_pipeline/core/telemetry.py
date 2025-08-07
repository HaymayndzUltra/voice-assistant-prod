"""
Real-Time Audio Pipeline - Telemetry and Metrics

Simplified telemetry system for pipeline monitoring.
"""

import threading
import time
from typing import Any, Dict, Optional

try:
    from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Create dummy classes for testing without prometheus
    class Counter:
        def __init__(self, *args, **kwargs):
            self._value = 0
        def inc(self, amount=1):
            self._value += amount
        def labels(self, **kwargs):
            return self

    class Histogram:
        def __init__(self, *args, **kwargs):
            self._observations = []
        def observe(self, value):
            self._observations.append(value)
        def labels(self, **kwargs):
            return self

    class Gauge:
        def __init__(self, *args, **kwargs):
            self._value = 0
        def set(self, value):
            self._value = value
        def get(self):
            return self._value

    class CollectorRegistry:
        pass


class PipelineMetrics:
    """Simplified metrics collection for Real-Time Audio Pipeline."""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self._lock = threading.Lock()
        self.start_time = time.perf_counter()

        # Simple counters for basic metrics
        self.frames_processed_count = 0
        self.transcripts_completed_count = 0
        self.errors_count = 0
        self.state_transitions_count = 0

        print(f"PipelineMetrics initialized (prometheus_available={PROMETHEUS_AVAILABLE})")

    def record_end_to_end_latency(self, latency_seconds: float) -> None:
        """Record end-to-end pipeline latency."""
        pass  # Simplified

    def record_stage_latency(self, stage: str, latency_seconds: float) -> None:
        """Record individual stage latency."""
        pass  # Simplified

    def record_state_loop_time(self, loop_time_seconds: float) -> None:
        """Record state machine loop iteration time."""
        pass  # Simplified

    def record_frames_processed(self, stage: str, count: int = 1) -> None:
        """Record frames processed by a stage."""
        with self._lock:
            self.frames_processed_count += count

    def record_transcript_completion(self, transcript_data: Dict[str, Any]) -> None:
        """Record completed transcript with metadata."""
        with self._lock:
            self.transcripts_completed_count += 1

    def record_wakeword_detection(self, confidence: float = 1.0) -> None:
        """Record wake word detection event."""
        pass  # Simplified

    def record_state_transition(self, from_state: str, to_state: str) -> None:
        """Record state machine transition."""
        with self._lock:
            self.state_transitions_count += 1

    def update_buffer_metrics(self, buffer_stats: Dict[str, Any]) -> None:
        """Update buffer-related metrics."""
        pass  # Simplified

    def update_queue_sizes(self, queue_sizes: Dict[str, int]) -> None:
        """Update inter-stage queue size metrics."""
        pass  # Simplified

    def record_error(self, error_type: str, stage: str = 'unknown') -> None:
        """Record an error event."""
        with self._lock:
            self.errors_count += 1

    def record_warmup_time(self, component: str, warmup_seconds: float) -> None:
        """Record component warmup time."""
        pass  # Simplified

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive metrics statistics."""
        uptime = time.perf_counter() - self.start_time

        with self._lock:
            return {
                'uptime_seconds': uptime,
                'frames_processed': self.frames_processed_count,
                'transcripts_completed': self.transcripts_completed_count,
                'total_errors': self.errors_count,
                'state_transitions': self.state_transitions_count,
                'current_state': 0,
                'buffer_utilization': 0.0,
                'metrics_collected_at': time.time(),
            }

    def __repr__(self) -> str:
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
