#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.log_setup import configure_logging
"""
Simple Service Discovery Test

A simplified test script that directly connects to SystemDigitalTwin
and tests the service discovery functionality.
"""

import os
import sys
import time
import json
import zmq
import logging
from pathlib import Path
from common.env_helpers import get_env

# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SimpleServiceDiscoveryTest")

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# ANSI color codes for terminal output
COLORS = {
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "RED": "\033[91m",
    "BLUE": "\033[94m",
    "END": "\033[0m",
    "BOLD": "\033[1m"
}

def send_request(socket, request):
    """Send a request to the socket and receive the response."""
    logger.info(f"Sending request: {request}")
    socket.send_json(request)
    response = socket.recv_json()
    logger.info(f"Received response: {response}")
    return response

def print_result(success, message):
    """Print a test result with colored output."""
    if success:
        print(f"{COLORS['GREEN']}✓ {message}{COLORS['END']}")
    else:
        print(f"{COLORS['RED']}✗ {message}{COLORS['END']}")
    return success

def main():
    """Run the simple service discovery test."""
    print(f"{COLORS['BOLD']}Simple Service Discovery Test{COLORS['END']}")
    print("This test assumes SystemDigitalTwin is already running.")
    print()

    # Create ZMQ socket
    context = zmq.Context.instance()
    socket = context.socket(zmq.REQ)

    # Connect to SystemDigitalTwin
    address = f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:7120"
    print(f"Connecting to SystemDigitalTwin at {address}...")
    socket.connect(address)
    socket.setsockopt(zmq.RCVTIMEO, 3000)  # 3 second timeout

    try:
        # Test 1: Register a service
        print(f"\n{COLORS['BLUE']}Test 1: Register a test service{COLORS['END']}")
        register_request = {
            "command": "REGISTER",
            "payload": {
                "name": "SimpleTestService",
                "location": "TestLocation",
                "ip": "localhost",
                "port": 9999,
                "test_id": str(time.time())
            }
        }
        
        try:
            response = send_request(socket, register_request)
            success = response.get("status") == "SUCCESS"
            print_result(success, "Service registration")
            if not success:
                print(f"Error: {response.get('message', 'Unknown error')}")
                return 1
        except zmq.error.Again:
            print_result(False, "Service registration - Timeout")
            print(f"{COLORS['RED']}Connection timeout. Is SystemDigitalTwin running?{COLORS['END']}")
            return 1
        except Exception as e:
            print_result(False, f"Service registration - Error: {e}")
            return 1

        # Test 2: Discover the service
        print(f"\n{COLORS['BLUE']}Test 2: Discover the test service{COLORS['END']}")
        discover_request = {
            "command": "DISCOVER",
            "payload": {
                "name": "SimpleTestService"
            }
        }
        
        try:
            response = send_request(socket, discover_request)
            success = response.get("status") == "SUCCESS"
            print_result(success, "Service discovery")
            if success:
                service_info = response.get("payload", {})
                print("Service info:")
                print(json.dumps(service_info, indent=2))
            else:
                print(f"Error: {response.get('message', 'Unknown error')}")
                return 1
        except Exception as e:
            print_result(False, f"Service discovery - Error: {e}")
            return 1

        # Test 3: Try to discover a non-existent service
        print(f"\n{COLORS['BLUE']}Test 3: Try to discover a non-existent service{COLORS['END']}")
        discover_request = {
            "command": "DISCOVER",
            "payload": {
                "name": "NonExistentService"
            }
        }
        
        try:
            response = send_request(socket, discover_request)
            success = response.get("status") == "NOT_FOUND"
            print_result(success, "Non-existent service returns NOT_FOUND")
            if not success:
                print(f"Unexpected response: {response}")
                return 1
        except Exception as e:
            print_result(False, f"Non-existent service test - Error: {e}")
            return 1

        print(f"\n{COLORS['GREEN']}All tests passed!{COLORS['END']}")
        return 0

    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    sys.exit(main()) 