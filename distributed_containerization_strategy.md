# Distributed Containerization Strategy for Multi-Machine Deployment

## Current Setup Analysis
- Single git repository containing code for both machines (MainPC and PC2)
- Agents distributed across multiple physical machines
- Cross-machine communication requirements
- Shared codebase but different runtime environments

## Recommended Approach: Unified Repository with Environment-Specific Deployments

### 1. Repository Structure Optimization

```
AI_System_Monorepo/
├── common/                  # Shared code and utilities
│   ├── base_agent.py
│   ├── zmq_helper.py
│   └── ...
├── main_pc_code/            # MainPC-specific agents
│   ├── agents/
│   └── ...
├── pc2_code/                # PC2-specific agents
│   ├── agents/
│   └── ...
├── docker/                  # Containerization files
│   ├── common/              # Base images and shared configurations
│   │   ├── Dockerfile.base
│   │   └── requirements.common.txt
│   ├── mainpc/              # MainPC-specific containers
│   │   ├── docker-compose.yml
│   │   ├── Dockerfile.mainpc
│   │   └── env.mainpc
│   └── pc2/                 # PC2-specific containers
│       ├── docker-compose.yml
│       ├── Dockerfile.pc2
│       └── env.pc2
└── scripts/                 # Deployment and management scripts
    ├── deploy_mainpc.sh
    ├── deploy_pc2.sh
    └── deploy_all.sh
```

### 2. Container Design for Distributed Architecture

#### Base Container Strategy
- Create a common base image with shared dependencies
- Extend with machine-specific images for MainPC and PC2
- Use build arguments to customize for each environment

```dockerfile
# docker/common/Dockerfile.base
FROM python:3.9-slim

ARG MACHINE_TYPE=mainpc
ENV MACHINE_TYPE=${MACHINE_TYPE}

# Install common dependencies
RUN apt-update && apt-get install -y --no-install-recommends \
    build-essential \
    libzmq3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy common requirements first
COPY docker/common/requirements.common.txt /app/requirements.common.txt
RUN pip install --no-cache-dir -r requirements.common.txt

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/models

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FORCE_LOCAL_MODE=false

# Default command
CMD ["python", "-u", "agent_runner.py"]
```

#### Machine-Specific Extensions

```dockerfile
# docker/mainpc/Dockerfile.mainpc
FROM ai_system/base:latest

# Copy MainPC-specific requirements
COPY docker/mainpc/requirements.mainpc.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy MainPC-specific code
COPY main_pc_code/ /app/main_pc_code/
COPY common/ /app/common/

# Set MainPC-specific environment variables
ENV MACHINE_TYPE=mainpc
ENV CONFIG_PATH=/app/config/mainpc_config.yaml

# Default command
CMD ["python", "-u", "/app/main_pc_code/utils/agent_supervisor.py"]
```

```dockerfile
# docker/pc2/Dockerfile.pc2
FROM ai_system/base:latest

# Copy PC2-specific requirements
COPY docker/pc2/requirements.pc2.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy PC2-specific code
COPY pc2_code/ /app/pc2_code/
COPY common/ /app/common/

# Set PC2-specific environment variables
ENV MACHINE_TYPE=pc2
ENV CONFIG_PATH=/app/config/pc2_config.yaml

# Default command
CMD ["python", "-u", "/app/pc2_code/utils/agent_supervisor.py"]
```

### 3. Network Configuration for Cross-Machine Communication

#### Shared Network Configuration
Create a shared network configuration that both machines can use:

```yaml
# docker/shared/docker-compose.network.yml
version: '3'

networks:
  ai_system_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

#### Machine-Specific Compose Files with Fixed IPs

```yaml
# docker/mainpc/docker-compose.yml
version: '3'

networks:
  ai_system_network:
    external: true

services:
  system_digital_twin:
    image: ai_system/mainpc:latest
    container_name: system_digital_twin
    networks:
      ai_system_network:
        ipv4_address: 172.20.0.10
    environment:
      - AGENT_NAME=SystemDigitalTwin
      - AGENT_PORT=7120
      - PC2_IP=192.168.1.102  # IP of the PC2 physical machine
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    command: ["python", "-u", "/app/main_pc_code/agents/system_digital_twin.py"]

  # Other MainPC agents...
```

```yaml
# docker/pc2/docker-compose.yml
version: '3'

networks:
  ai_system_network:
    external: true

services:
  authentication_agent:
    image: ai_system/pc2:latest
    container_name: authentication_agent
    networks:
      ai_system_network:
        ipv4_address: 172.20.1.10
    environment:
      - AGENT_NAME=AuthenticationAgent
      - AGENT_PORT=6120
      - MAINPC_IP=192.168.1.101  # IP of the MainPC physical machine
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    command: ["python", "-u", "/app/pc2_code/agents/authentication_agent.py"]

  # Other PC2 agents...
```

### 4. Environment-Specific Configuration

Create environment files for each machine:

```
# docker/mainpc/config/env.mainpc
MACHINE_TYPE=mainpc
MAINPC_IP=192.168.1.101
PC2_IP=192.168.1.102
BIND_ADDRESS=0.0.0.0
ENABLE_METRICS=true
LOG_LEVEL=INFO
```

```
# docker/pc2/config/env.pc2
MACHINE_TYPE=pc2
MAINPC_IP=192.168.1.101
PC2_IP=192.168.1.102
BIND_ADDRESS=0.0.0.0
ENABLE_METRICS=true
LOG_LEVEL=INFO
```

### 5. Deployment Strategy

#### Deployment Scripts

Create machine-specific deployment scripts:

```bash
# !/bin/bash
# scripts/deploy_mainpc.sh

