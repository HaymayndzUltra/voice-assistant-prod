#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Auto Fix Health Checks
=====================

This script automatically fixes health check issues by:
1. Killing any zombie ZMQ socket processes
2. Releasing ports that might be in TIME_WAIT state
3. Restarting key agents with proper socket cleanup

Usage:
    python auto_fix_health_checks.py [--restart-agents]

Options:
    --restart-agents    Restart all agents after applying fixes
"""

import os
import sys
import time
import argparse
import subprocess
import logging
import socket
import json
import signal
import psutil
from pathlib import Path
from common.env_helpers import get_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HealthCheckFixer")

# Port information from agent_ports.py
AGENT_PORTS = {
    "TaskRouter": 5571,
    "EnhancedModelRouter": 8570,
    "ChainOfThought": 5612, 
    "CognitiveModel": 5600,
    "TinyLlama": 5615,
    "RemoteConnector": 5557,
    "ConsolidatedTranslator": 5563
}

def check_port_in_use(port):
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_process_by_port(port):
    """Kill any process using the specified port."""
    try:
        if os.name == 'nt':  # Windows
            output = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True).decode()
            if output:
                # The last column is the PID
                pid = output.strip().split()[-1]
                try:
                    subprocess.check_output(f'taskkill /F /PID {pid}', shell=True)
                    logger.info(f"Killed process {pid} using port {port}")
                    return True
                except subprocess.CalledProcessError:
                    logger.warning(f"Failed to kill process {pid}")
        else:  # Linux/Unix
            output = subprocess.check_output(f'lsof -i :{port} -t', shell=True).decode()
            if output:
                pid = output.strip()
                os.kill(int(pid), signal.SIGKILL)
                logger.info(f"Killed process {pid} using port {port}")
                return True
    except (subprocess.CalledProcessError, ValueError, ProcessLookupError):
        pass
    return False

def release_port(port):
    """Release a port that might be in TIME_WAIT state."""
    if check_port_in_use(port):
        logger.info(f"Port {port} is in use, attempting to release...")
        if kill_process_by_port(port):
            time.sleep(1)  # Give the OS time to release the port
            if not check_port_in_use(port):
                logger.info(f"Successfully released port {port}")
                return True
            else:
                logger.warning(f"Port {port} still in use after killing process")
        else:
            logger.warning(f"No process found using port {port}")
    else:
        logger.info(f"Port {port} is already free")
        return True
    return False

def find_agent_script(agent_name):
    """Find the script file for an agent."""
    base_dir = Path(__file__).parent.parent
    
    # Common locations for agent scripts
    search_dirs = [
        base_dir / "src" / "agents",
        base_dir / "agents",
        base_dir / "FORMAINPC",
        base_dir / "agents" / "core_memory",
        base_dir / "src" / "memory",
        base_dir / "ForPC2",
        base_dir / "src" / "core"
    ]
    
    # Map agent names to actual filenames
    name_mapping = {
        "PredictiveHealthMonitor": ["predictive_health_monitor.py"],
        "TaskRouter": ["task_router.py"],
        "ChainOfThought": ["ChainOfThoughtAgent.py"],
        "CognitiveModel": ["CognitiveModelAgent.py"],
        "TinyLlama": ["TinyLlamaServiceEnhanced.py"],
        "RemoteConnector": ["remote_connector_agent.py"],
        "ConsolidatedTranslator": ["consolidated_translator.py"]
    }
    
    # Use specific mapping if available
    if agent_name in name_mapping:
        filenames = name_mapping[agent_name]
    else:
        # Convert agent name to potential filenames
        filenames = [
            f"{agent_name}.py",
            f"{agent_name.lower()}.py",
            f"{agent_name}_agent.py",
            f"{agent_name.lower()}_agent.py"
        ]
    
    # Search for the agent script in all directories
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
            
        for filename in filenames:
            script_path = search_dir / filename
            if script_path.exists():
                return script_path
                
    # If specific search failed, try to find any file that contains the agent name
    logger.info(f"Trying broader search for {agent_name}...")
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
            
        for file_path in search_dir.glob("*.py"):
            if agent_name.lower() in file_path.name.lower():
                return file_path
                
    return None

def restart_agent(agent_name):
    """Restart a specific agent."""
    script_path = find_agent_script(agent_name)
    if not script_path:
        logger.warning(f"Could not find script for {agent_name}")
        return False
        
    logger.info(f"Restarting {agent_name} from {script_path}")
    
    try:
        # Use Python executable from the current environment
        python_exe = sys.executable
        
        # Start the agent in the background
        if os.name == 'nt':  # Windows
            subprocess.Popen(
                [python_exe, str(script_path)],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:  # Linux/Unix
            subprocess.Popen(
                [python_exe, str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
        
        logger.info(f"Started {agent_name}")
        return True
    except Exception as e:
        logger.error(f"Error starting {agent_name}: {e}")
        return False

def check_agent_health(agent_name, port):
    """Check if an agent is healthy."""
    try:
        try:
            import zmq
        except ImportError:
            logger.warning("ZMQ not available, cannot check agent health")
            return False
            
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, 2000)  # 2 second timeout
        socket.setsockopt(zmq.SNDTIMEO, 2000)  # 2 second timeout
        socket.connect(f"tcp://localhost:{port}")
        
        socket.send_json({"action": "health_check"})
        response = socket.recv_json()
        
        socket.close()
        context.term()
        
        return response.get("status") == "healthy"
    except Exception as e:
        logger.warning(f"Health check failed for {agent_name}: {e}")
        return False

def fix_port_issues():
    """Fix issues with ports used by agents."""
    fixed_count = 0
    
    for agent_name, port in AGENT_PORTS.items():
        logger.info(f"Checking port {port} for {agent_name}...")
        if release_port(port):
            fixed_count += 1
    
    return fixed_count

def restart_key_agents():
    """Restart key agents in the correct order."""
    restart_order = [
        "PredictiveHealthMonitor",
        "TaskRouter",
        "EnhancedModelRouter",
        "ChainOfThought",
        "CognitiveModel", 
        "TinyLlama",
        "RemoteConnector",
        "ConsolidatedTranslator"
    ]
    
    success_count = 0
    
    for agent_name in restart_order:
        if restart_agent(agent_name):
            success_count += 1
            # Give agent time to initialize
            time.sleep(3)
    
    return success_count

def main():
    parser = argparse.ArgumentParser(description="Auto fix health check issues")
    parser.add_argument("--restart-agents", action="store_true", help="Restart agents after fixing issues")
    args = parser.parse_args()
    
    logger.info("Starting auto health check fixer...")
    
    fixed_count = fix_port_issues()
    logger.info(f"Fixed {fixed_count} port issues")
    
    if args.restart_agents:
        logger.info("Restarting key agents...")
        restarted = restart_key_agents()
        logger.info(f"Restarted {restarted} agents")
        
        # Wait for agents to initialize
        logger.info("Waiting for agents to initialize (20 seconds)...")
        time.sleep(20)
        
        # Check agent health
        try:
            import zmq
    except ImportError as e:
        print(f"Import error: {e}")
            healthy_count = 0
            for agent_name, port in AGENT_PORTS.items():
                if check_agent_health(agent_name, port):
                    healthy_count += 1
                    logger.info(f"{agent_name} is healthy")
                else:
                    logger.warning(f"{agent_name} is still unhealthy")
            
            logger.info(f"{healthy_count}/{len(AGENT_PORTS)} agents are now healthy")
        except ImportError:
            logger.warning("ZMQ not available, cannot check agent health")
    
    logger.info("Auto health check fixer completed")

if __name__ == "__main__":
    main() 