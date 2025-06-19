#!/usr/bin/env python3
"""
Test script for Enhanced Model Router health check functionality.
Verifies that the router responds correctly to health check requests.
"""
import zmq
import json
import time

def test_health_check():
    # Create ZMQ context and socket
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    
    # Connect to Enhanced Model Router
    socket.connect("tcp://localhost:5601")
    
    # Send health check request
    request = {
        "action": "health_check",
        "timestamp": time.time()
    }
    print("Sending health check request...")
    socket.send_json(request)
    
    # Wait for response
    response = socket.recv_json()
    print("\nHealth check response:")
    print(json.dumps(response, indent=2))
    
    # Cleanup
    socket.close()
    context.term()

if __name__ == "__main__":
    test_health_check() 