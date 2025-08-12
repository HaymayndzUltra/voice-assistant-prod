#!/bin/bash
# AGENT 3: Build CPU Services
# Run this in Background Agent Session 3 (after Agent 2 finishes)

set -e

echo "============================================================"
echo "🚀 AGENT 3: BUILDING CPU SERVICES"
echo "============================================================"

# Setup Docker
echo "Setting up Docker daemon..."
sudo -n nohup dockerd -H unix:///var/run/docker.sock \
    --storage-driver=vfs \
    --iptables=false \
    --bridge=none > /dev/null 2>&1 &
sleep 5

# Login to GHCR
echo "Logging in to GHCR..."
export GHCR_TOKEN="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"
echo $GHCR_TOKEN | docker login ghcr.io -u haymayndzultra --password-stdin

# Wait for family images to be ready
echo "Checking if family images are ready..."
while ! docker pull ghcr.io/haymayndzultra/family-web:latest; do
    echo "Waiting for family images to complete..."
    sleep 30
done
echo "✅ Family images ready!"

cd /workspace

# Build CPU services
echo "Building UnifiedObservabilityCenter..."
docker build -f unified_observability_center/Dockerfile.optimized \
    --build-arg MACHINE=mainpc \
    -t ghcr.io/haymayndzultra/ai_system/unified_observability_center:latest .
docker push ghcr.io/haymayndzultra/ai_system/unified_observability_center:latest
echo "✅ UnifiedObservabilityCenter pushed"

echo "Building SelfHealingSupervisor..."
docker build -f services/self_healing_supervisor/Dockerfile.optimized \
    --build-arg MACHINE=mainpc \
    -t ghcr.io/haymayndzultra/ai_system/self_healing_supervisor:latest .
docker push ghcr.io/haymayndzultra/ai_system/self_healing_supervisor:latest
echo "✅ SelfHealingSupervisor pushed"

echo "Building CentralErrorBus..."
docker build -f services/central_error_bus/Dockerfile.optimized \
    --build-arg MACHINE=pc2 \
    -t ghcr.io/haymayndzultra/ai_system/central_error_bus:latest .
docker push ghcr.io/haymayndzultra/ai_system/central_error_bus:latest
echo "✅ CentralErrorBus pushed"

echo "Building MemoryFusionHub..."
docker build -f memory_fusion_hub/Dockerfile.optimized \
    --build-arg MACHINE=mainpc \
    -t ghcr.io/haymayndzultra/ai_system/memory_fusion_hub:latest .
docker push ghcr.io/haymayndzultra/ai_system/memory_fusion_hub:latest
echo "✅ MemoryFusionHub pushed"

# Clean up to save space
docker system prune -a -f

echo "============================================================"
echo "✅ AGENT 3 COMPLETE! CPU services ready on GHCR"
echo "============================================================"