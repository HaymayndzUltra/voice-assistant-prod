#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Test script for improved Layer 0 startup

This script tests the improved Layer 0 startup by:
1. Cleaning up any existing processes
2. Starting the Layer 0 agents
3. Checking their health
4. Performing a graceful shutdown
"""

import os
import sys
import time
import signal
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/test_layer0.log')
    ]
)
logger = logging.getLogger('test_layer0')

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

def run_command(cmd, timeout=None):
    """Run a command and return its output"""
    logger.info(f"Running command: {cmd}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode != 0:
            logger.error(f"Command failed with exit code {result.returncode}")
            logger.error(f"Stderr: {result.stderr}")
            return False, result.stdout, result.stderr
        return True, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout} seconds")
        return False, "", "Timeout"
    except Exception as e:
        logger.error(f"Error running command: {e}")
        return False, "", str(e)

def cleanup_processes():
    """Clean up any existing processes"""
    logger.info("Cleaning up existing processes")
    success, stdout, stderr = run_command(["python3", "cleanup_agents.py", "--force"])
    if not success:
        logger.error("Failed to clean up processes")
        return False
    logger.info("Processes cleaned up successfully")
    return True

def start_layer0():
    """Start the Layer 0 agents"""
    logger.info("Starting Layer 0 agents")
    
    # Use Popen to start the process in the background
    process = subprocess.Popen(
        ["./run_improved_layer0.sh"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # Give it some time to start
    time.sleep(10)
    
    # Check if the process is still running
    if process.poll() is not None:
        logger.error(f"Layer 0 startup failed with exit code {process.returncode}")
        stdout, stderr = process.communicate()
        logger.error(f"Stdout: {stdout}")
        logger.error(f"Stderr: {stderr}")
        return False, None
    
    logger.info("Layer 0 agents started successfully")
    return True, process

def check_agent_health(agent_name, health_port):
    """Check the health of an agent"""
    logger.info(f"Checking health of {agent_name} on port {health_port}")
    
    # Use ZMQ to check health
    import zmq
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
    
    try:
        socket.connect(f"tcp://localhost:{health_port}")
        socket.send_json({"action": "health_check"})
        response = socket.recv_json()
        
        if response.get("status") == "ok":
            logger.info(f"Agent {agent_name} is healthy: {response}")
            return True
        else:
            logger.error(f"Agent {agent_name} is not healthy: {response}")
            return False
    except Exception as e:
        logger.error(f"Error checking health of {agent_name}: {e}")
        return False
    finally:
        socket.close()
        context.term()

def check_all_agents_health():
    """Check the health of all Layer 0 agents"""
    logger.info("Checking health of all Layer 0 agents")
    
    # Define the agents to check
    agents = [
        {"name": "SystemDigitalTwin", "port": 7120, "health_port": 7121},
        {"name": "ModelManagerAgent", "port": 5570, "health_port": 5571},
        {"name": "CoordinatorAgent", "port": 26002, "health_port": 26003},
        {"name": "ChainOfThoughtAgent", "port": 5612, "health_port": 5613}
    ]
    
    all_healthy = True
    
    for agent in agents:
        if not check_agent_health(agent["name"], agent["health_port"]):
            all_healthy = False
    
    return all_healthy

def shutdown_layer0(process):
    """Shut down the Layer 0 agents"""
    logger.info("Shutting down Layer 0 agents")
    
    # Send SIGTERM to the process
    process.terminate()
    
    try:
        # Wait for the process to terminate
        process.wait(timeout=10)
        logger.info("Layer 0 agents shut down successfully")
        return True
    except subprocess.TimeoutExpired:
        logger.error("Timeout waiting for Layer 0 agents to shut down, sending SIGKILL")
        process.kill()
        return False

def main():
    """Main entry point"""
    logger.info("Starting test of improved Layer 0 startup")
    
    # Clean up any existing processes
    if not cleanup_processes():
        logger.error("Failed to clean up processes, aborting test")
        return 1
    
    # Start the Layer 0 agents
    success, process = start_layer0()
    if not success:
        logger.error("Failed to start Layer 0 agents, aborting test")
        return 1
    
    try:
        # Wait for agents to stabilize
        logger.info("Waiting for agents to stabilize")
        time.sleep(20)
        
        # Check the health of all agents
        if not check_all_agents_health():
            logger.error("Not all agents are healthy")
            return 1
        
        logger.info("All agents are healthy")
        
        # Keep the agents running for a while to observe stability
        logger.info("Keeping agents running for 30 seconds to observe stability")
        time.sleep(30)
        
        # Check health again
        if not check_all_agents_health():
            logger.error("Not all agents are healthy after stability period")
            return 1
        
        logger.info("All agents are still healthy after stability period")
        
        # Test passed
        logger.info("Test passed successfully")
        return 0
    finally:
        # Shut down the Layer 0 agents
        shutdown_layer0(process)
        
        # Final cleanup
        cleanup_processes()

if __name__ == "__main__":
    sys.exit(main()) 