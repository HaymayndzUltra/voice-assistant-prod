#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
# -*- coding: utf-8 -*-
"""
Test module for memory integration.
"""

import unittest
import json
import zmq
import logging
import sys
import os
from unittest.mock import MagicMock, patch

# Ensure the parent directory is in the path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from common.utils.path_env import get_project_root, get_main_pc_code

# Import the services to test
from pc2_code.agents.memory_orchestrator_service import MemoryOrchestratorService
from common.env_helpers import get_env

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

class MemoryClient:
    """Simple client to interact with MemoryOrchestratorService for testing"""
    def __init__(self, port=7140):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://localhost:{port}")
        
    def add_memory(self, content, metadata=None, importance_score=0.5):
        """Add a new memory"""
        request = {
            "action": "add_memory",
            "payload": {
                "content": content,
                "metadata": metadata or {},
                "importance_score": importance_score
            }
        }
        self.socket.send_json(request)
        return json.loads(self.socket.recv().decode('utf-8'))
    
    def get_memory(self, memory_id):
        """Get a memory by ID"""
        request = {
            "action": "get_memory",
            "memory_id": memory_id
        }
        self.socket.send_json(request)
        return json.loads(self.socket.recv().decode('utf-8'))
    
    def update_memory(self, memory_id, updates):
        """Update a memory"""
        request = {
            "action": "update_memory",
            "memory_id": memory_id,
            "payload": updates
        }
        self.socket.send_json(request)
        return json.loads(self.socket.recv().decode('utf-8'))
    
    def delete_memory(self, memory_id):
        """Delete a memory"""
        request = {
            "action": "delete_memory",
            "memory_id": memory_id
        }
        self.socket.send_json(request)
        return json.loads(self.socket.recv().decode('utf-8'))
    
    def search_memory(self, query, limit=10):
        """Search memories"""
        request = {
            "action": "search_memory",
            "query": query,
            "limit": limit
        }
        self.socket.send_json(request)
        return json.loads(self.socket.recv().decode('utf-8'))
    
    def close(self):
        """Close the connection"""
        self.socket.close()
        self.context.term()


