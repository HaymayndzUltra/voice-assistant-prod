# AI System Docker Deployment Guide

This document provides instructions for deploying the AI System components in Docker containers, with clear separation between MainPC and PC2 components.

## Overview

The AI System has been containerized with a clear separation between MainPC and PC2 components:

1. **MainPC Components** - Voice pipeline, task routing, and TTS services running on the RTX 4090 machine
2. **PC2 Components** - Translation, authentication, and monitoring services running on the secondary machine
3. **Shared Network** - A bridge network for communication between MainPC and PC2 containers

## Directory Structure

```
AI_System_Monorepo/
├── docker/
│   ├── mainpc/
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml
│   │   ├── requirements.mainpc.txt
│   │   └── config/
│   │       └── env.mainpc
│   ├── pc2/
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml
│   │   ├── requirements.pc2.txt
│   │   └── config/
│   │       └── env.pc2
│   └── shared/
│       └── docker-compose.network.yml
├── certificates/
├── logs/
└── scripts/
    └── manage_docker.sh
```

## Deployment Steps

### 1. Using the Management Script

The easiest way to deploy is using the provided management script:

```bash
bash scripts/manage_docker.sh
```

This interactive script provides options to:
- Deploy MainPC components
- Deploy PC2 components
- Deploy both systems
- View logs
- Stop containers
- Manage the shared network

### 2. Manual Deployment

If you prefer to deploy manually:

#### a. Create the shared network first:

```bash
cd docker/shared
docker-compose -f docker-compose.network.yml up -d
```

#### b. Deploy MainPC components:

```bash
cd docker/mainpc
docker-compose up -d
```

#### c. Deploy PC2 components:

```bash
cd docker/pc2
docker-compose up -d
```

## Configuration

### Environment Variables

The environment variables are defined in separate files for MainPC and PC2:

- **MainPC**: `docker/mainpc/config/env.mainpc`
- **PC2**: `docker/pc2/config/env.pc2`

Key differences in configuration:

| Setting | MainPC | PC2 |
|---------|--------|-----|
| MACHINE_TYPE | MAINPC | PC2 |
| FORCE_LOCAL_SDT | 1 (true) | 0 (false) |
| Resource limits | Higher (8GB) | Lower (4GB) |
| Service ports | Voice pipeline ports | Translation & auth ports |

### Network Configuration

The shared network (`ai-shared-network`) enables communication between MainPC and PC2 containers. Each machine also has its own internal network:

- `mainpc-network`: For communication between MainPC components
- `pc2-network`: For communication between PC2 components
- `ai-shared-network`: For cross-machine communication

## Component Dependencies

### MainPC Dependencies

- System Digital Twin is the primary service registry
- Task Router depends on System Digital Twin
- Streaming TTS and TTS Agent depend on Interrupt Handler
- Responder depends on TTS services

### PC2 Dependencies

- Advanced Router is the primary entry point for PC2
- All PC2 services depend on Advanced Router
- PC2 services discover MainPC services via the shared network

## Troubleshooting

### Common Issues

1. **Shared Network Issues**
   - Ensure the shared network is created before deploying components
   - Check network connectivity with `docker network inspect ai-shared-network`

2. **Service Discovery Issues**
   - MainPC's System Digital Twin must be running for PC2 services to register
   - Check logs with `docker-compose logs system-digital-twin`

3. **Resource Constraints**
   - Adjust memory limits in the env files if containers are being killed

4. **ZMQ Communication Issues**
   - Ensure certificates are properly mounted
   - Check that SECURE_ZMQ=1 is set in both environments

## Security Considerations

1. **ZMQ Security**
   - All ZMQ communications use CurveZMQ encryption
   - Certificates are shared between containers via volume mounts

2. **Network Isolation**
   - Each machine has its own isolated network
   - Only necessary services are exposed to the shared network

3. **Container Privileges**
   - Containers run with minimal privileges
   - No privileged containers are used

## Performance Optimization

1. **Resource Allocation**
   - MainPC containers are allocated more resources for TTS and audio processing
   - PC2 containers are optimized for translation tasks

2. **Volume Mounts**
   - Models and data are mounted as volumes for better performance
   - Logs are externalized for monitoring

## Monitoring

1. **Health Checks**
   - Each service has built-in health checks
   - Use `docker-compose ps` to see container health status

2. **Logging**
   - Centralized logs are available in the `logs` directory
   - View logs with `docker-compose logs -f` 