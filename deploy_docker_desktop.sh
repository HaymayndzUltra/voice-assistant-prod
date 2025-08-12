#!/bin/bash
# Docker Desktop Compatible Deployment Script

set -e

echo "================================================"
echo "🐳 Docker Desktop Deployment (Fixed)"
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
echo "🚀 Starting services with Docker Desktop compatibility..."

# ModelOpsCoordinator
echo "Starting ModelOpsCoordinator..."
docker run -d \
  --name model_ops_coordinator \
  --restart unless-stopped \
  -p 7212:7212 \
  -p 8212:8212 \
  -e MACHINE=mainpc \
  -e PYTHONPATH=/app:/workspace \
  -e CUDA_VISIBLE_DEVICES=-1 \
  -v "$(pwd):/workspace:ro" \
  ghcr.io/$ORG/ai_system/model_ops_coordinator:$TAG

# RealTimeAudioPipeline (no audio device)
echo "Starting RealTimeAudioPipeline..."
docker run -d \
  --name real_time_audio_pipeline \
  --restart unless-stopped \
  -p 5557:5557 \
  -p 6557:6557 \
  -e MACHINE=mainpc \
  -e PYTHONPATH=/app:/workspace \
  -e AUDIO_BACKEND=dummy \
  -e CUDA_VISIBLE_DEVICES=-1 \
  -v "$(pwd):/workspace:ro" \
  ghcr.io/$ORG/ai_system/real_time_audio_pipeline:$TAG

# AffectiveProcessingCenter
echo "Starting AffectiveProcessingCenter..."
docker run -d \
  --name affective_processing_center \
  --restart unless-stopped \
  -p 5560:5560 \
  -p 6560:6560 \
  -e MACHINE=mainpc \
  -e PYTHONPATH=/app:/workspace \
  -e CUDA_VISIBLE_DEVICES=-1 \
  -v "$(pwd):/workspace:ro" \
  ghcr.io/$ORG/ai_system/affective_processing_center:$TAG

# UnifiedObservabilityCenter
echo "Starting UnifiedObservabilityCenter..."
docker run -d \
  --name unified_observability_center \
  --restart unless-stopped \
  -p 9100:9100 \
  -p 9110:9110 \
  -e MACHINE=mainpc \
  -e PYTHONPATH=/app:/workspace \
  -v "$(pwd):/workspace:ro" \
  ghcr.io/$ORG/ai_system/unified_observability_center:$TAG

# SelfHealingSupervisor (Docker Desktop compatible)
echo "Starting SelfHealingSupervisor (Docker Desktop mode)..."
docker run -d \
  --name self_healing_supervisor \
  --restart unless-stopped \
  -p 7009:7009 \
  -p 9008:9008 \
  -e MACHINE=mainpc \
  -e PYTHONPATH=/app:/workspace \
  -e DOCKER_HOST=tcp://host.docker.internal:2375 \
  -v "$(pwd):/workspace:ro" \
  ghcr.io/$ORG/ai_system/self_healing_supervisor:$TAG

# CentralErrorBus
echo "Starting CentralErrorBus..."
docker run -d \
  --name central_error_bus \
  --restart unless-stopped \
  -p 7150:7150 \
  -p 8150:8150 \
  -e MACHINE=pc2 \
  -e PYTHONPATH=/app:/workspace \
  -v "$(pwd):/workspace:ro" \
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
echo "- Running in CPU mode (no GPU)"
echo "- Audio using dummy backend"
echo "- Docker socket via TCP (requires Docker Desktop setting)"
echo "- To enable Docker socket for SelfHealingSupervisor:"
echo "  Settings → General → Expose daemon on tcp://localhost:2375"
echo ""
echo "To check logs: docker logs <container_name>"