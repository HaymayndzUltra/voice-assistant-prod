#!/usr/bin/env python3
"""
Test script for SystemDigitalTwin health check
"""
import zmq
import json
import time

def test_health_check(port=8120):
    """Send a health check request to the SystemDigitalTwin agent"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
    socket.connect(f"tcp://localhost:{port}")
    
    # Send health check request
    request = {"action": "health_check"}
    socket.send_json(request)
    
    # Receive response
    try:
        response = socket.recv_json()
        print(f"Health check response: {json.dumps(response, indent=2)}")
        return response
    except zmq.error.Again:
        print(f"Health check request timed out after 5 seconds")
        return None
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    print("Testing SystemDigitalTwin health check...")
    test_health_check(8120) 