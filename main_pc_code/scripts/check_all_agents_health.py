#!/usr/bin/env python3
"""
Script to check health status of all agents
"""
import zmq
import json
import time
import sys
from pathlib import Path
import logging
import requests
import concurrent.futures
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Network Configuration - since we're on Main PC, use localhost
MAIN_PC_IP = "localhost"
PC2_IP = "localhost"  # We're on Main PC

# Agent Ports
PORTS = {
    "TaskRouter": 5571,
    "EnhancedModelRouter": 8570,
    "ChainOfThought": 5612,
    "CognitiveModel": 5600,
    "TinyLlama": 5615,
    "ConsolidatedTranslator": 5563,
    "RemoteConnector": 5557
}

def check_agent_health(name: str, port: int, host: str = "localhost") -> Dict:
    """Check health of a single agent"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)  # Don't wait on close
    socket.setsockopt(zmq.RCVTIMEO, 3000)  # 3 second timeout
    
    try:
        # Connect to agent
        socket.connect(f"tcp://{host}:{port}")
        logger.info(f"Checking {name} on {host}:{port}")
        
        # Send health check request
        socket.send_json({"type": "health_check"})
        
        # Wait for response
        response = socket.recv_json()
        status = "✅" if response.get("status") == "ok" else "❌"
        return {
            "name": name,
            "status": status,
            "host": host,
            "port": port,
            "response": response
        }
        
    except Exception as e:
        logger.error(f"Error checking {name}: {str(e)}")
        return {
            "name": name,
            "status": "❌",
            "host": host,
            "port": port,
            "error": str(e)
        }
    finally:
        socket.close()

def check_all_agents():
    """Check health of all agents"""
    results = []
    
    # Check Main PC agents
    main_pc_agents = {
        "TaskRouter": PORTS["TaskRouter"],
        "EnhancedModelRouter": PORTS["EnhancedModelRouter"],
        "ChainOfThought": PORTS["ChainOfThought"],
        "CognitiveModel": PORTS["CognitiveModel"],
        "TinyLlama": PORTS["TinyLlama"]
    }
    
    # Check PC2 agents
    pc2_agents = {
        "RemoteConnector": PORTS["RemoteConnector"],
        "ConsolidatedTranslator": PORTS["ConsolidatedTranslator"]
    }
    
    # Check Main PC agents
    logger.info("\nChecking Main PC agents...")
    for name, port in main_pc_agents.items():
        result = check_agent_health(name, port, MAIN_PC_IP)
        results.append(result)
    
    # Check PC2 agents (also on localhost since we're on Main PC)
    logger.info("\nChecking PC2 agents...")
    for name, port in pc2_agents.items():
        result = check_agent_health(name, port, PC2_IP)
        results.append(result)
    
    return results

def print_results(results: List[Dict]):
    """Print health check results in a formatted way"""
    print("\n" + "="*60)
    print("AGENT HEALTH STATUS")
    print("="*60)
    
    # Group by status
    healthy = []
    unhealthy = []
    
    for result in results:
        if result["status"] == "✅":
            healthy.append(result)
        else:
            unhealthy.append(result)
    
    # Print healthy agents
    if healthy:
        print("\n🟢 HEALTHY AGENTS:")
        print("-"*60)
        for agent in healthy:
            print(f"{agent['status']} {agent['name']} ({agent['host']}:{agent['port']})")
    
    # Print unhealthy agents
    if unhealthy:
        print("\n🔴 UNHEALTHY AGENTS:")
        print("-"*60)
        for agent in unhealthy:
            print(f"{agent['status']} {agent['name']} ({agent['host']}:{agent['port']})")
            if "error" in agent:
                print(f"   Error: {agent['error']}")
            elif "response" in agent:
                print(f"   Response: {agent['response']}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    try:
        results = check_all_agents()
        print_results(results)
    except KeyboardInterrupt:
        print("\nHealth check interrupted by user")
    except Exception as e:
        print(f"\nError running health checks: {e}") 