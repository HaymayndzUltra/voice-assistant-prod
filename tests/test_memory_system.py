#!/usr/bin/env python3
"""
Memory System Test Suite

This script provides comprehensive testing for the distributed memory system,
including unit tests, integration tests, and performance tests.
"""

import os
import sys
import time
import json
import unittest
import threading
import zmq
import sqlite3
import redis
import pytest
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import random
import string
import statistics

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MemorySystemTest")

# Import memory components (adjust paths as needed)
try:
    from main_pc_code.agents.memory_client import MemoryClient
except ImportError:
    logger.warning("Could not import MemoryClient. Some tests will be skipped.")

# Mock classes for unit testing
class MockMemoryClient:
    """Mock implementation of MemoryClient for unit testing"""
    
    def __init__(self):
        self.memories = {}
        self.relationships = {}
        self.groups = {}
        
    def add_memory(self, content, memory_type="general", memory_tier="short", 
                   importance=0.5, metadata=None, tags=None, parent_id=None):
        memory_id = f"mem-{len(self.memories) + 1}"
        self.memories[memory_id] = {
            "memory_id": memory_id,
            "content": content,
            "memory_type": memory_type,
            "memory_tier": memory_tier,
            "importance": importance,
            "metadata": metadata or {},
            "tags": tags or [],
            "parent_id": parent_id,
            "created_at": time.time(),
            "access_count": 0
        }
        return {"status": "success", "memory_id": memory_id}
    
    def get_memory(self, memory_id):
        if memory_id in self.memories:
            self.memories[memory_id]["access_count"] += 1
            return {"status": "success", "memory": self.memories[memory_id]}
        return {"status": "error", "message": f"Memory {memory_id} not found"}
    
    def search_memory(self, query, memory_type=None, limit=10):
        results = []
        for memory_id, memory in self.memories.items():
            if query.lower() in memory["content"].lower():
                if memory_type is None or memory["memory_type"] == memory_type:
                    results.append(memory)
                    if len(results) >= limit:
                        break
        return {"status": "success", "results": results, "count": len(results)}

class TestMemoryClientUnit(unittest.TestCase):
    """Unit tests for MemoryClient using mocks"""
    
    def setUp(self):
        self.mock_client = MockMemoryClient()
        
    def test_add_memory(self):
        """Test adding a memory"""
        result = self.mock_client.add_memory("Test memory content")
        self.assertEqual(result["status"], "success")
        self.assertTrue("memory_id" in result)
        
    def test_get_memory(self):
        """Test retrieving a memory"""
        add_result = self.mock_client.add_memory("Test memory for retrieval")
        memory_id = add_result["memory_id"]
        
        get_result = self.mock_client.get_memory(memory_id)
        self.assertEqual(get_result["status"], "success")
        self.assertEqual(get_result["memory"]["content"], "Test memory for retrieval")
        
    def test_get_nonexistent_memory(self):
        """Test retrieving a memory that doesn't exist"""
        result = self.mock_client.get_memory("non-existent-id")
        self.assertEqual(result["status"], "error")
        
    def test_search_memory(self):
        """Test searching for memories"""
        self.mock_client.add_memory("Apple is a fruit")
        self.mock_client.add_memory("Banana is yellow")
        self.mock_client.add_memory("Apple pie is delicious")
        
        result = self.mock_client.search_memory("apple")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 2)
        
        # Test with memory_type filter
        self.mock_client.add_memory("Knowledge about apples", memory_type="knowledge")
        result = self.mock_client.search_memory("apple", memory_type="knowledge")
        self.assertEqual(result["count"], 1)

