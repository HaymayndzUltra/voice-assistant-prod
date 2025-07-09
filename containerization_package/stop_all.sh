#!/bin/bash
# Script to stop all containers

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Stopping All Containers${NC}"
echo -e "${GREEN}====================${NC}"
echo

# Check if any containers are running
if [ -z "$(podman ps -q)" ]; then
    echo -e "${YELLOW}No containers are currently running.${NC}"
    exit 0
fi

# Stop all containers
echo -e "${YELLOW}Stopping all containers...${NC}"
podman stop $(podman ps -q)

echo
echo -e "${GREEN}All containers stopped!${NC}"
echo 