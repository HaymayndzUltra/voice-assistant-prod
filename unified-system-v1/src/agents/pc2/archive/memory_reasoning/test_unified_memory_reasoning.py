#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Test script for Unified Memory and Reasoning Agent
Tests all major features including context management, error patterns, and session handling
"""

import zmq
import json
import time
import logging
import sys
from pathlib import Path
from common.env_helpers import get_env

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("TestMemoryReasoning")

class TestClient:
    def __init__(self, port=5596, health_port=5597):
        """Initialize test client"""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.health_socket = self.context.socket(zmq.REQ)
        
        self.socket.connect(f"tcp://localhost:{port}")
        self.health_socket.connect(f"tcp://localhost:{health_port}")
        
        logger.info(f"Test client connected to ports {port} (main) and {health_port} (health)")
    
    def send_request(self, request):
        """Send request to agent"""
        self.socket.send_string(json.dumps(request))
        response = self.socket.recv_string()
        return json.loads(response)
    
    def check_health(self):
        """Check agent health"""
        self.health_socket.send_string(json.dumps({"action": "health_check"}))
        response = self.health_socket.recv_string()
        return json.loads(response)
    
    def close(self):
        """Close connections"""
        self.socket.close()
        self.health_socket.close()
        self.context.term()

def test_context_management(client):
    """Test context management features"""
    logger.info("Testing context management...")
    
    # Test adding interactions
    session_id = "test_session_1"
    interactions = [
        {
            "action": "add_interaction",
            "session_id": session_id,
            "type": "user_query",
            "content": "Please remember this important information: The system needs to be updated by Friday.",
            "metadata": {"importance": "high"}
        },
        {
            "action": "add_interaction",
            "session_id": session_id,
            "type": "system_response",
            "content": "I'll remember that the system update is needed by Friday.",
            "metadata": {"confidence": 0.9}
        },
        {
            "action": "add_interaction",
            "session_id": session_id,
            "type": "user_query",
            "content": "What was the last thing I asked you to remember?",
            "metadata": {"query_type": "recall"}
        }
    ]
    
    for interaction in interactions:
        response = client.send_request(interaction)
        logger.info(f"Interaction response: {response}")
        assert response["status"] == "ok"
    
    # Test getting context
    context_request = {
        "action": "get_context",
        "session_id": session_id,
        "max_tokens": 1000
    }
    
    response = client.send_request(context_request)
    logger.info(f"Context response: {response}")
    assert response["status"] == "ok"
    assert "summary" in response
    assert "conversation_summary" in response["summary"]
    
    return True

def test_error_patterns(client):
    """Test error pattern handling"""
    logger.info("Testing error patterns...")
    
    # Test adding error pattern
    error_pattern = {
        "action": "add_error_pattern",
        "error_type": "connection_timeout",
        "pattern": "Connection timed out after \\d+ seconds",
        "solution": "Check network connection and retry with exponential backoff"
    }
    
    response = client.send_request(error_pattern)
    logger.info(f"Add error pattern response: {response}")
    assert response["status"] == "ok"
    
    # Test getting error solution
    error_request = {
        "action": "get_error_solution",
        "error_message": "Connection timed out after 30 seconds"
    }
    
    response = client.send_request(error_request)
    logger.info(f"Get error solution response: {response}")
    assert response["status"] == "ok"
    assert response["solution"] == "Check network connection and retry with exponential backoff"
    
    return True

def test_health_monitoring(client):
    """Test health monitoring"""
    logger.info("Testing health monitoring...")
    
    response = client.check_health()
    logger.info(f"Health check response: {response}")
    
    assert response["status"] == "ok"
    assert "uptime_seconds" in response
    assert "total_requests" in response
    assert "error_patterns_count" in response
    assert "error_history_count" in response
    
    return True

def main():
    """Main test function"""
    try:
        client = TestClient()
        
        # Run tests
        tests = [
            ("Context Management", test_context_management),
            ("Error Patterns", test_error_patterns),
            ("Health Monitoring", test_health_monitoring)
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                logger.info(f"\nRunning test: {test_name}")
                result = test_func(client)
                results.append((test_name, result))
                logger.info(f"Test {test_name}: {'PASSED' if result else 'FAILED'}")
            except Exception as e:
                logger.error(f"Test {test_name} failed with error: {e}")
                results.append((test_name, False))
        
        # Print summary
        logger.info("\nTest Summary:")
        for test_name, result in results:
            logger.info(f"{test_name}: {'PASSED' if result else 'FAILED'}")
        
        # Final health check
        health = client.check_health()
        logger.info(f"\nFinal health status: {health}")
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        return 1
    finally:
        client.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 