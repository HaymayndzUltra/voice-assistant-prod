#!/bin/bash

# PC2 Startup Script - RTX 3060 Lightweight System
# Creates 5 container groups for efficient resource utilization

set -e

echo "🚀 Starting PC2 AI System (RTX 3060)"
echo "======================================"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if network exists, create if it doesn't
if ! docker network ls | grep -q ai_system_network; then
    echo "🌐 Creating ai_system_network..."
    docker network create ai_system_network
else
    echo "✅ ai_system_network already exists"
fi

# Navigate to docker directory
cd "$(dirname "$0")"

echo ""
echo "🐳 Building and starting PC2 container groups..."
echo ""

# Build and start all PC2 services
docker compose -f docker-compose.pc2.yml up -d --build

echo ""
echo "⏳ Waiting for services to initialize..."
sleep 30

echo ""
echo "🔍 Checking container status..."
docker compose -f docker-compose.pc2.yml ps

echo ""
echo "📊 PC2 Container Groups Status:"
echo "================================"

# Check health of each group
groups=("memory-services" "ai-reasoning" "web-services" "infrastructure" "observability-forwarder")

for group in "${groups[@]}"; do
    container="pc2-${group}"
    if docker ps --format "table {{.Names}}" | grep -q "$container"; then
        echo "✅ $group: Running"
    else
        echo "❌ $group: Not running"
    fi
done

echo ""
echo "🎯 PC2 Services Available:"
echo "========================="
echo "Memory Services:    ports 7140, 7102, 7105, 7111, 7112"
echo "AI Reasoning:       ports 7104, 7127, 7108, 7131, 7150"  
echo "Web Services:       ports 7123, 7124, 7126"
echo "Infrastructure:     ports 7100, 7101, 7113, 7115, 7129, 7116, 7118, 7119, 7122"
echo "Observability:      port 9000 (forwards to MainPC)"

echo ""
echo "🔗 Cross-machine communication:"
echo "PC2 → MainPC: http://192.168.100.16:9000"
echo "MainPC → PC2: http://192.168.100.17:9000"

echo ""
echo "🚀 PC2 AI System startup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Verify all containers are healthy"
echo "2. Test cross-machine communication" 
echo "3. Run end-to-end validation"

# Show logs command for debugging
echo ""
echo "💡 To view logs: docker compose -f docker-compose.pc2.yml logs -f [service-name]"
echo "💡 To stop: docker compose -f docker-compose.pc2.yml down" 