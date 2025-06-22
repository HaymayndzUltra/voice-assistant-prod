#!/usr/bin/env python3
"""
Agent Health Check Test Script
Tests each agent for health check functionality
"""

import zmq
import json
import time
import sys
from pathlib import Path

def test_agent_health(agent_name, port, timeout=5):
    """Test agent health check"""
    print(f"Testing {agent_name} on port {port}...")
    
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, timeout * 1000)  # 5 second timeout
        socket.setsockopt(zmq.SNDTIMEO, timeout * 1000)
        
        # Connect to agent
        socket.connect(f"tcp://localhost:{port}")
        
        # Send health check request
        health_request = {
            "request_type": "health_check",
            "timestamp": time.time()
        }
        
        socket.send_json(health_request)
        
        # Wait for response
        response = socket.recv_json()
        
        print(f"✅ {agent_name}: HEALTH CHECK SUCCESS")
        print(f"   Response: {json.dumps(response, indent=2)}")
        return True
        
    except zmq.error.Again:
        print(f"❌ {agent_name}: TIMEOUT - No response within {timeout} seconds")
        return False
    except zmq.error.ZMQError as e:
        print(f"❌ {agent_name}: ZMQ ERROR - {str(e)}")
        return False
    except Exception as e:
        print(f"❌ {agent_name}: ERROR - {str(e)}")
        return False
    finally:
        try:
            socket.close()
            context.term()
        except:
            pass

def main():
    """Test all agents"""
    print("=" * 60)
    print("AGENT HEALTH CHECK TEST")
    print("=" * 60)
    
    # Phase 1 Agents
    agents = [
        ("TieredResponder", 7100),
        ("AsyncProcessor", 7101),
        ("CacheManager", 7102),
        ("PerformanceMonitor", 7103),
    ]
    
    results = []
    
    for agent_name, port in agents:
        success = test_agent_health(agent_name, port)
        results.append((agent_name, success))
        time.sleep(1)  # Brief pause between tests
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    successful = 0
    for agent_name, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{agent_name}: {status}")
        if success:
            successful += 1
    
    print(f"\nTotal: {successful}/{len(results)} agents responded to health checks")
    
    return successful == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 