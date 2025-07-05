#!/usr/bin/env python3
"""
Layer 0 Agent Launcher with Improved Error Handling
"""

import os
import sys
import time
import yaml
import subprocess
import signal
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('layer0_launcher.log')
    ]
)
logger = logging.getLogger("Layer0Launcher")

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Global process list for cleanup
processes = []

def load_config():
    """Load the MVS configuration"""
    config_path = os.path.join(SCRIPT_DIR, "main_pc_code", "NEWMUSTFOLLOW", "minimal_system_config_local.yaml")
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        return None
        
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return None

def setup_environment():
    """Set up the environment variables needed for the agents"""
    # Create necessary directories
    for directory in ["logs", "data", "models", "cache", "certificates"]:
        os.makedirs(directory, exist_ok=True)
    
    # Machine configuration
    os.environ["MACHINE_TYPE"] = "MAINPC"
    os.environ["PYTHONPATH"] = f"{os.environ.get('PYTHONPATH', '')}:{SCRIPT_DIR}"
    
    # Network configuration
    os.environ["MAIN_PC_IP"] = "localhost"
    os.environ["PC2_IP"] = "localhost"
    os.environ["BIND_ADDRESS"] = "0.0.0.0"
    
    # Security settings
    os.environ["SECURE_ZMQ"] = "0"  # Disable secure ZMQ for initial testing
    
    # Dummy audio for testing
    os.environ["USE_DUMMY_AUDIO"] = "true"
    
    # Timeouts and retries
    os.environ["ZMQ_REQUEST_TIMEOUT"] = "10000"  # Increase timeout to 10 seconds
    os.environ["CONNECTION_RETRIES"] = "5"
    os.environ["SERVICE_DISCOVERY_TIMEOUT"] = "15000"

def launch_agent(agent_config):
    """Launch a single agent"""
    name = agent_config.get('name')
    file_path = agent_config.get('file_path')
    
    if not file_path:
        logger.error(f"No file path specified for {name}")
        return None
    
    # Determine the full path to the agent file
    if os.path.isabs(file_path):
        full_path = file_path
    else:
        # Try multiple possible locations
        search_dirs = [
            os.path.join(SCRIPT_DIR, "main_pc_code", "agents"),
            os.path.join(SCRIPT_DIR, "main_pc_code", "FORMAINPC"),
            os.path.join(SCRIPT_DIR, "main_pc_code", "src", "core"),
            os.path.join(SCRIPT_DIR, "main_pc_code", "src", "memory"),
            os.path.join(SCRIPT_DIR, "main_pc_code", "src", "audio"),
            os.path.join(SCRIPT_DIR, "main_pc_code"),
            SCRIPT_DIR
        ]
        
        for directory in search_dirs:
            candidate_path = os.path.join(directory, file_path)
            if os.path.exists(candidate_path):
                full_path = candidate_path
                break
        else:
            logger.error(f"Could not find {file_path} for {name}")
            return None
    
    # Launch the agent
    try:
        cmd = [sys.executable, full_path]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        logger.info(f"Launched {name} (PID: {process.pid})")
        return process
    except Exception as e:
        logger.error(f"Failed to launch {name}: {e}")
        return None

def main():
    """Main function"""
    # Setup environment
    setup_environment()
    
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return
    
    # Launch agents
    all_agents = []
    if 'core_agents' in config:
        all_agents.extend(config['core_agents'])
    if 'dependencies' in config:
        all_agents.extend(config['dependencies'])
    
    for agent_config in all_agents:
        name = agent_config.get('name')
        process = launch_agent(agent_config)
        if process:
            processes.append((name, process))
            print(f"Started {name}")
            time.sleep(2)  # Give each agent time to start
        else:
            print(f"Failed to start {name}")
    
    print(f"Launched {len(processes)} agents")
    
    # Wait for user to press Ctrl+C
    try:
        print("Press Ctrl+C to stop all agents")
        while True:
            time.sleep(1)
            
            # Check if any processes have terminated
            for name, process in list(processes):
                if process.poll() is not None:
                    print(f"Agent {name} has terminated with code {process.returncode}")
                    processes.remove((name, process))
            
            if not processes:
                print("All agents have terminated")
                break
    except KeyboardInterrupt:
        print("Stopping all agents...")
        for name, process in processes:
            print(f"Stopping {name}...")
            try:
                process.terminate()
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
    
    print("All agents stopped")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
