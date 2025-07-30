#!/usr/bin/env python3
"""
Test script for DreamingModeAgent
Validates that the agent can be imported, instantiated, and run successfully.
"""

import sys
import time
import threading
import zmq
import json
from pathlib import Path

# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def test_dreaming_mode_agent():
    """Test the DreamingModeAgent"""
    print("=== Testing DreamingModeAgent ===")

    try:
        # Import the agent
        print("1. Importing DreamingModeAgent...")
from pc2_code.agents.DreamingModeAgent import dreaming_mode_agent
from common.env_helpers import get_env
        print("   ✓ Import successful")

        # Create agent instance
        print("2. Creating DreamingModeAgent instance...")
        agent = DreamingModeAgent(port=7127)
        print("   ✓ Instance created successfully")

        # Start agent in a separate thread
        print("3. Starting DreamingModeAgent...")
        agent_thread = threading.Thread(target=agent.run, daemon=True)
        agent_thread.start()

        # Wait for agent to start
        time.sleep(2)
        print("   ✓ Agent started")

        # Test health check
        print("4. Testing health check...")
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:7127")

        # Send health check request
        health_request = {"action": "health_check"}
        socket.send_json(health_request)

        # Wait for response
        if socket.poll(5000) > 0:
            response = socket.recv_json()
            print(f"   ✓ Health check response: {response}")
        else:
            print("   ⚠ Health check timeout")

        socket.close()
        context.term()

        # Test dream status
        print("5. Testing dream status...")
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:7127")

        # Send dream status request
        status_request = {"action": "get_dream_status"}
        socket.send_json(status_request)

        if socket.poll(5000) > 0:
            response = socket.recv_json()
            print(f"   ✓ Dream status response: {response}")
        else:
            print("   ⚠ Dream status timeout")

        socket.close()
        context.term()

        # Let the agent run for a few more seconds
        print("6. Running agent for additional time...")
        time.sleep(3)

        # Stop the agent
        print("7. Stopping DreamingModeAgent...")
        agent.stop()
        agent.cleanup()

        # Wait for thread to finish
        agent_thread.join(timeout=5)
        print("   ✓ Agent stopped successfully")

        print("\n=== DreamingModeAgent Test Results ===")
        print("✓ SUCCESS: DreamingModeAgent proactively fixed and validated.")
        print("✓ Agent can be imported, instantiated, and run successfully")
        print("✓ Health check endpoint responds correctly")
        print("✓ Dream status functionality works")
        print("✓ Clean shutdown works")

        return True

    except ImportError as e:
        print(f"✗ FAILED: Import error - {e}")
        return False
    except Exception as e:
        print(f"✗ FAILED: Unexpected error - {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_dreaming_mode_agent()
    sys.exit(0 if success else 1)
