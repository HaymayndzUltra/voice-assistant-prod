"""
Memory Events - Event-driven communication for memory management
Decouples circular dependencies between memory agents, cache managers, and orchestration services.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import json

class MemoryEventType(Enum):
    """Types of memory-related events"""
    # Memory lifecycle events
    MEMORY_CREATED = "memory_created"
    MEMORY_RETRIEVED = "memory_retrieved"
    MEMORY_UPDATED = "memory_updated"
    MEMORY_DELETED = "memory_deleted"
    MEMORY_ARCHIVED = "memory_archived"
    
    # Cache management events
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    CACHE_EVICTION = "cache_eviction"
    CACHE_INVALIDATION = "cache_invalidation"
    CACHE_WARMING = "cache_warming"
    CACHE_FULL = "cache_full"
    
    # Memory orchestration events
    MEMORY_SYNC_REQUESTED = "memory_sync_requested"
    MEMORY_SYNC_COMPLETED = "memory_sync_completed"
    MEMORY_CONSOLIDATION = "memory_consolidation"
    MEMORY_FRAGMENTATION_DETECTED = "memory_fragmentation_detected"
    
    # Context and reasoning events
    CONTEXT_SWITCH = "context_switch"
    REASONING_CHAIN_STARTED = "reasoning_chain_started"
    REASONING_CHAIN_COMPLETED = "reasoning_chain_completed"
    CONTEXT_EXPIRED = "context_expired"
    
    # Cross-machine memory events
    MEMORY_REPLICATION_REQUESTED = "memory_replication_requested"
    MEMORY_REPLICATION_COMPLETED = "memory_replication_completed"
    CROSS_MACHINE_SYNC = "cross_machine_sync"
    
    # Performance and health events
    MEMORY_PRESSURE_WARNING = "memory_pressure_warning"
    MEMORY_LEAK_DETECTED = "memory_leak_detected"
    MEMORY_OPTIMIZATION_COMPLETED = "memory_optimization_completed"

class MemoryType(Enum):
    """Types of memory content"""
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    CACHE = "cache"
    SESSION = "session"
    CONTEXT = "context"

class CacheEvictionPolicy(Enum):
    """Cache eviction policies"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In, First Out
    TTL = "ttl"  # Time To Live
    ADAPTIVE = "adaptive"  # Adaptive based on usage patterns

@dataclass
class BaseMemoryEvent:
    """Base class for all memory events"""
    event_type: MemoryEventType
    timestamp: datetime = field(default_factory=datetime.now)
    source_agent: str = ""
    machine_id: str = ""
    event_id: str = field(default_factory=lambda: f"mem_evt_{int(datetime.now().timestamp() * 1000)}")
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
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseMemoryEvent':
        """Create event from dictionary"""
        event_type = MemoryEventType(data["event_type"])
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
class MemoryOperationEvent(BaseMemoryEvent):
    """Event for memory CRUD operations"""
    memory_id: str = ""
    memory_type: MemoryType = MemoryType.SHORT_TERM
    content: str = ""
    content_hash: str = ""
    size_bytes: int = 0
    ttl_seconds: Optional[int] = None
    priority: int = 0
    tags: List[str] = field(default_factory=list)
    related_memories: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.event_type:
            self.event_type = MemoryEventType.MEMORY_CREATED

@dataclass
class CacheEvent(BaseMemoryEvent):
    """Event for cache operations"""
    cache_key: str = ""
    cache_level: str = ""  # L1, L2, L3, disk
    hit_ratio: float = 0.0
    cache_size_bytes: int = 0
    max_cache_size_bytes: int = 0
    eviction_policy: CacheEvictionPolicy = CacheEvictionPolicy.LRU
    evicted_items_count: int = 0
    cache_efficiency_score: float = 0.0
    access_pattern: str = ""  # sequential, random, temporal
    
    def __post_init__(self):
        if not self.event_type:
            self.event_type = MemoryEventType.CACHE_HIT

@dataclass
class MemoryOrchestrationEvent(BaseMemoryEvent):
    """Event for memory orchestration operations"""
    operation_type: str = ""  # sync, consolidate, optimize, defragment
    affected_agents: List[str] = field(default_factory=list)
    memory_pool_id: str = ""
    sync_direction: str = ""  # bidirectional, push, pull
    consistency_level: str = ""  # eventual, strong, weak
    conflict_resolution: str = ""  # last_write_wins, merge, manual
    sync_progress_percentage: float = 0.0
    estimated_completion_time: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.event_type:
            self.event_type = MemoryEventType.MEMORY_SYNC_REQUESTED

