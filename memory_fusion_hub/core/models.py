"""
Core Pydantic data models for Memory Fusion Hub.

This module defines the fundamental data structures used throughout the service:
- MemoryItem: Primary memory storage unit
- SessionData: Session-specific information
- KnowledgeRecord: Knowledge base entries
- MemoryEvent: Event sourcing records
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, validator


class MemoryType(str, Enum):
    """Types of memory records."""
    CONVERSATION = "conversation"
    KNOWLEDGE = "knowledge"
    SESSION = "session"
    CONTEXT = "context"
    METADATA = "metadata"


class EventType(str, Enum):
    """Types of memory events for event sourcing."""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    READ = "READ"


class MemoryItem(BaseModel):
    """
    Primary memory storage unit representing any piece of information
    stored in the Memory Fusion Hub.
    """
    
    key: str = Field(..., description="Unique identifier for the memory item")
    content: Union[str, Dict[str, Any], List[Any]] = Field(
        ..., description="The actual memory content - can be text, JSON object, or array"
    )
    memory_type: MemoryType = Field(
        default=MemoryType.CONVERSATION, 
        description="Type classification of the memory"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this memory was created"
    )
    updated_at: Optional[datetime] = Field(
        None, description="When this memory was last updated"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the memory item"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorizing and searching memory items"
    )
    source_agent: Optional[str] = Field(
        None, description="Which agent or service created this memory"
    )
    expiry_timestamp: Optional[datetime] = Field(
        None, description="When this memory should be automatically expired"
    )
    
    @validator('key')
    def validate_key(cls, v):
        if not v or not v.strip():
            raise ValueError('Memory key cannot be empty')
        return v.strip()
    
    @validator('content')
    def validate_content(cls, v):
        if v is None:
            raise ValueError('Memory content cannot be None')
        return v
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "key": "user_123_last_conversation",
                "content": "User asked about weather in Tokyo",
                "memory_type": "conversation",
                "timestamp": "2025-08-07T17:30:00Z",
                "metadata": {"user_id": "123", "session_id": "abc-def"},
                "tags": ["weather", "tokyo", "question"],
                "source_agent": "conversation_manager"
            }
        }


class SessionData(BaseModel):
    """
    Session-specific information for maintaining conversational context
    and state across multiple interactions.
    """
    
    session_id: str = Field(..., description="Unique session identifier")
    user_id: Optional[str] = Field(None, description="Associated user identifier")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the session was created"
    )
    last_activity: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last activity timestamp"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Session context variables and state"
    )
    conversation_history: List[str] = Field(
        default_factory=list,
        description="Ordered list of memory keys representing conversation flow"
    )
    preferences: Dict[str, Any] = Field(
        default_factory=dict,
        description="User or session-specific preferences"
    )
    active: bool = Field(default=True, description="Whether session is currently active")
    
    @validator('session_id')
    def validate_session_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Session ID cannot be empty')
        return v.strip()
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "session_id": "session_abc_123",
                "user_id": "user_456",
                "created_at": "2025-08-07T17:00:00Z",
                "last_activity": "2025-08-07T17:30:00Z",
                "context": {"current_topic": "weather", "language": "en"},
                "conversation_history": ["msg_001", "msg_002", "msg_003"],
                "preferences": {"timezone": "UTC", "format": "json"},
                "active": True
            }
        }


class KnowledgeRecord(BaseModel):
    """
    Knowledge base entries representing factual information,
    procedures, or learned patterns.
    """
    
    knowledge_id: str = Field(..., description="Unique knowledge identifier")
    title: str = Field(..., description="Human-readable title for the knowledge")
    content: Union[str, Dict[str, Any]] = Field(
        ..., description="The knowledge content"
    )
    category: str = Field(..., description="Knowledge category or domain")
    confidence_score: float = Field(
        default=1.0, 
        ge=0.0, 
        le=1.0,
        description="Confidence level in this knowledge (0.0 to 1.0)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this knowledge was created"
    )
    updated_at: Optional[datetime] = Field(
        None, description="When this knowledge was last updated"
    )
    source: Optional[str] = Field(
        None, description="Source of this knowledge (URL, document, agent, etc.)"
    )
    related_items: List[str] = Field(
        default_factory=list,
        description="List of related knowledge or memory item keys"
    )
    access_count: int = Field(
        default=0, description="Number of times this knowledge has been accessed"
    )
    last_accessed: Optional[datetime] = Field(
        None, description="When this knowledge was last accessed"
    )
    
    @validator('knowledge_id')
    def validate_knowledge_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Knowledge ID cannot be empty')
        return v.strip()
    
    @validator('title')
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('Knowledge title cannot be empty')
        return v.strip()
    
    @validator('category')
    def validate_category(cls, v):
        if not v or not v.strip():
            raise ValueError('Knowledge category cannot be empty')
        return v.strip()
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "knowledge_id": "weather_api_usage",
                "title": "How to use weather API",
                "content": "The weather API requires an API key and accepts location parameters...",
                "category": "api_documentation",
                "confidence_score": 0.95,
                "created_at": "2025-08-07T16:00:00Z",
                "source": "internal_documentation",
                "related_items": ["api_key_management", "location_services"],
                "access_count": 42
            }
        }


class MemoryEvent(BaseModel):
    """
    Event sourcing record for tracking all operations performed
    on memory items. Used for replication and audit trails.
    """
    
    event_id: str = Field(..., description="Unique event identifier")
    event_type: EventType = Field(..., description="Type of operation performed")
    target_key: str = Field(..., description="Key of the memory item affected")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the event occurred"
    )
    agent_id: Optional[str] = Field(
        None, description="ID of the agent that performed the operation"
    )
    payload: Optional[Dict[str, Any]] = Field(
        None, description="Event-specific data (e.g., new content for UPDATE events)"
    )
    previous_value: Optional[Dict[str, Any]] = Field(
        None, description="Previous value before the change (for UPDATE/DELETE)"
    )
    sequence_number: Optional[int] = Field(
        None, description="Sequence number for ordering events"
    )
    correlation_id: Optional[str] = Field(
        None, description="ID for correlating related events"
    )
    
    @validator('event_id')
    def validate_event_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Event ID cannot be empty')
        return v.strip()
    
    @validator('target_key')
    def validate_target_key(cls, v):
        if not v or not v.strip():
            raise ValueError('Target key cannot be empty')
        return v.strip()
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "event_id": "evt_001_abc_123",
                "event_type": "UPDATE",
                "target_key": "user_123_last_conversation",
                "timestamp": "2025-08-07T17:30:00Z",
                "agent_id": "conversation_manager",
                "payload": {"content": "Updated conversation content"},
                "sequence_number": 1001,
                "correlation_id": "session_abc_123"
            }
        }


# Configuration models for type safety

class ServerConfig(BaseModel):
    """Server configuration settings."""
    zmq_port: int = Field(default=5713, description="ZMQ server port")
    grpc_port: int = Field(default=5714, description="gRPC server port")
    max_workers: int = Field(default=8, description="Maximum worker threads")


class StorageConfig(BaseModel):
    """Storage configuration settings."""
    write_strategy: str = Field(default="event_sourcing", description="Write strategy")
    sqlite_path: str = Field(default="/workspace/memory.db", description="SQLite database path")
    postgres_url: Optional[str] = Field(None, description="PostgreSQL connection URL")
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    cache_ttl_seconds: int = Field(default=900, description="Cache TTL in seconds")


class ReplicationConfig(BaseModel):
    """Replication configuration settings."""
    enabled: bool = Field(default=True, description="Enable replication")
    event_topic: str = Field(default="memory_events", description="Event topic name")
    nats_url: str = Field(default="nats://localhost:4222", description="NATS server URL")


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""
    failure_threshold: int = Field(default=5, description="Failure threshold")
    reset_timeout: int = Field(default=30, description="Reset timeout in seconds")


class BulkheadConfig(BaseModel):
    """Bulkhead configuration."""
    max_concurrent: int = Field(default=32, description="Maximum concurrent operations")
    max_queue_size: int = Field(default=128, description="Maximum queue size")


class ResilienceConfig(BaseModel):
    """Resilience configuration settings."""
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    bulkhead: BulkheadConfig = Field(default_factory=BulkheadConfig)


class FusionConfig(BaseModel):
    """Complete Memory Fusion Hub configuration."""
    title: str = Field(default="MemoryFusionHubConfig", description="Configuration title")
    version: str = Field(default="1.0", description="Configuration version")
    server: ServerConfig = Field(default_factory=ServerConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    replication: ReplicationConfig = Field(default_factory=ReplicationConfig)
    resilience: ResilienceConfig = Field(default_factory=ResilienceConfig)
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "title": "MemoryFusionHubConfig",
                "version": "1.0",
                "server": {
                    "zmq_port": 5713,
                    "grpc_port": 5714,
                    "max_workers": 8
                },
                "storage": {
                    "write_strategy": "event_sourcing",
                    "sqlite_path": "/workspace/memory.db",
                    "redis_url": "redis://localhost:6379/0",
                    "cache_ttl_seconds": 900
                },
                "replication": {
                    "enabled": True,
                    "event_topic": "memory_events",
                    "nats_url": "nats://localhost:4222"
                },
                "resilience": {
                    "circuit_breaker": {
                        "failure_threshold": 5,
                        "reset_timeout": 30
                    },
                    "bulkhead": {
                        "max_concurrent": 32,
                        "max_queue_size": 128
                    }
                }
            }
        }