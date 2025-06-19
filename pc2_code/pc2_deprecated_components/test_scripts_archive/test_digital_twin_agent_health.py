#!/usr/bin/env python3
"""
Health check test script for the Digital Twin Agent
"""
import zmq
import json
import time

def test_health_check():
    """Test the health check functionality of the Digital Twin Agent"""
    print("Sending health check request...")
    
    # Create ZMQ context and socket
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    
    # Connect to the Digital Twin Agent
    socket.connect("tcp://127.0.0.1:5597")
    
    # Send health check request
    request = {"action": "health_check"}
    socket.send_string(json.dumps(request))
    
    # Wait for response with timeout
    if socket.poll(5000) == 0:
        print("Error: Timeout waiting for response")
        return False
    
    # Get response
    response = socket.recv_string()
    result = json.loads(response)
    
    # Print response
    print("\nHealth check response:")
    print(json.dumps(result, indent=2))
    
    # Check if response is valid
    if result.get("status") == "ok":
        print("\nHealth check passed!")
        return True
    else:
        print("\nHealth check failed!")
        return False

if __name__ == "__main__":
    test_health_check() 