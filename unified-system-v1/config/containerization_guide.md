# PC2 System Containerization Guide with Podman

## Overview

This guide outlines the process for containerizing the PC2 system using Podman. The system has been organized into logical container groups based on agent functionality and dependencies.

## Container Groups

Based on the `startup_config_fixed.yaml` file, we've organized the agents into the following container groups:

1. **Core Infrastructure Container**
   - ResourceManager, HealthMonitor, TaskScheduler, AdvancedRouter
   - Foundation services that other containers depend on
   - Note: SystemDigitalTwin agent is only on main_pc and should not be included in PC2 containers

2. **Memory & Storage Container**
   - UnifiedMemoryReasoningAgent, MemoryManager, EpisodicMemoryAgent, ContextManager, ExperienceTracker, etc.
   - Handles all memory and storage operations

3. **Security & Authentication Container**
   - AuthenticationAgent, UnifiedErrorAgent, UnifiedUtilsAgent, AgentTrustScorer
   - Manages security and authentication services

4. **Integration & Communication Container**
   - TieredResponder, AsyncProcessor, CacheManager, RemoteConnectorAgent, FileSystemAssistantAgent
   - Handles communication between containers and external systems

5. **Monitoring & Support Container**
   - PerformanceMonitor, PerformanceLoggerAgent, SelfHealingAgent, ProactiveContextMonitor, RCAAgent
   - Monitors system health and provides support services

6. **Dream & Tutoring Container**
   - DreamWorldAgent, DreamingModeAgent, TutoringServiceAgent, TutorAgent
   - Specialized services for dreaming and tutoring functionality

7. **Web & External Services Container**
   - UnifiedWebAgent
   - Handles web-based interactions and external services

## Prerequisites

1. Install Podman:
   ```bash
   sudo apt-get update
   sudo apt-get install -y podman
   ```

2. Create a Podman network for inter-container communication:
   ```bash
   podman network create pc2-network
   ```

## Containerization Steps

### 1. Create Base Image

First, create a base image with common dependencies:

```dockerfile
# pc2_code/docker/Dockerfile.base
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libzmq3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install common Python dependencies
COPY requirements.common.txt .
RUN pip install --no-cache-dir -r requirements.common.txt

# Set environment variables
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
ENV DEBUG_MODE=false
ENV BIND_ADDRESS=0.0.0.0

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/config
```

### 2. Create Container-Specific Dockerfiles

For each container group, create a specific Dockerfile:

#### Core Infrastructure Container

```dockerfile
# pc2_code/docker/Dockerfile.core_infrastructure
FROM pc2-base:latest

WORKDIR /app

# Copy specific agent code
COPY pc2_code/agents/resource_manager.py /app/pc2_code/agents/
COPY pc2_code/agents/health_monitor.py /app/pc2_code/agents/
COPY pc2_code/agents/task_scheduler.py /app/pc2_code/agents/
COPY pc2_code/agents/advanced_router.py /app/pc2_code/agents/
# SystemDigitalTwin is not included as it's only on main_pc

# Copy configuration
COPY pc2_code/config/startup_config_fixed.yaml /app/pc2_code/config/startup_config.yaml
COPY pc2_code/config/network_config.yaml /app/pc2_code/config/

# Install specific dependencies
COPY pc2_code/docker/requirements.core_infrastructure.txt .
RUN pip install --no-cache-dir -r requirements.core_infrastructure.txt

# Set entry point
CMD ["python", "-m", "pc2_code.scripts.start_container", "core_infrastructure"]
```

(Similar Dockerfiles would be created for each container group)

### 3. Create Container Start Script

Create a script to start agents within each container:

