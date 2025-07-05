#!/usr/bin/env python3
"""
Verification script to check if core infrastructure agents are registered with SystemDigitalTwin.

This script connects to the SystemDigitalTwin agent and verifies that the following agents
are properly registered:
1. MemoryOrchestrator
2. CoordinatorAgent
3. ModelManagerAgent
"""

import zmq
import json
import time
import sys
from typing import Dict, Any, List, Optional

# Configuration
SYSTEM_DIGITAL_TWIN_PORT = 7120
TIMEOUT_MS = 5000  # 5 seconds

def connect_to_sdt() -> zmq.Socket:
    """Connect to the SystemDigitalTwin agent."""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, TIMEOUT_MS)
    socket.setsockopt(zmq.SNDTIMEO, TIMEOUT_MS)
    socket.connect(f"tcp://127.0.0.1:{SYSTEM_DIGITAL_TWIN_PORT}")
    return socket

def get_all_registered_agents(socket: zmq.Socket) -> Dict[str, Any]:
    """
    Get all agents registered with SystemDigitalTwin.
    
    Args:
        socket: ZMQ socket connected to SystemDigitalTwin
        
    Returns:
        Response from SystemDigitalTwin containing all registered agents
    """
    request = {
        "action": "get_all_agents"
    }
    
    print("Requesting all registered agents from SystemDigitalTwin...")
    socket.send_json(request)
    
    try:
        response = socket.recv_json()
        return response
    except zmq.error.Again:
        print("Request timed out")
        return {"status": "error", "error": "Request timed out"}

def verify_all_agents() -> bool:
    """
    Verify that all three core infrastructure agents are registered.
    
    Returns:
        True if all agents are registered, False otherwise
    """
    agents_to_check = [
        "MemoryOrchestrator",
        "CoordinatorAgent",
        "ModelManagerAgent"
    ]
    
    try:
        socket = connect_to_sdt()
    except Exception as e:
        print(f"Failed to connect to SystemDigitalTwin: {e}")
        return False
    
    response = get_all_registered_agents(socket)
    
    if response.get("status") != "success":
        print(f"Failed to get registered agents: {response.get('error', 'Unknown error')}")
        return False
    
    registered_agents = response.get("agents", {})
    
    all_registered = True
    results = {}
    
    for agent in agents_to_check:
        is_registered = agent in registered_agents
        agent_info = registered_agents.get(agent, {})
        
        results[agent] = {
            "registered": is_registered,
            "status": agent_info.get("status", "Unknown") if is_registered else "Not registered",
            "location": agent_info.get("location", "Unknown") if is_registered else "N/A",
            "last_update": agent_info.get("last_update", "Unknown") if is_registered else "N/A"
        }
        
        if not is_registered:
            all_registered = False
    
    # Print results
    print("\n=== Registration Verification Results ===")
    for agent, result in results.items():
        status = "✅ REGISTERED" if result["registered"] else "❌ NOT REGISTERED"
        print(f"{agent}: {status}")
        if result["registered"]:
            print(f"  Status: {result['status']}")
            print(f"  Location: {result['location']}")
            print(f"  Last Update: {result['last_update']}")
        print()
    
    return all_registered

if __name__ == "__main__":
    print("Verifying agent registration with SystemDigitalTwin...")
    success = verify_all_agents()
    
    if success:
        print("SUCCESS: All three base infrastructure agents are running and successfully registered with SystemDigitalTwin.")
        sys.exit(0)
    else:
        print("FAILURE: One or more agents failed to register with SystemDigitalTwin.")
        sys.exit(1) 