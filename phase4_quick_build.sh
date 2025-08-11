#!/bin/bash
# Phase 4 Quick Build Script - Run on MainPC
# Simple, direct commands for immediate execution

# Go to your repo
cd /home/haymayndz/AI_System_Monorepo

# Set variables
export ORG=haymayndzultra
export TAG=20250111-$(git rev-parse --short HEAD)
export BASE_TAG=20250810-9c99cc9  # Existing family images

# Login to GHCR (if not already)
echo "$GHCR_PAT" | docker login ghcr.io -u "$ORG" --password-stdin

# Build the 3 optimized services
echo "Building ModelOpsCoordinator..."
docker buildx build -f model_ops_coordinator/Dockerfile \
  --build-arg BASE_IMAGE=ghcr.io/$ORG/family-llm-cu121:$BASE_TAG \
  --build-arg MACHINE=mainpc \
  -t ghcr.io/$ORG/ai_system/model_ops_coordinator:$TAG \
  --push model_ops_coordinator

echo "Building RealTimeAudioPipeline..."
docker buildx build -f real_time_audio_pipeline/Dockerfile \
  --build-arg BASE_IMAGE=ghcr.io/$ORG/family-torch-cu121:$BASE_TAG \
  --build-arg MACHINE=mainpc \
  -t ghcr.io/$ORG/ai_system/real_time_audio_pipeline:$TAG \
  --push real_time_audio_pipeline

echo "Building AffectiveProcessingCenter..."
docker buildx build -f affective_processing_center/Dockerfile \
  --build-arg BASE_IMAGE=ghcr.io/$ORG/family-torch-cu121:$BASE_TAG \
  --build-arg MACHINE=mainpc \
  -t ghcr.io/$ORG/ai_system/affective_processing_center:$TAG \
  --push affective_processing_center

# Test deployment
echo "Starting services with new images..."
export FORCE_IMAGE_TAG=$TAG
docker compose up -d model_ops_coordinator real_time_audio_pipeline affective_processing_center

# Wait and check health
sleep 30
echo "Health checks:"
curl -s http://localhost:8212/health | jq .
curl -s http://localhost:6557/health | jq .
curl -s http://localhost:6560/health | jq .

echo "Done! If all health checks show {\"status\":\"ok\"}, Phase 4 is complete!"