#!/bin/bash
# Script to verify GHCR image presence and pullability
# Per Phase 4 requirements of Docker Architecture Implementation

set -euo pipefail

# Configuration
ORG="${ORG:-haymayndzultra}"
REGISTRY="ghcr.io"
DATE=$(date -u +%Y%m%d)
SHA="${GIT_SHA:-656873b3}"
TAG="${DATE}-${SHA}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "GHCR Image Verification for Phase 4"
echo "=========================================="
echo "Registry: ${REGISTRY}/${ORG}"
echo "Tag: ${TAG}"
echo ""

# Family base images to verify
FAMILY_IMAGES=(
    "base-python:3.11-slim"
    "base-utils"
    "base-cpu-pydeps"
    "family-web"
    "base-gpu-cu121"
    "family-torch-cu121"
    "family-llm-cu121"
    "family-vision-cu121"
    "legacy-py310-cpu"
)

# Service images to verify
SERVICE_IMAGES=(
    "ai_system/model_ops_coordinator"
    "ai_system/real_time_audio_pipeline"
    "ai_system/affective_processing_center"
    "ai_system/service_registry"
    "ai_system/system_digital_twin"
    "ai_system/unified_system_agent"
)

# Function to check if image exists
check_image() {
    local image="$1"
    local full_image="${REGISTRY}/${ORG}/${image}"
    
    echo -n "Checking ${image}... "
    
    # Try to inspect the image manifest
    if docker manifest inspect "${full_image}" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Available${NC}"
        return 0
    else
        echo -e "${RED}✗ Not found${NC}"
        return 1
    fi
}

# Verify authentication
echo "Verifying GHCR authentication..."
if docker pull "${REGISTRY}/${ORG}/hello-world:latest" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Authenticated to GHCR${NC}"
else
    echo -e "${YELLOW}⚠ Warning: Unable to authenticate to GHCR${NC}"
    echo "Please run: echo \$GHCR_PAT | docker login ghcr.io -u ${ORG} --password-stdin"
fi
echo ""

# Check family base images
echo "Family Base Images:"
echo "-------------------"
FAMILY_SUCCESS=0
FAMILY_TOTAL=0
for image in "${FAMILY_IMAGES[@]}"; do
    FAMILY_TOTAL=$((FAMILY_TOTAL + 1))
    if check_image "${image}:${TAG}"; then
        FAMILY_SUCCESS=$((FAMILY_SUCCESS + 1))
    fi
done
echo ""

# Check service images
echo "Service Images:"
echo "---------------"
SERVICE_SUCCESS=0
SERVICE_TOTAL=0
for image in "${SERVICE_IMAGES[@]}"; do
    SERVICE_TOTAL=$((SERVICE_TOTAL + 1))
    if check_image "${image}:${TAG}"; then
        SERVICE_SUCCESS=$((SERVICE_SUCCESS + 1))
    fi
done
echo ""

# Summary
echo "=========================================="
echo "Summary:"
echo "Family Images: ${FAMILY_SUCCESS}/${FAMILY_TOTAL} available"
echo "Service Images: ${SERVICE_SUCCESS}/${SERVICE_TOTAL} available"

if [ $FAMILY_SUCCESS -eq $FAMILY_TOTAL ] && [ $SERVICE_SUCCESS -eq $SERVICE_TOTAL ]; then
    echo -e "${GREEN}✓ All images verified successfully!${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠ Some images are missing. Build and push required images.${NC}"
    exit 1
fi