#!/usr/bin/env python3
"""
Test BaseAgent health check mechanism
"""

import sys
import os
sys.path.append('.')

from main_pc_code.src.core.base_agent import BaseAgent
import zmq
import json
import time
import threading
from common.env_helpers import get_env

def test_base_agent_health():
    print("🧪 Testing BaseAgent health check mechanism...")
    
    # Create a simple BaseAgent instance
    agent = BaseAgent(port=5580, name="TestAgent")
    
    # Wait for initialization
    time.sleep(2)
    
    print(f"✅ Agent created on port {agent.port} with health check on port {agent.health_check_port}")
    
    # Test health check
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, 5000)
    
    try:
        socket.connect(f"tcp://localhost:{agent.health_check_port}")
        
        # Send health check request
        request = {"action": "health_check"}
        print(f"📤 Sending: {json.dumps(request)}")
        socket.send_string(json.dumps(request))
        
        # Wait for response
        response = socket.recv_json()
        print(f"📥 Received: {json.dumps(response, indent=2)}")
        
        if response.get('status') == 'ok':
            print("✅ BaseAgent health check works!")
            return True
        else:
            print("❌ BaseAgent health check failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        socket.close()
        context.term()
        agent.cleanup()

if __name__ == "__main__":
    test_base_agent_health() 