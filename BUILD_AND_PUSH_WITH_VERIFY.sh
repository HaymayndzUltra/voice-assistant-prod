#!/bin/bash
# Phase 4 Implementation with Verification per plan.md §H
# Enhanced with sync_inventory.py verification

set -euo pipefail

# Configuration per plan.md §B
ORG=haymayndzultra
REGISTRY=ghcr.io
DATE=$(date -u +%Y%m%d)
SHA=$(git rev-parse --short HEAD)
TAG="${DATE}-${SHA}"
GHCR_PAT="${GHCR_PAT:-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}"

echo "============================================"
echo "Phase 4 Docker Build with Verification"
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

# Build services
echo "Building ModelOpsCoordinator (7212/8212)..."
docker build -f model_ops_coordinator/Dockerfile \
  --build-arg BASE_IMAGE=${REGISTRY}/${ORG}/family-llm-cu121:20250810-9c99cc9 \
  --build-arg MACHINE=mainpc \
  -t ${REGISTRY}/${ORG}/ai_system/model_ops_coordinator:${TAG} \
  model_ops_coordinator

echo "Building AffectiveProcessingCenter (5560/6560)..."
docker build -f affective_processing_center/Dockerfile \
  --build-arg BASE_IMAGE=${REGISTRY}/${ORG}/family-torch-cu121:20250810-9c99cc9 \
  --build-arg MACHINE=mainpc \
  -t ${REGISTRY}/${ORG}/ai_system/affective_processing_center:${TAG} \
  affective_processing_center

echo "Building RealTimeAudioPipeline (5557/6557)..."
docker build -f real_time_audio_pipeline/Dockerfile \
  --build-arg BASE_IMAGE=${REGISTRY}/${ORG}/family-torch-cu121:20250810-9c99cc9 \
  --build-arg MACHINE=mainpc \
  -t ${REGISTRY}/${ORG}/ai_system/real_time_audio_pipeline:${TAG} \
  real_time_audio_pipeline

# Verify local images before push
echo ""
echo "=== Verifying Local Images ==="
export GH_USERNAME=${ORG}
export GH_TOKEN=${GHCR_PAT}
python3 scripts/sync_inventory.py --dry-run

# Push all images
echo ""
echo "=== Pushing to GHCR ==="
docker push ${REGISTRY}/${ORG}/ai_system/model_ops_coordinator:${TAG}
docker push ${REGISTRY}/${ORG}/ai_system/affective_processing_center:${TAG}  
docker push ${REGISTRY}/${ORG}/ai_system/real_time_audio_pipeline:${TAG}

# Verify remote images after push
echo ""
echo "=== Verifying Remote Images ==="
python3 scripts/sync_inventory.py --dry-run

echo ""
echo "============================================"
echo "✅ Phase 4.2 Complete with Verification!"
echo "============================================"
echo "Tagged images:"
echo "  - model_ops_coordinator:${TAG}"
echo "  - affective_processing_center:${TAG}"
echo "  - real_time_audio_pipeline:${TAG}"
echo ""
echo "Port mappings per plan.md:"
echo "  ModelOpsCoordinator: 7212 (service) / 8212 (health)"
echo "  AffectiveProcessingCenter: 5560 (service) / 6560 (health)"
echo "  RealTimeAudioPipeline: 5557 (service) / 6557 (health)"
echo ""
echo "Test health endpoints:"
echo "  curl http://localhost:8212/health  # Returns {\"status\": \"ok\"}"
echo "  curl http://localhost:6560/health  # Returns {\"status\": \"ok\"}"
echo "  curl http://localhost:6557/health  # Returns {\"status\": \"ok\"}"