#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==== Testing Single Container ====${NC}"

# Directory paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Try to create network
sudo podman network rm ai_system_network 2>/dev/null || true
sudo podman network create --subnet 172.20.0.0/16 ai_system_network

# Stop and remove old container
sudo podman rm -f core-services 2>/dev/null || true

# Run core-services container
echo -e "${GREEN}Starting core-services container...${NC}"
sudo podman run -d --name core-services \
    --network ai_system_network \
    -e CONTAINER_GROUP="core-services" \
    -v "$PROJECT_ROOT/logs:/app/logs" \
    -v "$PROJECT_ROOT/data:/app/data" \
    -v "$PROJECT_ROOT/models:/app/models" \
    docker.io/ai-system/core-services:latest

# Show running containers
echo -e "${GREEN}Running containers:${NC}"
sudo podman ps

# Show logs
echo -e "${GREEN}Container logs:${NC}"
sudo podman logs core-services
