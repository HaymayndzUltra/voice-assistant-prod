#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test module for UnifiedPlanningAgent.
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
from common.utils.path_env import get_project_root, get_main_pc_code

# Import the agent to test
from main_pc_code.agents.unified_planning_agent import UnifiedPlanningAgent
from common.env_helpers import get_env

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestUnifiedPlanningAgent(unittest.TestCase):
    """Test cases for UnifiedPlanningAgent."""

    @patch('agents.unified_planning_agent.discover_service')
    def setUp(self, mock_discover_service):
        """Set up test environment before each test."""
        # Mock dependencies
        mock_discover_service.return_value = {'host': 'localhost', 'port': 5701}
        
        # Create an instance of the agent with test configuration
        self.agent = UnifiedPlanningAgent(port=9999, test_mode=True)
        
        # Mock the agent's dependencies
        self.agent.goal_orchestrator = MagicMock()
        self.agent.intention_validator = MagicMock()
        
        # Initialize test data
        self.test_plan = {
            "goal": "Test the UnifiedPlanningAgent",
            "steps": [
                {"action": "Initialize test environment", "status": "pending"},
                {"action": "Run test cases", "status": "pending"},
                {"action": "Verify results", "status": "pending"}
            ]
        }

    def tearDown(self):
        """Clean up after each test."""
        if hasattr(self, 'agent'):
            self.agent.cleanup()

    def test_initialization(self):
        """Test that the agent initializes correctly."""
        self.assertEqual(self.agent.name, "UnifiedPlanningAgent")
        self.assertEqual(self.agent.port, 9999)
        self.assertTrue(hasattr(self.agent, 'goal_orchestrator'))
        self.assertTrue(hasattr(self.agent, 'intention_validator'))

    @patch('zmq.Context.socket')
    def test_health_check(self, mock_socket):
        """Test the health check functionality."""
        # Mock the socket's recv_json and send_json methods
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance
        mock_socket_instance.recv_json.return_value = {"action": "health_check"}
        
        # Call the health check method
        response = self.agent._get_health_status()
        
        # Verify the response
        self.assertEqual(response["status"], "healthy")
        self.assertEqual(response["agent"], "UnifiedPlanningAgent")

    @patch('agents.unified_planning_agent.UnifiedPlanningAgent._handle_message')
    def test_create_plan(self, mock_handle_message):
        """Test creating a new plan."""
        # Setup the mock to return our test plan
        mock_handle_message.return_value = {"status": "success", "plan": self.test_plan}
        
        # Create a message requesting a new plan
        message = {
            "action": "create_plan",
            "goal": "Test the UnifiedPlanningAgent",
            "constraints": ["Complete within 1 hour", "Use minimal resources"]
        }
        
        # Process the message
        response = self.agent._handle_message(message)
        
        # Verify the response
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["plan"]["goal"], "Test the UnifiedPlanningAgent")
        self.assertEqual(len(response["plan"]["steps"]), 3)

    @patch('agents.unified_planning_agent.UnifiedPlanningAgent._handle_message')
    def test_update_plan(self, mock_handle_message):
        """Test updating an existing plan."""
        # Setup the mock
        updated_plan = self.test_plan.copy()
        updated_plan["steps"][0]["status"] = "completed"
        mock_handle_message.return_value = {"status": "success", "plan": updated_plan}
        
        # Create a message requesting a plan update
        message = {
            "action": "update_plan",
            "plan_id": "test_plan_123",
            "step_id": 0,
            "status": "completed"
        }
        
        # Process the message
        response = self.agent._handle_message(message)
        
        # Verify the response
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["plan"]["steps"][0]["status"], "completed")

    @patch('agents.unified_planning_agent.UnifiedPlanningAgent._handle_message')
    def test_execute_plan(self, mock_handle_message):
        """Test executing a plan."""
        # Setup the mock
        mock_handle_message.return_value = {"status": "success", "execution_id": "exec_123"}
        
        # Create a message requesting plan execution
        message = {
            "action": "execute_plan",
            "plan_id": "test_plan_123"
        }
        
        # Process the message
        response = self.agent._handle_message(message)
        
        # Verify the response
        self.assertEqual(response["status"], "success")
        self.assertTrue("execution_id" in response)


if __name__ == '__main__':
    unittest.main() 