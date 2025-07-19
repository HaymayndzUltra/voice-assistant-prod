#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Improved MainPC Agents Startup Script
-----------------------------------
This script starts MainPC agents with proper PYTHONPATH setup.
"""

import os
import sys
import subprocess
import time
import signal
import threading
from pathlib import Path

# Set up PYTHONPATH
project_root = Path(__file__).resolve().parent
main_pc_code_dir = project_root / 'main_pc_code'

# Add to PYTHONPATH
if main_pc_code_dir.as_posix() not in sys.path:
    sys.path.insert(0, main_pc_code_dir.as_posix())
if project_root.as_posix() not in sys.path:
    sys.path.insert(0, project_root.as_posix())

# Set environment variable
os.environ['PYTHONPATH'] = f"{main_pc_code_dir}:{project_root}:{os.environ.get('PYTHONPATH', '')}"

# Global variables
running_processes = {}
stop_event = threading.Event()

def run_agent(agent_path):
    """Run an agent with the correct environment"""
    env = os.environ.copy()
    
    print(f"Starting {agent_path}...")
    process = subprocess.Popen(
        [sys.executable, str(agent_path)],
        env=env,
        cwd=main_pc_code_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Start threads to monitor stdout and stderr
    threading.Thread(target=monitor_output, args=(process.stdout, f"{agent_path.name} [OUT]"), daemon=True).start()
    threading.Thread(target=monitor_output, args=(process.stderr, f"{agent_path.name} [ERR]"), daemon=True).start()
    
    return process

def monitor_output(pipe, prefix):
    """Monitor and print output from a subprocess pipe with a prefix"""
    for line in iter(pipe.readline, ''):
        print(f"{prefix}: {line.rstrip()}")

def check_agent_health(agent_name, port, timeout=5):
    """Check if an agent is healthy by connecting to its health port"""
    import zmq
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, timeout * 1000)
    socket.connect(f"tcp://localhost:{port}")
    
    try:
        socket.send_json({"action": "health_check"})
        response = socket.recv_json()
        print(f"✅ {agent_name} health check passed: {response}")
        return True
    except Exception as e:
        print(f"❌ {agent_name} health check failed: {e}")
        return False
    finally:
        socket.close()
        context.term()

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
    """Run core MainPC agents"""
    # Core agents to run in order with their ports
    core_agents = [
        {"path": "src/core/task_router.py", "port": 7000, "health_port": 7001},
        {"path": "agents/model_manager_agent.py", "port": 5570, "health_port": 5571},
        {"path": "agents/coordinator_agent.py", "port": 26002, "health_port": 26003},
        {"path": "FORMAINPC/ChainOfThoughtAgent.py", "port": 5580, "health_port": 5581},
        {"path": "FORMAINPC/GOT_TOTAgent.py", "port": 5590, "health_port": 5591},
        {"path": "agents/system_digital_twin.py", "port": 5717, "health_port": 5718}
    ]
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    processes = []
    
    try:
        # Start each agent and wait 3 seconds between starts
        for agent_info in core_agents:
            agent_path = main_pc_code_dir / agent_info["path"]
            if agent_path.exists():
                process = run_agent(agent_path)
                agent_name = agent_path.stem
                running_processes[agent_name] = process
                processes.append((agent_name, process))
                
                # Wait for agent to start
                time.sleep(3)
                
                # Check health if port is specified
                if "health_port" in agent_info:
                    check_agent_health(agent_name, agent_info["health_port"])
            else:
                print(f"Warning: Agent {agent_info['path']} not found at {agent_path}")
        
        print("\nAll agents started. Press Ctrl+C to stop all agents.\n")
        
        # Wait for Ctrl+C
        while not stop_event.is_set():
            # Check if any process has terminated unexpectedly
            for agent_name, process in list(running_processes.items()):
                if process.poll() is not None:
                    exit_code = process.poll()
                    print(f"⚠️ {agent_name} terminated unexpectedly with exit code {exit_code}")
                    # Remove from running processes
                    running_processes.pop(agent_name)
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()
