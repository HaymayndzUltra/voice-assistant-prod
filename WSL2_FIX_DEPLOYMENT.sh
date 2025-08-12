#!/bin/bash
# WSL2 FIX - Run without /dev/snd audio device

echo "================================================"
echo "🔧 WSL2 DEPLOYMENT FIX (No Audio Device)"
echo "================================================"

export ORG='haymayndzultra'
export TAG='20250812-576dfae'

# Step 1: Clean up
echo "🛑 Stopping all containers..."
docker stop model_ops_coordinator real_time_audio_pipeline affective_processing_center unified_observability_center self_healing_supervisor 2>/dev/null || true
docker rm -f model_ops_coordinator real_time_audio_pipeline affective_processing_center unified_observability_center self_healing_supervisor 2>/dev/null || true
sleep 3

# Step 2: Start containers WITHOUT audio device
echo ""
echo "🚀 Starting services (WSL2 compatible)..."

# ModelOpsCoordinator
echo "Starting ModelOpsCoordinator..."
docker run -d \
  --name model_ops_coordinator \
  --gpus all \
  --restart unless-stopped \
  --network host \
  -e MACHINE=mainpc \
  -v /home/haymayndz/AI_System_Monorepo:/workspace:ro \
  ghcr.io/$ORG/ai_system/model_ops_coordinator:$TAG

# RealTimeAudioPipeline (WITHOUT /dev/snd)
echo "Starting RealTimeAudioPipeline (no audio device)..."
docker run -d \
  --name real_time_audio_pipeline \
  --gpus all \
  --restart unless-stopped \
  --network host \
  -e MACHINE=mainpc \
  -e AUDIO_BACKEND=dummy \
  -v /home/haymayndz/AI_System_Monorepo:/workspace:ro \
  ghcr.io/$ORG/ai_system/real_time_audio_pipeline:$TAG
# Note: Using dummy audio backend for WSL2

# AffectiveProcessingCenter
echo "Starting AffectiveProcessingCenter..."
docker run -d \
  --name affective_processing_center \
  --gpus all \
  --restart unless-stopped \
  --network host \
  -e MACHINE=mainpc \
  -v /home/haymayndz/AI_System_Monorepo:/workspace:ro \
  ghcr.io/$ORG/ai_system/affective_processing_center:$TAG

# UnifiedObservabilityCenter
echo "Starting UnifiedObservabilityCenter..."
docker run -d \
  --name unified_observability_center \
  --restart unless-stopped \
  --network host \
  -e MACHINE=mainpc \
  -v /home/haymayndz/AI_System_Monorepo:/workspace:ro \
  ghcr.io/$ORG/ai_system/unified_observability_center:$TAG

# SelfHealingSupervisor
echo "Starting SelfHealingSupervisor..."
docker run -d \
  --name self_healing_supervisor \
  --restart unless-stopped \
  --network host \
  -e MACHINE=mainpc \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  ghcr.io/$ORG/ai_system/self_healing_supervisor:$TAG

echo "✅ All containers started"

# Step 3: Quick status check
echo ""
echo "⏳ Waiting 10 seconds..."
sleep 10

echo ""
echo "📊 Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(model_ops|real_time|affective|unified|self_healing)" || true

# Step 4: Check logs for actual errors
echo ""
echo "🔍 Checking for startup errors..."
echo ""

for service in model_ops_coordinator real_time_audio_pipeline affective_processing_center unified_observability_center self_healing_supervisor; do
    echo "--- $service ---"
    if docker ps --filter "name=$service" --filter "status=running" | grep -q $service; then
        echo "✅ Running"
    else
        echo "❌ Failed - Last error:"
        docker logs --tail 3 $service 2>&1 | sed 's/^/  /'
    fi
    echo ""
done

echo "================================================"
echo ""
echo "If containers are still failing, run:"
echo "  bash DIAGNOSE_STARTUP_ISSUE.sh"
echo ""
echo "This will show you exactly what's wrong inside the images."
echo "================================================"