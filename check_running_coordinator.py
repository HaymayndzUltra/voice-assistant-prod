#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Check the health of a running CoordinatorAgent without launching a new instance.
"""

import zmq
import json
import time

def check_health(port=26010):
    """Check the health of a running CoordinatorAgent."""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout
    socket.setsockopt(zmq.SNDTIMEO, 10000)  # 10 second timeout
    
    try:
        print(f"Checking health of CoordinatorAgent on port {port}...")
        socket.connect(f"tcp://127.0.0.1:{port}")
        
        # Send health check request
        socket.send_json({"action": "health_check"})
        print("Sent health check request")
        
        # Wait for response
        response = socket.recv_json()
        print(f"Received response: {response}")
        
        # Check if response indicates health
        if response.get("status") == "ok":
            print("✅ CoordinatorAgent is HEALTHY")
            return True
        else:
            print("❌ CoordinatorAgent is UNHEALTHY")
            return False
            
    except Exception as e:
        print(f"❌ Error checking health: {e}")
        return False
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    check_health() 