#!/bin/bash

# run_mvs.sh - Minimal Viable System Runner
# This script sets up the environment and launches the minimal viable system agents

# Create necessary directories
mkdir -p logs
mkdir -p data
mkdir -p models
mkdir -p cache
mkdir -p certificates

# ====== ENVIRONMENT VARIABLES ======

# Machine configuration
export MACHINE_TYPE="MAINPC"
export PYTHONPATH="${PYTHONPATH}:${PWD}/../../"

# Network configuration
export MAIN_PC_IP="localhost"
export PC2_IP="localhost"
export BIND_ADDRESS="0.0.0.0"

# Security settings
export SECURE_ZMQ="0"  # Disable secure ZMQ for initial testing
export ZMQ_CERTIFICATES_DIR="certificates"

# Service discovery
export SYSTEM_DIGITAL_TWIN_PORT="7120"
export SERVICE_DISCOVERY_ENABLED="1"
export FORCE_LOCAL_SDT="1"

# Voice pipeline ports
export TASK_ROUTER_PORT="8571"
export STREAMING_TTS_PORT="5562"
export TTS_PORT="5562"
export INTERRUPT_PORT="5576"

# Resource constraints
export MAX_MEMORY_MB="2048"
export MAX_VRAM_MB="2048"

# Logging
export LOG_LEVEL="INFO"
export LOG_DIR="logs"

# Timeouts and retries
export ZMQ_REQUEST_TIMEOUT="5000"
export CONNECTION_RETRIES="3"
export SERVICE_DISCOVERY_TIMEOUT="10000"

# Voice pipeline settings
export VOICE_SAMPLE_DIR="voice_samples"
export MODEL_DIR="models"
export CACHE_DIR="cache"

# Agent-specific variables
export MODEL_MANAGER_PORT="5570"
export USE_DUMMY_AUDIO="true"

# ====== LAUNCH MVS AGENTS ======

echo "Starting Minimal Viable System agents..."

# Create a Python script to launch the agents in the correct order
cat > launch_mvs.py << 'EOL'
#!/usr/bin/env python3

import os
import sys
import time
import yaml
import subprocess
import signal
import psutil
from pathlib import Path

# Load the minimal system configuration - use the local copy
config_path = "minimal_system_config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Combine core agents and dependencies into a single list
all_agents = []
if 'core_agents' in config:
    all_agents.extend(config['core_agents'])
if 'dependencies' in config:
    all_agents.extend(config['dependencies'])

# Sort agents by dependencies to determine launch order
def get_dependencies(agent):
    return agent.get('dependencies', [])

# First launch agents with no dependencies
independent_agents = [agent for agent in all_agents if not get_dependencies(agent)]
dependent_agents = [agent for agent in all_agents if get_dependencies(agent)]

# Function to launch an agent
def launch_agent(agent):
    name = agent.get('name')
    script_path = agent.get('script_path')
    port = agent.get('port')
    
    # Skip if script path is not specified
    if not script_path:
        print(f"Skipping {name}: No script path specified")
        return None
    
    # Construct full path - go up two directories to reach project root
    full_path = os.path.join("../../", "main_pc_code", script_path)
    
    # Check if file exists
    if not os.path.exists(full_path):
        print(f"Skipping {name}: Script not found at {full_path}")
        return None
    
    # Construct command
    cmd = [sys.executable, full_path]
    if port:
        cmd.extend(["--port", str(port)])
    
    # Launch the agent
    print(f"Launching {name} from {full_path}")
    process = subprocess.Popen(cmd)
    return process

# Launch independent agents first
processes = []
print("Launching independent agents...")
for agent in independent_agents:
    process = launch_agent(agent)
    if process:
        processes.append((agent.get('name'), process))
    time.sleep(2)  # Give each agent time to start

# Launch dependent agents in order of dependency depth
print("Launching dependent agents...")
# Simple approach: try to launch agents multiple times until all are launched
remaining_agents = dependent_agents.copy()
max_attempts = 3
for attempt in range(max_attempts):
    if not remaining_agents:
        break
        
    still_remaining = []
    for agent in remaining_agents:
        # Check if all dependencies are launched
        deps = get_dependencies(agent)
        deps_launched = all(any(p[0] == dep for p in processes) for dep in deps)
        
        if deps_launched:
            process = launch_agent(agent)
            if process:
                processes.append((agent.get('name'), process))
            time.sleep(2)  # Give the agent time to start
        else:
            still_remaining.append(agent)
    
    remaining_agents = still_remaining
    if remaining_agents and attempt < max_attempts - 1:
        print(f"Waiting for dependencies to start before launching: {[a.get('name') for a in remaining_agents]}")
        time.sleep(5)  # Wait before next attempt

# If some agents couldn't be launched due to dependencies
if remaining_agents:
    print(f"Warning: Could not launch these agents due to missing dependencies: {[a.get('name') for a in remaining_agents]}")

print(f"Launched {len(processes)} agents")

# Wait for user to press Ctrl+C
try:
    print("Press Ctrl+C to stop all agents")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping all agents...")
    for name, process in processes:
        print(f"Stopping {name}...")
        try:
            # Try graceful termination first
            process.terminate()
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            # Force kill if needed
            process.kill()
    
    print("All agents stopped")
EOL

# Make the launch script executable
chmod +x launch_mvs.py

# Run the launch script
python3 launch_mvs.py 