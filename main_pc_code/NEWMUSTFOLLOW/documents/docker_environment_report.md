# Operation: Build Final MainPC Docker Environment

**Date**: July 3, 2025

## Task Summary
Created the complete, final Docker environment for the MainPC system with a secure port mapping strategy that minimizes external exposure while enabling internal communication.

## Components Created

### 1. Dockerfile
- Created an optimized Dockerfile at the repository root
- Used a granular COPY strategy to include only necessary files
- Installed all required dependencies
- Set up the proper environment variables

### 2. run_group.sh Script
- Created a robust script in the scripts/ directory
- Handles agent group startup based on the startup_config.yaml
- Includes process monitoring and automatic restart capabilities
- Implements proper signal handling for graceful shutdowns

### 3. docker-compose.yml
- Created a complete docker-compose.yml at the repository root
- Configured services for each agent_group from startup_config.yaml
- Implemented secure port mapping strategy:
  - Only exposed the RequestCoordinator port (26002) as the main entry point
  - All other services communicate internally via the Docker network
- Added proper dependencies between services
- Configured GPU resources for services that require them
- Added health checks and restart policies

## Security Improvements
- Minimized attack surface by exposing only one necessary external port
- Internal services communicate securely over the Docker network
- Implemented proper dependency chains to ensure services start in the correct order

## Next Steps
The system is ready for launch with `docker-compose up` followed by validation testing to confirm functionality.

## Copy-Friendly Outputs

### Dockerfile
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy only necessary files for dependency installation
COPY pyproject.toml requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir -r requirements.txt

# Copy specific directories and files
COPY main_pc_code/ ./main_pc_code/
COPY common/ ./common/
COPY pc2_code/ ./pc2_code/
COPY utils/ ./utils/
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY config/ ./config/
COPY data/ ./data/

# Create necessary directories
RUN mkdir -p logs models

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set working directory for runtime
WORKDIR /app

# Default command (will be overridden by docker-compose)
CMD ["python", "-m", "main_pc_code.scripts.container_healthcheck"]
```

### docker-compose.yml
```yaml
version: '3.8'

networks:
  ai_system_network:
    driver: bridge

services:
  # Redis for HA service registry
  redis:
    image: redis:7-alpine
    container_name: redis
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks: [ai_system_network]

  # Service Registry - core service discovery
  service-registry:
    build: .
    container_name: service-registry
    command: ["python", "main_pc_code/agents/service_registry_agent.py", "--backend", "redis", "--redis-url", "redis://redis:6379/0"]
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./models:/app/models
    depends_on:
      redis:
        condition: service_healthy
    environment:
      - SERVICE_REGISTRY_BACKEND=redis
      - SERVICE_REGISTRY_REDIS_URL=redis://redis:6379/0
    networks: [ai_system_network]
    restart: unless-stopped

  # Core Services
  core_services:
    build: .
    container_name: mainpc-core_services
    command: ["./scripts/run_group.sh", "core_services"]
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./models:/app/models
    depends_on:
      - service-registry
    networks: [ai_system_network]
    # Only expose the RequestCoordinator port as the main entry point
    ports:
      - "26002:26002"
    restart: unless-stopped

  # Memory System
  memory_system:
    build: .
    container_name: mainpc-memory_system
    command: ["./scripts/run_group.sh", "memory_system"]
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./models:/app/models
    depends_on:
      - core_services
    networks: [ai_system_network]
    restart: unless-stopped

  # Utility Services
  utility_services:
    build: .
    container_name: mainpc-utility_services
    command: ["./scripts/run_group.sh", "utility_services"]
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./models:/app/models
    depends_on:
      - core_services
      - gpu_infrastructure
    networks: [ai_system_network]
    restart: unless-stopped

  # GPU Infrastructure
  gpu_infrastructure:
    build: .
    container_name: mainpc-gpu_infrastructure
    command: ["./scripts/run_group.sh", "gpu_infrastructure"]
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./models:/app/models
    depends_on:
      - core_services
    networks: [ai_system_network]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: unless-stopped

  # Reasoning Services
  reasoning_services:
    build: .
    container_name: mainpc-reasoning_services
    command: ["./scripts/run_group.sh", "reasoning_services"]
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./models:/app/models
    depends_on:
      - gpu_infrastructure
    networks: [ai_system_network]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: unless-stopped

  # Vision Processing
  vision_processing:
    build: .
    container_name: mainpc-vision_processing
    command: ["./scripts/run_group.sh", "vision_processing"]
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./models:/app/models
    depends_on:
      - gpu_infrastructure
    networks: [ai_system_network]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: unless-stopped

  # Learning Knowledge
  learning_knowledge:
    build: .
    container_name: mainpc-learning_knowledge
    command: ["./scripts/run_group.sh", "learning_knowledge"]
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./models:/app/models
    depends_on:
      - memory_system
      - utility_services
    networks: [ai_system_network]
    restart: unless-stopped

  # Language Processing
  language_processing:
    build: .
    container_name: mainpc-language_processing
    command: ["./scripts/run_group.sh", "language_processing"]
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./models:/app/models
    depends_on:
      - memory_system
      - utility_services
      - gpu_infrastructure
    networks: [ai_system_network]
    restart: unless-stopped

  # Speech Services
  speech_services:
    build: .
    container_name: mainpc-speech_services
    command: ["./scripts/run_group.sh", "speech_services"]
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./models:/app/models
    depends_on:
      - language_processing
      - gpu_infrastructure
    networks: [ai_system_network]
    restart: unless-stopped

  # Audio Interface
  audio_interface:
    build: .
    container_name: mainpc-audio_interface
    command: ["./scripts/run_group.sh", "audio_interface"]
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./models:/app/models
    depends_on:
      - speech_services
    networks: [ai_system_network]
    restart: unless-stopped

  # Emotion System
  emotion_system:
    build: .
    container_name: mainpc-emotion_system
    command: ["./scripts/run_group.sh", "emotion_system"]
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./models:/app/models
    depends_on:
      - core_services
    networks: [ai_system_network]
    restart: unless-stopped

