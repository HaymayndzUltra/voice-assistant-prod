#!/bin/bash
# Phase 4 Implementation per plan.md §H
# This script builds and pushes all Phase 4 services

set -euo pipefail

# Configuration per plan.md §B
ORG=haymayndzultra
REGISTRY=ghcr.io
DATE=$(date -u +%Y%m%d)
SHA=$(git rev-parse --short HEAD)
TAG="${DATE}-${SHA}"

echo "============================================"
echo "Phase 4 Docker Build per plan.md"
echo "============================================"
echo "Registry: ${REGISTRY}/${ORG}"
echo "Tag: ${TAG}"
echo ""

# Login to GHCR
echo "Authenticating to GHCR..."
echo "${GHCR_PAT}" | docker login ${REGISTRY} -u "${ORG}" --password-stdin

# Phase 4.2: MainPC GPU Services (per §F Fleet Coverage Table)
echo ""
echo "=== Phase 4.2: MainPC GPU Services ==="

# ModelOpsCoordinator - Port 7212/8212, family-llm-cu121
echo "Building ModelOpsCoordinator..."
docker build -f model_ops_coordinator/Dockerfile \
  --build-arg BASE_IMAGE=${REGISTRY}/${ORG}/family-llm-cu121:20250810-9c99cc9 \
  --build-arg MACHINE=mainpc \
  -t ${REGISTRY}/${ORG}/ai_system/model_ops_coordinator:${TAG} \
  model_ops_coordinator

# AffectiveProcessingCenter - Port 5560/6560, family-torch-cu121  
echo "Building AffectiveProcessingCenter..."
docker build -f affective_processing_center/Dockerfile \
  --build-arg BASE_IMAGE=${REGISTRY}/${ORG}/family-torch-cu121:20250810-9c99cc9 \
  --build-arg MACHINE=mainpc \
  -t ${REGISTRY}/${ORG}/ai_system/affective_processing_center:${TAG} \
  affective_processing_center

# RealTimeAudioPipeline - Port 5557/6557, family-torch-cu121
echo "Building RealTimeAudioPipeline..."
docker build -f real_time_audio_pipeline/Dockerfile \
  --build-arg BASE_IMAGE=${REGISTRY}/${ORG}/family-torch-cu121:20250810-9c99cc9 \
  --build-arg MACHINE=mainpc \
  -t ${REGISTRY}/${ORG}/ai_system/real_time_audio_pipeline:${TAG} \
  real_time_audio_pipeline

# Push all images
echo ""
echo "=== Pushing to GHCR ==="
docker push ${REGISTRY}/${ORG}/ai_system/model_ops_coordinator:${TAG}
docker push ${REGISTRY}/${ORG}/ai_system/affective_processing_center:${TAG}  
docker push ${REGISTRY}/${ORG}/ai_system/real_time_audio_pipeline:${TAG}

echo ""
echo "============================================"
echo "✅ Phase 4.2 Complete per plan.md!"
echo "============================================"
echo "Tagged images:"
echo "  - model_ops_coordinator:${TAG}"
echo "  - affective_processing_center:${TAG}"
echo "  - real_time_audio_pipeline:${TAG}"
echo ""
echo "Health check endpoints (per §F):"
echo "  curl http://localhost:8212/health  # ModelOpsCoordinator"
echo "  curl http://localhost:6560/health  # AffectiveProcessingCenter"
echo "  curl http://localhost:6557/health  # RealTimeAudioPipeline"