#!/usr/bin/env python3
"""
Simple Agent Health Check Test
Tests target agents with better error handling and debugging
"""

import subprocess
import zmq
import json
import time
import sys
import os
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import argparse
from common.env_helpers import get_env

def test_port_availability(host: str, port: int, timeout: int = 5) -> bool:
    """Test if a port is available for connection."""
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, timeout * 1000)
        socket.setsockopt(zmq.SNDTIMEO, timeout * 1000)
        
        socket.connect(f"tcp://{host}:{port}")
        socket.send_json({"action": "ping"})
        
        try:
            response = socket.recv_json()
            print(f"   ✅ Port {port} is responding")
            return True
        except zmq.error.Again:
            print(f"   ⚠️  Port {port} is open but not responding")
            return False
            
    except Exception as e:
        print(f"   ❌ Port {port} is not available: {e}")
        return False
    finally:
        try:
            socket.close()
            context.term()
        except:
            pass

def launch_agent(script_path: str, agent_name: str) -> Optional[subprocess.Popen]:
    """Launch an agent and return the process."""
    try:
        print(f"🚀 Launching {agent_name}...")
        print(f"   Script: {script_path}")
        
        # Launch agent process
        process = subprocess.Popen([
            sys.executable, script_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print(f"   ✅ Process started with PID: {process.pid}")
        return process
        
    except Exception as e:
        print(f"   ❌ Failed to launch {agent_name}: {e}")
        return None

def test_health_endpoint(host: str, port: int, action: str, agent_name: str, mode: str) -> Tuple[bool, Dict[str, Any]]:
    """Test a specific health endpoint with correct ZMQ mode."""
    try:
        print(f"🔍 Testing {agent_name} health endpoint...")
        print(f"   Port: {port}, Action: {action}, Mode: {mode}")
        
        # Wait for agent to initialize
        print("   ⏳ Waiting 7 seconds for initialization...")
        time.sleep(7)
        
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, 7000)  # 7 second timeout
        socket.setsockopt(zmq.SNDTIMEO, 3000)  # 3 second timeout
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
        print("   ❌ Timeout: No response within 7 seconds")
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
    parser = argparse.ArgumentParser()
    parser.add_argument('--script', type=str, required=True, help='Path to agent script')
    parser.add_argument('--port', type=int, required=True, help='Main port for the agent')
    parser.add_argument('--name', type=str, required=True, help='Agent name')
    args = parser.parse_args()

    print("=" * 80)
    print(f"🔬 {args.name.upper()} HEALTH CHECK TEST")
    print("=" * 80)
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    agent = {
        "name": args.name,
        "script": args.script,
        "main_port": args.port,
        "health_port": args.port + 1,
        "health_action": "health_check",
        "mode": "json"
    }
    
    results = {}
    print(f"🎯 Testing: {agent['name']}")
    print("-" * 60)
    
    # Step 1: Check if ports are already in use
    print("🔍 Checking port availability...")
    main_port_available = test_port_availability("localhost", agent['main_port'])
    health_port_available = test_port_availability("localhost", agent['health_port'])
    
    if not main_port_available and not health_port_available:
        print("   ⚠️  Ports appear to be free, proceeding with agent launch...")
    
    # Step 2: Launch agent
    process = launch_agent(agent['script'], agent['name'])
    if not process:
        results[agent['name']] = {
            "status": "❌ LAUNCH FAILED",
            "response": None,
            "is_valid": False
        }
    else:
        # Step 3: Test health endpoint (with correct mode)
        is_valid, response = test_health_endpoint(
            "localhost", 
            agent['health_port'], 
            agent['health_action'], 
            agent['name'],
            agent['mode']
        )
        # Step 4: Determine final status
        final_status = "✅ HEALTH CHECK VALIDATED" if is_valid else "❌ HEALTH CHECK FAILED"
        results[agent['name']] = {
            "status": final_status,
            "response": response,
            "is_valid": is_valid
        }
        # Step 5: Terminate agent
        terminate_process(process, agent['name'])
        print()
    # Generate copy-friendly summary report
    print("=" * 80)
    print("📊 TEST RESULT (COPY-FRIENDLY)")
    print("=" * 80)
    for agent_name, result in results.items():
        print(f"{agent_name} Health Check Report:")
        print("```json")
        print(json.dumps(result['response'], indent=2))
        print("```")
        print(f"Status: {result['status']}")
        print()
    print("=" * 80)
    print("END OF REPORT")
    print("=" * 80)

if __name__ == "__main__":
    main() 