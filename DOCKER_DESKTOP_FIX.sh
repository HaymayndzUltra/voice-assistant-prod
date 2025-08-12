#!/bin/bash
# DOCKER DESKTOP FIX - Windows-specific deployment

echo "================================================"
echo "🪟 DOCKER DESKTOP (Windows) DEPLOYMENT"
echo "================================================"

export ORG='haymayndzultra'
export TAG='20250812-576dfae'

# Step 1: Clean up
echo "🛑 Cleaning up old containers..."
docker stop model_ops_coordinator real_time_audio_pipeline affective_processing_center unified_observability_center self_healing_supervisor 2>/dev/null || true
docker rm -f model_ops_coordinator real_time_audio_pipeline affective_processing_center unified_observability_center self_healing_supervisor 2>/dev/null || true
sleep 3

# Step 2: Check Docker Desktop settings
echo ""
echo "📋 Docker Desktop Check:"
echo "Docker version: $(docker --version)"
echo "Docker context: $(docker context show)"
echo ""

# Step 3: Start containers with Docker Desktop compatibility
echo "🚀 Starting services (Docker Desktop mode)..."

# ModelOpsCoordinator - No GPU for now (test first)
echo "Starting ModelOpsCoordinator (CPU mode for testing)..."
docker run -d \
  --name model_ops_coordinator \
  --restart unless-stopped \
  -p 7212:7212 \
  -p 8212:8212 \
  -e MACHINE=mainpc \
  -e CUDA_VISIBLE_DEVICES=-1 \
  -v "$(pwd):/workspace:ro" \
  ghcr.io/$ORG/ai_system/model_ops_coordinator:$TAG

# RealTimeAudioPipeline - No audio device, no GPU
echo "Starting RealTimeAudioPipeline (no audio/GPU)..."
docker run -d \
  --name real_time_audio_pipeline \
  --restart unless-stopped \
  -p 5557:5557 \
  -p 6557:6557 \
  -e MACHINE=mainpc \
  -e AUDIO_BACKEND=dummy \
  -e CUDA_VISIBLE_DEVICES=-1 \
  -v "$(pwd):/workspace:ro" \
  ghcr.io/$ORG/ai_system/real_time_audio_pipeline:$TAG

# AffectiveProcessingCenter - CPU mode
echo "Starting AffectiveProcessingCenter (CPU mode)..."
docker run -d \
  --name affective_processing_center \
  --restart unless-stopped \
  -p 5560:5560 \
  -p 6560:6560 \
  -e MACHINE=mainpc \
  -e CUDA_VISIBLE_DEVICES=-1 \
  -v "$(pwd):/workspace:ro" \
  ghcr.io/$ORG/ai_system/affective_processing_center:$TAG

# UnifiedObservabilityCenter - CPU only service
echo "Starting UnifiedObservabilityCenter..."
docker run -d \
  --name unified_observability_center \
  --restart unless-stopped \
  -p 9100:9100 \
  -p 9110:9110 \
  -e MACHINE=mainpc \
  -v "$(pwd):/workspace:ro" \
  ghcr.io/$ORG/ai_system/unified_observability_center:$TAG

# SelfHealingSupervisor - Need to map docker.sock differently
echo "Starting SelfHealingSupervisor..."
docker run -d \
  --name self_healing_supervisor \
  --restart unless-stopped \
  -p 7009:7009 \
  -p 9008:9008 \
  -e MACHINE=mainpc \
  -v //var/run/docker.sock:/var/run/docker.sock:ro \
  ghcr.io/$ORG/ai_system/self_healing_supervisor:$TAG

echo "✅ All containers started (CPU mode)"

# Step 4: Wait and check
echo ""
echo "⏳ Waiting 15 seconds for initialization..."
sleep 15

# Step 5: Status check
echo ""
echo "📊 Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -1
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(model_ops|real_time|affective|unified|self_healing)" || true

# Step 6: Health checks using localhost
echo ""
echo "🏥 Health Checks (via localhost):"
for port in 8212 6557 6560 9110 9008; do
    printf "Port %s: " "$port"
    if curl -sf "http://localhost:$port/health" >/dev/null 2>&1; then
        echo "✅ OK"
    else
        echo "❌ FAIL"
    fi
done

echo ""
echo "================================================"
echo "📝 Docker Desktop Notes:"
echo "================================================"
echo ""
echo "1. Running in CPU mode (no GPU) for stability"
echo "2. Using port mapping instead of --network host"
echo "3. Audio disabled (use dummy backend)"
echo "4. Volumes use Windows paths internally"
echo ""
echo "To enable GPU (experimental):"
echo "  - Settings → Resources → WSL Integration → Enable"
echo "  - Then use '--gpus all' in docker run"
echo ""
echo "If containers are failing, check:"
echo "  docker logs <container_name>"
echo "================================================"