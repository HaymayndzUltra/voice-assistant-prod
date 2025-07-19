#!/usr/bin/env python3
"""
Memory System End-to-End Integration Test

This script tests the complete memory system integration between MainPC and PC2,
verifying that all components work together correctly.
"""

import os
import sys
import time
import json
import logging
import random
import string
import threading
import zmq
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MemoryIntegrationTest")

# Import memory components (adjust paths as needed)
try:
    from main_pc_code.agents.memory_client import MemoryClient
except ImportError:
    logger.error("Could not import MemoryClient. Tests cannot run.")
    sys.exit(1)

class MemoryIntegrationTest:
    """
    End-to-end integration tests for the memory system.
    Tests communication between MainPC (MemoryClient) and PC2 (MemoryOrchestratorService).
    """
    
    def __init__(self):
        """Initialize the test harness"""
        self.client = None
        self.test_results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "failures": []
        }
    
    def setup(self):
        """Set up test environment"""
        try:
            logger.info("Initializing MemoryClient for testing...")
            self.client = MemoryClient(agent_name="IntegrationTestClient", port=5797)
            self.client.set_agent_id("memory_integration_test")
            
            # Check connection to MemoryOrchestratorService
            status = self.client.get_circuit_breaker_status()
            if status["status"] != "success":
                logger.error("Failed to connect to MemoryOrchestratorService")
                return False
                
            logger.info("Successfully connected to MemoryOrchestratorService")
            return True
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up test environment"""
        if self.client:
            self.client.cleanup()
            logger.info("Cleaned up MemoryClient")
    
    def assert_true(self, condition, message):
        """Assert that a condition is true"""
        self.test_results["total"] += 1
        if condition:
            self.test_results["passed"] += 1
            logger.info(f"✅ PASS: {message}")
            return True
        else:
            self.test_results["failed"] += 1
            self.test_results["failures"].append(message)
            logger.error(f"❌ FAIL: {message}")
            return False
    
    def run_tests(self):
        """Run all integration tests"""
        if not self.setup():
            logger.error("Test setup failed. Cannot continue.")
            return False
        
        try:
            logger.info("Starting memory integration tests...")
            
            # Run the test cases
            self.test_basic_memory_operations()
            self.test_hierarchical_memory()
            self.test_memory_relationships()
            self.test_memory_search()
            self.test_memory_reinforcement()
            self.test_batch_operations()
            self.test_error_handling()
            
            # Print test summary
            logger.info(f"Test Summary: {self.test_results['passed']}/{self.test_results['total']} tests passed")
            if self.test_results["failed"] > 0:
                logger.error(f"Failed tests: {len(self.test_results['failures'])}")
                for i, failure in enumerate(self.test_results["failures"]):
                    logger.error(f"  {i+1}. {failure}")
                return False
            return True
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            return False
        finally:
            self.cleanup()
    
    def test_basic_memory_operations(self):
        """Test basic memory CRUD operations"""
        logger.info("Testing basic memory operations...")
        
        # Generate unique test content
        test_content = f"Basic memory test {random.randint(1000, 9999)}"
        
        # Test adding memory
        add_result = self.client.add_memory(
            content=test_content,
            memory_type="integration_test",
            memory_tier="short",
            importance=0.8,
            metadata={"test_type": "basic_operations"},
            tags=["test", "integration", "basic"]
        )
        
        if not self.assert_true(
            add_result["status"] == "success", 
            "Add memory operation should succeed"
        ):
            return
        
        memory_id = add_result["memory_id"]
        logger.info(f"Created test memory with ID: {memory_id}")
        
        # Test retrieving memory
        get_result = self.client.get_memory(memory_id)
        
        if not self.assert_true(
            get_result["status"] == "success", 
            "Get memory operation should succeed"
        ):
            return
            
        self.assert_true(
            get_result["memory"]["content"] == test_content,
            "Retrieved memory content should match original content"
        )
        
        # Test updating memory
        updated_content = f"{test_content} - UPDATED"
        update_result = self.client.update_memory(
            memory_id=memory_id,
            update_payload={"content": updated_content}
        )
        
        self.assert_true(
            update_result["status"] == "success",
            "Update memory operation should succeed"
        )
        
        # Verify update
        get_updated_result = self.client.get_memory(memory_id)
        self.assert_true(
            get_updated_result["memory"]["content"] == updated_content,
            "Updated memory content should match new content"
        )
        
        # Test deleting memory
        delete_result = self.client.delete_memory(memory_id)
        self.assert_true(
            delete_result["status"] == "success",
            "Delete memory operation should succeed"
        )
        
        # Verify deletion
        get_deleted_result = self.client.get_memory(memory_id)
        self.assert_true(
            get_deleted_result["status"] == "error",
            "Getting deleted memory should return error"
        )
    
    def test_hierarchical_memory(self):
        """Test hierarchical memory operations"""
        logger.info("Testing hierarchical memory operations...")
        
        # Create parent memory
        parent_result = self.client.add_memory(
            content="Parent memory for hierarchy test",
            memory_type="integration_test",
            tags=["test", "hierarchy", "parent"]
        )
        
        if not self.assert_true(
            parent_result["status"] == "success", 
            "Add parent memory operation should succeed"
        ):
            return
            
        parent_id = parent_result["memory_id"]
        
        # Create child memories
        child_ids = []
        for i in range(3):
            child_result = self.client.add_memory(
                content=f"Child memory {i} for hierarchy test",
                memory_type="integration_test",
                parent_id=parent_id,
                tags=["test", "hierarchy", "child"]
            )
            
            if not self.assert_true(
                child_result["status"] == "success", 
                f"Add child memory {i} operation should succeed"
            ):
                return
                
            child_ids.append(child_result["memory_id"])
        
        # Test retrieving children
        children_result = self.client.get_children(parent_id)
        
        self.assert_true(
            children_result["status"] == "success",
            "Get children operation should succeed"
        )
        
        self.assert_true(
            len(children_result["children"]) == 3,
            f"Parent should have 3 children, found {len(children_result['children'])}"
        )
        
        # Clean up
        for child_id in child_ids:
            self.client.delete_memory(child_id)
        self.client.delete_memory(parent_id)
    
    def test_memory_relationships(self):
        """Test memory relationship operations"""
        logger.info("Testing memory relationship operations...")
        
        # Create two related memories
        memory1_result = self.client.add_memory(
            content="First memory for relationship test",
            memory_type="integration_test",
            tags=["test", "relationship"]
        )
        
        memory2_result = self.client.add_memory(
            content="Second memory for relationship test",
            memory_type="integration_test",
            tags=["test", "relationship"]
        )
        
        if not self.assert_true(
            memory1_result["status"] == "success" and memory2_result["status"] == "success", 
            "Add memory operations should succeed"
        ):
            return
            
        memory1_id = memory1_result["memory_id"]
        memory2_id = memory2_result["memory_id"]
        
        # Create relationship
        rel_result = self.client.add_relationship(
            source_id=memory1_id,
            target_id=memory2_id,
            relationship_type="related_to",
            strength=0.8
        )
        
        self.assert_true(
            rel_result["status"] == "success",
            "Add relationship operation should succeed"
        )
        
        # Test retrieving relationships
        related_result = self.client.get_related_memories(memory1_id)
        
        self.assert_true(
            related_result["status"] == "success",
            "Get related memories operation should succeed"
        )
        
        self.assert_true(
            len(related_result["related_memories"]) > 0,
            "Should find related memories"
        )
        
        if len(related_result["related_memories"]) > 0:
            self.assert_true(
                related_result["related_memories"][0]["memory"]["memory_id"] == memory2_id,
                "Related memory should match memory2_id"
            )
        
        # Clean up
        self.client.delete_memory(memory1_id)
        self.client.delete_memory(memory2_id)
    
    def test_memory_search(self):
        """Test memory search operations"""
        logger.info("Testing memory search operations...")
        
        # Create test memories with unique identifier
        unique_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        test_contents = [
            f"SEARCHTEST_{unique_id} Apple is a fruit",
            f"SEARCHTEST_{unique_id} Banana is yellow",
            f"SEARCHTEST_{unique_id} Orange is orange",
            f"SEARCHTEST_{unique_id} Grape is purple"
        ]
        
        memory_ids = []
        for content in test_contents:
            result = self.client.add_memory(
                content=content,
                memory_type="search_test",
                tags=["test", "search"]
            )
            
            if result["status"] == "success":
                memory_ids.append(result["memory_id"])
        
        # Test basic search
        search_result = self.client.search_memory(f"SEARCHTEST_{unique_id}")
        
        self.assert_true(
            search_result["status"] == "success",
            "Search operation should succeed"
        )
        
        self.assert_true(
            search_result["count"] >= 4,
            f"Search should find at least 4 results, found {search_result['count']}"
        )
        
        # Test filtered search
        filtered_search = self.client.search_memory(f"SEARCHTEST_{unique_id} Apple")
        
        self.assert_true(
            filtered_search["status"] == "success",
            "Filtered search operation should succeed"
        )
        
        self.assert_true(
            filtered_search["count"] >= 1,
            f"Filtered search should find at least 1 result, found {filtered_search['count']}"
        )
        
        # Test semantic search if available
        try:
            semantic_result = self.client.semantic_search(f"SEARCHTEST_{unique_id} fruit")
            
            self.assert_true(
                semantic_result["status"] == "success",
                "Semantic search operation should succeed"
            )
        except Exception:
            logger.warning("Semantic search not fully implemented, skipping test")
        
        # Clean up
        for memory_id in memory_ids:
            self.client.delete_memory(memory_id)
    
    def test_memory_reinforcement(self):
        """Test memory reinforcement operations"""
        logger.info("Testing memory reinforcement operations...")
        
        # Create test memory
        memory_result = self.client.add_memory(
            content="Memory for reinforcement test",
            memory_type="integration_test",
            importance=0.5,
            tags=["test", "reinforcement"]
        )
        
        if not self.assert_true(
            memory_result["status"] == "success", 
            "Add memory operation should succeed"
        ):
            return
            
        memory_id = memory_result["memory_id"]
        
        # Get initial importance
        get_result = self.client.get_memory(memory_id)
        initial_importance = get_result["memory"]["importance"]
        
        # Reinforce memory
        reinforce_result = self.client.reinforce_memory(
            memory_id=memory_id,
            reinforcement_factor=1.2
        )
        
        self.assert_true(
            reinforce_result["status"] == "success",
            "Reinforce memory operation should succeed"
        )
        
        # Verify reinforcement
        get_reinforced_result = self.client.get_memory(memory_id)
        reinforced_importance = get_reinforced_result["memory"]["importance"]
        
        self.assert_true(
            reinforced_importance > initial_importance,
            f"Reinforced importance ({reinforced_importance}) should be greater than initial importance ({initial_importance})"
        )
        
        # Clean up
        self.client.delete_memory(memory_id)
    
    def test_batch_operations(self):
        """Test batch memory operations"""
        logger.info("Testing batch memory operations...")
        
        # Create batch of memories
        batch_memories = []
        for i in range(5):
            batch_memories.append({
                "content": f"Batch test memory {i}",
                "memory_type": "batch_test",
                "memory_tier": "short",
                "importance": 0.5,
                "tags": ["test", "batch"]
            })
        
        # Test batch add
        batch_add_result = self.client.batch_add_memories(batch_memories)
        
        self.assert_true(
            batch_add_result["status"] == "success",
            "Batch add operation should succeed"
        )
        
        self.assert_true(
            len(batch_add_result["memory_ids"]) == 5,
            f"Batch add should return 5 memory IDs, got {len(batch_add_result['memory_ids'])}"
        )
        
        memory_ids = batch_add_result["memory_ids"]
        
        # Test batch get
        batch_get_result = self.client.batch_get_memories(memory_ids)
        
        self.assert_true(
            batch_get_result["status"] == "success",
            "Batch get operation should succeed"
        )
        
        self.assert_true(
            len(batch_get_result["memories"]) == 5,
            f"Batch get should return 5 memories, got {len(batch_get_result['memories'])}"
        )
        
        # Clean up
        for memory_id in memory_ids:
            self.client.delete_memory(memory_id)
    
    def test_error_handling(self):
        """Test error handling in the memory system"""
        logger.info("Testing error handling...")
        
        # Test getting non-existent memory
        get_result = self.client.get_memory("non-existent-memory-id")
        
        self.assert_true(
            get_result["status"] == "error",
            "Getting non-existent memory should return error status"
        )
        
        # Test invalid relationship
        rel_result = self.client.add_relationship(
            source_id="non-existent-source",
            target_id="non-existent-target",
            relationship_type="test"
        )
        
        self.assert_true(
            rel_result["status"] == "error",
            "Adding relationship with non-existent memories should return error status"
        )
        
        # Test circuit breaker status
        cb_status = self.client.get_circuit_breaker_status()
        
        self.assert_true(
            cb_status["status"] == "success",
            "Circuit breaker status should be accessible"
        )
        
        self.assert_true(
            "state" in cb_status,
            "Circuit breaker status should include state information"
        )

def main():
    """Run the integration tests"""
    test = MemoryIntegrationTest()
    success = test.run_tests()
    
    if success:
        logger.info("✅ All integration tests passed!")
        return 0
    else:
        logger.error("❌ Integration tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 