"""
Unit tests for Memory Fusion Hub Pydantic models.

Tests model validation, serialization, deserialization, and edge cases.
"""

import pytest
from datetime import datetime, timedelta
from typing import Any, Dict
from pydantic import ValidationError

from memory_fusion_hub.core.models import (
    MemoryItem, SessionData, KnowledgeRecord, MemoryEvent,
    MemoryType, EventType, FusionConfig,
    ServerConfig, StorageConfig, ReplicationConfig, ResilienceConfig
)


class TestMemoryItem:
    """Tests for MemoryItem model."""
    
    def test_create_memory_item_minimal(self):
        """Test creating MemoryItem with minimal required fields."""
        item = MemoryItem(key="test_key", content="test content")
        
        assert item.key == "test_key"
        assert item.content == "test content"
        assert item.memory_type == MemoryType.CONVERSATION
        assert isinstance(item.timestamp, datetime)
        assert item.updated_at is None
        assert item.metadata == {}
        assert item.tags == []
        assert item.source_agent is None
        assert item.expiry_timestamp is None
    
    def test_create_memory_item_full(self):
        """Test creating MemoryItem with all fields."""
        now = datetime.utcnow()
        expiry = now + timedelta(hours=1)
        
        item = MemoryItem(
            key="full_key",
            content={"type": "object", "data": [1, 2, 3]},
            memory_type=MemoryType.KNOWLEDGE,
            timestamp=now,
            updated_at=now,
            metadata={"user_id": "123", "session": "abc"},
            tags=["important", "test"],
            source_agent="test_agent",
            expiry_timestamp=expiry
        )
        
        assert item.key == "full_key"
        assert item.content == {"type": "object", "data": [1, 2, 3]}
        assert item.memory_type == MemoryType.KNOWLEDGE
        assert item.timestamp == now
        assert item.updated_at == now
        assert item.metadata == {"user_id": "123", "session": "abc"}
        assert item.tags == ["important", "test"]
        assert item.source_agent == "test_agent"
        assert item.expiry_timestamp == expiry
    
    def test_memory_item_validation_empty_key(self):
        """Test validation fails for empty key."""
        with pytest.raises(ValueError, match="Memory key cannot be empty"):
            MemoryItem(key="", content="test")
    
    def test_memory_item_validation_whitespace_key(self):
        """Test validation fails for whitespace-only key."""
        with pytest.raises(ValueError, match="Memory key cannot be empty"):
            MemoryItem(key="   ", content="test")
    
    def test_memory_item_validation_none_content(self):
        """Test validation fails for None content."""
        with pytest.raises(ValidationError, match="none is not an allowed value"):
            MemoryItem(key="test", content=None)
    
    def test_memory_item_key_stripped(self):
        """Test that key is automatically stripped."""
        item = MemoryItem(key="  test_key  ", content="test")
        assert item.key == "test_key"
    
    def test_memory_item_serialization(self):
        """Test JSON serialization."""
        item = MemoryItem(
            key="serialize_test",
            content="test content",
            metadata={"test": "value"},
            tags=["tag1", "tag2"]
        )
        
        json_data = item.json()
        assert "serialize_test" in json_data
        assert "test content" in json_data
        assert "tag1" in json_data
    
    def test_memory_item_dict_conversion(self):
        """Test dictionary conversion."""
        item = MemoryItem(key="dict_test", content="test")
        data = item.dict()
        
        assert data["key"] == "dict_test"
        assert data["content"] == "test"
        assert "memory_type" in data
        assert "timestamp" in data
    
    def test_memory_item_example_schema(self):
        """Test that example in schema is valid."""
        example = {
            "key": "user_123_last_conversation",
            "content": "User asked about weather in Tokyo",
            "memory_type": "conversation",
            "timestamp": "2025-08-07T17:30:00Z",
            "metadata": {"user_id": "123", "session_id": "abc-def"},
            "tags": ["weather", "tokyo", "question"],
            "source_agent": "conversation_manager"
        }
        
        # Should not raise validation error
        item = MemoryItem(**example)
        assert item.key == example["key"]
        assert item.content == example["content"]


