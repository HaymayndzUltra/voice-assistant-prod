#!/usr/bin/env python3
"""
Simple test script to check if the CoordinatorAgent's health check socket is responding.
"""

import zmq
import json
import time

def test_coordinator_health():
    """Test the health check endpoint of the CoordinatorAgent."""
    print("Testing CoordinatorAgent health check...")
    
    # Create ZMQ context and socket
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout
    
    # Try to connect to the health check port
    health_check_port = 26010  # The specific port used by CoordinatorAgent
    socket.connect(f"tcp://127.0.0.1:{health_check_port}")
    
    # Send health check request
    request = {"action": "health_check"}
    print(f"Sending health check request to port {health_check_port}: {request}")
    socket.send_json(request)
    
    try:
        # Wait for response
        response = socket.recv_json()
        print(f"Received response: {response}")
        
        # Check if the response indicates the agent is healthy
        if response.get("status") == "ok":
            print("CoordinatorAgent is healthy!")
            return True
        else:
            print(f"CoordinatorAgent reported unhealthy status: {response}")
            return False
    except zmq.error.Again:
        print("Timeout waiting for response from CoordinatorAgent")
        return False
    except Exception as e:
        print(f"Error testing CoordinatorAgent health: {e}")
        return False
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    test_coordinator_health() 