#!/bin/bash

# MainPC Docker Startup Script
# Purpose: Start primary monitoring hub with RTX 4090

set -e

echo "🚀 Starting MainPC Docker Services (Primary Hub - RTX 4090)"
echo "=================================================="

# Check Docker and Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

# Check NVIDIA Docker runtime
if ! docker info | grep -q nvidia; then
    echo "⚠️  NVIDIA Docker runtime not detected. GPU features may not work."
fi

# Navigate to MainPC docker directory
cd "$(dirname "$0")/../mainpc"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p ../../logs ../../data ../../cache ../../models

# Create external network if it doesn't exist
echo "🌐 Setting up Docker network..."
docker network create ai_system_cross_machine --driver bridge --subnet=172.22.0.0/16 2>/dev/null || echo "Network already exists"

# Pull latest images
echo "📦 Pulling base images..."
docker-compose -f docker-compose.mainpc.yml pull

# Build custom images
echo "🔧 Building MainPC images..."
docker-compose -f docker-compose.mainpc.yml build

# Start services
echo "🚀 Starting MainPC services..."
docker-compose -f docker-compose.mainpc.yml up -d

# Check service health
echo "🔍 Checking service health..."
sleep 10

services=("mainpc-redis" "mainpc-observability-hub" "mainpc-service-registry")
for service in "${services[@]}"; do
    if docker ps --filter "name=$service" --filter "status=running" | grep -q "$service"; then
        echo "✅ $service: Running"
    else
        echo "❌ $service: Not running"
    fi
done

echo ""
echo "🎉 MainPC Docker services started!"
echo "📊 ObservabilityHub: http://192.168.100.16:9000"
echo "📈 Prometheus: http://192.168.100.16:9090"
echo "🏥 Health Check: http://192.168.100.16:9100"
echo ""
echo "📋 To view logs: docker-compose -f docker-compose.mainpc.yml logs -f"
echo "🛑 To stop: docker-compose -f docker-compose.mainpc.yml down" 