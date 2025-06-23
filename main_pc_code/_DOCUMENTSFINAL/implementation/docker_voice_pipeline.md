# Docker Voice Pipeline Deployment Guide

This document provides instructions for deploying the voice pipeline components in Docker containers.

## Overview

The voice pipeline components have been containerized to ensure consistent deployment across different environments. The following components are included:

1. **System Digital Twin** - Service registry and discovery
2. **Task Router** - Routes tasks to appropriate models and services
3. **Streaming Interrupt Handler** - Handles interruptions for real-time control
4. **Streaming TTS Agent** - Provides streaming text-to-speech capabilities
5. **TTS Agent** - Provides standard text-to-speech capabilities
6. **Responder Agent** - Handles responses and communicates with TTS services

## Prerequisites

- Docker Engine (version 20.10.0 or later)
- Docker Compose (version 2.0.0 or later)
- 4GB+ of RAM available for Docker
- 10GB+ of disk space

## Directory Structure

```
AI_System_Monorepo/
├── docker/
│   ├── Dockerfile.voice_pipeline
│   ├── docker-compose.voice_pipeline.yml
│   └── config/
│       └── env.template
├── certificates/
│   ├── client.key_secret
│   └── server.key_secret
├── logs/
├── scripts/
│   ├── deploy_voice_pipeline_docker.sh
│   └── docker_health_check.py
└── main_pc_code/
    ├── utils/
    │   ├── env_loader.py
    │   └── docker_network_utils.py
    └── ...
```

## Deployment Steps

### 1. Generate ZMQ Certificates

If you haven't already generated ZMQ certificates, run:

```bash
python scripts/generate_zmq_certificates.py
```

### 2. Deploy with Script

The easiest way to deploy is using the provided script:

```bash
bash scripts/deploy_voice_pipeline_docker.sh
```

This script will:
- Check for Docker and Docker Compose
- Create necessary directories
- Generate requirements.txt if needed
- Generate ZMQ certificates if needed
- Build Docker images
- Start the services
- Check service status

### 3. Manual Deployment

If you prefer to deploy manually:

```bash
# Build the images
cd docker
docker-compose -f docker-compose.voice_pipeline.yml build

# Start the services
docker-compose -f docker-compose.voice_pipeline.yml up -d

# Check status
docker-compose -f docker-compose.voice_pipeline.yml ps
```

## Configuration

### Environment Variables

The environment variables are defined in `docker/config/env.template`. You can modify this file to change the configuration.

Key environment variables:

- `MACHINE_TYPE`: Set to `MAINPC` or `PC2`
- `BIND_ADDRESS`: Set to `0.0.0.0` for Docker
- `SECURE_ZMQ`: Set to `1` to enable secure ZMQ
- `SERVICE_DISCOVERY_ENABLED`: Set to `1` to enable service discovery

### Network Configuration

In Docker, services communicate using their service names as hostnames. The `docker_network_utils.py` module handles the translation between service names and Docker hostnames.

## Health Checks

Each service has a health check endpoint that can be used to verify its status. You can use the `docker_health_check.py` script to check the health of a service:

```bash
python scripts/docker_health_check.py --service system-digital-twin
```

## Troubleshooting

### Viewing Logs

To view logs for a specific service:

```bash
docker-compose -f docker/docker-compose.voice_pipeline.yml logs -f system-digital-twin
```

To view logs for all services:

```bash
docker-compose -f docker/docker-compose.voice_pipeline.yml logs -f
```

### Common Issues

1. **Service fails to start**: Check the logs for error messages.
2. **Services can't communicate**: Make sure the Docker network is properly configured.
3. **ZMQ connection errors**: Verify that the ZMQ certificates are properly mounted.

## Stopping the Services

To stop all services:

```bash
docker-compose -f docker/docker-compose.voice_pipeline.yml down
```

To stop a specific service:

```bash
docker-compose -f docker/docker-compose.voice_pipeline.yml stop system-digital-twin
```

## Performance Considerations

- The voice pipeline is designed to run on a machine with at least 4GB of RAM.
- For production use, consider increasing the resource limits in the Docker Compose file.
- The TTS services require significant CPU resources. Consider using a machine with at least 4 CPU cores. 