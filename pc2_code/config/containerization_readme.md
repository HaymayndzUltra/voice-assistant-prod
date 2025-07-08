# PC2 Containerization Guide

This document outlines the containerization strategy and deployment instructions for the PC2 component of the AI System.

## Overview

The PC2 system has been containerized using Docker to improve deployment consistency, resource isolation, and scalability. The containerization follows a microservices approach with logical grouping of agents into specialized containers.

## Container Architecture

The PC2 system is divided into the following container groups:

1. **Core Infrastructure**
   - Provides essential services like health monitoring, resource management, and error reporting
   - Entry point for the system with high availability requirements

2. **Memory System**
   - Handles persistence, memory orchestration, and data caching
   - Contains the MemoryOrchestratorService and related agents

3. **AI Models**
   - Runs the primary AI model services
   - Requires GPU access for optimal performance

4. **User Services**
   - Manages user-facing functionality
   - Handles authentication and user interaction

5. **AI Monitoring**
   - Provides system monitoring, trust scoring, and proactive management
   - Collects metrics and health data

6. **Translation Services**
   - Provides language translation capabilities
   - Contains the NLLB translator service

## Prerequisites

- Docker Engine 23.0+
- Docker Compose 2.17+
- At least 16GB RAM
- NVIDIA GPU with CUDA 12.0+ (recommended)
- NVIDIA Container Toolkit installed

## Deployment Instructions

### 1. Prepare the Environment

Create the necessary directories for persistent data:

```bash
mkdir -p data/redis data/users data/monitoring
mkdir -p logs
mkdir -p models/language models/vision models/generative models/memory models/translation
```

### 2. Configure Environment Variables

Copy the environment template and edit it:

```bash
cp docker/config/env.template docker/pc2/config/.env
```

Edit the `.env` file to set:
- `MAINPC_IP`: IP address of the MainPC machine
- `PC2_IP`: IP address of the PC2 machine
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
- Any API keys or credentials needed

### 3. Build the Container Images

```bash
cd docker/pc2
docker-compose -f docker-compose.enhanced.yml build
```

### 4. Start the Containers

Start the full stack:

```bash
docker-compose -f docker-compose.enhanced.yml up -d
```

Or start individual container groups:

```bash
# Start just core infrastructure and memory system
docker-compose -f docker-compose.enhanced.yml up -d core-infrastructure redis memory-system
```

### 5. Verify Deployment

Check if all containers are running:

```bash
docker-compose -f docker-compose.enhanced.yml ps
```

View logs for a specific service:

```bash
docker-compose -f docker-compose.enhanced.yml logs -f memory-system
```

### 6. Container Health Checks

All containers have built-in health checks that monitor:
- Process existence for each agent
- Port availability
- Health check API responses

Monitor container health:

```bash
docker ps --format "{{.Names}}: {{.Status}}"
```

## Networking

The containerized system uses three distinct networks:

1. `ai_system_network`: Primary network for container communication
2. `ai_internal_network`: Isolated network for sensitive services
3. `ai_external_network`: Network for services that need external connectivity

## Data Persistence

All persistent data is stored in mounted volumes:

- `/app/data`: General data storage
- `/app/logs`: Log files
- `/app/models`: AI models
- `/app/data/redis`: Redis persistence
- `/app/data/users`: User-specific data

## Troubleshooting

### Common Issues

1. **Container fails to start**
   - Check logs: `docker-compose logs -f [service_name]`
   - Verify environment variables are set correctly
   - Ensure resource limits are appropriate

2. **Communication issues between containers**
   - Check network configuration
   - Verify service discovery settings
   - Ensure ports are properly exposed

3. **Performance issues**
   - Monitor resource usage with `docker stats`
   - Adjust container resource limits as needed
   - Consider scaling horizontally for high-load services

### Restarting Services

To restart a specific service:

```bash
docker-compose -f docker-compose.enhanced.yml restart [service_name]
```

To restart the entire system:

```bash
docker-compose -f docker-compose.enhanced.yml down
docker-compose -f docker-compose.enhanced.yml up -d
```

## Rollback Procedure

In case of deployment issues, roll back to the previous version:

1. Stop all containers:
   ```bash
   docker-compose -f docker-compose.enhanced.yml down
   ```

2. Restore from backup (if available):
   ```bash
   # Restore data from backup location
   cp -r /path/to/backup/data/* ./data/
   ```

3. Use previous container images:
   ```bash
   # Pull previous image versions
   docker pull [repository]/pc2:[previous-tag]
   ```

4. Start with previous versions:
   ```bash
   # Edit docker-compose.yml to use previous versions
   # Then start containers
   docker-compose -f docker-compose.enhanced.yml up -d
   ``` 