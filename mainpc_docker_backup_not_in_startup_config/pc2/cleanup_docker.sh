#!/bin/bash

# Docker Cleanup Script for PC2
# This script removes unused Docker containers, images, volumes, and networks

echo "===== Docker Cleanup Script for PC2 ====="
echo "This will remove all unused Docker resources to free up space"
echo "Started: $(date)"
echo ""

# Stop all running containers first
echo "[1/7] Stopping all running containers..."
docker stop $(docker ps -q) 2>/dev/null || echo "No running containers to stop."

# Remove all containers related to old PC2 system
echo "[2/7] Removing all PC2-related containers..."
docker rm $(docker ps -a | grep 'ai-system-pc2\|pc2\|cascade' | awk '{print $1}') 2>/dev/null || echo "No PC2-related containers to remove."

# Remove all stopped containers
echo "[3/7] Removing all stopped containers..."
docker container prune -f

# Remove all unused images
echo "[4/7] Removing all unused images..."
docker image prune -a -f

# Remove all dangling volumes
echo "[5/7] Removing all dangling volumes..."
docker volume prune -f

# Remove all unused networks
echo "[6/7] Removing all unused networks..."
docker network prune -f

# Remove all build cache
echo "[7/7] Removing Docker build cache..."
docker builder prune -a -f

# Show disk usage after cleanup
echo ""
echo "===== Cleanup Complete ====="
echo "Docker disk usage after cleanup:"
docker system df

echo ""
echo "You can now build the new PC2 containers with:"
echo "cd docker/pc2"
echo "docker-compose -f docker-compose.enhanced.yml build"
echo ""
echo "Completed: $(date)" 