# AI System Containerization

This document provides instructions for running the AI System in Docker containers using the provided configuration files.

## Prerequisites

- Docker Engine 20.10.0 or higher
- Docker Compose 2.0.0 or higher
- NVIDIA Container Toolkit (for GPU support)
- At least 16GB of RAM
- At least 50GB of free disk space
- NVIDIA GPU with at least 8GB VRAM (for full functionality)

## Directory Structure

The containerization setup consists of the following files:

- `.dockerignore`: Excludes unnecessary files from the Docker build context
- `Dockerfile`: Multi-stage build for a lean Python 3.11 image
- `docker-compose.yml`: Service definitions based on agent groups
- `launch_containers.sh`: Helper script to build, launch, and verify the containers

## Container Organization

The services are organized according to the logical agent groups defined in `startup_config.yaml`:

1. **Core Services**: SystemDigitalTwin, RequestCoordinator, UnifiedSystemAgent
2. **GPU Infrastructure**: GGUFModelManager, ModelManagerAgent, VRAMOptimizerAgent, PredictiveLoader
3. **Reasoning Services**: ChainOfThoughtAgent, GoTToTAgent, CognitiveModelAgent
4. **Utility Services**: CodeGenerator, SelfTrainingOrchestrator, etc.
5. **Speech Services**: STTService, TTSService
6. **Audio Interface**: AudioCapture, FusedAudioPreprocessor, etc.
7. **Memory System**: MemoryClient, SessionMemoryAgent

## Getting Started

### 1. Verify NVIDIA Container Toolkit Installation

```bash
nvidia-smi
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

Both commands should display information about your GPU.

### 2. Prepare Data Directories

Ensure the following directories exist and have appropriate permissions:

```bash
mkdir -p logs data models config
chmod -R 777 logs data models config
```

### 3. Launch the Containers

Use the provided script to build and launch the containers:

```bash
./launch_containers.sh
```

Or manually with Docker Compose:

```bash
docker-compose up --build -d
```

### 4. Verify the System

Check the status of all containers:

```bash
docker-compose ps
```

View logs for a specific service:

```bash
docker-compose logs -f systemdigitaltwin
```

### 5. Stopping the System

To stop all containers:

```bash
docker-compose down
```

## Volume Mounts

The following directories are mounted as volumes:

- `./logs:/app/logs`: Log files
- `./data:/app/data`: Data files
- `./models:/app/models`: AI models
- `./config:/app/config`: Configuration files

## Networking

All services are connected to the `ai_system_network` bridge network with subnet `172.20.0.0/16`.

## Health Checks

Each service has a health check configured to verify its status. You can monitor health status with:

```bash
docker-compose ps
```

## Troubleshooting

### GPU Access Issues

If containers cannot access the GPU, verify the NVIDIA Container Toolkit installation:

```bash
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### Container Startup Failures

Check the logs for the failing container:

```bash
docker-compose logs <container_name>
```

### Memory/Disk Space Issues

The system requires significant resources. Verify available resources with:

```bash
df -h
free -h
```

## Next Steps

- Perform deep validation and stress testing
- Implement container orchestration for horizontal scaling
- Create deployment scripts for various environments