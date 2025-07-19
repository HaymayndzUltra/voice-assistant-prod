#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Unified Layer 0 Startup Script
------------------------------
Handles the startup sequence for Layer 0 agents in the AI system.
Ensures proper dependency order, environment setup, and error handling.
"""

import os
import sys
import time
import yaml
import signal
import logging
import argparse
import subprocess
import threading
import importlib.util
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import requests
import zmq
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("layer0_startup.log")
    ]
)
logger = logging.getLogger("Layer0Startup")

# Global variables
running_processes = {}
stop_event = threading.Event()


def find_project_root() -> Path:
    """Find the project root directory by looking for specific markers"""
    current_dir = Path.cwd()
    
    # Check if we're already at the project root
    if (current_dir / "main_pc_code").exists() and (current_dir / "pc2_code").exists():
        return current_dir
    
    # Try to find project root by traversing up
    for parent in current_dir.parents:
        if (parent / "main_pc_code").exists() and (parent / "pc2_code").exists():
            return parent
    
    # If we can't find it, just use the current directory
    logger.warning("Could not find project root, using current directory")
    return current_dir


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dictionary containing the configuration
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return {}


def resolve_agent_path(file_path: str, project_root: Path) -> Optional[Path]:
    """
    Resolve the absolute path to an agent file.
    
    Args:
        file_path: Relative path to the agent file
        project_root: Project root directory
        
    Returns:
        Absolute path to the agent file or None if not found
    """
    # List of possible base directories to check
    base_dirs = [
        project_root / "main_pc_code",
        project_root / "main_pc_code" / "agents",
        project_root / "main_pc_code" / "FORMAINPC",
        project_root / "main_pc_code" / "NEWMUSTFOLLOW" / "agents",
        project_root / "pc2_code" / "agents",
        project_root / "src" / "agents",
        project_root
    ]
    
    # First check if the path is already absolute or relative to project root
    direct_path = Path(file_path)
    if direct_path.is_absolute() and direct_path.exists():
        return direct_path
    
    project_relative = project_root / file_path
    if project_relative.exists():
        return project_relative
    
    # Try each base directory
    for base_dir in base_dirs:
        full_path = base_dir / file_path
        if full_path.exists():
            return full_path
        
        # Also try with just the filename
        filename = Path(file_path).name
        name_only_path = base_dir / filename
        if name_only_path.exists():
            return name_only_path
    
    logger.error(f"Could not find agent file: {file_path}")
    return None


def check_health(agent_name: str, port: int, timeout: int = 5) -> Tuple[bool, str]:
    """
    Check the health of an agent via its health check endpoint.
    
    Args:
        agent_name: Name of the agent
        port: Health check port
        timeout: Timeout in seconds
        
    Returns:
        Tuple of (is_healthy, status_message)
    """
    try:
        # First try HTTP health check
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "")
                if isinstance(status, str) and status.upper() in ["HEALTHY", "OK"]:
                    return True, f"HTTP health check passed: {status}"
                else:
                    return False, f"HTTP health check failed: {status}"
        except requests.RequestException:
            # HTTP health check failed, try ZMQ
            pass
        
        # Try ZMQ health check
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, timeout * 1000)
        socket.connect(f"tcp://localhost:{port}")
        
        # Send health check request
        socket.send_json({"action": "health_check"})
        response = socket.recv_json()
        
        # Check response
        status = response.get("status", "")
        if isinstance(status, str) and status.upper() in ["HEALTHY", "OK"]:
            return True, f"ZMQ health check passed: {status}"
        else:
            return False, f"ZMQ health check failed: {status}"
    
    except Exception as e:
        return False, f"Health check error: {e}"
    
    finally:
        if 'socket' in locals():
            socket.close()
        if 'context' in locals():
            context.term()


def start_agent(agent_config: Dict[str, Any], project_root: Path) -> Optional[subprocess.Popen]:
    """
    Start an agent as a subprocess.
    
    Args:
        agent_config: Agent configuration
        project_root: Project root directory
        
    Returns:
        Subprocess object or None if failed
    """
    try:
        # Extract agent information
        agent_name = agent_config.get("name", "unknown")
        file_path = agent_config.get("file_path", "")
        port = agent_config.get("port")
        
        if not file_path:
            logger.error(f"No file path specified for agent {agent_name}")
            return None
            
        if not port:
            logger.error(f"No port specified for agent {agent_name}")
            return None
            
        # Get health check port with safe default
        params = agent_config.get("params", {})
        health_port = params.get("health_check_port") if isinstance(params, dict) else None
        if health_port is None:
            health_port = port + 1 if port is not None else None
        
        if health_port is None:
            logger.error(f"Could not determine health check port for {agent_name}")
            return None
        
        # Resolve the agent file path
        agent_path = resolve_agent_path(str(file_path), project_root)
        if not agent_path:
            logger.error(f"Could not resolve path for agent {agent_name}")
            return None
        
        # Prepare environment variables
        env = os.environ.copy()
        
        # Add any agent-specific environment variables
        agent_env_vars = params.get("env_vars", {}) if isinstance(params, dict) else {}
        for key, value in agent_env_vars.items():
            env[key] = str(value)
        
        # Set PYTHONPATH to include project root
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = f"{project_root}:{env['PYTHONPATH']}"
        else:
            env["PYTHONPATH"] = str(project_root)
        
        # Prepare command
        cmd = [
            sys.executable,
            str(agent_path),
            "--port", str(port),
            "--health-port", str(health_port)
        ]
        
        # Start the process
        logger.info(f"Starting agent {agent_name} from {agent_path}")
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


def monitor_output(pipe, prefix):
    """Monitor and log output from a subprocess pipe"""
    try:
        for line in pipe:
            logger.info(f"[{prefix}] {line.rstrip()}")
    except Exception as e:
        logger.error(f"Error monitoring {prefix}: {e}")
    finally:
        pipe.close()


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


def start_agents(config: Dict[str, Any], project_root: Path) -> bool:
    """
    Start all agents in the correct order.
    
    Args:
        config: System configuration
        project_root: Project root directory
        
    Returns:
        True if all required agents started successfully, False otherwise
    """
    # Start core agents first
    core_agents = config.get("core_agents", [])
    for agent_config in core_agents:
        agent_name = agent_config.get("name", "unknown")
        required = agent_config.get("required", False)
        
        # Start the agent
        process = start_agent(agent_config, project_root)
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
        process = start_agent(agent_config, project_root)
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


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Unified Layer 0 Startup")
    parser.add_argument("--config", default="main_pc_code/NEWMUSTFOLLOW/minimal_system_config_local.yaml",
                        help="Path to configuration file")
    args = parser.parse_args()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Find project root
    project_root = find_project_root()
    logger.info(f"Project root: {project_root}")
    
    # Load configuration
    config_path = project_root / args.config
    config = load_config(str(config_path))
    if not config:
        logger.error("Failed to load configuration")
        return 1
    
    # Start agents
    success = start_agents(config, project_root)
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
