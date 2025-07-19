#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Fixed Layer 0 Agent Startup Script

This script addresses common issues with Layer 0 agents:
1. Port conflicts
2. Environment setup
3. Path resolution
4. Health check setup
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
        logging.FileHandler('fixed_layer0_startup.log')
    ]
)
logger = logging.getLogger("FixedStartup")

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Store agent processes
agent_processes = {}

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
    
    # Project root
    os.environ["PROJECT_ROOT"] = SCRIPT_DIR

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

def start_agent(agent_config):
    """Start a single agent"""
    name = agent_config.get('name')
    file_path = agent_config.get('file_path')
    port = agent_config.get('port')
    
    if not file_path:
        logger.error(f"No file path specified for {name}")
        return False
    
    if not port:
        logger.error(f"No port specified for {name}")
        return False
    
    full_path = find_agent_file(file_path)
    if not full_path:
        logger.error(f"Could not find {file_path} for {name}")
        return False
    
    logger.info(f"Starting agent {name} ({full_path}) on port {port}")
    
    # Set agent-specific environment variables
    env = os.environ.copy()
    env["AGENT_NAME"] = name
    env["AGENT_PORT"] = str(port)
    env["HEALTH_CHECK_PORT"] = str(port + 1)
    
    # Start the agent process
    try:
        process = subprocess.Popen(
            [sys.executable, full_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1
        )
        
        agent_processes[name] = process
        logger.info(f"Agent {name} started with PID {process.pid}")
        return True
    except Exception as e:
        logger.error(f"Error starting agent {name}: {e}")
        return False

def check_agent_health(name, port):
    """Check if an agent is healthy"""
    health_port = port + 1
    
    try:
        import zmq
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        
        socket.connect(f"tcp://localhost:{health_port}")
        socket.send(b"health")
        
        response = socket.recv_json()
        status = response.get("status", "unknown")
        
        if status == "ok":
            logger.info(f"Agent {name} is healthy")
            return True
        else:
            logger.warning(f"Agent {name} reported status: {status}")
            return False
    except zmq.error.Again:
        logger.warning(f"Health check timed out for agent {name}")
        return False
    except Exception as e:
        logger.error(f"Error checking health for agent {name}: {e}")
        return False
    finally:
        socket.close()
        context.term()

def monitor_agents():
    """Monitor agent health"""
    logger.info("Starting agent health monitoring")
    
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return
    
    # Combine core agents and dependencies
    all_agents = []
    if 'core_agents' in config:
        all_agents.extend(config['core_agents'])
    if 'dependencies' in config:
        all_agents.extend(config['dependencies'])
    
    # Check each agent's health
    healthy_agents = 0
    unhealthy_agents = 0
    
    for agent_config in all_agents:
        name = agent_config.get('name')
        port = agent_config.get('port')
        
        if not port:
            logger.warning(f"No port specified for {name}")
            continue
        
        if check_agent_health(name, port):
            healthy_agents += 1
        else:
            unhealthy_agents += 1
    
    logger.info(f"Health check complete: {healthy_agents} healthy, {unhealthy_agents} unhealthy")
    return healthy_agents, unhealthy_agents

def cleanup():
    """Clean up resources and terminate agent processes"""
    logger.info("Cleaning up resources")
    
    for name, process in agent_processes.items():
        logger.info(f"Terminating agent {name}")
        try:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"Agent {name} did not terminate gracefully, killing")
                process.kill()
        except Exception as e:
            logger.error(f"Error terminating agent {name}: {e}")
    
    logger.info("Cleanup complete")

def signal_handler(sig, frame):
    """Handle signals to clean up properly"""
    logger.info(f"Received signal {sig}, cleaning up")
    cleanup()
    sys.exit(0)

def main():
    """Main function"""
    logger.info("Starting Fixed Layer 0 Agent Startup")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Setup environment
    setup_environment()
    
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return
    
    # Combine core agents and dependencies
    all_agents = []
    if 'core_agents' in config:
        all_agents.extend(config['core_agents'])
    if 'dependencies' in config:
        all_agents.extend(config['dependencies'])
    
    # Start each agent
    for agent_config in all_agents:
        start_agent(agent_config)
        # Sleep briefly to avoid port conflicts
        time.sleep(1)
    
    # Wait for agents to initialize
    logger.info("Waiting for agents to initialize (30 seconds)")
    time.sleep(30)
    
    # Monitor agent health
    healthy_agents, unhealthy_agents = monitor_agents()
    
    # Keep monitoring until interrupted
    try:
        while True:
            logger.info("Press Ctrl+C to stop")
            time.sleep(60)
            healthy_agents, unhealthy_agents = monitor_agents()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        cleanup()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Error: {e}")
        cleanup()
