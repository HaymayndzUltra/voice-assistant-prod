#!/bin/bash

# Script to stop all PC2 containers
# This script should be run from the project root directory

echo "Stopping PC2 containers..."

# Stop containers using podman-compose
cd pc2_code/docker
podman-compose -f podman-compose.yaml down

# Check if any containers are still running
echo "Checking for any remaining containers..."
remaining=$(podman ps --filter "name=pc2-" --format "{{.Names}}")

if [ -n "$remaining" ]; then
    echo "Some containers are still running. Stopping them forcefully..."
    podman stop $(podman ps --filter "name=pc2-" -q)
    podman rm $(podman ps -a --filter "name=pc2-" -q)
else
    echo "All containers stopped successfully!"
fi

# Optional: Clean up unused volumes and networks
read -p "Do you want to clean up unused volumes and networks? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleaning up unused volumes..."
    podman volume prune -f
    echo "Cleaning up unused networks..."
    podman network prune -f
fi

echo "Cleanup complete!" 