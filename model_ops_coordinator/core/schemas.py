"""Pydantic schemas and data models for ModelOps Coordinator."""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class ModelStatus(str, Enum):
    """Model status enumeration."""
    LOADING = "loading"
    LOADED = "loaded"
    UNLOADING = "unloading"
    FAILED = "failed"
    UNKNOWN = "unknown"


class JobStatus(str, Enum):
    """Learning job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GoalPriority(str, Enum):
    """Goal priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Configuration Schemas
class ServerConfig(BaseModel):
    """Server configuration schema."""
    zmq_port: int = Field(default=7211, description="ZMQ server port")
    grpc_port: int = Field(default=7212, description="gRPC server port")
    rest_port: int = Field(default=8008, description="REST API port")
    max_workers: int = Field(default=16, description="Maximum worker threads")


class ResourceConfig(BaseModel):
    """Resource management configuration."""
    gpu_poll_interval: int = Field(default=5, description="GPU polling interval in seconds")
    vram_soft_limit_mb: int = Field(default=22000, description="VRAM soft limit in MB")
    eviction_threshold_pct: int = Field(default=90, description="Eviction threshold percentage")


class ModelPreloadConfig(BaseModel):
    """Model preload configuration."""
    name: str = Field(description="Model name")
    path: str = Field(description="Model file path")
    shards: int = Field(default=1, description="Number of shards")


class ModelsConfig(BaseModel):
    """Models configuration schema."""
    preload: List[ModelPreloadConfig] = Field(default=[], description="Models to preload")
    default_dtype: str = Field(default="float16", description="Default data type")
    quantization: bool = Field(default=True, description="Enable quantization")


class LearningConfig(BaseModel):
    """Learning configuration schema."""
    enable_auto_tune: bool = Field(default=True, description="Enable auto-tuning")
    max_parallel_jobs: int = Field(default=2, description="Maximum parallel jobs")
    job_store: str = Field(default="/workspace/learning_jobs.db", description="Job store path")


class GoalsConfig(BaseModel):
    """Goals configuration schema."""
    policy: str = Field(default="priority_queue", description="Goal management policy")
    max_active_goals: int = Field(default=10, description="Maximum active goals")


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""
    failure_threshold: int = Field(default=4, description="Failure threshold")
    reset_timeout: int = Field(default=20, description="Reset timeout in seconds")


class BulkheadConfig(BaseModel):
    """Bulkhead configuration."""
    max_concurrent: int = Field(default=64, description="Maximum concurrent operations")
    max_queue_size: int = Field(default=256, description="Maximum queue size")


class ResilienceConfig(BaseModel):
    """Resilience configuration schema."""
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    bulkhead: BulkheadConfig = Field(default_factory=BulkheadConfig)


