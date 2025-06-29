#!/usr/bin/env python3
"""
Simple script to test ZMQ health check connection
"""

import zmq
import json
import time

def test_health_check(host, port, action):
    print(f"Testing health check on {host}:{port} with action '{action}'...")
    
    # Create ZMQ client
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
    socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5 second timeout
    
    # Connect to health port
    socket.connect(f"tcp://{host}:{port}")
    
    # Send health check request
    request = {'action': action}
    print(f"Sending request: {request}")
    socket.send_json(request)
    
    # Receive response
    try:
        print("Waiting for response...")
        response_bytes = socket.recv()
        response = json.loads(response_bytes.decode('utf-8'))
        print(f"Response received: {json.dumps(response, indent=2)}")
        return True, response
    except zmq.error.Again:
        print("Timeout: No response within 5 seconds")
        return False, {"error": "Timeout - no response received"}
    except Exception as e:
        print(f"Error: {e}")
        return False, {"error": str(e)}
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    # Test MoodTrackerAgent
    print("=" * 60)
    print("Testing MoodTrackerAgent")
    print("=" * 60)
    test_health_check("localhost", 5705, "health")
    
    # Test HumanAwarenessAgent
    print("\n" + "=" * 60)
    print("Testing HumanAwarenessAgent")
    print("=" * 60)
    test_health_check("localhost", 5706, "health") 