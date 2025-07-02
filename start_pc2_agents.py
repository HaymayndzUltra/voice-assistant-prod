#!/usr/bin/env python3
"""
PC2 Agents Startup Script
------------------------
This script starts all PC2 agents in the correct order based on their dependencies.
It reads from the startup_config.yaml file to determine which agents to start.

Usage:
    python start_pc2_agents.py [--dry-run]
"""

import os
import sys
import yaml
import time
import subprocess
import argparse
from pathlib import Path
import zmq
import signal
import threading

# Define paths
PROJECT_ROOT = Path(__file__).resolve().parent
PC2_CODE_ROOT = PROJECT_ROOT / 'pc2_code'
PC2_CONFIG_PATH = PC2_CODE_ROOT / 'config' / 'startup_config.yaml'
PC2_AGENTS_DIR = PC2_CODE_ROOT / 'agents'

# Global variables
running_processes = {}
stop_event = threading.Event()

def load_config():
    """Load the startup configuration from YAML file"""
    try:
        with open(PC2_CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return None

def check_port_available(port):
    """Check if a port is available"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result != 0  # If result is not 0, the port is available

def check_agent_health(name, port, timeout=5):
    """Check if an agent is healthy by connecting to its health port"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, timeout * 1000)
    socket.connect(f"tcp://localhost:{port}")
    
    try:
        socket.send_json({"action": "health_check"})
        response = socket.recv_json()
        print(f"✅ {name} health check passed: {response}")
        return True
    except Exception as e:
        print(f"❌ {name} health check failed: {e}")
        return False
    finally:
        socket.close()
        context.term()

def start_agent(agent, dry_run=False):
    """Start a single agent based on its configuration"""
    name = agent.get('name', 'Unknown')
    script_path = agent.get('script_path', '')
    port = agent.get('port', 0)
    health_port = agent.get('health_check_port', port + 1)
    
    if not script_path:
        print(f"❌ {name}: No script path specified")
        return False
    
    full_script_path = PC2_AGENTS_DIR / script_path
    if not full_script_path.exists():
        print(f"❌ {name}: Script not found at {full_script_path}")
        return False
    
    # Check if port is already in use
    if port > 0 and not check_port_available(port):
        print(f"⚠️ {name}: Port {port} is already in use")
        
    print(f"\n=== Starting {name} ({script_path}) on port {port} ===")
    
    if dry_run:
        print(f"🔍 DRY RUN: Would start {name} using python3 {full_script_path}")
        return True
    
    try:
        # Start the process
        process = subprocess.Popen(
            ["python3", str(full_script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=PC2_AGENTS_DIR
        )
        
        # Store the process
        running_processes[name] = process
        
        # Wait a bit for the agent to start
        time.sleep(2)
        
        # Check if process is still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print(f"❌ {name} failed to start. Return code: {process.returncode}")
            if stdout:
                print(f"Output: {stdout[:200]}...")
            if stderr:
                print(f"Error: {stderr[:200]}...")
            return False
        
        print(f"✅ {name} started with PID {process.pid}")
        
        # Check agent health if health port is available
        if health_port > 0:
            time.sleep(3)  # Give more time for health endpoint to be ready
            check_agent_health(name, health_port)
            
        return True
        
    except Exception as e:
        print(f"❌ Error starting {name}: {e}")
        return False

def start_agents_in_order(config, dry_run=False):
    """Start agents in the correct order based on dependencies"""
    if not config:
        print("No configuration loaded")
        return False
    
    agents = config.get('pc2_services', [])
    if not agents:
        print("No agents found in configuration")
        return False
    
    print(f"Found {len(agents)} agents in configuration")
    
    # First pass: Start agents with no dependencies
    print("\n=== Starting agents with no dependencies ===")
    for agent in agents:
        if not agent.get('dependencies'):
            start_agent(agent, dry_run)
    
    # Give some time for the first batch to initialize
    time.sleep(5)
    
    # Second pass: Start agents with dependencies
    print("\n=== Starting agents with dependencies ===")
    for agent in agents:
        if agent.get('dependencies'):
            dependencies = agent.get('dependencies', [])
            print(f"Starting {agent.get('name')} with dependencies: {dependencies}")
            start_agent(agent, dry_run)
    
    return True

def cleanup(signum=None, frame=None):
    """Clean up all running processes"""
    print("\n\n=== Cleaning up processes ===")
    stop_event.set()
    
    for name, process in running_processes.items():
        if process.poll() is None:  # Process is still running
            print(f"Stopping {name}...")
            try:
                process.terminate()
                # Wait a bit for graceful termination
                time.sleep(1)
                if process.poll() is None:
                    process.kill()
            except Exception as e:
                print(f"Error stopping {name}: {e}")
    
    print("All processes stopped")
    sys.exit(0)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Start PC2 agents")
    parser.add_argument("--dry-run", action="store_true", help="Show commands without executing")
    args = parser.parse_args()
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    print("=== PC2 Agents Startup Script ===")
    
    # Load configuration
    config = load_config()
    if not config:
        sys.exit(1)
    
    # Start agents
    success = start_agents_in_order(config, args.dry_run)
    
    if success:
        print("\n✅ All agents started successfully!")
        if not args.dry_run:
            print("\nPress Ctrl+C to stop all agents")
            try:
                while not stop_event.is_set():
                    time.sleep(1)
            except KeyboardInterrupt:
                cleanup()
    else:
        print("\n❌ Failed to start some agents")
        cleanup()

if __name__ == "__main__":
    main() 