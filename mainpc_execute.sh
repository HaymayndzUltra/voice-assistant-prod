#!/bin/bash
# SIMPLE PHASE 4 EXECUTION FOR MAINPC LOCAL
# Run this on your MainPC, NOT in container

echo "==================================="
echo "Phase 4 Docker Build - MainPC Local"
echo "==================================="

# 1. Go to your repo
cd /home/haymayndz/AI_System_Monorepo || exit 1

# 2. Get latest changes from this session
git pull origin main

# 3. Set variables
export ORG=haymayndzultra
export GHCR_PAT=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
export TAG=20250111-$(git rev-parse --short HEAD)
export BASE_TAG=20250810-9c99cc9

echo "Using tag: $TAG"

# 4. Login to GHCR
echo "$GHCR_PAT" | docker login ghcr.io -u "$ORG" --password-stdin

# 5. Build the 3 optimized services
echo ""
echo "Building Model Ops Coordinator..."
docker build -f model_ops_coordinator/Dockerfile \
  --build-arg BASE_IMAGE=ghcr.io/$ORG/family-llm-cu121:$BASE_TAG \
  --build-arg MACHINE=mainpc \
  -t ghcr.io/$ORG/ai_system/model_ops_coordinator:$TAG \
  model_ops_coordinator

echo ""
echo "Building Real Time Audio Pipeline..."
docker build -f real_time_audio_pipeline/Dockerfile \
  --build-arg BASE_IMAGE=ghcr.io/$ORG/family-torch-cu121:$BASE_TAG \
  --build-arg MACHINE=mainpc \
  -t ghcr.io/$ORG/ai_system/real_time_audio_pipeline:$TAG \
  real_time_audio_pipeline

echo ""
echo "Building Affective Processing Center..."
docker build -f affective_processing_center/Dockerfile \
  --build-arg BASE_IMAGE=ghcr.io/$ORG/family-torch-cu121:$BASE_TAG \
  --build-arg MACHINE=mainpc \
  -t ghcr.io/$ORG/ai_system/affective_processing_center:$TAG \
  affective_processing_center

# 6. Push to GHCR
echo ""
echo "Pushing images to GHCR..."
docker push ghcr.io/$ORG/ai_system/model_ops_coordinator:$TAG
docker push ghcr.io/$ORG/ai_system/real_time_audio_pipeline:$TAG
docker push ghcr.io/$ORG/ai_system/affective_processing_center:$TAG

# 7. Verify
echo ""
echo "==================================="
echo "✅ Phase 4 Build Complete!"
echo "==================================="
echo "Images pushed:"
echo "  - model_ops_coordinator:$TAG"
echo "  - real_time_audio_pipeline:$TAG"
echo "  - affective_processing_center:$TAG"
echo ""
echo "Test health endpoints:"
echo "  curl http://localhost:8001/health"
echo "  curl http://localhost:8002/health"
echo "  curl http://localhost:8003/health"