@pytest.mark.integration
class TestMemoryClientIntegration:
    """Integration tests for MemoryClient with actual MemoryOrchestratorService"""
    
    @pytest.fixture(scope="class")
    def memory_client(self):
        """Create a MemoryClient instance for testing"""
        try:
            client = MemoryClient(agent_name="TestClient", port=5799)
            client.set_agent_id("memory_system_test")
            yield client
            client.cleanup()
        except Exception as e:
            pytest.skip(f"Could not initialize MemoryClient: {e}")
    
    def test_connection(self, memory_client):
        """Test connection to MemoryOrchestratorService"""
        status = memory_client.get_circuit_breaker_status()
        assert status["status"] == "success", "Failed to connect to MemoryOrchestratorService"
    
    def test_add_and_retrieve_memory(self, memory_client):
        """Test adding and retrieving a memory"""
        test_content = f"Test memory {random.randint(1000, 9999)}"
        add_result = memory_client.add_memory(
            content=test_content,
            memory_type="test",
            memory_tier="short",
            importance=0.8,
            metadata={"test_id": "integration_test"},
            tags=["test", "integration"]
        )
        
        assert add_result["status"] == "success", "Failed to add memory"
        memory_id = add_result["memory_id"]
        
        # Retrieve the memory
        get_result = memory_client.get_memory(memory_id)
        assert get_result["status"] == "success", "Failed to retrieve memory"
        assert get_result["memory"]["content"] == test_content, "Memory content doesn't match"
    
    def test_memory_relationships(self, memory_client):
        """Test creating and retrieving memory relationships"""
        # Create parent memory
        parent_result = memory_client.add_memory(
            content="Parent memory",
            memory_type="test",
            tags=["parent", "test"]
        )
        parent_id = parent_result["memory_id"]
        
        # Create child memory
        child_result = memory_client.add_memory(
            content="Child memory",
            memory_type="test",
            parent_id=parent_id,
            tags=["child", "test"]
        )
        child_id = child_result["memory_id"]
        
        # Add explicit relationship
        rel_result = memory_client.add_relationship(
            source_id=parent_id,
            target_id=child_id,
            relationship_type="parent_of",
            strength=1.0
        )
        assert rel_result["status"] == "success", "Failed to add relationship"
        
        # Get children
        children_result = memory_client.get_children(parent_id)
        assert children_result["status"] == "success", "Failed to get children"
        assert len(children_result["children"]) > 0, "No children found"
        
        # Get related memories
        related_result = memory_client.get_related_memories(parent_id)
        assert related_result["status"] == "success", "Failed to get related memories"
        assert len(related_result["related_memories"]) > 0, "No related memories found"
    
    def test_search_memory(self, memory_client):
        """Test searching for memories"""
        # Add some test memories with unique identifier
        unique_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        test_contents = [
            f"SEARCHTEST_{unique_id} Apple is a fruit",
            f"SEARCHTEST_{unique_id} Banana is yellow",
            f"SEARCHTEST_{unique_id} Orange is orange"
        ]
        
        for content in test_contents:
            memory_client.add_memory(content=content, memory_type="test_search")
        
        # Search for the unique identifier
        search_result = memory_client.search_memory(f"SEARCHTEST_{unique_id}")
        assert search_result["status"] == "success", "Search failed"
        assert search_result["count"] >= 3, f"Expected at least 3 results, got {search_result['count']}"
    
    def test_error_handling(self, memory_client):
        """Test error handling for invalid operations"""
        # Try to get a non-existent memory
        result = memory_client.get_memory("non-existent-memory-id")
        assert result["status"] == "error", "Expected error status for non-existent memory"
        
        # Try to add a relationship with non-existent memories
        rel_result = memory_client.add_relationship(
            source_id="non-existent-source",
            target_id="non-existent-target",
            relationship_type="test"
        )
        assert rel_result["status"] == "error", "Expected error for invalid relationship"

