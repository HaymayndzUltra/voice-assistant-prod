# PC2 Docker Environment

This directory contains the Docker configuration for containerizing all PC2 agents.

## Overview

The PC2 Docker setup provides isolated containers for each agent with proper networking, resource limits, and inter-container communication. All agents are orchestrated via Docker Compose.

## Architecture

### Network Architecture
- **pc2_network**: Internal bridge network (172.22.0.0/16) for PC2 agent communication
- **mainpc_bridge**: External network for PC2 ↔ MainPC communication
- All agents communicate via container names internally

### Service Groups
1. **Infrastructure**: Redis, ObservabilityHub
2. **Core Memory**: MemoryOrchestratorService
3. **Processing**: TieredResponder, AsyncProcessor, TaskScheduler
4. **Specialized**: Authentication, Web, FileSystem agents
5. **GPU Services**: VisionProcessingAgent (RTX 3060)

## Quick Start

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+
- NVIDIA Container Toolkit (for GPU support)
- Network connectivity to MainPC (192.168.100.16)

### Starting the Environment

1. **Copy environment configuration**:
   ```bash
   cp pc2_code/docker/.env.example pc2_code/docker/.env
   # Edit .env as needed
   ```

2. **Start all services**:
   ```bash
   ./pc2_code/docker/start_pc2_docker.sh
   ```

3. **Monitor services**:
   ```bash
   # View logs
   docker-compose -f pc2_code/docker/docker-compose.yml logs -f

   # Check service health
   docker-compose -f pc2_code/docker/docker-compose.yml ps
   ```

### Stopping the Environment

```bash
./pc2_code/docker/stop_pc2_docker.sh
```

## Service Details

### Core Services

| Service | Port | Health Port | Description |
|---------|------|-------------|-------------|
| MemoryOrchestratorService | 7140 | 8140 | Central memory management |
| TieredResponder | 7100 | 8100 | Multi-tier response system |
| ObservabilityHub | 9000 | 9100 | Monitoring and metrics |

### Complete Port Mapping
See [PORT_MAPPING.md](PORT_MAPPING.md) for full details.

## Configuration

### Environment Variables
Key environment variables (set in `.env`):
- `MAINPC_HOST`: MainPC IP address (default: 192.168.100.16)
- `LOG_LEVEL`: Logging level (INFO, DEBUG, ERROR)
- `CUDA_VISIBLE_DEVICES`: GPU device for vision processing

### Resource Limits
Each service has configured resource limits:
```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 4096M
```

### Volumes
- `pc2_logs`: Application logs
- `pc2_data`: Persistent data (databases, files)
- `pc2_models`: ML model storage
- `pc2_cache`: Cache data
- `redis_data`: Redis persistence

## Cross-Machine Communication

### PC2 → MainPC
- RemoteConnectorAgent (7124) acts as the bridge
- ObservabilityHub syncs metrics to MainPC hub

### MainPC → PC2
- Requests route through RemoteConnectorAgent
- Service Registry on MainPC knows PC2 endpoints

## Monitoring

### Health Checks
All services have health endpoints:
```bash
# Check individual service
curl http://localhost:8140/health  # MemoryOrchestratorService

# Check all services
for port in {8100..8150}; do
  echo "Checking port $port"
  curl -s http://localhost:$port/health || echo "No service on $port"
done
```

### Metrics
ObservabilityHub exposes Prometheus metrics:
```bash
curl http://localhost:9000/metrics
```

## Troubleshooting

### Common Issues

1. **Port conflicts**:
   ```bash
   # Check if ports are in use
   netstat -tulpn | grep -E "7[0-9]{3}|8[0-9]{3}"
   ```

2. **Container startup failures**:
   ```bash
   # Check logs
   docker-compose -f pc2_code/docker/docker-compose.yml logs <service-name>
   ```

3. **Network connectivity**:
   ```bash
   # Test cross-machine communication
   docker exec pc2-remote-connector ping 192.168.100.16
   ```

### Debug Commands

```bash
# Enter container shell
docker exec -it pc2-memory-orchestrator /bin/bash

# Check container resources
docker stats pc2-*

# Inspect network
docker network inspect pc2_network
```

## Development

### Building Images

```bash
# Build base image
docker build -t pc2_code/docker:latest -f pc2_code/docker/Dockerfile .

# Build specific service
docker-compose -f pc2_code/docker/docker-compose.yml build memory-orchestrator
```

### Adding New Agents

1. Add service definition to `docker-compose.yml`
2. Create Dockerfile if specialized dependencies needed
3. Update port mapping in `PORT_MAPPING.md`
4. Add to appropriate startup group in `start_pc2_docker.sh`

## Security

- All containers run as non-root user `ai`
- Read-only volume mounts where appropriate
- Network isolation between internal and external traffic
- Environment variables for sensitive configuration

## Maintenance

### Backup
```bash
# Backup volumes
docker run --rm -v pc2_data:/data -v $(pwd):/backup alpine tar czf /backup/pc2_data_backup.tar.gz -C /data .
```

### Updates
```bash
# Pull latest images
docker-compose -f pc2_code/docker/docker-compose.yml pull

# Recreate containers
docker-compose -f pc2_code/docker/docker-compose.yml up -d --force-recreate
```

## Files in this Directory

- `docker-compose.yml`: Main orchestration file
- `Dockerfile`: Base image for PC2 agents
- `Dockerfile.*`: Specialized images for specific agents
- `.env.example`: Example environment configuration
- `start_pc2_docker.sh`: Startup script
- `stop_pc2_docker.sh`: Shutdown script
- `PORT_MAPPING.md`: Complete port documentation
- `README.md`: This file