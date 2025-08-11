#!/bin/bash
# MAINPC DEPLOYMENT SCRIPT - Phase 4
# Run this directly on MainPC

set -e  # Exit on error

echo "================================================"
echo "Phase 4 Docker Deployment - Starting"
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
echo ""

# Step 4: Login to GHCR
echo "🔐 Logging into GHCR..."
echo "$GHCR_PAT" | docker login ghcr.io -u "$ORG" --password-stdin

# Step 5: Build base/family images first
echo ""
echo "🔨 Building base and family images..."
if [ -f scripts/build_families.sh ]; then
    bash scripts/build_families.sh
else
    echo "⚠️  No family build script, skipping..."
fi

# Step 6: Build Phase 4 services
echo ""
echo "🚀 Building Phase 4 services..."

# ModelOpsCoordinator
echo "Building ModelOpsCoordinator..."
docker build -f model_ops_coordinator/Dockerfile \
  --build-arg BASE_IMAGE=ghcr.io/$ORG/family-llm-cu121:20250810-9c99cc9 \
  --build-arg MACHINE=mainpc \
  -t ghcr.io/$ORG/ai_system/model_ops_coordinator:$TAG \
  model_ops_coordinator

# RealTimeAudioPipeline
echo "Building RealTimeAudioPipeline..."
docker build -f real_time_audio_pipeline/Dockerfile \
  --build-arg BASE_IMAGE=ghcr.io/$ORG/family-torch-cu121:20250810-9c99cc9 \
  --build-arg MACHINE=mainpc \
  -t ghcr.io/$ORG/ai_system/real_time_audio_pipeline:$TAG \
  real_time_audio_pipeline

# AffectiveProcessingCenter
echo "Building AffectiveProcessingCenter..."
docker build -f affective_processing_center/Dockerfile \
  --build-arg BASE_IMAGE=ghcr.io/$ORG/family-torch-cu121:20250810-9c99cc9 \
  --build-arg MACHINE=mainpc \
  -t ghcr.io/$ORG/ai_system/affective_processing_center:$TAG \
  affective_processing_center

# SelfHealingSupervisor
echo "Building SelfHealingSupervisor..."
docker build -f services/self_healing_supervisor/Dockerfile \
  --build-arg BASE_IMAGE=ghcr.io/$ORG/base-cpu-pydeps:20250810-9c99cc9 \
  --build-arg MACHINE=mainpc \
  -t ghcr.io/$ORG/ai_system/self_healing_supervisor:$TAG \
  services/self_healing_supervisor

# CentralErrorBus
echo "Building CentralErrorBus..."
docker build -f services/central_error_bus/Dockerfile \
  --build-arg BASE_IMAGE=ghcr.io/$ORG/family-web:20250810-9c99cc9 \
  --build-arg MACHINE=pc2 \
  -t ghcr.io/$ORG/ai_system/central_error_bus:$TAG \
  services/central_error_bus

# UnifiedObservabilityCenter
echo "Building UnifiedObservabilityCenter..."
docker build -f unified_observability_center/Dockerfile \
  --build-arg BASE_IMAGE=ghcr.io/$ORG/family-web:20250810-9c99cc9 \
  --build-arg MACHINE=mainpc \
  -t ghcr.io/$ORG/ai_system/unified_observability_center:$TAG \
  unified_observability_center

# Step 7: Push all images
echo ""
echo "📤 Pushing images to GHCR..."
docker push ghcr.io/$ORG/ai_system/model_ops_coordinator:$TAG
docker push ghcr.io/$ORG/ai_system/real_time_audio_pipeline:$TAG
docker push ghcr.io/$ORG/ai_system/affective_processing_center:$TAG
docker push ghcr.io/$ORG/ai_system/self_healing_supervisor:$TAG
docker push ghcr.io/$ORG/ai_system/central_error_bus:$TAG
docker push ghcr.io/$ORG/ai_system/unified_observability_center:$TAG

# Step 8: Verify with sync_inventory
echo ""
echo "🔍 Verifying registry sync..."
export GH_USERNAME=$ORG
export GH_TOKEN=$GHCR_PAT
python3 scripts/sync_inventory.py --dry-run

# Step 9: Deploy locally
echo ""
echo "🚀 Deploying services..."
export FORCE_IMAGE_TAG=$TAG
sudo systemctl reload supervisor

# Step 10: Wait for services
echo ""
echo "⏳ Waiting 60 seconds for services to start..."
sleep 60

# Step 11: Health checks
echo ""
echo "================================================"
echo "🏥 HEALTH CHECK RESULTS"
echo "================================================"
echo ""

echo -n "ModelOpsCoordinator (8212): "
curl -sf http://localhost:8212/health && echo " ✅" || echo " ❌"

echo -n "RealTimeAudioPipeline (6557): "
curl -sf http://localhost:6557/health && echo " ✅" || echo " ❌"

echo -n "AffectiveProcessingCenter (6560): "
curl -sf http://localhost:6560/health && echo " ✅" || echo " ❌"

echo -n "UnifiedObservabilityCenter (9110): "
curl -sf http://localhost:9110/health && echo " ✅" || echo " ❌"

echo -n "CentralErrorBus (8150): "
curl -sf http://localhost:8150/health && echo " ✅" || echo " ❌"

echo -n "SelfHealingSupervisor (9008): "
curl -sf http://localhost:9008/health && echo " ✅" || echo " ❌"

echo ""
echo "================================================"
echo "✅ Deployment Complete!"
echo "================================================"
echo "TAG used: $TAG"
echo ""
echo "If any health checks failed, check:"
echo "  sudo journalctl -u supervisor -n 50"
echo "  docker logs <container_name>"
echo ""
echo "To rollback:"
echo "  export FORCE_IMAGE_TAG=20250810-9c99cc9"
echo "  sudo systemctl reload supervisor"