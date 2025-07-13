"""Integration tests for ServiceRegistryAgent with Redis backend.

This test requires a running Redis instance. It will be skipped if Redis is not available.
"""

import unittest
import os
from unittest.mock import patch, MagicMock

# Try to import redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Import the ServiceRegistryAgent
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main_pc_code.agents.service_registry_agent import ServiceRegistryAgent, RedisBackend


@unittest.skipIf(not REDIS_AVAILABLE, "Redis package not installed")
class TestServiceRegistryRedis(unittest.TestCase):
    """Test ServiceRegistryAgent with Redis backend."""
    
    def setUp(self):
        """Set up test environment."""
        # Use a test-specific Redis database
        self.redis_url = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/15")
        self.test_prefix = "test_registry:"
        
        # Check if Redis is available
        try:
            r = redis.from_url(self.redis_url)
            r.ping()
            self.redis_available = True
        except (redis.exceptions.ConnectionError, redis.exceptions.ResponseError):
            self.redis_available = False
            self.skipTest("Redis server not available")
            return
            
        # Clear any existing test data
        keys = r.keys(f"{self.test_prefix}*")
        if keys:
            r.delete(*keys)
            
        # Create agent with Redis backend
        self.agent = ServiceRegistryAgent(
            backend="redis",
            redis_url=self.redis_url,
            port=7100,
            health_check_port=8100
        )
        
        # Replace the backend with one using our test prefix
        self.agent.backend = RedisBackend(self.redis_url, self.test_prefix)
    
    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self, 'redis_available') and self.redis_available:
            # Clean up Redis data
            r = redis.from_url(self.redis_url)
            keys = r.keys(f"{self.test_prefix}*")
            if keys:
                r.delete(*keys)
            
            # Close agent resources
            if hasattr(self, 'agent'):
                self.agent.cleanup()
    
    def test_register_and_retrieve(self):
        """Test registering an agent and retrieving its endpoint."""
        # Register a test agent
        registration = {
            "action": "register_agent",
            "agent_id": "TestAgent",
            "host": "test.host",
            "port": 12345,
            "health_check_port": 12346,
            "agent_type": "test",
            "capabilities": ["test"],
            "metadata": {"test": True}
        }
        
        # Register the agent
        response = self.agent.handle_request(registration)
        self.assertEqual(response["status"], "success")
        
        # Retrieve the agent endpoint
        lookup = {
            "action": "get_agent_endpoint",
            "agent_name": "TestAgent"
        }
        response = self.agent.handle_request(lookup)
        
        # Verify response
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["host"], "test.host")
        self.assertEqual(response["port"], 12345)
        self.assertEqual(response["health_check_port"], 12346)
        self.assertEqual(response["agent_type"], "test")
        
    def test_list_agents(self):
        """Test listing registered agents."""
        # Register multiple test agents
        for i in range(3):
            registration = {
                "action": "register_agent",
                "agent_id": f"TestAgent{i}",
                "host": f"test{i}.host",
                "port": 12345 + i,
                "health_check_port": 12346 + i,
                "agent_type": "test",
                "capabilities": ["test"],
                "metadata": {"test": True}
            }
            self.agent.handle_request(registration)
        
        # List all agents
        response = self.agent.handle_request({"action": "list_agents"})
        
        # Verify response
        self.assertEqual(response["status"], "success")
        self.assertIn("TestAgent0", response["agents"])
        self.assertIn("TestAgent1", response["agents"])
        self.assertIn("TestAgent2", response["agents"])
        self.assertEqual(len(response["agents"]), 3)
    
    def test_persistence(self):
        """Test that data persists across agent restarts."""
        # Register a test agent
        registration = {
            "action": "register_agent",
            "agent_id": "PersistentAgent",
            "host": "persistent.host",
            "port": 54321,
            "health_check_port": 54322,
            "agent_type": "test",
            "capabilities": ["test"],
            "metadata": {"test": True}
        }
        
        # Register the agent
        self.agent.handle_request(registration)
        
        # Close the agent
        self.agent.cleanup()
        
        # Create a new agent instance with the same Redis backend
        new_agent = ServiceRegistryAgent(
            backend="redis",
            redis_url=self.redis_url,
            port=7100,
            health_check_port=8100
        )
        new_agent.backend = RedisBackend(self.redis_url, self.test_prefix)
        
        # Retrieve the agent endpoint from the new instance
        lookup = {
            "action": "get_agent_endpoint",
            "agent_name": "PersistentAgent"
        }
        response = new_agent.handle_request(lookup)
        
        # Verify data persisted
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["host"], "persistent.host")
        self.assertEqual(response["port"], 54321)
        
        # Clean up
        new_agent.cleanup()


if __name__ == "__main__":
    unittest.main() 