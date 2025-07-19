#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Layer 0 Agent Debug Script

This script launches each Layer 0 agent individually with stdout/stderr capture
to diagnose the exact errors causing them to terminate.
"""

import os
import sys
import time
import yaml
import subprocess
import logging
import threading
import queue
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('agent_debug.log')
    ]
)
logger = logging.getLogger("AgentDebug")

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
    
    # Debug mode
    os.environ["DEBUG"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"

def find_agent_file(file_path):
    """Find the full path to an agent file"""
    if os.path.isabs(file_path):
        return file_path if os.path.exists(file_path) else None
    
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
            return candidate_path
    
    return None

def output_reader(pipe, queue):
    """Read output from a pipe and put it in a queue"""
    try:
        for line in iter(pipe.readline, b''):
            queue.put(line.decode('utf-8', errors='replace').rstrip())
    except Exception as e:
        queue.put(f"Error reading output: {e}")
    finally:
        queue.put(None)  # Signal that the reader has finished

def debug_agent(agent_config):
    """Debug a single agent by capturing its output"""
    name = agent_config.get('name')
    file_path = agent_config.get('file_path')
    
    if not file_path:
        print(f"{RED}No file path specified for {name}{RESET}")
        return False
    
    full_path = find_agent_file(file_path)
    if not full_path:
        print(f"{RED}Could not find {file_path} for {name}{RESET}")
        return False
    
    print(f"\n{BLUE}{BOLD}Debugging {name} ({full_path}){RESET}")
    print("-" * 80)
    
    # Create output queues
    stdout_queue = queue.Queue()
    stderr_queue = queue.Queue()
    
    # Launch the agent
    try:
        process = subprocess.Popen(
            [sys.executable, full_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            universal_newlines=False
        )
        
        # Start output reader threads
        stdout_thread = threading.Thread(target=output_reader, args=(process.stdout, stdout_queue))
        stderr_thread = threading.Thread(target=output_reader, args=(process.stderr, stderr_queue))
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()
        
        # Wait for output or process termination
        timeout = 15  # seconds
        start_time = time.time()
        
        stdout_lines = []
        stderr_lines = []
        stdout_done = False
        stderr_done = False
        
        while time.time() - start_time < timeout and process.poll() is None:
            # Check stdout
            try:
                if not stdout_done:
                    line = stdout_queue.get(block=False, timeout=0.1)
                    if line is None:
                        stdout_done = True
                    else:
                        stdout_lines.append(line)
                        print(f"{GREEN}[STDOUT]{RESET} {line}")
            except queue.Empty:
                pass
            
            # Check stderr
            try:
                if not stderr_done:
                    line = stderr_queue.get(block=False, timeout=0.1)
                    if line is None:
                        stderr_done = True
                    else:
                        stderr_lines.append(line)
                        print(f"{RED}[STDERR]{RESET} {line}")
            except queue.Empty:
                pass
            
            time.sleep(0.1)
        
        # Check if the process terminated
        if process.poll() is not None:
            exit_code = process.returncode
            print(f"\n{YELLOW}Process terminated with exit code {exit_code}{RESET}")
        else:
            print(f"\n{YELLOW}Process still running after {timeout} seconds, terminating...{RESET}")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"{RED}Process killed forcefully{RESET}")
        
        # Drain remaining output
        while not (stdout_done and stderr_done):
            try:
                if not stdout_done:
                    line = stdout_queue.get(block=False)
                    if line is None:
                        stdout_done = True
                    else:
                        stdout_lines.append(line)
                        print(f"{GREEN}[STDOUT]{RESET} {line}")
            except queue.Empty:
                pass
            
            try:
                if not stderr_done:
                    line = stderr_queue.get(block=False)
                    if line is None:
                        stderr_done = True
                    else:
                        stderr_lines.append(line)
                        print(f"{RED}[STDERR]{RESET} {line}")
            except queue.Empty:
                pass
            
            time.sleep(0.1)
        
        # Analyze the output for common errors
        print("\n" + "-" * 80)
        print(f"{BLUE}{BOLD}Analysis for {name}:{RESET}")
        
        error_found = False
        
        # Check for ZMQ errors
        zmq_errors = [line for line in stderr_lines if "zmq" in line.lower() or "socket" in line.lower()]
        if zmq_errors:
            print(f"{RED}ZMQ/Socket errors detected:{RESET}")
            for error in zmq_errors:
                print(f"  - {error}")
            error_found = True
        
        # Check for import errors
        import_errors = [line for line in stderr_lines if "import" in line.lower() and "error" in line.lower()]
        if import_errors:
            print(f"{RED}Import errors detected:{RESET}")
            for error in import_errors:
                print(f"  - {error}")
            error_found = True
        
        # Check for file not found errors
        file_errors = [line for line in stderr_lines if "no such file" in line.lower() or "filenotfound" in line.lower()]
        if file_errors:
            print(f"{RED}File not found errors detected:{RESET}")
            for error in file_errors:
                print(f"  - {error}")
            error_found = True
        
        # Check for permission errors
        perm_errors = [line for line in stderr_lines if "permission" in line.lower()]
        if perm_errors:
            print(f"{RED}Permission errors detected:{RESET}")
            for error in perm_errors:
                print(f"  - {error}")
            error_found = True
        
        # If no specific errors found but stderr has content
        if not error_found and stderr_lines:
            print(f"{RED}Other errors detected:{RESET}")
            for line in stderr_lines[-5:]:  # Show the last 5 lines
                print(f"  - {line}")
        
        # If no errors found at all
        if not error_found and not stderr_lines:
            print(f"{GREEN}No errors detected in stderr.{RESET}")
            if stdout_lines:
                print(f"{YELLOW}Last stdout messages:{RESET}")
                for line in stdout_lines[-5:]:  # Show the last 5 lines
                    print(f"  - {line}")
        
        return True
    except Exception as e:
        print(f"{RED}Error debugging {name}: {e}{RESET}")
        return False

def main():
    """Main function"""
    print(f"{BLUE}{BOLD}Layer 0 Agent Debug Tool{RESET}")
    
    # Setup environment
    setup_environment()
    
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
    
    # Debug each agent
    for agent_config in all_agents:
        debug_agent(agent_config)
        print("\n" + "=" * 80)
    
    print(f"\n{GREEN}{BOLD}Debug session completed{RESET}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted by user{RESET}")
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"{RED}Error: {e}{RESET}")
