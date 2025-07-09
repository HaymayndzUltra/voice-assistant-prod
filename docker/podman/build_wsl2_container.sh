#!/bin/bash
# Script to build and test WSL2-specific container for AI System

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BLUE}${BOLD}=================================================${NC}"
echo -e "${BLUE}${BOLD}  AI System - WSL2 Container Build Script  ${NC}"
echo -e "${BLUE}${BOLD}=================================================${NC}"

# Directory paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCKER_DIR="$PROJECT_ROOT/docker/podman"

# Display project information
echo -e "${GREEN}Project root:${NC} $PROJECT_ROOT"
echo -e "${GREEN}Docker directory:${NC} $DOCKER_DIR"

# Check if podman is installed
if ! command -v podman &> /dev/null; then
    echo -e "${RED}Error: Podman is not installed. Please install Podman first.${NC}"
    exit 1
fi

# Check if NVIDIA GPU is available
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${RED}Error: nvidia-smi not found. NVIDIA drivers may not be installed.${NC}"
    exit 1
fi

echo -e "${GREEN}Host GPU Information:${NC}"
nvidia-smi

# Create podman network if it doesn't exist
if ! podman network inspect ai_system_network &> /dev/null; then
    echo -e "${GREEN}Creating podman network: ai_system_network${NC}"
    podman network create --subnet 192.168.100.0/24 ai_system_network
else
    echo -e "${GREEN}Network ai_system_network already exists${NC}"
fi

# Copy requirements.txt to project root for Docker build context
echo -e "${GREEN}Copying requirements.txt to project root...${NC}"
cp "$DOCKER_DIR/requirements.txt" "$PROJECT_ROOT/requirements.txt"

# Build WSL2-specific base image
echo -e "\n${GREEN}Building WSL2-specific base image...${NC}"
echo -e "${YELLOW}This may take some time. Please be patient...${NC}"

podman build --format docker -t ai-system/base:latest -f "$DOCKER_DIR/Dockerfile.wsl2" "$PROJECT_ROOT"

# Function to build image for a specific group
build_group_image() {
    local group_name="$1"
    local display_name="$2"
    
    echo -e "\n${GREEN}Building image for $display_name...${NC}"
    podman tag ai-system/base:latest "ai-system/$group_name:latest"
    echo -e "${GREEN}Tagged ai-system/base:latest as ai-system/$group_name:latest${NC}"
}

echo -e "\n${BLUE}${BOLD}Building container images for each agent group...${NC}"

# Build images for each agent group
build_group_image "core-services" "Core Services"
build_group_image "memory-system" "Memory System"
build_group_image "utility-services" "Utility Services"
build_group_image "ai-models-gpu-services" "GPU Services (with WSL2 support)"
build_group_image "language-processing" "Language Processing (with WSL2 support)"

# Create a test container with PyTorch CUDA test script
echo -e "\n${GREEN}Creating test container with PyTorch CUDA test script...${NC}"

# Copy test script to a temporary location
cp "$DOCKER_DIR/scripts/test_pytorch_cuda.py" "/tmp/test_pytorch_cuda.py"

# Run a test container with the PyTorch CUDA test script
echo -e "\n${YELLOW}Running test container to verify PyTorch CUDA functionality...${NC}"
echo -e "${YELLOW}This will create a temporary container and run the PyTorch CUDA test.${NC}"

podman run --rm \
    --name ai-system-test \
    --privileged \
    -e PYTHONPATH=/app \
    -e NVIDIA_VISIBLE_DEVICES=all \
    -e CUDA_VISIBLE_DEVICES=0 \
    -v /usr/bin/nvidia-smi:/usr/bin/nvidia-smi \
    -v /usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1:/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1 \
    -v /usr/lib/x86_64-linux-gnu/libnvidia-ml.so.575.57.08:/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.575.57.08 \
    -v /usr/lib/wsl/lib/libnvidia-ml.so.1:/usr/lib/wsl/lib/libnvidia-ml.so.1 \
    -v /usr/local/cuda-12.1:/usr/local/cuda-12.1 \
    -v /tmp/test_pytorch_cuda.py:/test_pytorch_cuda.py \
    ai-system/ai-models-gpu-services:latest python /test_pytorch_cuda.py

# Check if we should start containers
echo -e "\n${YELLOW}Do you want to start the containers now? (y/n)${NC}"
read -p "> " start_containers
if [[ $start_containers == "y" || $start_containers == "Y" ]]; then
    echo -e "\n${GREEN}Starting containers...${NC}"
    
    # Start core-services container
    echo -e "${GREEN}Starting core-services container...${NC}"
    "$DOCKER_DIR/scripts/launch_wsl2_container.sh" core-services
    
    # Start memory-system container
    echo -e "${GREEN}Starting memory-system container...${NC}"
    "$DOCKER_DIR/scripts/launch_wsl2_container.sh" memory-system
    
    # Start utility-services container
    echo -e "${GREEN}Starting utility-services container...${NC}"
    "$DOCKER_DIR/scripts/launch_wsl2_container.sh" utility-services
    
    # Start GPU containers if requested
    echo -e "\n${YELLOW}Do you want to start the GPU containers? (y/n)${NC}"
    read -p "> " start_gpu
    if [[ $start_gpu == "y" || $start_gpu == "Y" ]]; then
        echo -e "${GREEN}Starting ai-models-gpu-services container...${NC}"
        "$DOCKER_DIR/scripts/launch_wsl2_container.sh" ai-models-gpu-services
        
        echo -e "${GREEN}Starting language-processing container...${NC}"
        "$DOCKER_DIR/scripts/launch_wsl2_container.sh" language-processing
    fi
    
    echo -e "\n${GREEN}All containers started successfully!${NC}"
    echo -e "${GREEN}To check container status, run: ${YELLOW}podman ps${NC}"
    echo -e "${GREEN}To view container logs, run: ${YELLOW}podman logs -f <container_name>${NC}"
    echo -e "${GREEN}To stop all containers, run: ${YELLOW}podman stop \$(podman ps -q)${NC}"
else
    echo -e "\n${GREEN}Build completed. To start containers manually, use:${NC}"
    echo -e "${YELLOW}$DOCKER_DIR/scripts/launch_wsl2_container.sh <container_group>${NC}"
fi

# Cleanup
rm -f "$PROJECT_ROOT/requirements.txt"
rm -f "/tmp/test_pytorch_cuda.py"

echo -e "\n${BLUE}${BOLD}=================================================${NC}"
echo -e "${BLUE}${BOLD}  Build process completed successfully!  ${NC}"
echo -e "${BLUE}${BOLD}=================================================${NC}" 