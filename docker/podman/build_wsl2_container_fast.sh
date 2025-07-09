#!/bin/bash
# Optimized script to build and test WSL2-specific container for AI System with sudo

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BLUE}${BOLD}=================================================${NC}"
echo -e "${BLUE}${BOLD}  AI System - WSL2 Fast Container Build Script  ${NC}"
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

# Configure registries for podman
echo -e "${GREEN}Configuring podman registries...${NC}"
sudo mkdir -p /etc/containers
echo 'unqualified-search-registries = ["docker.io"]' | sudo tee /etc/containers/registries.conf

# Create podman network if it doesn't exist
if ! sudo podman network inspect ai_system_network &> /dev/null; then
    echo -e "${GREEN}Creating podman network: ai_system_network${NC}"
    sudo podman network create --subnet 192.168.100.0/24 ai_system_network
else
    echo -e "${GREEN}Network ai_system_network already exists${NC}"
fi

# Copy requirements.txt to project root for Docker build context
echo -e "${GREEN}Copying requirements.txt to project root...${NC}"
cp "$DOCKER_DIR/requirements.txt" "$PROJECT_ROOT/requirements.txt"

# Build WSL2-specific base image with layer caching enabled
echo -e "\n${GREEN}Building WSL2-specific base image...${NC}"
echo -e "${YELLOW}This may take some time. Please be patient...${NC}"

# Use sudo for building to overcome permission issues with GPU access
# Use fully qualified image name
sudo podman build --format docker -t docker.io/ai-system/base:latest -f "$DOCKER_DIR/Dockerfile.wsl2" "$PROJECT_ROOT"

# Function to build image for a specific group (just tagging, very fast)
build_group_image() {
    local group_name="$1"
    local display_name="$2"
    
    echo -e "\n${GREEN}Building image for $display_name...${NC}"
    sudo podman tag docker.io/ai-system/base:latest "docker.io/ai-system/$group_name:latest"
    echo -e "${GREEN}Tagged docker.io/ai-system/base:latest as docker.io/ai-system/$group_name:latest${NC}"
}

echo -e "\n${BLUE}${BOLD}Building container images for each agent group...${NC}"

# Build images for each agent group (just tagging)
build_group_image "core-services" "Core Services"
build_group_image "memory-system" "Memory System"
build_group_image "utility-services" "Utility Services"
build_group_image "ai-models-gpu-services" "GPU Services (with WSL2 support)"
build_group_image "language-processing" "Language Processing (with WSL2 support)"

# Ask if user wants to run a test container
echo -e "\n${YELLOW}Do you want to run a test container to verify GPU access? (y/n)${NC}"
read -p "> " run_test
if [[ $run_test == "y" || $run_test == "Y" ]]; then
    echo -e "\n${GREEN}Running test container with nvidia-smi...${NC}"
    sudo podman run --rm --device /dev/nvidia0 --device /dev/nvidiactl --device /dev/nvidia-uvm docker.io/ai-system/base:latest nvidia-smi
fi

# Ask if user wants to start containers
echo -e "\n${YELLOW}Do you want to start the containers now? (y/n)${NC}"
read -p "> " start_containers
if [[ $start_containers == "y" || $start_containers == "Y" ]]; then
    echo -e "\n${GREEN}Starting containers...${NC}"
    
    # Start core-services container with sudo
    echo -e "${GREEN}Starting core-services container...${NC}"
    sudo CONTAINER_IMAGE="docker.io/ai-system/core-services:latest" "$DOCKER_DIR/scripts/launch_wsl2_container.sh" core-services
    
    # Ask about GPU containers
    echo -e "\n${YELLOW}Do you want to start the GPU containers? (y/n)${NC}"
    read -p "> " start_gpu
    if [[ $start_gpu == "y" || $start_gpu == "Y" ]]; then
        echo -e "${GREEN}Starting ai-models-gpu-services container...${NC}"
        sudo CONTAINER_IMAGE="docker.io/ai-system/ai-models-gpu-services:latest" "$DOCKER_DIR/scripts/launch_wsl2_container.sh" ai-models-gpu-services
    fi
    
    echo -e "\n${GREEN}Containers started successfully!${NC}"
    echo -e "${GREEN}To check container status, run: ${YELLOW}sudo podman ps${NC}"
else
    echo -e "\n${GREEN}Build completed. To start containers manually, use:${NC}"
    echo -e "${YELLOW}sudo CONTAINER_IMAGE=\"docker.io/ai-system/<container_group>:latest\" $DOCKER_DIR/scripts/launch_wsl2_container.sh <container_group>${NC}"
fi

# Cleanup
rm -f "$PROJECT_ROOT/requirements.txt"

echo -e "\n${BLUE}${BOLD}=================================================${NC}"
echo -e "${BLUE}${BOLD}  Fast build process completed successfully!  ${NC}"
echo -e "${BLUE}${BOLD}=================================================${NC}" 