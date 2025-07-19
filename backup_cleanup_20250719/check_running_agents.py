#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Check the health of running agents without launching new instances.
"""

import zmq
import json
import time
import logging
import argparse
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AgentHealthChecker")

# Agent configuration
AGENTS = {
    "SystemDigitalTwin": {
        "port": 7121,  # Health check port (7120 + 1)
        "type": "zmq",
        "request": {"action": "health_check"}
    },
    "MemoryOrchestrator": {
        "port": 5576,  # Health check port (5575 + 1)
        "type": "zmq",
        "request": {"action": "health_check"}
    },
    "ModelManagerAgent": {
        "port": 5571,  # Health check port (5570 + 1)
        "type": "zmq",
        "request": {"action": "health_check"}
    },
    "CoordinatorAgent": {
        "port": 26010,  # Custom health check port
        "type": "zmq",
        "request": {"action": "health_check"}
    }
}

def check_zmq_health(agent_name: str, port: int, request: Dict[str, Any]) -> bool:
    """Check the health of an agent using ZMQ."""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout
    socket.setsockopt(zmq.SNDTIMEO, 10000)  # 10 second timeout
    
    try:
        logger.info(f"Checking health of {agent_name} on port {port}...")
        socket.connect(f"tcp://127.0.0.1:{port}")
        
        # Send health check request
        socket.send_json(request)
        logger.debug(f"Sent health check request to {agent_name}: {request}")
        
        # Wait for response
        response = socket.recv_json()
        logger.info(f"Received response from {agent_name}: {response}")
        
        # Check if response indicates health
        if "status" in response and response["status"] == "ok":
            logger.info(f"✅ {agent_name} is HEALTHY")
            return True
        else:
            logger.warning(f"❌ {agent_name} is UNHEALTHY: {response}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error checking health of {agent_name}: {e}")
        return False
    finally:
        socket.close()
        context.term()

def check_all_agents():
    """Check the health of all configured agents."""
    results = {}
    
    for agent_name, config in AGENTS.items():
        if config["type"] == "zmq":
            results[agent_name] = check_zmq_health(
                agent_name, 
                config["port"], 
                config["request"]
            )
    
    # Print summary
    print("\n=== Agent Health Summary ===")
    for agent_name, is_healthy in results.items():
        status = "✅ HEALTHY" if is_healthy else "❌ UNHEALTHY"
        print(f"{agent_name}: {status}")
    
    # Return overall status
    return all(results.values())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check the health of running agents")
    parser.add_argument("--agent", help="Specific agent to check")
    args = parser.parse_args()
    
    if args.agent:
        if args.agent in AGENTS:
            config = AGENTS[args.agent]
            if config["type"] == "zmq":
                check_zmq_health(args.agent, config["port"], config["request"])
        else:
            logger.error(f"Unknown agent: {args.agent}")
    else:
        check_all_agents() 