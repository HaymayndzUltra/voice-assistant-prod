#!/usr/bin/env python3
"""
Container healthcheck script for Podman containerized deployment.
This script checks the health of all agents running in a container group.
"""

import os
import sys
import json
import yaml
import socket
import logging
import requests
from pathlib import Path
from common.env_helpers import get_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("container_healthcheck")

def load_startup_config():
    """Load the startup configuration."""
    config_path = Path(__file__).parent.parent / "config" / "startup_config.yaml"
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Failed to load startup config: {e}")
        sys.exit(1)

def check_agent_health(host, port):
    """Check if an agent's health endpoint is responding."""
    try:
        # Try HTTP health check first
        url = f"http://{host}:{port}/health"
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            health_data = response.json()
            if health_data.get("status") == "healthy":
                return True
            else:
                logger.warning(f"Agent health check failed: {health_data}")
                return False
    except requests.RequestException:
        # If HTTP fails, try TCP socket connection
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect((host, port))
                return True
        except (socket.timeout, ConnectionRefusedError):
            logger.warning(f"Agent health check failed: {host}:{port}")
            return False
    
    return False

def main():
    """Main entry point for the container healthcheck script."""
    # Get the container group from environment
    container_group = os.environ.get("CONTAINER_GROUP")
    if not container_group:
        logger.error("CONTAINER_GROUP environment variable not set")
        sys.exit(1)

    # Load startup config
    config = load_startup_config()
    if not config:
        sys.exit(1)

    # Get agents for the current container group
    agents = config.get("agent_groups", {}).get(container_group, {})
    if not agents:
        logger.error(f"No agents found for container group: {container_group}")
        sys.exit(1)

    # Check each agent's health
    healthy_agents = 0
    required_healthy_agents = 0

    for agent_name, agent_config in agents.items():
        if agent_config.get("required", False):
            required_healthy_agents += 1
            host = get_env("BIND_ADDRESS", "0.0.0.0")  # Since we're checking from inside the container
            health_check_port = agent_config.get("health_check_port")
            
            if health_check_port and check_agent_health(host, health_check_port):
                logger.info(f"Agent {agent_name} is healthy")
                healthy_agents += 1
            else:
                logger.error(f"Agent {agent_name} health check failed")

    # If at least one required agent is healthy, the container is considered healthy
    if healthy_agents > 0:
        logger.info(f"Container {container_group} is healthy: {healthy_agents}/{required_healthy_agents} required agents are healthy")
        sys.exit(0)
    else:
        logger.error(f"Container {container_group} is unhealthy: no required agents are healthy")
        sys.exit(1)

if __name__ == "__main__":
    main() 