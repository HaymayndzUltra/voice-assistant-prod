"""Custom exception definitions for ModelOps Coordinator."""


class ModelOpsError(Exception):
    """Base exception for ModelOps Coordinator."""
    
    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"


class ModelLoadError(ModelOpsError):
    """Exception raised when model loading fails."""
    
    def __init__(self, model_name: str, reason: str):
        message = f"Failed to load model '{model_name}': {reason}"
        super().__init__(message, "MODEL_LOAD_ERROR")
        self.model_name = model_name
        self.reason = reason


class ModelUnloadError(ModelOpsError):
    """Exception raised when model unloading fails."""
    
    def __init__(self, model_name: str, reason: str):
        message = f"Failed to unload model '{model_name}': {reason}"
        super().__init__(message, "MODEL_UNLOAD_ERROR")
        self.model_name = model_name
        self.reason = reason


class ModelNotFoundError(ModelOpsError):
    """Exception raised when a requested model is not found."""
    
    def __init__(self, model_name: str):
        message = f"Model '{model_name}' not found"
        super().__init__(message, "MODEL_NOT_FOUND")
        self.model_name = model_name


class GPUUnavailable(ModelOpsError):
    """Exception raised when GPU resources are unavailable."""
    
    def __init__(self, required_vram_mb: int, available_vram_mb: int):
        message = f"Insufficient GPU memory: required {required_vram_mb}MB, available {available_vram_mb}MB"
        super().__init__(message, "GPU_UNAVAILABLE")
        self.required_vram_mb = required_vram_mb
        self.available_vram_mb = available_vram_mb


class VRAMExhausted(ModelOpsError):
    """Exception raised when VRAM is exhausted."""
    
    def __init__(self, total_vram_mb: int, used_vram_mb: int, threshold_pct: int):
        message = f"VRAM exhausted: {used_vram_mb}/{total_vram_mb}MB ({used_vram_mb/total_vram_mb*100:.1f}% > {threshold_pct}%)"
        super().__init__(message, "VRAM_EXHAUSTED")
        self.total_vram_mb = total_vram_mb
        self.used_vram_mb = used_vram_mb
        self.threshold_pct = threshold_pct


class InferenceError(ModelOpsError):
    """Exception raised during inference operations."""
    
    def __init__(self, model_name: str, reason: str):
        message = f"Inference failed for model '{model_name}': {reason}"
        super().__init__(message, "INFERENCE_ERROR")
        self.model_name = model_name
        self.reason = reason


class ConfigurationError(ModelOpsError):
    """Exception raised for configuration-related errors."""
    
    def __init__(self, config_key: str, reason: str):
        message = f"Configuration error for '{config_key}': {reason}"
        super().__init__(message, "CONFIGURATION_ERROR")
        self.config_key = config_key
        self.reason = reason


class CircuitBreakerError(ModelOpsError):
    """Exception raised when circuit breaker is open."""
    
    def __init__(self, operation: str, failure_count: int):
        message = f"Circuit breaker open for '{operation}' (failures: {failure_count})"
        super().__init__(message, "CIRCUIT_BREAKER_OPEN")
        self.operation = operation
        self.failure_count = failure_count


class BulkheadRejection(ModelOpsError):
    """Exception raised when bulkhead pattern rejects request."""
    
    def __init__(self, operation: str, current_load: int, max_capacity: int):
        message = f"Bulkhead rejection for '{operation}': {current_load}/{max_capacity} capacity"
        super().__init__(message, "BULKHEAD_REJECTION")
        self.operation = operation
        self.current_load = current_load
        self.max_capacity = max_capacity


class LearningJobError(ModelOpsError):
    """Exception raised for learning job operations."""
    
    def __init__(self, job_id: str, reason: str):
        message = f"Learning job '{job_id}' error: {reason}"
        super().__init__(message, "LEARNING_JOB_ERROR")
        self.job_id = job_id
        self.reason = reason


class GoalError(ModelOpsError):
    """Exception raised for goal management operations."""
    
    def __init__(self, goal_id: str, reason: str):
        message = f"Goal '{goal_id}' error: {reason}"
        super().__init__(message, "GOAL_ERROR")
        self.goal_id = goal_id
        self.reason = reason