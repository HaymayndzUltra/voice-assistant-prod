#!/usr/bin/env python3
"""
Test script for Unified Memory and Reasoning Agent
Tests all major features including context management, error patterns, and session handling
"""

import zmq
import json
import logging
import sys
from pathlib import Path
from common.utils.log_setup import configure_logging

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent)

# Configure logging
logger = configure_logging(__name__)
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
                results.append((test_name, result)
                logger.info(f"Test {test_name}: {'PASSED' if result else 'FAILED'}")
            except Exception as e:
                logger.error(f"Test {test_name} failed with error: {e}")
                results.append((test_name, False)
        
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
    sys.exit(main() 