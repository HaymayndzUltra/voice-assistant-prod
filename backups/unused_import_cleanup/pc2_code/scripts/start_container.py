#!/usr/bin/env python3
"""
Container Start Script

This script starts agents within a container based on the container group.
It reads the startup configuration and launches the appropriate agents.
"""

import os
import sys
import yaml
import subprocess
import time
import signal
import threading
import logging
from pathlib import Path


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
        logging.FileHandler(PathManager.join_path("logs", str(PathManager.get_logs_dir() / "container_start.log")))
    ]
)
logger = logging.getLogger("container_start")

def load_config():
    """Load the startup configuration."""
    config_path = PathManager.join_path("pc2_code", PathManager.join_path("config", "startup_config.yaml"))
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return None

def get_container_agents(config, container_group):
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

def start_agent(agent):
    """Start a single agent."""
    script_path = agent["script_path"]
    if not os.path.exists(script_path):
        logger.error(f"Agent script not found: {script_path}")
        return None
        
    cmd = ["python", script_path]
    
    # Add environment variables
    env = os.environ.copy()
    env["AGENT_NAME"] = agent["name"]
    env["AGENT_PORT"] = str(agent["port"])
    env["HEALTH_CHECK_PORT"] = str(agent["health_check_port"])
    env["BIND_ADDRESS"] = agent.get("host", "0.0.0.0")
    
    # Start the agent
    logger.info(f"Starting agent: {agent['name']} on port {agent['port']}")
    try:
        return subprocess.Popen(cmd, env=env)
    except Exception as e:
        logger.error(f"Error starting agent {agent['name']}: {e}")
        return None

def monitor_agent(name, process, restart_callback):
    """Monitor an agent process and restart if it fails."""
    while True:
        exit_code = process.wait()
        if exit_code != 0:
            logger.warning(f"Agent {name} exited with code {exit_code}, restarting...")
            restart_callback()
        else:
            logger.info(f"Agent {name} exited normally")
            break

def main():
    if len(sys.argv) < 2:
        logger.error("Usage: python start_container.py <container_group>")
        sys.exit(1)
    
    container_group = sys.argv[1]
    logger.info(f"Starting container group: {container_group}")
    
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        sys.exit(1)
        
    agents = get_container_agents(config, container_group)
    
    if not agents:
        logger.error(f"No agents found for container group: {container_group}")
        sys.exit(1)
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Start agents
    processes = []
    for agent in agents:
        proc = start_agent(agent)
        if proc:
            processes.append((agent["name"], proc, agent))
    
    if not processes:
        logger.error("Failed to start any agents")
        sys.exit(1)
    
    # Handle signals
    def signal_handler(sig, frame):
        logger.info("Shutting down agents...")
        for name, proc, _ in processes:
            logger.info(f"Stopping {name}...")
            proc.terminate()
        
        # Give processes time to terminate gracefully
        time.sleep(2)
        
        # Force kill any remaining processes
        for name, proc, _ in processes:
            if proc.poll() is None:
                logger.warning(f"Force killing {name}...")
                proc.kill()
                
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Monitor processes
    monitor_threads = []
    for i, (name, proc, agent) in enumerate(processes):
        def restart_callback(index=i, agent_info=agent):
            nonlocal processes
            logger.info(f"Restarting agent {agent_info['name']}...")
            new_proc = start_agent(agent_info)
            if new_proc:
                processes[index] = (agent_info["name"], new_proc, agent_info)
                # Start a new monitor thread
                thread = threading.Thread(
                    target=monitor_agent,
                    args=(agent_info["name"], new_proc, lambda: restart_callback(index, agent_info)),
                    daemon=True
                )
                thread.start()
        
        thread = threading.Thread(
            target=monitor_agent,
            args=(name, proc, lambda idx=i, a=agent: restart_callback(idx, a)),
            daemon=True
        )
        thread.start()
        monitor_threads.append(thread)
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
            # Check if all processes are still running
            all_running = True
            for name, proc, _ in processes:
                if proc.poll() is not None:
                    all_running = False
                    break
            
            if not all_running:
                logger.warning("One or more agents have stopped running")
            
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main() 