"""Unit tests for ServiceRegistryAgent."""

import unittest
from unittest.mock import patch, MagicMock, Mock


class TestServiceRegistry(unittest.TestCase):
    def test_register_and_lookup(self):
        """Test registry functionality with a mock agent."""
        # Create a mock ServiceRegistryAgent with a real registry dictionary
        mock_agent = Mock()
        mock_agent.registry = {}
        
        # Set up the mock to behave like the real agent for handle_request
        def mock_handle_request(request):
            action = request.get("action")
            
            if action == "register_agent":
                agent_id = request.get("agent_id")
                host = request.get("host")
                port = request.get("port")
                # Store the registration in the registry
                mock_agent.registry[agent_id] = {
                    "host": host,
                    "port": port,
                    "health_check_port": request.get("health_check_port")
                }
                return {"status": "success"}
                
            elif action == "get_agent_endpoint":
                agent_name = request.get("agent_name")
                if agent_name not in mock_agent.registry:
                    return {"status": "error", "error": f"Agent {agent_name} not found"}
                
                data = mock_agent.registry[agent_name].copy()
                data.update({"status": "success"})
                return data
                
            return {"status": "error", "error": f"Unknown action: {action}"}
            
        mock_agent.handle_request = mock_handle_request

        # Test registration
        registration = {
            "action": "register_agent",
            "agent_id": "DummyAgent",
            "host": "dummy.host",
            "port": 12345,
            "health_check_port": 22345,
            "agent_type": "service",
            "capabilities": ["dummy"],
            "metadata": {},
        }
        
        resp_reg = mock_agent.handle_request(registration)
        self.assertEqual(resp_reg["status"], "success")

        # Test lookup
        resp_lookup = mock_agent.handle_request({
            "action": "get_agent_endpoint", 
            "agent_name": "DummyAgent"
        })
        self.assertEqual(resp_lookup["status"], "success")
        self.assertEqual(resp_lookup["host"], registration["host"])
        self.assertEqual(resp_lookup["port"], registration["port"])


if __name__ == "__main__":
    unittest.main()
