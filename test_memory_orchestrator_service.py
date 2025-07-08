#!/usr/bin/env python3
"""
Memory Orchestrator Service Test Suite

This script provides comprehensive testing for the MemoryOrchestratorService,
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
import tempfile
import shutil
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
logger = logging.getLogger("MemoryOrchestratorTest")

# Import memory components (adjust paths as needed)
try:
    from pc2_code.agents.memory_orchestrator_service import MemoryOrchestratorService, MemoryStorageManager
except ImportError:
    logger.warning("Could not import MemoryOrchestratorService. Some tests will be skipped.")

class TestMemoryStorageManagerUnit(unittest.TestCase):
    """Unit tests for MemoryStorageManager"""
    
    def setUp(self):
        """Set up a test database and storage manager"""
        self.test_db_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.test_db_dir, "test_memory.db")
        self.storage = MemoryStorageManager(db_path=self.test_db_path, redis_conn=None)
    
    def tearDown(self):
        """Clean up test database"""
        shutil.rmtree(self.test_db_dir)
    
    def test_add_memory(self):
        """Test adding a memory entry"""
        from pc2_code.agents.memory_orchestrator_service import MemoryEntry
        
        memory = MemoryEntry(
            content="Test memory content",
            memory_type="test",
            memory_tier="short",
            importance=0.8,
            metadata={"test": True},
            tags=["test", "unit"]
        )
        
        result = self.storage.add_or_update_memory(memory)
        self.assertTrue(result)
        
        # Verify memory was added
        retrieved = self.storage.get_memory(memory.memory_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.content, "Test memory content")
        self.assertEqual(retrieved.memory_type, "test")
        self.assertEqual(retrieved.importance, 0.8)
    
    def test_memory_relationships(self):
        """Test adding and retrieving memory relationships"""
        from pc2_code.agents.memory_orchestrator_service import MemoryEntry
        
        # Create parent memory
        parent = MemoryEntry(
            content="Parent memory",
            memory_type="test",
            memory_tier="short"
        )
        self.storage.add_or_update_memory(parent)
        
        # Create child memory
        child = MemoryEntry(
            content="Child memory",
            memory_type="test",
            memory_tier="short",
            parent_id=parent.memory_id
        )
        self.storage.add_or_update_memory(child)
        
        # Add explicit relationship
        result = self.storage.add_memory_relationship(
            parent.memory_id, 
            child.memory_id, 
            "parent_of", 
            1.0
        )
        self.assertTrue(result)
        
        # Get children
        children = self.storage.get_memory_children(parent.memory_id)
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0].content, "Child memory")
        
        # Get related memories
        related = self.storage.get_related_memories(parent.memory_id)
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0]["memory"]["memory_id"], child.memory_id)
    
    def test_context_groups(self):
        """Test context group functionality"""
        from pc2_code.agents.memory_orchestrator_service import MemoryEntry
        
        # Create a context group
        group_id = self.storage.create_context_group("Test Group", "A test group")
        self.assertIsNotNone(group_id)
        
        # Create a memory
        memory = MemoryEntry(content="Group test memory", memory_type="test")
        self.storage.add_or_update_memory(memory)
        
        # Add memory to group
        result = self.storage.add_memory_to_group(memory.memory_id, group_id)
        self.assertTrue(result)
        
        # Note: get_memories_by_group is not implemented yet in MemoryStorageManager
        # This would be the place to test it when implemented

@pytest.mark.integration
class TestMemoryOrchestratorServiceIntegration:
    """Integration tests for MemoryOrchestratorService"""
    
    @pytest.fixture(scope="class")
    def orchestrator_service(self):
        """Create a MemoryOrchestratorService instance for testing"""
        try:
            # Create a temporary directory for test database
            test_dir = tempfile.mkdtemp()
            test_db_path = os.path.join(test_dir, "test_memory.db")
            
            # Set environment variables for testing
            os.environ["MEMORY_SQLITE_PATH"] = test_db_path
            
            # Create service
            service = MemoryOrchestratorService(port=7999)  # Use different port for testing
            
            # Start service in a separate thread
            service_thread = threading.Thread(target=service.run, daemon=True)
            service_thread.start()
            
            # Give it time to start
            time.sleep(1)
            
            yield service
            
            # Clean up
            service.cleanup()
            shutil.rmtree(test_dir)
            
        except Exception as e:
            pytest.skip(f"Could not initialize MemoryOrchestratorService: {e}")
    
    @pytest.fixture(scope="class")
    def client_socket(self):
        """Create a ZMQ client socket for testing"""
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect(f"tcp://localhost:7999")  # Connect to test service
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        
        yield socket
        
        socket.close()
        context.term()
    
    def test_add_memory(self, client_socket):
        """Test adding a memory through the service"""
        request = {
            "action": "add_memory",
            "data": {
                "content": "Test memory through service",
                "memory_type": "test",
                "memory_tier": "short",
                "importance": 0.8,
                "metadata": {"test": True},
                "tags": ["test", "integration"]
            }
        }
        
        client_socket.send_json(request)
        response = client_socket.recv_json()
        
        assert response["status"] == "success", "Failed to add memory"
        assert "memory_id" in response, "No memory_id in response"
        
        return response["memory_id"]
    
    def test_get_memory(self, client_socket):
        """Test retrieving a memory through the service"""
        # First add a memory
        memory_id = self.test_add_memory(client_socket)
        
        # Now retrieve it
        request = {
            "action": "get_memory",
            "data": {
                "memory_id": memory_id
            }
        }
        
        client_socket.send_json(request)
        response = client_socket.recv_json()
        
        assert response["status"] == "success", "Failed to get memory"
        assert "memory" in response, "No memory in response"
        assert response["memory"]["content"] == "Test memory through service", "Memory content doesn't match"
    
    def test_search_memory(self, client_socket):
        """Test searching for memories through the service"""
        # Add some test memories with unique identifier
        unique_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        for i in range(3):
            request = {
                "action": "add_memory",
                "data": {
                    "content": f"SEARCHTEST_{unique_id} Test memory {i}",
                    "memory_type": "test_search"
                }
            }
            client_socket.send_json(request)
            client_socket.recv_json()  # Wait for response but ignore it
        
        # Now search for them
        request = {
            "action": "search_memory",
            "data": {
                "query": f"SEARCHTEST_{unique_id}",
                "limit": 10
            }
        }
        
        client_socket.send_json(request)
        response = client_socket.recv_json()
        
        assert response["status"] == "success", "Search failed"
        assert response["count"] >= 3, f"Expected at least 3 results, got {response['count']}"
    
    def test_memory_relationships(self, client_socket):
        """Test memory relationships through the service"""
        # Add parent memory
        parent_request = {
            "action": "add_memory",
            "data": {
                "content": "Parent memory for relationship test",
                "memory_type": "test_rel"
            }
        }
        client_socket.send_json(parent_request)
        parent_response = client_socket.recv_json()
        parent_id = parent_response["memory_id"]
        
        # Add child memory
        child_request = {
            "action": "add_memory",
            "data": {
                "content": "Child memory for relationship test",
                "memory_type": "test_rel",
                "parent_id": parent_id
            }
        }
        client_socket.send_json(child_request)
        child_response = client_socket.recv_json()
        child_id = child_response["memory_id"]
        
        # Add explicit relationship
        rel_request = {
            "action": "add_relationship",
            "data": {
                "source_id": parent_id,
                "target_id": child_id,
                "relationship_type": "parent_of",
                "strength": 1.0
            }
        }
        client_socket.send_json(rel_request)
        rel_response = client_socket.recv_json()
        assert rel_response["status"] == "success", "Failed to add relationship"
        
        # Get children
        children_request = {
            "action": "get_children",
            "data": {
                "parent_id": parent_id
            }
        }
        client_socket.send_json(children_request)
        children_response = client_socket.recv_json()
        assert children_response["status"] == "success", "Failed to get children"
        assert len(children_response["children"]) > 0, "No children found"
        
        # Get related memories
        related_request = {
            "action": "get_related",
            "data": {
                "memory_id": parent_id
            }
        }
        client_socket.send_json(related_request)
        related_response = client_socket.recv_json()
        assert related_response["status"] == "success", "Failed to get related memories"
        assert len(related_response["related_memories"]) > 0, "No related memories found"

@pytest.mark.performance
class TestMemoryOrchestratorServicePerformance:
    """Performance tests for MemoryOrchestratorService"""
    
    @pytest.fixture(scope="class")
    def client_socket(self):
        """Create a ZMQ client socket for testing"""
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect(f"tcp://localhost:7140")  # Connect to actual service
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        
        # Test connection
        try:
            socket.send_json({"action": "health_check"})
            socket.recv_json()
        except Exception as e:
            pytest.skip(f"Could not connect to MemoryOrchestratorService: {e}")
        
        yield socket
        
        socket.close()
        context.term()
    
    def test_add_memory_performance(self, client_socket):
        """Test add_memory performance"""
        num_iterations = 50
        latencies = []
        
        for i in range(num_iterations):
            content = f"Performance test memory {i} with some additional content to make it realistic"
            request = {
                "action": "add_memory",
                "data": {
                    "content": content,
                    "memory_type": "perf_test"
                }
            }
            
            start_time = time.time()
            client_socket.send_json(request)
            response = client_socket.recv_json()
            end_time = time.time()
            
            assert response["status"] == "success", f"Failed to add memory on iteration {i}"
            latencies.append((end_time - start_time) * 1000)  # Convert to ms
        
        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(num_iterations * 0.95)]
        p99_latency = sorted(latencies)[int(num_iterations * 0.99)]
        
        logger.info(f"Add Memory Performance: Avg={avg_latency:.2f}ms, P95={p95_latency:.2f}ms, P99={p99_latency:.2f}ms")
        
        # Reasonable performance expectations (adjust based on your system)
        assert avg_latency < 200, f"Average latency too high: {avg_latency:.2f}ms"
        assert p95_latency < 300, f"P95 latency too high: {p95_latency:.2f}ms"
    
    def test_get_memory_performance(self, client_socket):
        """Test get_memory performance"""
        # First create test memories
        memory_ids = []
        for i in range(20):
            request = {
                "action": "add_memory",
                "data": {
                    "content": f"Performance test get memory {i}",
                    "memory_type": "perf_test"
                }
            }
            client_socket.send_json(request)
            response = client_socket.recv_json()
            memory_ids.append(response["memory_id"])
        
        # Now test get performance
        num_iterations = 100
        latencies = []
        
        for i in range(num_iterations):
            memory_id = random.choice(memory_ids)
            request = {
                "action": "get_memory",
                "data": {
                    "memory_id": memory_id
                }
            }
            
            start_time = time.time()
            client_socket.send_json(request)
            response = client_socket.recv_json()
            end_time = time.time()
            
            assert response["status"] == "success", f"Failed to get memory on iteration {i}"
            latencies.append((end_time - start_time) * 1000)  # Convert to ms
        
        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(num_iterations * 0.95)]
        
        logger.info(f"Get Memory Performance: Avg={avg_latency:.2f}ms, P95={p95_latency:.2f}ms")
        
        # Reasonable performance expectations (adjust based on your system)
        assert avg_latency < 100, f"Average latency too high: {avg_latency:.2f}ms"
        assert p95_latency < 200, f"P95 latency too high: {p95_latency:.2f}ms"
    
    def test_search_memory_performance(self, client_socket):
        """Test search_memory performance"""
        # First create test memories with searchable content
        unique_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        for i in range(30):
            request = {
                "action": "add_memory",
                "data": {
                    "content": f"PERFTEST_{unique_id} Performance search test memory {i} with additional content",
                    "memory_type": "perf_test"
                }
            }
            client_socket.send_json(request)
            client_socket.recv_json()
        
        # Now test search performance
        num_iterations = 20
        latencies = []
        
        for i in range(num_iterations):
            request = {
                "action": "search_memory",
                "data": {
                    "query": f"PERFTEST_{unique_id}",
                    "limit": 10
                }
            }
            
            start_time = time.time()
            client_socket.send_json(request)
            response = client_socket.recv_json()
            end_time = time.time()
            
            assert response["status"] == "success", f"Failed to search memory on iteration {i}"
            latencies.append((end_time - start_time) * 1000)  # Convert to ms
        
        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(num_iterations * 0.95)]
        
        logger.info(f"Search Memory Performance: Avg={avg_latency:.2f}ms, P95={p95_latency:.2f}ms")
        
        # Reasonable performance expectations (adjust based on your system)
        assert avg_latency < 300, f"Average latency too high: {avg_latency:.2f}ms"
        assert p95_latency < 500, f"P95 latency too high: {p95_latency:.2f}ms"
    
    def test_batch_operations_performance(self, client_socket):
        """Test batch operations performance"""
        # Create batch of memories
        num_memories = 20
        memories = []
        
        for i in range(num_memories):
            memories.append({
                "content": f"Batch test memory {i}",
                "memory_type": "batch_test",
                "memory_tier": "short",
                "importance": 0.5 + (i / 100)
            })
        
        # Test batch add
        batch_add_request = {
            "action": "batch_add_memories",
            "data": {
                "memories": memories
            }
        }
        
        start_time = time.time()
        client_socket.send_json(batch_add_request)
        batch_add_response = client_socket.recv_json()
        end_time = time.time()
        
        assert batch_add_response["status"] == "success", "Batch add failed"
        batch_add_time = (end_time - start_time) * 1000  # ms
        
        # Compare with individual adds
        individual_add_times = []
        for i in range(5):  # Just do a few to get an average
            request = {
                "action": "add_memory",
                "data": {
                    "content": f"Individual test memory {i}",
                    "memory_type": "batch_test"
                }
            }
            
            start_time = time.time()
            client_socket.send_json(request)
            client_socket.recv_json()
            end_time = time.time()
            
            individual_add_times.append((end_time - start_time) * 1000)  # ms
        
        avg_individual_time = statistics.mean(individual_add_times)
        total_individual_time = avg_individual_time * num_memories
        
        logger.info(f"Batch Add Performance: {batch_add_time:.2f}ms for {num_memories} memories")
        logger.info(f"Individual Add Performance: {avg_individual_time:.2f}ms per memory, {total_individual_time:.2f}ms total")
        
        # Batch should be significantly faster than individual operations
        assert batch_add_time < total_individual_time * 0.8, "Batch operations not performing efficiently"

def run_tests():
    """Run all tests"""
    # Run unit tests
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
    
    # Run integration and performance tests with pytest
    pytest.main(["-xvs", __file__, "-m", "integration or performance"])

if __name__ == "__main__":
    run_tests() 