```python
# pc2_code/scripts/start_container.py
import os
import sys
import yaml
import subprocess
import time
import signal
import threading

def load_config():
    """Load the startup configuration."""
    config_path = os.path.join("pc2_code", "config", "startup_config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def get_container_agents(config, container_group):
    """Get agents for a specific container group."""
    container_agents = []
    
    # Map container group names to comment markers in the config
    group_markers = {
        "core_infrastructure": "Group 1: Core Infrastructure Container",
        "memory_storage": "Group 2: Memory & Storage Container",
        "security_authentication": "Group 3: Security & Authentication Container",
        "integration_communication": "Group 4: Integration & Communication Container",
        "monitoring_support": "Group 5: Monitoring & Support Container",
        "dream_tutoring": "Group 6: Dream & Tutoring Container",
        "web_external": "Group 7: Web & External Services Container"
    }
    
    marker = group_markers.get(container_group)
    if not marker:
        print(f"Unknown container group: {container_group}")
        return []
    
    # Find agents in the specified group
    in_group = False
    for agent in config["pc2_services"]:
        if in_group and (agent.get("name", "").strip().startswith("#") and "Group" in agent.get("name", "")):
            # We've hit the next group marker
            break
            
        if in_group:
            container_agents.append(agent)
            
        if agent.get("name", "").strip().startswith("#") and marker in agent.get("name", ""):
            in_group = True
    
    return container_agents

def start_agent(agent):
    """Start a single agent."""
    script_path = agent["script_path"]
    cmd = ["python", script_path]
    
    # Add environment variables
    env = os.environ.copy()
    env["AGENT_NAME"] = agent["name"]
    env["AGENT_PORT"] = str(agent["port"])
    env["HEALTH_CHECK_PORT"] = str(agent["health_check_port"])
    
    # Start the agent
    print(f"Starting agent: {agent['name']}")
    return subprocess.Popen(cmd, env=env)

def main():
    if len(sys.argv) < 2:
        print("Usage: python start_container.py <container_group>")
        sys.exit(1)
    
    container_group = sys.argv[1]
    config = load_config()
    agents = get_container_agents(config, container_group)
    
    if not agents:
        print(f"No agents found for container group: {container_group}")
        sys.exit(1)
    
    # Start agents
    processes = []
    for agent in agents:
        proc = start_agent(agent)
        processes.append((agent["name"], proc))
    
    # Handle signals
    def signal_handler(sig, frame):
        print("Shutting down agents...")
        for name, proc in processes:
            print(f"Stopping {name}...")
            proc.terminate()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Monitor processes
    while True:
        for i, (name, proc) in enumerate(processes):
            if proc.poll() is not None:
                print(f"Agent {name} exited with code {proc.returncode}")
                # Restart the agent
                agent = next(a for a in agents if a["name"] == name)
                new_proc = start_agent(agent)
                processes[i] = (name, new_proc)
        time.sleep(5)

if __name__ == "__main__":
    main()
```

### 4. Create Podman Compose File

Create a Podman Compose file to orchestrate all containers:

```yaml
# pc2_code/docker/podman-compose.yaml
version: '3'

services:
  core_infrastructure:
    build:
      context: ../..
      dockerfile: pc2_code/docker/Dockerfile.core_infrastructure
    image: pc2-core-infrastructure:latest
    container_name: pc2-core-infrastructure
    networks:
      - pc2-network
    volumes:
      - ../logs:/app/logs
      - ../config:/app/config
      - ../data:/app/data
    restart: unless-stopped
    environment:
      - PYTHONPATH=/app
      - LOG_LEVEL=INFO
      - DEBUG_MODE=false
      - BIND_ADDRESS=0.0.0.0
    healthcheck:
      test: ["CMD", "python", "-m", "pc2_code.scripts.health_check", "core_infrastructure"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  memory_storage:
    build:
      context: ../..
      dockerfile: pc2_code/docker/Dockerfile.memory_storage
    image: pc2-memory-storage:latest
    container_name: pc2-memory-storage
    depends_on:
      - core_infrastructure
    networks:
      - pc2-network
    volumes:
      - ../logs:/app/logs
      - ../config:/app/config
      - ../data:/app/data
    restart: unless-stopped
    environment:
      - PYTHONPATH=/app
      - LOG_LEVEL=INFO
      - DEBUG_MODE=false
      - BIND_ADDRESS=0.0.0.0
    healthcheck:
      test: ["CMD", "python", "-m", "pc2_code.scripts.health_check", "memory_storage"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # Define similar services for other container groups
  security_authentication:
    # ...

  integration_communication:
    # ...

  monitoring_support:
    # ...

  dream_tutoring:
    # ...

  web_external:
    # ...

networks:
  pc2-network:
    external: true
```

