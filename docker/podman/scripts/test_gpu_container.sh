#!/bin/bash
# Script to test GPU access in a container

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}===== Testing GPU Access in Container =====${NC}"

# Check if podman is installed
if ! command -v podman &> /dev/null; then
    echo -e "${RED}Error: podman not found. Please install podman first.${NC}"
    exit 1
fi

# Check if NVIDIA GPU is available
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${RED}Error: nvidia-smi not found. NVIDIA drivers may not be installed.${NC}"
    exit 1
fi

echo -e "${GREEN}Host GPU Information:${NC}"
nvidia-smi

echo -e "\n${GREEN}Testing GPU access in container...${NC}"
echo -e "${YELLOW}This will pull a small NVIDIA CUDA container and test GPU access.${NC}"

# Run a simple CUDA container to test GPU access
echo -e "${YELLOW}Trying alternative method for GPU access...${NC}"
podman run --rm \
    --device /dev/nvidia0:/dev/nvidia0 \
    --device /dev/nvidia-uvm:/dev/nvidia-uvm \
    --device /dev/nvidia-uvm-tools:/dev/nvidia-uvm-tools \
    --device /dev/nvidiactl:/dev/nvidiactl \
    --security-opt=label=disable \
    -e NVIDIA_VISIBLE_DEVICES=all \
    -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    docker.io/nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi

echo -e "\n${GREEN}===== GPU Test Complete =====${NC}" 