#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==== Testing Basic Container ====${NC}"

# Directory paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Stop and remove old container
sudo podman rm -f basic-test 2>/dev/null || true

# Run core-services container in host network mode
echo -e "${GREEN}Starting basic test container...${NC}"
sudo podman run -d --name basic-test \
    --net=host \
    -e CONTAINER_GROUP="core-services" \
    -v "$PROJECT_ROOT/logs:/app/logs" \
    -v "$PROJECT_ROOT/data:/app/data" \
    -v "$PROJECT_ROOT/models:/app/models" \
    docker.io/ai-system/core-services:latest

# Show running containers
echo -e "${GREEN}Running containers:${NC}"
sudo podman ps

# Wait a moment for the container to start
sleep 2

# Show logs
echo -e "${GREEN}Container logs:${NC}"
sudo podman logs basic-test
