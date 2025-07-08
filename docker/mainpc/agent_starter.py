#!/usr/bin/env python3
"""
Agent starter script for Podman containerized deployment.
This script starts all agents for a specified container group.
"""

import os
import sys
import yaml
import time
import signal
import logging
import subprocess
from pathlib import Path
import multiprocessing as mp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("agent_starter")

# Global process list for cleanup
processes = []

def load_startup_config():
    """Load the startup configuration."""
    config_path = Path("/app/main_pc_code/config/startup_config.yaml")
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Failed to load startup config: {e}")
        sys.exit(1)

def start_agent(agent_name, script_path):
    """Start an agent process."""
    logger.info(f"Starting agent: {agent_name} from {script_path}")
    
    try:
        # Convert relative path to absolute path
        if not script_path.startswith('/'):
            script_path = f"/app/{script_path}"
            
        # Run the agent as a Python module
        process = subprocess.Popen(
            ["python", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Start log monitoring threads
        mp.Process(target=log_monitor, args=(agent_name, process.stdout, False)).start()
        mp.Process(target=log_monitor, args=(agent_name, process.stderr, True)).start()
        
        return process
    except Exception as e:
        logger.error(f"Failed to start agent {agent_name}: {e}")
        return None

def log_monitor(agent_name, pipe, is_stderr):
    """Monitor and log output from an agent."""
    prefix = f"[{agent_name}] "
    log_func = logger.error if is_stderr else logger.info
    
    try:
        for line in pipe:
            log_func(f"{prefix}{line.strip()}")
    except Exception as e:
        logger.error(f"Log monitor failed for {agent_name}: {e}")
    finally:
        pipe.close()

def cleanup(signum=None, frame=None):
    """Clean up all started processes when exiting."""
    logger.info("Cleaning up agent processes...")
    
    for process in processes:
        try:
            if process.poll() is None:  # If process is still running
                process.terminate()
                time.sleep(0.5)
                if process.poll() is None:  # If still running after terminate
                    process.kill()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    logger.info("All agent processes terminated")
    sys.exit(0)

def main():
    """Main entry point for the agent starter script."""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)
    
    # Get the container group from environment
    container_group = os.environ.get("CONTAINER_GROUP")
    if not container_group:
        logger.error("CONTAINER_GROUP environment variable not set")
        sys.exit(1)
    
    logger.info(f"Starting agents for container group: {container_group}")
    
    # Load startup config
    config = load_startup_config()
    if not config:
        sys.exit(1)
    
    # Get agents for the current container group
    agents = config.get("agent_groups", {}).get(container_group, {})
    if not agents:
        logger.error(f"No agents found for container group: {container_group}")
        sys.exit(1)
    
    # Start each agent
    global processes
    for agent_name, agent_config in agents.items():
        script_path = agent_config.get("script_path")
        if not script_path:
            logger.error(f"Script path not defined for agent {agent_name}")
            continue
        
        process = start_agent(agent_name, script_path)
        if process:
            processes.append(process)
    
    logger.info(f"Started {len(processes)} agents for container group {container_group}")
    
    # Keep the script running to maintain the child processes
    try:
        while True:
            # Check if any process has terminated
            for i, process in enumerate(processes[:]):
                if process.poll() is not None:
                    exit_code = process.returncode
                    logger.error(f"Agent process terminated with exit code {exit_code}")
                    processes.pop(i)
                    
            # If all processes have terminated, exit
            if not processes:
                logger.error("All agents have terminated, exiting")
                sys.exit(1)
                
            time.sleep(10)  # Check every 10 seconds
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main() 