@pytest.mark.performance
class TestMemorySystemPerformance:
    """Performance tests for the memory system"""
    
    @pytest.fixture(scope="class")
    def memory_client(self):
        """Create a MemoryClient instance for testing"""
        try:
            client = MemoryClient(agent_name="PerfTestClient", port=5798)
            client.set_agent_id("performance_test")
            yield client
            client.cleanup()
        except Exception as e:
            pytest.skip(f"Could not initialize MemoryClient: {e}")
    
    def test_add_memory_performance(self, memory_client):
        """Test add_memory performance"""
        num_iterations = 50
        latencies = []
        
        for i in range(num_iterations):
            content = f"Performance test memory {i} with some additional content to make it realistic"
            start_time = time.time()
            result = memory_client.add_memory(content=content, memory_type="perf_test")
            end_time = time.time()
            
            assert result["status"] == "success", f"Failed to add memory on iteration {i}"
            latencies.append((end_time - start_time) * 1000)  # Convert to ms
        
        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(num_iterations * 0.95)]
        p99_latency = sorted(latencies)[int(num_iterations * 0.99)]
        
        logger.info(f"Add Memory Performance: Avg={avg_latency:.2f}ms, P95={p95_latency:.2f}ms, P99={p99_latency:.2f}ms")
        
        # Reasonable performance expectations (adjust based on your system)
        assert avg_latency < 200, f"Average latency too high: {avg_latency:.2f}ms"
        assert p95_latency < 300, f"P95 latency too high: {p95_latency:.2f}ms"
    
    def test_get_memory_performance(self, memory_client):
        """Test get_memory performance"""
        # First create test memories
        memory_ids = []
        for i in range(20):
            result = memory_client.add_memory(
                content=f"Performance test get memory {i}",
                memory_type="perf_test"
            )
            memory_ids.append(result["memory_id"])
        
        # Now test get performance
        num_iterations = 100
        latencies = []
        
        for i in range(num_iterations):
            memory_id = random.choice(memory_ids)
            start_time = time.time()
            result = memory_client.get_memory(memory_id)
            end_time = time.time()
            
            assert result["status"] == "success", f"Failed to get memory on iteration {i}"
            latencies.append((end_time - start_time) * 1000)  # Convert to ms
        
        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(num_iterations * 0.95)]
        
        logger.info(f"Get Memory Performance: Avg={avg_latency:.2f}ms, P95={p95_latency:.2f}ms")
        
        # Reasonable performance expectations (adjust based on your system)
        assert avg_latency < 100, f"Average latency too high: {avg_latency:.2f}ms"
        assert p95_latency < 200, f"P95 latency too high: {p95_latency:.2f}ms"
    
    def test_search_memory_performance(self, memory_client):
        """Test search_memory performance"""
        # First create test memories with searchable content
        unique_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        for i in range(30):
            memory_client.add_memory(
                content=f"PERFTEST_{unique_id} Performance search test memory {i} with additional content",
                memory_type="perf_test"
            )
        
        # Now test search performance
        num_iterations = 20
        latencies = []
        
        for i in range(num_iterations):
            start_time = time.time()
            result = memory_client.search_memory(f"PERFTEST_{unique_id}")
            end_time = time.time()
            
            assert result["status"] == "success", f"Failed to search memory on iteration {i}"
            latencies.append((end_time - start_time) * 1000)  # Convert to ms
        
        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(num_iterations * 0.95)]
        
        logger.info(f"Search Memory Performance: Avg={avg_latency:.2f}ms, P95={p95_latency:.2f}ms")
        
        # Reasonable performance expectations (adjust based on your system)
        assert avg_latency < 300, f"Average latency too high: {avg_latency:.2f}ms"
        assert p95_latency < 500, f"P95 latency too high: {p95_latency:.2f}ms"
    
    def test_cache_effectiveness(self, memory_client):
        """Test cache effectiveness for repeated memory retrievals"""
        # Create test memory
        add_result = memory_client.add_memory(
            content="Cache test memory with unique content",
            memory_type="cache_test"
        )
        memory_id = add_result["memory_id"]
        
        # First access (cache miss)
        start_time = time.time()
        memory_client.get_memory(memory_id)
        first_access_time = time.time() - start_time
        
        # Second access (should be cache hit)
        start_time = time.time()
        memory_client.get_memory(memory_id)
        second_access_time = time.time() - start_time
        
        logger.info(f"Cache Test: First access={first_access_time*1000:.2f}ms, Second access={second_access_time*1000:.2f}ms")
        
        # Second access should be significantly faster if caching is working
        assert second_access_time < first_access_time * 0.8, "Cache doesn't appear to be effective"

def run_tests():
    """Run all tests"""
    # Run unit tests
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
    
    # Run integration and performance tests with pytest
    pytest.main(["-xvs", __file__, "-m", "integration or performance"])

if __name__ == "__main__":
    run_tests() 