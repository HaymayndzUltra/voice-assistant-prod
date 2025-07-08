# AI System Containerization with Podman

This directory contains the necessary files to containerize the AI System using Podman, with special focus on preserving GPU functionality for RTX 4090 and ensuring proper communication between MainPC and PC2.

## Directory Structure

- `Dockerfile.base` - Base Dockerfile with CUDA support for RTX 4090
- `requirements.txt` - Python dependencies
- `podman_build.sh` - Script to build and run containers
- `config/` - Configuration files for containers
- `scripts/` - Utility scripts for containers

## Requirements

- Podman (version 3.0+)
- NVIDIA GPU with drivers installed (RTX 4090 recommended)
- NVIDIA Container Toolkit
- podman-compose (optional, but recommended)

## Installation

### Install Podman

```bash
sudo apt-get update
sudo apt-get install -y podman
```

### Install NVIDIA Container Toolkit

```bash
sudo apt-get install -y nvidia-container-toolkit
```

### Install podman-compose (Optional)

```bash
pip install podman-compose
```

## Container Groups

The AI system is organized into the following container groups:

1. **core-services** - Core system services (SystemDigitalTwin, RequestCoordinator, UnifiedSystemAgent)
2. **memory-system** - Memory-related services (MemoryClient, SessionMemoryAgent, KnowledgeBase)
3. **utility-services** - Utility services (CodeGenerator, LLMService, SelfTrainingOrchestrator, PC2Services)
4. **ai-models-gpu-services** - GPU-accelerated model services (GGUFModelManager, ModelManagerAgent, VRAMOptimizerAgent)
5. **learning-knowledge** - Learning and knowledge services
6. **language-processing** - Language processing services (with GPU support)
7. **audio-processing** - Audio processing services
8. **emotion-system** - Emotion-related services
9. **utilities-support** - Support utilities
10. **security-auth** - Security and authentication services

## Usage

### Building and Running Containers

Run the build script:

```bash
./podman_build.sh
```

The script will:
1. Check for required dependencies
2. Build a base image with CUDA support
3. Create images for each agent group
4. Optionally test GPU support
5. Optionally start all containers

### Manual Container Management

#### Start Containers

```bash
# Using podman-compose
cd docker/podman
podman-compose -f docker-compose.yml up -d

# OR using native podman commands
podman run -d --name core-services [options] ai-system/core-services:latest
```

#### Check Container Status

```bash
podman ps
```

#### View Container Logs

```bash
podman logs <container_name>
```

#### Stop Containers

```bash
podman stop $(podman ps -q)
```

## GPU Support

The containerization is configured to properly access the NVIDIA RTX 4090 GPU. The GPU is shared between containers that need it, primarily:

- **ai-models-gpu-services** - For model loading and inference
- **language-processing** - For LLM operations

A GPU test script is included to verify proper GPU access from within containers.

## MainPC and PC2 Communication

Communication between MainPC and PC2 is preserved through:

1. **PC2Services** agent in the utility-services container
2. **MemoryClient** in the memory-system container that connects to PC2's memory services
3. **NetworkConfig** that maintains proper IP addressing and port mapping

The containers are configured to use the correct IP addresses and ports for cross-machine communication.

## Troubleshooting

### GPU Not Detected in Container

1. Check that NVIDIA Container Toolkit is installed
2. Verify that the container has the correct device mounts:
   ```
   --device /dev/nvidia0:/dev/nvidia0
   --device /dev/nvidia-uvm:/dev/nvidia-uvm
   --device /dev/nvidia-uvm-tools:/dev/nvidia-uvm-tools
   --device /dev/nvidiactl:/dev/nvidiactl
   ```
3. Ensure the container has the runtime flag: `--runtime=nvidia`

### Container Network Issues

1. Check that the ai_system_network exists: `podman network ls`
2. Verify IP assignments match the configuration in network_config.yaml

### Memory Issues

If containers crash due to memory limits, adjust the resource limits in the docker-compose.yml file or podman run commands.

## Additional Resources

- [Podman Documentation](https://docs.podman.io/)
- [NVIDIA Container Toolkit Documentation](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/overview.html) 