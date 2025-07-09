#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==== Running AI System Agent Containers ====${NC}"

# Directory paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Define agent groups
GROUPS=("core-services" "memory-system" "utility-services" "ai-models-gpu-services" 
        "vision-system" "learning-knowledge" "language-processing" 
        "audio-processing" "emotion-system" "utilities-support" "security-auth")

# 1. Clean up old containers
echo -e "${GREEN}Removing old containers...${NC}"
for group in "${GROUPS[@]}"; do
    sudo podman rm -f "$group" 2>/dev/null || true
done

# 2. Launch containers
echo -e "${GREEN}Launching agent containers...${NC}"
for group in "${GROUPS[@]}"; do
    echo -e "${YELLOW}Starting $group...${NC}"
    sudo podman run -d --name "$group" \
        --network ai_system_network \
        -e CONTAINER_GROUP="$group" \
        -v "$PROJECT_ROOT/logs:/app/logs" \
        -v "$PROJECT_ROOT/data:/app/data" \
        -v "$PROJECT_ROOT/models:/app/models" \
        "docker.io/ai-system/$group:latest"
done

# 3. Add GPU support for specific containers
if [ -e /dev/nvidia0 ]; then
    echo -e "${GREEN}Adding GPU support for AI model and language containers...${NC}"
    sudo podman stop "ai-models-gpu-services" "language-processing" || true
    sudo podman rm "ai-models-gpu-services" "language-processing" || true
    
    sudo podman run -d --name "ai-models-gpu-services" \
        --network ai_system_network \
        -e CONTAINER_GROUP="ai-models-gpu-services" \
        -v "$PROJECT_ROOT/logs:/app/logs" \
        -v "$PROJECT_ROOT/data:/app/data" \
        -v "$PROJECT_ROOT/models:/app/models" \
        --device /dev/nvidia0:/dev/nvidia0 \
        --device /dev/nvidiactl:/dev/nvidiactl \
        --device /dev/nvidia-uvm:/dev/nvidia-uvm \
        "docker.io/ai-system/ai-models-gpu-services:latest"
        
    sudo podman run -d --name "language-processing" \
        --network ai_system_network \
        -e CONTAINER_GROUP="language-processing" \
        -v "$PROJECT_ROOT/logs:/app/logs" \
        -v "$PROJECT_ROOT/data:/app/data" \
        -v "$PROJECT_ROOT/models:/app/models" \
        --device /dev/nvidia0:/dev/nvidia0 \
        --device /dev/nvidiactl:/dev/nvidiactl \
        --device /dev/nvidia-uvm:/dev/nvidia-uvm \
        "docker.io/ai-system/language-processing:latest"
fi

# 4. Show running containers
echo -e "${GREEN}All containers started! Running containers:${NC}"
sudo podman ps

# 5. Monitor logs (optional)
echo -e "${YELLOW}To view logs from a container, run:${NC}"
echo -e "sudo podman logs -f <container-name>"
