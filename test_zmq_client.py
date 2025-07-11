#!/usr/bin/env python3
"""
Simple ZMQ client to test the UnifiedMemoryReasoningAgent
"""

import zmq
import json
import time
import sys

def test_health_check(port=7106):
    """Test health check endpoint"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
    
    print(f"Connecting to health check on port {port}...")
    socket.connect(f"tcp://localhost:{port}")
    
    # Send health check request
    request = {"action": "health_check"}
    print(f"Sending health check request: {request}")
    socket.send_json(request)
    
    # Receive response
    try:
        response = socket.recv_json()
        print(f"Received health check response: {json.dumps(response, indent=2)}")
    except zmq.error.Again:
        print(f"Timeout waiting for health check response")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        socket.close()
        context.term()

def test_store_memory(port=7105):
    """Test store_memory endpoint"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
    
    print(f"Connecting to main endpoint on port {port}...")
    socket.connect(f"tcp://localhost:{port}")
    
    # Send store_memory request
    request = {
        "action": "store_memory",
        "memory_id": "test_memory",
        "content": "This is a test memory"
    }
    print(f"Sending store_memory request: {request}")
    socket.send_json(request)
    
    # Receive response
    try:
        response = socket.recv_json()
        print(f"Received store_memory response: {json.dumps(response, indent=2)}")
    except zmq.error.Again:
        print(f"Timeout waiting for store_memory response")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        socket.close()
        context.term()

def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "store":
        test_store_memory()
    else:
        test_health_check()

if __name__ == "__main__":
    main() 