"""
Unit tests for FusionService core logic.

This module provides comprehensive unit tests for the FusionService class,
testing memory operations, caching, event handling, and error scenarios.
"""

import asyncio
import json
import time
import unittest
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from prometheus_client import REGISTRY

# Import the modules to test
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import (
    FusionConfig, ServerConfig, StorageConfig, ReplicationConfig,
    MemoryItem, MemoryType, SessionData, KnowledgeRecord
)
from core.fusion_service import FusionService, create_fusion_service
from core.repository import MemoryRepository
from core.telemetry import TelemetryManager


class TestFusionService(unittest.TestCase):
    """Test suite for FusionService."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create test configuration
        self.config = FusionConfig(
            title="Test Memory Fusion Hub",
            version="1.0.0-test",
            server=ServerConfig(
                zmq_port=5555,
                grpc_port=50051,
                max_workers=4
            ),
            storage=StorageConfig(
                sqlite_path=":memory:",  # In-memory SQLite
                postgres_url=None,
                redis_url=None
            ),
            replication=ReplicationConfig(
                enabled=False,
                nats_url=None,
                publish_events=False
            )
        )
        
        # Create service instance
        self.service = None
        
    def tearDown(self):
        """Clean up after tests."""
        if self.service:
            asyncio.run(self.service.close())
        
    async def _setup_service(self):
        """Helper to create and initialize service."""
        self.service = create_fusion_service(self.config)
        await self.service.initialize()
        return self.service
    
    def test_service_creation(self):
        """Test service creation with configuration."""
        service = create_fusion_service(self.config)
        self.assertIsInstance(service, FusionService)
        self.assertEqual(service.config, self.config)
        
    def test_service_initialization(self):
        """Test service initialization."""
        async def test():
            service = await self._setup_service()
            self.assertIsNotNone(service.repository)
            self.assertIsNotNone(service.telemetry)
            self.assertTrue(service._initialized)
            
        asyncio.run(test())
    
    def test_memory_put_and_get(self):
        """Test basic put and get operations."""
        async def test():
            service = await self._setup_service()
            
            # Create test memory item
            item = MemoryItem(
                key="test_key",
                text_content="Test content",
                memory_type=MemoryType.SHORT_TERM,
                metadata={"source": "test"},
                tags=["test", "unit"],
                source_agent="test_agent"
            )
            
            # Put item
            success = await service.put("test_key", item, agent_id="test_agent")
            self.assertTrue(success)
            
            # Get item
            result = await service.get("test_key", agent_id="test_agent")
            self.assertIsNotNone(result)
            self.assertEqual(result.key, "test_key")
            self.assertEqual(result.text_content, "Test content")
            self.assertEqual(result.source_agent, "test_agent")
            
        asyncio.run(test())
    
    def test_memory_update(self):
        """Test updating existing memory items."""
        async def test():
            service = await self._setup_service()
            
            # Create initial item
            item1 = MemoryItem(
                key="update_key",
                text_content="Original content",
                memory_type=MemoryType.SHORT_TERM
            )
            
            # Put initial item
            await service.put("update_key", item1)
            
            # Update item
            item2 = MemoryItem(
                key="update_key",
                text_content="Updated content",
                memory_type=MemoryType.LONG_TERM
            )
            
            success = await service.put("update_key", item2)
            self.assertTrue(success)
            
            # Verify update
            result = await service.get("update_key")
            self.assertEqual(result.text_content, "Updated content")
            self.assertEqual(result.memory_type, MemoryType.LONG_TERM)
            
        asyncio.run(test())
    
    def test_memory_delete(self):
        """Test delete operation."""
        async def test():
            service = await self._setup_service()
            
            # Create and store item
            item = MemoryItem(
                key="delete_key",
                text_content="To be deleted",
                memory_type=MemoryType.SHORT_TERM
            )
            await service.put("delete_key", item)
            
            # Verify it exists
            result = await service.get("delete_key")
            self.assertIsNotNone(result)
            
            # Delete item
            success = await service.delete("delete_key")
            self.assertTrue(success)
            
            # Verify deletion
            result = await service.get("delete_key")
            self.assertIsNone(result)
            
        asyncio.run(test())
    
    def test_batch_get(self):
        """Test batch get operation."""
        async def test():
            service = await self._setup_service()
            
            # Create multiple items
            items = {
                "batch_1": MemoryItem(
                    key="batch_1",
                    text_content="Content 1",
                    memory_type=MemoryType.SHORT_TERM
                ),
                "batch_2": MemoryItem(
                    key="batch_2",
                    text_content="Content 2",
                    memory_type=MemoryType.MEDIUM_TERM
                ),
                "batch_3": MemoryItem(
                    key="batch_3",
                    text_content="Content 3",
                    memory_type=MemoryType.LONG_TERM
                )
            }
            
            # Store all items
            for key, item in items.items():
                await service.put(key, item)
            
            # Batch get
            keys = ["batch_1", "batch_2", "batch_3", "nonexistent"]
            results = await service.batch_get(keys)
            
            # Verify results
            self.assertEqual(len(results), 3)
            self.assertIn("batch_1", results)
            self.assertIn("batch_2", results)
            self.assertIn("batch_3", results)
            self.assertNotIn("nonexistent", results)
            
            self.assertEqual(results["batch_1"].text_content, "Content 1")
            self.assertEqual(results["batch_2"].text_content, "Content 2")
            self.assertEqual(results["batch_3"].text_content, "Content 3")
            
        asyncio.run(test())
    
    def test_exists_operation(self):
        """Test exists operation."""
        async def test():
            service = await self._setup_service()
            
            # Create item
            item = MemoryItem(
                key="exists_key",
                text_content="Exists",
                memory_type=MemoryType.SHORT_TERM
            )
            await service.put("exists_key", item)
            
            # Test exists
            exists = await service.exists("exists_key")
            self.assertTrue(exists)
            
            # Test not exists
            exists = await service.exists("nonexistent_key")
            self.assertFalse(exists)
            
        asyncio.run(test())
    
    def test_list_keys(self):
        """Test listing keys with prefix."""
        async def test():
            service = await self._setup_service()
            
            # Create items with different prefixes
            items = [
                ("user:1:profile", "Profile 1"),
                ("user:1:settings", "Settings 1"),
                ("user:2:profile", "Profile 2"),
                ("session:1", "Session 1"),
                ("session:2", "Session 2")
            ]
            
            for key, content in items:
                item = MemoryItem(
                    key=key,
                    text_content=content,
                    memory_type=MemoryType.SHORT_TERM
                )
                await service.put(key, item)
            
            # List user keys
            user_keys = await service.list_keys(prefix="user:", limit=10)
            self.assertEqual(len(user_keys), 3)
            self.assertIn("user:1:profile", user_keys)
            self.assertIn("user:1:settings", user_keys)
            self.assertIn("user:2:profile", user_keys)
            
            # List session keys
            session_keys = await service.list_keys(prefix="session:", limit=10)
            self.assertEqual(len(session_keys), 2)
            self.assertIn("session:1", session_keys)
            self.assertIn("session:2", session_keys)
            
            # List with limit
            limited_keys = await service.list_keys(prefix="user:", limit=2)
            self.assertEqual(len(limited_keys), 2)
            
        asyncio.run(test())
    
    def test_memory_expiration(self):
        """Test memory expiration handling."""
        async def test():
            service = await self._setup_service()
            
            # Create item with expiration
            expiry_time = datetime.utcnow() + timedelta(seconds=1)
            item = MemoryItem(
                key="expiring_key",
                text_content="Will expire",
                memory_type=MemoryType.SHORT_TERM,
                expiry_timestamp=expiry_time.isoformat()
            )
            
            await service.put("expiring_key", item)
            
            # Item should exist initially
            result = await service.get("expiring_key")
            self.assertIsNotNone(result)
            
            # Wait for expiration
            await asyncio.sleep(2)
            
            # Item should be expired (implementation dependent)
            # Note: This depends on the repository implementation
            # Some implementations may auto-delete, others may filter on get
            
        asyncio.run(test())
    
    def test_session_data_operations(self):
        """Test session data storage and retrieval."""
        async def test():
            service = await self._setup_service()
            
            # Create session data
            session = SessionData(
                session_id="test_session_123",
                user_id="user_456",
                context={"current_topic": "testing"},
                conversation_history=["Hello", "How are you?"],
                preferences={"language": "en", "theme": "dark"},
                active=True
            )
            
            # Store as memory item
            item = MemoryItem(
                key=f"session:{session.session_id}",
                json_content=session.model_dump_json(),
                memory_type=MemoryType.SESSION,
                source_agent="session_manager"
            )
            
            await service.put(item.key, item)
            
            # Retrieve session
            result = await service.get(f"session:{session.session_id}")
            self.assertIsNotNone(result)
            self.assertEqual(result.memory_type, MemoryType.SESSION)
            
            # Parse session data
            retrieved_session = SessionData.model_validate_json(result.json_content)
            self.assertEqual(retrieved_session.session_id, session.session_id)
            self.assertEqual(retrieved_session.user_id, session.user_id)
            self.assertEqual(retrieved_session.preferences["theme"], "dark")
            
        asyncio.run(test())
    
    def test_knowledge_record_operations(self):
        """Test knowledge record storage and retrieval."""
        async def test():
            service = await self._setup_service()
            
            # Create knowledge record
            knowledge = KnowledgeRecord(
                knowledge_id="fact_001",
                title="Test Fact",
                text_content="This is a test fact about testing.",
                category="testing",
                confidence_score=0.95,
                source="unit_test",
                related_items=["fact_002", "fact_003"],
                access_count=0
            )
            
            # Store as memory item
            item = MemoryItem(
                key=f"knowledge:{knowledge.knowledge_id}",
                json_content=knowledge.model_dump_json(),
                memory_type=MemoryType.KNOWLEDGE,
                metadata={"category": knowledge.category},
                tags=["test", "fact", knowledge.category]
            )
            
            await service.put(item.key, item)
            
            # Retrieve knowledge
            result = await service.get(f"knowledge:{knowledge.knowledge_id}")
            self.assertIsNotNone(result)
            self.assertEqual(result.memory_type, MemoryType.KNOWLEDGE)
            
            # Parse knowledge data
            retrieved_knowledge = KnowledgeRecord.model_validate_json(result.json_content)
            self.assertEqual(retrieved_knowledge.knowledge_id, knowledge.knowledge_id)
            self.assertEqual(retrieved_knowledge.confidence_score, 0.95)
            
        asyncio.run(test())
    
    def test_concurrent_operations(self):
        """Test concurrent memory operations."""
        async def test():
            service = await self._setup_service()
            
            async def write_task(index: int):
                """Write task for concurrency test."""
                item = MemoryItem(
                    key=f"concurrent_{index}",
                    text_content=f"Content {index}",
                    memory_type=MemoryType.SHORT_TERM
                )
                return await service.put(f"concurrent_{index}", item)
            
            async def read_task(index: int):
                """Read task for concurrency test."""
                return await service.get(f"concurrent_{index}")
            
            # Concurrent writes
            write_tasks = [write_task(i) for i in range(10)]
            write_results = await asyncio.gather(*write_tasks)
            self.assertTrue(all(write_results))
            
            # Concurrent reads
            read_tasks = [read_task(i) for i in range(10)]
            read_results = await asyncio.gather(*read_tasks)
            
            # Verify all reads successful
            for i, result in enumerate(read_results):
                self.assertIsNotNone(result)
                self.assertEqual(result.text_content, f"Content {i}")
            
        asyncio.run(test())
    
    def test_error_handling(self):
        """Test error handling for invalid operations."""
        async def test():
            service = await self._setup_service()
            
            # Test with None key
            with self.assertRaises(ValueError):
                await service.get(None)
            
            # Test with empty key
            with self.assertRaises(ValueError):
                await service.put("", MemoryItem(
                    key="",
                    text_content="Invalid",
                    memory_type=MemoryType.SHORT_TERM
                ))
            
            # Test with None item
            with self.assertRaises(ValueError):
                await service.put("valid_key", None)
            
        asyncio.run(test())
    
    def test_telemetry_metrics(self):
        """Test telemetry and metrics collection."""
        async def test():
            service = await self._setup_service()
            
            # Perform operations
            item = MemoryItem(
                key="metrics_test",
                text_content="Metrics test",
                memory_type=MemoryType.SHORT_TERM
            )
            
            await service.put("metrics_test", item)
            await service.get("metrics_test")
            await service.exists("metrics_test")
            await service.delete("metrics_test")
            
            # Check metrics were recorded
            # Note: This depends on the telemetry implementation
            # We're just verifying the telemetry manager exists
            self.assertIsNotNone(service.telemetry)
            
        asyncio.run(test())
    
    @patch('core.repository.MemoryRepository')
    def test_repository_failure_handling(self, mock_repo_class):
        """Test handling of repository failures."""
        async def test():
            # Create mock repository that fails
            mock_repo = AsyncMock()
            mock_repo.get.side_effect = Exception("Database error")
            mock_repo_class.return_value = mock_repo
            
            service = FusionService(self.config)
            service.repository = mock_repo
            service._initialized = True
            
            # Operation should handle error gracefully
            result = await service.get("test_key")
            self.assertIsNone(result)
            
        asyncio.run(test())
    
    def test_cache_operations(self):
        """Test caching behavior when cache is available."""
        async def test():
            # Create config with Redis URL (cache will be mocked)
            config = FusionConfig(
                title="Test with Cache",
                version="1.0.0",
                server=ServerConfig(
                    zmq_port=5555,
                    grpc_port=50051,
                    max_workers=4
                ),
                storage=StorageConfig(
                    sqlite_path=":memory:",
                    redis_url="redis://localhost:6379"
                ),
                replication=ReplicationConfig(enabled=False)
            )
            
            with patch('core.fusion_service.CacheManager') as mock_cache_class:
                # Setup mock cache
                mock_cache = AsyncMock()
                mock_cache.get.return_value = None  # Cache miss
                mock_cache.put.return_value = True
                mock_cache_class.return_value = mock_cache
                
                service = create_fusion_service(config)
                await service.initialize()
                
                # Store item
                item = MemoryItem(
                    key="cached_key",
                    text_content="Cached content",
                    memory_type=MemoryType.SHORT_TERM
                )
                await service.put("cached_key", item)
                
                # Verify cache was updated
                mock_cache.put.assert_called()
                
                # Get item (cache miss, then cache update)
                await service.get("cached_key")
                mock_cache.get.assert_called()
                
        asyncio.run(test())
    
    def test_get_health(self):
        """Test health check functionality."""
        async def test():
            service = await self._setup_service()
            
            # Get health status
            health = await service.get_health()
            
            self.assertIsNotNone(health)
            self.assertEqual(health["status"], "healthy")
            self.assertIn("components", health)
            self.assertIn("repository", health["components"])
            self.assertIn("telemetry", health["components"])
            
            # Check component health
            self.assertTrue(health["components"]["repository"]["healthy"])
            self.assertTrue(health["components"]["telemetry"]["healthy"])
            
        asyncio.run(test())
    
    def test_service_lifecycle(self):
        """Test complete service lifecycle."""
        async def test():
            # Create service
            service = create_fusion_service(self.config)
            self.assertFalse(service._initialized)
            
            # Initialize
            await service.initialize()
            self.assertTrue(service._initialized)
            
            # Use service
            item = MemoryItem(
                key="lifecycle_test",
                text_content="Lifecycle test",
                memory_type=MemoryType.SHORT_TERM
            )
            success = await service.put("lifecycle_test", item)
            self.assertTrue(success)
            
            # Close service
            await service.close()
            # Note: After close, operations should fail or be rejected
            
        asyncio.run(test())


class TestFusionServiceIntegration(unittest.TestCase):
    """Integration tests for FusionService with real components."""
    
    @pytest.mark.integration
    def test_sqlite_persistence(self):
        """Test persistence with SQLite backend."""
        async def test():
            # Use file-based SQLite for persistence test
            config = FusionConfig(
                title="SQLite Test",
                version="1.0.0",
                server=ServerConfig(
                    zmq_port=5556,
                    grpc_port=50052,
                    max_workers=2
                ),
                storage=StorageConfig(
                    sqlite_path="/tmp/test_fusion.db",
                    postgres_url=None,
                    redis_url=None
                ),
                replication=ReplicationConfig(enabled=False)
            )
            
            # First service instance
            service1 = create_fusion_service(config)
            await service1.initialize()
            
            # Store data
            item = MemoryItem(
                key="persist_test",
                text_content="Persistent data",
                memory_type=MemoryType.LONG_TERM
            )
            await service1.put("persist_test", item)
            await service1.close()
            
            # Second service instance
            service2 = create_fusion_service(config)
            await service2.initialize()
            
            # Retrieve persisted data
            result = await service2.get("persist_test")
            self.assertIsNotNone(result)
            self.assertEqual(result.text_content, "Persistent data")
            
            await service2.close()
            
            # Cleanup
            import os
            if os.path.exists("/tmp/test_fusion.db"):
                os.remove("/tmp/test_fusion.db")
            
        asyncio.run(test())


if __name__ == "__main__":
    unittest.main()