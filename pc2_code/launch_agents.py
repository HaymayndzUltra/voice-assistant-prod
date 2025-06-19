"""
Distributed Agents Launcher for PC2
-----------------------------------
Script to launch all required agents for the distributed voice assistant system
Connects to Main PC (192.168.1.27) and provides required services
"""

import os
import time
import subprocess
import socket
from datetime import datetime

# Configuration
AGENTS = [
    {"name": "Enhanced Router", "script": "remote_connector_agent.py", "port": 5555},
    {"name": "Task Router", "script": "remote_connector_agent.py", "port": 5556},
    {"name": "Remote Connector", "script": "remote_connector_agent.py", "port": 5557},
    {"name": "Context Memory", "script": "contextual_memory_agent.py", "port": 5558},
    {"name": "Jarvis Memory", "script": "jarvis_memory_agent.py", "port": 5559},
    {"name": "Digital Twin", "script": "digital_twin_agent.py", "port": 5560},
    {"name": "Learning Mode", "script": "learning_mode_agent.py", "port": 5561},
    {"name": "Translator Agent", "script": "translator_agent.py", "port": 5562},
    {"name": "Web Scraper", "script": "web_scraper_agent.py", "port": 5563},
    {"name": "TinyLlama", "script": "model_manager_agent.py", "port": 5564, "args": "--model=tinyllama"}
]

def print_header(message):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"{message}")
    print("=" * 70)

def check_port_in_use(port):
    """Check if a port is already in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def launch_agents():
    """Launch all required agents"""
    print_header("LAUNCHING ALL CORE DISTRIBUTED AGENTS - PC2")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")
        print("Created logs directory")
    
    # Launch each agent
    processes = []
    for agent in AGENTS:
        port = agent["port"]
        name = agent["name"]
        script = agent["script"]
        
        # Check if port is already in use
        if check_port_in_use(port):
            print(f"WARNING: Port {port} is already in use! Skipping {name}...")
            continue
        
        # Build command
        args = agent.get("args", "")
        script_path = os.path.join("agents", script)
        cmd = f"python {script_path} --port={port} {args}"
        
        # Launch agent
        print(f"Starting {name} on port {port}...")
        log_file = open(f"logs/{name.lower().replace(' ', '_')}_{port}.log", "w")
        process = subprocess.Popen(
            cmd, 
            shell=True,
            stdout=log_file,
            stderr=subprocess.STDOUT
        )
        processes.append({"process": process, "name": name, "port": port, "log": log_file})
        time.sleep(1)  # Small delay between launches
    
    return processes

def check_agent_status(processes):
    """Check status of launched agents"""
    print_header("CHECKING AGENT STATUS")
    
    running = 0
    for p in processes:
        name = p["name"]
        port = p["port"]
        
        # Check if process is still running
        if p["process"].poll() is None:
            # Process is running, check if port is active
            if check_port_in_use(port):
                status = "RUNNING (port active)"
                running += 1
            else:
                status = "RUNNING (port not active)"
        else:
            status = f"STOPPED (exit code: {p['process'].returncode})"
        
        print(f"{name} (port {port}): {status}")
    
    return running

def main():
    """Main function to launch all agents"""
    # Launch agents
    processes = launch_agents()
    
    # Wait for agents to initialize
    print("\nWaiting for agents to initialize (15 seconds)...")
    time.sleep(15)
    
    # Check status
    running_count = check_agent_status(processes)
    
    # Show summary
    print_header("DISTRIBUTED SYSTEM STATUS")
    print(f"Successfully launched {running_count} out of {len(AGENTS)} agents")
    print(f"Phi Translator: Running on port 5581")
    print(f"Main PC Bridge connection: tcp://192.168.1.27:5600")
    print("\nSYSTEM READY FOR CONNECTION FROM MAIN PC (192.168.1.27)")
    
    print("\nLogs available in the logs directory")
    print("Press Ctrl+C to terminate all agents and exit")
    
    # Keep script running to maintain processes
    try:
        while True:
            time.sleep(60)
            # Every minute, verify agents are still running
            running_count = check_agent_status(processes)
            print(f"Status check: {running_count}/{len(AGENTS)} agents running")
    except KeyboardInterrupt:
        print("\nShutting down all agents...")
        for p in processes:
            if p["process"].poll() is None:
                p["process"].terminate()
            p["log"].close()
        print("All agents terminated.")

if __name__ == "__main__":
    main()
