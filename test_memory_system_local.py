#!/usr/bin/env python3
"""
Simplified Memory System Test

This script provides a simplified test for the memory system
using a local MemoryOrchestratorService on port 7140.
"""

import os
import sys
import time
import logging
import unittest
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MemorySystemTest")

# Set environment variables for testing
os.environ["MEMORY_ORCHESTRATOR_ADDR"] = "tcp://localhost:7140"
os.environ["PC2_IP"] = "localhost"

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import memory components
try:
    from main_pc_code.agents.memory_client import MemoryClient
except ImportError:
    logger.error("Could not import MemoryClient. Tests cannot run.")
    sys.exit(1)

class TestMemorySystem(unittest.TestCase):
    """Basic tests for the memory system"""
    
    def setUp(self):
        """Set up the test environment"""
        self.client = MemoryClient(agent_name="TestClient", port=5799)
        self.client.set_agent_id("memory_test")
        
    def tearDown(self):
        """Clean up the test environment"""
        if hasattr(self, 'client'):
            self.client.cleanup()
    
    def test_connection(self):
        """Test connection to MemoryOrchestratorService"""
        status = self.client.get_circuit_breaker_status()
        self.assertEqual(status["status"], "success")
        logger.info("Connection test passed")
    
    def test_add_and_retrieve_memory(self):
        """Test adding and retrieving a memory"""
        # Add memory
        test_content = "Test memory content"
        add_result = self.client.add_memory(
            content=test_content,
            memory_type="test",
            memory_tier="short",
            importance=0.8,
            metadata={"test_id": "basic_test"},
            tags=["test", "basic"]
        )
        
        self.assertEqual(add_result["status"], "success")
        self.assertTrue("memory_id" in add_result)
        memory_id = add_result["memory_id"]
        logger.info(f"Added memory with ID: {memory_id}")
        
        # Retrieve memory
        get_result = self.client.get_memory(memory_id)
        self.assertEqual(get_result["status"], "success")
        self.assertEqual(get_result["memory"]["content"], test_content)
        logger.info("Memory retrieval test passed")
        
        # Clean up
        delete_result = self.client.delete_memory(memory_id)
        self.assertEqual(delete_result["status"], "success")
        logger.info("Memory deletion test passed")
    
    def test_search_memory(self):
        """Test searching for memories"""
        # Add test memories
        memory_ids = []
        test_contents = [
            "Apple is a fruit",
            "Banana is yellow",
            "Orange is orange"
        ]
        
        for content in test_contents:
            result = self.client.add_memory(
                content=content,
                memory_type="search_test",
                tags=["test", "search"]
            )
            self.assertEqual(result["status"], "success")
            memory_ids.append(result["memory_id"])
        
        # Search for memories
        search_result = self.client.search_memory("fruit")
        self.assertEqual(search_result["status"], "success")
        self.assertGreaterEqual(search_result["count"], 1)
        logger.info(f"Search found {search_result['count']} results")
        
        # Clean up
        for memory_id in memory_ids:
            self.client.delete_memory(memory_id)
        logger.info("Search test passed")

if __name__ == "__main__":
    unittest.main() 