#!/usr/bin/env python3
"""
Test script for Unified Web Agent
Tests all major features including navigation, scraping, form filling, and conversation analysis
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