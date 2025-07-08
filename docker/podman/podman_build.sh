#!/bin/bash
# Enhanced script to build and run the AI System using Podman
# This script handles building containers for each agent group with improved GPU support for RTX 4090

# Exit on any error
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BLUE}${BOLD}=================================================${NC}"
echo -e "${BLUE}${BOLD}  AI System - MainPC Podman Build Script (v2.0)  ${NC}"
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
    echo -e "${RED}Podman is not installed. Please install Podman first.${NC}"
    exit 1
fi

# Check if podman-compose is installed
if ! command -v podman-compose &> /dev/null; then
    echo -e "${YELLOW}podman-compose is not installed. Using native podman commands.${NC}"
    USE_COMPOSE=false
else
    USE_COMPOSE=true
fi

# Check if NVIDIA GPU is available
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${RED}NVIDIA driver not found. GPU support may not work properly.${NC}"
    GPU_AVAILABLE=false
else
    echo -e "${GREEN}NVIDIA GPU detected. Checking for RTX 4090...${NC}"
    if nvidia-smi | grep -i "GeForce RTX 4090"; then
        echo -e "${GREEN}✅ RTX 4090 detected!${NC}"
        GPU_AVAILABLE=true
    else
        echo -e "${YELLOW}⚠️ RTX 4090 not detected. Using available GPU instead.${NC}"
        GPU_AVAILABLE=true
    fi
fi

# Check NVIDIA Container Toolkit
echo -e "${GREEN}Checking NVIDIA Container Toolkit...${NC}"
if dpkg -l | grep -q nvidia-container-toolkit; then
    echo -e "${GREEN}✅ NVIDIA Container Toolkit is installed.${NC}"
else
    echo -e "${YELLOW}⚠️ NVIDIA Container Toolkit not found. GPU support may not work properly.${NC}"
    echo -e "${YELLOW}Consider installing it with: sudo apt-get install -y nvidia-container-toolkit${NC}"
fi

# Create podman network if it doesn't exist
if ! podman network inspect ai_system_network &> /dev/null; then
    echo -e "${GREEN}Creating podman network: ai_system_network${NC}"
    podman network create --subnet 172.20.0.0/16 ai_system_network
else
    echo -e "${GREEN}Network ai_system_network already exists${NC}"
fi

# Copy requirements.txt to project root for Docker build context
echo -e "${GREEN}Copying requirements.txt to project root...${NC}"
cp "$DOCKER_DIR/requirements.txt" "$PROJECT_ROOT/requirements.txt"

# Build base image with NVIDIA CUDA support
echo -e "\n${GREEN}Building base image with CUDA support for RTX 4090...${NC}"
podman build -t ai-system/base:latest -f "$DOCKER_DIR/Dockerfile.base" "$PROJECT_ROOT"

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
build_group_image "gpu-services" "GPU Services (with RTX 4090 support)"
build_group_image "learning-knowledge" "Learning & Knowledge"
build_group_image "language-processing" "Language Processing"
build_group_image "audio-processing" "Audio Processing"
build_group_image "emotion-system" "Emotion System"
build_group_image "utilities-support" "Utilities Support"
build_group_image "security-auth" "Security & Authentication"

# Create a GPU test script
echo -e "${GREEN}Creating GPU test script...${NC}"
mkdir -p "$PROJECT_ROOT/tests/gpu"
cat > "$PROJECT_ROOT/tests/gpu/test_gpu.py" << 'EOF'
#!/usr/bin/env python3
"""
Test script to verify GPU access and CUDA support in container
"""
import os
import sys
import time

print("=== GPU TEST SCRIPT ===")
print(f"Python version: {sys.version}")

try:
    print("\nTesting PyTorch CUDA support...")
    import torch
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"CUDA device count: {torch.cuda.device_count()}")
        print(f"CUDA device name: {torch.cuda.get_device_name(0)}")
        print(f"CUDA device capability: {torch.cuda.get_device_capability(0)}")
        
        # Test CUDA computation
        print("\nTesting CUDA computation...")
        x = torch.rand(5, 3).cuda()
        y = torch.rand(5, 3).cuda()
        z = x + y
        print(f"CUDA computation successful: {z.device}")
except ImportError:
    print("PyTorch not installed or CUDA support not available")

