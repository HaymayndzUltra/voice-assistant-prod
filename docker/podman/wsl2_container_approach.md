# AI System Containerization in WSL2 Environment

## Current Environment Analysis

Based on our testing, we've identified that the WSL2 environment has some specific characteristics for GPU access:

1. **CUDA is installed** on the host system (version 12.1)
2. **NVIDIA driver is accessible** through nvidia-smi (version 575.57.08)
3. **NVIDIA device files** (`/dev/nvidia*`) are **not directly available** in the WSL2 environment
4. **NVIDIA libraries** are available at non-standard locations:
   - `/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1`
   - `/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.575.57.08`
   - `/usr/lib/wsl/lib/libnvidia-ml.so.1`

## Containerization Strategy for WSL2

Given these constraints, we need to adapt our containerization strategy:

### 1. Base Container Approach

Instead of trying to access NVIDIA devices directly, we'll use a different approach:

- Use a standard Ubuntu base image
- Install Python and other dependencies
- Mount the host's CUDA libraries and binaries into the container
- Use the PyTorch CUDA packages that are designed to work with WSL2

### 2. Updated Dockerfile

```dockerfile
FROM ubuntu:22.04

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    NVIDIA_VISIBLE_DEVICES=all

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3-setuptools \
    python3-dev \
    build-essential \
    curl \
    git \
    libportaudio2 \
    libsndfile1 \
    portaudio19-dev \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Make python3 the default python
RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Create application directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -U pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Install PyTorch with CUDA support for WSL2
RUN pip install --no-cache-dir torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu121

# Copy application code
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/models /app/config

# Default command
ENTRYPOINT ["python", "/app/docker/podman/scripts/container_startup.py"]
```

### 3. Container Launch Script

We'll create a script to launch containers with the appropriate volume mounts:

```bash
#!/bin/bash
# Launch container with WSL2 CUDA access

podman run --rm -it \
    --privileged \
    -e NVIDIA_VISIBLE_DEVICES=all \
    -e CUDA_VISIBLE_DEVICES=0 \
    -v /usr/bin/nvidia-smi:/usr/bin/nvidia-smi \
    -v /usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1:/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1 \
    -v /usr/lib/x86_64-linux-gnu/libnvidia-ml.so.575.57.08:/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.575.57.08 \
    -v /usr/lib/wsl/lib/libnvidia-ml.so.1:/usr/lib/wsl/lib/libnvidia-ml.so.1 \
    -v /usr/local/cuda-12.1:/usr/local/cuda-12.1 \
    -v $(pwd):/app \
    ai-system/base:latest
```

### 4. Container Groups

We'll maintain the same container grouping strategy, but with modified launch parameters:

1. **core-services**: Basic services without GPU requirements
2. **memory-system**: Memory services without GPU requirements
3. **utility-services**: Utility services without GPU requirements
4. **ai-models-gpu-services**: GPU-accelerated services with special WSL2 mounts
5. **language-processing**: GPU-accelerated language services with special WSL2 mounts

### 5. Testing Strategy

For each container group, we'll:

1. Test basic functionality without GPU access
2. For GPU containers, test PyTorch CUDA functionality
3. Test inter-container communication
4. Test communication with PC2

## Implementation Plan

1. **Create WSL2-specific Dockerfiles** for each container group
2. **Create launch scripts** with appropriate volume mounts
3. **Test PyTorch CUDA access** in the containers
4. **Implement container health checks** that don't rely on direct GPU device access
5. **Test inter-container communication**
6. **Test PC2 communication**

## Limitations and Considerations

1. **Performance**: WSL2 GPU access may have some overhead compared to native Linux
2. **Compatibility**: Some CUDA features may not be fully available
3. **Updates**: WSL2 NVIDIA driver updates may require adjustments to the container setup
4. **Alternative Approach**: Consider using Docker Desktop for Windows with WSL2 integration as an alternative to Podman

## Next Steps

1. Implement the WSL2-specific Dockerfiles
2. Create the launch scripts
3. Test PyTorch CUDA functionality
4. Proceed with the containerization of the AI system components 