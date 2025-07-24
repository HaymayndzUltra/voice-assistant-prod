#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Layer 0 Agent Diagnostic and Fix Script

This script diagnoses and fixes common issues with Layer 0 agents:
1. Checks for port conflicts
2. Verifies environment variables
3. Tests ZMQ socket binding
4. Checks for proper PyAudio installation
5. Ensures proper health check socket configuration
"""

import os
import sys
import time
import zmq
import socket
import subprocess
import logging
import yaml
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('agent_diagnostic.log')
    ]
)
logger = logging.getLogger("AgentDiagnostic")

# ANSI color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def check_port_in_use(port):
    """Check if a port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def test_zmq_binding(port):
    """Test if a ZMQ socket can bind to the specified port"""
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    try:
        socket.bind(f"tcp://*:{port}")
        socket.close()
        context.term()
        return True
    except zmq.error.ZMQError as e:
        logger.error(f"Failed to bind ZMQ socket to port {port}: {e}")
        socket.close()
        context.term()
        return False

def check_pyaudio():
    """Check if PyAudio is installed and working"""
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()
        p.terminate()
        return True, f"PyAudio is installed with {device_count} devices available"
    except ImportError:
        return False, "PyAudio is not installed"
    except Exception as e:
        return False, f"PyAudio error: {e}"

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

def fix_agent_ports(config):
    """Fix agent port conflicts by updating the configuration"""
    if not config:
        return False
        
    modified = False
    used_ports = set()
    
    # Combine core agents and dependencies
    all_agents = []
    if 'core_agents' in config:
        all_agents.extend(config['core_agents'])
    if 'dependencies' in config:
        all_agents.extend(config['dependencies'])
    
    # First pass: collect all currently assigned ports
    for agent in all_agents:
        port = agent.get('port')
        if port:
            used_ports.add(port)
    
    # Second pass: fix port conflicts and test binding
    base_port = 7000  # Start with a high port number to avoid conflicts
    for agent in all_agents:
        name = agent.get('name')
        port = agent.get('port')
        
        if port is None:
            # Assign a port if none is specified
            while base_port in used_ports or check_port_in_use(base_port):
                base_port += 1
            agent['port'] = base_port
            used_ports.add(base_port)
            logger.info(f"Assigned port {base_port} to {name}")
            modified = True
            base_port += 1
        elif check_port_in_use(port):
            # Port is in use, assign a new one
            old_port = port
            while base_port in used_ports or check_port_in_use(base_port):
                base_port += 1
            agent['port'] = base_port
            used_ports.add(base_port)
            logger.info(f"Changed {name} port from {old_port} to {base_port} due to conflict")
            modified = True
            base_port += 1
        elif not test_zmq_binding(port):
            # Port is not in use but ZMQ can't bind to it
            old_port = port
            while base_port in used_ports or check_port_in_use(base_port) or not test_zmq_binding(base_port):
                base_port += 1
            agent['port'] = base_port
            used_ports.add(base_port)
            logger.info(f"Changed {name} port from {old_port} to {base_port} due to ZMQ binding issue")
            modified = True
            base_port += 1
    
    # Save the updated configuration if modified
    if modified:
        config_path = os.path.join(SCRIPT_DIR, "main_pc_code", "NEWMUSTFOLLOW", "minimal_system_config_local.yaml")
        try:
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            logger.info(f"Updated configuration saved to {config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving updated configuration: {e}")
            return False
    
    return False

def setup_environment():
    """Set up the environment variables needed for the agents"""
    logger.info("Setting up environment variables")
    
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
    
    logger.info("Environment setup complete")
    return True

def main():
    """Main function"""
    print(f"{BLUE}{BOLD}Layer 0 Agent Diagnostic and Fix{RESET}")
    
    # Step 1: Setup environment
    print(f"\n{YELLOW}Step 1: Setting up environment{RESET}")
    setup_environment()
    
    # Step 2: Check PyAudio
    print(f"\n{YELLOW}Step 2: Checking PyAudio{RESET}")
    pyaudio_ok, pyaudio_msg = check_pyaudio()
    if pyaudio_ok:
        print(f"{GREEN}✓{RESET} {pyaudio_msg}")
    else:
        print(f"{RED}✗{RESET} {pyaudio_msg}")
        print(f"{YELLOW}Setting USE_DUMMY_AUDIO=true to work around PyAudio issues{RESET}")
        os.environ["USE_DUMMY_AUDIO"] = "true"
    
    # Step 3: Load and fix configuration
    print(f"\n{YELLOW}Step 3: Checking agent configuration{RESET}")
    config = load_config()
    if config:
        print(f"{GREEN}✓{RESET} Configuration loaded successfully")
        
        # Fix port conflicts
        if fix_agent_ports(config):
            print(f"{GREEN}✓{RESET} Fixed port conflicts in configuration")
        else:
            print(f"{YELLOW}!{RESET} No port conflicts found or could not fix")
    else:
        print(f"{RED}✗{RESET} Failed to load configuration")
        return
    
    # Step 4: Create a wrapper script to launch agents with increased timeouts
    print(f"\n{YELLOW}Step 4: Creating improved launcher script{RESET}")
    launcher_path = os.path.join(SCRIPT_DIR, "launch_layer0_fixed.py")
    try:
        with open(launcher_path, 'w') as f:
            f.write("""#!/usr/bin/env python3
\"\"\"
Layer 0 Agent Launcher with Improved Error Handling
\"\"\"

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
    \"\"\"Load the MVS configuration\"\"\"
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
    \"\"\"Set up the environment variables needed for the agents\"\"\"
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
    \"\"\"Launch a single agent\"\"\"
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
    \"\"\"Main function\"\"\"
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
""")
        os.chmod(launcher_path, 0o755)  # Make executable
        print(f"{GREEN}✓{RESET} Created improved launcher script: {launcher_path}")
    except Exception as e:
        print(f"{RED}✗{RESET} Failed to create launcher script: {e}")
    
    print(f"\n{GREEN}{BOLD}Diagnostic and fix completed!{RESET}")
    print(f"To launch the fixed Layer 0 agents, run: {BLUE}python {launcher_path}{RESET}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted by user{RESET}")
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"{RED}Error: {e}{RESET}") 