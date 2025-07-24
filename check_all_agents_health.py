#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Comprehensive Health Check for Layer 0 and Layer 1 Agents

This script checks the health of all Layer 0 and Layer 1 agents by connecting
to their health check ports and requesting status information.
"""

import sys
import json
import time
import logging
import argparse
import zmq
from typing import Dict, List, Tuple, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('health_check')

# Define agent configurations
LAYER0_AGENTS = [
    {"name": "SystemDigitalTwin", "port": 7120, "health_port": 7121},
    {"name": "ModelManagerAgent", "port": 5570, "health_port": 5571},
    {"name": "CoordinatorAgent", "port": 26002, "health_port": 26003},
    {"name": "ChainOfThoughtAgent", "port": 5612, "health_port": 5613}
]

LAYER1_AGENTS = [
    {"name": "PredictiveHealthMonitor", "port": 5613, "health_port": 5614},
    {"name": "StreamingTTSAgent", "port": 5562, "health_port": 5563},
    {"name": "SessionMemoryAgent", "port": 5574, "health_port": 5575},
    {"name": "TinyLlamaService", "port": 5615, "health_port": 5616},
    {"name": "NLLBAdapter", "port": 5581, "health_port": 5582},
    {"name": "EnhancedModelRouter", "port": 5598, "health_port": 5599},
    {"name": "CognitiveModelAgent", "port": 5641, "health_port": 5642},
    {"name": "EmotionSynthesisAgent", "port": 5706, "health_port": 5707}
]

def check_agent_health(agent: Dict[str, Any], timeout: int = 5) -> Tuple[bool, Dict[str, Any]]:
    """
    Check the health of an agent by connecting to its health check port.
    
    Args:
        agent: Dictionary containing agent information
        timeout: Timeout in seconds
        
    Returns:
        Tuple of (is_healthy, response_data)
    """
    name = agent["name"]
    health_port = agent["health_port"]
    
    logger.info(f"Checking health of {name} on port {health_port}...")
    
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, timeout * 1000)
        socket.connect(f"tcp://localhost:{health_port}")
        
        # Send health check request
        socket.send_json({"action": "health_check"})
        
        # Wait for response
        response = socket.recv_json()
        
        # Check if response indicates health
        is_healthy = response.get("status") == "ok"
        if is_healthy:
            logger.info(f"✅ {name} is healthy: {json.dumps(response)}")
        else:
            logger.error(f"❌ {name} is NOT healthy: {json.dumps(response)}")
        
        return is_healthy, response
    except zmq.error.Again:
        logger.error(f"❌ {name} health check timed out after {timeout} seconds")
        return False, {"status": "error", "message": "Timeout"}
    except Exception as e:
        logger.error(f"❌ {name} health check failed: {e}")
        return False, {"status": "error", "message": str(e)}
    finally:
        try:
            socket.close()
            context.term()
        except Exception:
            pass

def check_all_agents(agents: List[Dict[str, Any]], timeout: int = 5) -> Dict[str, Tuple[bool, Dict[str, Any]]]:
    """
    Check the health of all agents in the list.
    
    Args:
        agents: List of agent configurations
        timeout: Timeout in seconds
        
    Returns:
        Dictionary mapping agent names to (is_healthy, response_data) tuples
    """
    results = {}
    
    for agent in agents:
        name = agent["name"]
        is_healthy, response = check_agent_health(agent, timeout)
        results[name] = (is_healthy, response)
    
    return results

def print_summary(layer0_results: Dict[str, Tuple[bool, Dict[str, Any]]], 
                 layer1_results: Dict[str, Tuple[bool, Dict[str, Any]]]) -> Tuple[bool, bool]:
    """
    Print a summary of health check results.
    
    Args:
        layer0_results: Results for Layer 0 agents
        layer1_results: Results for Layer 1 agents
        
    Returns:
        Tuple of (all_layer0_healthy, all_layer1_healthy)
    """
    print("\n" + "=" * 70)
    print("HEALTH CHECK SUMMARY")
    print("=" * 70)
    
    # Layer 0 summary
    print("\nLAYER 0 AGENTS:")
    print("-" * 70)
    all_layer0_healthy = True
    for name, (is_healthy, _) in layer0_results.items():
        status = "✅ HEALTHY" if is_healthy else "❌ UNHEALTHY"
        print(f"{name:30} {status}")
        all_layer0_healthy = all_layer0_healthy and is_healthy
    
    # Layer 1 summary
    print("\nLAYER 1 AGENTS:")
    print("-" * 70)
    all_layer1_healthy = True
    for name, (is_healthy, _) in layer1_results.items():
        status = "✅ HEALTHY" if is_healthy else "❌ UNHEALTHY"
        print(f"{name:30} {status}")
        all_layer1_healthy = all_layer1_healthy and is_healthy
    
    # Overall summary
    print("\nOVERALL SUMMARY:")
    print("-" * 70)
    print(f"Layer 0: {'✅ ALL HEALTHY' if all_layer0_healthy else '❌ SOME UNHEALTHY'}")
    print(f"Layer 1: {'✅ ALL HEALTHY' if all_layer1_healthy else '❌ SOME UNHEALTHY'}")
    print("=" * 70)
    
    return all_layer0_healthy, all_layer1_healthy

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Check health of Layer 0 and Layer 1 agents")
    parser.add_argument("--timeout", type=int, default=5, help="Timeout in seconds for each health check")
    parser.add_argument("--layer", choices=["0", "1", "all"], default="all", help="Which layer(s) to check")
    args = parser.parse_args()
    
    # Check Layer 0 if requested
    layer0_results = {}
    if args.layer in ["0", "all"]:
        logger.info("Checking Layer 0 agents...")
        layer0_results = check_all_agents(LAYER0_AGENTS, args.timeout)
    
    # Check Layer 1 if requested
    layer1_results = {}
    if args.layer in ["1", "all"]:
        logger.info("Checking Layer 1 agents...")
        layer1_results = check_all_agents(LAYER1_AGENTS, args.timeout)
    
    # Print summary
    all_layer0_healthy, all_layer1_healthy = print_summary(layer0_results, layer1_results)
    
    # Determine exit code
    if args.layer == "0":
        return 0 if all_layer0_healthy else 1
    elif args.layer == "1":
        return 0 if all_layer1_healthy else 1
    else:
        return 0 if all_layer0_healthy and all_layer1_healthy else 1

if __name__ == "__main__":
    sys.exit(main()) 