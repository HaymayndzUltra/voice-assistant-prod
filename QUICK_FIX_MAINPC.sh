#!/bin/bash
# QUICK FIX - Pull images if missing, then run properly

echo "================================================"
echo "🚀 QUICK FIX FOR MAINPC"
echo "================================================"

export ORG='haymayndzultra'
export TAG='20250812-576dfae'
export GHCR_PAT='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'

# Step 1: Login to GHCR
echo "🔐 Logging into GHCR..."
echo "$GHCR_PAT" | docker login ghcr.io -u "$ORG" --password-stdin

# Step 2: Stop broken containers
echo ""
echo "🛑 Cleaning up broken containers..."
docker stop model_ops_coordinator real_time_audio_pipeline affective_processing_center unified_observability_center self_healing_supervisor 2>/dev/null || true
docker rm -f model_ops_coordinator real_time_audio_pipeline affective_processing_center unified_observability_center self_healing_supervisor 2>/dev/null || true
sleep 3

# Step 3: Pull ALL images (in case they're missing)
echo ""
echo "📥 Pulling images from GHCR..."
echo "(This might take a few minutes if images are missing)"

pull_image() {
    local service=$1
    local image="ghcr.io/$ORG/ai_system/$service:$TAG"
    echo -n "  $service: "
    if docker pull "$image" 2>/dev/null; then
        echo "✅"
    else
        echo "❌ Failed - will try to rebuild"
        return 1
    fi
}

# Try to pull all images
NEED_REBUILD=0
pull_image "model_ops_coordinator" || NEED_REBUILD=1
pull_image "real_time_audio_pipeline" || NEED_REBUILD=1
pull_image "affective_processing_center" || NEED_REBUILD=1
pull_image "unified_observability_center" || NEED_REBUILD=1
pull_image "self_healing_supervisor" || NEED_REBUILD=1

# Step 4: If images are missing, we need to rebuild
if [ $NEED_REBUILD -eq 1 ]; then
    echo ""
    echo "⚠️  Some images are missing from GHCR!"
    echo ""
    echo "📦 You need to BUILD first. Run:"
    echo "   bash AUTOMATED_MAINPC_CRON.sh"
    echo ""
    echo "This will build and push all images (~20 minutes)"
    exit 1
fi

# Step 5: Create machine profile if missing
echo ""
echo "📋 Checking machine profile..."
if [ ! -f /etc/machine-profile.json ]; then
    echo "Creating /etc/machine-profile.json..."
    sudo tee /etc/machine-profile.json > /dev/null << 'EOF'
{
  "GPU_VISIBLE_DEVICES": "0",
  "TORCH_CUDA_ALLOC_CONF": "max_split_size_mb:64",
  "TORCH_CUDA_ARCH_LIST": "8.9",
  "OMP_NUM_THREADS": "16",
  "UVICORN_WORKERS": "32",
  "MODEL_EVICT_THRESHOLD_PCT": "90",
  "MAX_CONCURRENT_MODELS": "8",
  "BATCH_SIZE_DEFAULT": "32",
  "MEMORY_FRACTION": "0.95",
  "CUDA_MPS_ACTIVE_THREAD_PERCENTAGE": "100"
}
EOF
else
    echo "✅ Machine profile exists"
fi

# Step 6: Run containers PROPERLY
echo ""
echo "🚀 Starting services..."

# ModelOpsCoordinator
docker run -d \
  --name model_ops_coordinator \
  --gpus all \
  --restart unless-stopped \
  --network host \
  -e MACHINE=mainpc \
  -v /home/haymayndz/AI_System_Monorepo:/workspace:ro \
  -v /etc/machine-profile.json:/etc/machine-profile.json:ro \
  ghcr.io/$ORG/ai_system/model_ops_coordinator:$TAG

# RealTimeAudioPipeline
docker run -d \
  --name real_time_audio_pipeline \
  --gpus all \
  --restart unless-stopped \
  --network host \
  -e MACHINE=mainpc \
  -v /home/haymayndz/AI_System_Monorepo:/workspace:ro \
  -v /etc/machine-profile.json:/etc/machine-profile.json:ro \
  --device /dev/snd \
  ghcr.io/$ORG/ai_system/real_time_audio_pipeline:$TAG

# AffectiveProcessingCenter
docker run -d \
  --name affective_processing_center \
  --gpus all \
  --restart unless-stopped \
  --network host \
  -e MACHINE=mainpc \
  -v /home/haymayndz/AI_System_Monorepo:/workspace:ro \
  -v /etc/machine-profile.json:/etc/machine-profile.json:ro \
  ghcr.io/$ORG/ai_system/affective_processing_center:$TAG

# UnifiedObservabilityCenter
docker run -d \
  --name unified_observability_center \
  --restart unless-stopped \
  --network host \
  -e MACHINE=mainpc \
  -v /home/haymayndz/AI_System_Monorepo:/workspace:ro \
  -v /etc/machine-profile.json:/etc/machine-profile.json:ro \
  ghcr.io/$ORG/ai_system/unified_observability_center:$TAG

# SelfHealingSupervisor
docker run -d \
  --name self_healing_supervisor \
  --restart unless-stopped \
  --network host \
  -e MACHINE=mainpc \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /etc/machine-profile.json:/etc/machine-profile.json:ro \
  ghcr.io/$ORG/ai_system/self_healing_supervisor:$TAG

echo "✅ All containers started"

# Step 7: Wait and check
echo ""
echo "⏳ Waiting 30 seconds for initialization..."
sleep 30

# Step 8: Final status
echo ""
echo "================================================"
echo "📊 FINAL STATUS"
echo "================================================"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(model_ops|real_time|affective|unified|self_healing)" || true

echo ""
echo "🏥 Health Checks:"
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
echo "✅ Done! Check the health status above."
echo ""
echo "If services are failing, check logs:"
echo "  docker logs <service_name>"
echo "================================================"