volumes:
  redis_data:
    driver: local
```

### run_group.sh
```bash
#!/bin/bash

# This script starts all agents in a specified group from startup_config.yaml
# Usage: ./run_group.sh <group_name>

set -e

# Get the group name from the first argument
GROUP_NAME=$1

if [ -z "$GROUP_NAME" ]; then
    echo "Error: Group name not provided"
    echo "Usage: ./run_group.sh <group_name>"
    exit 1
fi

echo "Starting agents in group: $GROUP_NAME"

# Path to the startup config file
CONFIG_FILE="main_pc_code/config/startup_config.yaml"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found at $CONFIG_FILE"
    exit 1
fi

# Use Python to parse the YAML file and extract agent information
python3 -c "
import yaml
import sys
import subprocess
import os
import time
import signal
import threading
from typing import Dict, List

# Global variables
processes = []
stop_flag = False

# Signal handler for graceful shutdown
def signal_handler(sig, frame):
    global stop_flag
    print('\\nShutting down all agents...')
    stop_flag = True
    for p in processes:
        if p.poll() is None:  # If process is still running
            p.terminate()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Load the config file
with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f)

# Check if the group exists
if '$GROUP_NAME' not in config.get('agent_groups', {}):
    print(f'Error: Group \\'$GROUP_NAME\\' not found in config')
    sys.exit(1)

# Get the agents in the group
agents = config['agent_groups']['$GROUP_NAME']

# Function to monitor a process and restart it if it fails
def monitor_process(name, cmd, restart_delay=5):
    global stop_flag
    while not stop_flag:
        try:
            print(f'Starting agent: {name}')
            process = subprocess.Popen(cmd, shell=True)
            processes.append(process)
            process.wait()
            if stop_flag:
                break
            print(f'Agent {name} exited with code {process.returncode}')
            if process.returncode != 0:
                print(f'Restarting {name} in {restart_delay} seconds...')
                time.sleep(restart_delay)
            else:
                break
        except Exception as e:
            print(f'Error running {name}: {e}')
            time.sleep(restart_delay)

# Start each agent in the group
threads = []
for agent_name, agent_config in agents.items():
    script_path = agent_config.get('script_path')
    if not script_path:
        print(f'Warning: No script path for agent {agent_name}')
        continue
        
    # Build the command with any additional arguments
    cmd = f'python {script_path}'
    if 'command_args' in agent_config:
        cmd += f' {agent_config[\"command_args\"]}'
        
    # Start the agent in a separate thread
    thread = threading.Thread(target=monitor_process, args=(agent_name, cmd))
    thread.daemon = True
    thread.start()
    threads.append(thread)
    
    # Small delay to avoid startup race conditions
    time.sleep(1)

# Wait for all threads to complete
try:
    while any(t.is_alive() for t in threads):
        time.sleep(1)
except KeyboardInterrupt:
    signal_handler(signal.SIGINT, None)

print(f'All agents in group \\'$GROUP_NAME\\' have exited')
"

# If the Python script exits with an error, this will run
if [ $? -ne 0 ]; then
    echo "Failed to start agents in group: $GROUP_NAME"
    exit 1
fi

exit 0
``` 