@dataclass
class ContextEvent(BaseMemoryEvent):
    """Event for context and reasoning operations"""
    context_id: str = ""
    session_id: str = ""
    reasoning_chain_id: str = ""
    context_type: str = ""  # conversation, task, reasoning, system
    context_scope: str = ""  # local, global, cross_agent
    context_size_tokens: int = 0
    context_depth: int = 0
    parent_context_id: str = ""
    child_context_ids: List[str] = field(default_factory=list)
    reasoning_steps: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.event_type:
            self.event_type = MemoryEventType.CONTEXT_SWITCH

@dataclass
class CrossMachineMemoryEvent(BaseMemoryEvent):
    """Event for cross-machine memory operations"""
    target_machine: str = ""
    source_machine: str = ""
    replication_type: str = ""  # full, incremental, differential
    sync_strategy: str = ""  # immediate, batched, scheduled
    bandwidth_used_mbps: float = 0.0
    compression_ratio: float = 0.0
    transfer_size_mb: int = 0
    checksum: str = ""
    replica_count: int = 0
    consistency_check_passed: bool = True
    
    def __post_init__(self):
        if not self.event_type:
            self.event_type = MemoryEventType.MEMORY_REPLICATION_REQUESTED

@dataclass
class MemoryPerformanceEvent(BaseMemoryEvent):
    """Event for memory performance monitoring"""
    operation_latency_ms: float = 0.0
    throughput_ops_per_second: float = 0.0
    memory_utilization_percentage: float = 0.0
    fragmentation_percentage: float = 0.0
    gc_pressure_score: float = 0.0
    memory_leak_detected: bool = False
    optimization_suggestions: List[str] = field(default_factory=list)
    performance_baseline: Dict[str, float] = field(default_factory=dict)
    current_metrics: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.event_type:
            self.event_type = MemoryEventType.MEMORY_PRESSURE_WARNING

# Event factory functions for common use cases
def create_memory_operation(
    operation_type: MemoryEventType,
    memory_id: str,
    memory_type: MemoryType,
    content: str = "",
    size_bytes: int = 0,
    source_agent: str = "",
    machine_id: str = "",
    ttl_seconds: Optional[int] = None,
    tags: Optional[List[str]] = None
) -> MemoryOperationEvent:
    """Create a memory operation event"""
    return MemoryOperationEvent(
        event_type=operation_type,
        memory_id=memory_id,
        memory_type=memory_type,
        content=content,
        size_bytes=size_bytes,
        ttl_seconds=ttl_seconds,
        tags=tags or [],
        source_agent=source_agent,
        machine_id=machine_id
    )

def create_cache_event(
    event_type: MemoryEventType,
    cache_key: str,
    cache_level: str,
    hit_ratio: float = 0.0,
    cache_size_bytes: int = 0,
    source_agent: str = "",
    machine_id: str = ""
) -> CacheEvent:
    """Create a cache operation event"""
    return CacheEvent(
        event_type=event_type,
        cache_key=cache_key,
        cache_level=cache_level,
        hit_ratio=hit_ratio,
        cache_size_bytes=cache_size_bytes,
        source_agent=source_agent,
        machine_id=machine_id
    )

def create_memory_sync_request(
    operation_type: str,
    affected_agents: List[str],
    memory_pool_id: str = "",
    sync_direction: str = "bidirectional",
    source_agent: str = "",
    machine_id: str = ""
) -> MemoryOrchestrationEvent:
    """Create a memory synchronization request"""
    return MemoryOrchestrationEvent(
        event_type=MemoryEventType.MEMORY_SYNC_REQUESTED,
        operation_type=operation_type,
        affected_agents=affected_agents,
        memory_pool_id=memory_pool_id,
        sync_direction=sync_direction,
        source_agent=source_agent,
        machine_id=machine_id
    )

def create_context_switch(
    context_id: str,
    session_id: str,
    context_type: str,
    context_scope: str = "local",
    source_agent: str = "",
    machine_id: str = ""
) -> ContextEvent:
    """Create a context switch event"""
    return ContextEvent(
        event_type=MemoryEventType.CONTEXT_SWITCH,
        context_id=context_id,
        session_id=session_id,
        context_type=context_type,
        context_scope=context_scope,
        source_agent=source_agent,
        machine_id=machine_id
    )

