"""
Standardized Data Models for Cross-System Communication

This module defines Pydantic models for all critical, cross-system data structures.
These models serve as a single source of truth for data exchanged between agents
across the distributed system.
"""

from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Standardized task status values"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ErrorSeverity(str, Enum):
    """Standardized error severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class TaskDefinition(BaseModel):
    """Standardized task definition model"""
    task_id: str = Field(..., description="Unique identifier for the task")
    agent_id: str = Field(..., description="ID of the agent that created the task")
    task_type: str = Field(..., description="Type of task to be performed")
    priority: int = Field(default=1, description="Task priority (1-10, higher is more important)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Task-specific parameters")
    dependencies: List[str] = Field(default_factory=list, description="List of task IDs that must complete before this task")
    timeout_seconds: Optional[int] = Field(default=None, description="Maximum time allowed for task execution")
    created_at: datetime = Field(default_factory=datetime.now, description="Task creation timestamp")
    scheduled_for: Optional[datetime] = Field(default=None, description="When the task should be executed")

    # Added computed helper property for backward-compatibility with older code that used task.description
    @property
    def description(self) -> str:  # type: ignore[override]
        """Return a human-readable task description.
        Looks for 'description', 'prompt', or 'text' inside parameters.
        This avoids AttributeError in legacy code while keeping the model immutable.
        """
        return str(self.parameters.get("description") or
                   self.parameters.get("prompt") or
                   self.parameters.get("text") or
                   "")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task-123456",
                "agent_id": "translator-agent",
                "task_type": "translate_text",
                "priority": 3,
                "parameters": {
                    "text": "Hello world",
                    "source_language": "en",
                    "target_language": "es"
                },
                "dependencies": [],
                "timeout_seconds": 30,
                "created_at": "2025-07-01T12:00:00Z",
                "scheduled_for": None
            }
        }


class TaskResult(BaseModel):
    """Standardized task result model"""
    task_id: str = Field(..., description="ID of the task this result belongs to")
    agent_id: str = Field(..., description="ID of the agent that processed the task")
    status: TaskStatus = Field(..., description="Final status of the task")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Task-specific result data")
    error: Optional[str] = Field(default=None, description="Error message if task failed")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Performance metrics for the task")
    started_at: datetime = Field(default_factory=datetime.now, description="When task execution started")
    completed_at: Optional[datetime] = Field(default=None, description="When task execution completed")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task-123456",
                "agent_id": "translator-agent",
                "status": "completed",
                "result": {
                    "translated_text": "Hola mundo"
                },
                "error": None,
                "metrics": {
                    "execution_time_ms": 245,
                    "model_used": "nllb-200-distilled-600M"
                },
                "started_at": "2025-07-01T12:00:05Z",
                "completed_at": "2025-07-01T12:00:05.245Z"
            }
        }


class SystemEvent(BaseModel):
    """Standardized system event model for cross-agent communication"""
    event_id: str = Field(..., description="Unique identifier for the event")
    event_type: str = Field(..., description="Type of event")
    source_agent: str = Field(..., description="ID of the agent that generated the event")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the event occurred")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event-specific data")
    propagate: bool = Field(default=False, description="Whether this event should be propagated to other machines")
    ttl: int = Field(default=3, description="Time-to-live for propagated events (hop count)")

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt-789012",
                "event_type": "model_loaded",
                "source_agent": "model-manager",
                "timestamp": "2025-07-01T12:01:00Z",
                "data": {
                    "model_id": "whisper-large-v3",
                    "device": "cuda:0",
                    "vram_mb": 4200
                },
                "propagate": True,
                "ttl": 3
            }
        }


class ErrorReport(BaseModel):
    """Standardized error report model"""
    error_id: str = Field(..., description="Unique identifier for the error")
    agent_id: str = Field(..., description="ID of the agent that reported the error")
    severity: ErrorSeverity = Field(..., description="Severity level of the error")
    error_type: str = Field(..., description="Type or category of error")
    message: str = Field(..., description="Human-readable error message")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the error occurred")
    context: Dict[str, Any] = Field(default_factory=dict, description="Contextual information about the error")
    stack_trace: Optional[str] = Field(default=None, description="Stack trace if available")
    related_task_id: Optional[str] = Field(default=None, description="ID of related task if applicable")
    recovery_attempted: bool = Field(default=False, description="Whether recovery was attempted")
    recovery_successful: Optional[bool] = Field(default=None, description="Whether recovery was successful")

    class Config:
        json_schema_extra = {
            "example": {
                "error_id": "err-345678",
                "agent_id": "streaming-tts",
                "severity": "error",
                "error_type": "connection_failure",
                "message": "Failed to connect to TTS service endpoint",
                "timestamp": "2025-07-01T12:02:30Z",
                "context": {
                    "endpoint": "http://tts-service:5000/synthesize",
                    "attempt": 3,
                    "timeout_ms": 5000
                },
                "stack_trace": "Traceback (most recent call last):\n  File \"tts_agent.py\", line 142...",
                "related_task_id": "task-123456",
                "recovery_attempted": True,
                "recovery_successful": False
            }
        }


class PerformanceMetric(BaseModel):
    """Standardized performance metric model"""
    metric_id: str = Field(..., description="Unique identifier for the metric")
    agent_id: str = Field(..., description="ID of the agent that reported the metric")
    metric_type: str = Field(..., description="Type of metric being reported")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the metric was recorded")
    value: Union[float, int, str, bool] = Field(..., description="Metric value")
    unit: Optional[str] = Field(default=None, description="Unit of measurement")
    dimensions: Dict[str, str] = Field(default_factory=dict, description="Metric dimensions for aggregation")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

    class Config:
        json_schema_extra = {
            "example": {
                "metric_id": "metric-901234",
                "agent_id": "speech-recognition",
                "metric_type": "latency",
                "timestamp": "2025-07-01T12:03:15Z",
                "value": 320.5,
                "unit": "ms",
                "dimensions": {
                    "model": "whisper-large-v3",
                    "audio_length": "5s",
                    "language": "en"
                },
                "tags": ["speech", "recognition", "performance"]
            }
        }


class AgentRegistration(BaseModel):
    """Model for agent registration with the system digital twin"""
    agent_id: str = Field(..., description="Unique identifier for the agent")
    agent_type: str = Field(..., description="Type or category of the agent")
    host: str = Field(..., description="Hostname or IP address where the agent is running")
    port: int = Field(..., description="Port number the agent is listening on")
    health_check_port: Optional[int] = Field(default=None, description="Port for health check endpoint")
    capabilities: List[str] = Field(default_factory=list, description="List of agent capabilities")
    dependencies: List[str] = Field(default_factory=list, description="List of dependencies on other agents")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional agent metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "translator-agent",
                "agent_type": "language_processing",
                "host": "10.0.0.5",
                "port": 5564,
                "health_check_port": 5565,
                "capabilities": ["text_translation", "language_detection"],
                "dependencies": ["model-manager", "memory-orchestrator"],
                "metadata": {
                    "version": "2.3.0",
                    "supported_languages": ["en", "es", "fr", "de", "zh"]
                }
            }
        } 