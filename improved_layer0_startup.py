#!/usr/bin/env python3
"""
Improved Layer 0 Startup Script

This script provides a more robust way to start Layer 0 agents with:
- Better path resolution using the centralized PathManager
- Enhanced error handling and diagnostic information
- Proper socket cleanup before agent startup
- Improved process management
"""

import os
import sys
import time
import signal
import socket
import logging
import argparse
import subprocess
import threading
import yaml
import json
import zmq
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/layer0_startup.log')
    ]
)
logger = logging.getLogger('layer0_startup')

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# Global variables
running_processes = {}
stop_event = threading.Event()

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import the PathManager
try:
    from main_pc_code.utils.path_manager import PathManager
except ImportError:
    logger.error("Could not import PathManager. Make sure main_pc_code/utils/path_manager.py exists.")
    sys.exit(1)

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Dictionary containing configuration
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration from {config_path}: {e}")
        return {}

def check_port_availability(port: int) -> bool:
    """
    Check if a port is available.
    
    Args:
        port: Port number to check
        
    Returns:
        True if port is available, False otherwise
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', port))
            return True
    except socket.error:
        return False

def cleanup_port(port: int) -> bool:
    """
    Attempt to clean up a port that's in use.
    
    Args:
        port: Port number to clean up
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Try to find the process using the port
        cmd = ["lsof", "-i", f":{port}", "-t"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.stdout.strip():
            pid = int(result.stdout.strip())
            logger.info(f"Found process {pid} using port {port}, attempting to terminate")
            
            try:
                # Try SIGTERM first
                os.kill(pid, signal.SIGTERM)
                
                # Wait a bit for the process to terminate
                time.sleep(1)
                
                # Check if the port is now available
                if check_port_availability(port):
                    logger.info(f"Successfully freed port {port}")
                    return True
                
                # If not, try SIGKILL
                logger.info(f"Port {port} still in use, sending SIGKILL to process {pid}")
                os.kill(pid, signal.SIGKILL)
                
                # Wait a bit for the process to terminate
                time.sleep(1)
                
                # Check if the port is now available
                if check_port_availability(port):
                    logger.info(f"Successfully freed port {port} after SIGKILL")
                    return True
                else:
                    logger.error(f"Failed to free port {port} even after SIGKILL")
                    return False
            except Exception as e:
                logger.error(f"Error terminating process {pid}: {e}")
                return False
        else:
            logger.warning(f"Could not find process using port {port}")
            return False
    except Exception as e:
        logger.error(f"Error cleaning up port {port}: {e}")
        return False

def check_health(agent_name: str, port: int, timeout: int = 5) -> Tuple[bool, str]:
    """
    Check the health of an agent.
    
    Args:
        agent_name: Name of the agent
        port: Health check port
        timeout: Timeout in seconds
        
    Returns:
        Tuple of (is_healthy, message)
    """
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, timeout * 1000)
        socket.connect(f"tcp://localhost:{port}")
        
        # Send health check request
        socket.send_json({"action": "health_check"})
        
        # Wait for response
        response = socket.recv_json()
        
        # Check if response indicates health
        if response.get("status") == "ok":
            return True, json.dumps(response)
        else:
            return False, json.dumps(response)
    except zmq.error.Again:
        return False, "Timeout waiting for response"
    except Exception as e:
        return False, f"Error checking health: {e}"
    finally:
        socket.close()
        context.term()

def monitor_output(pipe, prefix):
    """Monitor and log output from a subprocess pipe"""
    try:
        for line in pipe:
            logger.info(f"[{prefix}] {line.rstrip()}")
    except Exception as e:
        logger.error(f"Error monitoring {prefix}: {e}")
    finally:
        pipe.close()

