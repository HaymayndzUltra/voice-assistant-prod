#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Working Agent Health Check Test
Properly instantiates agents with correct ports and tests health endpoints
"""

import zmq
import json
import time
import sys
import os
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

# Add the current directory to Python path to import agents
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_agent_health(agent_class, agent_name: str, port: int, health_port: int, health_action: str) -> Tuple[bool, Dict[str, Any]]:
    """Test a specific agent's health endpoint."""
    try:
        print(f"🔍 Testing {agent_name}...")
        print(f"   Main port: {port}")
        print(f"   Health port: {health_port}")
        print(f"   Health action: {health_action}")
        
        # Import and instantiate the agent with correct port
        print("   🚀 Instantiating agent...")
        agent = agent_class(port=port)
        
        # Wait for initialization
        print("   ⏳ Waiting 3 seconds for initialization...")
        time.sleep(3)
        
        # Test health endpoint
        print("   📤 Testing health endpoint...")
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        socket.setsockopt(zmq.SNDTIMEO, 2000)  # 2 second timeout
        
        # Connect to health port
        socket.connect(f"tcp://localhost:{health_port}")
        
        # Send health check request
        request = {"action": health_action}
        print(f"   📤 Sending: {request}")
        socket.send_json(request)
        
        # Receive response
        print("   📥 Waiting for response...")
        response = socket.recv_json()
        print(f"   📋 Response: {json.dumps(response, indent=2)}")
        
        # Validate response
        is_valid = validate_health_response(response)
        
        # Cleanup
        socket.close()
        context.term()
        
        # Stop the agent
        print("   🛑 Stopping agent...")
        agent.stop()
        
        return is_valid, response
        
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

def main():
    """Main test function."""
    print("=" * 80)
    print("🔬 WORKING AGENT HEALTH CHECK TEST")
    print("=" * 80)
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {}
    
    # Test MoodTrackerAgent
    print("🎯 Testing MoodTrackerAgent")
    print("-" * 60)
    
    try:
from main_pc_code.agents.mood_tracker_agent import MoodTrackerAgent
    except ImportError as e:
        print(f"Import error: {e}")
        is_valid, response = test_agent_health(
            MoodTrackerAgent, 
            "MoodTrackerAgent", 
            5704, 
            5705, 
            "health"
        )
        
        final_status = "✅ HEALTH CHECK VALIDATED" if is_valid else "❌ HEALTH CHECK FAILED"
        results["MoodTrackerAgent"] = {
            "status": final_status,
            "response": response,
            "is_valid": is_valid
        }
        
    except Exception as e:
        print(f"   ❌ Failed to test MoodTrackerAgent: {e}")
        results["MoodTrackerAgent"] = {
            "status": "❌ TEST FAILED",
            "response": {"error": str(e)},
            "is_valid": False
        }
    
    print()
    
    # Test HumanAwarenessAgent
    print("🎯 Testing HumanAwarenessAgent")
    print("-" * 60)
    
    try:
from main_pc_code.agents.human_awareness_agent import HumanAwarenessAgent
from common.env_helpers import get_env
    except ImportError as e:
        print(f"Import error: {e}")
        is_valid, response = test_agent_health(
            HumanAwarenessAgent, 
            "HumanAwarenessAgent", 
            5705, 
            5706, 
            "health_check"
        )
        
        final_status = "✅ HEALTH CHECK VALIDATED" if is_valid else "❌ HEALTH CHECK FAILED"
        results["HumanAwarenessAgent"] = {
            "status": final_status,
            "response": response,
            "is_valid": is_valid
        }
        
    except Exception as e:
        print(f"   ❌ Failed to test HumanAwarenessAgent: {e}")
        results["HumanAwarenessAgent"] = {
            "status": "❌ TEST FAILED",
            "response": {"error": str(e)},
            "is_valid": False
        }
    
    print()
    
    # Generate report
    print("=" * 80)
    print("📊 TEST RESULTS")
    print("=" * 80)
    
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
    print("📈 SUMMARY")
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