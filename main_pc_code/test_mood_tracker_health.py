#!/usr/bin/env python3
"""
MoodTrackerAgent Health Check Test
Tests the MoodTrackerAgent on port 5705 (main port 5704 + 1)
"""

import zmq
import json
import time
import subprocess
import signal
import os
from common.env_helpers import get_env

def test_mood_tracker_health():
    print("🎯 MOOD TRACKER AGENT HEALTH CHECK VALIDATION")
    print("=" * 50)
    
    # Step 1: Launch the agent
    print("1️⃣ Launching MoodTrackerAgent on port 5704...")
    try:
        process = subprocess.Popen(
            ["python3", "agents/mood_tracker_agent.py", "--port", "5704"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"   ✅ Agent started with PID: {process.pid}")
    except Exception as e:
        print(f"   ❌ Failed to start agent: {e}")
        return False
    
    # Step 2: Wait for initialization
    print("2️⃣ Waiting 5 seconds for initialization...")
    time.sleep(5)
    
    # Step 3: Perform health check
    print("3️⃣ Performing health check on port 5001...")
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
    
    try:
        socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5001")
        
        request = {"action": "health_check"}
        print(f"   📤 Sending request: {request}")
        socket.send_string(json.dumps(request))
        
        print("   ⏳ Waiting for response...")
        response = socket.recv()
        response_json = json.loads(response.decode())
        
        print("   📥 Response received:")
        print(json.dumps(response_json, indent=2))
        
        # Step 4: Validate response
        print("4️⃣ Validating response...")
        if response_json.get('status') == 'ok':
            print("   ✅ Status: 'ok' found")
            has_init_status = 'initialization_status' in response_json
            print(f"   {'✅' if has_init_status else '⚠️'} Initialization status field: {'Present' if has_init_status else 'Missing'}")
            
            print("\n🎉 FINAL RESULT: ✅ HEALTH CHECK VALIDATED")
            print("=" * 50)
            return True
        else:
            print(f"   ❌ Status not 'ok': {response_json.get('status')}")
            print("\n❌ FINAL RESULT: ❌ HEALTH CHECK FAILED")
            print("=" * 50)
            return False
            
    except zmq.error.Again:
        print("   ❌ Timeout: No response within 5 seconds")
        print("\n❌ FINAL RESULT: ❌ HEALTH CHECK FAILED")
        print("=" * 50)
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        print("\n❌ FINAL RESULT: ❌ HEALTH CHECK FAILED")
        print("=" * 50)
        return False
    finally:
        socket.close()
        context.term()
        
        # Step 5: Terminate agent
        print("5️⃣ Terminating agent...")
        try:
            process.terminate()
            process.wait(timeout=5)
            print("   ✅ Agent terminated successfully")
        except subprocess.TimeoutExpired:
            process.kill()
            print("   ⚠️ Agent force killed")
        except Exception as e:
            print(f"   ❌ Error terminating agent: {e}")

if __name__ == "__main__":
    test_mood_tracker_health() 