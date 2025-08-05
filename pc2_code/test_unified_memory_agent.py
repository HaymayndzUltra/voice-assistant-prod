#!/usr/bin/env python3
"""
Test script for UnifiedMemoryReasoningAgent
"""

import os
import sys
import time
import zmq
import json
import threading

# Set a different port for testing
os.environ['UNIFIED_MEMORY_PORT'] = '7205'

try:
    print("Testing UnifiedMemoryReasoningAgent import...")
from pc2_code.agents.unified_memory_reasoning_agent import UnifiedMemoryReasoningAgent
from common.env_helpers import get_env
    
    print("Creating UnifiedMemoryReasoningAgent instance...")
    agent = UnifiedMemoryReasoningAgent(zmq_port=7205, health_check_port=7206)
    
    print("UnifiedMemoryReasoningAgent created successfully!")
    print(f"Main port: 7205")
    print(f"Health port: 7206")
    
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
    socket.connect(ff"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:7206")
    
    request = {'action': 'health_check'}
    socket.send_string(json.dumps(request)
    
    response = socket.recv_string()
    response_data = json.loads(response)
    print(f"Health check response: {json.dumps(response_data, indent=2)}")
    
    socket.close()
    context.term()
    
    # Stop the agent
    agent.stop()
    
    print("✅ UnifiedMemoryReasoningAgent test PASSED")
    
except Exception as e:
    print(f"❌ UnifiedMemoryReasoningAgent test FAILED: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1) 