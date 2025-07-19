#!/usr/bin/env python3
"""
Debug Health Check - Shows exactly what's being sent and received
"""

import zmq
import json
import time
from common.env_helpers import get_env

def debug_health_check():
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout
    
    try:
        print("🔍 DEBUG: Connecting to health check port 5576...")
        socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5576")
        print("✅ DEBUG: Connected successfully")
        
        # Test 1: Send raw string
        print("\n🔍 DEBUG: Test 1 - Sending raw JSON string...")
        request = {"action": "health_check"}
        request_str = json.dumps(request)
        print(f"📤 DEBUG: Sending: {request_str}")
        socket.send_string(request_str)
        
        print("⏳ DEBUG: Waiting for response...")
        try:
            response = socket.recv_json()
            print(f"📥 DEBUG: Received JSON response: {json.dumps(response, indent=2)}")
            return response
        except zmq.error.Again:
            print("❌ DEBUG: Timeout waiting for response")
            return None
        except Exception as e:
            print(f"❌ DEBUG: Error receiving response: {e}")
            return None
            
    except Exception as e:
        print(f"❌ DEBUG: Error: {e}")
        return None
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    debug_health_check() 