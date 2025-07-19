#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Manual Registration Script for Core Infrastructure Agents

This script manually registers the three core infrastructure agents with SystemDigitalTwin:
1. MemoryOrchestrator
2. CoordinatorAgent
3. ModelManagerAgent
"""

import zmq
import json
import time
import sys

# Configuration
SYSTEM_DIGITAL_TWIN_PORT = 7120
TIMEOUT_MS = 5000  # 5 seconds

def connect_to_sdt():
    """Connect to the SystemDigitalTwin agent."""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, TIMEOUT_MS)
    socket.setsockopt(zmq.SNDTIMEO, TIMEOUT_MS)
    socket.connect(f"tcp://127.0.0.1:{SYSTEM_DIGITAL_TWIN_PORT}")
    return socket

def register_agent(socket, agent_name, location="MainPC", status="HEALTHY"):
    """
    Register an agent with SystemDigitalTwin.
    
    Args:
        socket: ZMQ socket connected to SystemDigitalTwin
        agent_name: Name of the agent to register
        location: Location of the agent (default: "MainPC")
        status: Status of the agent (default: "HEALTHY")
        
    Returns:
        Response from SystemDigitalTwin
    """
    request = {
        "action": "register_agent",
        "agent_name": agent_name,
        "location": location,
        "status": status
    }
    
    print(f"Registering agent {agent_name} at {location} with status {status}...")
    socket.send_json(request)
    
    try:
        response = socket.recv_json()
        return response
    except zmq.error.Again:
        print(f"Request for {agent_name} timed out")
        return {"status": "error", "error": "Request timed out"}

def register_all_agents():
    """
    Register all three core infrastructure agents with SystemDigitalTwin.
    
    Returns:
        True if all agents were registered successfully, False otherwise
    """
    agents_to_register = [
        {"name": "MemoryOrchestrator", "port": 5576, "location": "MainPC"},
        {"name": "CoordinatorAgent", "port": 26002, "location": "MainPC"},
        {"name": "ModelManagerAgent", "port": 5570, "location": "MainPC"}
    ]
    
    try:
        socket = connect_to_sdt()
    except Exception as e:
        print(f"Failed to connect to SystemDigitalTwin: {e}")
        return False
    
    all_registered = True
    results = {}
    
    for agent in agents_to_register:
        response = register_agent(socket, agent["name"], agent["location"])
        is_registered = response.get("status") == "success"
        
        results[agent["name"]] = {
            "registered": is_registered,
            "response": response
        }
        
        if not is_registered:
            all_registered = False
    
    # Print results
    print("\n=== Registration Results ===")
    for agent_name, result in results.items():
        status = "✅ REGISTERED" if result["registered"] else "❌ FAILED"
        print(f"{agent_name}: {status}")
        print(f"  Response: {result['response']}")
        print()
    
    return all_registered

def verify_registration():
    """
    Verify that all three core infrastructure agents are registered with SystemDigitalTwin.
    
    Returns:
        True if all agents are registered, False otherwise
    """
    try:
        socket = connect_to_sdt()
    except Exception as e:
        print(f"Failed to connect to SystemDigitalTwin: {e}")
        return False
    
    request = {
        "action": "get_all_agents"
    }
    
    print("Requesting all registered agents from SystemDigitalTwin...")
    socket.send_json(request)
    
    try:
        response = socket.recv_json()
    except zmq.error.Again:
        print("Request timed out")
        return False
    
    if response.get("status") != "success":
        print(f"Failed to get registered agents: {response.get('error', 'Unknown error')}")
        return False
    
    registered_agents = response.get("agents", {})
    
    agents_to_check = [
        "MemoryOrchestrator",
        "CoordinatorAgent",
        "ModelManagerAgent"
    ]
    
    all_registered = True
    results = {}
    
    for agent in agents_to_check:
        is_registered = agent in registered_agents
        agent_info = registered_agents.get(agent, {})
        
        results[agent] = {
            "registered": is_registered,
            "status": agent_info.get("status", "Unknown") if is_registered else "Not registered",
            "location": agent_info.get("location", "Unknown") if is_registered else "N/A",
            "last_update": agent_info.get("last_seen", "Unknown") if is_registered else "N/A"
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
    print("Registering core infrastructure agents with SystemDigitalTwin...")
    success = register_all_agents()
    
    if success:
        print("\nVerifying registration...")
        verify_success = verify_registration()
        
        if verify_success:
            print("\nSUCCESS: All three base infrastructure agents are running and successfully registered with SystemDigitalTwin.")
            sys.exit(0)
        else:
            print("\nFAILURE: One or more agents failed to register with SystemDigitalTwin.")
            sys.exit(1)
    else:
        print("\nFAILURE: Failed to register one or more agents with SystemDigitalTwin.")
        sys.exit(1) 