# Set environment variables
export MACHINE_TYPE=mainpc
export COMPOSE_PROJECT_NAME=ai_system_mainpc

# Navigate to project root
cd "$(dirname "$0")/.."

# Build images
docker build -t ai_system/base:latest -f docker/common/Dockerfile.base --build-arg MACHINE_TYPE=mainpc .
docker build -t ai_system/mainpc:latest -f docker/mainpc/Dockerfile.mainpc .

# Create network if it doesn't exist
| docker network create ai_system_network 2>/dev/null |  | true |

# Deploy using docker-compose
docker-compose -f docker/mainpc/docker-compose.yml up -d
```

```bash
# !/bin/bash
# scripts/deploy_pc2.sh

# Set environment variables
export MACHINE_TYPE=pc2
export COMPOSE_PROJECT_NAME=ai_system_pc2

# Navigate to project root
cd "$(dirname "$0")/.."

# Build images
docker build -t ai_system/base:latest -f docker/common/Dockerfile.base --build-arg MACHINE_TYPE=pc2 .
docker build -t ai_system/pc2:latest -f docker/pc2/Dockerfile.pc2 .

# Create network if it doesn't exist
| docker network create ai_system_network 2>/dev/null |  | true |

# Deploy using docker-compose
docker-compose -f docker/pc2/docker-compose.yml up -d
```

#### CI/CD Pipeline Integration

```yaml
# .github/workflows/build-deploy.yml
name: Build and Deploy

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build-mainpc:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build MainPC images
| run: |
          docker build -t ai_system/base:latest -f docker/common/Dockerfile.base --build-arg MACHINE_TYPE=mainpc .
          docker build -t ai_system/mainpc:latest -f docker/mainpc/Dockerfile.mainpc .

  build-pc2:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build PC2 images
| run: |
          docker build -t ai_system/base:latest -f docker/common/Dockerfile.base --build-arg MACHINE_TYPE=pc2 .
          docker build -t ai_system/pc2:latest -f docker/pc2/Dockerfile.pc2 .
```

### 6. Cross-Machine Communication

#### ZMQ Configuration for Containers

Update the ZMQ connection code to handle container networking:

```python
def get_zmq_address(service_name, machine_type=None):
    """Get the ZMQ address for a service based on machine type."""
    # Get environment variables
    mainpc_ip = os.environ.get('MAINPC_IP', '172.20.0.10')
    pc2_ip = os.environ.get('PC2_IP', '172.20.1.10')

    # Determine which IP to use based on service location
    if machine_type is None:
        machine_type = os.environ.get('MACHINE_TYPE', 'mainpc')

    # Use the appropriate IP based on where the service is located
    if service_name in MAINPC_SERVICES:
        ip = mainpc_ip
    elif service_name in PC2_SERVICES:
        ip = pc2_ip
    else:
        # Default to local machine
        ip = mainpc_ip if machine_type == 'mainpc' else pc2_ip

    # Get the port for this service
    port = SERVICE_PORTS.get(service_name, 5000)

    return f"tcp://{ip}:{port}"
```

### 7. Data Synchronization Strategy

For shared data that needs to be consistent across machines:

1. **Git-Based Synchronization**:
   - Use git hooks to automatically pull changes to both machines
   - Implement a CI/CD pipeline that deploys to both machines

2. **Volume Mounting**:
   - Mount specific directories from the host to containers
   - Use rsync or similar tools to keep directories in sync between machines

3. **Distributed Storage**:
   - Consider using a distributed file system for shared data
   - Alternatively, use a database or message queue for shared state

### 8. Testing and Validation

1. **Local Testing**:
   - Test the full system on a single machine first
   - Use Docker's network features to simulate the distributed environment

2. **Distributed Testing**:
   - Deploy to actual machines and test cross-machine communication
   - Validate that all agents can communicate properly

3. **Monitoring**:
   - Implement centralized logging across both machines
   - Set up monitoring to track system health across the distributed environment

## Implementation Roadmap

### Phase 1: Containerize Each Machine Separately
1. Start with MainPC containerization
2. Test and validate MainPC containers
3. Proceed with PC2 containerization
4. Test and validate PC2 containers

### Phase 2: Establish Cross-Machine Communication
1. Configure network for cross-machine communication
2. Test ZMQ connections between containers on different machines
3. Validate service discovery across machines

### Phase 3: Implement Deployment Automation
1. Create deployment scripts for each machine
2. Set up CI/CD pipeline for automated builds
3. Implement monitoring and logging

### Phase 4: Full System Validation
1. Deploy the complete system across both machines
2. Run comprehensive tests to validate functionality
3. Monitor performance and stability

## Conclusion

This distributed containerization strategy allows you to maintain a single git repository while deploying to multiple machines. By using machine-specific Docker images and compose files, you can ensure that each machine runs only the agents it needs, while the shared codebase ensures consistency across the system. The fixed IP addressing and environment-specific configuration make cross-machine communication reliable and predictable.