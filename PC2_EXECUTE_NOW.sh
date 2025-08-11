#!/bin/bash
# PC2 DEPLOYMENT SCRIPT - Phase 4
# Run this on PC2 (3060 GPU machine)

set -e  # Exit on error

echo "================================================"
echo "Phase 4 PC2 Deployment - Starting"
echo "================================================"

# Step 1: Setup
cd /home/haymayndz/AI_System_Monorepo || exit 1
echo "📁 Current directory: $(pwd)"

# Step 2: Get latest code
echo ""
echo "📥 Getting latest code..."
git fetch origin
git checkout cursor/build-and-deploy-ai-system-services-0e14
git pull origin cursor/build-and-deploy-ai-system-services-0e14

# Step 3: Set variables
export ORG=haymayndzultra
export GHCR_PAT=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
export DATE=$(date -u +%Y%m%d)
export SHA=$(git rev-parse --short HEAD)
export TAG="${DATE}-${SHA}"

echo ""
echo "🏷️  Using TAG: $TAG"
echo "🖥️  Machine: PC2 (3060 GPU)"
echo ""

# Step 4: Login to GHCR
echo "🔐 Logging into GHCR..."
echo "$GHCR_PAT" | docker login ghcr.io -u "$ORG" --password-stdin

# Step 5: Pull pre-built images from GHCR (built on MainPC)
echo ""
echo "📥 Pulling PC2 services from GHCR..."

# CentralErrorBus (PC2 primary service)
echo "Pulling CentralErrorBus..."
docker pull ghcr.io/$ORG/ai_system/central_error_bus:$TAG

# Also pull services that can run on PC2 as backup/load balancing
echo "Pulling backup services for PC2..."
docker pull ghcr.io/$ORG/ai_system/unified_observability_center:$TAG
docker pull ghcr.io/$ORG/ai_system/self_healing_supervisor:$TAG

# Step 6: Deploy services
echo ""
echo "🚀 Deploying PC2 services..."

# Stop existing containers
docker stop central_error_bus 2>/dev/null || true
docker stop unified_observability_center 2>/dev/null || true
docker stop self_healing_supervisor 2>/dev/null || true

docker rm central_error_bus 2>/dev/null || true
docker rm unified_observability_center 2>/dev/null || true
docker rm self_healing_supervisor 2>/dev/null || true

# Run CentralErrorBus (main PC2 service)
echo "Starting CentralErrorBus on PC2..."
docker run -d \
  --name central_error_bus \
  --restart unless-stopped \
  --network host \
  -e MACHINE=pc2 \
  -v /etc/machine-profile.json:/etc/machine-profile.json:ro \
  ghcr.io/$ORG/ai_system/central_error_bus:$TAG

# Run UnifiedObservabilityCenter (backup/monitoring)
echo "Starting UnifiedObservabilityCenter on PC2..."
docker run -d \
  --name unified_observability_center \
  --restart unless-stopped \
  --network host \
  -e MACHINE=pc2 \
  -e HTTP_PORT=9111 \
  -e GRPC_PORT=9101 \
  -v /etc/machine-profile.json:/etc/machine-profile.json:ro \
  ghcr.io/$ORG/ai_system/unified_observability_center:$TAG

# Run SelfHealingSupervisor (system monitoring)
echo "Starting SelfHealingSupervisor on PC2..."
docker run -d \
  --name self_healing_supervisor \
  --restart unless-stopped \
  --network host \
  -e MACHINE=pc2 \
  -e HTTP_PORT=9009 \
  -e GRPC_PORT=7010 \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /etc/machine-profile.json:/etc/machine-profile.json:ro \
  ghcr.io/$ORG/ai_system/self_healing_supervisor:$TAG

# Step 7: Wait for services
echo ""
echo "⏳ Waiting 30 seconds for services to start..."
sleep 30

# Step 8: Health checks
echo ""
echo "================================================"
echo "🏥 PC2 HEALTH CHECK RESULTS"
echo "================================================"
echo ""

echo -n "CentralErrorBus (8150): "
curl -sf http://localhost:8150/health && echo " ✅" || echo " ❌"

echo -n "UnifiedObservabilityCenter (9111): "
curl -sf http://localhost:9111/health && echo " ✅" || echo " ❌"

echo -n "SelfHealingSupervisor (9009): "
curl -sf http://localhost:9009/health && echo " ✅" || echo " ❌"

# Step 9: Show running containers
echo ""
echo "📦 Running Containers on PC2:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "================================================"
echo "✅ PC2 Deployment Complete!"
echo "================================================"
echo "TAG used: $TAG"
echo ""
echo "PC2 is now running:"
echo "  - CentralErrorBus (primary)"
echo "  - UnifiedObservabilityCenter (backup monitoring)"
echo "  - SelfHealingSupervisor (system health)"
echo ""
echo "To check logs:"
echo "  docker logs central_error_bus"
echo "  docker logs unified_observability_center"
echo "  docker logs self_healing_supervisor"
echo ""
echo "To rollback:"
echo "  Use the previous working TAG"