### 5. Create Health Check Script

Create a health check script for container health monitoring:

```python
# pc2_code/scripts/health_check.py
import os
import sys
import yaml
import requests
import time

def load_config():
    """Load the startup configuration."""
    config_path = os.path.join("pc2_code", "config", "startup_config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def get_container_agents(config, container_group):
    """Get agents for a specific container group."""
    # (Same implementation as in start_container.py)
    # ...

def check_agent_health(agent):
    """Check health of a single agent."""
    health_url = f"http://localhost:{agent['health_check_port']}/health"
    try:
        response = requests.get(health_url, timeout=5)
        if response.status_code == 200:
            return True
        return False
    except Exception:
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python health_check.py <container_group>")
        sys.exit(1)
    
    container_group = sys.argv[1]
    config = load_config()
    agents = get_container_agents(config, container_group)
    
    if not agents:
        print(f"No agents found for container group: {container_group}")
        sys.exit(1)
    
    # Check health of all agents in the container
    all_healthy = True
    for agent in agents:
        if not check_agent_health(agent):
            all_healthy = False
            print(f"Agent {agent['name']} is unhealthy")
    
    if all_healthy:
        print(f"All agents in {container_group} are healthy")
        sys.exit(0)
    else:
        print(f"One or more agents in {container_group} are unhealthy")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Deployment Process

1. **Build the base image**:
   ```bash
   cd pc2_code/docker
   podman build -t pc2-base:latest -f Dockerfile.base ../..
   ```

2. **Build all container images**:
   ```bash
   podman-compose -f podman-compose.yaml build
   ```

3. **Start all containers**:
   ```bash
   podman-compose -f podman-compose.yaml up -d
   ```

4. **Check container status**:
   ```bash
   podman-compose -f podman-compose.yaml ps
   ```

5. **View container logs**:
   ```bash
   podman-compose -f podman-compose.yaml logs -f core_infrastructure
   ```

## Volume Mounts

Each container mounts the following volumes:

1. **Logs**: `/app/logs` - For agent log files
2. **Config**: `/app/config` - For configuration files
3. **Data**: `/app/data` - For persistent data storage

## Network Configuration

All containers connect to the `pc2-network` Podman network, allowing them to communicate with each other using service names as hostnames.

## Troubleshooting

1. **Container fails to start**:
   - Check container logs: `podman logs pc2-core-infrastructure`
   - Verify that all required dependencies are installed
   - Ensure that the startup configuration is correct

2. **Agent health check fails**:
   - Check agent logs in the `/app/logs` directory
   - Verify that the agent is properly configured
   - Check if the agent's dependencies are running

3. **Communication issues between containers**:
   - Verify that all containers are on the same network
   - Check that the correct ports are exposed
   - Ensure that the agent is binding to `0.0.0.0` instead of `localhost`

## Resource Management

Resource limits for each container are defined in the `container_resource_limits` section of the startup configuration. Adjust these limits based on the available resources on your system.

## Security Considerations

1. **Network Security**:
   - Use secure ZMQ connections between agents
   - Implement proper authentication for agent communication
   - Consider using Podman's built-in security features

2. **Data Security**:
   - Ensure that sensitive data is properly encrypted
   - Use secure storage for credentials and keys
   - Implement proper access controls for mounted volumes

## Maintenance

1. **Updating Containers**:
   - Rebuild container images when agent code changes
   - Use versioning for container images
   - Implement rolling updates to minimize downtime

2. **Monitoring**:
   - Set up monitoring for container health
   - Configure alerts for container failures
   - Regularly check container logs for issues

3. **Backup and Recovery**:
   - Regularly backup mounted volumes
   - Implement disaster recovery procedures
   - Test recovery procedures periodically 