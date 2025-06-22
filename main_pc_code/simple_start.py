#!/usr/bin/env python3
"""
Simple AI System Startup Script
"""

import os
import sys
import yaml
import subprocess
import time
import logging
import signal
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("system_startup.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Startup")

# Set up paths
CURRENT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = CURRENT_DIR.parent
CONFIG_FILE = CURRENT_DIR / "config" / "simple_startup_config.yaml"

# Set PYTHONPATH
os.environ["PYTHONPATH"] = f"{PROJECT_ROOT}:{CURRENT_DIR}:{os.environ.get('PYTHONPATH', '')}"
logger.info(f"PYTHONPATH set to: {os.environ['PYTHONPATH']}")

# Global process list
processes = []

def load_config():
    """Load configuration from simple_startup_config.yaml"""
    logger.info(f"Loading config from {CONFIG_FILE}")
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f)
        
        if not config:
            logger.error("Config file is empty or invalid")
            return None
        
        logger.info(f"Loaded configuration with {len(config.get('agents', []))} agents")
        return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return None

def start_agent(agent_info):
    """Start a single agent"""
    name = agent_info.get('name', 'unknown')
    path = agent_info.get('path')
    port = agent_info.get('port')
    
    if not path:
        logger.error(f"No path specified for agent {name}")
        return None
    
    # Check if the path exists
    agent_path = CURRENT_DIR / path
    if not agent_path.exists():
        logger.error(f"Agent file not found: {agent_path}")
        return None
    
    # Build command
    cmd = [sys.executable, str(agent_path)]
    
    # Add port if specified
    if port:
        cmd.extend(["--port", str(port)])
    
    # Add any additional args
    args = agent_info.get('args', {})
    for key, value in args.items():
        if key and value:
            cmd.extend([f"--{key}", str(value)])
    
    logger.info(f"Starting agent {name}: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(
            cmd,
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        logger.info(f"Started agent {name} with PID {process.pid}")
        return process
    except Exception as e:
        logger.error(f"Error starting agent {name}: {e}")
        return None

def start_agents(config):
    """Start all agents in the config"""
    agents = config.get('agents', [])
    logger.info(f"Starting {len(agents)} agents...")
    
    for agent_info in agents:
        name = agent_info.get('name', 'unknown')
        
        # Skip disabled agents
        if not agent_info.get('enabled', True):
            logger.info(f"Skipping disabled agent: {name}")
            continue
        
        process = start_agent(agent_info)
        if process:
            processes.append((name, process))
            # Small delay to avoid port conflicts
            time.sleep(1)
    
    logger.info(f"Started {len(processes)} agents")

def monitor_processes():
    """Monitor running processes"""
    logger.info("Monitoring processes...")
    
    try:
        while processes:
            for name, process in processes[:]:
                if process.poll() is not None:
                    returncode = process.poll()
                    stdout, stderr = process.communicate()
                    
                    if returncode != 0:
                        logger.error(f"Agent {name} exited with code {returncode}")
                        if stderr:
                            logger.error(f"Error output: {stderr}")
                    else:
                        logger.info(f"Agent {name} completed successfully")
                    
                    processes.remove((name, process))
            
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, stopping all processes...")
        stop_all_processes()

def stop_all_processes():
    """Stop all running processes"""
    logger.info(f"Stopping {len(processes)} processes...")
    
    for name, process in processes:
        try:
            logger.info(f"Stopping {name} (PID {process.pid})...")
            process.terminate()
            
            # Wait for up to 5 seconds for the process to terminate
            for _ in range(5):
                if process.poll() is not None:
                    break
                time.sleep(1)
            
            # If the process is still running, kill it
            if process.poll() is None:
                logger.info(f"Killing {name} (PID {process.pid})...")
                process.kill()
        except Exception as e:
            logger.error(f"Error stopping {name}: {e}")
    
    # Clear the process list
    processes.clear()
    logger.info("All processes stopped")

def signal_handler(sig, frame):
    """Handle signals"""
    logger.info(f"Received signal {sig}, stopping all processes...")
    stop_all_processes()
    sys.exit(0)

def main():
    """Main function"""
    logger.info("Starting AI system...")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return False
    
    # Start agents
    start_agents(config)
    
    # Monitor processes
    monitor_processes()
    
    logger.info("AI system shutdown complete")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 