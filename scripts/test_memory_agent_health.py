#!/usr/bin/env python3
"""
Test Memory Agent Health Check
-----------------------------
This script tests the health check functionality of the UnifiedMemoryReasoningAgent.
"""

import os
import sys
import zmq
import json
import time
import logging
from pathlib import Path

# Add project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import common utilities
try:
    from common_utils.env_loader import get_ip, addr
    USE_COMMON_UTILS = True
except ImportError:
    USE_COMMON_UTILS = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("MemoryHealthTest")

def test_memory_agent_health(host: str = "localhost", port: int = 5597, timeout: int = 5000) -> bool:
    """
    Test the health check functionality of the UnifiedMemoryReasoningAgent.
    
    Args:
        host: Host of the memory agent
        port: Health check port of the memory agent
        timeout: Timeout in milliseconds
        
    Returns:
        bool: True if health check passed, False otherwise
    """
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, timeout)
    socket.setsockopt(zmq.LINGER, 0)
    
    try:
        # Connect to the memory agent
        address = f"tcp://{host}:{port}"
        logger.info(f"Connecting to memory agent at {address}")
        socket.connect(address)
        
        # Send health check request
        request = {"action": "health_check"}
        logger.info(f"Sending health check request: {request}")
        socket.send_json(request)
        
        # Wait for response
        response = socket.recv_json()
        logger.info(f"Received response: {json.dumps(response, indent=2)}")
        
        # Check response
        if response.get("status") == "success":
            logger.info("Health check passed!")
            return True
        else:
            logger.error(f"Health check failed: {response.get('message', 'Unknown error')}")
            return False
            
    except zmq.Again:
        logger.error(f"Timeout waiting for response from {host}:{port}")
        return False
    except Exception as e:
        logger.error(f"Error testing memory agent health: {e}")
        return False
    finally:
        socket.close()
        context.term()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Memory Agent Health Check")
    parser.add_argument("--host", default="localhost", help="Host of the memory agent")
    parser.add_argument("--port", type=int, default=5597, help="Health check port of the memory agent")
    parser.add_argument("--timeout", type=int, default=5000, help="Timeout in milliseconds")
    parser.add_argument("--use-env", action="store_true", help="Use environment variables for host")
    args = parser.parse_args()
    
    # Use environment variables if requested
    host = args.host
    if args.use_env and USE_COMMON_UTILS:
        host = get_ip("pc2")
        logger.info(f"Using host from environment: {host}")
    
    # Test memory agent health
    success = test_memory_agent_health(host, args.port, args.timeout)
    
    # Return exit code
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 