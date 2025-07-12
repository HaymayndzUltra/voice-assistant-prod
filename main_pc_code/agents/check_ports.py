#!/usr/bin/env python3
"""
Check if ports can be bound to by ZMQ
"""

import zmq
import yaml
import os
import sys
from pathlib import Path


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", ".."))))
from common.utils.path_env import get_path, join_path, get_file_path
# ANSI color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def load_config():
    """Load the MVS configuration"""
    config_path = join_path("main_pc_code", "NEWMUSTFOLLOW/minimal_system_config_local.yaml")
    if not os.path.exists(config_path):
        print(f"Config file not found: {config_path}")
        return None
        
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return None

def test_port(port):
    """Test if a port can be bound to by ZMQ"""
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    try:
        socket.bind(f"tcp://*:{port}")
        socket.close()
        context.term()
        return True
    except zmq.error.ZMQError as e:
        print(f"Failed to bind to port {port}: {e}")
        socket.close()
        context.term()
        return False

def main():
    """Main function"""
    print(f"{BLUE}{BOLD}Port Binding Test{RESET}")
    
    # Load configuration
    config = load_config()
    if not config:
        print(f"{RED}Failed to load configuration{RESET}")
        return
    
    # Combine core agents and dependencies
    all_agents = []
    if 'core_agents' in config:
        all_agents.extend(config['core_agents'])
    if 'dependencies' in config:
        all_agents.extend(config['dependencies'])
    
    # Test each agent's port
    for agent_config in all_agents:
        name = agent_config.get('name')
        port = agent_config.get('port')
        
        if port is None:
            print(f"{YELLOW}Agent {name} has no port specified{RESET}")
            continue
        
        # Test main port
        if test_port(port):
            print(f"{GREEN}✓{RESET} Agent {name} port {port} is available")
        else:
            print(f"{RED}✗{RESET} Agent {name} port {port} is NOT available")
        
        # Test health check port (port + 1)
        health_port = port + 1
        if test_port(health_port):
            print(f"{GREEN}✓{RESET} Agent {name} health port {health_port} is available")
        else:
            print(f"{RED}✗{RESET} Agent {name} health port {health_port} is NOT available")
        
        print()

if __name__ == "__main__":
    main()
