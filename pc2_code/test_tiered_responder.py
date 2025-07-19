#!/usr/bin/env python3
"""
Test script for TieredResponder agent validation
Part of PC2 Phase 1 - Core Agents Implementation
"""

import sys
import os
import time
import threading
import signal
import zmq
import json
from pathlib import Path
from common.env_helpers import get_env

# Add agents directory to path
sys.path.insert(0, str(Path(__file__).parent / 'agents'))

def test_tiered_responder():
    """Test TieredResponder agent for stability"""
    print("=== Testing TieredResponder Agent ===")
    print("Starting TieredResponder...")
    
    try:
        # Import the agent
        from tiered_responder import TieredResponder
        
        # Create agent instance
        agent = TieredResponder()
        
        # Start the agent in a separate thread
        agent_thread = threading.Thread(target=agent.run, daemon=True)
        agent_thread.start()
        
        print("TieredResponder started successfully")
        print("Running for 10 seconds to validate stability...")
        
        # Wait for 10 seconds
        time.sleep(10)
        
        # Check if agent is still running
        if agent_thread.is_alive():
            print("SUCCESS: TieredResponder validation SUCCESS")
            print("Agent ran for 10+ seconds without crashing")
            return True
        else:
            print("FAILED: TieredResponder validation FAILED")
            print("Agent thread stopped unexpectedly")
            return False
            
    except Exception as e:
        print(f"FAILED: TieredResponder validation FAILED")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_tiered_responder_on_port():
    print("Testing TieredResponder on port 7100...")
    
    context = zmq.Context()
    sock = context.socket(zmq.REQ)
    sock.setsockopt(zmq.LINGER, 0)
    sock.setsockopt(zmq.RCVTIMEO, 3000)
    sock.setsockopt(zmq.SNDTIMEO, 3000)
    
    try:
        sock.connect('tcp://127.0.0.1:7100')
        sock.send_string(json.dumps({'action': 'health_check'}))
        
        try:
            response = sock.recv_string()
            print(f"SUCCESS: TieredResponder is responding!")
            print(f"Response: {response}")
            return True
        except zmq.error.Again:
            print("TIMEOUT: TieredResponder is not responding")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    finally:
        sock.close()
        context.term()

if __name__ == "__main__":
    success = test_tiered_responder()
    if not success:
        test_tiered_responder_on_port()
    sys.exit(0 if success else 1) 