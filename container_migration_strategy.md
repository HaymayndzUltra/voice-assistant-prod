# Containerization Strategy for AI System using Podman

## Overview
This document outlines a strategy for containerizing the AI System Monorepo using Podman, with a focus on ensuring system stability and proper agent management during the migration process.

## Why Podman?
- **Daemonless architecture**: Unlike Docker, Podman doesn't require a daemon process
- **Rootless containers**: Enhanced security with user namespace isolation
- **OCI compliance**: Full compatibility with Docker containers and Docker Compose
- **Pod-native support**: Better for multi-container applications that need to share resources

## Containerization Approach

### Phase 1: Analyze and Prepare

1. **Agent Dependency Mapping**
   - Create a complete dependency graph of all agents
   - Identify communication patterns between agents
   - Document resource requirements for each agent

2. **Container Grouping Strategy**
   - Group agents based on:
     - Dependency relationships
     - Resource requirements
     - Communication frequency
     - Startup order
   - Determine which agents should share containers vs. run in separate containers

3. **Networking Plan**
   - Design container networking to ensure proper communication between agents
   - Plan for service discovery in a containerized environment
   - Determine how to handle ZMQ connections across containers

4. **Volume Mapping**
   - Identify all persistent storage needs
   - Plan volume mounts for logs, models, and other data
   - Ensure proper permissions for mounted volumes

### Phase 2: Containerize Core Components

1. **Create Base Images**
   - Develop a base image with common dependencies
   - Create specialized images for different agent types (ML, networking, etc.)
   - Optimize images for size and startup time

2. **MVS Container First**
   - Start by containerizing the Minimal Viable System (MVS)
   - Focus on the 8 core agents identified in the stability testing
   - Ensure health checks work properly in containerized environment

3. **Container Health Checks**
   - Implement container-native health checks
   - Map agent health endpoints to container health checks
   - Configure proper restart policies based on health status

4. **Resource Limits**
   - Set appropriate CPU and memory limits for each container
   - Implement resource quotas to prevent resource contention
   - Configure proper scaling policies

### Phase 3: Compose and Orchestrate

1. **Podman Compose Setup**
   - Create a podman-compose.yml file for the MVS
   - Define proper startup order using depends_on
   - Configure networks and volumes

2. **Pod-Based Grouping**
   - Use Podman pods for agents that need to share resources
   - Group tightly coupled agents in the same pod
   - Configure proper inter-pod communication

3. **Layered Deployment Strategy**
   - Layer 0: Infrastructure services (networking, service discovery)
   - Layer 1: Core MVS agents
   - Layer 2: Secondary agents
   - Layer 3: Specialized and optional agents

4. **Automated Testing**
   - Create container-specific tests
   - Implement CI/CD pipeline for container builds
   - Test container startup and communication

### Phase 4: Incremental Migration

1. **Start with Stable Components**
   - Begin with the most stable and independent agents
   - Validate each containerized agent before proceeding
   - Use a hybrid approach during migration (some containerized, some not)

2. **Monitoring and Observability**
   - Implement container-specific monitoring
   - Set up centralized logging for containers
   - Create dashboards for container health and performance

3. **Progressive Rollout**
   - Deploy containers in stages
   - Validate each stage before proceeding
   - Maintain ability to roll back to non-containerized version

4. **Performance Tuning**
   - Optimize container resource allocation
   - Fine-tune network settings for container communication
   - Implement caching strategies where appropriate

## Implementation Plan

### Step 1: Create Base Dockerfile
```dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-update && apt-get install -y --no-install-recommends \
    build-essential \
    libzmq3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FORCE_LOCAL_MODE=true

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/models

# Default command
CMD ["python", "-u", "agent_runner.py"]
```

### Step 2: MVS Podman Compose File
```yaml
version: '3'

networks:
  agent_network:
    driver: bridge

volumes:
  logs_volume:
  models_volume:
  data_volume:

services:
  system_digital_twin:
    build:
      context: .
      dockerfile: docker/Dockerfile.system_digital_twin
    image: ai_system/system_digital_twin:latest
    container_name: system_digital_twin
    ports:
      - "7120:7120"
      - "7121:7121"
    volumes:
      - logs_volume:/app/logs
      - ./config:/app/config:ro
    environment:
      - AGENT_NAME=SystemDigitalTwin
      - AGENT_PORT=7120
      - HEALTH_CHECK_PORT=7121
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7121/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - agent_network
    restart: unless-stopped

  model_manager_agent:
    build:
      context: .
      dockerfile: docker/Dockerfile.model_manager
    image: ai_system/model_manager:latest
    container_name: model_manager_agent
    depends_on:
      system_digital_twin:
        condition: service_healthy
    ports:
      - "5570:5570"
      - "5571:5571"
    volumes:
      - logs_volume:/app/logs
      - models_volume:/app/models
      - ./config:/app/config:ro
    environment:
      - AGENT_NAME=ModelManagerAgent
      - AGENT_PORT=5570
      - HEALTH_CHECK_PORT=5571
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "python", "-c", "import zmq; context = zmq.Context(); socket = context.socket(zmq.REQ); socket.connect('tcp://localhost:5571'); socket.send_json({'action': 'health_check'}); socket.setsockopt(zmq.RCVTIMEO, 5000); print(socket.recv_json())"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - agent_network
    restart: unless-stopped

  # Add other MVS agents following the same pattern...
```

### Step 3: Agent Supervisor Container
```yaml
  agent_supervisor:
    build:
      context: .
      dockerfile: docker/Dockerfile.supervisor
    image: ai_system/agent_supervisor:latest
    container_name: agent_supervisor
    volumes:
      - logs_volume:/app/logs
      - ./config:/app/config:ro
    environment:
      - LOG_LEVEL=INFO
      - CONFIG_PATH=/app/config/startup_config.yaml
    networks:
      - agent_network
    restart: unless-stopped
```

## Migration Roadmap

1. **Week 1: Setup and Base Images**
   - Create base Docker images
   - Set up Podman environment
   - Implement container networking

2. **Week 2: MVS Containerization**
   - Containerize the 8 core MVS agents
   - Create docker-compose.yml for MVS
   - Test MVS container stability

3. **Week 3: Extend to Secondary Agents**
   - Containerize Layer 1 agents
   - Update compose file with new agents
   - Test inter-container communication

4. **Week 4: Complete Migration**
   - Containerize remaining agents
   - Implement monitoring and logging
   - Performance testing and optimization

## Best Practices for AI System Containerization

1. **Container-Specific Health Checks**
   - Implement health checks that verify agent functionality
   - Use appropriate timeouts for different agent types
   - Configure proper restart policies

2. **Resource Management**
   - Set appropriate memory limits to prevent OOM kills
   - Configure CPU shares based on agent priority
   - Use resource quotas to prevent resource contention

3. **Networking Considerations**
   - Use host networking for performance-critical agents
   - Implement proper service discovery
   - Configure ZMQ for containerized environment

4. **Logging and Monitoring**
   - Implement centralized logging
   - Set up container monitoring
   - Create dashboards for system health

5. **Security Considerations**
   - Run containers with least privilege
   - Implement proper secret management
   - Scan container images for vulnerabilities

## Conclusion
Containerizing the AI System using Podman provides significant benefits in terms of deployment consistency, resource isolation, and scalability. By following this phased approach, we can ensure a smooth migration while maintaining system stability.