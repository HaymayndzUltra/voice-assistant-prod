#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Health Check Script

This script checks the health of agents in a container group.
It reads the startup configuration and checks the health of each agent.
"""

import os
import sys
import yaml
import requests
import time
import logging
import socket
import json
from pathlib import Path
from typing import Dict, Any, List, Optional


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, get_project_root())
from common.utils.path_manager import PathManager
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PathManager.join_path("logs", str(PathManager.get_logs_dir() / "health_check.log")))
    ]
)
logger = logging.getLogger("health_check")

def load_config() -> Optional[Dict[str, Any]]:
    """Load the startup configuration."""
    config_path = PathManager.join_path("pc2_code", PathManager.join_path("config", "startup_config.yaml"))
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return None

def get_container_agents(config: Dict[str, Any], container_group: str) -> List[Dict[str, Any]]:
    """Get agents for a specific container group."""
    if not config or "pc2_services" not in config:
        logger.error("Invalid configuration")
        return []
        
    container_agents = []
    
    # Map container group names to comment markers in the config
    group_markers = {
        "core_infrastructure": "Group 1: Core Infrastructure Container",
        "memory_storage": "Group 2: Memory & Storage Container",
        "security_authentication": "Group 3: Security & Authentication Container",
        "integration_communication": "Group 4: Integration & Communication Container",
        "monitoring_support": "Group 5: Monitoring & Support Container",
        "dream_tutoring": "Group 6: Dream & Tutoring Container",
        "web_external": "Group 7: Web & External Services Container"
    }
    
    marker = group_markers.get(container_group)
    if not marker:
        logger.error(f"Unknown container group: {container_group}")
        return []
    
    # Find agents in the specified group
    in_group = False
    for agent in config["pc2_services"]:
        # Check if we've hit a comment that marks the start of a group
        if isinstance(agent, str) and marker in agent:
            in_group = True
            continue
            
        # Check if we've hit a comment that marks the start of another group
        if in_group and isinstance(agent, str) and any(m in agent for m in group_markers.values() if m != marker):
            break
            
        # Add agent to the list if we're in the right group
        if in_group and isinstance(agent, dict) and "name" in agent:
            container_agents.append(agent)
    
    # If we didn't find any agents using comment markers, try using the agent list directly
    if not container_agents:
        logger.warning(f"No agents found for {container_group} using comment markers, trying direct search")
        for agent in config["pc2_services"]:
            if isinstance(agent, dict) and "name" in agent:
                # Check if agent script path contains the container group name
                script_path = agent.get("script_path", "")
                if container_group.replace("_", "") in script_path.lower().replace("_", ""):
                    container_agents.append(agent)
    
    logger.info(f"Found {len(container_agents)} agents for container group {container_group}")
    return container_agents

def check_agent_health_http(agent: Dict[str, Any]) -> bool:
    """Check health of a single agent using HTTP."""
    health_url = f"http://localhost:{agent['health_check_port']}/health"
    try:
        response = requests.get(health_url, timeout=5)
        if response.status_code == 200:
            logger.info(f"Agent {agent['name']} is healthy (HTTP)")
            return True
        else:
            logger.warning(f"Agent {agent['name']} returned status code {response.status_code}")
            return False
    except Exception as e:
        logger.warning(f"Failed to check health of agent {agent['name']} via HTTP: {e}")
        return False

def check_agent_health_socket(agent: Dict[str, Any]) -> bool:
    """Check health of a single agent using socket connection."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', agent['port']))
        sock.close()
        
        if result == 0:
            logger.info(f"Agent {agent['name']} is healthy (Socket)")
            return True
        else:
            logger.warning(f"Agent {agent['name']} port {agent['port']} is not open")
            return False
    except Exception as e:
        logger.warning(f"Failed to check health of agent {agent['name']} via socket: {e}")
        return False

def check_agent_health_zmq(agent: Dict[str, Any]) -> bool:
    """Check health of a single agent using ZMQ health check."""
    try:
        import zmq
from main_pc_code.utils.network_utils import get_zmq_connection_string, get_machine_ip
from common.env_helpers import get_env
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, 2000)
        socket.connect(get_zmq_connection_string({agent[, "localhost"))health_check_port']}")
        
        # Send health check request
        socket.send_json({"action": "health_check"})
        
        # Wait for response
        response = socket.recv_json()
        socket.close()
        
        if isinstance(response, dict) and response.get("status") == "ok":
            logger.info(f"Agent {agent['name']} is healthy (ZMQ)")
            return True
        else:
            logger.warning(f"Agent {agent['name']} returned unhealthy status: {response}")
            return False
    except Exception as e:
        logger.warning(f"Failed to check health of agent {agent['name']} via ZMQ: {e}")
        return False

def check_agent_health(agent: Dict[str, Any]) -> bool:
    """Check health of a single agent using multiple methods."""
    # Try HTTP health check first
    if check_agent_health_http(agent):
        return True
    
    # Try ZMQ health check
    try:
        if check_agent_health_zmq(agent):
            return True
    except ImportError:
        logger.warning("ZMQ not available, skipping ZMQ health check")
    
    # Fall back to socket check
    return check_agent_health_socket(agent)

def main():
    if len(sys.argv) < 2:
        logger.error("Usage: python health_check.py <container_group>")
        sys.exit(1)
    
    container_group = sys.argv[1]
    logger.info(f"Checking health of container group: {container_group}")
    
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        sys.exit(1)
        
    agents = get_container_agents(config, container_group)
    
    if not agents:
        logger.error(f"No agents found for container group: {container_group}")
        sys.exit(1)
    
    # Check health of all agents in the container
    all_healthy = True
    health_status = {}
    
    for agent in agents:
        is_healthy = check_agent_health(agent)
        health_status[agent["name"]] = "healthy" if is_healthy else "unhealthy"
        
        if not is_healthy:
            all_healthy = False
            logger.error(f"Agent {agent['name']} is unhealthy")
    
    # Write health status to file
    health_file = PathManager.join_path("logs", "{container_group}_health.json")
    with open(health_file, "w") as f:
        json.dump({
            "container_group": container_group,
            "timestamp": time.time(),
            "all_healthy": all_healthy,
            "agents": health_status
        }, f)
    
    if all_healthy:
        logger.info(f"All agents in {container_group} are healthy")
        sys.exit(0)
    else:
        logger.error(f"One or more agents in {container_group} are unhealthy")
        sys.exit(1)

if __name__ == "__main__":
    main() 