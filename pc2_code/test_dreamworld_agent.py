#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Test script for DreamWorldAgent
"""

import os
import sys
import time
import zmq
import json

# Set a different port for testing
os.environ['DREAM_WORLD_PORT'] = '7200'

try:
    print("Testing DreamWorldAgent import...")
except Exception:
    pass
from pc2_code.agents.DreamWorldAgent import dream_world_agent
from common.env_helpers import get_env

    print("Creating DreamWorldAgent instance...")
    agent = DreamWorldAgent()

    print("DreamWorldAgent created successfully!")
    print(f"Main port: {agent.port}")
    print(f"Health port: {agent.health_port}")

    # Test health check
    print("Testing health check...")
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, 3000)  # 3 second timeout
    socket.connect(f"tcp://localhost:{agent.health_port}")

    request = {'action': 'health_check'}
    socket.send_json(request)

    response = socket.recv_json()
    print(f"Health check response: {json.dumps(response, indent=2)}")

    socket.close()
    context.term()

    print("✅ DreamWorldAgent test PASSED")

except Exception as e:
    print(f"❌ DreamWorldAgent test FAILED: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
