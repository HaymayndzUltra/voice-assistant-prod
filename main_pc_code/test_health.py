#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test script to verify health check functionality of SystemDigitalTwin agent."""

import zmq
import json
import time
import logging
from typing import Dict, Any, cast

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_health_check(port: int = 5585) -> bool:
    """Test health check functionality.
    
    Args:
        port: Port number of the SystemDigitalTwin agent
        
    Returns:
        bool: True if health check passed, False otherwise
    """
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
    
    try:
        # Connect to the agent
        socket.connect(f"tcp://localhost:{port}")
        logger.info(f"Connected to SystemDigitalTwin on port {port}")
        
        # Send health check request
        request = {"action": "health_check"}
        logger.info(f"Sending request: {request}")
        socket.send_json(request)
        
        # Wait for response
        response = cast(Dict[str, Any], socket.recv_json())
        logger.info(f"Received response: {response}")
        
        # Validate response
        if not isinstance(response, dict):
            raise AssertionError("Response is not a dictionary")
            
        if response.get("status") != "ok":
            raise AssertionError("Health check failed")
            
        if "agent" not in response:
            raise AssertionError("Response missing agent field")
            
        if response.get("agent") != "SystemDigitalTwin":
            raise AssertionError("Wrong agent responded")
        
        logger.info("Health check test passed!")
        return True
        
    except Exception as e:
        logger.error(f"Health check test failed: {e}")
        return False
        
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    test_health_check()
