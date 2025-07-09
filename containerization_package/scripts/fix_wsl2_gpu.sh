#!/usr/bin/env bash
#
# Script to fix NVIDIA device paths in WSL2 for container GPU access
# This script ensures that all NVIDIA devices are properly accessible
# in WSL2 before starting containers with GPU access.

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Checking for NVIDIA devices in WSL2...${NC}"

# Check if nvidia-smi exists and is accessible
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${RED}Error: nvidia-smi not found!${NC}"
    echo -e "${YELLOW}Make sure NVIDIA drivers are installed on the Windows host${NC}"
    exit 1
fi

# Run nvidia-smi to check if GPU is accessible
echo -e "${GREEN}Testing NVIDIA GPU access with nvidia-smi:${NC}"
if ! nvidia-smi; then
    echo -e "${RED}Error: Unable to access NVIDIA GPU!${NC}"
    echo -e "${YELLOW}Check that NVIDIA drivers are working on the Windows host${NC}"
    exit 1
fi

# Verify CUDA is working
echo -e "${GREEN}Checking CUDA availability...${NC}"
if [ -z "$CUDA_VERSION" ]; then
    echo -e "${YELLOW}Warning: CUDA_VERSION not set. Setting to default 12.1${NC}"
    export CUDA_VERSION=12.1
fi

# Make sure the required NVIDIA device files exist
echo -e "${GREEN}Checking NVIDIA device files...${NC}"

# Check for /dev/nvidia0
if [ ! -c /dev/nvidia0 ]; then
    echo -e "${YELLOW}Warning: /dev/nvidia0 not found. Attempting to create it...${NC}"
    sudo mknod -m 666 /dev/nvidia0 c 195 0 || echo -e "${RED}Failed to create /dev/nvidia0${NC}"
fi

# Check for /dev/nvidiactl
if [ ! -c /dev/nvidiactl ]; then
    echo -e "${YELLOW}Warning: /dev/nvidiactl not found. Attempting to create it...${NC}"
    sudo mknod -m 666 /dev/nvidiactl c 195 255 || echo -e "${RED}Failed to create /dev/nvidiactl${NC}"
fi

# Check for /dev/nvidia-uvm
if [ ! -c /dev/nvidia-uvm ]; then
    echo -e "${YELLOW}Warning: /dev/nvidia-uvm not found. Attempting to create it...${NC}"
    sudo mknod -m 666 /dev/nvidia-uvm c 245 0 || echo -e "${RED}Failed to create /dev/nvidia-uvm${NC}"
fi

# Check for cuda libraries
echo -e "${GREEN}Checking CUDA libraries...${NC}"
if [ ! -d /usr/local/cuda-${CUDA_VERSION}/lib64 ]; then
    echo -e "${YELLOW}Warning: CUDA libraries not found at expected location${NC}"
    echo -e "${YELLOW}If you're using a container with CUDA, make sure it has the correct version${NC}"
fi

echo -e "${GREEN}GPU device path check completed.${NC}"
echo -e "${GREEN}Your WSL2 environment should now be ready for GPU containers.${NC}"

# Final test for container GPU access
echo -e "${GREEN}You can test container GPU access with:${NC}"
echo -e "${YELLOW}podman run --rm --device nvidia.com/gpu=all nvidia/cuda:12.1-base-ubuntu22.04 nvidia-smi${NC}"

exit 0
