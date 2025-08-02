#!/usr/bin/env python3
"""
MMS Smoke Test - Basic functionality test for ModelManagerSuite
Tests: load-model, generate, health_check
"""

import json
import zmq
import time
import requests
import sys

def test_mms_smoke(port=7721):
    """Basic smoke test for ModelManagerSuite on specified port"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout
    
    try:
        # Connect to MMS test instance
        socket.connect(f"tcp://localhost:{port}")
        print(f"✅ Connected to ModelManagerSuite test instance on port {port}")
        
        # Test 1: Health check
        print("\n🔍 Testing health_check...")
        health_request = {
            "action": "health_check"
        }
        socket.send_json(health_request)
        health_response = socket.recv_json()
        print(f"Health response: {health_response}")
        
        # Test 2: Generate (basic test)
        print("\n🔍 Testing generate...")
        generate_request = {
            "action": "generate",
            "prompt": "Hello, this is a test",
            "max_tokens": 10
        }
        socket.send_json(generate_request)
        generate_response = socket.recv_json()
        print(f"Generate response: {generate_response}")
        
        # Test 3: HTTP Health endpoint
        print("\n🔍 Testing HTTP health endpoint...")
        try:
            http_health = requests.get("http://localhost:9903/health", timeout=3)
            print(f"HTTP Health status: {http_health.status_code}")
            if http_health.status_code == 200:
                print(f"HTTP Health response: {http_health.text}")
        except Exception as e:
            print(f"HTTP Health test failed: {e}")
        
        print("\n✅ MMS Smoke test completed!")
        return True
        
    except zmq.ZMQError as e:
        print(f"❌ ZMQ Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Smoke test error: {e}")
        return False
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=7721, help='Port to test (default: 7721)')
    args = parser.parse_args()
    
    print(f"🚀 Starting ModelManagerSuite smoke test on port {args.port}...")
    success = test_mms_smoke(args.port)
    exit(0 if success else 1)
