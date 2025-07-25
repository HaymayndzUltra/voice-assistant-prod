#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Minimal test of EmotionEngine health check
"""

import sys
import os
sys.path.append('.')

from main_pc_code.agents.emotion_engine import EmotionEngine
import zmq
import json
import time
from common.env_helpers import get_env

def test_emotion_engine_health():
    print("🧪 Testing EmotionEngine health check...")
    
    # Create EmotionEngine instance
    agent = EmotionEngine(port=5585, pub_port=5587)
    
    # Wait for initialization
    time.sleep(3)
    
    print(f"✅ EmotionEngine created on port {agent.port} with health check on port {agent.health_check_port}")
    
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
            print("✅ EmotionEngine health check works!")
            return True
        else:
            print("❌ EmotionEngine health check failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        socket.close()
        context.term()
        agent.cleanup()

if __name__ == "__main__":
    test_emotion_engine_health() 