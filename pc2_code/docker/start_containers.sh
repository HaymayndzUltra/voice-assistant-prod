#!/bin/bash

# Script to start all PC2 containers
# This script should be run from the project root directory

set -e  # Exit on error

echo "Starting PC2 containers..."

# Create directories if they don't exist
mkdir -p pc2_code/logs
mkdir -p pc2_code/data

# Check if the network exists, create if not
podman network exists pc2-network || podman network create pc2-network

# Start containers using podman-compose
cd pc2_code/docker
podman-compose -f podman-compose.yaml up -d

echo "Waiting for containers to initialize..."
sleep 10

# Check container status
echo "Container status:"
podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check container logs for any errors
echo "Checking container logs for errors..."
for container in pc2-core-infrastructure pc2-memory-storage pc2-security-authentication pc2-integration-communication pc2-monitoring-support pc2-dream-tutoring pc2-web-external; do
    echo "=== $container logs ==="
    podman logs --tail 10 $container
    echo ""
done

echo "All containers started!"
echo "To view logs: podman logs -f <container-name>"
echo "To stop containers: podman-compose -f pc2_code/docker/podman-compose.yaml down" 