class TestSessionData:
    """Tests for SessionData model."""
    
    def test_create_session_data_minimal(self):
        """Test creating SessionData with minimal required fields."""
        session = SessionData(session_id="test_session")
        
        assert session.session_id == "test_session"
        assert session.user_id is None
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.last_activity, datetime)
        assert session.context == {}
        assert session.conversation_history == []
        assert session.preferences == {}
        assert session.active is True
    
    def test_create_session_data_full(self):
        """Test creating SessionData with all fields."""
        now = datetime.utcnow()
        
        session = SessionData(
            session_id="full_session",
            user_id="user_456",
            created_at=now,
            last_activity=now,
            context={"current_topic": "weather"},
            conversation_history=["msg_001", "msg_002"],
            preferences={"timezone": "UTC"},
            active=False
        )
        
        assert session.session_id == "full_session"
        assert session.user_id == "user_456"
        assert session.created_at == now
        assert session.last_activity == now
        assert session.context == {"current_topic": "weather"}
        assert session.conversation_history == ["msg_001", "msg_002"]
        assert session.preferences == {"timezone": "UTC"}
        assert session.active is False
    
    def test_session_data_validation_empty_id(self):
        """Test validation fails for empty session ID."""
        with pytest.raises(ValueError, match="Session ID cannot be empty"):
            SessionData(session_id="")
    
    def test_session_data_id_stripped(self):
        """Test that session ID is automatically stripped."""
        session = SessionData(session_id="  test_session  ")
        assert session.session_id == "test_session"


class TestKnowledgeRecord:
    """Tests for KnowledgeRecord model."""
    
    def test_create_knowledge_record_minimal(self):
        """Test creating KnowledgeRecord with minimal required fields."""
        record = KnowledgeRecord(
            knowledge_id="test_knowledge",
            title="Test Knowledge",
            content="Test content",
            category="test"
        )
        
        assert record.knowledge_id == "test_knowledge"
        assert record.title == "Test Knowledge"
        assert record.content == "Test content"
        assert record.category == "test"
        assert record.confidence_score == 1.0
        assert isinstance(record.created_at, datetime)
        assert record.updated_at is None
        assert record.source is None
        assert record.related_items == []
        assert record.access_count == 0
        assert record.last_accessed is None
    
    def test_knowledge_record_confidence_validation(self):
        """Test confidence score validation."""
        # Valid confidence scores
        record = KnowledgeRecord(
            knowledge_id="test",
            title="Test",
            content="Test",
            category="test",
            confidence_score=0.5
        )
        assert record.confidence_score == 0.5
        
        # Invalid confidence scores
        with pytest.raises(ValueError):
            KnowledgeRecord(
                knowledge_id="test",
                title="Test",
                content="Test",
                category="test",
                confidence_score=1.5  # > 1.0
            )
        
        with pytest.raises(ValueError):
            KnowledgeRecord(
                knowledge_id="test",
                title="Test",
                content="Test",
                category="test",
                confidence_score=-0.1  # < 0.0
            )
    
    def test_knowledge_record_validation_fields(self):
        """Test validation of required fields."""
        # Empty knowledge_id
        with pytest.raises(ValueError, match="Knowledge ID cannot be empty"):
            KnowledgeRecord(knowledge_id="", title="Test", content="Test", category="test")
        
        # Empty title
        with pytest.raises(ValueError, match="Knowledge title cannot be empty"):
            KnowledgeRecord(knowledge_id="test", title="", content="Test", category="test")
        
        # Empty category
        with pytest.raises(ValueError, match="Knowledge category cannot be empty"):
            KnowledgeRecord(knowledge_id="test", title="Test", content="Test", category="")


class TestMemoryEvent:
    """Tests for MemoryEvent model."""
    
    def test_create_memory_event_minimal(self):
        """Test creating MemoryEvent with minimal required fields."""
        event = MemoryEvent(
            event_id="test_event",
            event_type=EventType.CREATE,
            target_key="test_key"
        )
        
        assert event.event_id == "test_event"
        assert event.event_type == EventType.CREATE
        assert event.target_key == "test_key"
        assert isinstance(event.timestamp, datetime)
        assert event.agent_id is None
        assert event.payload is None
        assert event.previous_value is None
        assert event.sequence_number is None
        assert event.correlation_id is None
    
    def test_create_memory_event_full(self):
        """Test creating MemoryEvent with all fields."""
        now = datetime.utcnow()
        
        event = MemoryEvent(
            event_id="full_event",
            event_type=EventType.UPDATE,
            target_key="full_key",
            timestamp=now,
            agent_id="test_agent",
            payload={"action": "update", "data": "new_value"},
            previous_value={"old": "value"},
            sequence_number=42,
            correlation_id="corr_123"
        )
        
        assert event.event_id == "full_event"
        assert event.event_type == EventType.UPDATE
        assert event.target_key == "full_key"
        assert event.timestamp == now
        assert event.agent_id == "test_agent"
        assert event.payload == {"action": "update", "data": "new_value"}
        assert event.previous_value == {"old": "value"}
        assert event.sequence_number == 42
        assert event.correlation_id == "corr_123"
    
    def test_memory_event_validation(self):
        """Test validation of required fields."""
        with pytest.raises(ValueError, match="Event ID cannot be empty"):
            MemoryEvent(event_id="", event_type=EventType.CREATE, target_key="test")
        
        with pytest.raises(ValueError, match="Target key cannot be empty"):
            MemoryEvent(event_id="test", event_type=EventType.CREATE, target_key="")


