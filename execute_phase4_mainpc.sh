#!/bin/bash
# Phase 4 Execution Script for MainPC
# Run this directly on MainPC host (not in container)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "Phase 4 Docker Implementation - MainPC Execution"
echo "==========================================${NC}"

# Step 1: Environment Setup
echo -e "\n${YELLOW}Step 1: Setting up environment...${NC}"
export ORG=haymayndzultra
export DATE=$(date -u +%Y%m%d)
export SHA=$(cd /home/haymayndz/AI_System_Monorepo && git rev-parse --short HEAD)
export TAG=${DATE}-${SHA}
export FORCE_IMAGE_TAG=${TAG}

echo "Organization: $ORG"
echo "Tag: $TAG"
echo "Repository: /home/haymayndz/AI_System_Monorepo"

# Step 2: Navigate to repository
echo -e "\n${YELLOW}Step 2: Navigating to repository...${NC}"
cd /home/haymayndz/AI_System_Monorepo

# Step 3: Docker Authentication
echo -e "\n${YELLOW}Step 3: Authenticating with GHCR...${NC}"
if [ -z "${GHCR_PAT:-}" ]; then
    echo -e "${RED}Error: GHCR_PAT environment variable not set${NC}"
    echo "Please run: export GHCR_PAT=your_github_token"
    exit 1
fi
echo "$GHCR_PAT" | docker login ghcr.io -u "$ORG" --password-stdin

# Step 4: Build Base Family Images (if not exists)
echo -e "\n${YELLOW}Step 4: Checking family images...${NC}"
if ! docker manifest inspect ghcr.io/$ORG/family-llm-cu121:20250810-9c99cc9 >/dev/null 2>&1; then
    echo -e "${RED}Family images not found. Please build them first.${NC}"
    echo "Refer to Phase 1-3 documentation"
else
    echo -e "${GREEN}✓ Family images available${NC}"
fi

# Step 5: Build Optimized Service Images
echo -e "\n${YELLOW}Step 5: Building optimized service images...${NC}"

# ModelOpsCoordinator
echo "Building ModelOpsCoordinator..."
docker buildx build -f model_ops_coordinator/Dockerfile \
  --platform=linux/amd64 \
  --build-arg BASE_IMAGE=ghcr.io/$ORG/family-llm-cu121:20250810-9c99cc9 \
  --build-arg MACHINE=mainpc \
  -t ghcr.io/$ORG/ai_system/model_ops_coordinator:$TAG \
  --push model_ops_coordinator

# RealTimeAudioPipeline
echo "Building RealTimeAudioPipeline..."
docker buildx build -f real_time_audio_pipeline/Dockerfile \
  --platform=linux/amd64 \
  --build-arg BASE_IMAGE=ghcr.io/$ORG/family-torch-cu121:20250810-9c99cc9 \
  --build-arg MACHINE=mainpc \
  -t ghcr.io/$ORG/ai_system/real_time_audio_pipeline:$TAG \
  --push real_time_audio_pipeline

# AffectiveProcessingCenter
echo "Building AffectiveProcessingCenter..."
docker buildx build -f affective_processing_center/Dockerfile \
  --platform=linux/amd64 \
  --build-arg BASE_IMAGE=ghcr.io/$ORG/family-torch-cu121:20250810-9c99cc9 \
  --build-arg MACHINE=mainpc \
  -t ghcr.io/$ORG/ai_system/affective_processing_center:$TAG \
  --push affective_processing_center

# Step 6: Verify Images
echo -e "\n${YELLOW}Step 6: Verifying pushed images...${NC}"
./verify_ghcr_images.sh || true

# Step 7: Canary Deployment
echo -e "\n${YELLOW}Step 7: Starting canary deployment...${NC}"
echo "Using FORCE_IMAGE_TAG=$FORCE_IMAGE_TAG"

# Update docker-compose with new tag
export FORCE_IMAGE_TAG
docker compose pull model_ops_coordinator real_time_audio_pipeline affective_processing_center
docker compose up -d model_ops_coordinator real_time_audio_pipeline affective_processing_center

# Wait for services to start
echo "Waiting 30 seconds for services to initialize..."
sleep 30

# Step 8: Health Checks
echo -e "\n${YELLOW}Step 8: Performing health checks...${NC}"

check_health() {
    local service=$1
    local port=$2
    local url="http://localhost:$port/health"
    
    echo -n "Checking $service at port $port... "
    if curl -fsS "$url" | grep -q '"status":"ok"'; then
        echo -e "${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Unhealthy${NC}"
        return 1
    fi
}

HEALTH_PASS=0
check_health "ModelOpsCoordinator" 8212 && ((HEALTH_PASS++)) || true
check_health "RealTimeAudioPipeline" 6557 && ((HEALTH_PASS++)) || true
check_health "AffectiveProcessingCenter" 6560 && ((HEALTH_PASS++)) || true

# Step 9: Show Logs Summary
echo -e "\n${YELLOW}Step 9: Recent logs summary...${NC}"
docker compose logs --tail=20 --no-color model_ops_coordinator | grep -E "ERROR|WARNING|INFO.*started" || true

# Step 10: Final Status
echo -e "\n${BLUE}=========================================="
echo "Phase 4 Canary Deployment Status"
echo "==========================================${NC}"

if [ $HEALTH_PASS -eq 3 ]; then
    echo -e "${GREEN}✓ All services healthy!${NC}"
    echo -e "\n${YELLOW}Next Steps:${NC}"
    echo "1. Monitor services for 30 minutes"
    echo "2. Check logs: docker compose logs -f"
    echo "3. If stable, run batch rollout:"
    echo "   docker compose up -d"
    echo "4. Mark Phase 4 complete:"
    echo "   python3 todo_manager.py done docker_arch_impl_20250810 4"
else
    echo -e "${RED}⚠ Some services unhealthy${NC}"
    echo "Check logs: docker compose logs --tail=100"
    echo "Debug: docker ps -a"
fi

echo -e "\n${GREEN}Script completed!${NC}"