#!/bin/bash

# PC2 Complete Rebuild Script
# This script cleans old Docker resources, rebuilds all PC2 containers, and starts the system

echo "===== PC2 Complete Rebuild Script ====="
echo "Started: $(date)"
echo ""

# Change to the script directory
cd "$(dirname "$0")"

# Set to exit on error
set -e

# Check if running as root or with sudo
if [ "$(id -u)" -ne 0 ]; then
    echo "WARNING: This script may need elevated privileges to clean Docker resources"
    echo "Consider running with sudo if errors occur"
    echo ""
fi

# Step 1: Check Docker is running
echo "[1/7] Checking Docker service..."
if ! docker info &>/dev/null; then
    echo "ERROR: Docker is not running! Please start Docker first."
    exit 1
fi
echo "✓ Docker is running"

# Step 2: Backup data if needed
echo ""
echo "[2/7] Backing up important data..."
BACKUP_DIR="../../backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup configuration files
if [ -d "../../config" ]; then
    echo "Backing up config files..."
    cp -r ../../config "$BACKUP_DIR/"
fi

# Backup data
if [ -d "../../data" ]; then
    echo "Backing up essential data..."
    mkdir -p "$BACKUP_DIR/data"
    # Only backup small essential data, not large files
    find ../../data -type f -size -10M | grep -v ".bin\|.pt\|.ckpt" | xargs -I{} cp --parents {} "$BACKUP_DIR/"
fi
echo "✓ Backup created in $BACKUP_DIR"

# Step 3: Clean up Docker resources
echo ""
echo "[3/7] Cleaning up Docker resources..."
# Source the cleanup script
if [ -f "./cleanup_docker.sh" ]; then
    bash ./cleanup_docker.sh
else
    echo "Warning: cleanup_docker.sh not found, skipping detailed cleanup"
    # Fallback cleanup
    docker stop $(docker ps -q) 2>/dev/null || true
    docker system prune -af --volumes
fi

# Step 4: Check prerequisites
echo ""
echo "[4/7] Checking prerequisites..."

# Check disk space
AVAILABLE_GB=$(df -k . | awk 'NR==2 {print $4 / 1024 / 1024}')
if (( $(echo "$AVAILABLE_GB < 20" | bc -l) )); then
    echo "WARNING: Less than 20GB available disk space (${AVAILABLE_GB}GB). Build might fail."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Build cancelled by user."
        exit 1
    fi
else
    echo "✓ Sufficient disk space available (${AVAILABLE_GB}GB)"
fi

# Check Docker Compose file
if [ ! -f "docker-compose.enhanced.yml" ]; then
    echo "ERROR: docker-compose.enhanced.yml not found!"
    exit 1
fi
echo "✓ Found docker-compose.enhanced.yml"

# Check .dockerignore
if [ ! -f "../.dockerignore" ]; then
    echo "WARNING: .dockerignore not found, build might include unnecessary files"
else
    echo "✓ Found .dockerignore file"
fi

# Step 5: Rebuild all containers
echo ""
echo "[5/7] Rebuilding all PC2 containers..."
# Force rebuild with no cache
docker-compose -f docker-compose.enhanced.yml build --no-cache

# Step 6: Create necessary directories for volumes
echo ""
echo "[6/7] Creating necessary directories for volumes..."
mkdir -p ../../data/redis
mkdir -p ../../data/users
mkdir -p ../../data/monitoring
mkdir -p ../../logs
mkdir -p ../../models/language
mkdir -p ../../models/vision
mkdir -p ../../models/generative
mkdir -p ../../models/memory
mkdir -p ../../models/translation
echo "✓ Volume directories created"

# Step 7: Start the services
echo ""
echo "[7/7] Starting PC2 services..."
docker-compose -f docker-compose.enhanced.yml up -d

# Show running services
echo ""
echo "===== PC2 System Status ====="
docker-compose -f docker-compose.enhanced.yml ps

echo ""
echo "===== PC2 System Rebuild Complete ====="
echo "The system has been rebuilt and started"
echo ""
echo "To monitor all services:"
echo "  docker-compose -f docker-compose.enhanced.yml logs -f"
echo ""
echo "To monitor a specific service:"
echo "  docker-compose -f docker-compose.enhanced.yml logs -f [service-name]"
echo ""
echo "To stop all services:"
echo "  docker-compose -f docker-compose.enhanced.yml down"
echo ""
echo "Completed: $(date)" 