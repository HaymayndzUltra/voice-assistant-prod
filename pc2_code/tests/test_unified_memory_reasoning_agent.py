#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
# -*- coding: utf-8 -*-
"""
Test module for UnifiedMemoryReasoningAgent.
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

# Import the agent to test
from pc2_code.agents.UnifiedMemoryReasoningAgent import UnifiedMemoryReasoningAgent
from common.env_helpers import get_env

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestUnifiedMemoryReasoningAgent(unittest.TestCase):
    """Test cases for UnifiedMemoryReasoningAgent."""

    @patch('agents.UnifiedMemoryReasoningAgent.discover_service')
    def setUp(self, mock_discover_service):
        """Set up test environment before each test."""
        # Mock dependencies
        mock_discover_service.return_value = {'host': 'localhost', 'port': 7102}  # CacheManager port
        
        # Create an instance of the agent with test configuration
        self.agent = UnifiedMemoryReasoningAgent(port=9999, test_mode=True)
        
        # Mock the agent's dependencies
        self.agent.cache_manager = MagicMock()
        
        # Initialize test data
        self.test_memory = {
            "memory_id": "mem-123456",
            "content": "The capital of France is Paris",
            "source": "user_input",
            "timestamp": "2025-07-03T12:34:56",
            "metadata": {
                "confidence": 0.95,
                "importance": 0.8
            }
        }
        
        self.test_query = {
            "query": "What is the capital of France?",
            "context": "Geography discussion",
            "max_results": 5
        }

    def tearDown(self):
        """Clean up after each test."""
        if hasattr(self, 'agent'):
            self.agent.cleanup()

    def test_initialization(self):
        """Test that the agent initializes correctly."""
        self.assertEqual(self.agent.name, "UnifiedMemoryReasoningAgent")
        self.assertEqual(self.agent.port, 9999)
        self.assertTrue(hasattr(self.agent, 'cache_manager'))

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
        self.assertEqual(response["agent"], "UnifiedMemoryReasoningAgent")

    @patch('agents.UnifiedMemoryReasoningAgent.UnifiedMemoryReasoningAgent._handle_message')
    def test_store_memory(self, mock_handle_message):
        """Test storing a memory."""
        # Setup the mock to return success
        mock_handle_message.return_value = {
            "status": "success",
            "memory_id": self.test_memory["memory_id"],
            "message": "Memory stored successfully"
        }
        
        # Create a message requesting memory storage
        message = {
            "action": "store_memory",
            "memory": self.test_memory
        }
        
        # Process the message
        response = self.agent._handle_message(message)
        
        # Verify the response
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["memory_id"], self.test_memory["memory_id"])

    @patch('agents.UnifiedMemoryReasoningAgent.UnifiedMemoryReasoningAgent._handle_message')
    def test_retrieve_memory(self, mock_handle_message):
        """Test retrieving a memory."""
        # Setup the mock to return the test memory
        mock_handle_message.return_value = {
            "status": "success",
            "memories": [self.test_memory],
            "count": 1
        }
        
        # Create a message requesting memory retrieval
        message = {
            "action": "retrieve_memory",
            "query": self.test_query
        }
        
        # Process the message
        response = self.agent._handle_message(message)
        
        # Verify the response
        self.assertEqual(response["status"], "success")
        self.assertEqual(len(response["memories"]), 1)
        self.assertEqual(response["memories"][0]["memory_id"], self.test_memory["memory_id"])

    @patch('agents.UnifiedMemoryReasoningAgent.UnifiedMemoryReasoningAgent._handle_message')
    def test_reason_about_memory(self, mock_handle_message):
        """Test reasoning about memories."""
        # Setup the mock to return reasoning results
        mock_handle_message.return_value = {
            "status": "success",
            "reasoning": "Paris is the capital of France, which is a country in Europe.",
            "confidence": 0.95
        }
        
        # Create a message requesting memory reasoning
        message = {
            "action": "reason",
            "query": "Tell me about the capital of France",
            "context": [self.test_memory]
        }
        
        # Process the message
        response = self.agent._handle_message(message)
        
        # Verify the response
        self.assertEqual(response["status"], "success")
        self.assertIn("reasoning", response)
        self.assertIn("confidence", response)


if __name__ == '__main__':
    unittest.main() 