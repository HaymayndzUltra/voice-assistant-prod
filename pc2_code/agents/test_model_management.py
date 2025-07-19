"""
Test suite for Model Management Hierarchy components
Tests the Enhanced Model Router, Remote Connector Agent, and TinyLlama Service
"""
import unittest
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import json
import time
import threading
import logging
from pathlib import Path
import sys
import os
import traceback
from typing import Dict, Any, Optional


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("pc2_code", "..")))
from common.utils.path_env import get_path, join_path, get_file_path
# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import components to test
from enhanced_model_router import EnhancedModelRouter
from remote_connector_agent import RemoteConnectorAgent
from tinyllama_service_enhanced import TinyLlamaService
from common.env_helpers import get_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(join_path("logs", "test_model_management.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ModelManagementTests")

class TestModelManagementHierarchy(unittest.TestCase):
    """Test suite for Model Management Hierarchy components"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        logger.info("Setting up test environment")
        
        # Create test directories
        Path("logs").mkdir(exist_ok=True)
        Path("test_data").mkdir(exist_ok=True)
        
        # Initialize components
        cls.router = EnhancedModelRouter()
        cls.connector = RemoteConnectorAgent()
        cls.tinyllama = TinyLlamaService()
        
        # Start components in separate threads
        cls.router_thread = threading.Thread(target=cls.router.run)
        cls.connector_thread = threading.Thread(target=cls.connector.run)
        cls.tinyllama_thread = threading.Thread(target=cls.tinyllama.run)
        
        cls.router_thread.daemon = True
        cls.connector_thread.daemon = True
        cls.tinyllama_thread.daemon = True
        
        cls.router_thread.start()
        cls.connector_thread.start()
        cls.tinyllama_thread.start()
        
        # Wait for components to initialize
        time.sleep(2)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        logger.info("Cleaning up test environment")
        
        # Stop components
        cls.router.running = False
        cls.connector.running = False
        cls.tinyllama.running = False
        
        # Wait for threads to finish
        cls.router_thread.join(timeout=5)
        cls.connector_thread.join(timeout=5)
        cls.tinyllama_thread.join(timeout=5)
    
    def setUp(self):
        """Set up each test"""
        self.context = None  # Using pool
        
        # Create sockets for each component
        self.router_socket = self.context.socket(zmq.REQ)
        self.router_socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5610")
        
        self.connector_socket = self.context.socket(zmq.REQ)
        self.connector_socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5611")
        
        self.tinyllama_socket = self.context.socket(zmq.REQ)
        self.tinyllama_socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5615")
    
    def tearDown(self):
        """Clean up each test"""
        self.router_
        self.connector_
        self.tinyllama_
        self.
    def test_router_health_check(self):
        """Test router health check"""
        logger.info("Testing router health check")
        
        request = {"action": "health_check"}
        self.router_socket.send_json(request)
        response = self.router_socket.recv_json()
        
        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["service"], "enhanced_model_router")
        self.assertIn("timestamp", response)
    
    def test_router_model_selection(self):
        """Test router model selection"""
        logger.info("Testing router model selection")
        
        request = {
            "action": "route_request",
            "task_type": "text_generation",
            "prompt": "Test prompt",
            "max_tokens": 100
        }
        self.router_socket.send_json(request)
        response = self.router_socket.recv_json()
        
        self.assertEqual(response["status"], "success")
        self.assertIn("model_id", response)
        self.assertIn("confidence", response)
    
    def test_connector_api_management(self):
        """Test connector API management"""
        logger.info("Testing connector API management")
        
        # Test connection state
        request = {"action": "get_connection_state"}
        self.connector_socket.send_json(request)
        response = self.connector_socket.recv_json()
        
        self.assertEqual(response["status"], "success")
        self.assertIn("state", response)
        
        # Test API request
        request = {
            "action": "inference",
            "model": "ollama",
            "prompt": "Test prompt",
            "max_tokens": 100
        }
        self.connector_socket.send_json(request)
        response = self.connector_socket.recv_json()
        
        self.assertEqual(response["status"], "success")
        self.assertIn("text", response)
    
    def test_tinyllama_resource_management(self):
        """Test TinyLlama resource management"""
        logger.info("Testing TinyLlama resource management")
        
        # Test resource stats
        request = {"action": "resource_stats"}
        self.tinyllama_socket.send_json(request)
        response = self.tinyllama_socket.recv_json()
        
        self.assertEqual(response["status"], "success")
        self.assertIn("stats", response)
        self.assertIn("cpu_percent", response["stats"])
        self.assertIn("memory_percent", response["stats"])
        
        # Test model loading
        request = {"action": "ensure_loaded"}
        self.tinyllama_socket.send_json(request)
        response = self.tinyllama_socket.recv_json()
        
        self.assertEqual(response["status"], "success")
        
        # Test generation
        request = {
            "action": "generate",
            "prompt": "Test prompt",
            "max_tokens": 100
        }
        self.tinyllama_socket.send_json(request)
        response = self.tinyllama_socket.recv_json()
        
        self.assertEqual(response["status"], "success")
        self.assertIn("text", response)
    
    def test_integration_flow(self):
        """Test integration flow between components"""
        logger.info("Testing integration flow")
        
        # 1. Route request through router
        request = {
            "action": "route_request",
            "task_type": "text_generation",
            "prompt": "Test integration",
            "max_tokens": 100
        }
        self.router_socket.send_json(request)
        router_response = self.router_socket.recv_json()
        
        self.assertEqual(router_response["status"], "success")
        
        # 2. Send request to connector
        request = {
            "action": "inference",
            "model": router_response["model_id"],
            "prompt": "Test integration",
            "max_tokens": 100
        }
        self.connector_socket.send_json(request)
        connector_response = self.connector_socket.recv_json()
        
        self.assertEqual(connector_response["status"], "success")
        
        # 3. Verify TinyLlama state
        request = {"action": "health_check"}
        self.tinyllama_socket.send_json(request)
        tinyllama_response = self.tinyllama_socket.recv_json()
        
        self.assertEqual(tinyllama_response["status"], "ok")
    
    def test_error_handling(self):
        """Test error handling across components"""
        logger.info("Testing error handling")
        
        # Test invalid request
        request = {"action": "invalid_action"}
        self.router_socket.send_json(request)
        response = self.router_socket.recv_json()
        
        self.assertEqual(response["status"], "error")
        
        # Test resource exhaustion
        request = {
            "action": "generate",
            "prompt": "Test prompt" * 1000,  # Very long prompt
            "max_tokens": 1000
        }
        self.tinyllama_socket.send_json(request)
        response = self.tinyllama_socket.recv_json()
        
        self.assertIn(response["status"], ["error", "success"])
        if response["status"] == "error":
            self.assertIn("message", response)
    
    def test_performance_metrics(self):
        """Test performance metrics collection"""
        logger.info("Testing performance metrics")
        
        # Test router metrics
        request = {"action": "get_metrics"}
        self.router_socket.send_json(request)
        response = self.router_socket.recv_json()
        
        self.assertEqual(response["status"], "success")
        self.assertIn("metrics", response)
        
        # Test connector metrics
        request = {"action": "get_metrics"}
        self.connector_socket.send_json(request)
        response = self.connector_socket.recv_json()
        
        self.assertEqual(response["status"], "success")
        self.assertIn("metrics", response)
        
        # Test TinyLlama metrics
        request = {"action": "resource_stats"}
        self.tinyllama_socket.send_json(request)
        response = self.tinyllama_socket.recv_json()
        
        self.assertEqual(response["status"], "success")
        self.assertIn("stats", response)

def run_tests():
    """Run the test suite"""
    try:
        # Create test directories
        Path("logs").mkdir(exist_ok=True)
        Path("test_data").mkdir(exist_ok=True)
        
        # Run tests
        unittest.main(verbosity=2)
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    run_tests() 