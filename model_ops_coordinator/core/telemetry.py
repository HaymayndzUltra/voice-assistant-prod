"""Telemetry and metrics collection for ModelOps Coordinator."""

import time
from typing import Dict, Optional
from prometheus_client import Counter, Gauge, Histogram, Info, CollectorRegistry
from threading import Lock


class Telemetry:
    """Prometheus metrics collector for ModelOps Coordinator."""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """Initialize telemetry with optional custom registry."""
        self.registry = registry
        self._lock = Lock()
        self._start_time = time.time()

        # System info
        self.service_info = Info(
            'modelops_service_info',
            'ModelOps Coordinator service information',
            registry=self.registry
        )
        self.service_info.info({
            'version': '1.0.0',
            'component': 'modelops_coordinator'
        })

        # System metrics
        self.uptime_seconds = Gauge(
            'modelops_uptime_seconds',
            'Service uptime in seconds',
            registry=self.registry
        )

        self.cpu_usage_percent = Gauge(
            'modelops_cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )

        self.memory_usage_bytes = Gauge(
            'modelops_memory_usage_bytes',
            'Memory usage in bytes',
            registry=self.registry
        )

        self.memory_total_bytes = Gauge(
            'modelops_memory_total_bytes',
            'Total memory in bytes',
            registry=self.registry
        )

        # GPU metrics
        self.gpu_usage_percent = Gauge(
            'modelops_gpu_usage_percent',
            'GPU usage percentage',
            registry=self.registry
        )

        self.vram_usage_bytes = Gauge(
            'modelops_vram_usage_bytes',
            'VRAM usage in bytes',
            registry=self.registry
        )

        self.vram_total_bytes = Gauge(
            'modelops_vram_total_bytes',
            'Total VRAM in bytes',
            registry=self.registry
        )

        # Model metrics
        self.models_loaded_total = Gauge(
            'modelops_models_loaded_total',
            'Total number of loaded models',
            registry=self.registry
        )

        self.model_load_counter = Counter(
            'modelops_model_loads_total',
            'Total number of model load attempts',
            ['model_name', 'status'],
            registry=self.registry
        )

        self.model_unload_counter = Counter(
            'modelops_model_unloads_total',
            'Total number of model unload attempts',
            ['model_name', 'status'],
            registry=self.registry
        )

        self.model_load_duration = Histogram(
            'modelops_model_load_duration_seconds',
            'Model load duration in seconds',
            ['model_name'],
            registry=self.registry
        )

        self.model_vram_usage = Gauge(
            'modelops_model_vram_usage_bytes',
            'VRAM usage per model in bytes',
            ['model_name'],
            registry=self.registry
        )

        # Inference metrics
        self.inference_requests_total = Counter(
            'modelops_inference_requests_total',
            'Total number of inference requests',
            ['model_name', 'status'],
            registry=self.registry
        )

        self.inference_duration = Histogram(
            'modelops_inference_duration_seconds',
            'Inference duration in seconds',
            ['model_name'],
            registry=self.registry
        )

        self.inference_tokens_generated = Counter(
            'modelops_inference_tokens_generated_total',
            'Total tokens generated',
            ['model_name'],
            registry=self.registry
        )

        self.inference_active_requests = Gauge(
            'modelops_inference_active_requests',
            'Number of active inference requests',
            ['model_name'],
            registry=self.registry
        )

        # Learning job metrics
        self.learning_jobs_total = Gauge(
            'modelops_learning_jobs_total',
            'Total number of learning jobs',
            ['status'],
            registry=self.registry
        )

        self.learning_job_duration = Histogram(
            'modelops_learning_job_duration_seconds',
            'Learning job duration in seconds',
            ['job_type'],
            registry=self.registry
        )

        # Goal metrics
        self.goals_total = Gauge(
            'modelops_goals_total',
            'Total number of goals',
            ['status', 'priority'],
            registry=self.registry
        )

        self.goal_completion_time = Histogram(
            'modelops_goal_completion_time_seconds',
            'Goal completion time in seconds',
            ['priority'],
            registry=self.registry
        )

        # Circuit breaker metrics
        self.circuit_breaker_state = Gauge(
            'modelops_circuit_breaker_state',
            'Circuit breaker state (0=closed, 1=open, 2=half-open)',
            ['operation'],
            registry=self.registry
        )

        self.circuit_breaker_failures = Counter(
            'modelops_circuit_breaker_failures_total',
            'Total circuit breaker failures',
            ['operation'],
            registry=self.registry
        )

        # Bulkhead metrics
        self.bulkhead_rejections = Counter(
            'modelops_bulkhead_rejections_total',
            'Total bulkhead rejections',
            ['operation'],
            registry=self.registry
        )

        self.bulkhead_active_requests = Gauge(
            'modelops_bulkhead_active_requests',
            'Active requests in bulkhead',
            ['operation'],
            registry=self.registry
        )

        self.bulkhead_queue_size = Gauge(
            'modelops_bulkhead_queue_size',
            'Bulkhead queue size',
            ['operation'],
            registry=self.registry
        )

        # Error metrics
        self.errors_total = Counter(
            'modelops_errors_total',
            'Total number of errors',
            ['error_type', 'component'],
            registry=self.registry
        )

    def update_uptime(self):
        """Update service uptime metric."""
        with self._lock:
            uptime = time.time() - self._start_time
            self.uptime_seconds.set(uptime)

    def update_system_metrics(self, cpu_percent: float, memory_used: int, memory_total: int):
        """Update system resource metrics."""
        self.cpu_usage_percent.set(cpu_percent)
        self.memory_usage_bytes.set(memory_used)
        self.memory_total_bytes.set(memory_total)

    def update_gpu_metrics(self, gpu_percent: float, vram_used: int, vram_total: int):
        """Update GPU resource metrics."""
        self.gpu_usage_percent.set(gpu_percent)
        self.vram_usage_bytes.set(vram_used)
        self.vram_total_bytes.set(vram_total)

    def record_model_load(self, model_name: str, success: bool,
                          duration: float, vram_usage: int = 0):
        """Record model load metrics."""
        status = "success" if success else "failure"
        self.model_load_counter.labels(model_name=model_name, status=status).inc()
        self.model_load_duration.labels(model_name=model_name).observe(duration)

        if success and vram_usage > 0:
            self.model_vram_usage.labels(model_name=model_name).set(vram_usage)
            # Update total loaded models
            self.models_loaded_total.inc()

    def record_model_unload(self, model_name: str, success: bool):
        """Record model unload metrics."""
        status = "success" if success else "failure"
        self.model_unload_counter.labels(model_name=model_name, status=status).inc()

        if success:
            # Remove model VRAM usage
            self.model_vram_usage.remove(model_name)
            # Update total loaded models
            self.models_loaded_total.dec()

    def record_inference(self, model_name: str, success: bool, duration: float, tokens: int = 0):
        """Record inference metrics."""
        status = "success" if success else "failure"
        self.inference_requests_total.labels(model_name=model_name, status=status).inc()

        if success:
            self.inference_duration.labels(model_name=model_name).observe(duration)
            if tokens > 0:
                self.inference_tokens_generated.labels(model_name=model_name).inc(tokens)

    def set_active_inference_requests(self, model_name: str, count: int):
        """Set active inference request count for a model."""
        self.inference_active_requests.labels(model_name=model_name).set(count)

    def update_learning_jobs(self, status_counts: Dict[str, int]):
        """Update learning job metrics by status."""
        for status, count in status_counts.items():
            self.learning_jobs_total.labels(status=status).set(count)

    def record_learning_job_completion(self, job_type: str, duration: float):
        """Record learning job completion."""
        self.learning_job_duration.labels(job_type=job_type).observe(duration)

    def update_goals(self, status_priority_counts: Dict[str, Dict[str, int]]):
        """Update goal metrics by status and priority."""
        for status, priority_counts in status_priority_counts.items():
            for priority, count in priority_counts.items():
                self.goals_total.labels(status=status, priority=priority).set(count)

    def record_goal_completion(self, priority: str, completion_time: float):
        """Record goal completion time."""
        self.goal_completion_time.labels(priority=priority).observe(completion_time)

    def update_circuit_breaker(self, operation: str, state: int, failures: int = 0):
        """Update circuit breaker metrics."""
        self.circuit_breaker_state.labels(operation=operation).set(state)
        if failures > 0:
            self.circuit_breaker_failures.labels(operation=operation).inc(failures)

    def record_bulkhead_rejection(self, operation: str):
        """Record bulkhead rejection."""
        self.bulkhead_rejections.labels(operation=operation).inc()

    def update_bulkhead_metrics(self, operation: str, active_requests: int, queue_size: int):
        """Update bulkhead metrics."""
        self.bulkhead_active_requests.labels(operation=operation).set(active_requests)
        self.bulkhead_queue_size.labels(operation=operation).set(queue_size)

    def record_error(self, error_type: str, component: str):
        """Record error occurrence."""
        self.errors_total.labels(error_type=error_type, component=component).inc()

    def get_metrics_summary(self) -> Dict[str, float]:
        """Get summary of key metrics."""
        return {
            'uptime_seconds': time.time() - self._start_time,
            'models_loaded': self.models_loaded_total._value._value,
            'inference_requests_total': sum(
                counter._value._value for counter in self.inference_requests_total._metrics.values()
            ),
            'errors_total': sum(
                counter._value._value for counter in self.errors_total._metrics.values()
            )
        }