def create_reasoning_chain_event(
    event_type: MemoryEventType,
    reasoning_chain_id: str,
    context_id: str,
    reasoning_steps: List[Dict[str, Any]],
    source_agent: str = "",
    machine_id: str = ""
) -> ContextEvent:
    """Create a reasoning chain event"""
    return ContextEvent(
        event_type=event_type,
        reasoning_chain_id=reasoning_chain_id,
        context_id=context_id,
        reasoning_steps=reasoning_steps,
        source_agent=source_agent,
        machine_id=machine_id
    )

def create_cross_machine_replication(
    target_machine: str,
    source_machine: str,
    replication_type: str,
    transfer_size_mb: int,
    source_agent: str = "",
    machine_id: str = ""
) -> CrossMachineMemoryEvent:
    """Create a cross-machine memory replication event"""
    return CrossMachineMemoryEvent(
        event_type=MemoryEventType.MEMORY_REPLICATION_REQUESTED,
        target_machine=target_machine,
        source_machine=source_machine,
        replication_type=replication_type,
        transfer_size_mb=transfer_size_mb,
        source_agent=source_agent,
        machine_id=machine_id
    )

def create_memory_pressure_warning(
    memory_utilization_percentage: float,
    fragmentation_percentage: float,
    optimization_suggestions: List[str],
    source_agent: str = "",
    machine_id: str = ""
) -> MemoryPerformanceEvent:
    """Create a memory pressure warning event"""
    return MemoryPerformanceEvent(
        event_type=MemoryEventType.MEMORY_PRESSURE_WARNING,
        memory_utilization_percentage=memory_utilization_percentage,
        fragmentation_percentage=fragmentation_percentage,
        optimization_suggestions=optimization_suggestions,
        source_agent=source_agent,
        machine_id=machine_id
    )

# Event serialization helpers
def serialize_memory_event(event: BaseMemoryEvent) -> str:
    """Serialize memory event to JSON string"""
    return json.dumps(event.to_dict(), default=str)

def deserialize_memory_event(json_str: str) -> BaseMemoryEvent:
    """Deserialize memory event from JSON string"""
    data = json.loads(json_str)
    event_type = MemoryEventType(data["event_type"])
    
    # Route to appropriate event class based on type
    if event_type in [MemoryEventType.MEMORY_CREATED, MemoryEventType.MEMORY_RETRIEVED,
                     MemoryEventType.MEMORY_UPDATED, MemoryEventType.MEMORY_DELETED,
                     MemoryEventType.MEMORY_ARCHIVED]:
        return MemoryOperationEvent.from_dict(data)
    elif event_type in [MemoryEventType.CACHE_HIT, MemoryEventType.CACHE_MISS,
                       MemoryEventType.CACHE_EVICTION, MemoryEventType.CACHE_INVALIDATION,
                       MemoryEventType.CACHE_WARMING, MemoryEventType.CACHE_FULL]:
        return CacheEvent.from_dict(data)
    elif event_type in [MemoryEventType.MEMORY_SYNC_REQUESTED, MemoryEventType.MEMORY_SYNC_COMPLETED,
                       MemoryEventType.MEMORY_CONSOLIDATION, MemoryEventType.MEMORY_FRAGMENTATION_DETECTED]:
        return MemoryOrchestrationEvent.from_dict(data)
    elif event_type in [MemoryEventType.CONTEXT_SWITCH, MemoryEventType.REASONING_CHAIN_STARTED,
                       MemoryEventType.REASONING_CHAIN_COMPLETED, MemoryEventType.CONTEXT_EXPIRED]:
        return ContextEvent.from_dict(data)
    elif event_type in [MemoryEventType.MEMORY_REPLICATION_REQUESTED, MemoryEventType.MEMORY_REPLICATION_COMPLETED,
                       MemoryEventType.CROSS_MACHINE_SYNC]:
        return CrossMachineMemoryEvent.from_dict(data)
    elif event_type in [MemoryEventType.MEMORY_PRESSURE_WARNING, MemoryEventType.MEMORY_LEAK_DETECTED,
                       MemoryEventType.MEMORY_OPTIMIZATION_COMPLETED]:
        return MemoryPerformanceEvent.from_dict(data)
    else:
        return BaseMemoryEvent.from_dict(data) 