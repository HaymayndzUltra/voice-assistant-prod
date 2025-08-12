#!/bin/bash
# Master build script for all Docker images following plan.md
# Builds in correct dependency order: base → family → services

set -e

# Configuration
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
export ORG="haymayndzultra"
export TAG="20250812-$(git rev-parse --short HEAD 2>/dev/null || echo 'latest')"
export REGISTRY="ghcr.io/${ORG}"

echo "============================================================"
echo "🚀 BUILDING ALL OPTIMIZED DOCKER IMAGES"
echo "============================================================"
echo "Registry: ${REGISTRY}"
echo "Tag: ${TAG}"
echo ""

# Function to build and push
build_and_push() {
    local name=$1
    local context=$2
    local dockerfile=$3
    local machine=${4:-mainpc}
    
    echo "Building ${name}..."
    docker buildx build \
        --platform linux/amd64 \
        --build-arg MACHINE=${machine} \
        --cache-from type=registry,ref=${REGISTRY}/${name}:cache \
        --cache-to type=registry,ref=${REGISTRY}/${name}:cache,mode=max \
        -t ${REGISTRY}/${name}:${TAG} \
        -t ${REGISTRY}/${name}:latest \
        -f ${dockerfile} \
        ${context} \
        --push
    
    echo "✅ ${name} built and pushed"
    echo ""
}

# Create buildx builder if not exists
echo "Setting up Docker buildx..."
docker buildx create --name optimized-builder --use --driver docker-container 2>/dev/null || true
docker buildx use optimized-builder

# Phase 1: Build base images
echo "============================================================"
echo "PHASE 1: BASE IMAGES"
echo "============================================================"

build_and_push "base-python" "/workspace/docker/base-images/base-python" "Dockerfile"
build_and_push "base-utils" "/workspace/docker/base-images/base-utils" "Dockerfile"
build_and_push "base-cpu-pydeps" "/workspace/docker/base-images/base-cpu-pydeps" "Dockerfile"
build_and_push "base-gpu-cu121" "/workspace/docker/base-images/base-gpu-cu121" "Dockerfile"
build_and_push "legacy-py310-cpu" "/workspace/docker/base-images/legacy-py310-cpu" "Dockerfile"

# Phase 2: Build family images
echo "============================================================"
echo "PHASE 2: FAMILY IMAGES"
echo "============================================================"

build_and_push "family-web" "/workspace/docker/base-images/family-web" "Dockerfile"
build_and_push "family-torch-cu121" "/workspace/docker/base-images/family-torch-cu121" "Dockerfile"
build_and_push "family-llm-cu121" "/workspace/docker/base-images/family-llm-cu121" "Dockerfile"
build_and_push "family-vision-cu121" "/workspace/docker/base-images/family-vision-cu121" "Dockerfile"

# Phase 3: Build core services (6 main ones)
echo "============================================================"
echo "PHASE 3: CORE SERVICES"
echo "============================================================"

build_and_push "ai_system/model_ops_coordinator" "/workspace" "model_ops_coordinator/Dockerfile.optimized" "mainpc"
build_and_push "ai_system/real_time_audio_pipeline" "/workspace" "real_time_audio_pipeline/Dockerfile.optimized" "mainpc"
build_and_push "ai_system/affective_processing_center" "/workspace" "affective_processing_center/Dockerfile.optimized" "mainpc"
build_and_push "ai_system/unified_observability_center" "/workspace" "unified_observability_center/Dockerfile.optimized" "mainpc"
build_and_push "ai_system/self_healing_supervisor" "/workspace" "services/self_healing_supervisor/Dockerfile.optimized" "mainpc"
build_and_push "ai_system/central_error_bus" "/workspace" "services/central_error_bus/Dockerfile.optimized" "pc2"

# Phase 4: Build MainPC agents (optional - comment out to save time)
echo "============================================================"
echo "PHASE 4: MAINPC AGENTS (Optional)"
echo "============================================================"
echo "Skipping remaining 59 agents to save time..."
echo "To build all, uncomment the lines below"

# Uncomment to build all MainPC agents:
# build_and_push "ai_system/service_registry" "/workspace" "main_pc_code/services/serviceregistry/Dockerfile.optimized" "mainpc"
# build_and_push "ai_system/system_digital_twin" "/workspace" "main_pc_code/services/systemdigitaltwin/Dockerfile.optimized" "mainpc"
# ... (add all other agents here)

echo "============================================================"
echo "✅ BUILD COMPLETE!"
echo "============================================================"
echo ""
echo "Images built and pushed to: ${REGISTRY}"
echo "Tag: ${TAG}"
echo ""
echo "To deploy on MainPC:"
echo "  ./deploy_native_linux.sh"
echo ""
echo "To deploy on Docker Desktop:"
echo "  ./deploy_docker_desktop.sh"