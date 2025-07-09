#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==== AI System Containerization - Final Run ====${NC}"

# Directory paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Stop existing containers
echo -e "${GREEN}Stopping existing containers...${NC}"
sudo podman stop core-services memory-system utility-services ai-models-gpu-services language-processing 2>/dev/null
sudo podman rm -f core-services memory-system utility-services ai-models-gpu-services language-processing 2>/dev/null

# Start containers one by one with host networking
echo -e "${GREEN}Starting core-services...${NC}"
sudo podman run -d --name core-services \
    --net=host \
    -e CONTAINER_GROUP="core-services" \
    -v "$PROJECT_ROOT/logs:/app/logs" \
    -v "$PROJECT_ROOT/data:/app/data" \
    -v "$PROJECT_ROOT/models:/app/models" \
    docker.io/ai-system/core-services:latest

echo -e "${GREEN}Starting memory-system...${NC}"
sudo podman run -d --name memory-system \
    --net=host \
    -e CONTAINER_GROUP="memory-system" \
    -v "$PROJECT_ROOT/logs:/app/logs" \
    -v "$PROJECT_ROOT/data:/app/data" \
    -v "$PROJECT_ROOT/models:/app/models" \
    docker.io/ai-system/memory-system:latest

echo -e "${GREEN}Starting utility-services...${NC}"
sudo podman run -d --name utility-services \
    --net=host \
    -e CONTAINER_GROUP="utility-services" \
    -v "$PROJECT_ROOT/logs:/app/logs" \
    -v "$PROJECT_ROOT/data:/app/data" \
    -v "$PROJECT_ROOT/models:/app/models" \
    docker.io/ai-system/utility-services:latest

# GPU containers with device access
if [ -e /dev/nvidia0 ]; then
    echo -e "${GREEN}Starting ai-models-gpu-services with GPU support...${NC}"
    sudo podman run -d --name ai-models-gpu-services \
        --net=host \
        -e CONTAINER_GROUP="ai-models-gpu-services" \
        -v "$PROJECT_ROOT/logs:/app/logs" \
        -v "$PROJECT_ROOT/data:/app/data" \
        -v "$PROJECT_ROOT/models:/app/models" \
        --device /dev/nvidia0:/dev/nvidia0 \
        --device /dev/nvidiactl:/dev/nvidiactl \
        --device /dev/nvidia-uvm:/dev/nvidia-uvm \
        docker.io/ai-system/ai-models-gpu-services:latest
    
    echo -e "${GREEN}Starting language-processing with GPU support...${NC}"
    sudo podman run -d --name language-processing \
        --net=host \
        -e CONTAINER_GROUP="language-processing" \
        -v "$PROJECT_ROOT/logs:/app/logs" \
        -v "$PROJECT_ROOT/data:/app/data" \
        -v "$PROJECT_ROOT/models:/app/models" \
        --device /dev/nvidia0:/dev/nvidia0 \
        --device /dev/nvidiactl:/dev/nvidiactl \
        --device /dev/nvidia-uvm:/dev/nvidia-uvm \
        docker.io/ai-system/language-processing:latest
else
    echo -e "${YELLOW}No GPU detected, starting containers without GPU support...${NC}"
    
    sudo podman run -d --name ai-models-gpu-services \
        --net=host \
        -e CONTAINER_GROUP="ai-models-gpu-services" \
        -v "$PROJECT_ROOT/logs:/app/logs" \
        -v "$PROJECT_ROOT/data:/app/data" \
        -v "$PROJECT_ROOT/models:/app/models" \
        docker.io/ai-system/ai-models-gpu-services:latest
        
    sudo podman run -d --name language-processing \
        --net=host \
        -e CONTAINER_GROUP="language-processing" \
        -v "$PROJECT_ROOT/logs:/app/logs" \
        -v "$PROJECT_ROOT/data:/app/data" \
        -v "$PROJECT_ROOT/models:/app/models" \
        docker.io/ai-system/language-processing:latest
fi

# Show running containers
echo -e "${GREEN}All containers started! Running containers:${NC}"
sudo podman ps

echo -e "${YELLOW}Showing a few seconds of logs from core-services:${NC}"
sudo timeout 5s sudo podman logs -f core-services || true

echo -e "${GREEN}All agent groups are now containerized and running!${NC}"
echo -e "${YELLOW}To view logs from a container, run:${NC}"
echo -e "sudo podman logs -f <container-name>"