def start_agent(agent_config: Dict[str, Any]) -> Optional[subprocess.Popen]:
    """
    Start an agent.
    
    Args:
        agent_config: Agent configuration
        
    Returns:
        Process object if successful, None otherwise
    """
    try:
        # Extract agent information
        agent_name = agent_config.get("name", "unknown")
        file_path = agent_config.get("file_path")
        port = agent_config.get("port")
        params = agent_config.get("params", {})
        health_port = params.get("health_check_port") if isinstance(params, dict) else None
        
        if health_port is None:
            health_port = port + 1 if port is not None else None
        
        if file_path is None or port is None:
            logger.error(f"Missing file_path or port for agent {agent_name}")
            return None
        
        # Resolve agent path
        agent_path = PathManager.resolve_path(file_path)
        if not agent_path.exists():
            logger.error(f"Agent file not found: {agent_path}")
            return None
        
        logger.info(f"Starting agent {agent_name} from {agent_path}")
        
        # Check if ports are available
        if not check_port_availability(port):
            logger.warning(f"Port {port} is already in use, attempting to clean up")
            if not cleanup_port(port):
                logger.error(f"Failed to clean up port {port}, cannot start agent {agent_name}")
                return None
        
        if health_port and not check_port_availability(health_port):
            logger.warning(f"Health port {health_port} is already in use, attempting to clean up")
            if not cleanup_port(health_port):
                logger.error(f"Failed to clean up health port {health_port}, cannot start agent {agent_name}")
                return None
        
        # Prepare environment
        env = os.environ.copy()
        
        # Set PYTHONPATH to include project root
        project_root_str = str(PathManager.get_project_root())
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = f"{project_root_str}:{env['PYTHONPATH']}"
        else:
            env["PYTHONPATH"] = project_root_str
        
        # Prepare command
        cmd = [
            sys.executable,
            str(agent_path),
            "--port", str(port)
        ]
        
        if health_port:
            cmd.extend(["--health-port", str(health_port)])
        
        # Add additional parameters
        if isinstance(params, dict):
            for key, value in params.items():
                if key != "health_check_port":  # Already handled
                    cmd.extend([f"--{key.replace('_', '-')}", str(value)])
        
        # Start the process
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Start threads to monitor stdout and stderr
        threading.Thread(
            target=monitor_output,
            args=(process.stdout, f"{agent_name}-stdout"),
            daemon=True
        ).start()
        
        threading.Thread(
            target=monitor_output,
            args=(process.stderr, f"{agent_name}-stderr"),
            daemon=True
        ).start()
        
        # Wait a bit for the process to start
        time.sleep(2)
        
        # Check if the process is still running
        if process.poll() is not None:
            logger.error(f"Agent {agent_name} failed to start, exit code: {process.returncode}")
            return None
        
        # Return the process object
        return process
    
    except Exception as e:
        logger.error(f"Error starting agent {agent_config.get('name', 'unknown')}: {e}")
        return None

def wait_for_health(agent_name: str, health_port: int, timeout: int = 60) -> bool:
    """
    Wait for an agent to become healthy.
    
    Args:
        agent_name: Name of the agent
        health_port: Health check port
        timeout: Maximum time to wait in seconds
        
    Returns:
        True if the agent is healthy, False otherwise
    """
    logger.info(f"Waiting for {agent_name} to become healthy on port {health_port}")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        is_healthy, message = check_health(agent_name, health_port)
        if is_healthy:
            logger.info(f"Agent {agent_name} is healthy: {message}")
            return True
        
        logger.info(f"Agent {agent_name} not yet healthy: {message}")
        time.sleep(5)
    
    logger.error(f"Timed out waiting for {agent_name} to become healthy")
    return False

