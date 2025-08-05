#!/bin/bash

# Docker Check Script for PC2
# This script checks Docker system resources and existing containers before building new ones

echo "===== Docker System Check for PC2 ====="
echo "Started: $(date)"
echo ""

# Check if Docker is running
echo "[1/6] Checking if Docker is running..."
if ! docker info &>/dev/null; then
    echo "ERROR: Docker is not running! Please start Docker first."
    exit 1
else
    echo "✓ Docker is running"
fi

# Check Docker system resources
echo "[2/6] Checking Docker system resources..."
echo "Current Docker disk usage:"
docker system df

# Check available disk space
echo ""
echo "[3/6] Checking available disk space..."
AVAILABLE_SPACE=$(df -h / | awk 'NR==2 {print $4}')
echo "Available disk space: $AVAILABLE_SPACE"

if df -h / | awk 'NR==2 {print $4}' | grep -q "^[0-9]\+G"; then
    AVAILABLE_GB=$(df -k / | awk 'NR==2 {print $4 / 1024 / 1024}')
    if (( $(echo "$AVAILABLE_GB < 20" | bc -l) )); then
        echo "⚠️  WARNING: Less than 20GB available disk space. Cleaning recommended before building."
    else
        echo "✓ Sufficient disk space available"
    fi
else
    echo "⚠️  WARNING: Low disk space detected. Cleaning recommended before building."
fi

# Check existing PC2 containers
echo ""
echo "[4/6] Checking existing PC2 containers..."
EXISTING_CONTAINERS=$(docker ps -a | grep -E 'ai-system-pc2|pc2|cascade' | wc -l)
if [ "$EXISTING_CONTAINERS" -gt 0 ]; then
    echo "⚠️  Found $EXISTING_CONTAINERS existing PC2-related containers:"
    docker ps -a | grep -E 'ai-system-pc2|pc2|cascade'
else
    echo "✓ No existing PC2 containers found"
fi

# Check existing PC2 images
echo ""
echo "[5/6] Checking existing PC2 images..."
EXISTING_IMAGES=$(docker images | grep -E 'ai-system-pc2|pc2|cascade' | wc -l)
if [ "$EXISTING_IMAGES" -gt 0 ]; then
    echo "⚠️  Found $EXISTING_IMAGES existing PC2-related images:"
    docker images | grep -E 'ai-system-pc2|pc2|cascade'
else
    echo "✓ No existing PC2 images found"
fi

# Check Docker Compose file
echo ""
echo "[6/6] Checking Docker Compose file..."
if [ -f "docker-compose.enhanced.yml" ]; then
    echo "✓ Found docker-compose.enhanced.yml"
else
    echo "❌ ERROR: docker-compose.enhanced.yml not found in current directory!"
    echo "Please run this script from the docker/pc2/ directory"
    exit 1
fi

# Summary and recommendations
echo ""
echo "===== System Check Summary ====="
if [ "$EXISTING_CONTAINERS" -gt 0 ] || [ "$EXISTING_IMAGES" -gt 0 ]; then
    echo "⚠️  Recommendations:"
    echo "   - Run cleanup_docker.sh script to remove old containers and images"
    echo "   - Then build new containers with: docker-compose -f docker-compose.enhanced.yml build"
else
    echo "✓ System ready for building new PC2 containers"
    echo "   You can build with: docker-compose -f docker-compose.enhanced.yml build"
fi

echo ""
echo "Completed: $(date)" 