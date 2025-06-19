#!/usr/bin/env python3
"""
Comprehensive Health Check Script
Tests all running agents in the system
"""

import zmq
import json
import time
import sys
from pathlib import Path

# Agent configurations with their ports
AGENTS = {
    "SelfHealingAgent": {"port": 7125, "health_port": 7129},
    "UnifiedWebAgent": {"port": 7126, "health_port": 7127},
    "DreamingModeAgent": {"port": 7127, "health_port": 7128},
    "HealthCheckAgent": {"port": 5591, "health_port": 5592},
    "MetricsCollectorAgent": {"port": 5592, "health_port": 5593},
    "AlertManagerAgent": {"port": 5593, "health_port": 5594}
}

def test_agent_health(agent_name, port, timeout=5):
    """Test health check for a specific agent"""
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, timeout * 1000)  # Set receive timeout
        socket.setsockopt(zmq.SNDTIMEO, timeout * 1000)  # Set send timeout
        
        print(f"Testing {agent_name} on port {port}...")
        socket.connect(f"tcp://localhost:{port}")
        
        # Send health check request
        health_request = {"action": "health_check"}
        socket.send_json(health_request)
        
        # Wait for response
        if socket.poll(timeout * 1000):
            response = socket.recv_json()
            socket.close()
            context.term()
            
            if response.get('status') == 'success':
                print(f"✅ {agent_name}: HEALTHY")
                print(f"   - Agent: {response.get('agent', 'Unknown')}")
                print(f"   - Port: {response.get('port', 'Unknown')}")
                print(f"   - Timestamp: {response.get('timestamp', 'Unknown')}")
                return True
            else:
                print(f"❌ {agent_name}: UNHEALTHY - {response.get('message', 'Unknown error')}")
                return False
        else:
            socket.close()
            context.term()
            print(f"❌ {agent_name}: TIMEOUT")
            return False
            
    except Exception as e:
        print(f"❌ {agent_name}: ERROR - {str(e)}")
        return False

def test_health_port(agent_name, health_port, timeout=5):
    """Test health port for a specific agent"""
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, timeout * 1000)  # Set receive timeout
        socket.setsockopt(zmq.SNDTIMEO, timeout * 1000)  # Set send timeout
        
        print(f"Testing {agent_name} health port {health_port}...")
        socket.connect(f"tcp://localhost:{health_port}")
        
        health_request = {"action": "health_check"}
        socket.send_json(health_request)
        
        if socket.poll(timeout * 1000):
            response = socket.recv_json()
            socket.close()
            context.term()
            
            if response.get('status') == 'success':
                print(f"✅ {agent_name} Health Port: HEALTHY")
                return True
            else:
                print(f"❌ {agent_name} Health Port: UNHEALTHY")
                return False
        else:
            socket.close()
            context.term()
            print(f"❌ {agent_name} Health Port: TIMEOUT")
            return False
            
    except Exception as e:
        print(f"❌ {agent_name} Health Port: ERROR - {str(e)}")
        return False

def main():
    print("🔍 COMPREHENSIVE AGENT HEALTH CHECK")
    print("=" * 50)
    
    healthy_agents = 0
    total_agents = len(AGENTS)
    
    for agent_name, config in AGENTS.items():
        print(f"\n--- Testing {agent_name} ---")
        
        # Test main port
        main_healthy = test_agent_health(agent_name, config["port"])
        
        # Test health port
        health_healthy = test_health_port(agent_name, config["health_port"])
        
        if main_healthy and health_healthy:
            healthy_agents += 1
            print(f"🎉 {agent_name}: FULLY OPERATIONAL")
        elif main_healthy:
            print(f"⚠️  {agent_name}: PARTIALLY OPERATIONAL (main port only)")
        else:
            print(f"💥 {agent_name}: NOT OPERATIONAL")
        
        print("-" * 30)
    
    print(f"\n📊 HEALTH CHECK SUMMARY")
    print("=" * 50)
    print(f"Healthy Agents: {healthy_agents}/{total_agents}")
    print(f"Success Rate: {(healthy_agents/total_agents)*100:.1f}%")
    
    if healthy_agents == total_agents:
        print("🎉 ALL AGENTS ARE HEALTHY!")
        return 0
    else:
        print("⚠️  SOME AGENTS NEED ATTENTION")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 