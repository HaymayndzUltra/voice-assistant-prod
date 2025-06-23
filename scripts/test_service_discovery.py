#!/usr/bin/env python3
"""
Service Discovery Test Script

This script tests the service discovery mechanism by:
1. Directly using the service_discovery_client utility
2. Testing registration and discovery
"""

import os
import sys
import time
import json
import logging
from pathlib import Path

# Add project root to path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import the service discovery client
from main_pc_code.utils.service_discovery_client import register_service, discover_service, get_service_address

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ServiceDiscoveryTest")

def test_service_registry():
    """Test the service registration and discovery."""
    # Generate a unique service name using timestamp
    timestamp = int(time.time())
    test_service_name = f"TestService_{timestamp}"
    
    logger.info(f"Testing service discovery with service name: {test_service_name}")
    
    # Step 1: Register a test service
    logger.info("Step 1: Registering test service...")
    register_response = register_service(
        name=test_service_name,
        location="TestLocation",
        ip="192.168.0.123",
        port=12345,
        additional_info={
            "capabilities": ["test", "debug"],
            "version": "1.0.0",
            "status": "TESTING"
        }
    )
    
    logger.info(f"Registration response: {register_response}")
    if register_response.get("status") != "SUCCESS":
        logger.error("❌ Service registration failed")
        return False
    
    logger.info("✅ Service registration successful")
    
    # Step 2: Discover the service we just registered
    logger.info(f"Step 2: Discovering service: {test_service_name}...")
    discover_response = discover_service(test_service_name)
    
    logger.info(f"Discovery response: {discover_response}")
    if discover_response.get("status") != "SUCCESS":
        logger.error("❌ Service discovery failed")
        return False
    
    # Verify the service information matches what we registered
    service_info = discover_response.get("payload", {})
    if (service_info.get("name") == test_service_name and 
            service_info.get("location") == "TestLocation" and
            service_info.get("ip") == "192.168.0.123" and
            service_info.get("port") == 12345):
        logger.info("✅ Service discovery returned correct information")
    else:
        logger.error("❌ Service discovery returned incorrect information")
        logger.error(f"Expected: {test_service_name}, TestLocation, 192.168.0.123, 12345")
        logger.error(f"Got: {service_info}")
        return False
    
    # Step 3: Get service address using the helper function
    logger.info(f"Step 3: Getting service address for: {test_service_name}...")
    address = get_service_address(test_service_name)
    
    if address == "tcp://192.168.0.123:12345":
        logger.info(f"✅ Service address correctly returned: {address}")
    else:
        logger.error(f"❌ Incorrect service address returned: {address}")
        logger.error("Expected: tcp://192.168.0.123:12345")
        return False
    
    # Step 4: Try to discover a non-existent service
    logger.info("Step 4: Testing discovery of non-existent service...")
    non_existent_response = discover_service(f"NonExistentService_{timestamp}")
    
    if non_existent_response.get("status") == "NOT_FOUND":
        logger.info("✅ Correctly returned NOT_FOUND for non-existent service")
    else:
        logger.error(f"❌ Unexpected response for non-existent service: {non_existent_response}")
        return False
    
    logger.info("All service discovery tests passed successfully! ✅")
    return True

if __name__ == "__main__":
    logger.info("=== Service Discovery Test Script ===")
    
    # Run the test
    success = test_service_registry()
    
    if success:
        logger.info("🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Tests failed")
        sys.exit(1) 