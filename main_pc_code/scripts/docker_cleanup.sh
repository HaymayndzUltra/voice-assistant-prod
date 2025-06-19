#!/bin/bash

echo "Starting Docker cleanup..."

# Stop all containers
echo "Stopping all containers..."
docker stop $(docker ps -aq) 2>/dev/null || true

# Remove all stopped containers
echo "Removing stopped containers..."
docker container prune -f

# Remove unused images
echo "Removing unused images..."
docker image prune -a -f

# Remove unused volumes
echo "Removing unused volumes..."
docker volume prune -f

# Remove unused networks
echo "Removing unused networks..."
docker network prune -f

# Remove build cache
echo "Removing build cache..."
docker builder prune -f

# Clean up system
echo "Cleaning up system..."
docker system prune -f

echo "Cleanup complete!"

# Show current disk usage
echo "Current Docker disk usage:"
docker system df 