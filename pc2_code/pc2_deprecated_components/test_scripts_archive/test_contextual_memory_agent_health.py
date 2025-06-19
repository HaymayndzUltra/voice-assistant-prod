#!/usr/bin/env python3
"""
Test script for Contextual Memory Agent health check functionality.
Verifies that the Contextual Memory Agent responds correctly to health check requests.
"""
import zmq
import json
import time

def test_health_check():
    """Test the health check functionality of the Contextual Memory Agent."""
    # Create ZeroMQ context and request socket
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    
    # Connect to the Contextual Memory Agent
    socket.connect("tcp://localhost:5596")
    
    # Construct health check request
    request = {
        "action": "health_check",
        "timestamp": time.time()
    }
    
    # Send health check request
    print("Sending health check request...")
    socket.send_json(request)
    
    # Wait for response
    response = socket.recv_json()
    
    # Print health check response
    print("\nHealth Check Response:")
    print(json.dumps(response, indent=2))
    
    # Close socket and terminate context
    socket.close()
    context.term()

if __name__ == "__main__":
    test_health_check() 