#!/bin/bash

echo "🚀 Building and running infra_core containers..."

# Navigate to project root
cd "$(dirname "$0")/../.."

echo "📦 Building infra_core image with --no-cache..."
sudo docker build --no-cache -t infra_core:latest -f docker/infra_core/Dockerfile .

if [ $? -eq 0 ]; then
    echo "✅ Image built successfully!"
else
    echo "❌ Image build failed!"
    exit 1
fi

echo "🌐 Creating network (if it doesn't exist)..."
sudo docker network create ai_system_network 2>/dev/null || echo "Network already exists"

echo "🔧 Starting backend services (Redis & NATS)..."
cd docker/infra_core
sudo docker compose up -d redis nats

sleep 5

echo "🤖 Starting infra core agents..."
sudo docker compose up -d service_registry system_digital_twin

sleep 10

echo "🏥 Testing health endpoints..."
echo -n "ServiceRegistry (8200): "
curl -s -f http://localhost:8200/health > /dev/null && echo "✅ Healthy" || echo "❌ Failed"

echo -n "SystemDigitalTwin (8220): "
curl -s -f http://localhost:8220/health > /dev/null && echo "✅ Healthy" || echo "❌ Failed"

echo ""
echo "📋 Container status:"
sudo docker compose ps

echo ""
echo "📝 To check logs:"
echo "  sudo docker logs -f service_registry"
echo "  sudo docker logs -f system_digital_twin"

echo ""
echo "🎯 If both health checks are ✅, reply: infra_core OK"
