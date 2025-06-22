#!/usr/bin/env python3
"""
Test script for Chain of Thought Agent health check
"""
import zmq
import json
import time

def test_health_check():
    # Create ZMQ context and socket
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    
    # Connect to the Chain of Thought Agent
    socket.connect("tcp://localhost:5612")
    
    # Send health check request
    print("Sending health check request...")
    socket.send_string(json.dumps({"request_type": "health_check"}))
    
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