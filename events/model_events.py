"""
Model Events - Event-driven communication for model management
Decouples circular dependencies between ModelManagerAgent, VRAMOptimizerAgent, and other model-related components.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import json

class ModelEventType(Enum):
    """Types of model-related events"""
    # Model lifecycle events
    MODEL_LOAD_REQUESTED = "model_load_requested"
    MODEL_LOADED = "model_loaded"
    MODEL_UNLOAD_REQUESTED = "model_unload_requested"
    MODEL_UNLOADED = "model_unloaded"
    MODEL_LOAD_FAILED = "model_load_failed"
    
    # Resource management events
    VRAM_THRESHOLD_EXCEEDED = "vram_threshold_exceeded"
    VRAM_OPTIMIZED = "vram_optimized"
    GPU_MEMORY_WARNING = "gpu_memory_warning"
    GPU_MEMORY_CRITICAL = "gpu_memory_critical"
    
    # Performance events
    MODEL_PERFORMANCE_DEGRADED = "model_performance_degraded"
    MODEL_INFERENCE_SLOW = "model_inference_slow"
    MODEL_INFERENCE_COMPLETED = "model_inference_completed"
    
    # Health and monitoring events
    MODEL_HEALTH_CHECK = "model_health_check"
    MODEL_HEARTBEAT = "model_heartbeat"
    MODEL_ERROR = "model_error"
    
    # Cross-machine coordination events
    CROSS_MACHINE_MODEL_REQUEST = "cross_machine_model_request"
    CROSS_MACHINE_MODEL_TRANSFER = "cross_machine_model_transfer"
    LOAD_BALANCING_REQUIRED = "load_balancing_required"

class ModelStatus(Enum):
    """Model status states"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    UNLOADING = "unloading"
    ERROR = "error"
    TRANSFERRING = "transferring"

@dataclass
class BaseModelEvent:
    """Base class for all model events"""
    event_type: ModelEventType
    timestamp: datetime = field(default_factory=datetime.now)
    source_agent: str = ""
    machine_id: str = ""
    event_id: str = field(default_factory=lambda: f"evt_{int(datetime.now().timestamp() * 1000)}")
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "source_agent": self.source_agent,
            "machine_id": self.machine_id,
            "event_id": self.event_id,
            "metadata": self.metadata,
            **{k: v for k, v in self.__dict__.items() 
               if k not in ["event_type", "timestamp", "source_agent", "machine_id", "event_id", "metadata"]}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModelEvent':
        """Create event from dictionary"""
        event_type = ModelEventType(data["event_type"])
        timestamp = datetime.fromisoformat(data["timestamp"])
        return cls(
            event_type=event_type,
            timestamp=timestamp,
            source_agent=data.get("source_agent", ""),
            machine_id=data.get("machine_id", ""),
            event_id=data.get("event_id", ""),
            metadata=data.get("metadata", {})
        )

@dataclass
class ModelLoadEvent(BaseModelEvent):
    """Event for model loading operations"""
    model_id: str = ""
    model_path: str = ""
    model_type: str = ""
    expected_vram_mb: int = 0
    priority: int = 0
    requester_agent: str = ""
    loading_parameters: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.event_type:
            self.event_type = ModelEventType.MODEL_LOAD_REQUESTED

@dataclass
class ModelStatusEvent(BaseModelEvent):
    """Event for model status changes"""
    model_id: str = ""
    old_status: Optional[ModelStatus] = None
    new_status: ModelStatus = ModelStatus.UNLOADED
    vram_usage_mb: int = 0
    load_time_seconds: float = 0.0
    error_message: str = ""
    
    def __post_init__(self):
        if not self.event_type:
            self.event_type = ModelEventType.MODEL_LOADED

@dataclass
class VRAMEvent(BaseModelEvent):
    """Event for VRAM-related operations"""
    total_vram_mb: int = 0
    used_vram_mb: int = 0
    available_vram_mb: int = 0
    threshold_percentage: float = 0.0
    affected_models: List[str] = field(default_factory=list)
    optimization_action: str = ""
    bytes_freed: int = 0
    
    def __post_init__(self):
        if not self.event_type:
            self.event_type = ModelEventType.VRAM_THRESHOLD_EXCEEDED

@dataclass
class ModelPerformanceEvent(BaseModelEvent):
    """Event for model performance metrics"""
    model_id: str = ""
    inference_time_ms: float = 0.0
    throughput_tokens_per_second: float = 0.0
    error_rate: float = 0.0
    latency_p95_ms: float = 0.0
    memory_usage_mb: int = 0
    cpu_usage_percent: float = 0.0
    performance_score: float = 0.0
    degradation_reason: str = ""
    
    def __post_init__(self):
        if not self.event_type:
            self.event_type = ModelEventType.MODEL_PERFORMANCE_DEGRADED

@dataclass
class CrossMachineModelEvent(BaseModelEvent):
    """Event for cross-machine model coordination"""
    target_machine: str = ""
    source_machine: str = ""
    model_id: str = ""
    transfer_size_mb: int = 0
    transfer_priority: int = 0
    coordination_type: str = ""  # "request", "transfer", "balance"
    estimated_transfer_time_seconds: int = 0
    bandwidth_requirements_mbps: int = 0
    
    def __post_init__(self):
        if not self.event_type:
            self.event_type = ModelEventType.CROSS_MACHINE_MODEL_REQUEST

