#!/bin/bash
# Script to copy and adapt the docker-compose.yml file from mainpc for podman

# Exit on any error
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Copying and adapting docker-compose.yml for podman...${NC}"

# Directory paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DOCKER_MAINPC_DIR="$PROJECT_ROOT/docker/mainpc"
DOCKER_PODMAN_DIR="$PROJECT_ROOT/docker/podman"

# Check if docker-compose.yml exists in mainpc directory
if [ ! -f "$DOCKER_MAINPC_DIR/docker-compose.yml" ]; then
    echo -e "${RED}Error: docker-compose.yml not found in $DOCKER_MAINPC_DIR${NC}"
    exit 1
fi

# Copy docker-compose.yml from mainpc to podman directory
echo -e "${GREEN}Copying docker-compose.yml from mainpc to podman directory...${NC}"
cp "$DOCKER_MAINPC_DIR/docker-compose.yml" "$DOCKER_PODMAN_DIR/docker-compose.yml"

# Adapt docker-compose.yml for podman
echo -e "${GREEN}Adapting docker-compose.yml for podman...${NC}"

# Replace Docker-specific settings with Podman-compatible ones
sed -i 's/runtime: nvidia/runtime: nvidia/g' "$DOCKER_PODMAN_DIR/docker-compose.yml"

# Update build context paths
sed -i 's|context: ../../|context: ../../../|g' "$DOCKER_PODMAN_DIR/docker-compose.yml"

# Update Dockerfile paths
sed -i 's|dockerfile: docker/mainpc/Dockerfile|dockerfile: docker/podman/Dockerfile.base|g' "$DOCKER_PODMAN_DIR/docker-compose.yml"

# Add podman-specific labels
sed -i '/restart: unless-stopped/a\    labels:\n      - "io.podman.annotations.autoremove=false"' "$DOCKER_PODMAN_DIR/docker-compose.yml"

echo -e "${GREEN}docker-compose.yml has been copied and adapted for podman.${NC}"
echo -e "${YELLOW}You may need to manually review and adjust the file for your specific podman setup.${NC}" 