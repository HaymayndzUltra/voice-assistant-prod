#!/bin/bash
# Setup script for AI System containerization package

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo -e "${GREEN}AI System Containerization Package Setup${NC}"
echo -e "${GREEN}=======================================${NC}"
echo

# Make all scripts executable
echo -e "${YELLOW}Making scripts executable...${NC}"
chmod +x "$SCRIPT_DIR/scripts/launch_wsl2_container.sh"
chmod +x "$SCRIPT_DIR/scripts/launch_pc2_container.sh"
chmod +x "$SCRIPT_DIR/scripts/fix_wsl2_gpu.sh"
chmod +x "$SCRIPT_DIR/scripts/run_systemdigitaltwin.py"
chmod +x "$SCRIPT_DIR/scripts/run_memory_client.py"
chmod +x "$SCRIPT_DIR/scripts/run_pc2_health_monitor.py"
echo -e "${GREEN}Done!${NC}"
echo

# Check for Podman
echo -e "${YELLOW}Checking for Podman...${NC}"
if command -v podman &> /dev/null; then
    echo -e "${GREEN}Podman is installed.${NC}"
    podman --version
else
    echo -e "${RED}Podman is not installed.${NC}"
    echo -e "${YELLOW}Installing Podman...${NC}"
    sudo apt-get update
    sudo apt-get install -y podman
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Podman installed successfully.${NC}"
    else
        echo -e "${RED}Failed to install Podman. Please install it manually.${NC}"
        echo -e "${YELLOW}sudo apt-get update && sudo apt-get install -y podman${NC}"
    fi
fi
echo

# Check for NVIDIA GPU
echo -e "${YELLOW}Checking for NVIDIA GPU...${NC}"
if command -v nvidia-smi &> /dev/null; then
    echo -e "${GREEN}NVIDIA GPU found.${NC}"
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
    
    # Fix GPU device paths
    echo -e "${YELLOW}Fixing GPU device paths...${NC}"
    "$SCRIPT_DIR/scripts/fix_wsl2_gpu.sh"
else
    echo -e "${RED}NVIDIA GPU not found or drivers not installed.${NC}"
    echo -e "${YELLOW}Some containers may not work properly without GPU support.${NC}"
fi
echo

# Check if the container image exists
echo -e "${YELLOW}Checking for container image...${NC}"
if podman image exists ai-system:cuda-wsl2; then
    echo -e "${GREEN}Container image found.${NC}"
else
    echo -e "${RED}Container image not found.${NC}"
    echo -e "${YELLOW}Would you like to build the container image now? (y/n)${NC}"
    read -r build_image
    if [[ $build_image == "y" || $build_image == "Y" ]]; then
        echo -e "${YELLOW}Building container image...${NC}"
        if [ -f "$PROJECT_ROOT/docker/podman/build_wsl2_container.sh" ]; then
            "$PROJECT_ROOT/docker/podman/build_wsl2_container.sh"
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}Container image built successfully.${NC}"
            else
                echo -e "${RED}Failed to build container image.${NC}"
            fi
        else
            echo -e "${RED}Build script not found at $PROJECT_ROOT/docker/podman/build_wsl2_container.sh${NC}"
        fi
    else
        echo -e "${YELLOW}Skipping container image build.${NC}"
        echo -e "${YELLOW}You will need to build the image before running containers:${NC}"
        echo -e "${YELLOW}$PROJECT_ROOT/docker/podman/build_wsl2_container.sh${NC}"
    fi
fi
echo

echo -e "${GREEN}Setup complete!${NC}"
echo -e "${YELLOW}To get started, read the README.md file in this directory.${NC}"
echo -e "${YELLOW}For quick start, run:${NC}"
echo -e "${GREEN}./scripts/launch_wsl2_container.sh core-services${NC}"
echo 