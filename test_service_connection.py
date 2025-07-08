#!/usr/bin/env python3
"""
Test connection to MemoryOrchestratorService
"""

import zmq
import json
import time
import sys

def test_connection(port=7140):
    """Test connection to MemoryOrchestratorService"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
    
    print(f"Connecting to tcp://localhost:{port}...")
    socket.connect(f"tcp://localhost:{port}")
    
    # Step 1: Add a new memory
    add_request = {
        "action": "add_memory",
        "data": {
            "content": "This is a test memory from MainPC",
            "memory_type": "test",
            "importance": 0.8,
            "metadata": {"source": "test_script"},
            "tags": ["test", "local"]
        }
    }
    print(f"Sending add_memory request: {add_request}")
    
    try:
        socket.send_json(add_request)
        print("Request sent, waiting for response...")
        add_response = socket.recv_json()
        print(f"Received response: {add_response}")
        
        if not isinstance(add_response, dict) or add_response.get("status") != "success":
            print("Failed to add memory")
            return False
        
        # Step 2: Retrieve the memory we just added
        memory_id = add_response.get("memory_id")
        if not memory_id:
            print("No memory_id in response")
            return False
            
        get_request = {
            "action": "get_memory",
            "data": {"memory_id": memory_id}
        }
        print(f"\nSending get_memory request: {get_request}")
        
        socket.send_json(get_request)
        print("Request sent, waiting for response...")
        get_response = socket.recv_json()
        print(f"Received response: {get_response}")
        
        return isinstance(get_response, dict) and get_response.get("status") == "success"
        
    except zmq.error.Again:
        print("Timeout waiting for response")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        socket.close()
        context.term()

def test_health_check(health_port=7141):
    """Test the health check endpoint"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
    
    print(f"Connecting to health check endpoint at tcp://localhost:{health_port}...")
    socket.connect(f"tcp://localhost:{health_port}")
    
    # Send a health check request
    request = {"action": "health_check"}
    print(f"Sending health check request: {request}")
    
    try:
        socket.send_json(request)
        print("Request sent, waiting for response...")
        response = socket.recv_json()
        print(f"Received health check response: {response}")
        
        if isinstance(response, dict) and response.get("status") == "ok":
            print("Health check passed!")
            return True
        else:
            print("Health check failed!")
            return False
    except zmq.error.Again:
        print("Timeout waiting for health check response")
        return False
    except Exception as e:
        print(f"Error during health check: {e}")
        return False
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "health":
        health_port = 7141
        if len(sys.argv) > 2:
            health_port = int(sys.argv[2])
        success = test_health_check(health_port)
    else:
        port = 7140
        if len(sys.argv) > 1:
            port = int(sys.argv[1])
        success = test_connection(port)
    
    sys.exit(0 if success else 1) 