class TestMemoryIntegration(unittest.TestCase):
    """Integration tests for MemoryOrchestratorService with direct Redis integration"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        # Create a temporary directory for test files
        cls.temp_dir = os.path.join(get_project_root(), "tests", "temp_test_db")
        os.makedirs(cls.temp_dir, exist_ok=True)
        cls.db_path = os.path.join(cls.temp_dir, str(PathManager.get_data_dir() / "test_memory.db"))
        
        # Start MemoryOrchestratorService in a separate thread
        cls.memory_service = MemoryOrchestratorService(
            port=7140, 
            health_port=7141,
            db_path=cls.db_path
        )
        cls.memory_thread = threading.Thread(target=cls.memory_service.run, daemon=True)
        cls.memory_thread.start()
        
        # Wait for service to start
        time.sleep(1)
        
        # Create a client for testing
        cls.client = MemoryClient(port=7140)
        
        # Create direct connection to Redis for verification
        cls.redis_client = redis.Redis(
            host=os.environ.get('REDIS_HOST', 'localhost'),
            port=int(os.environ.get('REDIS_PORT', 6379)),
            password=os.environ.get('REDIS_PASSWORD', None),
            decode_responses=True
        )
        
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        # Close client
        cls.client.close()
        
        # Stop services
        if hasattr(cls, 'memory_service'):
            try:
                cls.memory_service.stop()
            except:
                pass
            
        # Wait for threads to terminate
        if hasattr(cls, 'memory_thread'):
            cls.memory_thread.join(timeout=2.0)
            
        # Clean up Redis
        if hasattr(cls, 'redis_client'):
            cls.redis_client.flushdb()
            cls.redis_client.close()
            
        # Remove temporary directory
        if hasattr(cls, 'temp_dir') and os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)
    
    def setUp(self):
        """Set up before each test"""
        # Clear database and cache
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memory_entries")
        conn.commit()
        conn.close()
        
        # Clear Redis cache
        self.redis_client.flushdb()
    
    def test_add_memory_persists_to_db(self):
        """Test that adding a memory persists it to the database"""
        # Add a memory
        content = "This is a test memory"
        response = self.client.add_memory(content, importance_score=0.8)
        
        # Check response
        self.assertEqual(response["status"], "success")
        self.assertIn("memory_id", response)
        memory_id = response["memory_id"]
        
        # Verify in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT content, importance_score FROM memory_entries WHERE memory_id = ?", (memory_id,))
        result = cursor.fetchone()
        conn.close()
        
        # Assert memory was stored correctly
        self.assertIsNotNone(result)
        self.assertEqual(result[0], content)
        self.assertEqual(result[1], 0.8)
    
    def test_get_memory_cache_miss_and_hit(self):
        """Test cache miss and hit when getting a memory"""
        # Add a memory
        content = "Cache test memory"
        add_response = self.client.add_memory(content)
        memory_id = add_response["memory_id"]
        
        # First get (cache miss)
        start_time = time.time()
        get_response1 = self.client.get_memory(memory_id)
        miss_time = time.time() - start_time
        
        # Check if memory is now in Redis cache
        cache_key = f"memory:{memory_id}"
        cached_data = self.redis_client.get(cache_key)
        self.assertIsNotNone(cached_data, "Memory should be in Redis cache after first get")
        
        # Second get (cache hit)
        start_time = time.time()
        get_response2 = self.client.get_memory(memory_id)
        hit_time = time.time() - start_time
        
        # Both responses should be the same
        self.assertEqual(get_response1["memory"]["content"], content)
        self.assertEqual(get_response2["memory"]["content"], content)
        
        # Cache hit should be faster than cache miss (this is not always true in testing
        # environments but is a good sanity check)
        print(f"Cache miss time: {miss_time:.6f}s, Cache hit time: {hit_time:.6f}s")
    
    def test_update_memory_invalidates_cache(self):
        """Test that updating a memory invalidates its cache entry"""
        # Add a memory
        original_content = "Original content"
        add_response = self.client.add_memory(original_content)
        memory_id = add_response["memory_id"]
        
        # Get memory to cache it
        self.client.get_memory(memory_id)
        
        # Verify it's in cache
        cache_key = f"memory:{memory_id}"
        self.assertIsNotNone(self.redis_client.get(cache_key), "Memory should be in cache")
        
        # Update memory
        updated_content = "Updated content"
        update_response = self.client.update_memory(memory_id, {"content": updated_content})
        self.assertEqual(update_response["status"], "success")
        
        # Verify cache was invalidated
        self.assertIsNone(self.redis_client.get(cache_key), "Cache should be invalidated after update")
        
        # Get memory again to verify update
        get_response = self.client.get_memory(memory_id)
        self.assertEqual(get_response["memory"]["content"], updated_content)
    
    def test_delete_memory_invalidates_cache(self):
        """Test that deleting a memory removes it from both DB and cache"""
        # Add a memory
        content = "Memory to delete"
        add_response = self.client.add_memory(content)
        memory_id = add_response["memory_id"]
        
        # Get memory to cache it
        self.client.get_memory(memory_id)
        
        # Verify it's in cache
        cache_key = f"memory:{memory_id}"
        self.assertIsNotNone(self.redis_client.get(cache_key), "Memory should be in cache")
        
        # Delete memory
        delete_response = self.client.delete_memory(memory_id)
        self.assertEqual(delete_response["status"], "success")
        
        # Verify cache was invalidated
        self.assertIsNone(self.redis_client.get(cache_key), "Cache should be invalidated after delete")
        
        # Verify it's gone from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memory_entries WHERE memory_id = ?", (memory_id,))
        count = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(count, 0, "Memory should be deleted from database")
        
        # Get memory should return error
        get_response = self.client.get_memory(memory_id)
        self.assertEqual(get_response["status"], "error")


if __name__ == "__main__":
    unittest.main() 