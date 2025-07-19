#!/usr/bin/env python3
"""
Minimal ZMQ Health Check Test
Directly test the health check port without the full health check script
"""

import zmq
import json
import time
from common.env_helpers import get_env

def test_health_check():
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
    
    try:
        print("Connecting to health check port 5591...")
        socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5591")
        
        print("Sending health check request...")
        request = {"action": "health_check"}
        socket.send_string(json.dumps(request))
        
        print("Waiting for response...")
        response = socket.recv()
        response_json = json.loads(response.decode())
        
        print("✅ Response received:")
        print(json.dumps(response_json, indent=2))
        return response_json
        
    except zmq.error.Again:
        print("❌ Timeout: No response within 5 seconds")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    test_health_check() 