def start_agents(config: Dict[str, Any]) -> bool:
    """
    Start all agents in the correct order.
    
    Args:
        config: System configuration
        
    Returns:
        True if all required agents started successfully, False otherwise
    """
    # Start core agents first
    core_agents = config.get("core_agents", [])
    for agent_config in core_agents:
        agent_name = agent_config.get("name", "unknown")
        required = agent_config.get("required", False)
        
        # Start the agent
        process = start_agent(agent_config)
        if process:
            running_processes[agent_name] = process
            
            # Wait for health check
            params = agent_config.get("params", {})
            health_port = params.get("health_check_port") if isinstance(params, dict) else None
            if health_port is None:
                port = agent_config.get("port")
                health_port = port + 1 if port is not None else None
                
            if health_port is None:
                logger.error(f"Could not determine health check port for {agent_name}")
                return False
                
            is_healthy = wait_for_health(agent_name, health_port)
            
            if not is_healthy and required:
                logger.error(f"Required agent {agent_name} failed health check")
                return False
        elif required:
            logger.error(f"Failed to start required agent {agent_name}")
            return False
        
        # Brief pause between agent startups
        time.sleep(2)
    
    # Then start dependency agents
    dependency_agents = config.get("dependencies", [])
    for agent_config in dependency_agents:
        agent_name = agent_config.get("name", "unknown")
        required = agent_config.get("required", False)
        
        # Start the agent
        process = start_agent(agent_config)
        if process:
            running_processes[agent_name] = process
            
            # Wait for health check
            params = agent_config.get("params", {})
            health_port = params.get("health_check_port") if isinstance(params, dict) else None
            if health_port is None:
                port = agent_config.get("port")
                health_port = port + 1 if port is not None else None
                
            if health_port is None:
                logger.error(f"Could not determine health check port for {agent_name}")
                return False
                
            is_healthy = wait_for_health(agent_name, health_port)
            
            if not is_healthy and required:
                logger.error(f"Required dependency agent {agent_name} failed health check")
                return False
        elif required:
            logger.error(f"Failed to start required dependency agent {agent_name}")
            return False
        
        # Brief pause between agent startups
        time.sleep(2)
    
    return True

def shutdown_agents():
    """Gracefully shut down all running agents"""
    logger.info("Shutting down agents...")
    
    for name, process in running_processes.items():
        try:
            logger.info(f"Sending SIGTERM to {name}")
            process.terminate()
        except Exception as e:
            logger.error(f"Error terminating {name}: {e}")
    
    # Wait for processes to terminate
    for name, process in running_processes.items():
        try:
            process.wait(timeout=5)
            logger.info(f"Agent {name} terminated")
        except subprocess.TimeoutExpired:
            logger.warning(f"Agent {name} did not terminate, sending SIGKILL")
            try:
                process.kill()
            except Exception as e:
                logger.error(f"Error killing {name}: {e}")

def signal_handler(sig, frame):
    """Handle signals to gracefully shut down"""
    logger.info(f"Received signal {sig}, shutting down")
    stop_event.set()

def cleanup_zmq_sockets():
    """Clean up any lingering ZMQ socket files"""
    try:
        # Check for ZMQ socket files in /tmp
        cmd = ["find", "/tmp", "-name", "*.zmq", "-o", "-name", "*.ipc"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        for file_path in result.stdout.strip().split('\n'):
            if file_path:
                try:
                    os.remove(file_path)
                    logger.info(f"Removed socket file: {file_path}")
                except Exception as e:
                    logger.error(f"Error removing socket file {file_path}: {e}")
    except Exception as e:
        logger.error(f"Error cleaning up ZMQ sockets: {e}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Improved Layer 0 Startup")
    parser.add_argument("--config", default="main_pc_code/NEWMUSTFOLLOW/minimal_system_config_local.yaml",
                        help="Path to configuration file")
    parser.add_argument("--cleanup-only", action="store_true",
                        help="Only clean up resources without starting agents")
    args = parser.parse_args()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Clean up ZMQ sockets
    cleanup_zmq_sockets()
    
    if args.cleanup_only:
        logger.info("Cleanup completed, exiting as requested")
        return 0
    
    # Load configuration
    config_path = PathManager.resolve_path(args.config)
    config = load_config(str(config_path))
    if not config:
        logger.error("Failed to load configuration")
        return 1
    
    # Start agents
    success = start_agents(config)
    if not success:
        logger.error("Failed to start all required agents")
        shutdown_agents()
        return 1
    
    logger.info("All agents started successfully")
    
    # Wait for signal to exit
    try:
        while not stop_event.is_set():
            time.sleep(1)
    finally:
        shutdown_agents()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