class Config(BaseModel):
    """Main configuration schema."""
    title: str = Field(default="ModelOpsCoordinatorConfig", description="Configuration title")
    version: str = Field(default="1.0", description="Configuration version")
    server: ServerConfig = Field(default_factory=ServerConfig)
    resources: ResourceConfig = Field(default_factory=ResourceConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    learning: LearningConfig = Field(default_factory=LearningConfig)
    goals: GoalsConfig = Field(default_factory=GoalsConfig)
    resilience: ResilienceConfig = Field(default_factory=ResilienceConfig)


# API Request/Response Schemas
class InferenceRequest(BaseModel):
    """Inference request schema."""
    model_name: str = Field(description="Name of the model to use")
    prompt: str = Field(description="Input prompt for inference")
    parameters: Optional[Dict[str, Any]] = Field(default={}, description="Additional parameters")
    max_tokens: Optional[int] = Field(default=100, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(default=0.7, description="Sampling temperature")


class InferenceResponse(BaseModel):
    """Inference response schema."""
    response_text: str = Field(description="Generated response text")
    tokens_generated: int = Field(description="Number of tokens generated")
    inference_time_ms: float = Field(description="Inference time in milliseconds")
    status: str = Field(description="Operation status")
    error_message: Optional[str] = Field(default=None, description="Error message if any")


class ModelLoadRequest(BaseModel):
    """Model load request schema."""
    model_name: str = Field(description="Name of the model")
    model_path: str = Field(description="Path to the model file")
    load_params: Optional[Dict[str, Any]] = Field(default={}, description="Load parameters")
    shards: Optional[int] = Field(default=1, description="Number of shards")


class ModelLoadResponse(BaseModel):
    """Model load response schema."""
    success: bool = Field(description="Whether the operation succeeded")
    message: str = Field(description="Operation message")
    model_id: Optional[str] = Field(default=None, description="Loaded model ID")
    vram_used_mb: Optional[int] = Field(default=None, description="VRAM used in MB")


class ModelUnloadRequest(BaseModel):
    """Model unload request schema."""
    model_name: str = Field(description="Name of the model to unload")
    force: bool = Field(default=False, description="Force unload if true")


class ModelUnloadResponse(BaseModel):
    """Model unload response schema."""
    success: bool = Field(description="Whether the operation succeeded")
    message: str = Field(description="Operation message")
    vram_freed_mb: Optional[int] = Field(default=None, description="VRAM freed in MB")


class ModelInfo(BaseModel):
    """Model information schema."""
    name: str = Field(description="Model name")
    path: str = Field(description="Model file path")
    status: ModelStatus = Field(description="Current model status")
    vram_mb: int = Field(description="VRAM usage in MB")
    shards: int = Field(description="Number of shards")
    load_time: Optional[datetime] = Field(default=None, description="Load timestamp")


class ModelListResponse(BaseModel):
    """Model list response schema."""
    models: List[ModelInfo] = Field(description="List of models")
    total_count: int = Field(description="Total number of models")
    total_vram_mb: int = Field(description="Total VRAM usage in MB")


# Learning Job Schemas
class LearningJob(BaseModel):
    """Learning job schema."""
    job_id: str = Field(description="Unique job identifier")
    job_type: str = Field(description="Type of learning job")
    model_name: str = Field(description="Target model name")
    dataset_path: str = Field(description="Path to training dataset")
    parameters: Dict[str, Any] = Field(default={}, description="Job parameters")
    status: JobStatus = Field(default=JobStatus.PENDING, description="Job status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    progress: float = Field(default=0.0, description="Job progress (0.0-1.0)")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")


class LearningJobRequest(BaseModel):
    """Learning job creation request."""
    job_type: str = Field(description="Type of learning job")
    model_name: str = Field(description="Target model name")
    dataset_path: str = Field(description="Path to training dataset")
    parameters: Optional[Dict[str, Any]] = Field(default={}, description="Job parameters")


class LearningJobResponse(BaseModel):
    """Learning job response schema."""
    job: LearningJob = Field(description="Learning job details")


class LearningJobListResponse(BaseModel):
    """Learning job list response."""
    jobs: List[LearningJob] = Field(description="List of learning jobs")
    total_count: int = Field(description="Total number of jobs")


# Goal Management Schemas
class Goal(BaseModel):
    """Goal schema."""
    goal_id: str = Field(description="Unique goal identifier")
    title: str = Field(description="Goal title")
    description: str = Field(description="Goal description")
    priority: GoalPriority = Field(default=GoalPriority.MEDIUM, description="Goal priority")
    status: str = Field(default="active", description="Goal status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    target_completion: Optional[datetime] = Field(default=None, description="Target completion time")
    progress: float = Field(default=0.0, description="Goal progress (0.0-1.0)")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")


class GoalRequest(BaseModel):
    """Goal creation/update request."""
    title: str = Field(description="Goal title")
    description: str = Field(description="Goal description")
    priority: Optional[GoalPriority] = Field(default=GoalPriority.MEDIUM, description="Goal priority")
    target_completion: Optional[datetime] = Field(default=None, description="Target completion time")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional metadata")


class GoalResponse(BaseModel):
    """Goal response schema."""
    goal: Goal = Field(description="Goal details")


class GoalListResponse(BaseModel):
    """Goal list response."""
    goals: List[Goal] = Field(description="List of goals")
    total_count: int = Field(description="Total number of goals")


# System Status Schemas
class SystemStatus(BaseModel):
    """System status schema."""
    uptime_seconds: int = Field(description="System uptime in seconds")
    cpu_usage_percent: float = Field(description="CPU usage percentage")
    memory_usage_mb: int = Field(description="Memory usage in MB")
    total_memory_mb: int = Field(description="Total memory in MB")
    gpu_usage_percent: float = Field(description="GPU usage percentage")
    vram_usage_mb: int = Field(description="VRAM usage in MB")
    total_vram_mb: int = Field(description="Total VRAM in MB")
    active_models: int = Field(description="Number of active models")
    active_jobs: int = Field(description="Number of active learning jobs")
    active_goals: int = Field(description="Number of active goals")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(description="Service health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    version: str = Field(description="Service version")
    components: Dict[str, str] = Field(description="Component status map")


# Error Schemas
class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(default=None, description="Request ID for tracking")