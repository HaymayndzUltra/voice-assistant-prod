# CASCADE Docker Deployment

This directory contains the Docker deployment configurations for both MainPC (RTX 4090) and PC2 (RTX 3060) systems.

## Directory Structure

```
docker-deployment/
├── mainpc/                 # MainPC deployment files
│   ├── docker-compose.yml  # Main compose file for MainPC
│   ├── dockerfiles/        # Dockerfiles for different service groups
│   └── config/            # Configuration files (Prometheus, etc.)
├── pc2/                   # PC2 deployment files
│   ├── docker-compose.yml  # Main compose file for PC2
│   ├── dockerfiles/        # Dockerfiles for PC2 services
│   └── config/            # PC2-specific configurations
├── shared/                # Shared resources
│   ├── health_check.py    # Common health check implementation
│   └── requirements/      # Python requirements files
├── deploy.sh              # Deployment management script
└── README.md              # This file
```

## Quick Start

### Prerequisites

1. Docker Engine (20.10+)
2. Docker Compose (v2.0+)
3. NVIDIA Docker Runtime (for GPU support)
4. At least 64GB RAM for MainPC, 32GB for PC2
5. RTX 4090 for MainPC, RTX 3060 for PC2

### Deployment Commands

```bash
# Deploy entire MainPC system
./deploy.sh deploy-mainpc

# Deploy entire PC2 system
./deploy.sh deploy-pc2

# Deploy both systems
./deploy.sh deploy-all

# Check system status
./deploy.sh status

# Check health of all services
./deploy.sh health

# View logs for a specific service
./deploy.sh logs service-registry
```

## Service Groups

### MainPC Groups

1. **core_platform** - Foundation services (ServiceRegistry, SystemDigitalTwin, ObservabilityHub)
2. **ai_engine** - GPU-intensive AI services (ModelManagerSuite, VRAMOptimizer, etc.)
3. **request_processing** - Request handling pipeline
4. **memory_learning** - Memory and learning services
5. **audio_realtime** - Real-time audio processing
6. **personality** - Emotion and personality modeling
7. **auxiliary** - Optional specialized services

### PC2 Groups

1. **core_services** - Foundation services for PC2
2. **application_services** - All PC2-specific functionality

## Configuration

### Environment Variables

Create a `.env` file in the docker-deployment directory:

```env
# CASCADE version
CASCADE_VERSION=latest

# Port offset for multiple deployments
PORT_OFFSET=0

# Logging level
LOG_LEVEL=INFO

# MainPC host configuration
MAINPC_HOST=mainpc
MAINPC_OBS_HUB=http://mainpc:9000

# Grafana admin password
GRAFANA_PASSWORD=your_secure_password
```

### Resource Allocation

MainPC resource allocation:
- Total CPU: 32 cores
- Total Memory: 80GB
- GPU: RTX 4090 (80% VRAM for models)

PC2 resource allocation:
- Total CPU: 16 cores
- Total Memory: 32GB
- GPU: RTX 3060 (via MainPC for inference)

## Networking

- MainPC Internal Network: `172.20.0.0/16`
- PC2 Internal Network: `172.21.0.0/16`
- Cross-system communication via external network

## Health Checks

All services implement standardized health checks:

```json
{
  "status": "healthy|degraded|unhealthy",
  "service": {
    "name": "ServiceName",
    "version": "1.0.0",
    "uptime_seconds": 3600
  },
  "checks": {
    "self": {"status": "healthy"},
    "dependencies": {...},
    "resources": {...}
  }
}
```

## Monitoring

Access monitoring dashboards:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/cascade_admin)
- MainPC ObservabilityHub: http://localhost:9001
- PC2 ObservabilityHub: http://localhost:9110

## Troubleshooting

### Common Issues

1. **Service fails to start**
   - Check logs: `./deploy.sh logs <service-name>`
   - Verify dependencies are healthy: `./deploy.sh health`

2. **GPU not available**
   - Ensure NVIDIA Docker runtime is installed
   - Check GPU availability: `docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi`

3. **Port conflicts**
   - Use PORT_OFFSET environment variable
   - Example: `PORT_OFFSET=1000 ./deploy.sh deploy-mainpc`

4. **Out of memory**
   - Check resource limits in docker-compose.yml
   - Monitor with: `docker stats`

### Rollback Procedure

1. Stop affected services: `./deploy.sh stop-all`
2. Restore previous version: `CASCADE_VERSION=v1.0.0 ./deploy.sh deploy-all`
3. Verify health: `./deploy.sh health`

## Development

### Building Images Locally

```bash
# Build all MainPC images
docker-compose -f mainpc/docker-compose.yml build

# Build specific service
docker-compose -f mainpc/docker-compose.yml build service-registry
```

### Running in Development Mode

```bash
# Set development mode
export DEPLOYMENT_MODE=development
export LOG_LEVEL=DEBUG

# Deploy with development settings
./deploy.sh deploy-all
```

## Production Deployment

### Pre-deployment Checklist

- [ ] Update CASCADE_VERSION in .env
- [ ] Configure resource limits based on hardware
- [ ] Set secure passwords for Grafana
- [ ] Configure persistent volumes for data
- [ ] Setup backup strategy
- [ ] Configure monitoring alerts
- [ ] Test rollback procedure
- [ ] Document custom configurations

### Deployment Steps

1. Clone repository to production servers
2. Configure environment variables
3. Run deployment script: `./deploy.sh deploy-all`
4. Verify health: `./deploy.sh health`
5. Configure monitoring dashboards
6. Test system functionality
7. Enable automated backups

## Maintenance

### Backup Procedures

```bash
# Backup volumes
docker run --rm -v cascade_unified_memory:/data -v $(pwd):/backup \
  alpine tar czf /backup/unified_memory_backup.tar.gz -C /data .
```

### Update Procedures

1. Test update in staging environment
2. Create backup of current state
3. Update CASCADE_VERSION in .env
4. Deploy updates: `./deploy.sh deploy-all`
5. Monitor health and logs
6. Rollback if issues detected

## Support

For issues or questions:
1. Check service logs
2. Review health status
3. Consult dependency diagrams
4. Check monitoring dashboards