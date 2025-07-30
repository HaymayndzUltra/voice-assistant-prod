#!/usr/bin/env python3
"""
Test script for EpisodicMemoryAgent
"""

import os
import sys
import time
import zmq
import json
import threading

# Set a different port for testing
os.environ['EPISODIC_MEMORY_PORT'] = '7206'

try:
    print("Testing EpisodicMemoryAgent import...")
from pc2_code.agents.EpisodicMemoryAgent import episodic_memory_agent
from common.env_helpers import get_env

    print("Creating EpisodicMemoryAgent instance...")
    agent = EpisodicMemoryAgent(port=7206, health_port=7207)

    print("EpisodicMemoryAgent created successfully!")
    print(f"Main port: 7206")
    print(f"Health port: 7207")

    # Start the agent's service loop in background thread
    print("Starting agent service loop...")
    agent_thread = threading.Thread(target=agent.run, daemon=True)
    agent_thread.start()

    # Wait for initialization and service loop to start
    print("Waiting for initialization and service loop...")
    time.sleep(5)

    # Test health check
    print("Testing health check...")
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
    socket.connect(ff"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:7207")

    request = {'action': 'health_check'}
    socket.send_json(request)

    response = socket.recv_json()
    print(f"Health check response: {json.dumps(response, indent=2)}")

    socket.close()
    context.term()

    print("✅ EpisodicMemoryAgent test PASSED")

except Exception as e:
    print(f"❌ EpisodicMemoryAgent test FAILED: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