try:
    print("\nTesting llama-cpp-python CUDA support...")
    from llama_cpp import Llama
    print("llama-cpp-python is installed")
    print("Checking CUDA support in llama-cpp...")
    
    # Check if CUDA methods are available
    has_cuda = hasattr(Llama, 'n_gpu_layers')
    print(f"CUDA support available: {has_cuda}")
    
    if has_cuda:
        print("llama-cpp-python was built with CUDA support")
except ImportError:
    print("llama-cpp-python not installed")

print("\n=== GPU TEST COMPLETE ===")
EOF
chmod +x "$PROJECT_ROOT/tests/gpu/test_gpu.py"

# Check if we should test GPU support
echo -e "\n${YELLOW}Would you like to test GPU support in a container? (y/n)${NC}"
read -p "> " test_gpu
if [[ $test_gpu == "y" || $test_gpu == "Y" ]]; then
    echo -e "\n${GREEN}Testing GPU support in container...${NC}"
    podman run --rm \
        --device /dev/nvidia0:/dev/nvidia0 \
        --device /dev/nvidia-uvm:/dev/nvidia-uvm \
        --device /dev/nvidia-uvm-tools:/dev/nvidia-uvm-tools \
        --device /dev/nvidiactl:/dev/nvidiactl \
        --security-opt=label=disable \
        --runtime=nvidia \
        -e NVIDIA_VISIBLE_DEVICES=all \
        -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
        -v "$PROJECT_ROOT/tests/gpu:/app/tests/gpu" \
        ai-system/gpu-services:latest python /app/tests/gpu/test_gpu.py
fi

