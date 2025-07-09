#!/bin/bash
# Script to start PC2 containers

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${GREEN}Starting PC2 Containers${NC}"
echo -e "${GREEN}====================${NC}"
echo

# Check if the container image exists
if ! podman image exists ai-system:cuda-wsl2; then
    echo -e "${RED}Container image not found!${NC}"
    echo -e "${YELLOW}Please run setup.sh first to build the container image.${NC}"
    exit 1
fi

# Start pc2-core-services container
echo -e "${YELLOW}Starting pc2-core-services container...${NC}"
"$SCRIPT_DIR/scripts/launch_pc2_container.sh" pc2-core-services &
echo -e "${GREEN}Started pc2-core-services container.${NC}"
echo -e "${YELLOW}Waiting for core services to initialize (10 seconds)...${NC}"
sleep 10

# Start pc2-security-services container
echo -e "${YELLOW}Starting pc2-security-services container...${NC}"
"$SCRIPT_DIR/scripts/launch_pc2_container.sh" pc2-security-services &
echo -e "${GREEN}Started pc2-security-services container.${NC}"
sleep 5

# Start pc2-memory-services container
echo -e "${YELLOW}Starting pc2-memory-services container...${NC}"
"$SCRIPT_DIR/scripts/launch_pc2_container.sh" pc2-memory-services &
echo -e "${GREEN}Started pc2-memory-services container.${NC}"
sleep 5

# Start pc2-task-services container
echo -e "${YELLOW}Starting pc2-task-services container...${NC}"
"$SCRIPT_DIR/scripts/launch_pc2_container.sh" pc2-task-services &
echo -e "${GREEN}Started pc2-task-services container.${NC}"
sleep 5

# Check if GPU is available
if command -v nvidia-smi &> /dev/null; then
    # Start pc2-ai-services container
    echo -e "${YELLOW}Starting pc2-ai-services container...${NC}"
    "$SCRIPT_DIR/scripts/launch_pc2_container.sh" pc2-ai-services &
    echo -e "${GREEN}Started pc2-ai-services container.${NC}"
    sleep 5
else
    echo -e "${RED}NVIDIA GPU not found. Skipping GPU-dependent containers.${NC}"
fi

# Start pc2-web-services container
echo -e "${YELLOW}Starting pc2-web-services container...${NC}"
"$SCRIPT_DIR/scripts/launch_pc2_container.sh" pc2-web-services &
echo -e "${GREEN}Started pc2-web-services container.${NC}"

echo
echo -e "${GREEN}All PC2 containers started!${NC}"
echo -e "${YELLOW}To view container logs:${NC}"
echo -e "${GREEN}podman logs -f ai-system-pc2-core-services${NC}"
echo -e "${GREEN}podman logs -f ai-system-pc2-security-services${NC}"
echo -e "${GREEN}podman logs -f ai-system-pc2-memory-services${NC}"
echo -e "${GREEN}podman logs -f ai-system-pc2-task-services${NC}"
echo -e "${GREEN}podman logs -f ai-system-pc2-ai-services${NC}"
echo -e "${GREEN}podman logs -f ai-system-pc2-web-services${NC}"
echo
echo -e "${YELLOW}To stop all containers:${NC}"
echo -e "${GREEN}podman stop \$(podman ps -q)${NC}"
echo 