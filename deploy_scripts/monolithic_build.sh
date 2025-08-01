#!/usr/bin/env bash
# AI System Monolithic Build Script
# Generated from ai_docker_remediation_plan.md
# Execute this on a system with Docker installed

set -euo pipefail

echo "=== AI System Monolithic Build Script ==="
echo "Starting at: $(date)"

# Phase 2-B: Build monolithic images
echo ""
echo "=== PHASE 2-B: Building Monolithic Images ==="

echo "Building MainPC stack..."
docker build -f docker/mainpc/Dockerfile -t ai_system/mainpc_stack:latest .
if [ $? -eq 0 ]; then
    echo "✅ MainPC stack built successfully"
else
    echo "❌ MainPC stack build failed"
    exit 1
fi

echo "Building PC2 stack..."
docker build -f docker/pc2/Dockerfile -t ai_system/pc2_stack:latest .
if [ $? -eq 0 ]; then
    echo "✅ PC2 stack built successfully"
else
    echo "❌ PC2 stack build failed"
    exit 1
fi

echo ""
echo "=== Build Complete ==="
echo "Next steps: Run registry_push.sh to push images to GHCR"