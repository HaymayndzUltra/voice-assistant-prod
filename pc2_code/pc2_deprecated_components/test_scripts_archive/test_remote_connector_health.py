#!/usr/bin/env python3
"""
Test script for Remote Connector Agent health check
"""
import zmq
import json
import time

def test_health_check():
    # Create ZMQ context and socket
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    
    # Connect to the Remote Connector Agent
    socket.connect("tcp://localhost:5557")
    
    # Send health check request
    print("Sending health check request...")
    socket.send_string(json.dumps({
        "action": "health_check",
        "timestamp": time.time()
    }))
    
    # Wait for response
    response = json.loads(socket.recv_string())
    
    # Print response
    print("\nHealth Check Response:")
    print(json.dumps(response, indent=2))
    
    # Cleanup
    socket.close()
    context.term()

if __name__ == "__main__":
    test_health_check() 