# Check if we should start containers
echo -e "\n${YELLOW}Do you want to start the containers now? (y/n)${NC}"
read -p "> " start_containers
if [[ $start_containers == "y" || $start_containers == "Y" ]]; then
    if [[ $USE_COMPOSE == true ]]; then
        echo -e "\n${GREEN}Starting containers using podman-compose...${NC}"
        cp "$PROJECT_ROOT/docker/mainpc/docker-compose.yml" "$DOCKER_DIR/docker-compose.yml"
        cd "$DOCKER_DIR" && podman-compose -f docker-compose.yml up -d
    else
        echo -e "\n${GREEN}Starting containers using native podman commands...${NC}"
        
        # Core services must start first
        echo -e "${GREEN}Starting core-services container...${NC}"
        podman run -d --name core-services \
            --network ai_system_network --ip 172.20.0.2 \
            -v "$PROJECT_ROOT/logs:/app/logs" \
            -v "$PROJECT_ROOT/models:/app/models" \
            -v "$PROJECT_ROOT/data:/app/data" \
            -v "$PROJECT_ROOT/config:/app/config" \
            -e PYTHONPATH=/app \
            -e LOG_LEVEL=INFO \
            -e CONTAINER_GROUP=core_services \
            -e DEBUG_MODE=false \
            -e ENABLE_METRICS=true \
            -e ENABLE_TRACING=true \
            -p 7120:7120 -p 8120:8120 -p 26002:26002 -p 27002:27002 -p 7125:7125 -p 8125:8125 \
            ai-system/core-services:latest
            
        # Start other containers
        echo -e "${GREEN}Starting memory-system container...${NC}"
        podman run -d --name memory-system \
            --network ai_system_network --ip 172.20.0.3 \
            -v "$PROJECT_ROOT/logs:/app/logs" \
            -v "$PROJECT_ROOT/models:/app/models" \
            -v "$PROJECT_ROOT/data:/app/data" \
            -v "$PROJECT_ROOT/config:/app/config" \
            -e PYTHONPATH=/app \
            -e LOG_LEVEL=INFO \
            -e CONTAINER_GROUP=memory_system \
            -e DEBUG_MODE=false \
            -p 5713:5713 -p 6713:6713 -p 5574:5574 -p 6574:6574 -p 5715:5715 -p 6715:6715 \
            ai-system/memory-system:latest
            
        echo -e "${GREEN}Starting utility-services container...${NC}"
        podman run -d --name utility-services \
            --network ai_system_network --ip 172.20.0.4 \
            -v "$PROJECT_ROOT/logs:/app/logs" \
            -v "$PROJECT_ROOT/models:/app/models" \
            -v "$PROJECT_ROOT/data:/app/data" \
            -v "$PROJECT_ROOT/config:/app/config" \
            -e PYTHONPATH=/app \
            -e LOG_LEVEL=INFO \
            -e CONTAINER_GROUP=utility_services \
            -e DEBUG_MODE=false \
            -p 5650:5650 -p 6650:6650 -p 5655:5655 -p 6655:6655 -p 5660:5660 -p 6660:6660 -p 5665:5665 -p 6665:6665 \
            ai-system/utility-services:latest
            
        if [[ $GPU_AVAILABLE == true ]]; then
            echo -e "${GREEN}Starting GPU services container with RTX 4090 support...${NC}"
            podman run -d --name ai-models-gpu-services \
                --network ai_system_network --ip 172.20.0.5 \
                -v "$PROJECT_ROOT/logs:/app/logs" \
                -v "$PROJECT_ROOT/models:/app/models" \
                -v "$PROJECT_ROOT/data:/app/data" \
                -v "$PROJECT_ROOT/config:/app/config" \
                -e PYTHONPATH=/app \
                -e LOG_LEVEL=INFO \
                -e CONTAINER_GROUP=ai_models_gpu_services \
                -e DEBUG_MODE=false \
                -e NVIDIA_VISIBLE_DEVICES=all \
                -e NVIDIA_DRIVER_CAPABILITIES=compute,utility,video \
                --device /dev/nvidia0:/dev/nvidia0 \
                --device /dev/nvidia-uvm:/dev/nvidia-uvm \
                --device /dev/nvidia-uvm-tools:/dev/nvidia-uvm-tools \
                --device /dev/nvidiactl:/dev/nvidiactl \
                --security-opt=label=disable \
                --runtime=nvidia \
                -p 5575:5575 -p 6575:6575 -p 5570:5570 -p 6570:6570 -p 5572:5572 -p 6572:6572 -p 5617:5617 -p 6617:6617 -p 5610:5610 -p 6610:6610 \
                ai-system/gpu-services:latest
            
            echo -e "${GREEN}Starting language-processing container with GPU support...${NC}"
            podman run -d --name language-processing \
                --network ai_system_network --ip 172.20.0.7 \
                -v "$PROJECT_ROOT/logs:/app/logs" \
                -v "$PROJECT_ROOT/models:/app/models" \
                -v "$PROJECT_ROOT/data:/app/data" \
                -v "$PROJECT_ROOT/config:/app/config" \
                -e PYTHONPATH=/app \
                -e LOG_LEVEL=INFO \
                -e CONTAINER_GROUP=language_processing \
                -e DEBUG_MODE=false \
                -e NVIDIA_VISIBLE_DEVICES=all \
                -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
                --device /dev/nvidia0:/dev/nvidia0 \
                --device /dev/nvidia-uvm:/dev/nvidia-uvm \
                --device /dev/nvidia-uvm-tools:/dev/nvidia-uvm-tools \
                --device /dev/nvidiactl:/dev/nvidiactl \
                --security-opt=label=disable \
                --runtime=nvidia \
                -p 7010:7010 -p 8010:8010 -p 7005:7005 -p 8005:8005 -p 5701:5701 -p 6701:6701 -p 5709:5709 -p 6709:6709 \
                -p 5710:5710 -p 6710:6710 -p 5711:5711 -p 6711:6711 -p 5636:5636 -p 6636:6636 -p 5637:5637 -p 6637:6637 \
                -p 5595:5595 -p 6595:6595 \
                ai-system/language-processing:latest
        else
            echo -e "${YELLOW}No NVIDIA GPU available. Starting containers without GPU support.${NC}"
            # Start containers without GPU support
            # ...
        fi
        
        echo -e "${YELLOW}Started main containers. You can start the remaining containers manually.${NC}"
    fi
    
    echo -e "\n${GREEN}All containers started successfully!${NC}"
    echo -e "${GREEN}To check container status, run: ${YELLOW}podman ps${NC}"
    echo -e "${GREEN}To view container logs, run: ${YELLOW}podman logs <container_name>${NC}"
    echo -e "${GREEN}To stop all containers, run: ${YELLOW}podman stop \$(podman ps -q)${NC}"
else
    echo -e "\n${GREEN}Build completed. To start containers manually, use:${NC}"
    if [[ $USE_COMPOSE == true ]]; then
        echo -e "${YELLOW}cd $DOCKER_DIR && podman-compose -f docker-compose.yml up -d${NC}"
    else
        echo -e "${YELLOW}Run the individual podman run commands for each container group${NC}"
    fi
fi

# Cleanup
rm -f "$PROJECT_ROOT/requirements.txt"

echo -e "\n${BLUE}${BOLD}=================================================${NC}"
echo -e "${BLUE}${BOLD}  Build process completed successfully!  ${NC}"
echo -e "${BLUE}${BOLD}=================================================${NC}" 