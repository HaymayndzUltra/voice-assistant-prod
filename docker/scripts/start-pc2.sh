#!/bin/bash

# PC2 Docker Startup Script  
# Purpose: Start lightweight forwarder with RTX 3060

set -e

echo "🚀 Starting PC2 Docker Services (Forwarder - RTX 3060)"
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

# Check MainPC connectivity
echo "🔍 Checking MainPC connectivity..."
if ping -c 1 192.168.100.16 &> /dev/null; then
    echo "✅ MainPC (192.168.100.16) is reachable"
else
    echo "❌ MainPC (192.168.100.16) is not reachable. Check network connection."
    exit 1
fi

# Navigate to PC2 docker directory
cd "$(dirname "$0")/../pc2"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p ../../logs ../../data ../../cache

# Create external network if it doesn't exist
echo "🌐 Setting up Docker network..."
docker network create ai_system_cross_machine --driver bridge --subnet=172.22.0.0/16 2>/dev/null || echo "Network already exists"

# Pull latest images
echo "📦 Pulling base images..."
docker-compose -f docker-compose.pc2.yml pull

# Build custom images
echo "🔧 Building PC2 images..."
docker-compose -f docker-compose.pc2.yml build

# Start services
echo "🚀 Starting PC2 services..."
docker-compose -f docker-compose.pc2.yml up -d

# Check service health
echo "🔍 Checking service health..."
sleep 10

services=("pc2-redis" "pc2-observability-hub" "pc2-resource-manager")
for service in "${services[@]}"; do
    if docker ps --filter "name=$service" --filter "status=running" | grep -q "$service"; then
        echo "✅ $service: Running"
    else
        echo "❌ $service: Not running"
    fi
done

# Test connection to MainPC
echo "🔗 Testing MainPC connection..."
if curl -s http://192.168.100.16:9000/health &> /dev/null; then
    echo "✅ MainPC ObservabilityHub connection: OK"
else
    echo "⚠️  MainPC ObservabilityHub connection: Failed (may still be starting)"
fi

echo ""
echo "🎉 PC2 Docker services started!"
echo "📊 Local ObservabilityHub: http://192.168.100.17:9000"
echo "🏥 Health Check: http://192.168.100.17:9100"
echo "🔗 Forwarding to MainPC: http://192.168.100.16:9000"
echo ""
echo "📋 To view logs: docker-compose -f docker-compose.pc2.yml logs -f"
echo "🛑 To stop: docker-compose -f docker-compose.pc2.yml down" 