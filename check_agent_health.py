#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Check Agent Health
"""

import zmq
import time
import sys
import json

def check_health(port):
    """Check the health of an agent on the given port"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
    
    try:
        socket.connect(f"tcp://localhost:{port}")
        socket.send(b"health")
        
        response = socket.recv_json()
        print(f"Health check response: {json.dumps(response, indent=2)}")
        return True
    except zmq.error.Again:
        print(f"Health check timed out for port {port}")
        return False
    except Exception as e:
        print(f"Error checking health on port {port}: {e}")
        return False
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_agent_health.py <port>")
        sys.exit(1)
    
    port = int(sys.argv[1])
    check_health(port)
