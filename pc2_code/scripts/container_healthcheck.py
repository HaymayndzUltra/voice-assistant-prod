#!/usr/bin/env python3
"""
Container Health Check Script

This script is used as a health check for Docker containers running PC2 agents.
It verifies that all required agents in the container are running and responding.
"""

import os
import sys
import json
import time
import socket
import logging
import requests
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("container_healthcheck")

# Constants
TIMEOUT = 3  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def check_process_running(process_name: str) -> bool:
    """Check if a process is running by name."""
    try:
        output = subprocess.check_output(
            ["pgrep", "-f", process_name], 
            stderr=subprocess.DEVNULL, 
            text=True
        )
        return len(output.strip() > 0
    except subprocess.CalledProcessError:
        return False


def check_port_open(host: str, port: int) -> bool:
    """Check if a port is open and responding."""
    for _ in range(MAX_RETRIES):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TIMEOUT)
            result = sock.connect_ex((host, port)
            sock.close()
            if result == 0:
                return True
            time.sleep(RETRY_DELAY)
        except (socket.timeout, ConnectionRefusedError):
            time.sleep(RETRY_DELAY)
    return False


def check_agent_health(host: str, health_port: int) -> Tuple[bool, Optional[Dict]]:
    """Check agent health via HTTP health check endpoint."""
    for _ in range(MAX_RETRIES):
        try:
            response = requests.get(f"http://{host}:{health_port}/health", timeout=TIMEOUT)
            if response.status_code == 200:
                return True, response.json()
            time.sleep(RETRY_DELAY)
        except (requests.RequestException, json.JSONDecodeError):
            time.sleep(RETRY_DELAY)
    return False, None


def get_container_agents() -> List[Dict]:
    """Get the list of agents that should be running in this container."""
    pc2_role = os.environ.get("PC2_ROLE", "")
    
    if not pc2_role:
        logger.error("PC2_ROLE environment variable not set")
        return []
    
    # Try to load container groups config
    config_path = Path("/app/config/container_groups.yaml")
    if not config_path.exists():
        config_path = Path("/app/pc2_code/config/container_groups.yaml")
    
    if config_path.exists():
        try:
            import yaml
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            
            if pc2_role in config and "agents" in config[pc2_role]:
                return config[pc2_role]["agents"]
        except Exception as e:
            logger.error(f"Failed to load container groups config: {e}")
    
    # Fallback to startup_config.yaml
    config_path = Path("/app/config/startup_config.yaml")
    if not config_path.exists():
        config_path = Path("/app/pc2_code/config/startup_config.yaml")
    
    if config_path.exists():
        try:
            import yaml
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            
            agents = []
            for agent_config in config.get("pc2_services", []):
                # Logic to determine if this agent belongs to this container
                # This is a simplification - in a real implementation, you would need 
                # more robust logic to determine container membership
                if agent_config.get("name") in os.environ.get("CONTAINER_AGENTS", "").split(","):
                    agents.append(agent_config)
            
            return agents
        except Exception as e:
            logger.error(f"Failed to load startup config: {e}")
    
    return []


def main() -> int:
    """Main health check function."""
    agents = get_container_agents()
    
    if not agents:
        logger.warning("No agents configured for this container")
        # Return success in this case - the container might be a support container
        return 0
    
    all_healthy = True
    unhealthy_agents = []
    
    for agent in agents:
        agent_name = agent if isinstance(agent, str) else agent.get("name", "Unknown")
        
        # Check process (simple check)
        process_running = check_process_running(agent_name)
        
        # Check if port is open (if available in config)
        port_open = True  # Default to True if no port info
        if isinstance(agent, dict) and "port" in agent:
            port = agent["port"]
            port_open = check_port_open("localhost", port)
        
        # Check health endpoint (if available in config)
        health_check_ok = True  # Default to True if no health check port
        if isinstance(agent, dict) and "health_check_port" in agent:
            health_port = agent["health_check_port"]
            health_check_ok, _ = check_agent_health("localhost", health_port)
        
        agent_healthy = process_running and port_open and health_check_ok
        
        if not agent_healthy:
            all_healthy = False
            unhealthy_agents.append({
                "name": agent_name,
                "process_running": process_running,
                "port_open": port_open,
                "health_check_ok": health_check_ok
            })
    
    if not all_healthy:
        logger.error(f"Container unhealthy. Unhealthy agents: {json.dumps(unhealthy_agents, indent=2)}")
        return 1
    
    logger.info("All container agents are healthy")
    return 0


if __name__ == "__main__":
    sys.exit(main() 