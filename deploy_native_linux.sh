#!/bin/bash
# Native Linux Deployment Script

set -e

echo "================================================"
echo "🐧 Native Linux Deployment"
echo "================================================"

export ORG='haymayndzultra'
export DATE=$(date -u +%Y%m%d)
export SHA=$(git rev-parse --short HEAD)
export TAG="${DATE}-${SHA}"

# Clean up old containers
echo "🧹 Cleaning up old containers..."
docker stop model_ops_coordinator real_time_audio_pipeline affective_processing_center unified_observability_center self_healing_supervisor central_error_bus 2>/dev/null || true
docker rm -f model_ops_coordinator real_time_audio_pipeline affective_processing_center unified_observability_center self_healing_supervisor central_error_bus 2>/dev/null || true

echo ""
echo "🚀 Starting services for native Linux..."

# ModelOpsCoordinator
echo "Starting ModelOpsCoordinator..."
docker run -d \
  --name model_ops_coordinator \
  --gpus all \
  --restart unless-stopped \
  --network host \
  -e MACHINE=mainpc \
  -e PYTHONPATH=/app:/workspace \
  -v "$(pwd):/workspace:ro" \
  -v /etc/machine-profile.json:/etc/machine-profile.json:ro \
  ghcr.io/$ORG/ai_system/model_ops_coordinator:$TAG

# RealTimeAudioPipeline (with audio device)
echo "Starting RealTimeAudioPipeline..."
docker run -d \
  --name real_time_audio_pipeline \
  --gpus all \
  --restart unless-stopped \
  --network host \
  -e MACHINE=mainpc \
  -e PYTHONPATH=/app:/workspace \
  -v "$(pwd):/workspace:ro" \
  -v /etc/machine-profile.json:/etc/machine-profile.json:ro \
  --device /dev/snd \
  ghcr.io/$ORG/ai_system/real_time_audio_pipeline:$TAG

# AffectiveProcessingCenter
echo "Starting AffectiveProcessingCenter..."
docker run -d \
  --name affective_processing_center \
  --gpus all \
  --restart unless-stopped \
  --network host \
  -e MACHINE=mainpc \
  -e PYTHONPATH=/app:/workspace \
  -v "$(pwd):/workspace:ro" \
  -v /etc/machine-profile.json:/etc/machine-profile.json:ro \
  ghcr.io/$ORG/ai_system/affective_processing_center:$TAG

# UnifiedObservabilityCenter
echo "Starting UnifiedObservabilityCenter..."
docker run -d \
  --name unified_observability_center \
  --restart unless-stopped \
  --network host \
  -e MACHINE=mainpc \
  -e PYTHONPATH=/app:/workspace \
  -v "$(pwd):/workspace:ro" \
  -v /etc/machine-profile.json:/etc/machine-profile.json:ro \
  ghcr.io/$ORG/ai_system/unified_observability_center:$TAG

# SelfHealingSupervisor (with docker socket)
echo "Starting SelfHealingSupervisor..."
docker run -d \
  --name self_healing_supervisor \
  --restart unless-stopped \
  --network host \
  -e MACHINE=mainpc \
  -e PYTHONPATH=/app:/workspace \
  -v "$(pwd):/workspace:ro" \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /etc/machine-profile.json:/etc/machine-profile.json:ro \
  ghcr.io/$ORG/ai_system/self_healing_supervisor:$TAG

# CentralErrorBus (for PC2, but can run on MainPC for testing)
echo "Starting CentralErrorBus..."
docker run -d \
  --name central_error_bus \
  --restart unless-stopped \
  --network host \
  -e MACHINE=pc2 \
  -e PYTHONPATH=/app:/workspace \
  -v "$(pwd):/workspace:ro" \
  -v /etc/machine-profile.json:/etc/machine-profile.json:ro \
  ghcr.io/$ORG/ai_system/central_error_bus:$TAG

echo ""
echo "⏳ Waiting 30 seconds for services to start..."
sleep 30

echo ""
echo "================================================"
echo "🏥 Health Check Results"
echo "================================================"

check_health() {
    local name=$1
    local port=$2
    printf "%-30s: " "$name"
    if curl -sf "http://localhost:$port/health" >/dev/null 2>&1; then
        echo "✅ OK"
    else
        echo "❌ FAIL"
    fi
}

check_health "ModelOpsCoordinator" 8212
check_health "RealTimeAudioPipeline" 6557
check_health "AffectiveProcessingCenter" 6560
check_health "UnifiedObservabilityCenter" 9110
check_health "SelfHealingSupervisor" 9008
check_health "CentralErrorBus" 8150

echo ""
echo "================================================"
echo "📊 Container Status"
echo "================================================"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(model_ops|real_time|affective|unified|self_healing|central_error)" || true

echo ""
echo "📝 Notes:"
echo "- Running with GPU support (--gpus all)"
echo "- Audio device mounted (/dev/snd)"
echo "- Docker socket mounted for SelfHealingSupervisor"
echo "- Using --network host for performance"
echo ""
echo "To check logs: docker logs <container_name>"