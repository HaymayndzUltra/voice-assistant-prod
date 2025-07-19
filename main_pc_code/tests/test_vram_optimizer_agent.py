#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test module for VRAMOptimizerAgent.
"""

import unittest
import json
import zmq
import logging
import sys
import os
from unittest.mock import MagicMock, patch

# Ensure the parent directory is in the path for imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from common.utils.path_env import get_project_root, get_main_pc_code

# Import the agent to test
from main_pc_code.agents.vram_optimizer_agent import VRAMOptimizerAgent
from common.env_helpers import get_env

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestVRAMOptimizerAgent(unittest.TestCase):
    """Test cases for VRAMOptimizerAgent."""

    @patch('agents.vram_optimizer_agent.discover_service')
    def setUp(self, mock_discover_service):
        """Set up test environment before each test."""
        # Mock dependencies
        mock_discover_service.side_effect = lambda service_name: {
            'ModelManagerAgent': {'host': 'localhost', 'port': 5570},
            'SystemDigitalTwin': {'host': 'localhost', 'port': 7120}
        }.get(service_name, None)
        
        # Create an instance of the agent with test configuration
        self.agent = VRAMOptimizerAgent(port=9999)
        
        # Mock GPU utilities
        self.agent.get_gpu_memory_info = MagicMock(return_value={
            'total': 16384,  # 16GB in MB
            'used': 4096,    # 4GB in MB
            'free': 12288    # 12GB in MB
        })
        
        # Initialize test data
        self.test_model_info = {
            "model_id": "test-model-123",
            "name": "test-gpt-model",
            "size_mb": 2048,
            "last_used": "2025-07-03T12:34:56",
            "priority": "high"
        }

    def tearDown(self):
        """Clean up after each test."""
        if hasattr(self, 'agent'):
            if hasattr(self.agent, 'cleanup'):
                self.agent.cleanup()

    def test_initialization(self):
        """Test that the agent initializes correctly."""
        self.assertEqual(self.agent.name, "VRAMOptimizerAgent")
        self.assertEqual(self.agent.port, 9999)
        self.assertTrue(hasattr(self.agent, 'model_manager_host'))
        self.assertTrue(hasattr(self.agent, 'model_manager_port'))

    @patch('zmq.Context.socket')
    def test_health_check(self, mock_socket):
        """Test the health check functionality."""
        # Mock the socket's recv_json and send_json methods
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance
        mock_socket_instance.recv_json.return_value = {"action": "health_check"}
        
        # Call the health check method
        response = self.agent.handle_health_check()
        
        # Verify the response
        self.assertEqual(response["status"], "healthy")
        self.assertEqual(response["agent"], "VRAMOptimizerAgent")
        self.assertIn("vram_stats", response)

    @patch('agents.vram_optimizer_agent.VRAMOptimizerAgent.send_to_model_manager')
    def test_unload_model(self, mock_send):
        """Test unloading a model."""
        # Setup the mock
        mock_send.return_value = {"status": "success", "message": "Model unloaded"}
        
        # Call the unload method
        result = self.agent.unload_model(self.test_model_info["model_id"])
        
        # Verify the result
        self.assertEqual(result["status"], "success")
        mock_send.assert_called_once()
        
        # Check the message sent to model manager
        args, _ = mock_send.call_args
        self.assertEqual(args[0]["action"], "unload_model")
        self.assertEqual(args[0]["model_id"], self.test_model_info["model_id"])

    @patch('agents.vram_optimizer_agent.VRAMOptimizerAgent.get_loaded_models')
    def test_optimize_memory(self, mock_get_models):
        """Test memory optimization."""
        # Setup mock to return test models
        mock_get_models.return_value = {
            "models": [
                self.test_model_info,
                {
                    "model_id": "test-model-456",
                    "name": "test-bert-model",
                    "size_mb": 1024,
                    "last_used": "2025-07-03T10:00:00",
                    "priority": "medium"
                }
            ]
        }
        
        # Mock the unload_model method
        self.agent.unload_model = MagicMock(return_value={"status": "success"})
        
        # Call the optimize method
        result = self.agent.optimize_memory(threshold_mb=3000)
        
        # Verify the result
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["models_unloaded"], 1)
        
        # Verify that the least recently used model was unloaded
        self.agent.unload_model.assert_called_once()

    @patch('agents.vram_optimizer_agent.VRAMOptimizerAgent.send_to_system_digital_twin')
    def test_report_vram_status(self, mock_send):
        """Test reporting VRAM status to SystemDigitalTwin."""
        # Setup the mock
        mock_send.return_value = {"status": "success"}
        
        # Call the report method
        result = self.agent.report_vram_status()
        
        # Verify the result
        self.assertEqual(result["status"], "success")
        mock_send.assert_called_once()
        
        # Check the message sent to SystemDigitalTwin
        args, _ = mock_send.call_args
        self.assertEqual(args[0]["action"], "update_vram_stats")
        self.assertIn("vram_stats", args[0])


if __name__ == '__main__':
    unittest.main() 