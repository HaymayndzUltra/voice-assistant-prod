#!/usr/bin/env python
"""
Simple ZeroMQ client to check the health status of memory agents.
"""
import sys
import time
import json
import zmq
from common.env_helpers import get_env

def check_agent_health(port, name):
    """Connect to a ZeroMQ socket and send a health check request."""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    address = f"tcp://localhost:{port}"
    print(f"\nChecking {name} at {address}...")
    
    try:
        socket.connect(address)
        socket.setsockopt(zmq.RCVTIMEO, 3000)  # 3 second timeout
        
        # Send health check request
        request = {"action": "health_check"}
        socket.send_json(request)
        print(f"Sent health check request to {name}")
        
        # Wait for response
        try:
            response = socket.recv_json()
            print(f"Response from {name}:")
            print(json.dumps(response, indent=2))
            return True, response
        except zmq.error.Again:
            print(f"ERROR: No response from {name} (timeout)")
            return False, None
    except Exception as e:
        print(f"ERROR: Failed to connect to {name}: {str(e)}")
        return False, None
    finally:
        socket.close()
        context.term()

def check_memory_services():
    """Check all memory-related services."""
    print("PC2 MEMORY SERVICES HEALTH CHECK")
    print("=" * 50)
    
    # Define memory agents to check
    agents = [
        {"port": 5590, "name": "Memory Agent (memory.py)"},
        {"port": 5596, "name": "Contextual Memory Agent"},
        {"port": 5598, "name": "Jarvis Memory Agent (DEPRECATED)"}
    ]
    
    results = []
    
    # Check each agent
    for agent in agents:
        success, response = check_agent_health(agent["port"], agent["name"])
        agent_status = {
            "name": agent["name"],
            "port": agent["port"],
            "status": "ACTIVE" if success else "UNREACHABLE",
            "response": response
        }
        results.append(agent_status)
    
    # Print summary
    print("\nMEMORY AGENTS HEALTH CHECK SUMMARY")
    print("=" * 50)
    print(f"{'Agent':<35} {'Port':<8} {'Status':<12}")
    print("-" * 55)
    
    for result in results:
        print(f"{result['name']:<35} {result['port']:<8} {result['status']:<12}")
    
    return results

if __name__ == "__main__":
    check_memory_services()
