#!/usr/bin/env python3

"""
MVS Launcher - Improved Version
------------------------------
Launches the Minimal Viable System agents with proper error handling and path resolution.
"""

import os
import sys
import yaml
import time
import signal
import subprocess
import argparse
from pathlib import Path
import logging
import threading


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, get_project_root())
from common.utils.path_manager import PathManager
# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(PathManager.get_logs_dir() / "mvs_launcher.log"))
    ]
)

# ANSI color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

# Global process list for cleanup
processes = []
running = True

def find_config_file():
    """Find the minimal system configuration file."""
    possible_paths = [
        os.path.join(SCRIPT_DIR, "minimal_system_config.yaml"),
        PathManager.join_path("config", PathManager.join_path("config", "minimal_system_config.yaml")),
        PathManager.join_path("main_pc_code", PathManager.join_path("config", "minimal_system_config.yaml")),
        PathManager.join_path("main_pc_code", "NEWMUSTFOLLOW/minimal_system_config.yaml"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            logging.info(f"Found config at: {path}")
            return path
    
    logging.error(f"Could not find minimal_system_config.yaml in any of these locations:")
    for path in possible_paths:
        logging.error(f"  - {path}")
    return None

def load_config():
    """Load the MVS configuration."""
    config_path = find_config_file()
    if not config_path:
        logging.error("Failed to find configuration file")
        sys.exit(1)
        
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        sys.exit(1)

def find_agent_file(agent_name):
    """Find the Python file for an agent."""
    possible_locations = [
        PathManager.join_path("main_pc_code", "agents/{agent_name}.py"),
        PathManager.join_path("main_pc_code", "src/agents/{agent_name}.py"),
        os.path.join(PROJECT_ROOT, "src", "agents", f"{agent_name}.py"),
    ]
    
    for location in possible_locations:
        if os.path.exists(location):
            return location
    
    return None

def launch_agent(agent_config):
    """Launch a single agent."""
    name = agent_config.get('name')
    file_path = agent_config.get('file_path')
    port = agent_config.get('port')
    
    if not name:
        logging.error("Agent missing name in config")
        return False
    
    if not file_path:
        # Try to find the file based on the agent name
        file_path = find_agent_file(name)
        if not file_path:
            logging.error(f"Could not find file for agent: {name}")
            return False
    
    if not os.path.exists(file_path):
        logging.error(f"Agent file not found: {file_path}")
        return False
    
    try:
        # Prepare environment variables
        env = os.environ.copy()
        if port:
            env['AGENT_PORT'] = str(port)
        
        # Start the agent process
        logging.info(f"Launching {name} from {file_path}")
        process = subprocess.Popen(
            [sys.executable, file_path],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        processes.append({
            'name': name,
            'process': process,
            'file_path': file_path
        })
        
        # Start threads to monitor output
        threading.Thread(target=monitor_output, args=(process.stdout, name, False), daemon=True).start()
        threading.Thread(target=monitor_output, args=(process.stderr, name, True), daemon=True).start()
        
        return True
    except Exception as e:
        logging.error(f"Error launching agent {name}: {e}")
        return False

def monitor_output(pipe, agent_name, is_stderr):
    """Monitor and log output from an agent process."""
    prefix = f"{RED}[{agent_name} ERR]{RESET}" if is_stderr else f"{GREEN}[{agent_name}]{RESET}"
    
    for line in pipe:
        line = line.strip()
        if line:
            print(f"{prefix} {line}")
    
    if is_stderr:
        logging.warning(f"Agent {agent_name} stderr stream closed")
    else:
        logging.info(f"Agent {agent_name} stdout stream closed")

def launch_mvs():
    """Launch all agents in the Minimal Viable System."""
    config = load_config()
    
    # Launch core agents first
    core_agents = config.get('core_agents', [])
    logging.info(f"Launching {len(core_agents)} core agents...")
    
    for agent in core_agents:
        success = launch_agent(agent)
        if not success:
            logging.warning(f"Failed to launch core agent: {agent.get('name')}")
        time.sleep(1)  # Small delay between launching agents
    
    # Then launch dependencies
    dependencies = config.get('dependencies', [])
    logging.info(f"Launching {len(dependencies)} dependency agents...")
    
    for agent in dependencies:
        success = launch_agent(agent)
        if not success:
            logging.warning(f"Failed to launch dependency agent: {agent.get('name')}")
        time.sleep(1)  # Small delay between launching agents
    
    logging.info(f"Launched {len(processes)} agents successfully")
    return len(processes) > 0

def cleanup():
    """Clean up all launched processes."""
    logging.info("Cleaning up processes...")
    for p_info in processes:
        try:
            process = p_info['process']
            name = p_info['name']
            if process.poll() is None:  # Process is still running
                logging.info(f"Terminating {name}...")
                process.terminate()
                process.wait(timeout=5)
        except Exception as e:
            logging.error(f"Error terminating process: {e}")
    
    # Force kill any remaining processes
    for p_info in processes:
        try:
            process = p_info['process']
            name = p_info['name']
            if process.poll() is None:  # Process is still running
                logging.warning(f"Force killing {name}...")
                process.kill()
        except Exception as e:
            logging.error(f"Error killing process: {e}")

def signal_handler(sig, frame):
    """Handle interrupt signals."""
    global running
    logging.info("Interrupt received, shutting down...")
    running = False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Launch the Minimal Viable System")
    parser.add_argument("--check-only", action="store_true", help="Only check if agents can be launched without actually starting them")
    args = parser.parse_args()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        print(f"{BLUE}{BOLD}MVS Launcher - Improved Version{RESET}")
        print(f"{YELLOW}Press Ctrl+C to stop all agents{RESET}\n")
        
        if args.check_only:
            logging.info("Running in check-only mode")
            config = load_config()
            all_agents = []
            if 'core_agents' in config:
                all_agents.extend(config['core_agents'])
            if 'dependencies' in config:
                all_agents.extend(config['dependencies'])
            
            all_valid = True
            for agent in all_agents:
                name = agent.get('name', 'Unknown')
                file_path = agent.get('file_path')
                if not file_path:
                    file_path = find_agent_file(name)
                
                if file_path and os.path.exists(file_path):
                    print(f"[{GREEN}✓{RESET}] {name}: {file_path}")
                else:
                    print(f"[{RED}✗{RESET}] {name}: File not found")
                    all_valid = False
            
            if all_valid:
                print(f"\n{GREEN}{BOLD}All agent files found!{RESET}")
                return 0
            else:
                print(f"\n{RED}{BOLD}Some agent files are missing!{RESET}")
                return 1
        
        # Launch all agents
        success = launch_mvs()
        if not success:
            logging.error("Failed to launch any agents")
            return 1
        
        # Keep the main thread running
        while running:
            time.sleep(1)
            
            # Check if any processes have died
            for p_info in list(processes):
                process = p_info['process']
                name = p_info['name']
                if process.poll() is not None:
                    logging.warning(f"Agent {name} exited with code {process.returncode}")
                    processes.remove(p_info)
            
            if not processes:
                logging.error("All processes have terminated")
                running = False
        
        return 0
    except Exception as e:
        logging.error(f"Error in main: {e}", exc_info=True)
        return 1
    finally:
        cleanup()

if __name__ == "__main__":
    sys.exit(main()) 