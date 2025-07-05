#!/usr/bin/env python3

"""
MVS Local Launcher
----------------
Launches the Minimal Viable System using local agent files
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

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mvs_launcher.log')
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
AGENTS_DIR = os.path.join(SCRIPT_DIR, "agents")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "minimal_system_config_local.yaml")

# Global process list for cleanup
processes = []
running = True

def load_config():
    """Load the MVS configuration."""
    if not os.path.exists(CONFIG_FILE):
        logging.error(f"Config file not found: {CONFIG_FILE}")
        sys.exit(1)
        
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        sys.exit(1)

def launch_agent(agent_config, dummy_mode=False):
    """Launch a single agent."""
    name = agent_config.get('name')
    file_name = agent_config.get('file_path')
    port = agent_config.get('port')
    
    if not name:
        logging.error("Agent missing name in config")
        return False
    
    if not file_name:
        logging.error(f"No file path specified for {name}")
        return False
    
    # Get the full path to the agent file
    file_path = os.path.join(AGENTS_DIR, file_name)
    
    if not os.path.exists(file_path):
        logging.error(f"Agent file not found: {file_path}")
        return False
    
    try:
        # Prepare environment variables
        env = os.environ.copy()
        if port:
            env['AGENT_PORT'] = str(port)
        
        # Set dummy mode if requested
        if dummy_mode:
            env['USE_DUMMY_AUDIO'] = "true"
        
        # Set PYTHONPATH to include the current directory and parent directories
        env['PYTHONPATH'] = f"{SCRIPT_DIR}:{os.path.dirname(SCRIPT_DIR)}:{os.path.dirname(os.path.dirname(SCRIPT_DIR))}:{env.get('PYTHONPATH', '')}"
        
        # Start the agent process
        logging.info(f"Launching {name} from {file_path}")
        process = subprocess.Popen(
            [sys.executable, file_path],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=SCRIPT_DIR  # Run from the script directory
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

def launch_mvs(dummy_mode=False):
    """Launch all agents in the Minimal Viable System."""
    config = load_config()
    
    # Launch core agents first
    core_agents = config.get('core_agents', [])
    logging.info(f"Launching {len(core_agents)} core agents...")
    
    for agent in core_agents:
        success = launch_agent(agent, dummy_mode)
        if not success:
            logging.warning(f"Failed to launch core agent: {agent.get('name')}")
        time.sleep(1)  # Small delay between launching agents
    
    # Then launch dependencies
    dependencies = config.get('dependencies', [])
    logging.info(f"Launching {len(dependencies)} dependency agents...")
    
    for agent in dependencies:
        success = launch_agent(agent, dummy_mode)
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
    parser = argparse.ArgumentParser(description="Launch the Minimal Viable System using local agent files")
    parser.add_argument("--check-only", action="store_true", help="Only check if agents can be launched without actually starting them")
    parser.add_argument("--agent", help="Launch only a specific agent by name")
    parser.add_argument("--dummy", action="store_true", help="Run agents in dummy mode (for audio/hardware dependencies)")
    args = parser.parse_args()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        print(f"{BLUE}{BOLD}MVS Local Launcher{RESET}")
        print(f"Using agents from: {AGENTS_DIR}")
        print(f"Using config: {CONFIG_FILE}")
        print(f"Dummy mode: {args.dummy}")
        print(f"{YELLOW}Press Ctrl+C to stop all agents{RESET}\n")
        
        config = load_config()
        all_agents = []
        if 'core_agents' in config:
            all_agents.extend(config['core_agents'])
        if 'dependencies' in config:
            all_agents.extend(config['dependencies'])
        
        if args.check_only:
            logging.info("Running in check-only mode")
            
            all_valid = True
            for agent in all_agents:
                name = agent.get('name', 'Unknown')
                file_name = agent.get('file_path')
                if not file_name:
                    print(f"[{RED}✗{RESET}] {name}: No file path specified")
                    all_valid = False
                    continue
                
                file_path = os.path.join(AGENTS_DIR, file_name)
                
                if os.path.exists(file_path):
                    print(f"[{GREEN}✓{RESET}] {name}: {file_path}")
                else:
                    print(f"[{RED}✗{RESET}] {name}: File not found at {file_path}")
                    all_valid = False
            
            if all_valid:
                print(f"\n{GREEN}{BOLD}All agent files found!{RESET}")
                return 0
            else:
                print(f"\n{RED}{BOLD}Some agent files are missing!{RESET}")
                return 1
        
        if args.agent:
            # Launch a specific agent
            agent_name = args.agent
            logging.info(f"Launching single agent: {agent_name}")
            
            target_agent = None
            for agent in all_agents:
                if agent.get('name') == agent_name:
                    target_agent = agent
                    break
            
            if not target_agent:
                logging.error(f"Agent '{agent_name}' not found in configuration")
                return 1
            
            success = launch_agent(target_agent, args.dummy)
            if not success:
                logging.error(f"Failed to launch agent: {agent_name}")
                return 1
        else:
            # Launch all agents
            success = launch_mvs(args.dummy)
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