#!/usr/bin/env python3
"""
Test script for Unified Web Agent
Tests all major features including navigation, scraping, form filling, and conversation analysis
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
logger = logging.getLogger("TestWebAgent")

class TestClient:
    def __init__(self, port=5604, health_port=5605):
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

def test_navigation(client):
    """Test URL navigation"""
    logger.info("Testing URL navigation...")
    
    # Test navigating to a simple website
    request = {
        "action": "navigate",
        "url": "https://example.com"
    }
    
    response = client.send_request(request)
    logger.info(f"Navigation response: {response}")
    assert response["status"] == "success"
    assert "content" in response
    assert "headers" in response
    assert "status_code" in response
    
    return True

def test_scraping(client):
    """Test website scraping"""
    logger.info("Testing website scraping...")
    
    # Test scraping a simple website
    request = {
        "action": "scrape",
        "url": "https://example.com",
        "data_type": "text",
        "output_format": "json"
    }
    
    response = client.send_request(request)
    logger.info(f"Scraping response: {response}")
    assert response["status"] == "success"
    assert "data" in response
    assert "output_path" in response
    
    return True

def test_form_filling(client):
    """Test form filling"""
    logger.info("Testing form filling...")
    
    # Test filling a simple form
    request = {
        "action": "fill_form",
        "url": "https://httpbin.org/post",
        "form_data": {
            "name": "Test User",
            "email": "test@example.com"
        }
    }
    
    response = client.send_request(request)
    logger.info(f"Form filling response: {response}")
    assert response["status"] == "success"
    assert "response" in response
    
    return True

def test_conversation_analysis(client):
    """Test conversation analysis"""
    logger.info("Testing conversation analysis...")
    
    # Test analyzing a conversation
    request = {
        "action": "analyze_conversation",
        "conversation": [
            {"role": "user", "content": "Can you find information about Python web scraping?"},
            {"role": "assistant", "content": "I'll help you find information about web scraping in Python."}
        ]
    }
    
    response = client.send_request(request)
    logger.info(f"Conversation analysis response: {response}")
    assert response["status"] == "success"
    assert "analysis" in response
    
    return True

def test_proactive_gathering(client):
    """Test proactive information gathering"""
    logger.info("Testing proactive information gathering...")
    
    # Test proactive gathering
    request = {
        "action": "proactive_gather",
        "message": "I need to learn about web automation"
    }
    
    response = client.send_request(request)
    logger.info(f"Proactive gathering response: {response}")
    assert response["status"] == "success"
    assert "result" in response
    
    return True

def test_health_monitoring(client):
    """Test health monitoring"""
    logger.info("Testing health monitoring...")
    
    response = client.check_health()
    logger.info(f"Health check response: {response}")
    
    assert response["status"] == "ok"
    assert "uptime_seconds" in response
    assert "total_requests" in response
    assert "cache_size" in response
    assert "scraping_history_size" in response
    assert "form_history_size" in response
    
    return True

def main():
    """Main test function"""
    try:
        client = TestClient()
        
        # Run tests
        tests = [
            ("Navigation", test_navigation),
            ("Scraping", test_scraping),
            ("Form Filling", test_form_filling),
            ("Conversation Analysis", test_conversation_analysis),
            ("Proactive Gathering", test_proactive_gathering),
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