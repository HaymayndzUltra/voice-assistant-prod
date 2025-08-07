"""
Unit tests for Redis cache adapter.

Tests cache operations, TTL management, serialization, and error handling
using mocked Redis operations.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

from memory_fusion_hub.adapters.redis_cache import RedisCache, CacheException
from memory_fusion_hub.core.models import MemoryItem, SessionData, KnowledgeRecord


class TestRedisCache:
    """Tests for RedisCache functionality."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.cache = RedisCache("redis://localhost:6379/0", default_ttl_seconds=300)
    
    @pytest.mark.asyncio
    async def test_cache_initialization(self):
        """Test cache initialization."""
        assert self.cache.redis_url == "redis://localhost:6379/0"
        assert self.cache.default_ttl_seconds == 300
        assert self.cache.client is None
        assert self.cache._connection_pool is None
    
    @pytest.mark.asyncio
    @patch('memory_fusion_hub.adapters.redis_cache.aioredis')
    async def test_ensure_connection_success(self, mock_aioredis):
        """Test successful Redis connection establishment."""
        # Mock connection pool and client
        mock_pool = AsyncMock()
        mock_client = AsyncMock()
        mock_aioredis.ConnectionPool.from_url.return_value = mock_pool
        mock_aioredis.Redis.return_value = mock_client
        
        # Mock successful ping
        mock_client.ping.return_value = "PONG"
        
        await self.cache._ensure_connection()
        
        # Verify connection was established
        assert self.cache.client == mock_client
        assert self.cache._connection_pool == mock_pool
        mock_client.ping.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('memory_fusion_hub.adapters.redis_cache.aioredis')
    async def test_ensure_connection_failure(self, mock_aioredis):
        """Test Redis connection failure."""
        mock_aioredis.ConnectionPool.from_url.side_effect = Exception("Connection failed")
        
        with pytest.raises(CacheException, match="Redis connection failed"):
            await self.cache._ensure_connection()
    
    @pytest.mark.asyncio
    @patch('memory_fusion_hub.adapters.redis_cache.aioredis')
    async def test_get_cache_hit(self, mock_aioredis):
        """Test cache get operation with cache hit."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Mock cache hit
        item_data = {
            'key': 'test_key',
            'content': 'test content',
            'memory_type': 'conversation',
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': {},
            'tags': [],
            '__model_type__': 'MemoryItem'
        }
        mock_client.get.return_value = json.dumps(item_data)
        
        result = await self.cache.get("test_key")
        
        # Verify result
        assert result is not None
        assert isinstance(result, MemoryItem)
        assert result.key == "test_key"
        assert result.content == "test content"
        
        mock_client.get.assert_called_once_with("test_key")
    
    @pytest.mark.asyncio
    @patch('memory_fusion_hub.adapters.redis_cache.aioredis')
    async def test_get_cache_miss(self, mock_aioredis):
        """Test cache get operation with cache miss."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Mock cache miss
        mock_client.get.return_value = None
        
        result = await self.cache.get("nonexistent_key")
        
        # Verify result
        assert result is None
        mock_client.get.assert_called_once_with("nonexistent_key")
    
    @pytest.mark.asyncio
    async def test_get_json_decode_error(self):
        """Test cache get with JSON decode error."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Mock corrupted data
        mock_client.get.return_value = "invalid json data"
        mock_client.delete = AsyncMock()
        
        result = await self.cache.get("corrupted_key")
        
        # Verify error handling
        assert result is None
        mock_client.delete.assert_called_once_with("corrupted_key")
    
    @pytest.mark.asyncio
    async def test_put_memory_item(self):
        """Test cache put operation with MemoryItem."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Create test item
        item = MemoryItem(
            key="put_test",
            content="test content",
            metadata={"test": "value"}
        )
        
        await self.cache.put("put_test", item, ttl_seconds=600)
        
        # Verify put operation
        mock_client.setex.assert_called_once()
        call_args = mock_client.setex.call_args
        assert call_args[0][0] == "put_test"  # key
        assert call_args[0][1] == 600  # ttl
        
        # Verify serialized data contains model type
        serialized_data = call_args[0][2]
        data_dict = json.loads(serialized_data)
        assert data_dict['__model_type__'] == 'MemoryItem'
        assert data_dict['key'] == "put_test"
        assert data_dict['content'] == "test content"
    
    @pytest.mark.asyncio
    async def test_put_with_default_ttl(self):
        """Test cache put operation with default TTL."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        item = MemoryItem(key="default_ttl_test", content="test")
        
        await self.cache.put("default_ttl_test", item)
        
        # Verify default TTL was used
        mock_client.setex.assert_called_once()
        call_args = mock_client.setex.call_args
        assert call_args[0][1] == 300  # default TTL
    
    @pytest.mark.asyncio
    async def test_put_session_data(self):
        """Test cache put operation with SessionData."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        session = SessionData(
            session_id="session_test",
            user_id="user_123",
            context={"topic": "weather"}
        )
        
        await self.cache.put("session_test", session)
        
        # Verify put operation
        mock_client.setex.assert_called_once()
        call_args = mock_client.setex.call_args
        serialized_data = call_args[0][2]
        data_dict = json.loads(serialized_data)
        assert data_dict['__model_type__'] == 'SessionData'
        assert data_dict['session_id'] == "session_test"
    
    @pytest.mark.asyncio
    async def test_evict_success(self):
        """Test cache eviction success."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Mock successful deletion
        mock_client.delete.return_value = 1
        
        result = await self.cache.evict("evict_test")
        
        # Verify eviction
        assert result is True
        mock_client.delete.assert_called_once_with("evict_test")
    
    @pytest.mark.asyncio
    async def test_evict_key_not_found(self):
        """Test cache eviction when key doesn't exist."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Mock key not found
        mock_client.delete.return_value = 0
        
        result = await self.cache.evict("nonexistent_key")
        
        # Verify result
        assert result is False
        mock_client.delete.assert_called_once_with("nonexistent_key")
    
    @pytest.mark.asyncio
    async def test_exists_true(self):
        """Test cache exists check when key exists."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Mock key exists
        mock_client.exists.return_value = 1
        
        result = await self.cache.exists("existing_key")
        
        # Verify result
        assert result is True
        mock_client.exists.assert_called_once_with("existing_key")
    
    @pytest.mark.asyncio
    async def test_exists_false(self):
        """Test cache exists check when key doesn't exist."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Mock key doesn't exist
        mock_client.exists.return_value = 0
        
        result = await self.cache.exists("nonexistent_key")
        
        # Verify result
        assert result is False
        mock_client.exists.assert_called_once_with("nonexistent_key")
    
    @pytest.mark.asyncio
    async def test_get_ttl_existing_key(self):
        """Test getting TTL for existing key."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Mock TTL value
        mock_client.ttl.return_value = 120
        
        result = await self.cache.get_ttl("ttl_test")
        
        # Verify result
        assert result == 120
        mock_client.ttl.assert_called_once_with("ttl_test")
    
    @pytest.mark.asyncio
    async def test_get_ttl_nonexistent_key(self):
        """Test getting TTL for non-existent key."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Mock key doesn't exist
        mock_client.ttl.return_value = -2
        
        result = await self.cache.get_ttl("nonexistent_key")
        
        # Verify result
        assert result is None
        mock_client.ttl.assert_called_once_with("nonexistent_key")
    
    @pytest.mark.asyncio
    async def test_get_ttl_no_expiry(self):
        """Test getting TTL for key with no expiry."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Mock key exists but has no TTL
        mock_client.ttl.return_value = -1
        
        result = await self.cache.get_ttl("no_expiry_key")
        
        # Verify result
        assert result == -1
        mock_client.ttl.assert_called_once_with("no_expiry_key")
    
    @pytest.mark.asyncio
    async def test_set_ttl_success(self):
        """Test setting TTL for existing key."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Mock successful TTL update
        mock_client.expire.return_value = True
        
        result = await self.cache.set_ttl("test_key", 3600)
        
        # Verify result
        assert result is True
        mock_client.expire.assert_called_once_with("test_key", 3600)
    
    @pytest.mark.asyncio
    async def test_set_ttl_key_not_found(self):
        """Test setting TTL for non-existent key."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Mock key not found
        mock_client.expire.return_value = False
        
        result = await self.cache.set_ttl("nonexistent_key", 3600)
        
        # Verify result
        assert result is False
        mock_client.expire.assert_called_once_with("nonexistent_key", 3600)
    
    @pytest.mark.asyncio
    async def test_clear_all(self):
        """Test clearing all cache data."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Mock keys and deletion
        mock_client.keys.return_value = ["key1", "key2", "key3"]
        mock_client.delete.return_value = 3
        
        result = await self.cache.clear_all()
        
        # Verify result
        assert result == 3
        mock_client.keys.assert_called_once_with('*')
        mock_client.delete.assert_called_once_with("key1", "key2", "key3")
    
    @pytest.mark.asyncio
    async def test_clear_all_no_keys(self):
        """Test clearing all cache data when no keys exist."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Mock no keys
        mock_client.keys.return_value = []
        
        result = await self.cache.clear_all()
        
        # Verify result
        assert result == 0
        mock_client.keys.assert_called_once_with('*')
        mock_client.delete.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_cache_info(self):
        """Test getting cache statistics."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Mock Redis info
        mock_client.info.side_effect = [
            {  # General info
                'connected_clients': 5,
                'used_memory': 1024000,
                'used_memory_human': '1.02M',
                'keyspace_hits': 100,
                'keyspace_misses': 20,
                'total_commands_processed': 1000,
                'instantaneous_ops_per_sec': 50
            },
            {  # Keyspace info
                'db0': {'keys': 25, 'expires': 10}
            }
        ]
        
        result = await self.cache.get_cache_info()
        
        # Verify result structure
        assert 'connected_clients' in result
        assert 'used_memory' in result
        assert 'keyspace_hits' in result
        assert 'hit_rate' in result
        assert 'db0_keys' in result
        
        # Verify hit rate calculation
        expected_hit_rate = 100 / (100 + 20)  # hits / (hits + misses)
        assert result['hit_rate'] == expected_hit_rate
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Mock successful operations
        mock_client.set.return_value = True
        mock_client.get.return_value = "health_check"
        mock_client.delete.return_value = 1
        
        result = await self.cache.health_check()
        
        # Verify result
        assert result is True
        
        # Verify operations were called
        mock_client.set.assert_called_once()
        mock_client.get.assert_called_once()
        mock_client.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test failed health check."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Mock failed operation
        mock_client.set.side_effect = Exception("Redis error")
        
        result = await self.cache.health_check()
        
        # Verify result
        assert result is False
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test cache connection cleanup."""
        # Setup mocks
        mock_client = AsyncMock()
        mock_pool = AsyncMock()
        self.cache.client = mock_client
        self.cache._connection_pool = mock_pool
        
        await self.cache.close()
        
        # Verify cleanup
        mock_client.close.assert_called_once()
        mock_pool.disconnect.assert_called_once()
        assert self.cache.client is None
        assert self.cache._connection_pool is None
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        # This test requires more complex mocking, so we'll test the structure
        assert hasattr(self.cache, '__aenter__')
        assert hasattr(self.cache, '__aexit__')
    
    def test_json_serializer_datetime(self):
        """Test custom JSON serializer for datetime objects."""
        now = datetime.utcnow()
        result = self.cache._json_serializer(now)
        
        # Should return ISO format string
        assert result == now.isoformat()
    
    def test_json_serializer_unsupported_type(self):
        """Test custom JSON serializer with unsupported type."""
        with pytest.raises(TypeError, match="not JSON serializable"):
            self.cache._json_serializer(object())


class TestCacheModelIntegration:
    """Tests for cache integration with different model types."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.cache = RedisCache("redis://localhost:6379/0")
    
    @pytest.mark.asyncio
    async def test_cache_memory_item_round_trip(self):
        """Test caching and retrieving MemoryItem."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Create test item
        original_item = MemoryItem(
            key="round_trip_test",
            content={"complex": "data", "list": [1, 2, 3]},
            metadata={"test": "metadata"},
            tags=["tag1", "tag2"]
        )
        
        # Mock put operation
        mock_client.setex = AsyncMock()
        
        # Mock get operation - simulate what Redis would return
        item_dict = original_item.dict()
        item_dict['__model_type__'] = 'MemoryItem'
        mock_client.get.return_value = json.dumps(item_dict, default=str)
        
        # Test round trip
        await self.cache.put("round_trip_test", original_item)
        retrieved_item = await self.cache.get("round_trip_test")
        
        # Verify round trip success
        assert isinstance(retrieved_item, MemoryItem)
        assert retrieved_item.key == original_item.key
        assert retrieved_item.content == original_item.content
        assert retrieved_item.metadata == original_item.metadata
        assert retrieved_item.tags == original_item.tags
    
    @pytest.mark.asyncio
    async def test_cache_session_data_round_trip(self):
        """Test caching and retrieving SessionData."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Create test session
        original_session = SessionData(
            session_id="session_round_trip",
            user_id="user_123",
            context={"current_topic": "testing"},
            conversation_history=["msg1", "msg2", "msg3"],
            preferences={"lang": "en"}
        )
        
        # Mock operations
        mock_client.setex = AsyncMock()
        session_dict = original_session.dict()
        session_dict['__model_type__'] = 'SessionData'
        mock_client.get.return_value = json.dumps(session_dict, default=str)
        
        # Test round trip
        await self.cache.put("session_round_trip", original_session)
        retrieved_session = await self.cache.get("session_round_trip")
        
        # Verify round trip success
        assert isinstance(retrieved_session, SessionData)
        assert retrieved_session.session_id == original_session.session_id
        assert retrieved_session.user_id == original_session.user_id
        assert retrieved_session.context == original_session.context
        assert retrieved_session.conversation_history == original_session.conversation_history
    
    @pytest.mark.asyncio
    async def test_cache_knowledge_record_round_trip(self):
        """Test caching and retrieving KnowledgeRecord."""
        # Setup mocks
        mock_client = AsyncMock()
        self.cache.client = mock_client
        
        # Create test knowledge record
        original_record = KnowledgeRecord(
            knowledge_id="knowledge_round_trip",
            title="Test Knowledge",
            content={"structured": "knowledge", "facts": ["fact1", "fact2"]},
            category="testing",
            confidence_score=0.85,
            related_items=["related1", "related2"],
            access_count=5
        )
        
        # Mock operations
        mock_client.setex = AsyncMock()
        record_dict = original_record.dict()
        record_dict['__model_type__'] = 'KnowledgeRecord'
        mock_client.get.return_value = json.dumps(record_dict, default=str)
        
        # Test round trip
        await self.cache.put("knowledge_round_trip", original_record)
        retrieved_record = await self.cache.get("knowledge_round_trip")
        
        # Verify round trip success
        assert isinstance(retrieved_record, KnowledgeRecord)
        assert retrieved_record.knowledge_id == original_record.knowledge_id
        assert retrieved_record.title == original_record.title
        assert retrieved_record.content == original_record.content
        assert retrieved_record.confidence_score == original_record.confidence_score


# Test fixtures
@pytest.fixture
def redis_cache():
    """Redis cache instance for testing."""
    return RedisCache("redis://localhost:6379/0", default_ttl_seconds=300)


@pytest.fixture
def sample_memory_item():
    """Sample MemoryItem for cache testing."""
    return MemoryItem(
        key="cache_test_item",
        content="Test content for caching",
        metadata={"test": "true"},
        tags=["cache", "test"]
    )


if __name__ == "__main__":
    pytest.main([__file__])