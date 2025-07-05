#!/usr/bin/env python3
"""
Test script for SystemDigitalTwin main port
"""
import zmq
import json
import time

def test_agent_connection(port=7120):
    """Send a request to the SystemDigitalTwin agent on its main port"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
    socket.connect(f"tcp://localhost:{port}")
    
    # Send a simple request
    request = {"action": "ping"}
    print(f"Sending request: {request}")
    socket.send_json(request)
    
    # Receive response
    try:
        response = socket.recv_json()
        print(f"Response received: {json.dumps(response, indent=2)}")
        return response
    except zmq.error.Again:
        print(f"Request timed out after 5 seconds")
        return None
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    print("Testing SystemDigitalTwin connection on port 7120...")
    test_agent_connection(7120) 