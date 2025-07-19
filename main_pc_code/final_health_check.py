#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Final Agent Health Check Test
Robust health check with better error handling and clear reporting
"""

import subprocess
import zmq
import json
import time
import sys
import os
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from common.env_helpers import get_env

def launch_agent(script_path: str, agent_name: str, port: int) -> Optional[subprocess.Popen]:
    """Launch an agent with specific port."""
    try:
        print(f"🚀 Launching {agent_name} on port {port}...")
        process = subprocess.Popen([
            sys.executable, script_path, '--port', str(port)
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"   ✅ Process started with PID: {process.pid}")
        return process
    except Exception as e:
        print(f"   ❌ Failed to launch {agent_name}: {e}")
        return None

def test_health_endpoint(host: str, port: int, action: str, agent_name: str, mode: str) -> Tuple[bool, Dict[str, Any]]:
    """Test health endpoint with correct ZMQ mode."""
    try:
        print(f"🔍 Testing {agent_name} health endpoint...")
        print(f"   Port: {port}, Action: {action}, Mode: {mode}")
        
        # Wait for initialization
        print("   ⏳ Waiting 5 seconds for initialization...")
        time.sleep(5)
        
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        socket.setsockopt(zmq.SNDTIMEO, 2000)  # 2 second timeout
        socket.connect(f"tcp://{host}:{port}")
        
        request = {"action": action}
        print(f"   📤 Sending: {request}")
        
        if mode == "bytes":
            socket.send(json.dumps(request).encode("utf-8"))
            response_bytes = socket.recv()
            response = json.loads(response_bytes.decode("utf-8"))
        else:
            socket.send_json(request)
            response = socket.recv_json()
            
        print(f"   📋 Response: {json.dumps(response, indent=2)}")
        is_valid = validate_health_response(response)
        
        socket.close()
        context.term()
        return is_valid, response
        
    except zmq.error.Again:
        print("   ❌ Timeout: No response within 5 seconds")
        return False, {"error": "Timeout"}
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False, {"error": str(e)}

def validate_health_response(response: Dict[str, Any]) -> bool:
    """Validate health check response."""
    try:
        if not isinstance(response, dict):
            print("   ❌ Response is not a JSON object")
            return False
        
        if 'status' not in response:
            print("   ❌ Response missing 'status' field")
            return False
        
        status = response['status']
        if status not in ['ok', 'success']:
            print(f"   ❌ Status is not 'ok' or 'success': {status}")
            return False
        
        print("   ✅ Health check response validation passed")
        return True
        
    except Exception as e:
        print(f"   ❌ Response validation error: {e}")
        return False

def terminate_process(process: subprocess.Popen, agent_name: str):
    """Terminate a process gracefully."""
    try:
        print(f"🛑 Terminating {agent_name} (PID: {process.pid})...")
        process.terminate()
        process.wait(timeout=3)
        print(f"   ✅ {agent_name} terminated successfully")
    except subprocess.TimeoutExpired:
        print(f"   ⚠️  Force killing {agent_name}...")
        process.kill()
        process.wait()
        print(f"   ✅ {agent_name} force killed")
    except Exception as e:
        print(f"   ❌ Error terminating {agent_name}: {e}")

def main():
    """Main test function."""
    print("=" * 80)
    print("🔬 FINAL AGENT HEALTH CHECK TEST")
    print("=" * 80)
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test configuration
    agents = [
        {
            "name": "MoodTrackerAgent",
            "script": "agents/mood_tracker_agent.py",
            "port": 5704,
            "health_port": 5705,
            "health_action": "health",
            "mode": "bytes"
        },
        {
            "name": "HumanAwarenessAgent",
            "script": "agents/human_awareness_agent.py", 
            "port": 5705,
            "health_port": 5706,
            "health_action": "health_check",
            "mode": "json"
        }
    ]
    
    results = {}
    
    for agent in agents:
        print(f"🎯 Testing: {agent['name']}")
        print("-" * 60)
        
        # Launch agent
        process = launch_agent(agent['script'], agent['name'], agent['port'])
        if not process:
            results[agent['name']] = {
                "status": "❌ LAUNCH FAILED",
                "response": None,
                "is_valid": False
            }
            continue
        
        # Test health endpoint
        is_valid, response = test_health_endpoint(
            "localhost", 
            agent['health_port'], 
            agent['health_action'], 
            agent['name'],
            agent['mode']
        )
        
        # Determine final status
        final_status = "✅ HEALTH CHECK VALIDATED" if is_valid else "❌ HEALTH CHECK FAILED"
        
        results[agent['name']] = {
            "status": final_status,
            "response": response,
            "is_valid": is_valid
        }
        
        # Terminate agent
        terminate_process(process, agent['name'])
        print()
    
    # Generate final report
    print("=" * 80)
    print("📊 FINAL TEST RESULTS")
    print("=" * 80)
    print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    for agent_name, result in results.items():
        print(f"🎯 {agent_name}")
        print("-" * 40)
        print(f"Status: {result['status']}")
        if result['response']:
            print("Response:")
            print(json.dumps(result['response'], indent=2))
        print()
    
    # Summary
    total = len(results)
    successful = sum(1 for r in results.values() if r['is_valid'])
    failed = total - successful
    
    print("=" * 80)
    print("📈 FINAL SUMMARY")
    print("=" * 80)
    print(f"Total agents tested: {total}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    
    if successful == total:
        print("🎉 ALL AGENTS PASSED HEALTH CHECK!")
    else:
        print("⚠️  SOME AGENTS FAILED HEALTH CHECK")
    
    print("=" * 80)

if __name__ == "__main__":
    main() 