@dataclass
class ModelHealthEvent(BaseModelEvent):
    """Event for model health monitoring"""
    model_id: str = ""
    is_healthy: bool = True
    health_score: float = 1.0
    last_inference_time: Optional[datetime] = None
    error_count: int = 0
    warning_count: int = 0
    response_time_ms: float = 0.0
    health_check_details: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.event_type:
            self.event_type = ModelEventType.MODEL_HEALTH_CHECK

# Event factory functions for common use cases
def create_model_load_request(
    model_id: str,
    model_path: str,
    model_type: str,
    requester_agent: str,
    expected_vram_mb: int = 0,
    priority: int = 0,
    source_agent: str = "",
    machine_id: str = ""
) -> ModelLoadEvent:
    """Create a model load request event"""
    return ModelLoadEvent(
        event_type=ModelEventType.MODEL_LOAD_REQUESTED,
        model_id=model_id,
        model_path=model_path,
        model_type=model_type,
        expected_vram_mb=expected_vram_mb,
        priority=priority,
        requester_agent=requester_agent,
        source_agent=source_agent,
        machine_id=machine_id
    )

def create_vram_warning(
    used_vram_mb: int,
    total_vram_mb: int,
    threshold_percentage: float,
    affected_models: List[str],
    source_agent: str = "",
    machine_id: str = ""
) -> VRAMEvent:
    """Create a VRAM warning event"""
    return VRAMEvent(
        event_type=ModelEventType.VRAM_THRESHOLD_EXCEEDED,
        total_vram_mb=total_vram_mb,
        used_vram_mb=used_vram_mb,
        available_vram_mb=total_vram_mb - used_vram_mb,
        threshold_percentage=threshold_percentage,
        affected_models=affected_models,
        source_agent=source_agent,
        machine_id=machine_id
    )

def create_model_status_change(
    model_id: str,
    old_status: Optional[ModelStatus],
    new_status: ModelStatus,
    vram_usage_mb: int = 0,
    load_time_seconds: float = 0.0,
    error_message: str = "",
    source_agent: str = "",
    machine_id: str = ""
) -> ModelStatusEvent:
    """Create a model status change event"""
    event_type = ModelEventType.MODEL_LOADED
    if new_status == ModelStatus.UNLOADED:
        event_type = ModelEventType.MODEL_UNLOADED
    elif new_status == ModelStatus.ERROR:
        event_type = ModelEventType.MODEL_LOAD_FAILED
        
    return ModelStatusEvent(
        event_type=event_type,
        model_id=model_id,
        old_status=old_status,
        new_status=new_status,
        vram_usage_mb=vram_usage_mb,
        load_time_seconds=load_time_seconds,
        error_message=error_message,
        source_agent=source_agent,
        machine_id=machine_id
    )

def create_cross_machine_request(
    model_id: str,
    target_machine: str,
    source_machine: str,
    coordination_type: str,
    transfer_size_mb: int = 0,
    priority: int = 0,
    source_agent: str = "",
    machine_id: str = ""
) -> CrossMachineModelEvent:
    """Create a cross-machine model coordination event"""
    return CrossMachineModelEvent(
        event_type=ModelEventType.CROSS_MACHINE_MODEL_REQUEST,
        model_id=model_id,
        target_machine=target_machine,
        source_machine=source_machine,
        coordination_type=coordination_type,
        transfer_size_mb=transfer_size_mb,
        transfer_priority=priority,
        source_agent=source_agent,
        machine_id=machine_id
    )

# Event serialization helpers
def serialize_event(event: BaseModelEvent) -> str:
    """Serialize event to JSON string"""
    return json.dumps(event.to_dict(), default=str)

def deserialize_event(json_str: str) -> BaseModelEvent:
    """Deserialize event from JSON string"""
    data = json.loads(json_str)
    event_type = ModelEventType(data["event_type"])
    
    # Route to appropriate event class based on type
    if event_type in [ModelEventType.MODEL_LOAD_REQUESTED, ModelEventType.MODEL_UNLOAD_REQUESTED]:
        return ModelLoadEvent.from_dict(data)
    elif event_type in [ModelEventType.MODEL_LOADED, ModelEventType.MODEL_UNLOADED, ModelEventType.MODEL_LOAD_FAILED]:
        return ModelStatusEvent.from_dict(data)
    elif event_type in [ModelEventType.VRAM_THRESHOLD_EXCEEDED, ModelEventType.VRAM_OPTIMIZED, 
                       ModelEventType.GPU_MEMORY_WARNING, ModelEventType.GPU_MEMORY_CRITICAL]:
        return VRAMEvent.from_dict(data)
    elif event_type in [ModelEventType.MODEL_PERFORMANCE_DEGRADED, ModelEventType.MODEL_INFERENCE_SLOW,
                       ModelEventType.MODEL_INFERENCE_COMPLETED]:
        return ModelPerformanceEvent.from_dict(data)
    elif event_type in [ModelEventType.CROSS_MACHINE_MODEL_REQUEST, ModelEventType.CROSS_MACHINE_MODEL_TRANSFER,
                       ModelEventType.LOAD_BALANCING_REQUIRED]:
        return CrossMachineModelEvent.from_dict(data)
    elif event_type in [ModelEventType.MODEL_HEALTH_CHECK, ModelEventType.MODEL_HEARTBEAT, ModelEventType.MODEL_ERROR]:
        return ModelHealthEvent.from_dict(data)
    else:
        return BaseModelEvent.from_dict(data) 