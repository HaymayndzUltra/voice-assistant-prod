"""
Core data models for Memory Fusion Hub using Pydantic.

This module defines the fundamental data structures that represent memory items,
session data, knowledge records, and events in the system.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class MemoryType(str, Enum):
    """Types of memory items in the system."""
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    WORKING = "working"


class EventType(str, Enum):
    """Types of events that can occur in the memory system."""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    ACCESSED = "accessed"


class MemoryItem(BaseModel):
    """
    Core memory item that represents a single piece of information in the system.
    
    This is the primary data structure for storing and retrieving memory data.
    """
    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the memory item")
    key: str = Field(..., description="Primary key for retrieval")
    content: Dict[str, Any] = Field(..., description="The actual memory content")
    memory_type: MemoryType = Field(default=MemoryType.SEMANTIC, description="Type of memory")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    accessed_at: Optional[datetime] = Field(None, description="Last access timestamp")
    
    # Access and relevance metrics
    access_count: int = Field(default=0, description="Number of times this item was accessed")
    relevance_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Relevance score (0.0-1.0)")
    
    # Relationships and context
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    parent_id: Optional[UUID] = Field(None, description="Parent memory item ID")
    context: Dict[str, Any] = Field(default_factory=dict, description="Contextual information")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
        schema_extra = {
            "example": {
                "key": "user_preference_dark_mode",
                "content": {"preference": "dark_mode", "value": True},
                "memory_type": "semantic",
                "tags": ["user", "ui", "preference"],
                "relevance_score": 0.95
            }
        }

    @validator('updated_at', always=True)
    def set_updated_at(cls, v):
        """Ensure updated_at is set to current time."""
        return datetime.utcnow()


class SessionData(BaseModel):
    """
    Session-specific data that tracks user interactions and context.
    
    Used for maintaining session state and providing contextual memory access.
    """
    session_id: UUID = Field(default_factory=uuid4, description="Unique session identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    
    # Session lifecycle
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Session start time")
    last_activity: datetime = Field(default_factory=datetime.utcnow, description="Last activity timestamp")
    is_active: bool = Field(default=True, description="Whether session is currently active")
    
    # Session context and state
    context: Dict[str, Any] = Field(default_factory=dict, description="Session-specific context")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Session variables")
    
    # Activity tracking
    interaction_count: int = Field(default=0, description="Number of interactions in this session")
    accessed_memories: List[str] = Field(default_factory=list, description="Memory keys accessed in session")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
        schema_extra = {
            "example": {
                "user_id": "user123",
                "context": {"current_task": "data_analysis", "workspace": "project_alpha"},
                "variables": {"theme": "dark", "language": "en"},
                "interaction_count": 15
            }
        }

    @validator('last_activity', always=True)
    def update_activity(cls, v):
        """Update last activity to current time."""
        return datetime.utcnow()


class KnowledgeRecord(BaseModel):
    """
    Structured knowledge representation for semantic memory.
    
    Represents factual information, relationships, and learned knowledge.
    """
    id: UUID = Field(default_factory=uuid4, description="Unique knowledge record identifier")
    subject: str = Field(..., description="Subject of the knowledge")
    predicate: str = Field(..., description="Relationship or attribute")
    object: Union[str, int, float, bool, Dict[str, Any]] = Field(..., description="Object or value")
    
    # Knowledge metadata
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in this knowledge")
    source: Optional[str] = Field(None, description="Source of this knowledge")
    domain: Optional[str] = Field(None, description="Knowledge domain or category")
    
    # Temporal information
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When knowledge was acquired")
    valid_from: Optional[datetime] = Field(None, description="When this knowledge became valid")
    valid_until: Optional[datetime] = Field(None, description="When this knowledge expires")
    
    # Verification and trust
    verified: bool = Field(default=False, description="Whether this knowledge has been verified")
    verification_source: Optional[str] = Field(None, description="Source of verification")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
        schema_extra = {
            "example": {
                "subject": "Python",
                "predicate": "is_programming_language",
                "object": True,
                "confidence": 1.0,
                "domain": "programming",
                "verified": True
            }
        }


class MemoryEvent(BaseModel):
    """
    Event record for event sourcing and audit logging.
    
    Represents all changes and access patterns in the memory system.
    """
    id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    event_type: EventType = Field(..., description="Type of event")
    
    # Event target
    memory_key: str = Field(..., description="Key of the memory item affected")
    memory_id: Optional[UUID] = Field(None, description="ID of the memory item affected")
    
    # Event metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the event occurred")
    session_id: Optional[UUID] = Field(None, description="Session that triggered the event")
    user_id: Optional[str] = Field(None, description="User who triggered the event")
    
    # Event data
    old_value: Optional[Dict[str, Any]] = Field(None, description="Previous value (for updates/deletes)")
    new_value: Optional[Dict[str, Any]] = Field(None, description="New value (for creates/updates)")
    
    # Additional context
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional event context")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
        schema_extra = {
            "example": {
                "event_type": "updated",
                "memory_key": "user_preference_theme",
                "old_value": {"theme": "light"},
                "new_value": {"theme": "dark"},
                "context": {"source": "settings_page", "reason": "user_request"}
            }
        }


# JSON Schema generation functions
def generate_schemas() -> Dict[str, Dict[str, Any]]:
    """
    Generate JSON schemas for all data models.
    
    Returns:
        Dictionary mapping model names to their JSON schemas.
    """
    return {
        "MemoryItem": MemoryItem.schema(),
        "SessionData": SessionData.schema(),
        "KnowledgeRecord": KnowledgeRecord.schema(),
        "MemoryEvent": MemoryEvent.schema()
    }


# Model validation utilities
def validate_memory_item(data: Dict[str, Any]) -> MemoryItem:
    """Validate and create a MemoryItem from dictionary data."""
    return MemoryItem(**data)


def validate_session_data(data: Dict[str, Any]) -> SessionData:
    """Validate and create SessionData from dictionary data."""
    return SessionData(**data)


def validate_knowledge_record(data: Dict[str, Any]) -> KnowledgeRecord:
    """Validate and create a KnowledgeRecord from dictionary data."""
    return KnowledgeRecord(**data)


def validate_memory_event(data: Dict[str, Any]) -> MemoryEvent:
    """Validate and create a MemoryEvent from dictionary data."""
    return MemoryEvent(**data)