class TestConfigurationModels:
    """Tests for configuration models."""
    
    def test_server_config_defaults(self):
        """Test ServerConfig default values."""
        config = ServerConfig()
        
        assert config.zmq_port == 5713
        assert config.grpc_port == 5714
        assert config.max_workers == 8
    
    def test_storage_config_defaults(self):
        """Test StorageConfig default values."""
        config = StorageConfig()
        
        assert config.write_strategy == "event_sourcing"
        assert config.sqlite_path == "/workspace/memory.db"
        assert config.postgres_url is None
        assert config.redis_url == "redis://localhost:6379/0"
        assert config.cache_ttl_seconds == 900
    
    def test_replication_config_defaults(self):
        """Test ReplicationConfig default values."""
        config = ReplicationConfig()
        
        assert config.enabled is True
        assert config.event_topic == "memory_events"
        assert config.nats_url == "nats://localhost:4222"
    
    def test_fusion_config_full(self):
        """Test FusionConfig with all nested configs."""
        config = FusionConfig(
            title="TestConfig",
            version="2.0",
            server=ServerConfig(zmq_port=6000),
            storage=StorageConfig(cache_ttl_seconds=1800),
            replication=ReplicationConfig(enabled=False)
        )
        
        assert config.title == "TestConfig"
        assert config.version == "2.0"
        assert config.server.zmq_port == 6000
        assert config.server.grpc_port == 5714  # Default
        assert config.storage.cache_ttl_seconds == 1800
        assert config.replication.enabled is False
    
    def test_fusion_config_yaml_compatibility(self):
        """Test FusionConfig with YAML-like structure."""
        yaml_data = {
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
        
        # Should not raise validation error
        config = FusionConfig(**yaml_data)
        assert config.title == "MemoryFusionHubConfig"
        assert config.server.zmq_port == 5713
        assert config.storage.write_strategy == "event_sourcing"
        assert config.replication.enabled is True
        assert config.resilience.circuit_breaker.failure_threshold == 5


class TestModelInteroperability:
    """Tests for model interoperability and edge cases."""
    
    def test_json_schema_generation(self):
        """Test that all models can generate JSON schemas."""
        models = [MemoryItem, SessionData, KnowledgeRecord, MemoryEvent, FusionConfig]
        
        for model in models:
            schema = model.schema()
            assert "properties" in schema
            assert "title" in schema
            # Note: "required" may not be present if all fields have defaults
    
    def test_datetime_serialization(self):
        """Test datetime serialization in JSON."""
        item = MemoryItem(key="datetime_test", content="test")
        json_str = item.json()
        
        # Should contain ISO format timestamp
        assert "T" in json_str
        assert "Z" in json_str or "+" in json_str or item.timestamp.isoformat() in json_str
    
    def test_complex_content_serialization(self):
        """Test serialization of complex content types."""
        complex_content = {
            "nested": {
                "array": [1, 2, 3],
                "boolean": True,
                "null_value": None
            }
        }
        
        item = MemoryItem(key="complex_test", content=complex_content)
        
        # Should serialize and deserialize correctly
        json_data = item.json()
        reconstructed = MemoryItem.parse_raw(json_data)
        
        assert reconstructed.content == complex_content
    
    def test_memory_type_enum_values(self):
        """Test MemoryType enum values."""
        assert MemoryType.CONVERSATION == "conversation"
        assert MemoryType.KNOWLEDGE == "knowledge"
        assert MemoryType.SESSION == "session"
        assert MemoryType.CONTEXT == "context"
        assert MemoryType.METADATA == "metadata"
    
    def test_event_type_enum_values(self):
        """Test EventType enum values."""
        assert EventType.CREATE == "CREATE"
        assert EventType.UPDATE == "UPDATE"
        assert EventType.DELETE == "DELETE"
        assert EventType.READ == "READ"


# Pytest fixtures for common test data
@pytest.fixture
def sample_memory_item():
    """Sample MemoryItem for testing."""
    return MemoryItem(
        key="sample_key",
        content="sample content",
        metadata={"test": "value"},
        tags=["sample", "test"]
    )


@pytest.fixture
def sample_session_data():
    """Sample SessionData for testing."""
    return SessionData(
        session_id="sample_session",
        user_id="sample_user",
        context={"topic": "test"},
        conversation_history=["msg1", "msg2"]
    )


@pytest.fixture
def sample_fusion_config():
    """Sample FusionConfig for testing."""
    return FusionConfig(
        title="TestConfig",
        server=ServerConfig(zmq_port=6000),
        storage=StorageConfig(cache_ttl_seconds=1800)
    )


if __name__ == "__main__":
    pytest.main([__file__])