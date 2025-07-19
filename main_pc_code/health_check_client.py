#!/usr/bin/env python3
"""
ZMQ Health Check Client for ConsolidatedTranslator Agent
"""

import zmq
import json
import time
import sys
from common.env_helpers import get_env

def send_health_check(port=5564, timeout=5):
    """Send health check request to agent"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, timeout * 1000)  # 5 second timeout
    
    try:
        socket.connect(f"tcp://localhost:{port}")
        
        # Send health check request
        request = {'action': 'health_check'}
        print(f"Sending health check request to port {port}...")
        socket.send_json(request)
        
        # Wait for response
        response = socket.recv_json()
        print(f"✅ Response received: {json.dumps(response, indent=2)}")
        return response
        
    except zmq.error.Again:
        print(f"❌ Timeout: No response from port {port} within {timeout} seconds")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5564
    response = send_health_check(port)
    
    if response and isinstance(response, dict) and response.get('status') == 'ok':
        print("✅ HEALTH CHECK VALIDATED")
        sys.exit(0)
    else:
        print("❌ HEALTH CHECK FAILED")
        sys.exit(1) 