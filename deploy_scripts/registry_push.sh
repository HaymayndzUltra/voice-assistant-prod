#!/usr/bin/env bash
# AI System Registry Push Script
# Phase 3: Push images to GitHub Container Registry

set -euo pipefail

echo "=== AI System Registry Push Script ==="
echo "Starting at: $(date)"

# Phase 3: Registry setup
echo ""
echo "=== PHASE 3: Registry & Tag Policy (GHCR) ==="

# Check if GHCR_PAT is set
if [ -z "${GHCR_PAT:-}" ]; then
    echo "❌ Error: GHCR_PAT environment variable not set"
    echo "Please set: export GHCR_PAT=<your-github-personal-access-token>"
    exit 1
fi

# Registry configuration
export REG=ghcr.io
export USER=haymayndzultra

# Login to GHCR
echo "Logging in to GitHub Container Registry..."
echo "$GHCR_PAT" | docker login ghcr.io -u "$USER" --password-stdin
if [ $? -eq 0 ]; then
    echo "✅ Successfully logged in to GHCR"
else
    echo "❌ Failed to login to GHCR"
    exit 1
fi

# Generate version tag
export VERSION_TAG=$(date +%Y%m%d).$(git rev-parse --short HEAD 2>/dev/null || echo "manual")
echo "Using version tag: $VERSION_TAG"

# Tag images
echo ""
echo "Tagging images..."

# MainPC
docker tag ai_system/mainpc_stack:latest ghcr.io/haymayndzultra/ai_system/mainpc_stack:$VERSION_TAG
docker tag ai_system/mainpc_stack:latest ghcr.io/haymayndzultra/ai_system/mainpc_stack:latest
echo "✅ Tagged MainPC stack"

# PC2
docker tag ai_system/pc2_stack:latest ghcr.io/haymayndzultra/ai_system/pc2_stack:$VERSION_TAG
docker tag ai_system/pc2_stack:latest ghcr.io/haymayndzultra/ai_system/pc2_stack:latest
echo "✅ Tagged PC2 stack"

# Push images
echo ""
echo "Pushing images to GHCR..."

# Push MainPC
echo "Pushing MainPC stack..."
docker push ghcr.io/haymayndzultra/ai_system/mainpc_stack:$VERSION_TAG
docker push ghcr.io/haymayndzultra/ai_system/mainpc_stack:latest
echo "✅ Pushed MainPC stack"

# Push PC2
echo "Pushing PC2 stack..."
docker push ghcr.io/haymayndzultra/ai_system/pc2_stack:$VERSION_TAG
docker push ghcr.io/haymayndzultra/ai_system/pc2_stack:latest
echo "✅ Pushed PC2 stack"

echo ""
echo "=== Registry Push Complete ==="
echo "Version tag used: $VERSION_TAG"
echo "Next steps: Update docker-compose files with the new image tags"