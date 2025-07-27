#!/bin/bash

# Docker Cleanup Script for WSL2 Space Management
# Run this weekly or when Docker space gets too large

echo "🧹 Starting Docker cleanup process..."

# 1. Remove stopped containers
echo "Removing stopped containers..."
docker container prune -f

# 2. Remove unused images  
echo "Removing unused images..."
docker image prune -f

# 3. Remove unused networks
echo "Removing unused networks..."
docker network prune -f

# 4. Remove build cache (keep last 24h)
echo "Cleaning build cache (keeping last 24h)..."
docker builder prune --filter until=24h -f

# 5. Remove unused volumes (BE CAREFUL!)
echo "Removing unused volumes..."
docker volume prune -f

# 6. System-wide cleanup
echo "Running system-wide cleanup..."
docker system prune -f

# 7. Show current disk usage
echo "📊 Current Docker disk usage:"
sudo du -sh /var/lib/docker/
echo ""
docker system df

echo "✅ Cleanup completed!" 