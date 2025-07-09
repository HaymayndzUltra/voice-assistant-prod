#!/bin/bash
# Script to start MainPC containers

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${GREEN}Starting MainPC Containers${NC}"
echo -e "${GREEN}=======================${NC}"
echo

# Check if the container image exists
if ! podman image exists ai-system:cuda-wsl2; then
    echo -e "${RED}Container image not found!${NC}"
    echo -e "${YELLOW}Please run setup.sh first to build the container image.${NC}"
    exit 1
fi

# Start core-services container
echo -e "${YELLOW}Starting core-services container...${NC}"
"$SCRIPT_DIR/scripts/launch_wsl2_container.sh" core-services &
echo -e "${GREEN}Started core-services container.${NC}"
echo -e "${YELLOW}Waiting for core services to initialize (10 seconds)...${NC}"
sleep 10

# Start memory-system container
echo -e "${YELLOW}Starting memory-system container...${NC}"
"$SCRIPT_DIR/scripts/launch_wsl2_container.sh" memory-system &
echo -e "${GREEN}Started memory-system container.${NC}"
sleep 5

# Start utility-services container
echo -e "${YELLOW}Starting utility-services container...${NC}"
"$SCRIPT_DIR/scripts/launch_wsl2_container.sh" utility-services &
echo -e "${GREEN}Started utility-services container.${NC}"
sleep 5

# Check if GPU is available
if command -v nvidia-smi &> /dev/null; then
    # Start ai-models-gpu-services container
    echo -e "${YELLOW}Starting ai-models-gpu-services container...${NC}"
    "$SCRIPT_DIR/scripts/launch_wsl2_container.sh" ai-models-gpu-services &
    echo -e "${GREEN}Started ai-models-gpu-services container.${NC}"
    sleep 5

    # Start language-processing container
    echo -e "${YELLOW}Starting language-processing container...${NC}"
    "$SCRIPT_DIR/scripts/launch_wsl2_container.sh" language-processing &
    echo -e "${GREEN}Started language-processing container.${NC}"
else
    echo -e "${RED}NVIDIA GPU not found. Skipping GPU-dependent containers.${NC}"
fi

echo
echo -e "${GREEN}All MainPC containers started!${NC}"
echo -e "${YELLOW}To view container logs:${NC}"
echo -e "${GREEN}podman logs -f ai-system-core-services${NC}"
echo -e "${GREEN}podman logs -f ai-system-memory-system${NC}"
echo -e "${GREEN}podman logs -f ai-system-utility-services${NC}"
echo -e "${GREEN}podman logs -f ai-system-ai-models-gpu-services${NC}"
echo -e "${GREEN}podman logs -f ai-system-language-processing${NC}"
echo
echo -e "${YELLOW}To stop all containers:${NC}"
echo -e "${GREEN}podman stop \$(podman ps -q)${NC}"
echo 